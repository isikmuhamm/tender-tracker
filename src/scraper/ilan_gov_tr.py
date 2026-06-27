import logging
from typing import List, Dict, Any
import requests
from .base import BaseScraper, SourceFetchError, SourceParseError

logger = logging.getLogger(__name__)

class IlanGovTrScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="ilan_gov_tr")
        self.url = "https://www.ilan.gov.tr/api/api/services/app/Ad/AdsByFilter"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*"
        }

    def fetch(self) -> dict:
        logger.info("ilan.gov.tr API'sinden güncel ilanlar çekiliyor...")
        payload = {
            "keys": {
                "txv": [9]  # İhale duyuruları kategorisi
            },
            "skipCount": 0,
            "maxResultCount": 30
        }
        logger.warning("TLS verification bypassed for IlanGovTrScraper for compatibility.")
        import warnings
        import urllib3
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
                r = requests.post(self.url, json=payload, headers=self.headers, timeout=20, verify=False)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            raise SourceFetchError(f"ilan.gov.tr API sorgulama hatası: {e}")

    def parse(self, raw_data: dict) -> List[Dict[str, Any]]:
        if not raw_data or "result" not in raw_data or "ads" not in raw_data["result"]:
            raise SourceParseError("ilan.gov.tr API yanıtı geçersiz veya boş.")
            
        try:
            ads = raw_data["result"]["ads"]
            items = []
            
            for ad in ads:
                ad_id = ad.get("id")
                title = ad.get("title")
                
                if not ad_id or not title:
                    continue
                    
                link = f"https://www.ilan.gov.tr/ilan/{ad_id}"
                ad_no = ad.get("adNo", "")
                advertiser = ad.get("advertiserName", "")
                
                summary = f"İlan No: {ad_no}"
                if advertiser:
                    summary += f" | Yayınlayan: {advertiser}"
                    
                items.append({
                    "link": link,
                    "title": title,
                    "summary": summary,
                    "category": "İhale İlanı",
                    "source": self.source_name
                })
                
            # Çift kayıtları (aynı linki) kaldır
            unique_items = {}
            for item in items:
                unique_items[item["link"]] = item
                
            result = list(unique_items.values())
            logger.info(f"ilan.gov.tr API ayrıştırıldı. Toplam {len(result)} benzersiz ilan bulundu.")
            return result
        except Exception as e:
            raise SourceParseError(f"ilan.gov.tr API ayrıştırma hatası: {e}")
