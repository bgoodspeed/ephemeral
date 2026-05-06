"""
Unit tests for .planning/research/spike_workspace.py

Tests use importlib to load the script by path, monkeypatch to intercept
requests.Session, and capsys to capture output.
"""
import importlib.util
import json
import pathlib
import sys
from unittest.mock import MagicMock, patch

import pytest

SCRIPT_PATH = (
    pathlib.Path(__file__).parent.parent / ".planning" / "research" / "spike_workspace.py"
)

SAMPLE_CONFIG = {"do_token": "test-do-token-xyz"}
SAMPLE_STATE = {"workspace_uuid": "ws-uuid-abc123"}


def load_spike_workspace():
    """Import spike_workspace module by file path."""
    spec = importlib.util.spec_from_file_location("spike_workspace", str(SCRIPT_PATH))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# test_missing_config
# ---------------------------------------------------------------------------

def test_missing_config(tmp_path, monkeypatch, capsys):
    """When config.json does not exist, prints error to stderr and exits 1."""
    monkeypatch.chdir(tmp_path)
    spike = load_spike_workspace()

    with pytest.raises(SystemExit) as exc_info:
        spike.load_config()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "config.json" in captured.err
    assert "not found" in captured.err


# ---------------------------------------------------------------------------
# test_missing_state_workspace_uuid
# ---------------------------------------------------------------------------

def test_missing_state_workspace_uuid(tmp_path, monkeypatch, capsys):
    """When state.json is empty or has no workspace_uuid, prints error and exits 1."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text(json.dumps(SAMPLE_CONFIG))
    (tmp_path / "state.json").write_text(json.dumps({}))

    spike = load_spike_workspace()

    # Mock requests.Session so we don't make real HTTP calls
    mock_session = MagicMock()
    with patch("requests.Session", return_value=mock_session):
        with pytest.raises(SystemExit) as exc_info:
            spike.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "workspace_uuid" in captured.err


# ---------------------------------------------------------------------------
# test_probes_all_candidate_endpoints
# ---------------------------------------------------------------------------

def test_probes_all_candidate_endpoints(tmp_path, monkeypatch, capsys):
    """The script makes HTTP requests to all 4 candidate paths."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text(json.dumps(SAMPLE_CONFIG))
    (tmp_path / "state.json").write_text(json.dumps(SAMPLE_STATE))

    spike = load_spike_workspace()

    probed_paths = []

    def make_mock_resp(status):
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = {"id": "not_found", "message": "The resource you requested could not be found."}
        resp.content = b'{"id": "not_found"}'
        return resp

    mock_session = MagicMock()
    mock_session.get.return_value = make_mock_resp(404)
    mock_session.post.return_value = make_mock_resp(404)

    # Track which URLs were requested
    original_get = mock_session.get
    original_post = mock_session.post

    def track_get(url, **kwargs):
        probed_paths.append(("GET", url))
        return original_get(url, **kwargs)

    def track_post(url, **kwargs):
        probed_paths.append(("POST", url))
        return original_post(url, **kwargs)

    mock_session.get = track_get
    mock_session.post = track_post

    with patch("requests.Session", return_value=mock_session):
        spike.main()

    probed_urls = [url for _, url in probed_paths]
    ws_uuid = SAMPLE_STATE["workspace_uuid"]
    base = "https://api.digitalocean.com/v2"

    assert f"{base}/gen-ai/workspaces/{ws_uuid}/files" in probed_urls
    assert f"{base}/gen-ai/workspaces/{ws_uuid}/v1/files" in probed_urls
    assert f"{base}/gen-ai/knowledge_bases/data_sources/file_upload_presigned_urls" in probed_urls
    assert f"{base}/gen-ai/evaluation_datasets/file_upload_presigned_urls" in probed_urls


# ---------------------------------------------------------------------------
# test_404_not_found_body_unsupported
# ---------------------------------------------------------------------------

def test_404_not_found_body_unsupported():
    """interpret_result returns UNSUPPORTED for 404 with not_found body."""
    spike = load_spike_workspace()
    body = {"id": "not_found", "message": "The resource you requested could not be found."}
    result = spike.interpret_result(404, body)
    assert result == "UNSUPPORTED"


# ---------------------------------------------------------------------------
# test_404_empty_body_unknown
# ---------------------------------------------------------------------------

def test_404_empty_body_unknown():
    """interpret_result returns UNKNOWN for 404 with empty or ambiguous body."""
    spike = load_spike_workspace()
    result = spike.interpret_result(404, {})
    assert result == "UNKNOWN"

    result2 = spike.interpret_result(404, "")
    assert result2 == "UNKNOWN"


# ---------------------------------------------------------------------------
# test_2xx_exists
# ---------------------------------------------------------------------------

def test_2xx_exists():
    """interpret_result returns EXISTS for 200."""
    spike = load_spike_workspace()
    result = spike.interpret_result(200, {"files": []})
    assert result == "EXISTS"


# ---------------------------------------------------------------------------
# test_400_422_exists_bad_request
# ---------------------------------------------------------------------------

def test_400_422_exists_bad_request():
    """interpret_result returns EXISTS (bad request...) for 400 and 422."""
    spike = load_spike_workspace()
    result_400 = spike.interpret_result(400, {"message": "bad request"})
    assert "EXISTS" in result_400
    assert "bad request" in result_400.lower()

    result_422 = spike.interpret_result(422, {"message": "unprocessable"})
    assert "EXISTS" in result_422
    assert "bad request" in result_422.lower()


# ---------------------------------------------------------------------------
# test_no_secrets_in_output
# ---------------------------------------------------------------------------

def test_no_secrets_in_output(tmp_path, monkeypatch, capsys):
    """Captured stdout does not contain the do_token value."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text(json.dumps(SAMPLE_CONFIG))
    (tmp_path / "state.json").write_text(json.dumps(SAMPLE_STATE))

    spike = load_spike_workspace()

    def make_mock_resp(status):
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = {"id": "not_found", "message": "The resource you requested could not be found."}
        resp.content = b'{"id": "not_found"}'
        return resp

    mock_session = MagicMock()
    mock_session.get.return_value = make_mock_resp(404)
    mock_session.post.return_value = make_mock_resp(404)

    with patch("requests.Session", return_value=mock_session):
        spike.main()

    captured = capsys.readouterr()
    assert "test-do-token-xyz" not in captured.out


# ---------------------------------------------------------------------------
# test_uses_bearer_auth
# ---------------------------------------------------------------------------

def test_uses_bearer_auth(tmp_path, monkeypatch):
    """The session headers include Authorization: Bearer {do_token}."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text(json.dumps(SAMPLE_CONFIG))
    (tmp_path / "state.json").write_text(json.dumps(SAMPLE_STATE))

    spike = load_spike_workspace()

    headers_set = {}

    def make_mock_resp(status):
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = {"id": "not_found", "message": "The resource you requested could not be found."}
        resp.content = b'{"id": "not_found"}'
        return resp

    mock_session = MagicMock()
    mock_session.get.return_value = make_mock_resp(404)
    mock_session.post.return_value = make_mock_resp(404)

    real_session_instance = mock_session
    headers_store = {}

    original_headers_update = lambda h: headers_store.update(h)
    mock_session.headers = MagicMock()
    mock_session.headers.update = lambda h: headers_store.update(h)

    with patch("requests.Session", return_value=mock_session):
        spike.main()

    assert "Authorization" in headers_store
    assert headers_store["Authorization"] == f"Bearer {SAMPLE_CONFIG['do_token']}"
