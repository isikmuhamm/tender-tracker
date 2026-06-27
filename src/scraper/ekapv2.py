import logging
import ssl
import os
import uuid
import base64
import time
import json
import warnings
import urllib3
from typing import List, Dict, Any
from urllib.parse import quote
import requests
from requests.adapters import HTTPAdapter
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as crypto_padding
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
        self.url = "https://ekapv2.kik.gov.tr/b_ihalearama/api/Ihale/GetListByParameters"
        self.headers = {
            'Accept': 'application/json',
            'Accept-Language': 'tr',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Origin': 'https://ekapv2.kik.gov.tr',
            'Referer': 'https://ekapv2.kik.gov.tr/ekap/search',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'api-version': 'v1'
        }
        self._r8fact_key = b'Qm2LtXR0aByP69vZNKef4wMJ'

    def _aes_cbc_encrypt(self, plaintext: str, key: bytes, iv: bytes) -> bytes:
        padder = crypto_padding.PKCS7(128).padder()
        padded = padder.update(plaintext.encode('utf-8')) + padder.finalize()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        enc = cipher.encryptor()
        return enc.update(padded) + enc.finalize()

    def _generate_security_headers(self) -> Dict[str, str]:
        guid = str(uuid.uuid4())
        iv = os.urandom(16)
        ts_ms = str(int(time.time() * 1000))

        r8id = base64.b64encode(self._aes_cbc_encrypt(guid, self._r8fact_key, iv)).decode('utf-8')
        ts_enc = base64.b64encode(self._aes_cbc_encrypt(ts_ms, self._r8fact_key, iv)).decode('utf-8')
        siv = base64.b64encode(iv).decode('utf-8')

        return {
            'X-Custom-Request-Guid': guid,
            'X-Custom-Request-Siv': siv,
            'X-Custom-Request-Ts': ts_enc,
            'X-Custom-Request-R8id': r8id,
        }

    def fetch(self) -> str:
        logger.info(f"EKAPv2 ihaleleri çekiliyor: {self.url}")
        logger.warning("TLS verification bypassed for Ekapv2Scraper for compatibility.")
        
        session = requests.Session()
        session.headers.update(self.headers)
        try:
            session.headers.update(self._generate_security_headers())
        except Exception as e:
            logger.error(f"EKAPv2 güvenlik başlıkları oluşturulamadı: {e}")
            return ""
            
        session.verify = False
        session.mount("https://ekapv2.kik.gov.tr", TLSAdapter())
        
        # En güncel ihaleleri çekmek için arama parametreleri
        api_params = {
            "searchText": "",
            "filterType": None,
            "ikNdeAra": True,
            "ihaleAdindaAra": True,
            "ihaleIlanindaAra": True,
            "teknikSartnamedeAra": True,
            "idariSartnamedeAra": True,
            "benzerIsMaddesindeAra": True,
            "isinYapilacagiYerMaddesindeAra": True,
            "nitelikTurMiktarMaddesindeAra": True,
            "ihaleBilgilerindeAra": True,
            "sozlesmeTasarisindaAra": True,
            "teklifCetvelindeAra": True,
            "searchType": "GirdigimGibi",
            "iknYili": None,
            "iknSayi": None,
            "ihaleTarihSaatBaslangic": None,
            "ihaleTarihSaatBitis": None,
            "ilanTarihSaatBaslangic": None,
            "ilanTarihSaatBitis": None,
            "yasaKapsami4734List": [],
            "ihaleTuruIdList": [],
            "ihaleUsulIdList": [],
            "ihaleUsulAltIdList": [],
            "ihaleIlIdList": [],
            "ihaleDurumIdList": [],
            "idareIdList": [],
            "ihaleIlanTuruIdList": [],
            "teklifTuruIdList": [],
            "asiriDusukTeklifIdList": [],
            "istisnaMaddeIdList": [],
            "okasBransKodList": [],
            "okasBransAdiList": [],
            "titubbKodList": [],
            "gmdnKodList": [],
            "eIhale": None,
            "eEksiltmeYapilacakMi": None,
            "ortakAlimMi": None,
            "kismiTeklifMi": None,
            "fiyatDisiUnsurVarmi": None,
            "ekonomikVeMaliYeterlilikBelgeleriIsteniyorMu": None,
            "meslekiTeknikYeterlilikBelgeleriIsteniyorMu": None,
            "isDeneyimiGosterenBelgelerIsteniyorMu": None,
            "yerliIstekliyeFiyatAvantajiUgulaniyorMu": None,
            "yabanciIsteklilereIzinVeriliyorMu": None,
            "alternatifTeklifVerilebilirMi": None,
            "konsorsiyumKatilabilirMi": None,
            "altYukleniciCalistirilabilirMi": None,
            "fiyatFarkiVerilecekMi": None,
            "avansVerilecekMi": None,
            "cerceveAnlasmaMi": None,
            "personelCalistirilmasinaDayaliMi": None,
            "orderBy": "ihaleTarihi",
            "siralamaTipi": "desc",
            "paginationSkip": 0,
            "paginationTake": 20
        }
        
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
                r = session.post(self.url, json=api_params, timeout=30)
            r.raise_for_status()
            logger.info(f"EKAPv2 API çağrısı başarılı. HTTP Durumu: {r.status_code}")
            return r.text
        except Exception as e:
            logger.error(f"EKAPv2 API bağlantı hatası: {e}")
            return ""

    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        if not raw_data:
            return []
        try:
            data = json.loads(raw_data)
            tenders = data.get("list", [])
            
            items = []
            for tender in tenders:
                ikn = tender.get("ikn")
                if not ikn:
                    continue
                
                title = tender.get("ihaleAdi", "")
                link = f"https://ekap.kik.gov.tr/EKAP/Ortak/IhaleArama/IhaleArama.aspx?IKN={quote(ikn)}"
                category = tender.get("ihaleTipAciklama", "Diğer")
                
                authority = tender.get("idareAdi", "")
                province = tender.get("ihaleIlAdi", "")
                method = tender.get("ihaleUsulAciklama", "")
                status = tender.get("ihaleDurumAciklama", "")
                dt = tender.get("ihaleTarihSaat", "")
                
                summary_parts = []
                if ikn:
                    summary_parts.append(f"IKN: {ikn}")
                if authority:
                    summary_parts.append(f"İdare: {authority}")
                if province:
                    summary_parts.append(f"İl: {province}")
                if method:
                    summary_parts.append(f"Yöntem: {method}")
                if dt:
                    summary_parts.append(f"Tarih: {dt}")
                if status:
                    summary_parts.append(f"Durum: {status}")
                    
                summary = " | ".join(summary_parts)
                
                items.append({
                    "link": link,
                    "title": title,
                    "summary": summary,
                    "category": category,
                    "source": self.source_name
                })
                
            logger.info(f"EKAPv2 İhaleleri ayrıştırıldı. Toplam {len(items)} ihale bulundu.")
            return items
        except Exception as e:
            logger.error(f"EKAPv2 ayrıştırma hatası: {e}")
            return []
