import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
from memory import MemoryStore
from orbit_accounts import Accounts
from uuid import uuid4
from server import OrbitHandler


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = MemoryStore(self.temp.name)
        self.data = {"title": "Orbital paths", "provider": "Claude",
                     "transcript": "You: Build an orbit viewer.\nClaude: We chose elliptical paths.\nNext, add picking."}

    def test_storage_summary_and_retry(self):
        with ThreadPoolExecutor(4) as pool:
            ids = list(pool.map(lambda _: self.store.save(self.data), range(8)))
        self.assertEqual(len(set(ids)), 1)
        self.store.change(ids[0], True)
        saved, = MemoryStore(self.temp.name).list()
        self.assertTrue(saved["starred"])
        self.assertEqual(saved["transcript"], self.data["transcript"])
        self.assertIn("We chose elliptical paths.", saved["summary"]["decisions"])
        self.assertIn("Next, add picking.", saved["summary"]["next"])

    def test_partial_and_alternate_captures(self):
        data = {**self.data, "url": "https://claude.ai/chat/test"}
        mid = self.store.save(data, True)
        self.store.save({**data, "transcript": "We chose elliptical paths."}, True)
        self.assertEqual(self.store.list()[0]["transcript"], data["transcript"])
        self.store.save({**data, "transcript": "An edited conversation"}, True)
        self.assertEqual(self.store.snapshots(mid), [data["transcript"]])
        self.store.change(mid, "delete")
        self.assertEqual(self.store.snapshots(mid), [])
        self.assertEqual(self.store.list(), [])

    def test_api_capture_and_pair(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), OrbitHandler)
        server.accounts = Accounts(self.temp.name)
        uid=str(uuid4())
        key=server.accounts.pairing_key(uid,'extension')
        self.store=server.accounts.store(uid)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        def post(path, data, **headers):
            req = Request(f"http://127.0.0.1:{server.server_port}/api/"+path,
                          data=json.dumps(data).encode(),headers={"Content-Type":"application/json", **headers})
            with urlopen(req) as response:
                return json.load(response)
        ext = "chrome-extension://" + "a"*32
        self.assertTrue(post("pair", {"key":key}, Origin=ext)["ok"])
        captured = {**self.data,"url":"https://claude.ai/chat/test"}
        with self.assertRaises(HTTPError) as bad:
            post("capture", captured, Origin=ext)
        self.assertEqual(bad.exception.code, 403)
        with self.assertRaises(HTTPError):
            post("memories", self.data, Origin="https://unrelated.example")
        for route in ("selection", "capture"):
            self.assertTrue(post(route, captured, Origin=ext, Authorization="Bearer "+key)["id"])
        self.assertEqual(len(self.store.list()), 2)

    def test_local_model_brief_contract(self):
        from local_brief import synthesize
        brief = {"overview":"A solar viewer.", "highlights":["Elliptical orbits."], "decisions":[], "next":[]}
        def fixture(route, payload=None):
            if route == "tags":
                return {"models":[{"name":"fixture","size":500_000_000}]}
            self.assertEqual(payload["model"], "fixture")
            return {"message":{"content":json.dumps(brief)}}
        with patch("local_brief.request", side_effect=fixture):
            mid = self.store.save(self.data)
            self.store.generate_brief(mid, "fixture")
            self.assertEqual(self.store.list()[0]["summary"]["overview"], brief["overview"])
            self.assertEqual(synthesize("fixture", "hello world "*1100)["model"],"fixture")


if __name__ == "__main__":
    unittest.main()
