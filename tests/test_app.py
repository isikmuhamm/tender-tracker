import pytest
import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock
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

@patch("requests.get")
def test_get_models_endpoint(mock_get, client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [
            {"name": "models/gemini-1.5-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-1.5-pro", "supportedGenerationMethods": ["generateContent"]}
        ]
    }
    mock_get.return_value = mock_resp

    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    token = login_resp.json()["access_token"]
    
    response = client.get(
        "/api/models?provider=gemini",
        headers={
            "Authorization": f"Bearer {token}",
            "X-API-Key": "test_key"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "gemini-1.5-flash" in data["models"]
    
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "generativelanguage.googleapis.com" in args[0]
    assert "?key=" not in args[0]

def test_catchall_frontend_routes(client):
    response = client.get("/tenders")
    assert response.status_code == 200
    
    response2 = client.get("/config/general")
    assert response2.status_code == 200

    response3 = client.get("/api/nonexistent")
    assert response3.status_code == 404

@patch("requests.get")
def test_get_models_with_header_key(mock_get, client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [
            {"name": "models/gemini-1.5-flash", "supportedGenerationMethods": ["generateContent"]}
        ]
    }
    mock_get.return_value = mock_resp

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
    
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert kwargs["headers"]["x-goog-api-key"] == "mock_api_key"
    assert "?key=" not in args[0]

@patch("requests.get")
def test_get_models_exception_redaction(mock_get, client):
    mock_get.side_effect = Exception("Failed connecting to https://generativelanguage.googleapis.com/v1beta/models?key=super_secret_key_123")
    
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    token = login_resp.json()["access_token"]
    
    with patch("logging.error") as mock_log_error:
        response = client.get(
            "/api/models?provider=gemini",
            headers={
                "Authorization": f"Bearer {token}",
                "X-API-Key": "super_secret_key_123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        
        mock_log_error.assert_called_once()
        log_msg = mock_log_error.call_args[0][0]
        assert "super_secret_key_123" not in log_msg
        assert "HIDDEN_KEY" in log_msg

def test_job_status_and_mutual_exclusion(client):
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    status_resp = client.get("/api/job/status", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "idle"
    
    from app import job_state
    assert job_state.start_job("scanning") is True
    
    trigger_resp = client.post("/api/tenders/trigger", headers=headers)
    assert trigger_resp.status_code == 409
    assert "meşgul" in trigger_resp.json()["detail"]
    
    reeval_resp = client.post("/api/tenders/re-evaluate", headers=headers)
    assert reeval_resp.status_code == 409
    
    status_resp = client.get("/api/job/status", headers=headers)
    assert status_resp.json()["status"] == "scanning"
    
    job_state.finish_job(True)
    status_resp = client.get("/api/job/status", headers=headers)
    assert status_resp.json()["status"] == "idle"
    assert status_resp.json()["last_run_status"] == "success"

def test_process_lock_concurrency(client, tmp_path):
    from src.process_lock import ProcessLock
    
    def mock_get_data_path(filename):
        return str(tmp_path / filename)
        
    with patch("src.process_lock.get_data_path", side_effect=mock_get_data_path):
        lock1 = ProcessLock("scan")
        lock2 = ProcessLock("scan")
        
        lock1.release()
        
        assert lock1.acquire() is True
        assert lock2.acquire() is False
        
        login_resp = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin"}
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        trigger_resp = client.post("/api/tenders/trigger", headers=headers)
        assert trigger_resp.status_code == 409
        assert "meşgul" in trigger_resp.json()["detail"] or "meşgul" in trigger_resp.json()["detail"].lower()
            
        lock1.release()
        assert lock2.acquire() is True
        lock2.release()

def test_frontend_xss_via_node():
    import subprocess
    import os
    js_test_path = os.path.join(os.path.dirname(__file__), "test_frontend_xss.js")
    result = subprocess.run(["node", js_test_path], capture_output=True, text=True)
    assert result.returncode == 0, f"Frontend XSS JS tests failed: {result.stderr}\nOutput: {result.stdout}"

def test_process_lock_owner_token(tmp_path):
    from src.process_lock import ProcessLock
    import os
    
    def mock_get_data_path(filename):
        return str(tmp_path / filename)
        
    with patch("src.process_lock.get_data_path", side_effect=mock_get_data_path):
        lock1 = ProcessLock("test_owner")
        lock2 = ProcessLock("test_owner")
        
        assert lock1.acquire() is True
        
        # lock2 has a different owner token, trying to release should do nothing!
        lock2.release()
        
        # Verify that lock1 is STILL active and lock2 cannot acquire it
        assert os.path.exists(lock1.lock_path) is True
        assert lock2.acquire() is False
        
        # Now release with lock1 (which owns it)
        lock1.release()
        
        # Verify that it is released and lock2 can now acquire it
        assert os.path.exists(lock1.lock_path) is False
        assert lock2.acquire() is True
        lock2.release()

def test_run_startup_scan_triggered():
    import sys
    with patch("app.TenderBotOrchestrator") as mock_orch_class, patch("src.process_lock.ProcessLock") as mock_lock_class:
        # Mock ProcessLock to successfully acquire lock
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        mock_lock_class.return_value = mock_lock
        
        mock_orch = MagicMock()
        mock_orch_class.return_value = mock_orch
        
        # Remove pytest from sys.modules dictionary temporarily
        original_pytest = sys.modules.pop("pytest", None)
        
        try:
            import threading
            original_thread = threading.Thread
            threads = []
            def mock_thread(*args, **kwargs):
                t = original_thread(*args, **kwargs)
                threads.append(t)
                return t
            with patch("threading.Thread", side_effect=mock_thread):
                from app import run_startup_scan, job_state
                # Ensure job_state is idle
                job_state.status = "idle"
                run_startup_scan()
                
                # Wait for thread to finish
                for t in threads:
                    t.join(timeout=3)
        finally:
            if original_pytest:
                sys.modules["pytest"] = original_pytest
                    
        assert mock_orch.run_once.call_count == 1
        assert mock_lock.acquire.call_count == 1
        assert mock_lock.release.call_count == 1



