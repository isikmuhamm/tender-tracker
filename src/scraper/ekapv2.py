import logging
import ssl
import os
import uuid
import base64
import time
import json
import warnings
import urllib3
import yaml
from typing import List, Dict, Any
from urllib.parse import urlencode
import requests
from requests.adapters import HTTPAdapter
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as crypto_padding
from .base import BaseScraper, SourceFetchError, SourceParseError

logger = logging.getLogger(__name__)

class TLSAdapter(HTTPAdapter):
    """EKAPv2'nin SSL/TLS el sıkışma gereksinimleri için özel adaptör."""
    def __init__(self, verify_secure=True, *args, **kwargs):
        self.verify_secure = verify_secure
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        if not self.verify_secure:
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
        self.last_success_at = None
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
        
        insecure_fallback = os.getenv("EKAP_INSECURE_FALLBACK", "false").lower() in ("true", "1", "yes")
        if not insecure_fallback:
            from src.database import get_data_path
            cfg_path = get_data_path("config.yaml")
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        config = yaml.safe_load(f)
                        if config and "settings" in config:
                            insecure_fallback = config["settings"].get("ekap_insecure_fallback", False)
                except Exception:
                    pass

        date_start = None
        if self.last_success_at:
            date_start = self.last_success_at.strftime("%d.%m.%Y")
            logger.info(f"EKAPv2 incremental sync aktif: {date_start} tarihinden sonra yayımlanan ihaleler aranıyor.")
        else:
            logger.info("EKAPv2 ilk tarama aktif: Teklif vermeye açık ihaleler aranıyor.")

        all_tenders = []
        page = 0
        take = 40
        max_pages = 500
        
        def make_session(verify_secure=True):
            s = requests.Session()
            s.headers.update(self.headers)
            s.verify = verify_secure
            s.mount("https://ekapv2.kik.gov.tr", TLSAdapter(verify_secure=verify_secure))
            return s
            
        session = make_session(verify_secure=True)
        is_fallback_active = False

        while page < max_pages:
            skip = page * take
            try:
                session.headers.update(self._generate_security_headers())
            except Exception as e:
                raise SourceFetchError(f"EKAPv2 güvenlik başlıkları oluşturulamadı: {e}")
                
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
                "ilanTarihSaatBaslangic": date_start,
                "ilanTarihSaatBitis": None,
                "yasaKapsami4734List": [],
                "ihaleTuruIdList": [],
                "ihaleUsulIdList": [],
                "ihaleUsulAltIdList": [],
                "ihaleIlIdList": [],
                "ihaleDurumIdList": [2],  # Teklif Vermeye Açık
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
                "paginationSkip": skip,
                "paginationTake": take
            }
            
            try:
                r = session.post(self.url, json=api_params, timeout=30)
                r.raise_for_status()
                data = r.json()
            except requests.exceptions.SSLError as ssl_err:
                if insecure_fallback and not is_fallback_active:
                    logger.warning("EKAPv2 standard SSL verification failed. Falling back to insecure compatibility mode as configured.")
                    is_fallback_active = True
                    session = make_session(verify_secure=False)
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
                        try:
                            session.headers.update(self._generate_security_headers())
                            r = session.post(self.url, json=api_params, timeout=30)
                            r.raise_for_status()
                            data = r.json()
                        except Exception as retry_err:
                            raise SourceFetchError(f"EKAPv2 API bağlantı hatası (Fallback, Sayfa {page}): {retry_err}")
                else:
                    raise SourceFetchError(f"EKAPv2 SSL verification failed (Sayfa {page}): {ssl_err}. Fallback is disabled.")
            except Exception as e:
                raise SourceFetchError(f"EKAPv2 API bağlantı hatası (Sayfa {page}): {e}")
            
            if not isinstance(data, dict):
                raise SourceFetchError(f"EKAPv2 API yanıtı sözlük nesnesi değil (Sayfa {page})")
            if "list" not in data or not isinstance(data["list"], list):
                raise SourceFetchError(f"EKAPv2 API yanıtında 'list' alanı bulunamadı veya geçersiz (Sayfa {page})")
            if "totalCount" not in data or not isinstance(data["totalCount"], (int, float)) or data["totalCount"] < 0:
                raise SourceFetchError(f"EKAPv2 API yanıtında 'totalCount' alanı eksik veya negatif (Sayfa {page})")
                
            tenders = data["list"]
            total_count = int(data["totalCount"])
            
            if total_count > 0 and not tenders and page == 0:
                raise SourceFetchError("EKAPv2 API ilk sayfada kayıt dönmedi, totalCount sıfırdan büyük olmasına rağmen.")
            
            if not tenders:
                break
                
            all_tenders.extend(tenders)
            
            if len(all_tenders) >= total_count:
                break
                
            page += 1
            if page >= max_pages:
                if total_count > 0 and len(all_tenders) < total_count:
                    raise SourceFetchError("EKAPv2 sayfalama güvenlik sınırına (500 sayfa) ulaşıldı fakat tüm kayıtlar çekilemedi.")
                break
            time.sleep(0.5)
            
        logger.info(f"EKAPv2 API taraması bitti. Toplam çekilen: {len(all_tenders)}, Toplam sunucudaki: {total_count}")
        if is_fallback_active:
            logger.warning("EKAPv2 ran in Degraded/Compatibility mode bypassing TLS verification.")
            
        return json.dumps({"list": all_tenders, "totalCount": total_count})

    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        if not raw_data:
            raise SourceParseError("EKAPv2 boş veri döndü.")
        try:
            data = json.loads(raw_data)
            tenders = data.get("list", [])
            total_count = data.get("totalCount", 0)
            
            if not tenders and total_count == 0:
                return []
            
            items = []
            for tender in tenders:
                ikn = tender.get("ikn")
                if not ikn:
                    continue
                
                title = tender.get("ihaleAdi", "")
                if not title:
                    continue
                    
                link = f"https://ekap.kik.gov.tr/EKAP/Ortak/IhaleArama/IhaleArama.aspx?{urlencode({'IKN': ikn})}"
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
            if isinstance(e, SourceParseError):
                raise e
            raise SourceParseError(f"EKAPv2 ayrıştırma hatası: {e}")
