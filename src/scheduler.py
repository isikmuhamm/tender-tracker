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
    def __init__(self, config_path: str = None):
        from src.database import get_data_path
        self.config_path = config_path or get_data_path("config.yaml")
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
        
        # Sınıflandırıcı ayarlarını (API key vb.) ve özel süzgeçleri en güncel halinden yükle
        self.classifier = TenderClassifier()
        
        custom_filters = []
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    if config and "filters" in config:
                        custom_filters = config["filters"].get("custom_llm_filters", [])
            except Exception as e:
                logger.error(f"Yapılandırmadan akıllı süzgeçler yüklenirken hata: {e}")

        new_tenders_added = []
        successful_sources = 0
        failed_sources = 0
        records_added = 0
        processing_errors = 0
        
        try:
            # 1. Tüm kazıcıları çalıştır
            for scraper in self.scrapers:
                try:
                    logger.info(f"Kaynak taranıyor: {scraper.source_name}")
                    scraped_items = scraper.get_new_items()
                    successful_sources += 1
                    
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
                            try:
                                db.add(new_tender)
                                db.commit()
                                records_added += 1
                                logger.info(f"Elenen ihale kaydedildi (Excluded): {item['title'][:40]}...")
                            except Exception as db_err:
                                db.rollback()
                                processing_errors += 1
                                logger.error(f"Elenen ihale veritabanına kaydedilirken hata oluştu: {db_err}")
                            continue
                            
                        try:
                            # Sektörel Sınıflandırma
                            sector, method = self.classifier.classify(item["title"], item["summary"])
                            
                            # Özel Akıllı Süzgeçler (LLM) değerlendirmesi
                            matched_filters_str = None
                            if sector and sector != "Excluded" and custom_filters:
                                matched_ids = self.classifier.evaluate_custom_filters(
                                    item["title"], item["summary"], custom_filters, sector=sector
                                )
                                if matched_ids:
                                    matched_filters_str = ",".join(matched_ids)
                                    logger.info(f"İhale akıllı süzgeçlerle eşleşti: {matched_ids} | '{item['title'][:40]}...'")
                            
                            # Veritabanına kaydet
                            new_tender = Tender(
                                link=item["link"],
                                title=item["title"],
                                summary=item["summary"],
                                category=item["category"],
                                source=item["source"],
                                sector=sector,
                                classification_method=method,
                                matched_custom_filters=matched_filters_str
                            )
                            db.add(new_tender)
                            db.commit() # Her kayıtta commit ederek veritabanı durumunu güncel tutalım
                            records_added += 1
                            logger.info(f"İhale başarıyla kaydedildi: {item['title'][:40]}...")
                            
                            if sector:  # Sadece bir sektöre atanan ihaleleri bildirim listesine ekle
                                new_tenders_added.append({
                                    "link": item["link"],
                                    "title": item["title"],
                                    "summary": item["summary"],
                                    "category": item["category"],
                                    "source": item["source"],
                                    "sector": sector
                                })
                        except Exception as tender_err:
                            db.rollback()
                            processing_errors += 1
                            logger.error(f"İhale işlenirken veya kaydedilirken hata oluştu: {tender_err}")
                            
                except Exception as e:
                    failed_sources += 1
                    logger.error(f"{scraper.source_name} tarama döngüsünde hata oluştu: {e}", exc_info=True)

            logger.info(f"Yeni ihaleler kaydedildi. Bildirim gönderilecek ihale sayısı: {len(new_tenders_added)}")

            # 2. Bildirim kanallarını çalıştır (Veritabanındaki gönderilmeyen durumları toplayarak)
            notification_errors = self._process_notifications(db)

        except Exception as e:
            logger.error(f"Ana orkestrasyon döngüsünde kritik hata: {e}", exc_info=True)
            raise e
        finally:
            db.close()
            logger.info("Tarama döngüsü tamamlandı.")

        # Durumu belirle
        if successful_sources == 0 and failed_sources > 0:
            status_str = "failed"
        elif failed_sources > 0 or processing_errors > 0 or notification_errors > 0:
            status_str = "partial"
        else:
            status_str = "success"
            
        return {
            "successful_sources": successful_sources,
            "failed_sources": failed_sources,
            "records_added": records_added,
            "processing_errors": processing_errors,
            "notification_errors": notification_errors,
            "status": status_str
        }

    def _process_notifications(self, db: Session) -> int:
        """Veritabanında gönderilmemiş olan ihaleleri tespit edip bildirir. Hatalı bildirim sayısını döner."""
        notification_errors = 0
        
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
                try:
                    logger.info("E-posta bildirimi gönderiliyor...")
                    if email_notifier.send_notification(email_list):
                        for t in unsent_email:
                            t.email_sent = True
                        db.commit()
                        logger.info("E-posta bildirim durumu veritabanında güncellendi.")
                    else:
                        notification_errors += 1
                        logger.warning("E-posta bildirimi gönderilemedi (send_notification False döndü).")
                except Exception as notify_err:
                    db.rollback()
                    notification_errors += 1
                    logger.error(f"E-posta bildirimi gönderilirken hata oluştu: {notify_err}")

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
                try:
                    logger.info("Telegram bildirimi gönderiliyor...")
                    if telegram_notifier.send_notification(tg_list):
                        for t in unsent_telegram:
                            t.telegram_sent = True
                        db.commit()
                        logger.info("Telegram bildirim durumu veritabanında güncellendi.")
                    else:
                        notification_errors += 1
                        logger.warning("Telegram bildirimi gönderilemedi (send_notification False döndü).")
                except Exception as notify_err:
                    db.rollback()
                    notification_errors += 1
                    logger.error(f"Telegram bildirimi gönderilirken hata oluştu: {notify_err}")
                    
        return notification_errors

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
