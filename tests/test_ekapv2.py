import pytest
from src.scraper.ekapv2 import Ekapv2Scraper

def test_ekapv2_parser():
    scraper = Ekapv2Scraper()
    items = scraper.parse("<html><web-root></web-root></html>")
    assert isinstance(items, list)
    assert len(items) == 0
