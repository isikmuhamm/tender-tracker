from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SourceFetchError(Exception):
    """Veri çekme işlemi sırasında hata oluştuğunda fırlatılır."""
    pass

class SourceParseError(Exception):
    """Veri ayrıştırma işlemi sırasında hata oluştuğunda fırlatılır."""
    pass

class BaseScraper(ABC):
    """
    Tüm ihale kazıyıcı adaptörler için temel soyut sınıf.
    """

    def __init__(self, source_name: str):
        self.source_name = source_name

    @abstractmethod
    def fetch(self) -> Any:
        """
        Hedef web sayfasından veya API'den veri çeker.
        Ham HTML veya JSON verisi döner.
        """
        pass

    @abstractmethod
    def parse(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Ham veriyi ayrıştırır ve standart ihale sözlüğü listesine dönüştürür.
        
        Standart Sözlük Yapısı:
        {
            "link": str,          # İhalenin benzersiz URL'si
            "title": str,         # İhale başlığı
            "summary": str,       # İhale açıklaması veya özeti (isteğe bağlı)
            "category": str,      # Kaynak üzerindeki orijinal kategori
            "source": str         # Kaynak adı (örn. 'yatirimlar')
        }
        """
        pass

    def normalize_and_validate(self, items: List[Dict[str, Any]], parsed_count: int) -> List[Dict[str, Any]]:
        """
        Scraper çıktısını normalize eder ve doğrular.
        - link ve title alanları zorunludur ve boş olamaz.
        - link alanı geçerli bir URL olmalıdır.
        - summary ve category alanları string olmalıdır (yoksa boş string).
        - source alanı scraper.source_name ile aynı olmalıdır.
        - whitespace temizliği yapılır.
        - response içindeki mükerrer linkler tekilleştirilir.
        - Kayıt geldiği halde normalizasyon sonunda sıfır kayıt kalırsa SourceParseError fırlatır.
        """
        seen_links = set()
        validated_items = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning(f"[{self.source_name}] Kayıt sözlük nesnesi değil, atlanıyor: {item}")
                continue
            
            link = item.get("link")
            title = item.get("title")
            
            if not link or not isinstance(link, str) or not link.strip():
                logger.warning(f"[{self.source_name}] Kayıt linki eksik veya geçersiz, atlanıyor: {item}")
                continue
                
            if not title or not isinstance(title, str) or not title.strip():
                logger.warning(f"[{self.source_name}] Kayıt başlığı eksik veya geçersiz, atlanıyor: {item}")
                continue
                
            link_clean = link.strip()
            if not (link_clean.startswith("http://") or link_clean.startswith("https://")):
                logger.warning(f"[{self.source_name}] Kayıt linki geçerli bir URL değil, atlanıyor: {link_clean}")
                continue
                
            if link_clean in seen_links:
                continue
            seen_links.add(link_clean)
            
            summary = item.get("summary")
            if not isinstance(summary, str):
                summary = ""
            
            category = item.get("category")
            if not isinstance(category, str):
                category = ""
            
            validated_items.append({
                "link": link_clean,
                "title": title.strip(),
                "summary": summary.strip(),
                "category": category.strip(),
                "source": self.source_name
            })
            
        if parsed_count > 0 and not validated_items:
            raise SourceParseError(f"[{self.source_name}] Gelen kayıtlar eksik zorunlu alanlar (link/title) veya normalizasyon hataları nedeniyle elendi.")
            
        return validated_items

    def get_new_items(self) -> List[Dict[str, Any]]:
        """
        Veri çekme ve ayrıştırma işlemlerini sırayla çalıştırır.
        """
        raw_data = self.fetch()
        if not raw_data:
            return []
        items = self.parse(raw_data)
        parsed_count = len(items) if isinstance(items, list) else 0
        return self.normalize_and_validate(items, parsed_count)
