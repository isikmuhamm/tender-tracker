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

@patch("src.scheduler.SessionLocal")
@patch("src.scheduler.init_db")
def test_orchestrator_excluded_only(mock_init, mock_session_class, mock_db_setup, tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    mock_session_class.return_value = session
    
    config_file = tmp_path / "config.yaml"
    config_content = """
    settings:
      enabled_scrapers:
        - "yatirimlar"
    filters:
      exclude_keywords:
        - "satılık"
        - "kiralık"
    """
    config_file.write_text(config_content, encoding="utf-8")
    
    orch = TenderBotOrchestrator(config_path=str(config_file))
    orch.scrapers = [MagicMock()]
    orch.scrapers[0].source_name = "yatirimlar"
    orch.scrapers[0].get_new_items.return_value = [
        {
            "link": "https://example.com/satilik-bina",
            "title": "Satılık Eski Bina",
            "summary": "Bina",
            "category": "Satış",
            "source": "yatirimlar"
        }
    ]
    
    orch.notifiers = []
    orch.run_once()
    
    db_tenders = session.query(Tender).all()
    assert len(db_tenders) == 1
    assert db_tenders[0].sector == "Excluded"

@patch("src.scheduler.SessionLocal")
@patch("src.scheduler.init_db")
def test_orchestrator_notifier_disabled(mock_init, mock_session_class, mock_db_setup, tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    mock_session_class.return_value = session
    
    config_file = tmp_path / "config.yaml"
    config_content = "settings: {enabled_scrapers: [yatirimlar]}"
    config_file.write_text(config_content, encoding="utf-8")
    
    orch = TenderBotOrchestrator(config_path=str(config_file))
    orch.scrapers = [MagicMock()]
    orch.scrapers[0].source_name = "yatirimlar"
    orch.scrapers[0].get_new_items.return_value = [
        {
            "link": "https://example.com/tender",
            "title": "Tender Title",
            "summary": "Summary",
            "category": "Cat",
            "source": "yatirimlar"
        }
    ]
    orch.notifiers = []
    
    with patch("src.scheduler.TenderClassifier") as mock_class_type:
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = ("Construction", "rule")
        mock_class_type.return_value = mock_classifier
        
        orch.run_once()
        
    db_tenders = session.query(Tender).all()
    assert len(db_tenders) == 1
    assert db_tenders[0].sector == "Construction"

@patch("src.scheduler.SessionLocal")
@patch("src.scheduler.init_db")
def test_orchestrator_notifier_failed(mock_init, mock_session_class, mock_db_setup, tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    mock_session_class.return_value = session
    
    config_file = tmp_path / "config.yaml"
    config_content = "settings: {enabled_scrapers: [yatirimlar]}"
    config_file.write_text(config_content, encoding="utf-8")
    
    orch = TenderBotOrchestrator(config_path=str(config_file))
    orch.scrapers = [MagicMock()]
    orch.scrapers[0].source_name = "yatirimlar"
    orch.scrapers[0].get_new_items.return_value = [
        {
            "link": "https://example.com/t1",
            "title": "Tender 1",
            "summary": "Summary",
            "category": "Cat",
            "source": "yatirimlar"
        }
    ]
    
    mock_email = MagicMock()
    mock_email.name = "email"
    mock_email.send_notification.side_effect = Exception("SMTP Connection Failed")
    orch.notifiers = [mock_email]
    
    with patch("src.scheduler.TenderClassifier") as mock_class_type:
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = ("IT", "rule")
        mock_class_type.return_value = mock_classifier
        
        orch.run_once()
        
    db_tenders = session.query(Tender).all()
    assert len(db_tenders) == 1
    assert db_tenders[0].sector == "IT"
    assert db_tenders[0].email_sent is False

@patch("src.scheduler.SessionLocal")
@patch("src.scheduler.init_db")
def test_orchestrator_partial_source_failure(mock_init, mock_session_class, mock_db_setup, tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    mock_session_class.return_value = session
    
    config_file = tmp_path / "config.yaml"
    config_content = "settings: {enabled_scrapers: [yatirimlar, dmo]}"
    config_file.write_text(config_content, encoding="utf-8")
    
    orch = TenderBotOrchestrator(config_path=str(config_file))
    
    scraper_ok = MagicMock()
    scraper_ok.source_name = "yatirimlar"
    scraper_ok.get_new_items.return_value = [
        {
            "link": "https://example.com/ok",
            "title": "Good Tender",
            "summary": "Summary",
            "category": "Cat",
            "source": "yatirimlar"
        }
    ]
    
    scraper_fail = MagicMock()
    scraper_fail.source_name = "dmo"
    scraper_fail.get_new_items.side_effect = Exception("Scraper network error")
    
    orch.scrapers = [scraper_ok, scraper_fail]
    orch.notifiers = []
    
    with patch("src.scheduler.TenderClassifier") as mock_class_type:
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = ("Medical", "rule")
        mock_class_type.return_value = mock_classifier
        
        orch.run_once()
        
    db_tenders = session.query(Tender).all()
    assert len(db_tenders) == 1
    assert db_tenders[0].link == "https://example.com/ok"
