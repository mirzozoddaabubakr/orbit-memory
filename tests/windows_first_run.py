"""Windows smoke test driver. Use a disposable clean checkout and empty ORBIT_DATA_DIR.
Run with a Python environment containing Playwright. The checkout's setup must be running.
"""
import argparse
import json
import os
import secrets
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

BASE = "http://127.0.0.1:47831"
TEXT = "We chose elliptical orbits for the first scene."
CLIENT = """
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run():
    entry = json.load(sys.stdin)["mcpServers"]["orbit"]
    entry["env"] = {**os.environ, **entry["env"]}
    async with stdio_client(StdioServerParameters(**entry)) as streams, ClientSession(*streams) as client:
        await client.initialize()
        found = await client.call_tool("orbit_search_memories", {"query":"elliptical"})
        mid = found.structuredContent["memories"][0]["id"]
        read = await client.call_tool("orbit_read_memory", {"memory_id":mid})
        assert read.structuredContent["transcript"] == sys.argv[1]
asyncio.run(run())
"""


def run(root):
    assert not (root / "orbit-auth.json").exists()
    with urlopen(BASE + "/api/session") as response:
        assert json.load(response)["user"] is None
    with TemporaryDirectory() as profile, sync_playwright() as pw:
        extension = root / "extension"
        ctx = pw.chromium.launch_persistent_context(profile, channel="msedge", headless=True,
            args=[f"--disable-extensions-except={extension}", f"--load-extension={extension}"])
        page = ctx.new_page()
        page.goto(BASE)
        page.locator("#authSwitch").click()
        page.locator("#email").fill("trial-"+secrets.token_hex(6)+"@example.test")
        page.locator("#password").fill(secrets.token_urlsafe(20))
        page.locator("#authSubmit").click()
        checklist = page.locator("#checklist")
        expect(checklist.locator("li").nth(0)).to_contain_text("Done")
        expect(checklist.locator("li").nth(1)).to_contain_text("Done",timeout=12000)
        print("PASS account created and unpacked extension detected", flush=True)
        for index in (2,3,4):
            expect(checklist.locator("li").nth(index)).to_contain_text("Not done")
        page.locator('[data-nav="sources"]').click()
        page.locator(".setup-row summary").click()
        ctx.grant_permissions(["clipboard-read","clipboard-write"], origin=BASE)
        page.locator("#pairKey").click()
        expect(page.locator("#toast")).to_have_text("Pairing code copied")
        code = page.evaluate("navigator.clipboard.readText()")
        worker = ctx.service_workers[0]
        popup = ctx.new_page()
        popup.goto(worker.url.rsplit("/",1)[0]+"/popup.html")
        popup.locator("#key").fill(code)
        popup.locator("#saveKey").click()
        expect(popup.locator("#actions")).to_be_visible()
        popup.close()
        expect(checklist.locator("li").nth(2)).to_contain_text("Done",timeout=12000)
        print("PASS extension paired from its popup", flush=True)
        page.locator("#add").click()
        page.locator("#provider").fill("Example")
        page.locator("#title").fill("Orbit trial")
        page.locator("#transcript").fill(TEXT)
        page.locator("#importForm button[type=submit]").click()
        page.reload()
        page.locator('[data-nav="library"]').click()
        page.get_by_role("button",name="Open Orbit trial",exact=True).click()
        page.locator('[data-tab="transcript"]').click()
        expect(page.locator(".reader pre").first).to_have_text(TEXT)
        print("PASS chat saved and retrieved after reload", flush=True)
        page.keyboard.press("Escape")
        page.locator('[data-nav="agents"]').click()
        page.locator(".setup-row summary").click()
        page.locator("#agentChoice").select_option(label="Other local MCP client")
        config = page.locator(".agent-config").inner_text()
        subprocess.run([root/".orbit-mcp/Scripts/python.exe","-c",CLIENT,TEXT],
                       input=config,text=True,check=True)
        expect(checklist.locator("summary")).to_contain_text("5 / 5",timeout=15000)
        print("PASS MCP search and read; checklist 5 / 5", flush=True)
        ctx.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout",type=Path)
    args = parser.parse_args()
    start = monotonic()
    run(args.checkout.resolve())
    print(f"Browser and agent journey: {monotonic()-start:.1f}s")

