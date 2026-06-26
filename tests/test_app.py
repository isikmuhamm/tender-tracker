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
