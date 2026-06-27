import pytest
from unittest.mock import MagicMock, patch
from src.scraper.ilan_gov_tr import IlanGovTrScraper
from src.scraper.base import SourceFetchError, SourceParseError

@pytest.fixture
def sample_ilan_json():
    return {
        "success": True,
        "result": {
            "ads": [
                {
                    "id": "2143092",
                    "adNo": "ILN02492731",
                    "advertiserName": "VAN SU VE KANALİZASYON İDARESİ GENEL MÜDÜRLÜĞÜ",
                    "title": "Su deposu ve tesisatı işleri yaptırılacaktır"
                },
                {
                    "id": "2143099",
                    "adNo": "ILN02492799",
                    "advertiserName": "TCDD GENEL MÜDÜRLÜĞÜ",
                    "title": "Ray alımı ihalesi yapılacaktır"
                },
                # Geçersiz ilan (başlığı yok)
                {
                    "id": "2143100",
                    "adNo": "ILN02492800"
                }
            ],
            "totalCount": 2
        }
    }

def test_ilan_gov_tr_parser(sample_ilan_json):
    scraper = IlanGovTrScraper()
    items = scraper.parse(sample_ilan_json)
    
    assert len(items) == 2
    
    # 1. Öge Testi
    assert items[0]["link"] == "https://www.ilan.gov.tr/ilan/2143092"
    assert items[0]["title"] == "Su deposu ve tesisatı işleri yaptırılacaktır"
    assert items[0]["category"] == "İhale İlanı"
    assert items[0]["summary"] == "İlan No: ILN02492731 | Yayınlayan: VAN SU VE KANALİZASYON İDARESİ GENEL MÜDÜRLÜĞÜ"
    assert items[0]["source"] == "ilan_gov_tr"
    
    # 2. Öge Testi
    assert items[1]["link"] == "https://www.ilan.gov.tr/ilan/2143099"
    assert items[1]["title"] == "Ray alımı ihalesi yapılacaktır"
    assert items[1]["category"] == "İhale İlanı"
    assert items[1]["summary"] == "İlan No: ILN02492799 | Yayınlayan: TCDD GENEL MÜDÜRLÜĞÜ"
    assert items[1]["source"] == "ilan_gov_tr"

@patch("requests.post")
def test_ilan_gov_tr_fetch_pagination_basic(mock_post):
    # Mocking two pages: page 1 returns 30 items, page 2 returns 5 items
    resp1 = MagicMock()
    resp1.status_code = 200
    resp1.json.return_value = {
        "result": {
            "ads": [{"id": f"id_{i}", "title": f"Title {i}"} for i in range(30)],
            "totalCount": 35
        }
    }
    
    resp2 = MagicMock()
    resp2.status_code = 200
    resp2.json.return_value = {
        "result": {
            "ads": [{"id": f"id_{i}", "title": f"Title {i}"} for i in range(30, 35)],
            "totalCount": 35
        }
    }
    
    mock_post.side_effect = [resp1, resp2]
    
    scraper = IlanGovTrScraper()
    with patch("time.sleep"):
        raw_result = scraper.fetch()
        
    assert len(raw_result["result"]["ads"]) == 35
    assert mock_post.call_count == 2
    
    # Check payload parameters
    call_payload_1 = mock_post.call_args_list[0][1]["json"]
    call_payload_2 = mock_post.call_args_list[1][1]["json"]
    assert call_payload_1["skipCount"] == 0
    assert call_payload_2["skipCount"] == 30

@patch("requests.post")
def test_ilan_gov_tr_fetch_cycle_detected(mock_post):
    # Returns page 1 with 30 items, and page 2 returns exact same ids, causing a cycle loop error
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "result": {
            "ads": [{"id": f"id_{i}", "title": "Same Title"} for i in range(30)],
            "totalCount": 60
        }
    }
    mock_post.return_value = resp
    
    scraper = IlanGovTrScraper()
    with patch("time.sleep"):
        with pytest.raises(SourceFetchError) as exc:
            scraper.fetch()
        assert "sonsuz döngü" in str(exc.value)

@patch("requests.post")
def test_ilan_gov_tr_fetch_limit_exhausted(mock_post):
    # Always returns 30 items on page query, totalCount is 5000, 
    # hitting limit at page 100 before totalCount completed
    resp = MagicMock()
    resp.status_code = 200
    # generate unique IDs dynamically per call
    call_idx = 0
    def mock_json():
        nonlocal call_idx
        ads = [{"id": f"id_{call_idx}_{i}", "title": "Title"} for i in range(30)]
        call_idx += 1
        return {
            "result": {
                "ads": ads,
                "totalCount": 5000
            }
        }
        
    resp.json = mock_json
    mock_post.return_value = resp
    
    scraper = IlanGovTrScraper()
    with patch("time.sleep"):
        with pytest.raises(SourceFetchError) as exc:
            scraper.fetch()
        assert "sayfalama güvenlik sınırına" in str(exc.value)
