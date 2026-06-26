import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Dict, Any
from .base import BaseNotifier

logger = logging.getLogger(__name__)

class EmailNotifier(BaseNotifier):
    """
    İhaleleri SMTP sunucusu üzerinden e-posta olarak gönderen sınıf.
    """
    def __init__(self, config_path: str = None):
        super().__init__(name="email")
        from src.database import get_data_path
        self.config_path = config_path or get_data_path("config.yaml")
        self.smtp_host = None
        self.smtp_port = 587
        self.smtp_use_tls = True
        self.mail_from = None
        self.mail_password = None
        self.mail_to = []
        
        self.load_config()

    def load_config(self):
        import yaml
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                if config and "notifications" in config and "email" in config["notifications"]:
                    mail_cfg = config["notifications"]["email"]
                    self.smtp_host = mail_cfg.get("smtp_server")
                    self.smtp_port = int(mail_cfg.get("smtp_port", 587))
                    self.smtp_use_tls = True
                    self.mail_from = mail_cfg.get("sender")
                    self.mail_password = mail_cfg.get("password")
                    # handle string or list format for recipients
                    recipients = mail_cfg.get("recipients", [])
                    if isinstance(recipients, str):
                        self.mail_to = [m.strip() for m in recipients.split(",") if m.strip()]
                    else:
                        self.mail_to = [m.strip() for m in recipients if m.strip()]
        except Exception as e:
            logger.error(f"E-posta bildirim yapılandırması yüklenirken hata: {e}")

    def send_notification(self, tenders: List[Dict[str, Any]]) -> bool:
        if not tenders:
            logger.info("Gönderilecek ihale bulunmadığı için e-posta gönderilmedi.")
            return True

        if not self.smtp_host or not self.mail_from or not self.mail_to:
            logger.error("SMTP veya Alıcı ayarları eksik. E-posta bildirimi gönderilemiyor.")
            return False

        logger.info(f"E-posta hazırlanıyor. Toplam ihale sayısı: {len(tenders)}")
        
        try:
            # Sektörlere göre ihaleleri grupla
            grouped = {}
            for t in tenders:
                sector = t.get("sector") or "Sınıflandırılmamış"
                if sector not in grouped:
                    grouped[sector] = []
                grouped[sector].append(t)

            # HTML gövdesini oluştur
            today = datetime.now().strftime("%d.%m.%Y")
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; font-size: 13px; color: #333; line-height: 1.5;">
                <h2 style="color: #2b547e; border-bottom: 2px solid #2b547e; padding-bottom: 5px;">
                    📋 İhale Takip Raporu – {today}
                </h2>
                <p>Sistem tarafından yeni taranan ve sınıflandırılan ihalelerin dökümü aşağıdadır:</p>
            """

            for sector_name, items in grouped.items():
                body += f"""
                <h3 style="color: #d05b22; margin-top: 25px; border-bottom: 1px solid #ddd; padding-bottom: 3px;">
                    📁 {sector_name} ({len(items)} İhale)
                </h3>
                <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%; border: 1px solid #ddd;">
                    <thead>
                        <tr style="background-color: #f7f9fa; text-align: left;">
                            <th style="width: 15%;">Kaynak</th>
                            <th style="width: 20%;">Kategori</th>
                            <th style="width: 35%;">Başlık</th>
                            <th style="width: 20%;">Detay / Özellik</th>
                            <th style="width: 10%;">Bağlantı</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                for i in items:
                    source_badge = i.get('source', '').upper()
                    # Görsel vurgu için kaynak rengi
                    badge_style = "color: #007bff; font-weight: bold;"
                    if source_badge == "YATIRIMLAR":
                        badge_style = "color: #28a745; font-weight: bold;"
                    elif source_badge == "DMO":
                        badge_style = "color: #fd7e14; font-weight: bold;"
                        
                    body += f"""
                        <tr>
                            <td style="{badge_style}">{source_badge}</td>
                            <td>{i.get('category', '')}</td>
                            <td><b>{i.get('title', '')}</b></td>
                            <td style="font-size: 12px; color: #666;">{i.get('summary', '')}</td>
                            <td style="text-align: center;"><a href="{i.get('link', '#')}" style="color: #007bff; text-decoration: none; font-weight: bold;">İhale</a></td>
                        </tr>
                    """
                body += """
                    </tbody>
                </table>
                """

            body += """
                <br><br>
                <div style="border-top: 1px solid #ccc; padding-top: 15px; margin-top: 30px; font-size: 11px; color: #777;">
                    <p>Bu e-posta, İhale Takip Botu tarafından otomatik olarak üretilmiştir.</p>
                </div>
            </body>
            </html>
            """

            # E-posta nesnesini yapılandır
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"🔔 Günlük İhale Raporu – {today} ({len(tenders)} İhale)"
            msg["From"] = self.mail_from
            msg["To"] = ", ".join(self.mail_to)
            msg.attach(MIMEText(body, "html"))

            # SMTP Bağlantısı
            logger.info(f"SMTP sunucusuna bağlanılıyor: {self.smtp_host}:{self.smtp_port}")
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as s:
                if self.smtp_use_tls:
                    s.starttls()
                s.login(self.mail_from, self.mail_password)
                s.send_message(msg)
                
            logger.info(f"İhale raporu e-postası başarıyla gönderildi: {', '.join(self.mail_to)}")
            return True
            
        except Exception as e:
            logger.error(f"E-posta gönderiminde beklenmeyen hata oluştu: {e}", exc_info=True)
            return False
