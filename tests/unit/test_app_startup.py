from fastapi import FastAPI

from backend.api.app import create_app
from database.base import Base
from database import models  # noqa: F401


def test_app_starts() -> None:
    app = create_app()

    assert isinstance(app, FastAPI)
    assert app.title == "AgentOps"


def test_database_metadata_contains_foundation_models() -> None:
    assert {"organizations", "users"}.issubset(Base.metadata.tables)
