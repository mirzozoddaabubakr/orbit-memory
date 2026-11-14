"""Run with Playwright and Edge; uses only disposable accounts and intercepted site pages."""
import json
import shutil
from contextlib import ExitStack
import sys
import tempfile
import threading
from pathlib import Path
from uuid import uuid4
from http.server import ThreadingHTTPServer

from playwright.sync_api import expect, sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server import OrbitHandler
from orbit_accounts import Accounts
from recall import HEADER

SITES={
    "chatgpt.com":'<div id="prompt-textarea" contenteditable="true"></div>',
    "claude.ai":'<div data-testid="chat-input" contenteditable="true"></div>',
    "gemini.google.com":'<rich-textarea><div contenteditable="true"></div></rich-textarea>',
    "chat.qwen.ai":'<textarea placeholder="Message"></textarea>'
}


def run(live_qwen=False):
    with tempfile.TemporaryDirectory() as data, tempfile.TemporaryDirectory() as profile:
        with ThreadingHTTPServer(("127.0.0.1",47831),OrbitHandler) as server, ExitStack() as cleanup:
            server.accounts=Accounts(data)
            threading.Thread(target=server.serve_forever,daemon=True).start()
            cleanup.callback(server.shutdown)
            owner=str(uuid4())
            store=server.accounts.store(owner)
            secret="ghp_"+ "A"*36
            mid=store.save(dict(title="Application sketch",transcript="Historical first line\nSecond line "+secret))
            store.save(dict(title="Application notes",transcript="Discard this item"))
            # Pre-grant only the four fixture origins in a disposable manifest.
            folder=Path(data)/"extension"
            shutil.copytree(ROOT/"extension",folder)
            manifest=folder/"manifest.json"
            config=json.loads(manifest.read_text())
            hosts=["https://"+host+"/*" for host in SITES]
            config["host_permissions"]+=hosts
            config["content_scripts"].append({"matches":hosts,"js":["composer.js","recall-button.js"]})
            manifest.write_text(json.dumps(config))
            ext=str(folder)
            with sync_playwright() as pw:
                ctx=pw.chromium.launch_persistent_context(profile,channel="msedge",headless=True,
                        args=[f"--disable-extensions-except={ext}",f"--load-extension={ext}"])
                worker=ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker")
                worker.evaluate("key=>chrome.storage.local.set({key})",server.accounts.pairing_key(owner,"extension"))

                for host,html in SITES.items():
                    if live_qwen and host!="chat.qwen.ai":
                        continue
                    page=ctx.new_page()
                    if not live_qwen:
                        page.route("https://"+host+"/**",lambda r:r.fulfill(content_type="text/html",body=html))
                    page.goto("https://"+host+"/")
                    page.locator("textarea:visible,[contenteditable=true]:visible").first.fill("Application draft")
                    button=page.get_by_role("button",name="Load Orbit memory")
                    expect(button).to_be_visible()
                    def open_preview():
                        with ctx.expect_page() as opened:
                            button.click()
                        preview=opened.value
                        expect(preview.locator("#topic")).to_have_value("Application draft")
                        return preview
                    preview=open_preview()
                    preview.locator("#search").click()
                    expect(preview.locator("#items label")).to_have_count(2)
                    preview.get_by_label("Application notes").uncheck()
                    content=preview.locator("#preview").inner_text()
                    assert HEADER in content and "Discard" not in content and secret not in content
                    assert "Historical first line" not in page.locator("body").inner_text()
                    assert all(line.startswith("> ") for line in content.splitlines()[2:] if line)
                    store.review(mid,"private")
                    preview.locator("#copy").click()
                    expect(preview.locator("#status")).to_contain_text("Memory changed")
                    assert "Historical first line" not in preview.locator("#preview").inner_text()
                    store.review(mid,"shareable")
                    preview.locator("#search").click()
                    preview.get_by_label("Application notes").uncheck()
                    preview.locator("#copy").click()
                    expect(preview.locator("#status")).to_have_text("Copied.")
                    preview.locator("#cancel").click()
                    composer=page.locator("textarea:visible,[contenteditable=true]:visible").first
                    def draft():
                        return composer.evaluate("e=>e.value??e.innerText")
                    assert draft()=="Application draft"
                    preview=open_preview()
                    preview.locator("#search").click()
                    preview.get_by_label("Application notes").uncheck()
                    if host=="chat.qwen.ai":
                        preview.locator("#insert").click()
                        expect(composer).to_have_value("Application draft\n\n"+content)
                        outcome="confirmed insertion"
                    else:
                        expect(preview.locator("#insert")).to_be_hidden()
                        preview.locator("#cancel").click()
                        assert draft()=="Application draft"
                        outcome="copy only"
                    page.close()
                    print("PASS",host,"live" if live_qwen else "fixture","placement, isolated preview, privacy recheck, copy, cancel;",outcome)
                ctx.close()



if __name__=="__main__":
    run("--live-qwen" in sys.argv)
