import os
import logging
import yaml
from src.classifier import matches_keyword

logger = logging.getLogger(__name__)

class TenderFilter:
    """
    İhaleleri küresel kurallara (örneğin kiralık/satılık filtreleri) göre eleyen sınıf.
    """
    def __init__(self, config_path: str = None):
        from src.database import get_data_path
        self.config_path = config_path or get_data_path("config.yaml")
        self.exclude_keywords = []
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            logger.warning(f"Yapılandırma dosyası bulunamadı: {self.config_path}. Dışlama kuralları boş geçilecek.")
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                if config:
                    if "filters" in config:
                        self.exclude_keywords = config["filters"].get("exclude_keywords", [])
                    elif "global_filters" in config:
                        self.exclude_keywords = config["global_filters"].get("exclude_keywords", [])
            logger.info(f"Küresel filtreler yüklendi. {len(self.exclude_keywords)} adet dışlama kelimesi tanımlı.")
        except Exception as e:
            logger.error(f"Filtre yapılandırması yüklenirken hata: {e}")

    def is_excluded(self, title: str, summary: str = "") -> bool:
        """
        İhale başlığı veya açıklamasında dışlama kelimelerinden biri geçiyorsa True döner.
        """
        t = title.lower()
        s = (summary or "").lower()
        
        for kw in self.exclude_keywords:
            if matches_keyword(kw, t) or matches_keyword(kw, s):
                logger.info(f"İhale elendi. Eşleşen kelime: '{kw.lower()}' | Başlık: '{title}'")
                return True
        return False
