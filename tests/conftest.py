"""Configuración compartida para tests (fixtures de pytest)."""
import pytest
import tempfile
import os
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def test_client():
    """Cliente HTTP de prueba para la API FastAPI."""
    from app import app
    client = TestClient(app)
    yield client


@pytest.fixture(scope="function")
def auth_system():
    """Sistema de autenticación con base de datos temporal."""
    from src.auth.auth import AuthSystem

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    system = AuthSystem(db_path=db_path)
    yield system

    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def test_user(auth_system):
    """Crea y devuelve un usuario de test registrado."""
    user_data = {
        "username": "testuser",
        "email": "test@urjc.es",
        "password": "SecurePass1",
    }
    result = auth_system.register(**user_data)
    assert result["success"], f"Error al crear usuario de test: {result['message']}"
    user_data["id"] = result["user_id"]
    return user_data
