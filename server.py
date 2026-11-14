"""Run Orbit on the loopback interface. Uses only Python's standard library."""
import argparse
import json
import mimetypes
import re
import webbrowser
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from memory import library_directory
from orbit_accounts import Accounts, AccountError

ROOT = Path(__file__).resolve().parent
PORT = 47831


class OrbitHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, payload, mime="application/json", headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode() if mime == "application/json" else payload
        self.send_response(status)
        self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name,value in (headers or {}).items():
            self.send_header(name,value)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; object-src 'none'")
        self.end_headers()
        self.wfile.write(body)

    def local(self):
        address = f"127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host") != address:
            return False
        origin = self.headers.get("Origin")
        return (not origin or origin == "http://" + address) and self.headers.get("Sec-Fetch-Site") != "cross-site"

    def cookie(self, name):
        values=SimpleCookie()
        try:
            values.load(self.headers.get("Cookie",""))
        except CookieError:
            return ""
        return values[name].value if name in values else ""

    def signed_in(self):
        user=self.server.accounts.identity(self.cookie("orbit_session"))
        expected=self.headers.get("X-Orbit-Account")
        return user if not expected or (user and user["id"]==expected) else None

    def do_GET(self):
        route = urlsplit(self.path).path
        valid_host = self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"
        if not self.local() and not (valid_host and route=="/" and self.headers.get("Sec-Fetch-Mode")=="navigate"):
            return self.reply(403, {"error": "Open Orbit at its local address."})
        account=self.signed_in()
        if route=="/api/session":
            return self.reply(200,{"user":account})
        if route in ("/","/index.html") and not account:
            return self.reply(303,{},headers={"Location":"/login.html"})
        if route.startswith("/api/") and not account:
            return self.reply(401,{"error":"Sign in to Orbit."})
        if account and route.startswith("/api/"):
            self.store=self.server.accounts.store(account["id"])
        if route.startswith("/api/skills/"):
            name=route.removeprefix("/api/skills/")
            if name not in ("orbit-memory","orbit-handoff"):
                return self.reply(404,{"error":"Skill not found."})
            return self.reply(200,(ROOT/"skills"/name/"SKILL.md").read_bytes(),"text/markdown",
                              headers={"Content-Disposition":'attachment; filename="SKILL.md"'})
        if route == "/api/memories":
            return self.reply(200, self.store.list())
        if route == "/api/agent-connections":
            from agent_connections import configurations
            profile=self.store.path.parent
            key=self.server.accounts.pairing_key(account["id"],"agent")
            (profile/"agent.key").write_text(key,encoding="utf-8")
            return self.reply(200, configurations(profile))
        if route=="/api/agent-key":
            return self.reply(200,{"key":self.server.accounts.pairing_key(account["id"],"agent")})
        if route == "/api/orbit-memory.mcpb":
            bundle = ROOT / "agent-connections" / "Orbit Memory.mcpb"
            if bundle.exists():
                return self.reply(200, bundle.read_bytes(), "application/octet-stream")
            return self.reply(404, {"error":"Run agent_connections.py to build the desktop extension."})
        if route == "/api/models":
            from local_brief import models
            return self.reply(200, models())
        if route == "/api/checklist":
            return self.reply(200, self.store.setup_steps())
        if route == "/api/setup":
            return self.reply(200, {"key": self.server.accounts.pairing_key(account["id"],"extension"), "folder": str(ROOT / "extension")})
        match = re.fullmatch(r"/api/history/([0-9a-f]{32})", route)
        if match:
            return self.reply(200, self.store.snapshots(match[1]))
        path = (ROOT / "app" / (route.lstrip("/") or "index.html")).resolve()
        if path.is_relative_to(ROOT / "app") and path.is_file():
            return self.reply(200, path.read_bytes(), mimetypes.guess_type(path)[0] or "application/octet-stream")
        self.reply(404, {"error": "Page not found."})

    def do_POST(self):
        capture = self.path == "/api/capture"
        if capture or self.path == "/api/selection":
            valid_host = self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"
            header=self.headers.get("Authorization","")
            owner=self.server.accounts.paired_owner(header[7:],"extension") if header.startswith("Bearer ") else None
            if not valid_host or not owner:
                return self.reply(403, {"error": "Pair the extension with your library first."})
            self.store=self.server.accounts.store(owner)
        elif self.path == "/api/pair":
            origin = self.headers.get("Origin", "")
            if not self.local() and not (self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}" and re.fullmatch(r"chrome-extension://[a-p]{32}", origin)):
                return self.reply(403, {"error": "Pair from the Orbit extension."})
        elif not self.local():
            return self.reply(403, {"error": "Local access required."})
        if self.headers.get_content_type() != "application/json":
            return self.reply(415, {"error": "Expected JSON."})
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if not 0 < length <= 16_000_000:
                return self.reply(413, {"error": "Import one conversation under 12 MB at a time."})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Expected a conversation object.")
            if self.path in ("/api/auth/signin","/api/auth/signup"):
                accounts=self.server.accounts
                signup=self.path.endswith("/signup")
                user=accounts.authenticate(data.get("email"),data.get("password"),signup)
                session=accounts.issue(user)
                return self.reply(200,{"ok":True},headers={"Set-Cookie":"orbit_session="+session+"; Path=/; HttpOnly; SameSite=Strict; Max-Age=604800"})
            if self.path=="/api/auth/logout":
                self.server.accounts.logout(self.cookie("orbit_session"))
                return self.reply(200,{"ok":True},headers={"Set-Cookie":"orbit_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax"})
            if self.path not in ("/api/capture","/api/selection","/api/pair"):
                account=self.signed_in()
                if not account:
                    return self.reply(401,{"error":"Sign in to Orbit."})
                self.store=self.server.accounts.store(account["id"])
            if self.path in ("/api/memories", "/api/capture", "/api/selection"):
                return self.reply(200, {"id": self.store.save(data, capture)})
            if self.path == "/api/extension-loaded":
                self.store.complete_step("extension")
                return self.reply(200, {"ok": True})
            if self.path=="/api/review":
                self.store.review(data.get("id"),data.get("action"),data.get("original"))
                return self.reply(200,{"ok":True})
            if self.path=="/api/original":
                return self.reply(200,{"text":self.store.original(data.get("id"))})
            if self.path=="/api/handoff":
                return self.reply(200,self.store.export(data.get("id")))
            if self.path == "/api/pair":
                owner = self.server.accounts.paired_owner(str(data.get("key", "")), "extension")
                if owner:
                    self.server.accounts.store(owner).complete_step("pair")
                    return self.reply(200, {"ok": True})
                return self.reply(403, {"error": "Pairing code did not match."})
            if self.path == "/api/change":
                action = data.get("action")
                if action != "delete" and type(action) is not bool:
                    raise ValueError("Invalid action.")
                self.store.change(data.get("id", ""), action)
                return self.reply(200, {"ok": True})
            if self.path == "/api/brief":
                return self.reply(200, self.store.generate_brief(data.get("id"), data.get("model")))
            self.reply(404, {"error": "Unknown action."})
        except AccountError as error:
            self.reply(error.status,{"error":str(error)})
        except (ValueError, TypeError, UnicodeError) as error:
            self.reply(400, {"error": str(error)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--data-dir", default=str(library_directory()))
    args = parser.parse_args()
    url = f"http://127.0.0.1:{args.port}"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), OrbitHandler)
    except OSError:
        from urllib.request import urlopen
        with urlopen(url + "/api/session", timeout=2) as response:
            if "user" not in json.load(response):
                raise
        if args.open:
            webbrowser.open(url)
    else:
        server.accounts = Accounts(args.data_dir)
        if args.open:
            webbrowser.open(url)
        server.serve_forever()