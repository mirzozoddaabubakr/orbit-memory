# Orbit — project history and current state

Updated 12 November 2026.

## The original idea

You wanted a shared memory for conversations with different AI models. A conversation started in Claude should remain available when you move to ChatGPT, Gemini, Qwen, or another assistant. You should be able to find previous work and explain it to the next assistant without reconstructing the project yourself.

The interface you proposed was a solar system. Conversations would appear as selectable celestial objects. Opening one would reveal the conversation and an explanation of its purpose, decisions, and progress.

Orbit's core workflow is capture a conversation, preserve its text, find it later, and hand its context to another assistant. The source model is a label. A newly saved source should appear without requiring a fixed list of model names.

## What happened, in order

### 1. The first local application

We started in an empty Windows workspace and built a Python service and browser interface. The service runs at http://127.0.0.1:47831.

The interface includes an orbital map, a conversation library, search, starred memories, and a reader with Summary, Conversation, and Handoff tabs. The map uses projected orbital geometry and shaded sphere textures drawn on a canvas. It supports pointer rotation, zoom, and selecting a conversation.

SQLite stores conversation text, source, title, dates, summaries, stars, and previous captured versions. Repeated captures update the same source conversation. A shorter partial capture is prevented from replacing a longer saved transcript. Edited versions are retained when they differ.

We also added paste and file imports. Supported inputs include text, Markdown, Claude conversation JSON, ChatGPT conversation JSON, and generic conversation objects. ChatGPT imports preserve the active branch and readable alternate messages.

### 2. Capturing browser chats

We created a Chrome and Edge extension with site-specific capture adapters for Claude, ChatGPT, Gemini, and Qwen. Users pair it with Orbit and explicitly enable sites.

It reads rendered user and assistant messages. It excludes interface buttons, hidden elements, and private reasoning fields where available. Code text is preserved. It retries pending captures when the local service becomes available.

For other sites, it supports selected-text capture and configurable user/assistant message selectors. That gives an integration path for additional models.

This capture depends on the site exposing conversation text. Unopened conversations, messages that were never loaded, and attachment binaries require a separate import or another integration. Changes to a provider's page can require an adapter update.

### 3. Summaries and handoffs

Orbit creates an excerpt-based brief without requiring a model API. It extracts an overview, details, decisions, and possible next steps. These are source excerpts and can require interpretation.

We added optional synthesis through a downloaded local Ollama model. The app can discover installed local models and request a structured brief. The original transcript remains stored separately.

A copied or downloaded handoff includes the brief and full saved transcript. Earlier saved variants are included when available. Long inputs can exceed another assistant's context window, so the receiving model may need to retrieve them in pages.

### 4. MCP and agent integrations

You requested an MCP server so agents could connect directly.

We added four tools.

- orbit_save_conversation saves a full conversation snapshot.
- orbit_append_turn saves one user/assistant exchange with a stable turn ID.
- orbit_search_memories finds saved conversations.
- orbit_read_memory returns the brief and transcript, with pagination and earlier versions.

Turn IDs make repeat submissions safe. A saved conversation is identified by its provider and stable conversation ID.

We added turn-end hook adapters for Claude Code, Codex, Gemini CLI, and Qwen Code. These consume the session transcript supplied by the host. The integration generator builds client configurations and an installable Claude Desktop MCP bundle.

Claude Code connected to the plugin. A controlled local test of the real Claude Code process verified automatic turn-end capture. Other hook formats were checked using transcript fixtures. Separate MCP processes were tested for discovery, saving, retries, search, and paged retrieval.

A standard MCP connection exposes tools. Automatic saving still depends on a host hook, a host callback, or the model calling the save tool. A skill file supplies guidance.

### 5. Your interface corrections

The first version showed six fictional example chats and a permanent list of four providers. You asked to remove those and simplify the product.

We removed the examples. The sidebar now shows only providers with saved conversations, including arbitrary model names. An empty library has one Add memory action and a solar illustration. Connection instructions collapse until opened.

You also asked for a clearer MCP entry and GitHub skill access.

### 6. Registration and Supabase

You clarified that other people would use Orbit and requested registration.

We initially explored a separate free Supabase project. A free Orbit organization was created under the first account, but that account had reached its free project limit. You temporarily selected device-local accounts while we built account separation.

You then asked to switch accounts and delete the empty organization. You deleted it, and we verified it was gone. You signed into another account and created a new Orbit organization and Supabase project.

We connected the app's email sign-up and password sign-in to that project using its publishable key. Supabase verifies the identity, then Orbit creates a local browser session. Memories and pairing credentials are stored separately for each account ID.

The browser extension is paired to an account. Pending captures retain their original account binding. Agent configurations also carry an account pairing reference. A chat already bound to one account cannot be silently reassigned by reusing the same agent conversation ID.

Google OAuth has not been configured. Registration email delivery and the complete confirmation flow need live verification. Password reset and account deletion flows remain to be built.

The account is online, while conversation storage remains on the device. Signing in on another machine does not currently sync the first machine's library.

### 7. GitHub and reusable skills

You requested the project in GitHub. We initialized a Git repository, committed the application, and pushed orbit-memory to your account as a private repository.

Account configuration, local databases, pairing keys, generated machine-specific integrations, and the Python environment are excluded from Git. The public repository supplies an example auth configuration.

On 12 November, you authorized making the repository public and requested additional work and this history.

We added a dedicated MCP & Skills navigation entry. It offers GitHub links and downloads for two skills.

- orbit-memory explains saving and recalling conversations.
- orbit-handoff explains preparing an evidence-based project handoff.

The generator now includes both skills in its Claude Code, Gemini CLI, and Codex plugin outputs. Existing installed integrations need regeneration or refresh to receive the added files.

## What exists now

The source includes the local application, account sign-in, imports, browser extension, SQLite storage, orbital map, source-filtered library, search, stars, transcript history, handoff export, optional local AI briefs, MCP server, agent hooks, integration generator, and agent skills.

The repository contains the implementation and setup instructions. Generated bundles must be built for the target computer. The application is served locally, and its extension is loaded as an unpacked extension.

## Verification and its limits

The storage and capture tests cover concurrent saves, retry behavior, version retention, authentication of extension requests, and supported transcript formats. Import tests cover text and Claude/ChatGPT structures. MCP integration tests launch actual server processes and test a save followed by retrieval from a different client, including the Desktop bundle.

Account isolation and logout were checked with controlled identities. These checks do not establish successful email delivery or Google OAuth.

The UI was visually reviewed through the browser during development. Provider capture fixtures do not prove that every current live provider page works. The hook that was exercised through the actual host was Claude Code.

## What remains before a wider launch

1. Complete and verify registration, confirmation links, password recovery, Google sign-in, logout, and integration disconnection.
2. Decide the distribution model. A desktop installation needs an installer, portable configuration, and a dependable update path. A hosted service needs deployment and remote integration design.
3. Implement user-owned cloud conversation storage if cross-device sync is desired. This needs database ownership policies, migrations, conflict handling, and isolation tests.
4. Verify browser adapters on current live sites and each supported agent's current release. Handle attachments and large histories explicitly.
5. Add backup and restore, account export/deletion, and clearer pairing management.
6. Improve semantic search, project grouping, relationships between chats, and summary quality after capture reliability is established.
7. Set public distribution terms and complete the relevant privacy documentation before inviting general users.

## Recommended next milestone

A first-time user should install Orbit on a fresh machine, create an account, pair one agent, save a real chat automatically, and retrieve that chat from a second agent. Verify that a second Orbit account cannot read it.

That is the next end-to-end completion condition. The longer-term idea remains the same shared memory across AI assistants, explored through a visual universe.
