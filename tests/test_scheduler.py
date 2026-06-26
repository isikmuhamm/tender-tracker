import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, Tender
from src.scheduler import TenderBotOrchestrator

@pytest.fixture
def mock_db_setup(monkeypatch):
    # test.db gibi in-memory db URL'si ayarla
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

@patch("src.scheduler.SessionLocal")
@patch("src.scheduler.init_db")
def test_orchestrator_run_once(mock_init, mock_session_class, mock_db_setup, tmp_path):
    # İn-memory DB kuralım
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    mock_session_class.return_value = session
    
    # Geçici config dosyası oluştur
    config_file = tmp_path / "config.yaml"
    config_content = """
    settings:
      enabled_scrapers:
        - "yatirimlar"
    global_filters:
      exclude_keywords:
        - "satılık"
    """
    config_file.write_text(config_content, encoding="utf-8")
    
    # Geçici sektör dosyası oluştur
    sectors_file = tmp_path / "sectors.yaml"
    sectors_content = """
    Demiryolu:
      keywords:
        - "tcdd"
    """
    sectors_file.write_text(sectors_content, encoding="utf-8")
    
    # Sınıflandırıcıyı bu geçici sektör dosyasına yönlendirelim
    with patch("src.scheduler.TenderClassifier") as mock_class_type:
        mock_classifier = MagicMock()
        mock_classifier.classify.side_effect = lambda t, s: ("Demiryolu", "rule") if "tcdd" in t.lower() else (None, "none")
        mock_class_type.return_value = mock_classifier
        
        orch = TenderBotOrchestrator(config_path=str(config_file))
        orch.scrapers = [MagicMock()]
        orch.scrapers[0].source_name = "yatirimlar"
        
        # Scraper'dan dönecek sahte ihaleler
        orch.scrapers[0].get_new_items.return_value = [
            # 1. Eşleşen ihale
            {
                "link": "https://example.com/tcdd-ihalesi",
                "title": "TCDD Ray Yenileme İhalesi",
                "summary": "Ray alımı",
                "category": "Yapım",
                "source": "yatirimlar"
            },
            # 2. Elenen ihale (satılık geçiyor)
            {
                "link": "https://example.com/satilik-bina",
                "title": "Satılık Eski TCDD Binası",
                "summary": "Bina",
                "category": "Satış",
                "source": "yatirimlar"
            }
        ]
        
        # Notifier'ları mocklayalım
        mock_email = MagicMock()
        mock_email.name = "email"
        mock_email.send_notification.return_value = True
        
        mock_tg = MagicMock()
        mock_tg.name = "telegram"
        mock_tg.send_notification.return_value = True
        
        orch.notifiers = [mock_email, mock_tg]
        
        # Orkestratörü çalıştır
        orch.run_once()
        
        # DB kayıtlarını incele
        db_tenders = session.query(Tender).all()
        assert len(db_tenders) == 2  # Elenen de döküm olarak kaydedilmeli
        
        tcdd_tender = session.query(Tender).filter_by(link="https://example.com/tcdd-ihalesi").first()
        assert tcdd_tender is not None
        assert tcdd_tender.sector == "Demiryolu"
        assert tcdd_tender.email_sent is True
        assert tcdd_tender.telegram_sent is True
        
        excluded_tender = session.query(Tender).filter_by(link="https://example.com/satilik-bina").first()
        assert excluded_tender is not None
        assert excluded_tender.sector == "Excluded"
        assert excluded_tender.email_sent is True  # Elenenler bildirilmeyeceği için True
        assert excluded_tender.telegram_sent is True
        
        # Notifier'ların çağrıldığını doğrula
        mock_email.send_notification.assert_called_once()
        mock_tg.send_notification.assert_called_once()
