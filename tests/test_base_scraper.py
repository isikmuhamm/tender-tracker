import pytest
from src.scraper.base import BaseScraper, SourceParseError

class DummyScraper(BaseScraper):
    def fetch(self):
        return "raw"
    def parse(self, raw_data):
        return []

def test_base_scraper_contract_normalization():
    scraper = DummyScraper(source_name="dummy")
    
    raw_items = [
        {
            "link": "https://example.com/1",
            "title": "Tender 1",
            "summary": "   Some summary   ",
            "category": "   Category 1   ",
            "source": "incorrect_source"
        }
    ]
    
    normalized = scraper.normalize_and_validate(raw_items, 1)
    assert len(normalized) == 1
    item = normalized[0]
    assert item["link"] == "https://example.com/1"
    assert item["title"] == "Tender 1"
    assert item["summary"] == "Some summary"
    assert item["category"] == "Category 1"
    assert item["source"] == "dummy"

def test_base_scraper_missing_fields_skipped():
    scraper = DummyScraper(source_name="dummy")
    
    raw_items = [
        {"title": "Title"},
        {"link": "https://example.com"},
        {"link": "ftp://example.com", "title": "Title"},
        {"link": "https://example.com/ok", "title": "Ok Title"}
    ]
    
    normalized = scraper.normalize_and_validate(raw_items, 4)
    assert len(normalized) == 1
    assert normalized[0]["link"] == "https://example.com/ok"

def test_base_scraper_all_invalid_raises_parse_error():
    scraper = DummyScraper(source_name="dummy")
    
    raw_items = [
        {"title": "Only Title"},
        {"link": "Only Link"}
    ]
    
    with pytest.raises(SourceParseError):
        scraper.normalize_and_validate(raw_items, 2)

def test_base_scraper_empty_response_passes():
    scraper = DummyScraper(source_name="dummy")
    normalized = scraper.normalize_and_validate([], 0)
    assert normalized == []

def test_base_scraper_response_internal_dedupe():
    scraper = DummyScraper(source_name="dummy")
    
    raw_items = [
        {"link": "https://example.com/1", "title": "Tender 1"},
        {"link": "https://example.com/1", "title": "Duplicate Tender 1"},
        {"link": "https://example.com/2", "title": "Tender 2"}
    ]
    
    normalized = scraper.normalize_and_validate(raw_items, 3)
    assert len(normalized) == 2
    assert normalized[0]["link"] == "https://example.com/1"
    assert normalized[1]["link"] == "https://example.com/2"
