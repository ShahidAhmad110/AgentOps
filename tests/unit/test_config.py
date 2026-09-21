from backend.core.config import get_settings


def test_configuration_loads() -> None:
    settings = get_settings()

    assert settings.app_name == "AgentOps"
    assert settings.app_env == "development"
    assert "postgresql" in settings.database_url.lower()
