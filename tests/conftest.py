import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
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

# api_client fixture — added in Plan 02 when app/api/main.py exists
