import os
import logging
import requests
import html
from typing import List, Dict, Any
from .base import BaseNotifier

logger = logging.getLogger(__name__)

class TelegramNotifier(BaseNotifier):
    """
    İhaleleri Telegram Bot API üzerinden bir kanal veya gruba gönderen sınıf.
    """
    def __init__(self, config_path: str = None):
        super().__init__(name="telegram")
        from src.database import get_data_path
        self.config_path = config_path or get_data_path("config.yaml")
        self.bot_token = None
        self.chat_id = None
        self.api_url = None
        
        self.load_config()

    def load_config(self):
        import yaml
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                if config and "notifications" in config and "telegram" in config["notifications"]:
                    tg_cfg = config["notifications"]["telegram"]
                    self.bot_token = tg_cfg.get("bot_token")
                    self.chat_id = tg_cfg.get("chat_id")
                    if self.bot_token:
                        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        except Exception as e:
            logger.error(f"Telegram bildirim yapılandırması yüklenirken hata: {e}")

    def _send_raw_message(self, text: str) -> bool:
        """Telegram API'sine ham mesaj gönderir."""
        if not self.api_url or not self.chat_id:
            logger.error("Telegram API yapılandırması eksik. Mesaj gönderilemiyor.")
            return False

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        try:
            r = requests.post(self.api_url, json=payload, timeout=15)
            r.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Telegram mesaj gönderim hatası: {e}")
            return False

    def send_notification(self, tenders: List[Dict[str, Any]]) -> bool:
        if not tenders:
            logger.info("Gönderilecek ihale bulunmadığı için Telegram bildirimi gönderilmedi.")
            return True

        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram Bot Token veya Chat ID tanımlanmamış. Telegram bildirimi pas geçiliyor.")
            return True  # Engellememesi için True dönüyoruz, isteğe bağlı loglanır

        logger.info(f"Telegram bildirimleri hazırlanıyor. Toplam ihale: {len(tenders)}")
        
        try:
            # Sektörlere göre grupla
            grouped = {}
            for t in tenders:
                sector = t.get("sector") or "Sınıflandırılmamış"
                if sector not in grouped:
                    grouped[sector] = []
                grouped[sector].append(t)

            def safe_url(url: str) -> str:
                if not url:
                    return "#"
                clean = url.strip().lower()
                if clean.startswith("http://") or clean.startswith("https://"):
                    return url
                return "#"

            success = True
            for sector_name, items in grouped.items():
                escaped_sector = html.escape(sector_name)
                message = f"<b>📁 {escaped_sector} ({len(items)} Yeni İhale)</b>\n\n"
                
                for item in items:
                    source = item.get("source", "").upper()
                    title = item.get("title", "")
                    summary = item.get("summary", "")
                    link = item.get("link", "#")
                    
                    escaped_source = html.escape(source)
                    escaped_title = html.escape(title)
                    escaped_summary = html.escape(summary)
                    escaped_link = html.escape(safe_url(link))
                    
                    tender_text = f"• [{escaped_source}] <b>{escaped_title}</b>\n"
                    if escaped_summary:
                        tender_text += f"<i>{escaped_summary}</i>\n"
                    tender_text += f"🔗 <a href='{escaped_link}'>Detay ve Bağlantı</a>\n\n"
                    
                    # Telegram 4096 karakter sınırını aşmamak için bölme mantığı
                    if len(message) + len(tender_text) > 4000:
                        if not self._send_raw_message(message):
                            success = False
                        message = f"<b>📁 {escaped_sector} (Devam...)</b>\n\n"
                        
                    message += tender_text
                
                # Kalan mesajı gönder
                if not self._send_raw_message(message):
                    success = False
                    
            return success
            
        except Exception as e:
            logger.error(f"Telegram bildirim sürecinde hata oluştu: {e}")
            return False
