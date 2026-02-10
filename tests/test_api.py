"""Tests de la API FastAPI — TFG Scraper Pro."""
import uuid
import pytest


def _unique(prefix: str) -> str:
    """Genera un nombre único para evitar colisiones entre ejecuciones."""
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


class TestHealthCheck:
    """Tests del endpoint de health check."""

    def test_health_returns_200(self, test_client):
        response = test_client.get("/api/health")
        assert response.status_code == 200

    def test_health_has_components(self, test_client):
        data = test_client.get("/api/health").json()
        assert data["status"] == "ok"
        assert "components" in data
        assert "search_engine" in data["components"]
        assert "llm" in data["components"]
        assert "auth_system" in data["components"]

    def test_health_has_version(self, test_client):
        data = test_client.get("/api/health").json()
        assert "version" in data


class TestStats:
    """Tests del endpoint de estadísticas."""

    def test_stats_endpoint(self, test_client):
        response = test_client.get("/api/stats")
        assert response.status_code in (200, 503)

    def test_stats_has_fields_when_available(self, test_client):
        response = test_client.get("/api/stats")
        if response.status_code == 200:
            data = response.json()
            assert "total_profesores" in data
            assert "total_documents" in data


class TestAuthentication:
    """Tests de registro y login."""

    def test_register_success(self, test_client):
        username = _unique("reg")
        response = test_client.post("/api/auth/register", json={
            "username": username,
            "email": f"{username}@urjc.es",
            "password": "TestPass1",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "user_id" in data

    def test_register_duplicate_fails(self, test_client):
        username = _unique("dup")
        test_client.post("/api/auth/register", json={
            "username": username,
            "email": f"{username}@urjc.es",
            "password": "TestPass1",
        })
        response = test_client.post("/api/auth/register", json={
            "username": username,
            "email": f"{username}2@urjc.es",
            "password": "TestPass1",
        })
        assert response.status_code == 400

    def test_register_weak_password_fails(self, test_client):
        username = _unique("weak")
        response = test_client.post("/api/auth/register", json={
            "username": username,
            "email": f"{username}@urjc.es",
            "password": "123",
        })
        assert response.status_code == 400

    def test_login_success(self, test_client):
        username = _unique("login")
        test_client.post("/api/auth/register", json={
            "username": username,
            "email": f"{username}@urjc.es",
            "password": "LoginTest1",
        })
        response = test_client.post("/api/auth/login", json={
            "username": username,
            "password": "LoginTest1",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user"]["username"] == username

    def test_login_wrong_password_fails(self, test_client):
        username = _unique("wrongpw")
        test_client.post("/api/auth/register", json={
            "username": username,
            "email": f"{username}@urjc.es",
            "password": "CorrectPass1",
        })
        response = test_client.post("/api/auth/login", json={
            "username": username,
            "password": "WrongPass1",
        })
        assert response.status_code == 401


class TestProfile:
    """Tests de gestión de perfiles."""

    def test_get_profile(self, test_client):
        username = _unique("prof")
        reg = test_client.post("/api/auth/register", json={
            "username": username,
            "email": f"{username}@urjc.es",
            "password": "ProfileTest1",
        })
        user_id = reg.json()["user_id"]

        response = test_client.get(f"/api/profile/{user_id}")
        assert response.status_code == 200
        assert response.json()["username"] == username

    def test_update_profile(self, test_client):
        username = _unique("upd")
        reg = test_client.post("/api/auth/register", json={
            "username": username,
            "email": f"{username}@urjc.es",
            "password": "UpdateTest1",
        })
        user_id = reg.json()["user_id"]

        response = test_client.put(f"/api/profile/{user_id}", json={
            "full_name": "Test User",
            "degree": "Informática",
            "year": 4,
            "interests": "Machine Learning",
        })
        assert response.status_code == 200
        assert response.json()["success"] is True

        profile = test_client.get(f"/api/profile/{user_id}").json()
        assert profile["full_name"] == "Test User"
        assert profile["interests"] == "Machine Learning"

    def test_get_nonexistent_profile_404(self, test_client):
        response = test_client.get("/api/profile/99999")
        assert response.status_code == 404
