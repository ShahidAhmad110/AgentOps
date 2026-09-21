from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.errors import APIError, register_exception_handlers
from main import app


def test_health_returns_ok_and_request_id() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "degraded"}
    assert response.json()["database"] in {"connected", "unavailable"}
    assert response.headers["X-Request-ID"] == "test-request"


def test_api_error_responses_use_standard_error_contract() -> None:
    test_app = FastAPI()

    @test_app.get("/boom")
    async def boom() -> None:
        raise APIError(code="BAD_REQUEST", message="The request payload is invalid.", status_code=400)

    register_exception_handlers(test_app)
    client = TestClient(test_app)

    response = client.get("/boom")

    assert response.status_code == 400
    assert response.json() == {"error": {"code": "BAD_REQUEST", "message": "The request payload is invalid."}}