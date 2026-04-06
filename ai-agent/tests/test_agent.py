import argparse
import subprocess
import sys

import pytest

from agent import load_agents, resolve_agent, cmd_list, cmd_info, stream_ask, cmd_ask
import agent


def test_load_agents(agents_json_file):
    registry = load_agents()
    assert "version" in registry
    assert "agents" in registry


def test_load_agents_missing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        load_agents()
    assert exc_info.value.code == 1


def test_cmd_list_output(agents_json_file, capsys):
    class Args:
        pass

    cmd_list(Args())
    captured = capsys.readouterr()
    assert "test-agent" in captured.out
    assert "model-uuid-456" in captured.out
    assert "https://test.agents.do-ai.run" in captured.out


def test_cmd_info_output(agents_json_file, capsys):
    class Args:
        agent_name = "test-agent"

    cmd_info(Args())
    captured = capsys.readouterr()
    assert "name:" in captured.out
    assert "test-agent" in captured.out
    assert "id:" in captured.out
    assert "uuid-123" in captured.out
    assert "url:" in captured.out
    assert "https://test.agents.do-ai.run" in captured.out
    assert "model_uuid:" in captured.out
    assert "model-uuid-456" in captured.out
    assert "region:" in captured.out
    assert "tor1" in captured.out
    assert "api_key" not in captured.out


def test_resolve_agent_single_default(sample_registry):
    name, agent = resolve_agent(sample_registry, None)
    assert name == "test-agent"
    assert agent == sample_registry["agents"]["test-agent"]


def test_resolve_agent_named(sample_registry):
    name, agent = resolve_agent(sample_registry, "test-agent")
    assert name == "test-agent"
    assert agent == sample_registry["agents"]["test-agent"]


def test_resolve_agent_unknown_name(sample_registry):
    with pytest.raises(SystemExit) as exc_info:
        resolve_agent(sample_registry, "nope")
    assert exc_info.value.code == 1


def test_resolve_agent_multi_no_name(multi_agent_registry):
    with pytest.raises(SystemExit) as exc_info:
        resolve_agent(multi_agent_registry, None)
    assert exc_info.value.code == 1


def test_no_subcommand_exits_2():
    result = subprocess.run(
        [sys.executable, "agent.py"],
        capture_output=True,
        cwd="/home/bg/src/ephemeral/ai-agent",
    )
    assert result.returncode == 2


def test_stream_ask_writes_tokens(mock_sse_response, monkeypatch, capsys):
    import requests as req_mod

    monkeypatch.setattr(req_mod, "post", lambda *a, **kw: mock_sse_response)
    result = stream_ask(
        "https://fake.url",
        "fake-key",
        [{"role": "user", "content": "hi"}],
    )
    captured = capsys.readouterr()
    assert captured.out == "Hello world"
    assert result == "Hello world"


def test_cmd_ask_tty_header(agents_json_file, mock_sse_response, monkeypatch, capsys):
    import requests as req_mod

    monkeypatch.setattr(req_mod, "post", lambda *a, **kw: mock_sse_response)
    monkeypatch.setattr(agent, "IS_TTY", True)
    # Use a marker path that already exists so egress warning is skipped
    marker_path = agents_json_file.parent / ".warned"
    marker_path.touch()
    monkeypatch.setattr(agent, "WARNED_MARKER", marker_path)

    args = argparse.Namespace(agent_name="test-agent", prompt="hi", output_json=False)
    cmd_ask(args)
    captured = capsys.readouterr()
    assert "[test-agent]" in captured.err
    assert "Hello world" in captured.out


def test_cmd_ask_pipe_no_decoration(agents_json_file, mock_sse_response, monkeypatch, capsys):
    import requests as req_mod

    monkeypatch.setattr(req_mod, "post", lambda *a, **kw: mock_sse_response)
    monkeypatch.setattr(agent, "IS_TTY", False)
    marker_path = agents_json_file.parent / ".warned"
    marker_path.touch()
    monkeypatch.setattr(agent, "WARNED_MARKER", marker_path)

    args = argparse.Namespace(agent_name="test-agent", prompt="hi", output_json=False)
    cmd_ask(args)
    captured = capsys.readouterr()
    assert captured.out == "Hello world"
    assert "[test-agent]" not in captured.err


def test_json_flag(agents_json_file, mock_sse_response, monkeypatch, capsys):
    import json as json_mod
    import requests as req_mod

    monkeypatch.setattr(req_mod, "post", lambda *a, **kw: mock_sse_response)
    monkeypatch.setattr(agent, "IS_TTY", False)
    marker_path = agents_json_file.parent / ".warned"
    marker_path.touch()
    monkeypatch.setattr(agent, "WARNED_MARKER", marker_path)

    args = argparse.Namespace(agent_name="test-agent", prompt="hi", output_json=True)
    cmd_ask(args)
    captured = capsys.readouterr()
    result = json_mod.loads(captured.out)
    assert result == {"agent": "test-agent", "content": "Hello world"}


def test_egress_warning_shown_once(agents_json_file, mock_sse_response, monkeypatch, capsys, tmp_path):
    import requests as req_mod

    monkeypatch.setattr(req_mod, "post", lambda *a, **kw: mock_sse_response)
    monkeypatch.setattr(agent, "IS_TTY", False)
    marker_path = tmp_path / ".config" / "doagent" / ".warned"
    monkeypatch.setattr(agent, "WARNED_MARKER", marker_path)

    args = argparse.Namespace(agent_name="test-agent", prompt="hi", output_json=False)
    cmd_ask(args)
    captured = capsys.readouterr()
    assert "prompt content will leave this machine" in captured.err
    assert marker_path.exists()

    # Second call — mock needs a fresh iterator
    mock_sse_response.iter_lines = lambda chunk_size=1: iter([
        b'data: {"choices":[{"delta":{"content":"Hi"},"finish_reason":null}]}',
        b"data: [DONE]",
    ])
    cmd_ask(args)
    captured2 = capsys.readouterr()
    assert "prompt content will leave this machine" not in captured2.err


def test_http_error_exits_1(agents_json_file, monkeypatch):
    import requests as req_mod

    def mock_post(*a, **kw):
        mock_resp = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
        mock_resp.raise_for_status.side_effect = req_mod.HTTPError("401 Unauthorized")
        return mock_resp

    monkeypatch.setattr(req_mod, "post", mock_post)
    monkeypatch.setattr(agent, "IS_TTY", False)
    marker_path = agents_json_file.parent / ".warned"
    marker_path.touch()
    monkeypatch.setattr(agent, "WARNED_MARKER", marker_path)

    args = argparse.Namespace(agent_name="test-agent", prompt="hi", output_json=False)
    with pytest.raises(SystemExit) as exc_info:
        cmd_ask(args)
    assert exc_info.value.code == 1
