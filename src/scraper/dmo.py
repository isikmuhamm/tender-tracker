import logging
from typing import List, Dict, Any
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper

logger = logging.getLogger(__name__)

class DmoScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="dmo")
        self.url = "https://www.dmo.gov.tr/Ihale/Liste?type=1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch(self) -> str:
        logger.info(f"DMO İhale Listesi HTML çekiliyor: {self.url}")
        logger.warning("TLS verification bypassed for DmoScraper for compatibility.")
        import warnings
        import urllib3
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
                r = requests.get(self.url, headers=self.headers, verify=False, timeout=30)
            r.raise_for_status()
            return r.text
        except Exception as e:
            logger.error(f"DMO İhale Listesi veri çekme hatası: {e}")
            return ""

    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        if not raw_data:
            return []
        
        soup = BeautifulSoup(raw_data, "html.parser")
        items = []
        rows = soup.find_all("tr")
        
        for tr in rows:
            a_elem = tr.find("a", href=lambda h: h and '/Ihale/Detay/' in h)
            if not a_elem:
                continue
                
            tds = tr.find_all("td")
            if len(tds) < 8:
                continue
                
            link = urljoin("https://www.dmo.gov.tr", a_elem["href"])
            tender_id = tds[1].get_text(strip=True)
            title = tds[3].get_text(strip=True)
            category = tds[4].get_text(strip=True)
            start_date = tds[5].get_text(strip=True)
            end_date = tds[6].get_text(strip=True)
            explanation = tds[7].get_text(strip=True)
            
            # Başlıktaki zeyilname uyarılarını temizle veya düzelt
            if explanation and title.startswith(explanation):
                # Başlık zaten durumu içeriyorsa tekrarı engellemek için temizlik yapılabilir
                pass
                
            summary = f"İhale No: {tender_id} | Yayın: {start_date} | Bitiş: {end_date}"
            if explanation:
                summary += f" | Durum: {explanation}"
                
            items.append({
                "link": link,
                "title": title,
                "summary": summary,
                "category": category,
                "source": self.source_name
            })
            
        # Çift kayıtları (aynı linki) kaldır
        unique_items = {}
        for item in items:
            unique_items[item["link"]] = item
            
        result = list(unique_items.values())
        logger.info(f"DMO İhaleleri ayrıştırıldı. Toplam {len(result)} benzersiz ihale bulundu.")
        return result
