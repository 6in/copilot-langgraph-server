import pytest
from pathlib import Path
from app.auth.manager import CopilotAuthManager


@pytest.fixture
def auth_manager(tmp_path: Path) -> CopilotAuthManager:
    """CopilotAuthManager using tmp_path for token storage."""
    return CopilotAuthManager(token_path=str(tmp_path / "token.enc"))
