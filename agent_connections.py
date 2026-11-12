"""Prepare local client configurations and an installable Claude Desktop extension."""
import json
import os
import re
import sys
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "agent-connections"
VENV = ROOT / ".orbit-mcp"
PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
ENTRY = {"command":str(PYTHON),"args":[str(ROOT / "orbit_mcp.py")],"env":{"PYTHONUTF8":"1"}}
SERVERS = {"mcpServers":{"orbit":ENTRY}}
PLUGIN = {"name":"orbit-memory", "version":"1.0.0", "description":"Save conversations on this device and recall them across agents."}


def bundle_skills(destination):
    for skill in ("orbit-memory","orbit-handoff"):
        target=destination/"skills"/skill
        target.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/"skills"/skill/"SKILL.md",target/"SKILL.md")


def hooks(agent, key_file=None):
    # Forward slashes are accepted on Windows by the host's shell and by Python.
    executable = PYTHON.as_posix()
    if not re.fullmatch(r"[\w./:-]+",executable):
        executable = "python" if os.name == "nt" else "python3"
    command = f'{executable} "{(ROOT / "orbit_hook.py").as_posix()}" {agent}'
    if key_file:
        command += f' --key-file "{key_file.as_posix()}"'
    event = "AfterAgent" if agent == "gemini" else "Stop"
    return {"hooks":{event:[{"hooks":[{"type":"command","command":command}]}]}}


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def configurations(profile=None):
    out=OUT
    servers=SERVERS
    key_file=None
    if profile:
        out=profile/"integrations"
        key_file=profile/"agent.key"
        entry={**ENTRY,"env":{**ENTRY["env"],"ORBIT_AGENT_KEY_FILE":str(key_file)}}
        servers={"mcpServers":{"orbit":entry}}
        # Install paths identify one account. A later browser login cannot retarget a plugin.
        for rel in (".claude-plugin/marketplace.json","claude-code/.claude-plugin/plugin.json"):
            write_json(out/rel,json.loads((OUT/rel).read_text(encoding="utf-8")))
        write_json(out/"claude-code/.mcp.json",servers)
        write_json(out/"claude-code/hooks/hooks.json",hooks("claude",key_file))
        write_json(out/"gemini-cli/gemini-extension.json",{**PLUGIN,**servers})
        write_json(out/"gemini-cli/hooks/hooks.json",hooks("gemini",key_file))
        codex=out/"plugins/orbit-memory"
        for rel in ("plugins/orbit-memory/plugin.json",".agents/plugins/marketplace.json"):
            write_json(out/rel,json.loads((ROOT/rel).read_text(encoding="utf-8")))
        write_json(codex/"mcp.json",{"mcpServers":{"orbit":{"type":"stdio",**entry}}})
        write_json(codex/"hooks/hooks.json",hooks("codex",key_file))
        for plugin in (out/"claude-code",out/"gemini-cli",codex):
            bundle_skills(plugin)
    return {
        "Claude Code":{"help":"Run these two commands one at a time inside Claude Code, then reload plugins or start a new session. Orbit will save the visible conversation after each reply.",
                       "value":f'/plugin marketplace add "{out.as_posix()}"\n/plugin install orbit-memory@orbit-local'},
        "Claude Desktop":{"help":"Install the desktop extension and enter your agent pairing code. Ask Claude to save a conversation or recall a memory.",
                          "download":"/api/orbit-memory.mcpb"},
        "Codex":{"help":"Open this folder as a Codex project and install Orbit Memory from its local marketplace. Trust the Stop hook for automatic capture.","value":str(out)},
        "Gemini CLI":{"help":"Run this in a terminal, review the extension and start a new Gemini CLI session. Orbit saves each completed exchange.",
                      "value":f'gemini extensions link "{out / "gemini-cli"}"'},
        "Qwen Code":{"help":"Merge these mcpServers and hooks entries into your Qwen Code settings.json, preserving your existing entries. Restart Qwen Code and review the hook if prompted.",
                     "value":json.dumps({**servers,**hooks("qwen",key_file)},indent=2)},
        "Other local MCP client":{"help":"Add this server to the client’s MCP configuration. Ask the agent to save each exchange using orbit_append_turn. A client with a turn-end callback can call that tool directly for reliable automatic capture.",
                                  "value":json.dumps(servers,indent=2)}
    }


def prepare():
    if not PYTHON.exists():
        raise SystemExit("Create .orbit-mcp and install requirements-mcp.txt first.")
    write_json(OUT/"orbit-mcp.json",SERVERS)
    claude = OUT/"claude-code"
    write_json(OUT/".claude-plugin/marketplace.json",{"name":"orbit-local","owner":{"name":"Orbit Memory"},
               "plugins":[{"name":"orbit-memory","source":"./claude-code","description":PLUGIN["description"]}]})
    write_json(claude/".claude-plugin/plugin.json",{**PLUGIN,"author":{"name":"Orbit Memory"}})
    write_json(claude/".mcp.json",SERVERS)
    write_json(claude/"hooks/hooks.json",hooks("claude"))
    gemini = OUT/"gemini-cli"
    write_json(gemini/"gemini-extension.json",{**PLUGIN,**SERVERS})
    write_json(gemini/"hooks/hooks.json",hooks("gemini"))
    write_json(OUT/"qwen-settings.json",{**SERVERS,**hooks("qwen")})
    codex = ROOT/"plugins/orbit-memory"
    write_json(codex/"plugin.json",{"$schema":"https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",**PLUGIN,
               "extensions":{"com.openai":{"hooks":"./hooks/hooks.json","interface":{"displayName":"Orbit Memory"}}}})
    write_json(codex/"mcp.json",{"$schema":"https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
               "mcpServers":{"orbit":{"type":"stdio",**ENTRY}}})
    write_json(codex/"hooks/hooks.json",hooks("codex"))
    for plugin in (claude,gemini,codex):
        bundle_skills(plugin)
    write_json(ROOT/".agents/plugins/marketplace.json",{"name":"orbit-local","plugins":[{"name":"orbit-memory",
               "source":{"source":"local","path":"./plugins/orbit-memory"},"category":"Productivity",
               "policy":{"installation":"AVAILABLE","authentication":"ON_INSTALL"}}]})
    # Bundle this runtime's libraries so Desktop can launch without installing packages at startup.
    lib = VENV/"Lib/site-packages" if os.name=="nt" else next((VENV/"lib").glob("python*/site-packages"))
    manifest={"manifest_version":"0.3","name":"orbit-memory","display_name":"Orbit Memory","version":"1.0.0",
              "description":"Save, search and read conversations in the Orbit library on this computer.",
              "author":{"name":"Orbit Memory"},"tools_generated":True,
              "user_config":{"pairing_key":{"type":"string","title":"Orbit agent pairing code","description":"Copy from Orbit Sources after signing in.","sensitive":True,"required":True}},
              "compatibility":{"platforms":["win32" if os.name=="nt" else sys.platform],
                               "runtimes":{"python":f">={sys.version_info.major}.{sys.version_info.minor},<{sys.version_info.major}.{sys.version_info.minor+1}"}},
              "server":{"type":"python","entry_point":"server/start.py","mcp_config":{
                  "command":sys.executable,"args":["${__dirname}/server/start.py"],
                  "env":{"PYTHONPATH":"${__dirname}/server/lib","PYTHONUTF8":"1","ORBIT_AGENT_KEY":"${user_config.pairing_key}"}}}}
    bundle=OUT/"Orbit Memory.mcpb"
    temp=bundle.with_suffix(".tmp")
    with ZipFile(temp,"w",ZIP_DEFLATED) as z:
        z.writestr("manifest.json",json.dumps(manifest,indent=2))
        z.writestr("server/start.py", "from pathlib import Path\nimport site\n"
                   "site.addsitedir(str(Path(__file__).parent / 'lib'))\n"
                   "from orbit_mcp import server\nserver.run(transport='stdio')\n")
        for name in ("orbit_mcp.py","memory.py","orbit_accounts.py","redaction.py","extension/secret-patterns.json"):
            z.write(ROOT/name,"server/"+name)
        for path in sorted(lib.rglob("*")):
            rel=path.relative_to(lib)
            if path.is_file() and "__pycache__" not in rel.parts and not rel.parts[0].startswith(("pip-","pip.","pip/")) and rel.parts[0]!="pip":
                z.write(path,"server/lib/"+rel.as_posix())
    temp.replace(bundle)


if __name__ == "__main__":
    prepare()
