#!/usr/bin/env python3
"""
agent.py — CLI for interacting with DO Gradient AI agents.

Usage:
    python agent.py list
    python agent.py info [-n <name>]
    python agent.py ask [-n <name>] [--json] <prompt>
"""

import argparse
import json
import os
import pathlib
import sys
import tempfile
from datetime import datetime, timezone

import requests

AGENTS_FILE = "agents.json"
IS_TTY = sys.stdout.isatty()
WARNED_MARKER = pathlib.Path.home() / ".config" / "doagent" / ".warned"
SESSIONS_DIR = pathlib.Path.home() / ".local" / "share" / "doagent" / "sessions"


def load_agents():
    if not os.path.exists(AGENTS_FILE):
        print(
            f"error: {AGENTS_FILE} not found — run provision.py create first",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(AGENTS_FILE) as f:
        return json.load(f)


def resolve_agent(registry, name_arg):
    agents = registry.get("agents", {})
    if not agents:
        print(
            "error: agents.json contains no agents — run provision.py create",
            file=sys.stderr,
        )
        sys.exit(1)
    if name_arg is not None:
        if name_arg not in agents:
            print(
                f"error: agent '{name_arg}' not found in agents.json",
                file=sys.stderr,
            )
            sys.exit(1)
        return name_arg, agents[name_arg]
    if len(agents) == 1:
        name = next(iter(agents))
        return name, agents[name]
    print(
        f"error: multiple agents in registry — specify one with -n <name>. "
        f"Known agents: {', '.join(agents.keys())}",
        file=sys.stderr,
    )
    sys.exit(1)


def maybe_warn_egress():
    if WARNED_MARKER.exists():
        return
    print(
        "warning: prompt content will leave this machine and be processed by a remote AI "
        "service (DigitalOcean Gradient AI). This warning will not appear again.",
        file=sys.stderr,
    )
    WARNED_MARKER.parent.mkdir(parents=True, exist_ok=True)
    WARNED_MARKER.touch()


def load_session(name, current_agent):
    """Load a named session. Returns (path, messages, created_iso)."""
    path = SESSIONS_DIR / f"{name}.json"
    if not path.exists():
        SESSIONS_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        return path, [], datetime.now(timezone.utc).isoformat()
    with path.open() as f:
        data = json.load(f)
    if data.get("agent") != current_agent:
        print(
            f"warning: session '{name}' was created with agent '{data['agent']}', "
            f"now talking to '{current_agent}'",
            file=sys.stderr,
        )
    turns = len(data.get("messages", []))
    last = data.get("updated", "unknown")
    print(f"Resuming session '{name}' ({turns} turns, last: {last})", file=sys.stderr)
    return path, data.get("messages", []), data.get("created", datetime.now(timezone.utc).isoformat())


def save_session(session_path, agent_name, messages, created_iso):
    """Atomically write session JSON at 0600 permissions."""
    data = {
        "agent": agent_name,
        "created": created_iso,
        "updated": datetime.now(timezone.utc).isoformat(),
        "messages": messages,
    }
    session_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmppath = tempfile.mkstemp(dir=str(session_path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.chmod(tmppath, 0o600)
        os.replace(tmppath, str(session_path))
    except Exception:
        try:
            os.unlink(tmppath)
        except OSError:
            pass
        raise


def cmd_sessions_list(args):
    """List all saved sessions."""
    if not SESSIONS_DIR.exists():
        print("No sessions found.")
        return
    sessions = sorted(SESSIONS_DIR.glob("*.json"))
    if not sessions:
        print("No sessions found.")
        return
    print(f"{'NAME':<20}  {'AGENT':<20}  {'TURNS':>5}  LAST UPDATED")
    for path in sessions:
        try:
            with path.open() as f:
                data = json.load(f)
            name = path.stem
            agent_name = data.get("agent", "?")
            turns = len(data.get("messages", []))
            updated = data.get("updated", "?")
            print(f"{name:<20}  {agent_name:<20}  {turns:>5}  {updated}")
        except (json.JSONDecodeError, OSError):
            print(f"{path.stem:<20}  (unreadable)")


def cmd_sessions_rm(args):
    """Delete a named session."""
    path = SESSIONS_DIR / f"{args.name}.json"
    if not path.exists():
        print(f"error: session '{args.name}' not found", file=sys.stderr)
        sys.exit(1)
    path.unlink()
    print(f"Deleted session '{args.name}'")


def stream_ask(url, api_key, messages, quiet=False):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {"messages": messages, "stream": True}
    resp = requests.post(
        f"{url}/api/v1/chat/completions",
        headers=headers,
        json=body,
        stream=True,
        timeout=120,
    )
    resp.raise_for_status()
    full_text = ""
    for raw_line in resp.iter_lines(chunk_size=1):
        if not raw_line:
            continue
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if not line.startswith("data: "):
            continue
        payload = line[len("data: "):]
        if payload.strip() == "[DONE]":
            break
        try:
            chunk = json.loads(payload)
        except json.JSONDecodeError:
            continue
        delta = chunk.get("choices", [{}])[0].get("delta", {})
        token = delta.get("content")
        if token:
            full_text += token
            if not quiet:
                sys.stdout.write(token)
                sys.stdout.flush()
    return full_text


def cmd_list(args):
    registry = load_agents()
    agents = registry.get("agents", {})
    header = f"{'NAME':<20}  {'MODEL_UUID':<38}  ENDPOINT"
    print(header)
    for name, agent in agents.items():
        print(f"{name:<20}  {agent['model_uuid']:<38}  {agent['url']}")


def cmd_info(args):
    registry = load_agents()
    name, agent = resolve_agent(registry, args.agent_name)
    print(f"name:       {name}")
    print(f"id:         {agent['id']}")
    print(f"url:        {agent['url']}")
    print(f"model_uuid: {agent['model_uuid']}")
    print(f"region:     {agent['region']}")


def cmd_ask(args):
    registry = load_agents()
    agent_name, agent = resolve_agent(registry, args.agent_name)

    maybe_warn_egress()

    if IS_TTY:
        print(f"[{agent_name}]", file=sys.stderr)

    messages = [{"role": "user", "content": args.prompt}]

    try:
        full_text = stream_ask(agent["url"], agent["api_key"], messages, quiet=args.output_json)
    except requests.HTTPError as e:
        print(f"error: API request failed: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.ConnectionError as e:
        print(f"error: cannot reach agent endpoint: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.Timeout:
        print("error: request timed out", file=sys.stderr)
        sys.exit(1)

    if args.output_json:
        print(json.dumps({"agent": agent_name, "content": full_text}))
    elif IS_TTY:
        sys.stdout.write("\n")
        sys.stdout.flush()


def cmd_chat(args):
    registry = load_agents()
    name_arg = args.agent_name if args.agent_name else args.agent_name_flag
    agent_name, agent = resolve_agent(registry, name_arg)

    maybe_warn_egress()

    if IS_TTY:
        print(
            f"Connected to {agent_name} ({agent['model_uuid']}). "
            "Type your message, Ctrl+C to exit.",
            file=sys.stderr,
        )

    messages = []
    session_path = None
    created_iso = None

    if args.session:
        session_path, messages, created_iso = load_session(args.session, agent_name)

    while True:
        try:
            user_input = input(f"[{agent_name}] > ")
        except EOFError:
            break
        except KeyboardInterrupt:
            print(file=sys.stderr)
            break

        if not user_input.strip():
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            full_text = stream_ask(agent["url"], agent["api_key"], messages)
        except KeyboardInterrupt:
            messages.pop()
            sys.stdout.write("\n")
            sys.stdout.flush()
            continue
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as e:
            print(f"error: {e}", file=sys.stderr)
            messages.pop()
            continue

        sys.stdout.write("\n")
        sys.stdout.flush()

        messages.append({"role": "assistant", "content": full_text})

        if session_path:
            save_session(session_path, agent_name, messages, created_iso)


def main():
    parser = argparse.ArgumentParser(prog="agent", description="DO Gradient AI agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ask = sub.add_parser("ask", help="single-shot query to an agent")
    p_ask.add_argument("prompt", help="the prompt text")
    p_ask.add_argument("-n", dest="agent_name", default=None, help="agent name")
    p_ask.add_argument("--json", dest="output_json", action="store_true", help="wrap response in JSON envelope")
    p_ask.set_defaults(func=cmd_ask)

    p_chat = sub.add_parser("chat", help="interactive REPL with an agent")
    p_chat.add_argument("agent_name", nargs="?", default=None, help="agent name")
    p_chat.add_argument("-n", dest="agent_name_flag", default=None, help="agent name (flag form)")
    p_chat.add_argument("--session", dest="session", default=None, help="named session to persist/resume")
    p_chat.set_defaults(func=cmd_chat)

    p_list = sub.add_parser("list", help="show all agents in the registry")
    p_list.set_defaults(func=cmd_list)

    p_info = sub.add_parser("info", help="show detailed info for one agent")
    p_info.add_argument("-n", dest="agent_name", default=None, help="agent name")
    p_info.set_defaults(func=cmd_info)

    p_sessions = sub.add_parser("sessions", help="manage saved sessions")
    sessions_sub = p_sessions.add_subparsers(dest="sessions_command", required=True)

    p_sessions_list = sessions_sub.add_parser("list", help="list all sessions")
    p_sessions_list.set_defaults(func=cmd_sessions_list)

    p_sessions_rm = sessions_sub.add_parser("rm", help="delete a session")
    p_sessions_rm.add_argument("name", help="session name to delete")
    p_sessions_rm.set_defaults(func=cmd_sessions_rm)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
