import os
import logging
import requests
from typing import List, Dict, Any
from .base import BaseNotifier

logger = logging.getLogger(__name__)

class TelegramNotifier(BaseNotifier):
    """
    İhaleleri Telegram Bot API üzerinden bir kanal veya gruba gönderen sınıf.
    """
    def __init__(self):
        super().__init__(name="telegram")
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage" if self.bot_token else None

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

            success = True
            for sector_name, items in grouped.items():
                message = f"<b>📁 {sector_name} ({len(items)} Yeni İhale)</b>\n\n"
                
                for item in items:
                    source = item.get("source", "").upper()
                    title = item.get("title", "")
                    summary = item.get("summary", "")
                    link = item.get("link", "#")
                    
                    tender_text = f"• [{source}] <b>{title}</b>\n"
                    if summary:
                        tender_text += f"<i>{summary}</i>\n"
                    tender_text += f"🔗 <a href='{link}'>Detay ve Bağlantı</a>\n\n"
                    
                    # Telegram 4096 karakter sınırını aşmamak için bölme mantığı
                    if len(message) + len(tender_text) > 4000:
                        if not self._send_raw_message(message):
                            success = False
                        message = f"<b>📁 {sector_name} (Devam...)</b>\n\n"
                        
                    message += tender_text
                
                # Kalan mesajı gönder
                if not self._send_raw_message(message):
                    success = False
                    
            return success
            
        except Exception as e:
            logger.error(f"Telegram bildirim sürecinde hata oluştu: {e}")
            return False
