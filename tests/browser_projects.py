"""Playwright/Edge exercise of project review in an isolated Orbit library."""
import sys
import tempfile
from pathlib import Path
from threading import Thread
from uuid import uuid4
from http.server import ThreadingHTTPServer

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import OrbitHandler
from orbit_accounts import Accounts


def run():
    with tempfile.TemporaryDirectory() as root, ThreadingHTTPServer(("127.0.0.1",0),OrbitHandler) as server:
        accounts=server.accounts=Accounts(root)
        uid=str(uuid4())
        cookie=accounts.issue(dict(id=uid,email="project@example.test"))
        store=accounts.store(uid)
        store.save(dict(title="Atlas plan",transcript="Goal: build an atlas. We chose SQLite because it works offline."))
        Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel="msedge")
                context=browser.new_context()
                page=context.new_page()
                url=f"http://127.0.0.1:{server.server_port}"
                page.context.add_cookies([dict(name="orbit_session",value=cookie,url=url)])
                page.goto(url)
                page.locator('[data-nav="projects"]').click()
                page.once("dialog",lambda d:d.accept("Atlas"))
                page.locator("#newProject").click()
                page.locator('[data-nav="library"]').click()
                page.get_by_role("button",name="Open Atlas plan").click()
                page.get_by_role("button",name="Assign to Atlas").click()
                box=page.locator("#projectBrief")
                expect(box.locator("article")).to_have_count(2)
                while box.locator('[data-action="accept"]').count():
                    box.locator('[data-action="accept"]').first.click()
                    page.wait_for_timeout(100)
                box.get_by_text("Mark reviewed").click()
                expect(box.locator("h3")).to_have_text("Project brief · reviewed")
                with page.expect_download() as export:
                    box.locator("#projectExport").click()
                packet=export.value.path().read_text()
                assert "because it works offline" in packet and "/#memory/" in packet
                source=page.context.new_page()
                source.goto(url+"/#memory/"+store.list()[0]["id"])
                expect(source.locator("#modal h2")).to_have_text("Atlas plan")
                source.close()
                page.locator('[data-close]').click()
                page.locator('[data-nav="universe"]').click()
                page.get_by_role("button",name="Atlas",exact=True).click(timeout=3000)
                expect(box.locator("h3")).to_have_text("Project brief · reviewed")
                box.locator("[data-open]").first.click()
                expect(page.locator("#modal h2")).to_have_text("Atlas plan")
                print("PASS project creation, suggestion approval, per-line review, brief export, orbital star and source navigation")
                browser.close()
        finally:
            server.shutdown()


if __name__=="__main__":
    run()


