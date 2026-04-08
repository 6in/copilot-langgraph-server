"""Unit tests for POST /api/iframe-rpc endpoint."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.routes.iframe_rpc import router, IframeRpcRequest
from app.api.routes.chat import get_jwt_payload, get_github_token


# ---------------------------------------------------------------------------
# App fixture with dependency overrides
# ---------------------------------------------------------------------------

def _make_test_app(*, with_auth: bool = True):
    """Build a minimal FastAPI app with the iframe_rpc router mounted."""
    app = FastAPI()
    app.include_router(router)

    if with_auth:
        app.dependency_overrides[get_jwt_payload] = lambda: {
            "github_login": "test-user",
            "github_token": "encrypted-token",
        }
        app.dependency_overrides[get_github_token] = lambda: "ghu_test_token"

    # Attach a mock arq_redis to app.state
    mock_arq = AsyncMock()
    mock_arq.enqueue_job = AsyncMock()
    app.state.arq_redis = mock_arq

    return app, mock_arq


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_iframe_rpc_returns_job_id():
    """POST /api/iframe-rpc with valid JWT returns 200 + job_id."""
    app, mock_arq = _make_test_app(with_auth=True)

    with TestClient(app) as client:
        response = client.post(
            "/api/iframe-rpc",
            json={"id": "req-1", "method": "QUERY", "params": {"pool_name": "main", "sql": "SELECT 1"}},
        )

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert len(data["job_id"]) > 0


def test_iframe_rpc_enqueues_with_correct_task_type():
    """POST /api/iframe-rpc enqueues job with task_type='iframe_app_api'."""
    app, mock_arq = _make_test_app(with_auth=True)

    with TestClient(app) as client:
        response = client.post(
            "/api/iframe-rpc",
            json={"id": "req-2", "method": "AI", "params": {"model": "claude-sonnet-4.5", "prompt": "Hello"}},
        )

    assert response.status_code == 200

    # Verify enqueue_job was called with the correct arguments
    mock_arq.enqueue_job.assert_awaited_once()
    call_kwargs = mock_arq.enqueue_job.call_args.kwargs
    assert call_kwargs["task_type"] == "iframe_app_api"
    assert call_kwargs["rpc_method"] == "AI"
    assert call_kwargs["rpc_params"] == {"model": "claude-sonnet-4.5", "prompt": "Hello"}
    assert call_kwargs["github_login"] == "test-user"
    assert call_kwargs["thread_id"] == ""  # iframe-rpc doesn't use threads


def test_iframe_rpc_enqueues_query_method():
    """POST /api/iframe-rpc with QUERY method passes rpc_method and rpc_params."""
    app, mock_arq = _make_test_app(with_auth=True)

    with TestClient(app) as client:
        response = client.post(
            "/api/iframe-rpc",
            json={
                "id": "req-3",
                "method": "QUERY",
                "params": {"pool_name": "analytics", "sql": "SELECT count(*) FROM orders", "user": "alice"},
            },
        )

    assert response.status_code == 200
    call_kwargs = mock_arq.enqueue_job.call_args.kwargs
    assert call_kwargs["rpc_method"] == "QUERY"
    assert call_kwargs["rpc_params"]["pool_name"] == "analytics"
    assert call_kwargs["rpc_params"]["sql"] == "SELECT count(*) FROM orders"


def test_iframe_rpc_without_jwt_returns_401():
    """POST /api/iframe-rpc without JWT cookie returns 401."""
    # Build app WITHOUT auth overrides — real auth dependencies will raise 401
    app, _ = _make_test_app(with_auth=False)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/iframe-rpc",
            json={"id": "req-4", "method": "QUERY", "params": {}},
        )

    assert response.status_code == 401


def test_iframe_rpc_null_params_defaults_to_empty_dict():
    """POST /api/iframe-rpc with null params passes empty dict as rpc_params."""
    app, mock_arq = _make_test_app(with_auth=True)

    with TestClient(app) as client:
        response = client.post(
            "/api/iframe-rpc",
            json={"id": "req-5", "method": "AI", "params": None},
        )

    assert response.status_code == 200
    call_kwargs = mock_arq.enqueue_job.call_args.kwargs
    assert call_kwargs["rpc_params"] == {}


def test_iframe_rpc_job_id_is_unique():
    """Two separate calls each return a different job_id."""
    app, _ = _make_test_app(with_auth=True)
    job_ids = []

    with TestClient(app) as client:
        for _ in range(2):
            r = client.post(
                "/api/iframe-rpc",
                json={"id": "req-dup", "method": "QUERY", "params": {}},
            )
            job_ids.append(r.json()["job_id"])

    assert job_ids[0] != job_ids[1]
