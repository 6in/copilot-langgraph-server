import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.auth.manager import CopilotAuthManager


@pytest.fixture
def jwt_cookie():
    """A valid JWT session cookie value for use in chat endpoint tests."""
    from app.auth.jwt_utils import create_jwt
    return create_jwt("ghu_test_token_for_chat")


@pytest.fixture
def auth_manager(tmp_path: Path) -> CopilotAuthManager:
    """CopilotAuthManager using tmp_path for token storage."""
    return CopilotAuthManager(token_path=str(tmp_path / "token.enc"))


@pytest.fixture
def mock_graph():
    """Mock compiled LangGraph graph that returns a fixed AI reply."""
    graph = AsyncMock()
    graph.ainvoke = AsyncMock(return_value={
        "messages": [MagicMock(content="Hello from AI")]
    })
    return graph


@pytest.fixture
def mock_auth_manager(tmp_path):
    """Mock CopilotAuthManager for API tests."""
    manager = MagicMock()
    manager.load_token = MagicMock(return_value="ghu_fake_token")
    manager.start_device_flow = AsyncMock(return_value={
        "user_code": "ABCD-1234",
        "verification_uri": "https://github.com/login/device",
        "device_code": "dc_fake",
        "interval": 5,
    })
    manager.check_device_flow = AsyncMock(return_value=None)
    return manager


@pytest.fixture
def mock_job_store():
    """Mock JobStore for API tests."""
    store = AsyncMock()
    store.get = AsyncMock(return_value=None)  # default: pending
    store.save_result = AsyncMock()
    store.notify = AsyncMock()
    store.register_sse = MagicMock()
    store.unregister_sse = MagicMock()
    return store


@pytest.fixture
def mock_arq_redis():
    """Mock ArqRedis for enqueue tests."""
    arq = AsyncMock()
    arq.enqueue_job = AsyncMock()
    return arq


@pytest.fixture
async def api_client(mock_graph, mock_auth_manager, mock_job_store, mock_arq_redis):
    """Async HTTP client for testing FastAPI routes with mocked dependencies.

    Lifespan does NOT fire with ASGITransport — inject mocks directly into app.state.
    """
    from app.api.main import app

    # Inject mocked state directly (lifespan doesn't fire in test)
    mock_llm = MagicMock()
    mock_llm.model = "gpt-4.1"
    mock_llm.github_token = None
    mock_llm.close = AsyncMock()

    app.state.graph = mock_graph
    app.state.auth_manager = mock_auth_manager
    app.state.llm = mock_llm
    app.state.db_uri = "postgresql://test:test@localhost:5432/test"
    app.state.device_flows = {}
    app.state.checkpointer = MagicMock()
    app.state.job_store = mock_job_store
    app.state.arq_redis = mock_arq_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
