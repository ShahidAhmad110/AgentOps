from fastapi.testclient import TestClient

from main import app


def test_health_returns_ok_and_request_id() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "test-request"