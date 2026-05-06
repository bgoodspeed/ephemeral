"""
Session persistence tests (SESS-02, SESS-03).

Implements all session tests: load/save, permissions, list/rm, resume, mismatch, atomic write.
"""

import json
import os
import pathlib
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import agent


# ---------------------------------------------------------------------------
# test_session_file_permissions
# ---------------------------------------------------------------------------

def test_session_file_permissions(sessions_dir):
    """save_session() creates session file with 0o600 permissions."""
    path = sessions_dir / "test-sess.json"
    messages = [{"role": "user", "content": "hi"}]
    now = datetime.now(timezone.utc).isoformat()
    agent.save_session(path, "test-agent", messages, now)
    assert path.exists(), "session file should be created"
    mode = oct(path.stat().st_mode)
    assert "600" in mode, f"expected 0600 permissions, got {mode}"


# ---------------------------------------------------------------------------
# test_sessions_dir_permissions
# ---------------------------------------------------------------------------

def test_sessions_dir_permissions(tmp_path, monkeypatch):
    """SESSIONS_DIR is created at 0o700 when absent."""
    new_sessions = tmp_path / "newsessions"
    assert not new_sessions.exists(), "should not exist yet"
    monkeypatch.setattr(agent, "SESSIONS_DIR", new_sessions)
    # load_session creates SESSIONS_DIR if absent (when file doesn't exist)
    agent.load_session("test", "test-agent")
    assert new_sessions.exists(), "SESSIONS_DIR should have been created"
    mode = oct(new_sessions.stat().st_mode)
    assert "700" in mode, f"expected 0700 permissions, got {mode}"


# ---------------------------------------------------------------------------
# test_sessions_list_output
# ---------------------------------------------------------------------------

def test_sessions_list_output(sessions_dir, capsys, monkeypatch):
    """cmd_sessions_list prints NAME, AGENT, TURNS, LAST UPDATED columns."""
    monkeypatch.setattr(agent, "SESSIONS_DIR", sessions_dir)
    session_data = {
        "agent": "recon-agent",
        "created": "2026-04-01T10:00:00+00:00",
        "updated": "2026-04-01T14:32:00+00:00",
        "messages": [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "resp1"},
            {"role": "user", "content": "msg2"},
            {"role": "assistant", "content": "resp2"},
        ],
    }
    (sessions_dir / "recon.json").write_text(json.dumps(session_data, indent=2))
    args = SimpleNamespace()
    agent.cmd_sessions_list(args)
    captured = capsys.readouterr()
    assert "recon" in captured.out
    assert "recon-agent" in captured.out
    assert "4" in captured.out
    assert "2026-04-01" in captured.out


# ---------------------------------------------------------------------------
# test_sessions_rm_deletes
# ---------------------------------------------------------------------------

def test_sessions_rm_deletes(sessions_dir, monkeypatch):
    """cmd_sessions_rm removes session file from disk."""
    monkeypatch.setattr(agent, "SESSIONS_DIR", sessions_dir)
    session_file = sessions_dir / "old.json"
    session_file.write_text(json.dumps({"agent": "x", "messages": []}))
    assert session_file.exists()
    args = SimpleNamespace(name="old")
    agent.cmd_sessions_rm(args)
    assert not session_file.exists(), "session file should have been deleted"


# ---------------------------------------------------------------------------
# test_sessions_rm_missing_exits_1
# ---------------------------------------------------------------------------

def test_sessions_rm_missing_exits_1(sessions_dir, monkeypatch):
    """cmd_sessions_rm exits 1 for nonexistent session."""
    monkeypatch.setattr(agent, "SESSIONS_DIR", sessions_dir)
    args = SimpleNamespace(name="nope")
    with pytest.raises(SystemExit) as exc_info:
        agent.cmd_sessions_rm(args)
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# test_resume_loads_context
# ---------------------------------------------------------------------------

def test_resume_loads_context(
    sessions_dir, agents_json_file, mock_sse_response, monkeypatch, capsys
):
    """Loading session prepends messages; first API call includes history."""
    monkeypatch.setattr(agent, "SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr(agent, "IS_TTY", False)
    monkeypatch.setattr(agent, "WARNED_MARKER", sessions_dir / ".warned")

    # Pre-create session with 2 messages
    session_data = {
        "agent": "test-agent",
        "created": "2026-04-01T10:00:00+00:00",
        "updated": "2026-04-01T10:00:00+00:00",
        "messages": [
            {"role": "user", "content": "prior question"},
            {"role": "assistant", "content": "prior answer"},
        ],
    }
    (sessions_dir / "test-sess.json").write_text(json.dumps(session_data))

    # Track messages argument passed to requests.post
    captured_messages = []

    def fake_post(url, headers=None, json=None, stream=False, timeout=None, verify=True):
        if json and "messages" in json:
            captured_messages.extend(json["messages"])
        mock_sse_response.iter_lines = MagicMock(
            return_value=iter([
                b'data: {"choices":[{"delta":{"content":"reply"},"finish_reason":null}]}',
                b"data: [DONE]",
            ])
        )
        return mock_sse_response

    monkeypatch.setattr("requests.post", fake_post)

    # input() returns "turn2" once, then EOFError
    responses_iter = iter(["turn2"])

    def fake_input(prompt=""):
        try:
            return next(responses_iter)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr("builtins.input", fake_input)

    args = SimpleNamespace(
        agent_name="test-agent",
        agent_name_flag=None,
        session="test-sess",
    )
    agent.cmd_chat(args)

    captured = capsys.readouterr()
    # Should print resuming message to stderr
    assert "Resuming session" in captured.err, f"Expected 'Resuming session' in stderr: {captured.err!r}"

    # Messages sent to API should include: prior user, prior assistant, new user("turn2")
    assert len(captured_messages) == 3, f"Expected 3 messages in API call, got {len(captured_messages)}: {captured_messages}"
    assert captured_messages[0]["content"] == "prior question"
    assert captured_messages[1]["content"] == "prior answer"
    assert captured_messages[2]["content"] == "turn2"
    assert captured_messages[2]["role"] == "user"


# ---------------------------------------------------------------------------
# test_resume_agent_mismatch_warns
# ---------------------------------------------------------------------------

def test_resume_agent_mismatch_warns(sessions_dir, agents_json_file, monkeypatch, capsys):
    """Resuming with different agent prints warning to stderr."""
    monkeypatch.setattr(agent, "SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr(agent, "IS_TTY", False)
    monkeypatch.setattr(agent, "WARNED_MARKER", sessions_dir / ".warned")

    # Session was created with a DIFFERENT agent
    session_data = {
        "agent": "other-agent",
        "created": "2026-04-01T10:00:00+00:00",
        "updated": "2026-04-01T10:00:00+00:00",
        "messages": [],
    }
    (sessions_dir / "mismatch.json").write_text(json.dumps(session_data))

    # input() immediately raises EOFError (no turns)
    monkeypatch.setattr("builtins.input", lambda prompt="": (_ for _ in ()).throw(EOFError()))

    args = SimpleNamespace(
        agent_name="test-agent",
        agent_name_flag=None,
        session="mismatch",
    )
    agent.cmd_chat(args)

    captured = capsys.readouterr()
    assert "warning:" in captured.err.lower() or "warning" in captured.err.lower(), (
        f"Expected warning in stderr: {captured.err!r}"
    )
    assert "other-agent" in captured.err, f"Expected 'other-agent' in stderr: {captured.err!r}"


# ---------------------------------------------------------------------------
# test_atomic_write_safety
# ---------------------------------------------------------------------------

def test_atomic_write_safety(sessions_dir, monkeypatch):
    """save_session uses tempfile + os.replace; failure leaves no temp file."""
    import tempfile as tmpmod

    path = sessions_dir / "atomic.json"
    now = datetime.now(timezone.utc).isoformat()
    messages = [{"role": "user", "content": "hello"}]

    # Monkeypatch os.fdopen to raise IOError after temp file created
    original_mkstemp = tmpmod.mkstemp
    created_tmp = []

    def fake_mkstemp(dir=None):
        fd, tmppath = original_mkstemp(dir=dir)
        created_tmp.append(tmppath)
        return fd, tmppath

    monkeypatch.setattr(tmpmod, "mkstemp", fake_mkstemp)
    monkeypatch.setattr(os, "fdopen", lambda fd, mode: (_ for _ in ()).throw(IOError("simulated")))

    with pytest.raises(IOError):
        agent.save_session(path, "test-agent", messages, now)

    # The temp file should have been cleaned up
    for tmp in created_tmp:
        assert not pathlib.Path(tmp).exists(), f"temp file {tmp} was not cleaned up"
