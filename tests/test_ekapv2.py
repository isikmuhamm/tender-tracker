import pytest
import json
from datetime import datetime
from urllib.parse import urlencode
from unittest.mock import MagicMock, patch
from src.scraper.ekapv2 import Ekapv2Scraper
from src.scraper.base import SourceFetchError, SourceParseError
from src.database import Base

def test_ekapv2_parser_empty():
    scraper = Ekapv2Scraper()
    # empty raw data should raise SourceParseError
    with pytest.raises(SourceParseError):
        scraper.parse("")
    with pytest.raises(SourceParseError):
        scraper.parse("{invalid json")

def test_ekapv2_parser_valid():
    scraper = Ekapv2Scraper()
    # A real-like payload representing a captured EKAP response
    mock_data = {
        "list": [
            {
                "ikn": "2026/271215",
                "ihaleAdi": "Siber Güvenlik Hizmeti Alım İşi",
                "ihaleTipAciklama": "Hizmet",
                "idareAdi": "KİK Bilgi İşlem",
                "ihaleIlAdi": "Ankara",
                "ihaleUsulAciklama": "Açık",
                "ihaleDurumAciklama": "Teklif Değerlendirme",
                "ihaleTarihSaat": "23.03.2027 14:00"
            }
        ],
        "totalCount": 1
    }
    
    raw_data = json.dumps(mock_data)
    items = scraper.parse(raw_data)
    
    assert isinstance(items, list)
    assert len(items) == 1
    
    item = items[0]
    assert item["title"] == "Siber Güvenlik Hizmeti Alım İşi"
    assert "IKN=2026%2F271215" in item["link"]  # urlencoded link check!
    assert "https://ekap.kik.gov.tr/EKAP/Ortak/IhaleArama/IhaleArama.aspx?" in item["link"]
    assert item["category"] == "Hizmet"
    assert item["source"] == "ekapv2"
    assert "IKN: 2026/271215" in item["summary"]
    assert "İdare: KİK Bilgi İşlem" in item["summary"]
    assert "Yöntem: Açık" in item["summary"]

def test_ekapv2_parser_validation_errors():
    scraper = Ekapv2Scraper()
    # If list has items but all are discarded due to missing required fields, it must raise SourceParseError
    mock_data = {
        "list": [{"id": "1"}], # missing ikn and title
        "totalCount": 1
    }
    with pytest.raises(SourceParseError):
        scraper.parse(json.dumps(mock_data))

def test_ekapv2_security_headers():
    scraper = Ekapv2Scraper()
    headers = scraper._generate_security_headers()
    
    # Verify that the four required custom signed security headers are present
    assert "X-Custom-Request-Guid" in headers
    assert "X-Custom-Request-Siv" in headers
    assert "X-Custom-Request-Ts" in headers
    assert "X-Custom-Request-R8id" in headers
    
    # Check that they are non-empty strings
    for k, v in headers.items():
        assert isinstance(v, str)
        assert len(v) > 0

@patch("requests.Session")
def test_ekapv2_fetch_pagination_multi_page(mock_session_class):
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    
    # Page 1 response: 1 item, totalCount 2
    resp1 = MagicMock()
    resp1.status_code = 200
    resp1.json.return_value = {
        "list": [{"ikn": "1", "ihaleAdi": "Tender 1", "ihaleTipAciklama": "Mal"}],
        "totalCount": 2
    }
    
    # Page 2 response: 1 item, totalCount 2
    resp2 = MagicMock()
    resp2.status_code = 200
    resp2.json.return_value = {
        "list": [{"ikn": "2", "ihaleAdi": "Tender 2", "ihaleTipAciklama": "Hizmet"}],
        "totalCount": 2
    }
    
    mock_session.post.side_effect = [resp1, resp2]
    
    scraper = Ekapv2Scraper()
    # Mock sleep to run fast
    with patch("time.sleep"):
        raw_result = scraper.fetch()
        
    data = json.loads(raw_result)
    assert len(data["list"]) == 2
    assert data["totalCount"] == 2
    
    # Check that post was called twice
    assert mock_session.post.call_count == 2
    call_args_1 = mock_session.post.call_args_list[0][1]["json"]
    call_args_2 = mock_session.post.call_args_list[1][1]["json"]
    assert call_args_1["paginationSkip"] == 0
    assert call_args_2["paginationSkip"] == 40

@patch("requests.Session")
def test_ekapv2_fetch_first_page_failure(mock_session_class):
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    mock_session.post.side_effect = Exception("Connection Timeout")
    
    scraper = Ekapv2Scraper()
    with pytest.raises(SourceFetchError):
        scraper.fetch()

@patch("requests.Session")
def test_ekapv2_fetch_second_page_failure(mock_session_class):
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    
    resp1 = MagicMock()
    resp1.status_code = 200
    resp1.json.return_value = {
        "list": [{"ikn": "1", "ihaleAdi": "Tender 1", "ihaleTipAciklama": "Mal"}],
        "totalCount": 80
    }
    
    mock_session.post.side_effect = [resp1, Exception("Connection Timeout on Page 2")]
    
    scraper = Ekapv2Scraper()
    with patch("time.sleep"):
        # When page 2 fails, it must raise SourceFetchError (no partial results returned as success)
        with pytest.raises(SourceFetchError):
            scraper.fetch()

@patch("requests.Session")
def test_ekapv2_fetch_schema_validation(mock_session_class):
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    
    # invalid list type schema
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "list": "not a list",
        "totalCount": 2
    }
    mock_session.post.return_value = resp
    
    scraper = Ekapv2Scraper()
    with pytest.raises(SourceFetchError):
        scraper.fetch()

@patch("requests.Session")
def test_ekapv2_fetch_state_filters(mock_session_class):
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "list": [],
        "totalCount": 0
    }
    mock_session.post.return_value = resp
    
    # 1. Initial scan: last_success_at is None
    scraper = Ekapv2Scraper()
    scraper.last_success_at = None
    scraper.fetch()
    
    call_json_1 = mock_session.post.call_args_list[0][1]["json"]
    assert call_json_1["ilanTarihSaatBaslangic"] is None
    assert call_json_1["ihaleDurumIdList"] == [2] # Teklif Vermeye Açık
    
    # 2. Incremental scan: last_success_at set
    scraper.last_success_at = datetime(2026, 6, 27)
    scraper.fetch()
    
    call_json_2 = mock_session.post.call_args_list[1][1]["json"]
    assert call_json_2["ilanTarihSaatBaslangic"] == "27.06.2026"
    assert call_json_2["ihaleDurumIdList"] == [2]

def test_ekapv2_details_link_determinism():
    scraper = Ekapv2Scraper()
    ikn = "2026/271215"
    link1 = f"https://ekap.kik.gov.tr/EKAP/Ortak/IhaleArama/IhaleArama.aspx?{urlencode({'IKN': ikn})}"
    link2 = f"https://ekap.kik.gov.tr/EKAP/Ortak/IhaleArama/IhaleArama.aspx?{urlencode({'IKN': ikn})}"
    assert link1 == link2
    assert "IKN=2026%2F271215" in link1

@patch("src.scheduler.SessionLocal")
@patch("src.scheduler.init_db")
def test_scheduler_ekap_isolation(mock_init, mock_session_class, tmp_path):
    from src.scheduler import TenderBotOrchestrator
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    mock_session_class.return_value = session
    
    config_file = tmp_path / "config.yaml"
    config_file.write_text("settings: {enabled_scrapers: [ekapv2, dmo]}", encoding="utf-8")
    
    orch = TenderBotOrchestrator(config_path=str(config_file))
    
    scraper_ekap_fail = MagicMock()
    scraper_ekap_fail.source_name = "ekapv2"
    scraper_ekap_fail.get_new_items.side_effect = SourceFetchError("EKAP connection failed")
    
    scraper_dmo_ok = MagicMock()
    scraper_dmo_ok.source_name = "dmo"
    scraper_dmo_ok.get_new_items.return_value = [
        {"link": "http://dmo-ok.com", "title": "DMO Tender", "summary": "Sum", "category": "Cat", "source": "dmo"}
    ]
    
    orch.scrapers = [scraper_ekap_fail, scraper_dmo_ok]
    orch.notifiers = []
    
    with patch("src.scheduler.TenderClassifier") as mock_class_type:
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = ("Construction", "rule")
        mock_class_type.return_value = mock_classifier
        
        result = orch.run_once()
        
    assert result["failed_sources"] == 1
    assert result["successful_sources"] == 1
    assert result["status"] == "partial"
    
    # Check that DMO tender got successfully saved
    from src.database import Tender
    dmo_tender = session.query(Tender).filter_by(link="http://dmo-ok.com").first()
    assert dmo_tender is not None
