import json
import os
import pathlib
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_sse_response():
    """Mock requests.post() return value with stream=True simulating SSE chunks."""
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


@pytest.fixture
def warned_marker(tmp_path):
    """Returns a Path for the egress marker file. Does NOT create the file."""
    return tmp_path / ".config" / "doagent" / ".warned"


@pytest.fixture
def sample_registry():
    return {
        "version": 1,
        "agents": {
            "test-agent": {
                "id": "uuid-123",
                "url": "https://test.agents.do-ai.run",
                "model_uuid": "model-uuid-456",
                "region": "tor1",
                "api_key": "test-key-abc",
            }
        },
    }


@pytest.fixture
def multi_agent_registry():
    return {
        "version": 1,
        "agents": {
            "agent-a": {
                "id": "uuid-aaa",
                "url": "https://agent-a.agents.do-ai.run",
                "model_uuid": "model-uuid-aaa",
                "region": "tor1",
                "api_key": "key-aaa",
            },
            "agent-b": {
                "id": "uuid-bbb",
                "url": "https://agent-b.agents.do-ai.run",
                "model_uuid": "model-uuid-bbb",
                "region": "nyc3",
                "api_key": "key-bbb",
            },
        },
    }


@pytest.fixture
def agents_json_file(tmp_path, sample_registry, monkeypatch):
    agents_file = tmp_path / "agents.json"
    agents_file.write_text(json.dumps(sample_registry, indent=2))
    monkeypatch.chdir(tmp_path)
    return agents_file


@pytest.fixture
def empty_registry():
    return {"version": 1, "agents": {}}


@pytest.fixture
def sessions_dir(tmp_path):
    """Temp sessions directory for session tests."""
    d = tmp_path / "sessions"
    d.mkdir(mode=0o700)
    return d


@pytest.fixture
def mock_input_then_eof(monkeypatch):
    """Factory: returns a function that patches input() to yield given strings then raise EOFError."""
    def _make(responses):
        it = iter(responses)
        def fake_input(prompt=""):
            try:
                return next(it)
            except StopIteration:
                raise EOFError
        monkeypatch.setattr("builtins.input", fake_input)
    return _make
