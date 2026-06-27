import pytest
import json
from src.scraper.ekapv2 import Ekapv2Scraper

def test_ekapv2_parser_empty():
    scraper = Ekapv2Scraper()
    assert scraper.parse("") == []
    assert scraper.parse("{}") == []
    assert scraper.parse("{invalid json") == []

def test_ekapv2_parser_valid():
    scraper = Ekapv2Scraper()
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
    assert "2026/271215" in item["link"]
    assert "https://ekap.kik.gov.tr" in item["link"]
    assert item["category"] == "Hizmet"
    assert item["source"] == "ekapv2"
    assert "IKN: 2026/271215" in item["summary"]
    assert "İdare: KİK Bilgi İşlem" in item["summary"]
    assert "Yöntem: Açık" in item["summary"]
