import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base
from src.scheduler import TenderBotOrchestrator

@pytest.fixture
def mock_db_setup(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

@patch("src.scheduler.SessionLocal")
@patch("src.scheduler.init_db")
def test_status_scenarios(mock_init, mock_session_class, mock_db_setup, tmp_path):
    # Set up in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    mock_session_class.return_value = session

    # Config setup
    config_file = tmp_path / "config.yaml"
    config_file.write_text("settings: {enabled_scrapers: [yatirimlar, dmo]}", encoding="utf-8")

    # Scrapers mocks
    scraper_ok = MagicMock()
    scraper_ok.source_name = "yatirimlar"
    scraper_ok.get_new_items.return_value = [] # 0 records, successful run

    scraper_fail = MagicMock()
    scraper_fail.source_name = "dmo"
    scraper_fail.get_new_items.side_effect = Exception("Network error")

    # 1. Scenario: One source successful (0 records), other failed. Expected: partial
    orch = TenderBotOrchestrator(config_path=str(config_file))
    orch.scrapers = [scraper_ok, scraper_fail]
    orch.notifiers = []
    
    result = orch.run_once()
    assert result["status"] == "partial"
    assert result["successful_sources"] == 1
    assert result["failed_sources"] == 1
    assert result["records_added"] == 0

    # 2. Scenario: All sources failed. Expected: failed
    orch2 = TenderBotOrchestrator(config_path=str(config_file))
    orch2.scrapers = [scraper_fail]
    orch2.notifiers = []
    
    result2 = orch2.run_once()
    assert result2["status"] == "failed"
    assert result2["successful_sources"] == 0
    assert result2["failed_sources"] == 1

    # 3. Scenario: All sources successful, 0 records (all duplicates). Expected: success
    scraper_ok_with_items = MagicMock()
    scraper_ok_with_items.source_name = "yatirimlar"
    scraper_ok_with_items.get_new_items.return_value = [
        {"link": "http://existing.com", "title": "Title", "summary": "Sum", "category": "Cat", "source": "yatirimlar"}
    ]
    
    # We add the existing item to session first so it behaves as duplicate
    from src.database import Tender
    t = Tender(link="http://existing.com", title="Title", summary="Sum", category="Cat", source="yatirimlar")
    session.add(t)
    session.commit()

    orch3 = TenderBotOrchestrator(config_path=str(config_file))
    orch3.scrapers = [scraper_ok_with_items]
    orch3.notifiers = []
    
    result3 = orch3.run_once()
    assert result3["status"] == "success"
    assert result3["successful_sources"] == 1
    assert result3["failed_sources"] == 0
    assert result3["records_added"] == 0

    # 4. Scenario: Processing errors (record failing classification/save). Expected: partial
    scraper_fail_item = MagicMock()
    scraper_fail_item.source_name = "yatirimlar"
    scraper_fail_item.get_new_items.return_value = [
        {"link": "http://fail.com", "title": "Fail Title", "summary": "Sum", "category": "Cat", "source": "yatirimlar"},
        {"link": "http://ok.com", "title": "Ok Title", "summary": "Sum", "category": "Cat", "source": "yatirimlar"}
    ]

    orch4 = TenderBotOrchestrator(config_path=str(config_file))
    orch4.scrapers = [scraper_fail_item]
    orch4.notifiers = []
    
    # Mock classify to raise exception for fail.com and succeed for ok.com
    mock_classifier = MagicMock()
    def mock_classify(title, summary):
        if "Fail" in title:
            raise Exception("Classification failed")
        return ("Sector", "rule")
    mock_classifier.classify.side_effect = mock_classify
    
    with patch("src.scheduler.TenderClassifier", return_value=mock_classifier):
        result4 = orch4.run_once()
        
    assert result4["status"] == "partial"
    assert result4["successful_sources"] == 1
    assert result4["processing_errors"] == 1
    assert result4["records_added"] == 1
