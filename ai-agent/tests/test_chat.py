"""
Tests for cmd_chat() — interactive REPL (CHAT-04, CHAT-05).

These tests are written first (TDD Wave 0) and pass after Task 2 implements cmd_chat().
"""

import argparse
from unittest.mock import MagicMock, call, patch

import pytest
import requests

import agent
from agent import cmd_chat


def _make_args(agent_name="test-agent", session=None):
    return argparse.Namespace(agent_name=agent_name, agent_name_flag=None, session=session)


def _fresh_sse_mock():
    """Return a fresh mock SSE response (iterator can only be consumed once)."""
    sse_lines = [
        b'data: {"choices":[{"delta":{"role":"assistant"},"finish_reason":null}]}',
        b"",
        b'data: {"choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}',
        b"",
        b'data: {"choices":[{"delta":{"content":" world"},"finish_reason":null}]}',
        b"",
        b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
        b"",
        b"data: [DONE]",
    ]
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock(return_value=None)
    mock_resp.iter_lines = MagicMock(return_value=iter(sse_lines))
    return mock_resp


def test_repl_startup_header(agents_json_file, monkeypatch, capsys):
    """Startup header is printed to stderr when IS_TTY is True."""
    # Suppress egress warning by pointing marker to existing file
    marker_path = agents_json_file.parent / ".warned"
    marker_path.touch()
    monkeypatch.setattr(agent, "WARNED_MARKER", marker_path)
    monkeypatch.setattr(agent, "IS_TTY", True)
    # input() raises EOFError immediately — zero turns
    monkeypatch.setattr("builtins.input", lambda prompt="": (_ for _ in ()).throw(EOFError()))

    cmd_chat(_make_args())

    captured = capsys.readouterr()
    assert "Connected to test-agent (model-uuid-456). Type your message, Ctrl+C to exit." in captured.err


def test_repl_single_turn(agents_json_file, monkeypatch, capsys, mock_input_then_eof):
    """Single user turn: stream_ask called with correct messages, stdout contains response."""
    marker_path = agents_json_file.parent / ".warned"
    marker_path.touch()
    monkeypatch.setattr(agent, "WARNED_MARKER", marker_path)
    monkeypatch.setattr(agent, "IS_TTY", False)

    mock_input_then_eof(["hello"])

    captured_messages = []

    def fake_post(*args, **kwargs):
        # Capture the messages passed in the request body
        captured_messages.extend(kwargs.get("json", {}).get("messages", []))
        return _fresh_sse_mock()

    import requests as req_mod
    monkeypatch.setattr(req_mod, "post", fake_post)

    cmd_chat(_make_args())

    captured = capsys.readouterr()
    assert "Hello world" in captured.out
    assert len(captured_messages) == 1
    assert captured_messages[0] == {"role": "user", "content": "hello"}


def test_context_accumulates(agents_json_file, monkeypatch, capsys, mock_input_then_eof):
    """Second turn includes prior turns: [user(turn1), assistant(Hello world), user(turn2)]."""
    marker_path = agents_json_file.parent / ".warned"
    marker_path.touch()
    monkeypatch.setattr(agent, "WARNED_MARKER", marker_path)
    monkeypatch.setattr(agent, "IS_TTY", False)

    mock_input_then_eof(["turn1", "turn2"])

    call_count = [0]
    second_call_messages = []

    def fake_post(*args, **kwargs):
        call_count[0] += 1
        msgs = kwargs.get("json", {}).get("messages", [])
        if call_count[0] == 2:
            second_call_messages.extend(msgs)
        return _fresh_sse_mock()

    import requests as req_mod
    monkeypatch.setattr(req_mod, "post", fake_post)

    cmd_chat(_make_args())

    assert len(second_call_messages) == 3
    assert second_call_messages[0] == {"role": "user", "content": "turn1"}
    assert second_call_messages[1] == {"role": "assistant", "content": "Hello world"}
    assert second_call_messages[2] == {"role": "user", "content": "turn2"}


def test_ctrl_d_exits(agents_json_file, monkeypatch, capsys):
    """EOFError from input() causes clean return, no SystemExit."""
    marker_path = agents_json_file.parent / ".warned"
    marker_path.touch()
    monkeypatch.setattr(agent, "WARNED_MARKER", marker_path)
    monkeypatch.setattr(agent, "IS_TTY", False)
    monkeypatch.setattr("builtins.input", lambda prompt="": (_ for _ in ()).throw(EOFError()))

    # Must not raise
    cmd_chat(_make_args())


def test_ctrl_c_at_prompt_exits(agents_json_file, monkeypatch, capsys):
    """KeyboardInterrupt from input() causes clean return, no SystemExit."""
    marker_path = agents_json_file.parent / ".warned"
    marker_path.touch()
    monkeypatch.setattr(agent, "WARNED_MARKER", marker_path)
    monkeypatch.setattr(agent, "IS_TTY", False)
    monkeypatch.setattr("builtins.input", lambda prompt="": (_ for _ in ()).throw(KeyboardInterrupt()))

    # Must not raise
    cmd_chat(_make_args())


def test_abort_turn_not_saved(agents_json_file, monkeypatch, capsys, mock_input_then_eof):
    """KBI during stream_ask causes user message to be popped; loop continues cleanly."""
    marker_path = agents_json_file.parent / ".warned"
    marker_path.touch()
    monkeypatch.setattr(agent, "WARNED_MARKER", marker_path)
    monkeypatch.setattr(agent, "IS_TTY", False)

    mock_input_then_eof(["hello"])

    # stream_ask raises KBI
    monkeypatch.setattr(agent, "stream_ask", lambda *a, **kw: (_ for _ in ()).throw(KeyboardInterrupt()))

    cmd_chat(_make_args())

    # No output from the aborted turn
    captured = capsys.readouterr()
    assert "Hello world" not in captured.out


def test_network_error_returns_to_prompt(agents_json_file, monkeypatch, capsys, mock_input_then_eof):
    """ConnectionError is caught, error printed to stderr, loop continues for next turn."""
    marker_path = agents_json_file.parent / ".warned"
    marker_path.touch()
    monkeypatch.setattr(agent, "WARNED_MARKER", marker_path)
    monkeypatch.setattr(agent, "IS_TTY", False)

    mock_input_then_eof(["hello", "retry"])

    call_count = [0]

    def fake_post(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise requests.ConnectionError("offline")
        return _fresh_sse_mock()

    import requests as req_mod
    monkeypatch.setattr(req_mod, "post", fake_post)

    cmd_chat(_make_args())

    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "Hello world" in captured.out


def test_empty_input_skipped(agents_json_file, monkeypatch, capsys, mock_input_then_eof):
    """Empty or whitespace-only input does not call stream_ask."""
    marker_path = agents_json_file.parent / ".warned"
    marker_path.touch()
    monkeypatch.setattr(agent, "WARNED_MARKER", marker_path)
    monkeypatch.setattr(agent, "IS_TTY", False)

    mock_input_then_eof(["", "  ", "hello"])

    stream_ask_calls = [0]

    def fake_post(*args, **kwargs):
        stream_ask_calls[0] += 1
        return _fresh_sse_mock()

    import requests as req_mod
    monkeypatch.setattr(req_mod, "post", fake_post)

    cmd_chat(_make_args())

    assert stream_ask_calls[0] == 1


def test_no_session_no_file(agents_json_file, monkeypatch, capsys, tmp_path):
    """With session=None, no files are written to disk."""
    marker_path = agents_json_file.parent / ".warned"
    marker_path.touch()
    monkeypatch.setattr(agent, "WARNED_MARKER", marker_path)
    monkeypatch.setattr(agent, "IS_TTY", False)
    monkeypatch.setattr("builtins.input", lambda prompt="": (_ for _ in ()).throw(EOFError()))

    sessions_path = tmp_path / "sessions"
    sessions_path.mkdir(mode=0o700)

    cmd_chat(_make_args(session=None))

    # No files should have been created in the sessions directory
    assert list(sessions_path.iterdir()) == []
