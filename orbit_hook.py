"""Save the visible text of the session supplied by a trusted agent's lifecycle hook."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

from memory import compact, library_directory
from orbit_accounts import Accounts, agent_key

PROVIDERS = {"claude":"Claude Code","codex":"Codex","gemini":"Gemini CLI","qwen":"Qwen Code"}


def text_parts(value):
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        return ""
    pieces = []
    for block in value:
        if isinstance(block, str):
            pieces.append(block)
        elif isinstance(block, dict) and block.get("type") in (None, "text", "input_text", "output_text"):
            if not block.get("thought") and isinstance(block.get("text"), str):
                pieces.append(block["text"])
    return "\n".join(pieces)


def load_records(path):
    with path.open(encoding="utf-8-sig") as stream:
        if path.suffix.lower() == ".json":
            data = json.load(stream)
            return data.get("messages", []) if isinstance(data, dict) else data
        return [json.loads(line) for line in stream if line.strip()]


def gemini_records(rows):
    messages = {}
    for idx, row in enumerate(rows):
        if "$patch" in row:
            patch = row["$patch"]
            for update in [patch, *patch.get("updates", [])]:
                key = update.get("id")
                if key in messages and "content" in update:
                    messages[key]["content"] = update["content"]
            for key in patch.get("removeIds", []):
                messages.pop(key, None)
            for key in patch.get("orderIds", []):
                if key in messages:
                    messages[key] = messages.pop(key)
        elif "messages" in row.get("$set", {}):
            messages = {m["id"]:m for m in row["$set"]["messages"]}
        elif row.get("type") in ("user","gemini","assistant"):
            messages[row.get("id",idx)] = row
    return messages.values()


def extract(host, rows):
    if host == "gemini":
        rows = gemini_records(rows)
    turns = []
    for row in rows:
        role = row.get("type")
        if host == "codex":
            # Public event messages exclude tool calls, injected context and private reasoning.
            if role != "event_msg":
                continue
            event = row.get("payload", {})
            role = {"user_message":"user", "agent_message":"assistant"}.get(event.get("type"))
            content = event.get("message")
        elif host == "gemini":
            role = "assistant" if role == "gemini" else role
            content = row.get("content")
        else:
            if row.get("isMeta") or row.get("isSidechain") or row.get("isCompactSummary"):
                continue
            if host == "qwen" and row.get("provenance") not in (None,"real_user","assistant_output"):
                continue
            message = row.get("message", {})
            if not isinstance(message, dict):
                continue
            content = message.get("content", message.get("parts"))
        if role in ("user", "assistant"):
            text = text_parts(content).strip()
            if text:
                turns.append((role,text))
    return turns


def capture(host, event, store):
    allowed = {"AfterAgent","SessionEnd"} if host == "gemini" else {"Stop","SessionEnd"}
    if event.get("hook_event_name") not in allowed or event.get("agent_id"):
        return
    session = event.get("session_id")
    path = event.get("transcript_path")
    if not isinstance(session, str) or not session or not path:
        raise ValueError("Host did not provide a session ID and transcript path.")
    path = Path(path)
    if not path.is_absolute() or not path.is_file():
        raise ValueError("Session transcript is unavailable.")
    if path.stat().st_size > 128_000_000:
        raise ValueError("Transcript file is too large to load automatically.")
    turns = extract(host, load_records(path))
    # Some clients flush the last message after their Stop hook has started.
    final = event.get("last_assistant_message") or event.get("prompt_response")
    if turns and isinstance(final,str) and final.strip() and turns[-1] != ("assistant",final.strip()):
        turns.append(("assistant",final.strip()))
    if not turns:
        return
    provider = PROVIDERS[host]
    title = compact(next((text for role,text in turns if role=="user"), turns[0][1]), 90)
    transcript = "\n\n".join(f"{'You' if role=='user' else provider}: {text}" for role,text in turns)
    store.save({"title":title,"provider":provider,"transcript":transcript}, conversation_id=session)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("host", choices=PROVIDERS)
    parser.add_argument("--key-file")
    args = parser.parse_args()
    try:
        event = json.loads(sys.stdin.buffer.read())
        store = Accounts(library_directory()).agent_store(agent_key(args.key_file), PROVIDERS[args.host].casefold(), event.get("session_id"))
        capture(args.host, event, store)
        print("{}")
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
        print("Orbit could not capture this turn: " + str(exc), file=sys.stderr)
        sys.exit(1)
