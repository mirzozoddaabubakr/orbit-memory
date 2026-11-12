---
name: orbit-handoff
description: Prepare a project handoff from saved Orbit conversations when the user wants to continue work with another AI model or explain what was built.
---

# Orbit project handoff

Use the connected Orbit MCP tools to search for the project and read relevant memories.
Follow every next_offset needed to retrieve the relevant conversation text. Check earlier
versions when the current conversation omits a decision the user remembers.

Prepare a handoff with the following information, when the records support it.

- The user's goal and expected result.
- What is implemented and what has been verified.
- Decisions, requirements, exact file paths and commands relevant to continuing.
- Current failures, missing credentials, and external setup dependencies.
- The next action and any user decision required before it.

Include the source memory IDs so the receiving agent can retrieve the evidence.
Distinguish user requirements from suggestions and planned work. If a status is uncertain,
state that uncertainty. Never manufacture a completed test, deployment, or connection.

Preserve the full transcript through Orbit or a separate export when the user requests it.
Explain when a handoff covers only the memories that were retrieved.
