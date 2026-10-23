from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "macrolens-api"}


def test_real_usa_macro_cache_is_served():
    client = TestClient(app)
    response = client.get("/api/macro/usa")
    assert response.status_code == 200
    payload = response.json()
    assert payload["economy"]
    assert payload["environment_label"]
    assert len(payload["pillars"]) >= 3


def test_unsupported_country_fails_closed():
    client = TestClient(app)
    response = client.get("/api/macro/mars")
    assert response.status_code == 404
