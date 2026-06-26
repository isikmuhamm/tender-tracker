import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, Tender, User, init_db

# Testler için bellekte (in-memory) geçici bir SQLite veritabanı oluşturalım
@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()

def test_create_tender(db_session):
    """Tender kaydının veritabanına başarıyla eklenip eklenmediğini test eder."""
    tender = Tender(
        link="https://example.com/tender1",
        title="Test İhalesi 1",
        summary="Bu bir test ihalesidir.",
        category="Yapım İşleri",
        source="test_source"
    )
    
    db_session.add(tender)
    db_session.commit()
    
    # Veritabanından sorgula
    db_tender = db_session.query(Tender).filter_by(link="https://example.com/tender1").first()
    
    assert db_tender is not None
    assert db_tender.title == "Test İhalesi 1"
    assert db_tender.source == "test_source"
    assert db_tender.email_sent is False
    assert db_tender.telegram_sent is False
    assert db_tender.first_seen is not None

def test_create_user(db_session):
    """Kullanıcı kaydı oluşturma ve sorgulamayı test eder."""
    user = User(username="testuser", password_hash="hashedpassword123")
    db_session.add(user)
    db_session.commit()
    
    db_user = db_session.query(User).filter_by(username="testuser").first()
    assert db_user is not None
    assert db_user.username == "testuser"
    assert db_user.password_hash == "hashedpassword123"
    assert db_user.created_at is not None

@patch("src.database.SessionLocal")
def test_init_db_does_not_create_default_admin(mock_session_class):
    """init_db fonksiyonunun artık otomatik admin kullanıcısı oluşturmadığını test eder."""
    # Test için geçici veritabanı
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    mock_session_class.return_value = session
    
    # DB boşken init_db çalıştır
    from src.database import init_db
    with patch("src.database.engine", engine), patch("src.database.DATABASE_URL", "sqlite:///:memory:"):
        init_db()
        
    # Kullanıcı kaydı olmadığını doğrula
    users = session.query(User).all()
    assert len(users) == 0

