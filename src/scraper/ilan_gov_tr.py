import logging
import time
import requests
import warnings
import urllib3
from typing import List, Dict, Any
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
        
        all_ads = []
        page = 0
        take = 30
        max_pages = 100
        seen_ids = set()
        
        logger.warning("TLS verification bypassed for IlanGovTrScraper for compatibility.")
        
        while page < max_pages:
            skip = page * take
            payload = {
                "keys": {
                    "txv": [9]  # İhale duyuruları kategorisi
                },
                "skipCount": skip,
                "maxResultCount": take
            }
            
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
                    r = requests.post(self.url, json=payload, headers=self.headers, timeout=20, verify=False)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                raise SourceFetchError(f"ilan.gov.tr API sorgulama hatası (Sayfa {page}): {e}")
                
            # Şema Doğrulaması
            if not isinstance(data, dict):
                raise SourceFetchError(f"ilan.gov.tr API yanıtı sözlük nesnesi değil (Sayfa {page})")
            if "result" not in data or not isinstance(data["result"], dict):
                raise SourceFetchError(f"ilan.gov.tr API yanıtında 'result' alanı eksik veya geçersiz (Sayfa {page})")
            if "ads" not in data["result"] or not isinstance(data["result"]["ads"], list):
                raise SourceFetchError(f"ilan.gov.tr API yanıtında 'result.ads' alanı eksik veya geçersiz (Sayfa {page})")
                
            result_data = data["result"]
            ads = result_data["ads"]
            total_count = int(result_data.get("totalCount", 0))
            
            if total_count > 0 and not ads and page == 0:
                raise SourceFetchError("ilan.gov.tr API ilk sayfada kayıt dönmedi, totalCount sıfırdan büyük olmasına rağmen.")
                
            if not ads:
                break
                
            # Döngü/Tekrarlama Kontrolü (Cycle Detection)
            page_ids = {ad.get("id") for ad in ads if ad.get("id") is not None}
            if page_ids and page_ids.issubset(seen_ids):
                raise SourceFetchError("ilan.gov.tr API aynı kayıt kimliklerini içeren tekrarlı sayfa yanıtı döndü (sonsuz döngü tespit edildi).")
            seen_ids.update(page_ids)
            
            all_ads.extend(ads)
            
            if total_count > 0 and len(all_ads) >= total_count:
                break
                
            if len(ads) < take:
                break
                
            page += 1
            if page >= max_pages:
                if total_count > 0 and len(all_ads) < total_count:
                    raise SourceFetchError("ilan.gov.tr sayfalama güvenlik sınırına ulaşıldı fakat tüm ilanlar çekilemedi.")
                break
                
            time.sleep(0.2)
            
        return {"result": {"ads": all_ads}}

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
                
            logger.info(f"ilan.gov.tr API ayrıştırıldı. Toplam {len(items)} ilan bulundu.")
            return items
        except Exception as e:
            raise SourceParseError(f"ilan.gov.tr API ayrıştırma hatası: {e}")
