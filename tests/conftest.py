import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.auth.manager import CopilotAuthManager


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
async def api_client(mock_graph, mock_auth_manager):
    """Async HTTP client for testing FastAPI routes with mocked dependencies.

    Lifespan does NOT fire with ASGITransport — inject mocks directly into app.state.
    """
    from app.api.main import app

    # Inject mocked state directly (lifespan doesn't fire in test)
    app.state.graph = mock_graph
    app.state.auth_manager = mock_auth_manager
    app.state.llm = MagicMock()
    app.state.llm.model = "gpt-4.1"
    app.state.db_path = ":memory:"
    app.state.device_flows = {}
    app.state.checkpointer = MagicMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
