# Orbit

Orbit saves AI conversations in a private library on your computer. Select a planet to read its conversation, search by a phrase, or copy a handoff with the brief and full saved text.

## Start on Windows

Download the repository ZIP from GitHub, extract it, and open PowerShell in the folder containing `setup.ps1`. Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
```

Setup checks Python, installs Python 3.12 with Windows Package Manager if needed, prepares the environment and agent packages, and opens Orbit. Keep PowerShell open. You can also double-click **Setup Orbit.cmd**.

Choose **Create an account**. On a fresh install the account and chats stay on this device. Use a password of at least 12 characters. To try your first chat, choose **Add memory**, paste a conversation, save it and open it from **Memory library**. Follow **Sources** to capture from the browser and **MCP & Skills** to connect an agent.

### macOS and Linux

Install Python 3.10 or newer with venv and pip. From the extracted repository run:

```sh
python3 -m venv .orbit-mcp &&
.orbit-mcp/bin/python -m pip install -r requirements-mcp.txt &&
python3 agent_connections.py &&
.orbit-mcp/bin/python server.py --open
```

Existing installations with an `orbit-auth.json` configuration continue using their Supabase email accounts. Device accounts are separate. Google sign-in is unavailable.

The agent skills are [Memory](skills/orbit-memory/SKILL.md) and
[Project handoff](skills/orbit-handoff/SKILL.md). Open **MCP & Skills** in Orbit to
download either skill or copy the connection setup. Generated Claude Code, Gemini CLI,
and Codex integrations include both skills. Refresh an older plugin to pick up changes.
Generated client packages, pairing credentials, and local memory databases are excluded from Git.

Double-click **Open Orbit.cmd**. The library opens at http://127.0.0.1:47831. The launcher uses the Python 3 installation on this computer. Closing the browser tab leaves the capture service running. After restarting Windows, open the launcher again.

Each saved conversation adds a planet to your map. A source appears in the sidebar when it has a saved conversation.

## Save a conversation

- **Paste or import.** Select **Add memory**, enter the AI source, and paste the text or choose a file. Supported formats include plain text, Markdown, ChatGPT conversation JSON, Claude conversation JSON, and JSON objects with a title, provider, and transcript. Unzip account exports first.
- **Capture as you chat.** Follow **Sources** in the app to load the included extension in Chrome or Edge, pair it, and enable each site you want to capture. Built-in adapters cover Claude, ChatGPT, Gemini, and Qwen. Capture reads rendered text in conversations you visit. Open older chats and scroll through lazy-loaded messages, or import an export. The extension retries locally queued captures when the service is available.
- **Other models.** Enter any model name when importing. The extension can save selected text on other websites. To enable automatic capture for another HTTPS site, open a conversation with its own URL path and use **Configure another AI site**. Provide CSS selectors identifying complete user and assistant message elements. Each site receives its own browser permission.
- **Pause capture.** Open the extension on the site and select **Pause capture**. Saved memories remain in Orbit. To remove a saved chat, open it and use the delete button. Pause capture before deleting a conversation that is still open on its source site.

## Continue with a different AI

### Connect through MCP

Open **MCP & Skills → MCP connection** for the setup that matches your app. Claude Code, Codex, Gemini CLI, and Qwen Code have turn-end hooks that save visible chat text into this same library. Start a new session after enabling the integration and accepting any hook trust prompt. The local library works even with the Orbit browser window closed.

Use the account-specific configuration shown in **MCP & Skills**. Claude Desktop users
can download the desktop extension and enter their agent pairing code. Other local
clients can copy the MCP configuration shown for their signed-in account. The generic
generated configuration needs an explicit agent pairing key. Hosted web clients that
require a remote HTTPS connector cannot launch this local server.

The four MCP tools are **orbit_save_conversation**, **orbit_append_turn**, **orbit_search_memories**, and **orbit_read_memory**. A host integrating Orbit directly can call the append tool after committing each exchange, passing its agent name, a stable conversation ID, a title, a unique turn ID, and both visible messages. Reusing that turn ID makes retries safe. Reading a long transcript returns a next offset for the following page. In an MCP-only client, a project instruction can request a save after each reply. Capture then depends on the client or model making that call.

The hooks read the current session transcript supplied by the host. They save visible user and assistant text and skip private reasoning, tool-call records and attachment files. Earlier unrelated chats require a separate import. Remove the plugin, or its Orbit hook and MCP entry, in the host to disconnect it. The MCP tools work with the memories that already exist in the library.

If the project moves, recreate the isolated Python environment with `python -m venv .orbit-mcp`, install `requirements-mcp.txt` using that environment’s Python, and run `python agent_connections.py` with the system Python. This rebuilds the machine-specific client packages. Configure clients again with the new paths. Run `.orbit-mcp\Scripts\python.exe tests\mcp_roundtrip.py` on Windows to verify a save and retrieval across two real MCP processes using a temporary library.

### Copy a handoff

Open a planet or memory card. **Summary** shows a brief assembled from source excerpts. **Conversation** shows the original saved text and earlier versions when available. **Copy handoff** and **Download** include the brief, transcript, and saved variants. Paste the result into your chosen model, or attach the downloaded Markdown if its input box is too small.

For a synthesized brief, start Ollama with a downloaded local chat model, then expand **Generate a brief with local AI** in a saved memory. Orbit talks to Ollama on this computer. The excerpt-based brief works without a model installation.

## Storage

The library and extension pairing key are stored in `%LOCALAPPDATA%\OrbitMemory\orbit.sqlite3`. Treat backups of this file as private. Browser capture saves text, including visible code. Images, attachment binaries, and messages a site never renders require separate handling. A provider layout change can require an adapter update. Paste, file import, and selected-text capture remain available.

## Verification

Run `python -m unittest discover -s tests -v` for storage, capture authentication, concurrent saves, version retention, and the local model response contract. Run `node --test tests/imports.test.mjs` for the file import cases.
 
## Security and license

Read [SECURITY.md](SECURITY.md) before sharing configuration, backups or transcripts.
Orbit is available under the [MIT License](LICENSE).
