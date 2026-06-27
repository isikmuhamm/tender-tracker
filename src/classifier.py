import os
import re
import logging
import json
import yaml
from src.llm_client import LLMClient

logger = logging.getLogger(__name__)

def matches_keyword(kw: str, text: str) -> bool:
    kw_lower = kw.lower()
    if len(kw_lower) <= 5:
        # Enforce Turkish-safe word boundary
        pattern = rf"(?<![a-zA-Z0-9çğışöüÇĞIŞÖÜ]){re.escape(kw_lower)}(?![a-zA-Z0-9çğışöüÇĞIŞÖÜ])"
        return bool(re.search(pattern, text))
    else:
        return kw_lower in text

class TenderClassifier:
    """
    İhaleleri sektörel olarak sınıflandıran katman.
    sectors.yaml dosyasındaki anahtar kelimelere göre yerel sınıflandırma yapar.
    """
    def __init__(self, sectors_path: str = None):
        from src.database import get_data_path
        self.sectors_path = sectors_path or get_data_path("sectors.yaml")
        self.sectors = {}
        self.llm = LLMClient()
        self.ai_enabled = self.llm.is_enabled()
        
        self.load_sectors()

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

    def classify_local(self, title: str, summary: str = "") -> str:
        """
        sectors.yaml dosyasındaki anahtar kelimelere göre yerel sınıflandırma yapar.
        """
        t = title.lower()
        s = (summary or "").lower()
        
        best_sector = None
        max_score = 0
        
        for sector_name, rules in self.sectors.items():
            if not rules.get("enabled", True):
                continue
            negatives = rules.get("negative_keywords", [])
            has_negative = False
            for nw in negatives:
                if matches_keyword(nw, t) or matches_keyword(nw, s):
                    has_negative = True
                    break
            if has_negative:
                continue
                
            keywords = rules.get("keywords", [])
            score = 0
            for kw in keywords:
                if matches_keyword(kw, t) or matches_keyword(kw, s):
                    score += 2
            
            if score > max_score:
                max_score = score
                best_sector = sector_name
                
        if max_score >= 2:
            return best_sector
        return None

    def evaluate_custom_filters(self, title: str, summary: str, custom_filters: list, sector: str = None) -> list:
        """
        İhaleyi kullanıcının özel tanımladığı akıllı süzgeçlere (custom_llm_filters) göre LLM ile değerlendirir.
        Dönen çıktı: Eşleşen süzgeçlerin ID listesi (örn: ["metro_plc"])
        """
        if not self.ai_enabled or not custom_filters:
            return []
            
        # Filtreleri sektör bazlı sınırla (prior sector filter)
        active_filters = []
        for f in custom_filters:
            if not f.get("enabled", True):
                continue
            target_sec = f.get("target_sector", "all")
            if target_sec != "all" and sector and target_sec != sector:
                continue
            active_filters.append(f)
            
        if not active_filters:
            return []
            
        filters_json = [{"id": f["id"], "name": f["name"], "instruction": f["prompt_instruction"]} for f in active_filters]
        
        prompt = f"""
        Aşağıdaki ihale ilanı başlık ve detayını, tanımlanan 'Özel Akıllı Süzgeçler' yönergelerine göre değerlendir.
        Her süzgecin yönergesini oku ve bu ihalenin o yönergeyle eşleşip eşleşmediğini (True/False) belirle.
        
        İhale Başlığı: {title}
        İhale Detayı: {summary}
        
        Süzgeç Tanımları:
        {json.dumps(filters_json, ensure_ascii=False, indent=2)}
        
        Yanıtı sadece aşağıdaki JSON şemasında ver. Yalnızca eşleşen (True olan) süzgeçlerin ID listesini dön:
        {{
            "matched_filter_ids": ["eslesen_id_1", "eslesen_id_2"]
        }}
        """
        
        try:
            res_text = self.llm.complete(prompt, json_response=True)
            if not res_text:
                return []
            if res_text.startswith("```"):
                lines = res_text.splitlines()
                if len(lines) > 2:
                    res_text = "\n".join(lines[1:-1])
            data = json.loads(res_text)
            matched = data.get("matched_filter_ids", [])
            
            valid_ids = {f["id"] for f in active_filters}
            return [mid for mid in matched if mid in valid_ids]
        except Exception as e:
            logger.error(f"LLM akıllı süzgeç değerlendirme hatası: {e}")
            return []

    def classify(self, title: str, summary: str = "") -> tuple:
        """
        İhaleyi sınıflandırır. 
        Dönen çıktı: (SektörAdı veya None, SınıflandırmaYöntemi)
        """
        # Sadece hızlı yerel kural tabanlı sınıflandırmayı kullan (0ms latency, token maliyeti yok)
        sector = self.classify_local(title, summary)
        if sector:
            logger.info(f"İhale yerel kurallarla sınıflandırıldı: '{sector}' | '{title[:40]}...'")
            return sector, "rule"
            
        return None, "none"
