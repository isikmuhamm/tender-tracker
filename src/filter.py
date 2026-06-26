import os
import logging
import yaml

logger = logging.getLogger(__name__)

class TenderFilter:
    """
    İhaleleri küresel kurallara (örneğin kiralık/satılık filtreleri) göre eleyen sınıf.
    """
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.exclude_keywords = []
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            logger.warning(f"Yapılandırma dosyası bulunamadı: {self.config_path}. Dışlama kuralları boş geçilecek.")
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                if config and "global_filters" in config:
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
            kw_lower = kw.lower()
            if kw_lower in t or kw_lower in s:
                logger.info(f"İhale elendi. Eşleşen kelime: '{kw_lower}' | Başlık: '{title}'")
                return True
        return False
