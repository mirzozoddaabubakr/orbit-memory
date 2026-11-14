"""Account-bound local sessions and integration credentials."""
import hmac
import re
import hashlib
import secrets
import sqlite3
import time
import os
import threading
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from memory import MemoryStore, library_directory

_hash_slots = threading.BoundedSemaphore(2)


class AccountError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Accounts:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.path = self.root/"accounts.sqlite3"
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions(key TEXT PRIMARY KEY, uid TEXT, email TEXT, expires INTEGER);
            CREATE TABLE IF NOT EXISTS credentials(kind TEXT, uid TEXT, secret TEXT UNIQUE, PRIMARY KEY(kind,uid));
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, email TEXT UNIQUE, salt BLOB NOT NULL, password_hash BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS captured_sessions(host TEXT, sid TEXT, uid TEXT, PRIMARY KEY(host,sid));
            CREATE TABLE IF NOT EXISTS attempts(email TEXT PRIMARY KEY, count INTEGER, until INTEGER);
            """)

    @contextmanager
    def db(self):
        with closing(sqlite3.connect(self.path,timeout=12)) as db, db:
            yield db

    def issue(self, user):
        uid, email = str(UUID(user["id"])), user["email"]
        session = secrets.token_urlsafe(32)
        expiry = int(time.time()) + 7 * 24 * 3600
        with self.db() as db:
            db.execute("DELETE FROM sessions WHERE expires<=?",(time.time(),))
            db.execute("INSERT INTO sessions VALUES (?,?,?,?)",(digest(session),uid,email,expiry))
        return session

    def identity(self, session):
        with self.db() as db:
            row=db.execute("SELECT uid,email FROM sessions WHERE key=? AND expires>?",(digest(session),time.time())).fetchone()
        return {"id":row[0],"email":row[1]} if row else None

    def logout(self, session):
        with self.db() as db:
            db.execute("DELETE FROM sessions WHERE key=?",(digest(session),))

    def store(self, uid):
        return MemoryStore(self.root/"users"/str(UUID(uid)))

    def pairing_key(self, uid, kind):
        with self.db() as db:
            db.execute("INSERT OR IGNORE INTO credentials VALUES (?,?,?)",(kind,uid,secrets.token_urlsafe(32)))
            return db.execute("SELECT secret FROM credentials WHERE kind=? AND uid=?",(kind,uid)).fetchone()[0]

    def paired_owner(self, key, kind):
        with self.db() as db:
            row=db.execute("SELECT uid FROM credentials WHERE kind=? AND secret=?", (kind,key)).fetchone()
        return row[0] if row else None

    def local_account(self, email, password, signup):
        email = email.strip().casefold()
        if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise AccountError("Enter a valid email address.")
        if len(password) > 1024 or (signup and len(password) < 12):
            raise AccountError("Use a password between 12 and 1024 characters.")
        with self.db() as db:
            row = db.execute("SELECT id,salt,password_hash FROM users WHERE email=?", (email,)).fetchone()
            salt = secrets.token_bytes(16) if signup or not row else row[1]
            with _hash_slots:
                hashed = hashlib.scrypt(password.encode(), salt=salt, n=32768, r=8, p=1, maxmem=64*1024*1024)
            if signup:
                uid = str(uuid4())
                try:
                    db.execute("INSERT INTO users VALUES (?,?,?,?)", (uid,email,salt,hashed))
                except sqlite3.IntegrityError as error:
                    raise AccountError("This email already has a device account. Sign in.") from error
            elif row and hmac.compare_digest(row[2],hashed):
                uid = row[0]
            else:
                raise AccountError("Email or password did not match.",401)
        return {"id":uid,"email":email}

    def authenticate(self, email, password, signup):
        import json
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError, URLError
        if not isinstance(email,str) or not isinstance(password,str) or not email.strip() or not password:
            raise AccountError("Enter your email and password.")
        try:
            config=json.loads(Path(__file__).with_name("orbit-auth.json").read_text())
            if not config.get("url","").startswith("https://") or not config.get("publishable_key"):
                raise ValueError()
        except FileNotFoundError:
            return self.local_account(email,password,signup)
        except (OSError,ValueError,TypeError) as error:
            raise AccountError("Account setup is incomplete. Set the Supabase URL and publishable key in orbit-auth.json.",503) from error
        route="signup" if signup else "token?grant_type=password"
        req=Request(config["url"]+"/auth/v1/"+route,
                    data=json.dumps({"email":email.strip(),"password":password}).encode(),
                    headers={"apikey":config["publishable_key"],"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=15) as response:
                result=json.load(response)
            if not result.get("access_token"):
                raise AccountError("Check your email to confirm your account, then sign in.",202)
            verify=Request(config["url"]+"/auth/v1/user",headers={"apikey":config["publishable_key"],
                           "Authorization":"Bearer "+result["access_token"]})
            with urlopen(verify,timeout=15) as response:
                user=json.load(response)
            return {"id":str(UUID(user["id"])),"email":user["email"]}
        except HTTPError as error:
            try: message=json.load(error)
            except ValueError: message={}
            raise AccountError(message.get("msg") or message.get("error_description") or "Sign-in failed.",error.code) from error
        except (URLError,TimeoutError) as error:
            raise AccountError("Could not reach the account service. Try again.",503) from error

    def agent_store(self, key, host="", sid=""):
        uid=self.paired_owner(key,"agent")
        if not uid:
            raise AccountError("Pair this agent with your Orbit account in Sources.",401)
        if host and sid:
            with self.db() as db:
                db.execute("INSERT OR IGNORE INTO captured_sessions VALUES (?,?,?)",(host,sid,uid))
                owner=db.execute("SELECT uid FROM captured_sessions WHERE host=? AND sid=?",(host,sid)).fetchone()[0]
                if owner!=uid:
                    raise AccountError("This chat was paired with a different Orbit account. Start a new chat.",403)
        return self.store(uid)


def agent_key(path=None):
    if not path:
        path=os.environ.get("ORBIT_AGENT_KEY_FILE")
    return Path(path).read_text(encoding="utf-8").strip() if path else os.environ.get("ORBIT_AGENT_KEY","")
