import pytest
from src.scraper.ilan_gov_tr import IlanGovTrScraper

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
            ]
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
