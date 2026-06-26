import logging
import ssl
from typing import List, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from .base import BaseScraper

logger = logging.getLogger(__name__)

class TLSAdapter(HTTPAdapter):
    """EKAPv2'nin SSL/TLS el sıkışma gereksinimleri için özel adaptör."""
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs['ssl_context'] = ctx
        return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)

class Ekapv2Scraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="ekapv2")
        self.url = "https://ekapv2.kik.gov.tr/ekap/search"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "tr,en-US;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        }

    def fetch(self) -> str:
        logger.info(f"EKAPv2 bağlantısı test ediliyor: {self.url}")
        session = requests.Session()
        session.headers.update(self.headers)
        session.verify = False
        session.mount("https://ekapv2.kik.gov.tr", TLSAdapter())
        
        try:
            r = session.get(self.url, timeout=20)
            r.raise_for_status()
            logger.info(f"EKAPv2 bağlantısı başarılı. HTTP Durumu: {r.status_code}")
            return r.text
        except Exception as e:
            logger.error(f"EKAPv2 bağlantı hatası: {e}")
            return ""

    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        # Sayfa Angular (SPA) yapısında olduğu için doğrudan statik HTML parse etmek veri getirmez.
        # Bu kısım gelecekteki oturum bazlı (Session/AJAX) geliştirmeler için taslak olarak bırakılmıştır.
        if raw_data:
            logger.debug("EKAPv2 HTML verisi alındı fakat dinamik (SPA) yapıda olduğu için pas geçildi.")
        return []
