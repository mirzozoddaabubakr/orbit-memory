# Orbit

Orbit saves AI conversations in a private library on your computer. Select a planet to read its conversation, search by a phrase, or copy a handoff with the brief and full saved text.

## Start on Windows

For a new checkout, install Python 3.12, then run the following from the repository folder.

```powershell
python -m venv .orbit-mcp
.\.orbit-mcp\Scripts\python.exe -m pip install -r requirements-mcp.txt
Copy-Item orbit-auth.example.json orbit-auth.json
```

Set your Supabase project URL and publishable key in `orbit-auth.json`, then run
`python agent_connections.py` to build the client packages for your computer.
Sign up or sign in when Orbit opens. Accounts use Supabase authentication and have
separate libraries stored on the device.

The reusable agent skill is [skills/orbit-memory/SKILL.md](skills/orbit-memory/SKILL.md).
Install it in your agent's skills directory and connect the MCP server from Orbit Sources.
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

Open **Sources → Connect an AI agent** for the setup that matches your app. Claude Code, Codex, Gemini CLI, and Qwen Code have turn-end hooks that save visible chat text into this same library. Start a new session after enabling the integration and accepting any hook trust prompt. The local library works even with the Orbit browser window closed.

For a quick Claude Code session, double-click **Claude with Orbit.cmd**. For a persistent installation, use the two Claude Code commands shown in Sources. Claude Desktop users can install **agent-connections/Orbit Memory.mcpb**. Other local clients can use **agent-connections/orbit-mcp.json**. These desktop configurations target this computer. Hosted web clients that require a remote HTTPS connector cannot launch this local server.

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
