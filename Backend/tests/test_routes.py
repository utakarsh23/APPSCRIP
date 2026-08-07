from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data


def test_signup_validation_error():
    response = client.post("/auth/signup", json={"username": "user", "email": "invalid-email", "password": "123"})
    assert response.status_code == 422


def test_protected_route_unauthorized():
    response = client.get("/files")
    assert response.status_code == 401
