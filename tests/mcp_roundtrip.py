"""Run with .orbit-mcp's Python. Exercise the actual MCP client/server boundary."""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def run():
    with tempfile.TemporaryDirectory() as tmp:
        sys.path.insert(0,str(ROOT))
        from orbit_accounts import Accounts
        from uuid import uuid4
        accounts=Accounts(tmp)
        key=accounts.pairing_key(str(uuid4()),"agent")
        params = StdioServerParameters(command=sys.executable,args=[str(ROOT/"orbit_mcp.py")],
                    cwd=tmp,env={**os.environ,"ORBIT_DATA_DIR":tmp,"PYTHONUTF8":"1","ORBIT_AGENT_KEY":key})
        fake_key = "sk-proj-" + "F"*36
        text = "We chose ellipses. Next, test 轨道. " + fake_key
        async with stdio_client(params) as (reader,writer), ClientSession(reader,writer) as client:
            await client.initialize()
            assert len((await client.list_tools()).tools)==4
            saved = await client.call_tool("orbit_save_conversation", {"provider":"Claude","conversation_id":"orbit-1",
                                          "title":"Planets","transcript":text})
            assert not saved.isError
            mid = saved.structuredContent["memory_id"]
            args={"provider":"Claude","conversation_id":"orbit-1","title":"Planets","turn_id":"two",
                  "user_text":"What next?","assistant_text":"Try tilt."}
            for _ in range(2):
                reply=await client.call_tool("orbit_append_turn",args)
                assert reply.structuredContent["memory_id"]==mid
        # Launch the actual Desktop bundle as a different host reading the same test library.
        with ZipFile(ROOT/"agent-connections/Orbit Memory.mcpb") as archive:
            extracted=Path(tmp)/"desktop"
            archive.extractall(extracted)
            entry=json.loads(archive.read("manifest.json"))["server"]["mcp_config"]
        command_args=[a.replace("${__dirname}",str(extracted)) for a in entry["args"]]
        params=StdioServerParameters(command=entry["command"],args=command_args,cwd=tmp,
                  env={**os.environ,"ORBIT_DATA_DIR":tmp,"PYTHONUTF8":"1","ORBIT_AGENT_KEY":key,"PYTHONNOUSERSITE":"1",
                       "PYTHONPATH":str(extracted/"server/lib")})
        async with stdio_client(params) as (reader,writer), ClientSession(reader,writer) as client:
            await client.initialize()
            r=await client.call_tool("orbit_search_memories",{"query":"轨道"})
            assert [row["id"] for row in r.structuredContent["memories"]]==[mid]
            offset,parts=0,[]
            while offset is not None:
                r=await client.call_tool("orbit_read_memory",{"memory_id":mid,"limit":17,"offset":offset})
                assert not r.isError
                parts.append(r.structuredContent["transcript"])
                offset=r.structuredContent["next_offset"]
            assert fake_key not in "".join(parts)
            assert "".join(parts)==text.replace(fake_key,"<redacted:OpenAI-key>")+"\n\nYou: What next?\n\nClaude: Try tilt."
            owner=accounts.paired_owner(key,"agent")
            accounts.store(owner).review(mid,"private")
            hidden=await client.call_tool("orbit_search_memories",{"query":"轨道"})
            assert hidden.structuredContent["memories"]==[]
            forbidden=await client.call_tool("orbit_read_memory",{"memory_id":mid})
            assert forbidden.isError
            bad=await client.call_tool("orbit_read_memory",{"memory_id":mid,"limit":0})
            assert bad.isError
    print("Verified MCP discovery, save, idempotent append, cross-client search, paged handoff and Desktop bundle; fake key redacted and private memory excluded across MCP processes.")


if __name__=="__main__":
    asyncio.run(run())
