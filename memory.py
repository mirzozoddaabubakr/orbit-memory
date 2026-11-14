"""Local memory storage and source-grounded conversation briefs."""
import collections
import datetime
import hashlib
import json
import os
import re
import secrets
import sqlite3
import project_brief
import projects
from recall import initialize as initialize_recall
from redaction import mask, safe_object
from contextlib import contextmanager, closing
from pathlib import Path


def library_directory():
    return Path(os.environ.get("ORBIT_DATA_DIR") or Path(os.getenv("LOCALAPPDATA", Path.home())) / "OrbitMemory")


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def compact(text, limit):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def describe(transcript):
    # Rank source sentences and keep their original order and wording.
    clean = re.sub(r"```[\s\S]*?(?:```|$)", " [code in transcript] ", transcript)
    lines = [re.sub(r"^(?:User|Human|You|Assistant|Claude|ChatGPT|Gemini|Qwen):\s*", "", s.strip(), flags=re.I)
             for s in re.split(r"\n+|(?<=[.!?。！？])\s+", clean) if s.strip()]
    lines = list(dict.fromkeys(x for x in lines if x)) or [transcript]
    def words(s):
        return set(re.findall(r"[^\W\d_]{4,}", s.lower())) - set("that this with from have would should there their about could please using into them your what will these were they then like".split())
    counts = collections.Counter(w for line in lines for w in words(line))
    def rank(i):
        terms = words(lines[i])
        return sum(counts[w] for w in terms) / max(1, len(terms)) + (2 if i == len(lines)-1 else 0)
    best = sorted(sorted(range(1, len(lines)), key=rank, reverse=True)[:3])
    decisions = [compact(s, 520) for s in lines if re.search(r"\b(decided|agreed|chose|chosen|we.ll use|let.s use|settled on|implemented|completed|we used)\b", s, re.I)]
    pending = [compact(s, 520) for s in lines if re.search(r"\b(next|to.do|remaining|still need|follow.up|unresolved|pending|need to)\b|\?\s*$", s, re.I)]
    return {"overview": compact(lines[0], 440), "highlights": [compact(lines[i], 500) for i in best],
            "decisions": decisions[-8:], "next": pending[-8:]}


class MemoryStore:
    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "orbit.sqlite3"
        with self.connect() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY, title TEXT, provider TEXT, transcript TEXT,
                summary TEXT, url TEXT, created TEXT, updated TEXT, starred INTEGER DEFAULT 0);
              CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT);
              CREATE TABLE IF NOT EXISTS snapshots (id TEXT, digest TEXT, transcript TEXT,
                PRIMARY KEY(id,digest));
              CREATE TABLE IF NOT EXISTS agent_turns (id TEXT, turn_id TEXT, digest TEXT,
                PRIMARY KEY(id,turn_id));
            """)
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS privacy(id TEXT PRIMARY KEY, private INTEGER DEFAULT 0, original TEXT, reviewed INTEGER DEFAULT 0)")
            if not db.execute("SELECT 1 FROM settings WHERE name='masked_v1'").fetchone():
                for row in db.execute("SELECT * FROM memories").fetchall():
                    fields=[mask(row[k]) for k in ("transcript","title","provider","url")]
                    brief=json.dumps(safe_object(json.loads(row["summary"])))
                    db.execute("UPDATE memories SET transcript=?,title=?,provider=?,url=?,summary=? WHERE id=?",(*fields,brief,row["id"]))
                for row in db.execute("SELECT rowid,transcript FROM snapshots").fetchall():
                    db.execute("UPDATE snapshots SET transcript=? WHERE rowid=?",(mask(row[1]),row[0]))
                db.execute("INSERT INTO settings VALUES ('masked_v1','1')")
            projects.initialize(db)
            project_brief.initialize(db)
            initialize_recall(db)
            db.execute("INSERT OR IGNORE INTO settings VALUES ('pair',?)", (secrets.token_urlsafe(32),))

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.path, timeout=15)) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA secure_delete=ON")
            with db:
                yield db

    def complete_step(self, step):
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO settings VALUES (?, '1')", ("setup_"+step,))

    def setup_steps(self):
        with self.connect() as db:
            steps = {row[0] for row in db.execute("SELECT name FROM settings WHERE name LIKE 'setup_%'")}
            saved = bool(db.execute("SELECT 1 FROM memories LIMIT 1").fetchone())
        return {"account": True, "extension": "setup_extension" in steps or "setup_pair" in steps,
                "pair": "setup_pair" in steps, "chat": saved or "setup_chat" in steps,
                "agent": "setup_agent" in steps}

    def key(self):
        with self.connect() as db:
            return db.execute("SELECT value FROM settings WHERE name='pair'").fetchone()[0]

    def list(self):
        with self.connect() as db:
            rows = db.execute("SELECT m.*,(SELECT project FROM memberships WHERE chat=m.id) AS project_id,coalesce(p.private,0) AS private,p.original IS NOT NULL AS kept,coalesce(p.reviewed,0) AS reviewed FROM memories m LEFT JOIN privacy p USING(id) ORDER BY updated DESC").fetchall()
        return [{**dict(r), "summary": json.loads(r["summary"]), "starred": bool(r["starred"])} for r in rows]

    def save(self, data, captured=False, *, conversation_id=None, turn_id=None):
        if not isinstance(data, dict):
            raise ValueError("A memory must contain conversation text.")
        def field(key):
            val = data.get(key, "")
            if not isinstance(val, str):
                raise ValueError("Invalid " + key)
            return val.strip()
        transcript, provider = field("transcript"), field("provider")[:100] or "Other"
        if not transcript or len(transcript.encode()) > 12_000_000:
            raise ValueError("Use a nonempty transcript under 12 MB.")
        title = field("title")[:160] or compact(transcript.splitlines()[0], 80)
        url = field("url") if captured else ""
        if captured and not re.fullmatch(r"https://[^\s?#]+", url):
            raise ValueError("A conversation URL is required.")
        digest = hashlib.sha256(transcript.encode()).hexdigest()
        identity = url if captured else provider + "\n" + title + "\n" + digest
        mid = hashlib.sha256(identity.encode()).hexdigest()[:32]
        if conversation_id is not None:
            if not isinstance(conversation_id, str) or not 0 < len(conversation_id.strip()) <= 512:
                raise ValueError("Supply a stable conversation ID of 1 to 512 characters.")
            identity = json.dumps(["orbit-agent", provider.casefold(), conversation_id.strip()])
            mid = hashlib.sha256(identity.encode()).hexdigest()[:32]
        transcript = mask(transcript)
        title = mask(field("title"))[:160] or compact(transcript.splitlines()[0],80)
        provider = mask(field("provider"))[:100] or "Other"
        url = mask(url)
        stamp = now()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT transcript FROM memories WHERE id=?", (mid,)).fetchone()
            if turn_id is not None:
                if conversation_id is None or not isinstance(turn_id,str) or not 0 < len(turn_id.strip()) <= 512:
                    raise ValueError("Supply a stable turn ID of 1 to 512 characters.")
                saved = db.execute("SELECT digest FROM agent_turns WHERE id=? AND turn_id=?", (mid,turn_id)).fetchone()
                if saved:
                    if saved[0] != digest:
                        raise ValueError("That turn ID already identifies different text.")
                    return mid
                db.execute("INSERT INTO agent_turns VALUES (?,?,?)", (mid,turn_id,digest))
                if old:
                    transcript = old[0] + "\n\n" + transcript
                    if len(transcript.encode()) > 12_000_000:
                        raise ValueError("The combined conversation exceeds 12 MB.")
            if old and old[0] == transcript:
                return mid
            if old and (captured or conversation_id is not None):
                # A partially rendered page or edited branch must never erase previous text.
                if transcript in old[0]:
                    return mid
                if old[0] not in transcript:
                    db.execute("INSERT OR IGNORE INTO snapshots VALUES (?,?,?)",
                               (mid, hashlib.sha256(old[0].encode()).hexdigest(), old[0]))
            db.execute("INSERT OR IGNORE INTO settings VALUES ('setup_chat','1')")
            db.execute("UPDATE privacy SET original=NULL,reviewed=0 WHERE id=?", (mid,))
            db.execute("""INSERT INTO memories(id,title,provider,transcript,summary,url,created,updated)
                   VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,
                   transcript=excluded.transcript,summary=excluded.summary,updated=excluded.updated""",
                   (mid, title, provider, transcript, json.dumps(describe(transcript)), url, stamp, stamp))
        return mid

    def search(self, query, provider, limit, offset):
        with self.connect() as db:
            db.create_function("fold", 1, lambda value: value.casefold() if value else "")
            return [safe_object(dict(row)) for row in db.execute("""
                SELECT id,title,provider,updated,json_extract(summary,'$.overview') AS overview
                FROM memories WHERE id NOT IN (SELECT id FROM privacy WHERE private=1) AND (?='' OR fold(provider)=?) AND
                (instr(fold(title),?) OR instr(fold(transcript),?) OR instr(fold(provider),?))
                ORDER BY updated DESC,id LIMIT ? OFFSET ?
            """, (provider,provider.casefold(),*[query.casefold()]*3,limit,offset))]

    def read_page(self, mid, version, offset, limit):
        with self.connect() as db:
            db.execute("BEGIN")
            row = db.execute("SELECT title,provider,summary,url,updated FROM memories WHERE id=? AND id NOT IN (SELECT id FROM privacy WHERE private=1)", (mid,)).fetchone()
            if not row:
                raise ValueError("Memory not found.")
            count = db.execute("SELECT count(*) FROM snapshots WHERE id=?", (mid,)).fetchone()[0]
            if version == 0:
                source = "SELECT transcript FROM memories WHERE id=?"
                args = (mid,)
            else:
                source = "SELECT transcript FROM snapshots WHERE id=? ORDER BY rowid LIMIT 1 OFFSET ?"
                args = (mid,version-1)
            result = db.execute(source,args).fetchone()
            if not result:
                raise ValueError("Invalid version or offset.")
            # Mask before slicing so a page boundary cannot split a credential.
            transcript = mask(result[0])
            if offset > len(transcript):
                raise ValueError("Invalid version or offset.")
            end=offset+limit
            return {**safe_object(dict(row)), "summary":safe_object(json.loads(row["summary"])),
                    "transcript":transcript[offset:end],"version":version,"earlier_versions":count,
                    "next_offset":end if end < len(transcript) else None}

    def snapshots(self, mid):
        with self.connect() as db:
            return [r[0] for r in db.execute("SELECT transcript FROM snapshots WHERE id=? ORDER BY rowid", (mid,))]

    def generate_brief(self, mid, model):
        from local_brief import synthesize
        with self.connect() as db:
            row = db.execute("SELECT transcript FROM memories WHERE id=?", (mid,)).fetchone()
        if not row:
            raise ValueError("Memory not found.")
        if self.is_private(mid):
            raise ValueError("Private memory cannot be sent to a model.")
        brief = safe_object(synthesize(model, mask(row[0])))
        with self.connect() as db:
            updated = db.execute("UPDATE memories SET summary=? WHERE id=? AND transcript=?",
                                 (json.dumps(brief), mid, row[0]))
            if not updated.rowcount:
                raise ValueError("The conversation changed. Generate its brief again.")
        return brief

    def is_private(self, mid):
        with self.connect() as db:
            return bool(db.execute("SELECT 1 FROM privacy WHERE id=? AND private=1",(mid,)).fetchone())

    def review(self, mid, action, original=None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT transcript FROM memories WHERE id=?",(mid,)).fetchone()
            if not row:
                raise ValueError("Memory not found.")
            db.execute("INSERT OR IGNORE INTO privacy(id) VALUES (?)",(mid,))
            if action=="keep":
                if not isinstance(original,str) or not original or mask(original.strip())!=row[0]:
                    raise ValueError("Paste the matching original conversation to keep a local copy.")
                db.execute("UPDATE privacy SET original=?,reviewed=1 WHERE id=?",(original,mid))
            elif action in ("private","shareable"):
                db.execute("UPDATE privacy SET private=?,original=CASE WHEN ? THEN NULL ELSE original END WHERE id=?",(int(action=="private"),int(action=="private"),mid))
            elif action=="redact":
                db.execute("UPDATE privacy SET original=NULL,reviewed=1 WHERE id=?",(mid,))
            else:
                raise ValueError("Unknown privacy action.")

    def original(self, mid):
        with self.connect() as db:
            row=db.execute("SELECT original FROM privacy WHERE id=?",(mid,)).fetchone()
            return row[0] if row else None

    def export(self, mid):
        with self.connect() as db:
            db.execute("BEGIN")
            row=db.execute("SELECT * FROM memories WHERE id=? AND id NOT IN (SELECT id FROM privacy WHERE private=1)",(mid,)).fetchone()
            if not row:
                raise ValueError("This memory is unavailable for handoff.")
            versions=[r[0] for r in db.execute("SELECT transcript FROM snapshots WHERE id=? ORDER BY rowid",(mid,))]
            return safe_object({"memory":{**dict(row),"summary":json.loads(row["summary"])},"history":versions})

    def change(self, mid, action):
        with self.connect() as db:
            if action == "delete":
                db.execute("DELETE FROM privacy WHERE id=?",(mid,))
                db.execute("DELETE FROM agent_turns WHERE id=?", (mid,))
                db.execute("DELETE FROM snapshots WHERE id=?", (mid,))
                cursor = db.execute("DELETE FROM memories WHERE id=?", (mid,))
            else:
                cursor = db.execute("UPDATE memories SET starred=? WHERE id=?", (int(action), mid))
            if not cursor.rowcount:
                raise ValueError("Memory not found.")
