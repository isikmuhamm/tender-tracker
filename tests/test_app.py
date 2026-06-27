import pytest
import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.database import Base, get_db, User
from app import app

# Test için in-memory veritabanı kuralım ve StaticPool ile bağlantıyı paylaşalım
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Varsayılan test kullanıcısını ekle
    hashed = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode("utf-8")
    user = User(username="admin", password_hash=hashed)
    db.add(user)
    db.commit()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db):
    # FastAPI get_db bağımlılığını test_db ile ez
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_login_success(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_failure(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_tenders_endpoint_unauthorized(client):
    response = client.get("/api/tenders")
    assert response.status_code == 401

def test_tenders_endpoint_authorized(client):
    # Önce login ol
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    token = login_resp.json()["access_token"]
    
    # Token ile istek at
    response = client.get(
        "/api/tenders",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data

from unittest.mock import patch, mock_open

def test_get_config_authorized(client):
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    token = login_resp.json()["access_token"]
    
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="dummy: yaml_content")):
        response = client.get(
            "/api/config",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert "sectors" in data
        assert data["config"] == {"dummy": "yaml_content"}
        assert data["sectors"] == {"dummy": "yaml_content"}

def test_save_config_authorized(client):
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    token = login_resp.json()["access_token"]
    
    m = mock_open()
    with patch("builtins.open", m):
        response = client.post(
            "/api/config",
            json={"config": {"dummy": "new_config"}, "sectors": {"dummy": "new_sectors"}},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert m.call_count == 2

def test_save_config_invalid_json(client):
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    token = login_resp.json()["access_token"]
    
    response = client.post(
        "/api/config",
        content="invalid json {",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    assert response.status_code in (400, 422)

def test_get_logs(client):
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    token = login_resp.json()["access_token"]
    
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="line 1\nline 2\n")):
        response = client.get(
            "/api/logs",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "line 1" in data["logs"]

def test_trigger_scraper(client):
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    token = login_resp.json()["access_token"]
    
    with patch("src.scheduler.TenderBotOrchestrator.run_once") as mock_run_once:
        response = client.post(
            "/api/tenders/trigger",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        import time
        time.sleep(0.2)
        mock_run_once.assert_called_once()

def test_get_models_endpoint(client):
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    token = login_resp.json()["access_token"]
    
    response = client.get(
        "/api/models?provider=gemini",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "gemini-1.5-flash" in data["models"]

def test_catchall_frontend_routes(client):
    response = client.get("/tenders")
    assert response.status_code == 200
    
    response2 = client.get("/config/general")
    assert response2.status_code == 200

    response3 = client.get("/api/nonexistent")
    assert response3.status_code == 404

def test_get_models_with_header_key(client):
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    token = login_resp.json()["access_token"]
    
    response = client.get(
        "/api/models?provider=gemini",
        headers={
            "Authorization": f"Bearer {token}",
            "X-API-Key": "mock_api_key"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "models" in data

