import os
import logging
import json
import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Lazy import google.generativeai to avoid errors if not configured or needed
genai_available = False
try:
    import google.generativeai as genai
    genai_available = True
except ImportError:
    pass

class TenderClassifier:
    """
    İhaleleri sektörel olarak sınıflandıran katman.
    API anahtarı varsa Gemini ile, yoksa kural tabanlı (sectors.yaml) yerel filtreyle çalışır.
    """
    def __init__(self, sectors_path: str = "sectors.yaml"):
        self.sectors_path = sectors_path
        self.sectors = {}
        self.ai_enabled = False
        self.model = None
        
        self.load_sectors()
        self.init_ai()

    def load_sectors(self):
        if not os.path.exists(self.sectors_path):
            logger.warning(f"Sektör tanımları bulunamadı: {self.sectors_path}")
            return
        try:
            with open(self.sectors_path, "r", encoding="utf-8") as f:
                self.sectors = yaml.safe_load(f) or {}
            logger.info(f"Sektör tanımları yüklendi. Tanımlı sektörler: {list(self.sectors.keys())}")
        except Exception as e:
            logger.error(f"Sektör tanımları yüklenirken hata: {e}")

    def init_ai(self):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and genai_available:
            try:
                genai.configure(api_key=api_key)
                # Modern gemini-1.5-flash modelini kullanıyoruz
                self.model = genai.GenerativeModel("gemini-1.5-flash")
                self.ai_enabled = True
                logger.info("Yapay Zeka (Gemini API) sınıflandırma katmanı başarıyla aktif edildi.")
            except Exception as e:
                logger.error(f"Gemini API yapılandırılırken hata oluştu: {e}")
                self.ai_enabled = False
        else:
            logger.info("Yapay zeka anahtarı bulunamadı veya paket kurulu değil. Yerel kural tabanlı mod aktif.")

    def classify_local(self, title: str, summary: str = "") -> str:
        """
        sectors.yaml dosyasındaki anahtar kelimelere göre yerel sınıflandırma yapar.
        """
        t = title.lower()
        s = (summary or "").lower()
        
        best_sector = None
        max_score = 0
        
        for sector_name, rules in self.sectors.items():
            # Negatif anahtar kelime eşleşmesi kontrolü
            negatives = rules.get("negative_keywords", [])
            has_negative = False
            for nw in negatives:
                if nw.lower() in t or nw.lower() in s:
                    has_negative = True
                    break
            if has_negative:
                continue
                
            # Pozitif anahtar kelime puanlama
            keywords = rules.get("keywords", [])
            score = 0
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in t:
                    score += 2
                elif kw_lower in s:
                    score += 1
            
            # En yüksek skorlu sektörü seç
            if score > max_score:
                max_score = score
                best_sector = sector_name
                
        # Eşik değer 2'dir (başlıkta en az bir kelime veya açıklamada iki kelime eşleşmeli)
        if max_score >= 2:
            return best_sector
        return None

    def classify_ai(self, title: str, summary: str = "") -> str:
        """
        Gemini API kullanarak başlık ve özeti analiz edip ihaleyi sınıflandırır.
        """
        if not self.ai_enabled or not self.model:
            return None
            
        sectors_list = list(self.sectors.keys())
        prompt = f"""
        Aşağıdaki ihale başlığı ve detayını analiz ederek bu ihaleyi şu sektör listesinden en uygun olanına sınıflandır: {sectors_list}.
        Eğer ihale bu listedeki hiçbir sektöre uymuyorsa, "sector" değerini null olarak ata.
        
        İhale Başlığı: {title}
        İhale Detayı: {summary}
        
        Yanıtı sadece aşağıdaki JSON şemasında ver:
        {{
            "sector": "Sektör Adı veya null"
        }}
        """
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            data = json.loads(response.text)
            sector = data.get("sector")
            if sector in sectors_list:
                return sector
            return None
        except Exception as e:
            logger.error(f"Gemini API sınıflandırma hatası: {e}")
            return None

    def classify(self, title: str, summary: str = "") -> tuple:
        """
        İhaleyi sınıflandırır. 
        Dönen çıktı: (SektörAdı veya None, SınıflandırmaYöntemi)
        """
        # Önce yapay zeka ile dene
        if self.ai_enabled:
            sector = self.classify_ai(title, summary)
            if sector:
                logger.info(f"İhale AI ile sınıflandırıldı: '{sector}' | '{title[:40]}...'")
                return sector, "ai"
                
        # Yapay zeka eşleşme bulamazsa veya kapalıysa kural tabanlıya dön
        sector = self.classify_local(title, summary)
        method = "rule" if sector else "none"
        if sector:
            logger.info(f"İhale yerel kurallarla sınıflandırıldı: '{sector}' | '{title[:40]}...'")
        return sector, method
