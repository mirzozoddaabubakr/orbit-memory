import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from memory import MemoryStore
from orbit_hook import capture


class CaptureTests(unittest.TestCase):
    def test_hooks_save_user_and_assistant_text_once(self):
        q, a = "Build an orbit", "We chose a tilted plane."
        sources = {
            "claude":[{"type":"user","message":{"content":q}},
                      {"type":"assistant","message":{"content":[{"type":"thinking","thinking":"private"},
                       {"type":"text","text":a},{"type":"tool_use","input":{"secret":"hidden"}}]}}],
            "qwen":[{"type":"user","message":{"parts":[{"text":q}]}},
                    {"type":"assistant","message":{"parts":[{"thought":True,"text":"private"},{"text":a}]}}],
            "codex":[{"type":"event_msg","payload":{"type":"user_message","message":q}},
                     {"type":"event_msg","payload":{"type":"agent_reasoning","text":"private"}},
                     {"type":"event_msg","payload":{"type":"agent_message","message":a}}],
            "gemini":[{"id":"u","type":"user","content":q},
                      {"id":"a","type":"gemini","content":[{"text":"draft"}]},
                      {"$patch":{"id":"a","content":[{"text":a}]}}]
        }
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(tmp)
            for host,rows in sources.items():
                path = Path(tmp)/(host+".jsonl")
                path.write_text("\n".join(json.dumps(r) for r in rows),encoding="utf-8")
                event = {"hook_event_name":"AfterAgent" if host=="gemini" else "Stop",
                         "session_id":"same-host-issued-id","transcript_path":str(path)}
                for _ in range(2):
                    capture(host,event,store)
            self.assertEqual(len(store.list()),4)
            for m in store.list():
                self.assertEqual(m["transcript"],f"You: {q}\n\n{m['provider']}: {a}")
            path = Path(tmp)/"legacy.json"
            path.write_text(json.dumps({"messages":sources["gemini"][:2]}),encoding="utf-8")
            capture("gemini",{"session_id":"new","hook_event_name":"AfterAgent","transcript_path":str(path)},store)
            self.assertEqual(len(store.list()),5)

    def test_concurrent_turns_retry_update_and_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(tmp)
            def append(i):
                return store.save({"provider":"Claude","title":"Orbit","transcript":f"Turn {i}"},
                                  conversation_id="one", turn_id=str(i))
            with ThreadPoolExecutor(4) as pool:
                ids=list(pool.map(append,[1,2,3,1,2,3]))
            self.assertEqual(len(set(ids)),1)
            row,=store.list()
            self.assertEqual(sorted(row["transcript"].split("\n\n")),["Turn 1","Turn 2","Turn 3"])
            with self.assertRaises(ValueError):
                store.save({"provider":"Claude","title":"Orbit","transcript":"different"},conversation_id="one",turn_id="1")
            store.save({"provider":"Claude","title":"Edited","transcript":"Revised orbit"},conversation_id="one")
            self.assertEqual(store.read_page(ids[0],1,0,40)["transcript"],row["transcript"])
            self.assertEqual(store.search("ORBIT","claude",10,0)[0]["id"],ids[0])
            store.change(ids[0],"delete")
            append(1)
            self.assertEqual(store.list()[0]["transcript"],"Turn 1")
