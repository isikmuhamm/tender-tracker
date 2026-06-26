import os
import logging
import yaml
from sqlalchemy.orm import Session
from src.database import init_db, SessionLocal, Tender
from src.filter import TenderFilter
from src.classifier import TenderClassifier
from src.scraper.yatirimlar import YatirimlarScraper
from src.scraper.dmo import DmoScraper
from src.scraper.ilan_gov_tr import IlanGovTrScraper
from src.scraper.ekapv2 import Ekapv2Scraper
from src.notifier.email_client import EmailNotifier
from src.notifier.telegram_bot import TelegramNotifier

logger = logging.getLogger(__name__)

class TenderBotOrchestrator:
    """
    Tüm kazıyıcı, filtreleyici, sınıflandırıcı ve bildirim modüllerini
    yöneten ve koordine eden ana orkestrasyon sınıfı.
    """
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.scrapers = []
        self.filter = TenderFilter(config_path=config_path)
        self.classifier = TenderClassifier()
        self.notifiers = []
        
        self.setup_modules()

    def setup_modules(self):
        # 1. Yapılandırmadan etkinleştirilmiş kazıcıları yükle
        enabled_scrapers = ["yatirimlar", "dmo", "ilan_gov_tr", "ekapv2"]
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    if config and "settings" in config:
                        enabled_scrapers = config["settings"].get("enabled_scrapers", enabled_scrapers)
            except Exception as e:
                logger.error(f"Yapılandırma yüklenirken hata: {e}")

        # Kazıcıları oluştur
        scraper_map = {
            "yatirimlar": YatirimlarScraper,
            "dmo": DmoScraper,
            "ilan_gov_tr": IlanGovTrScraper,
            "ekapv2": Ekapv2Scraper
        }
        
        for name in enabled_scrapers:
            if name in scraper_map:
                self.scrapers.append(scraper_map[name]())
                logger.info(f"Scraper yüklendi: {name}")

        # 2. Bildirim kanallarını oluştur
        self.notifiers.append(EmailNotifier())
        self.notifiers.append(TelegramNotifier())

    def run_once(self):
        """Tek bir tarama ve bildirim döngüsü çalıştırır."""
        logger.info("Tarama döngüsü başlatıldı...")
        init_db()
        db: Session = SessionLocal()
        
        new_tenders_added = []
        
        try:
            # 1. Tüm kazıcıları çalıştır
            for scraper in self.scrapers:
                try:
                    logger.info(f"Kaynak taranıyor: {scraper.source_name}")
                    scraped_items = scraper.get_new_items()
                    
                    for item in scraped_items:
                        # Veritabanında mükerrerlik kontrolü
                        exists = db.query(Tender).filter_by(link=item["link"]).first()
                        if exists:
                            continue
                            
                        # Küresel filtre kontrolü (kiralık/satılık vb.)
                        if self.filter.is_excluded(item["title"], item["summary"]):
                            # Elenenleri veritabanına 'Excluded' olarak kaydedelim ki tekrar taramayalım
                            new_tender = Tender(
                                link=item["link"],
                                title=item["title"],
                                summary=item["summary"],
                                category=item["category"],
                                source=item["source"],
                                sector="Excluded",
                                classification_method="none",
                                email_sent=True,  # Bildirim gitmesin diye baştan True yapıyoruz
                                telegram_sent=True
                            )
                            db.add(new_tender)
                            continue
                            
                        # Sektörel Sınıflandırma
                        sector, method = self.classifier.classify(item["title"], item["summary"])
                        
                        # Veritabanına kaydet
                        new_tender = Tender(
                            link=item["link"],
                            title=item["title"],
                            summary=item["summary"],
                            category=item["category"],
                            source=item["source"],
                            sector=sector,
                            classification_method=method
                        )
                        db.add(new_tender)
                        db.commit() # Her kayıtta commit ederek veritabanı durumunu güncel tutalım
                        
                        if sector:  # Sadece bir sektöre atanan ihaleleri bildirim listesine ekle
                            new_tenders_added.append({
                                "link": item["link"],
                                "title": item["title"],
                                "summary": item["summary"],
                                "category": item["category"],
                                "source": item["source"],
                                "sector": sector
                            })
                            
                except Exception as e:
                    logger.error(f"{scraper.source_name} tarama döngüsünde hata oluştu: {e}", exc_info=True)

            logger.info(f"Yeni ihaleler kaydedildi. Bildirim gönderilecek ihale sayısı: {len(new_tenders_added)}")

            # 2. Bildirim kanallarını çalıştır (Veritabanındaki gönderilmeyen durumları toplayarak)
            self._process_notifications(db)

        except Exception as e:
            logger.error(f"Ana orkestrasyon döngüsünde kritik hata: {e}", exc_info=True)
        finally:
            db.close()
            logger.info("Tarama döngüsü tamamlandı.")

    def _process_notifications(self, db: Session):
        """Veritabanında gönderilmemiş olan ihaleleri tespit edip bildirir."""
        # 1. E-posta için gönderilmeyenleri bul (Sektörü 'Excluded' veya None olmayanlar)
        unsent_email = db.query(Tender).filter(
            Tender.email_sent == False,
            Tender.sector != None,
            Tender.sector != "Excluded"
        ).all()
        
        if unsent_email:
            email_notifier = next((n for n in self.notifiers if n.name == "email"), None)
            if email_notifier:
                email_list = [self._to_dict(t) for t in unsent_email]
                if email_notifier.send_notification(email_list):
                    for t in unsent_email:
                        t.email_sent = True
                    db.commit()

        # 2. Telegram için gönderilmeyenleri bul
        unsent_telegram = db.query(Tender).filter(
            Tender.telegram_sent == False,
            Tender.sector != None,
            Tender.sector != "Excluded"
        ).all()
        
        if unsent_telegram:
            telegram_notifier = next((n for n in self.notifiers if n.name == "telegram"), None)
            if telegram_notifier:
                tg_list = [self._to_dict(t) for t in unsent_telegram]
                if telegram_notifier.send_notification(tg_list):
                    for t in unsent_telegram:
                        t.telegram_sent = True
                    db.commit()

    @staticmethod
    def _to_dict(tender: Tender) -> dict:
        return {
            "link": tender.link,
            "title": tender.title,
            "summary": tender.summary,
            "category": tender.category,
            "source": tender.source,
            "sector": tender.sector
        }
