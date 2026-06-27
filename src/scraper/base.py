from abc import ABC, abstractmethod
from typing import List, Dict, Any

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

    def get_new_items(self) -> List[Dict[str, Any]]:
        """
        Veri çekme ve ayrıştırma işlemlerini sırayla çalıştırır.
        """
        raw_data = self.fetch()
        if not raw_data:
            return []
        return self.parse(raw_data)
