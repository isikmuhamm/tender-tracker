import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, Tender

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
