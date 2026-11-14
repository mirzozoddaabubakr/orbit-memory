import json
import tempfile
import unittest
from uuid import uuid4
from unittest.mock import patch

import projects
import project_brief as briefs
from memory import MemoryStore
from orbit_accounts import Accounts
from recall import recall, HEADER,estimate


class ProjectTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.accounts=Accounts(tmp.name)
        self.store=self.accounts.store(str(uuid4()))
        self.pid=self.change("create",name="Orbit atlas")["project_id"]
        self.chat=self.store.save({"title":"Orbit atlas","transcript":
            "Goal: map the stars. We chose SQLite because offline access matters. What remains? Next build rings."})

    def change(self,action,**data):
        return projects.change(self.store,{"project_id":getattr(self,"pid",None),"action":action,**data})

    def assign(self):
        self.change("assign",chat=self.chat)
        return briefs.generate(self.store,self.pid)

    def review(self,action,line=None,**args):
        return briefs.review(self.store,dict(project_id=self.pid,action=action,line=line,**args))

    def accept_all(self):
        for line in self.assign()["lines"]:
            self.review("accept",line["id"])
        self.review("review")

    def test_project_crud_delete_keeps_chats(self):
        self.assign()
        self.change("rename",name="Renamed")
        self.assertEqual(projects.listing(self.store)[0]["name"],"Renamed")
        self.change("delete")
        self.assertEqual(projects.listing(self.store),[])
        self.assertIsNone(self.store.list()[0]["project_id"])
        self.assertEqual(self.store.list()[0]["id"],self.chat)

    def test_suggestion_requires_approval(self):
        self.assertEqual(projects.suggest(self.store,self.chat)["id"],self.pid)
        self.assertIsNone(self.store.list()[0]["project_id"])
        self.assign()
        self.assertIsNone(projects.suggest(self.store,self.chat))

    def test_private_source_and_moved_source_excluded(self):
        self.accept_all()
        self.store.review(self.chat,"private")
        self.assertFalse(briefs.generate(self.store,self.pid)["lines"])
        self.assertFalse(briefs.handoff(self.store,self.pid)["lines"])
        self.assertFalse(recall(self.store,"atlas")["items"])
        self.store.review(self.chat,"shareable")
        self.change("assign",project_id=None,chat=self.chat)
        self.assertFalse(briefs.handoff(self.store,self.pid)["lines"])

    def test_edited_and_rejected_lines_survive_updates(self):
        a,b,*_=self.assign()["lines"]
        self.review("edit",a["id"],text="Map the stars.")
        self.review("reject",b["id"])
        chat=self.store.save({"title":"Atlas rings","transcript":"Next test the rings."})
        self.change("assign",chat=chat)
        result=briefs.generate(self.store,self.pid)
        self.assertEqual(result["status"],"draft")
        self.assertTrue(any(l["edited"] and l["text"]=="Map the stars." for l in result["lines"]))
        self.assertFalse(any(l["id"]==b["id"] for l in result["lines"]))
        self.assertTrue(any(l["source_id"]==chat and l["state"]=="pending" for l in result["lines"]))
        self.assertFalse(any(l["source_id"]==chat for l in briefs.handoff(self.store,self.pid)["lines"]))

    def test_secrets_and_source_links(self):
        fake="ghp_"+"Z"*36
        chat=self.store.save(dict(title=fake,transcript="Goal: rotate "+fake))
        self.change("assign",chat=chat)
        result=briefs.generate(self.store,self.pid)
        self.assertNotIn(fake,json.dumps(result))
        for l in result["lines"]:
            self.assertIn(l["evidence"],self.store.read_page(l["source_id"],0,0,1000)["transcript"])
            self.review("edit",l["id"],text="Rotate "+fake)
        self.assertNotIn(fake,json.dumps(briefs.handoff(self.store,self.pid)))

    def test_cross_account_and_existing_library_migration(self):
        other=self.accounts.store(str(uuid4()))
        with self.assertRaises(ValueError):briefs.handoff(other,self.pid)
        self.assertFalse(recall(other,"atlas")["items"])
        with self.store.connect() as db:
            for r in db.execute("SELECT name FROM sqlite_master WHERE name LIKE 'brief_dirty_%'").fetchall():
                db.execute("DROP TRIGGER "+r[0])
            for table in ("brief_lines","memberships","projects"):
                db.execute("DROP TABLE "+table)
        store=MemoryStore(self.store.path.parent)
        self.assertEqual(store.list()[0]["id"],self.chat)
        self.assertFalse(projects.listing(store))

    def test_project_first_budgets_and_review_status(self):
        self.accept_all()
        result=recall(self.store,"atlas")
        self.assertTrue(result["text"].startswith(HEADER))
        self.assertEqual(result["items"][0]["project_id"],self.pid)
        self.assertEqual(result["items"][1]["memory_id"],self.chat)
        self.assertIn("because offline access matters",result["text"])
        self.assertEqual(briefs.handoff(self.store,self.pid)["status"],"reviewed")
        for budget in (28,100,300):
            self.assertLessEqual(estimate(recall(self.store,"atlas",budget)["text"]),budget)

    def test_model_selects_only_source_excerpts(self):
        self.assign()
        with patch("local_brief.models",return_value=["fixture"]),patch("local_brief.request",return_value={
                "message":{"content":'{"indices":[0,999,"unsupported claim"]}'}}):
            result=briefs.generate(self.store,self.pid,"fixture")
        self.assertEqual(sum(line["model_suggested"] for line in result["lines"]),1)
        self.assertNotIn("unsupported claim",json.dumps(result))
