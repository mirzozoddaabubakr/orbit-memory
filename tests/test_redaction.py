import hashlib
import json
import tempfile
import unittest

from memory import MemoryStore
from redaction import mask


class SecretTests(unittest.TestCase):
    def test_vendor_formats(self):
        for prefix,length in [("sk-proj-",38),("sk-ant-",40),("AIza",35),("github_pat_",72),
                              ("ghp_",36),("AKIA",16),("ASIA",16),("sb_secret_",32),
                              ("sb_publishable_",32),("sbp_",40),("sk_live_",24),("rk_test_",24)]:
            with self.subTest(prefix=prefix):
                fake=prefix+"Z"*length
                safe=mask("Use "+fake+" here.")
                self.assertNotIn(fake,safe)
                self.assertIn("<redacted:",safe)
                self.assertEqual(mask(safe),safe)

    def test_structured_secrets(self):
        jwt="eyJ"+"abc"*5+".eyJ"+"xyz"*6+"."+"s"*32
        private="-----BEGIN "+"RSA PRIVATE KEY-----\nnot-a-real-key\n-----END RSA PRIVATE KEY-----"
        for text,secret in [(jwt,jwt),(private,"not-a-real-key"),("Authorization: Bearer fake-demo-value","fake-demo-value"),
                            ("postgres://someone:example%20pass@localhost/db","example%20pass"),
                            ('export APP_TOKEN="two words"',"two words"),('{"password": "fake secret"}',"fake secret"),
                            ("AWS_SECRET_ACCESS_KEY=sample-secret","sample-secret")]:
            with self.subTest(format=text[:8]):
                safe=mask(text)
                self.assertNotIn(secret,safe)
                self.assertEqual(mask(safe),safe)

    def test_ordinary_text_code_and_hashes(self):
        for value in ["We store a password hash.", "def login(password: str):", "API_KEY=os.getenv('TEST')",
                      "const account = user.id;",hashlib.sha256(b'example').hexdigest(),"BUILD_MODE=debug"]:
            self.assertEqual(mask(value),value)

    def test_reader_choices_and_private_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            store=MemoryStore(directory)
            fake="ghp_"+"X"*36
            item={"provider":"Example","title":"Investigate "+fake,"transcript":"Token "+fake}
            mid=store.save(item,conversation_id="one")
            self.assertIsNone(store.original(mid))
            self.assertNotIn(fake,json.dumps(store.list()))
            store.review(mid,"keep",item["transcript"])
            self.assertEqual(store.original(mid),item["transcript"])
            self.assertNotIn(fake,json.dumps(store.export(mid)))
            self.assertNotIn(fake,json.dumps(store.read_page(mid,0,0,500)))
            store.review(mid,"private")
            self.assertIsNone(store.original(mid))
            self.assertEqual(store.search("","",20,0),[])
            for operation in (lambda:store.export(mid),lambda:store.read_page(mid,0,0,500),
                              lambda:store.generate_brief(mid,"fixture")):
                with self.assertRaises(ValueError):operation()
            store.review(mid,"shareable")
            store.review(mid,"redact")
            self.assertIn("<redacted:",store.export(mid)["memory"]["transcript"])


    def test_existing_database_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            store=MemoryStore(directory)
            fake="sk-ant-"+"V"*32
            mid=store.save({"title":"Legacy","transcript":"hello"})
            with store.connect() as db:
                db.execute("DELETE FROM settings WHERE name='masked_v1'")
                db.execute("UPDATE memories SET transcript=?,title=?,summary=?",(fake,fake,json.dumps({"overview":fake})))
                db.execute("INSERT INTO snapshots VALUES (?,?,?)",(mid,"old",fake))
            migrated=MemoryStore(directory)
            for data in [migrated.list(),migrated.snapshots(mid),migrated.export(mid),migrated.read_page(mid,1,0,7)]:
                self.assertNotIn(fake,json.dumps(data))
            self.assertEqual(migrated.snapshots(mid),["<redacted:Anthropic-key>"])
