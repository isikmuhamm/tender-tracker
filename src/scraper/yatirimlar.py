import logging
from typing import List, Dict, Any
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper, SourceFetchError, SourceParseError

logger = logging.getLogger(__name__)

class YatirimlarScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="yatirimlar")
        self.url = "https://yatirimlar.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch(self) -> str:
        logger.info(f"Yatırımlar Dergisi HTML çekiliyor: {self.url}")
        try:
            r = requests.get(self.url, headers=self.headers, timeout=30)
            r.raise_for_status()
            return r.text
        except Exception as e:
            raise SourceFetchError(f"Yatırımlar Dergisi veri çekme hatası: {e}")

    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        if not raw_data:
            raise SourceParseError("Yatırımlar Dergisi boş veri döndü.")
        
        try:
            soup = BeautifulSoup(raw_data, "html.parser")
            items = []
            links = soup.select("a[href*='/haber/']")
            
            for a in links:
                title = a.get_text(strip=True)
                link = a["href"]
                
                if not title or len(title) < 10:
                    continue
                    
                # Göreli URL'leri mutlak URL'ye dönüştür
                if not link.startswith("http"):
                    link = urljoin(self.url, link)
                    
                container = a.find_parent(["div", "article"])
                if not container:
                    continue
                    
                cat_elem = container.select_one(".post-category")
                category = cat_elem.get_text(strip=True) if cat_elem else ""
                
                p_elem = container.find("p")
                summary = p_elem.get_text(strip=True) if p_elem else ""
                
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
            logger.info(f"Yatırımlar Dergisi ayrıştırıldı. Toplam {len(result)} benzersiz haber bulundu.")
            return result
        except Exception as e:
            raise SourceParseError(f"Yatırımlar Dergisi veri ayrıştırma hatası: {e}")
