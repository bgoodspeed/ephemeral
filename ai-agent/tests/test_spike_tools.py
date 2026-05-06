"""
Unit tests for .planning/research/spike_tools.py

Tests use importlib to load the script by path, and monkeypatch/capsys
to intercept requests and capture output.
"""
import importlib.util
import json
import sys
import pathlib
from unittest.mock import MagicMock

import pytest

SCRIPT_PATH = pathlib.Path(__file__).parent.parent / ".planning" / "research" / "spike_tools.py"


def load_spike_tools():
    """Import spike_tools module by file path."""
    spec = importlib.util.spec_from_file_location("spike_tools", str(SCRIPT_PATH))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# test_missing_agents_json
# ---------------------------------------------------------------------------

def test_missing_agents_json(tmp_path, monkeypatch, capsys):
    """When agents.json does not exist, prints error to stderr and exits 1."""
    monkeypatch.chdir(tmp_path)
    spike = load_spike_tools()

    with pytest.raises(SystemExit) as exc_info:
        spike.load_agents()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "agents.json" in captured.err
    assert "not found" in captured.err


# ---------------------------------------------------------------------------
# test_empty_agents
# ---------------------------------------------------------------------------

def test_empty_agents(tmp_path, monkeypatch, capsys):
    """When agents.json has no agents, prints error to stderr and exits 1."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "agents.json").write_text(json.dumps({"version": 1, "agents": {}}))

    spike = load_spike_tools()
    registry = spike.load_agents()

    with pytest.raises(SystemExit) as exc_info:
        spike.resolve_agent(registry)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "no agents" in captured.err.lower() or "contains no agents" in captured.err


# ---------------------------------------------------------------------------
# test_request_body_shape
# ---------------------------------------------------------------------------

def test_request_body_shape(agents_json_file, monkeypatch):
    """The POST request body contains messages, tools, tool_choice, and stream=False."""
    spike = load_spike_tools()

    captured_kwargs = {}

    def mock_post(url, headers=None, json=None, timeout=None, **kwargs):
        captured_kwargs["url"] = url
        captured_kwargs["json"] = json
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"finish_reason": "stop", "message": {"content": "It's sunny."}}]
        }
        return mock_resp

    import requests
    monkeypatch.setattr(requests, "post", mock_post)

    spike = load_spike_tools()
    spike.probe_tool_use("https://test.agents.do-ai.run", "test-key-abc")

    body = captured_kwargs["json"]
    assert "messages" in body
    assert isinstance(body["messages"], list)
    assert len(body["messages"]) >= 1
    assert body["messages"][0]["role"] == "user"
    assert "tools" in body
    assert isinstance(body["tools"], list)
    assert len(body["tools"]) >= 1
    assert "tool_choice" in body
    assert body["tool_choice"] == "auto"
    assert "stream" in body
    assert body["stream"] is False


# ---------------------------------------------------------------------------
# test_supported_tool_calls
# ---------------------------------------------------------------------------

def test_supported_tool_calls(agents_json_file, monkeypatch, capsys):
    """When API returns finish_reason 'tool_calls', stdout contains SUPPORTED."""
    import requests

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": '{"location": "Toronto"}'},
                        }
                    ]
                },
            }
        ]
    }
    monkeypatch.setattr(requests, "post", lambda *a, **kw: mock_resp)

    spike = load_spike_tools()
    spike.main()

    captured = capsys.readouterr()
    assert "SUPPORTED" in captured.out
    assert "tool_calls" in captured.out


# ---------------------------------------------------------------------------
# test_unsupported_stop
# ---------------------------------------------------------------------------

def test_unsupported_stop(agents_json_file, monkeypatch, capsys):
    """When API returns finish_reason 'stop' with no tool_calls, stdout contains UNSUPPORTED."""
    import requests

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"finish_reason": "stop", "message": {"content": "It's sunny in Toronto."}}]
    }
    monkeypatch.setattr(requests, "post", lambda *a, **kw: mock_resp)

    spike = load_spike_tools()
    spike.main()

    captured = capsys.readouterr()
    assert "UNSUPPORTED" in captured.out
    assert "stop" in captured.out


# ---------------------------------------------------------------------------
# test_unsupported_http_4xx
# ---------------------------------------------------------------------------

def test_unsupported_http_4xx(agents_json_file, monkeypatch, capsys):
    """When API returns HTTP 400, stdout contains UNSUPPORTED and HTTP 400; no crash."""
    import requests

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"error": {"message": "tools field not supported"}}
    monkeypatch.setattr(requests, "post", lambda *a, **kw: mock_resp)

    spike = load_spike_tools()
    spike.main()

    captured = capsys.readouterr()
    assert "UNSUPPORTED" in captured.out
    assert "400" in captured.out


# ---------------------------------------------------------------------------
# test_no_secrets_in_output
# ---------------------------------------------------------------------------

def test_no_secrets_in_output(agents_json_file, monkeypatch, capsys):
    """The captured stdout from a probe run does not contain the api_key value."""
    import requests

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"finish_reason": "stop", "message": {"content": "Fine."}}]
    }
    monkeypatch.setattr(requests, "post", lambda *a, **kw: mock_resp)

    spike = load_spike_tools()
    spike.main()

    captured = capsys.readouterr()
    # The api_key from sample_registry fixture is "test-key-abc"
    assert "test-key-abc" not in captured.out


# ---------------------------------------------------------------------------
# test_endpoint_url
# ---------------------------------------------------------------------------

def test_endpoint_url(agents_json_file, monkeypatch):
    """POST is sent to {agent_url}/api/v1/chat/completions."""
    import requests

    captured_url = {}

    def mock_post(url, **kwargs):
        captured_url["url"] = url
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"finish_reason": "stop", "message": {"content": "Fine."}}]
        }
        return mock_resp

    monkeypatch.setattr(requests, "post", mock_post)

    spike = load_spike_tools()
    spike.probe_tool_use("https://test.agents.do-ai.run", "test-key-abc")

    assert captured_url["url"] == "https://test.agents.do-ai.run/api/v1/chat/completions"
