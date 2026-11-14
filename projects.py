"""Projects are local to a single account library."""
import json
import re
from uuid import uuid4

from redaction import mask


def initialize(db):
    db.execute("CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,reviewed INTEGER DEFAULT 0)")
    db.execute("""CREATE TABLE IF NOT EXISTS memberships(chat TEXT PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
                project TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE)""")


def require_project(db, pid):
    project=db.execute("SELECT * FROM projects WHERE id=?",(pid,)).fetchone()
    if not project:
        raise ValueError("Project unavailable.")
    return project


def words(text):
    return set(re.findall(r"[^\W_]{3,}",text.casefold())) - set("the and this that with for from have chat about into".split())


def listing(store):
    with store.connect() as db:
        return [dict(r) for r in db.execute("SELECT id,name FROM projects ORDER BY name COLLATE NOCASE,id")]


def suggest(store, chat):
    with store.connect() as db:
        rows=db.execute("""SELECT m.id,m.title,m.summary,l.project FROM memories m
            LEFT JOIN memberships l ON l.chat=m.id WHERE NOT EXISTS
            (SELECT 1 FROM privacy WHERE id=m.id AND private=1)""").fetchall()
        target=next((r for r in rows if r['id']==chat),None)
        if not target or target['project']:
            return None
        def terms(r):
            return words(r['title']+' '+json.loads(r['summary'])['overview'])
        topic=terms(target)
        best=None
        score=0
        for p in db.execute("SELECT id,name FROM projects ORDER BY name,id"):
            candidates=[words(p['name'])]+[terms(r) for r in rows if r['project']==p['id']]
            overlap=max(len(topic & t)/max(1,len(topic|t)) for t in candidates)
            if overlap>score:
                best,score=dict(p),overlap
        return best


def change(store, data):
    action=data.get("action")
    pid=data.get("project_id")
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if action in ("create","rename"):
            name=data.get("name")
            if not isinstance(name,str) or not 0<len(name.strip())<=120:
                raise ValueError("Enter a project name of up to 120 characters.")
            name=mask(name.strip())
        if action=="create":
            pid=uuid4().hex
            db.execute("INSERT INTO projects(id,name) VALUES (?,?)",(pid,name))
        elif action=="assign":
            chat=data.get("chat")
            if not db.execute("SELECT 1 FROM memories WHERE id=?",(chat,)).fetchone():
                raise ValueError("Conversation unavailable.")
            if pid:
                require_project(db,pid)
            db.execute("DELETE FROM memberships WHERE chat=?",(chat,))
            if pid:
                db.execute("INSERT INTO memberships VALUES (?,?)",(chat,pid))
        else:
            require_project(db,pid)
            if action=="rename":
                db.execute("UPDATE projects SET name=? WHERE id=?",(name,pid))
            elif action=="delete":
                db.execute("DELETE FROM projects WHERE id=?",(pid,))
            else:
                raise ValueError("Unknown project change.")
    return {"project_id":pid}
