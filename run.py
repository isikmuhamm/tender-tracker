import argparse
import sys
import os
import time
import logging
import urllib3
from dotenv import load_dotenv
from src.scheduler import TenderBotOrchestrator
from src.database import init_db, SessionLocal, Tender, get_data_path

# Çevresel değişkenleri yükle
load_dotenv()

# =========================================================
# LOGGING SETUP
# =========================================================
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Terminal handler (Tüm detaylar)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Dosya handler (Özet loglar)
file_handler = logging.FileHandler(get_data_path("events.log"), encoding="utf-8")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="İhale Takip Botu (Tender Tracker) CLI Arayüzü",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--once",
        action="store_true",
        help="Botu bir kez çalıştırır, yeni ihaleleri tarar, kaydeder ve bildirir."
    )
    group.add_argument(
        "--daemon",
        action="store_true",
        help="Botu sürekli arka planda çalıştırır (belirlenen aralıklarla tarama yapar)."
    )
    group.add_argument(
        "--stats",
        action="store_true",
        help="Veritabanındaki ihalelere ait güncel istatistikleri ve özet raporu gösterir."
    )
    return parser.parse_args()

def show_stats():
    """Veritabanı istatistiklerini görüntüler."""
    init_db()
    db = SessionLocal()
    try:
        total = db.query(Tender).count()
        excluded = db.query(Tender).filter_by(sector="Excluded").count()
        classified = db.query(Tender).filter(
            Tender.sector.isnot(None),
            Tender.sector != "Excluded"
        ).count()
        unclassified = db.query(Tender).filter(
            Tender.sector.is_(None)
        ).count()
        
        # Sektör dağılımı
        print("=" * 60)
        print("İHALE TAKİP BOTU - VERİTABANI İSTATİSTİKLERİ")
        print("=" * 60)
        print(f"Toplam Taranan İhale: {total}")
        print(f"Elenen İhale (Küresel Filtre): {excluded}")
        print(f"Sınıflandırılan Aktif İhale: {classified}")
        print(f"Sektör Atanamayan İhale (Unclassified): {unclassified}")
        print("-" * 60)
        
        sectors = db.query(Tender.sector).filter(Tender.sector != "Excluded", Tender.sector != None).distinct().all()
        print("Sektörel Dağılım:")
        for (sec,) in sectors:
            count = db.query(Tender).filter_by(sector=sec).count()
            print(f"  - {sec}: {count} ihale")
            
        print("-" * 60)
        sources = db.query(Tender.source).distinct().all()
        print("Kaynak Dağılımı:")
        for (src,) in sources:
            count = db.query(Tender).filter_by(source=src).count()
            print(f"  - {src}: {count} ihale")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"İstatistikler alınırken hata: {e}")
        sys.exit(1)
    finally:
        db.close()

def get_check_interval() -> int:
    """Tarama aralığını belirler. Öncelik sırası: ENV > config.yaml settings.check_interval_minutes > settings.check_interval > Varsayılan (60 dk)."""
    import yaml
    
    # 1. ENV kontrolü (En yüksek öncelik)
    env_val = os.getenv("CHECK_INTERVAL_MINUTES")
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            pass
            
    # 2. config.yaml kontrolü
    config_path = get_data_path("config.yaml")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                settings = config.get("settings", {})
                interval = settings.get("check_interval_minutes", settings.get("check_interval"))
                if interval is not None:
                    return int(interval)
        except Exception:
            pass
            
    # 3. Varsayılan
    return 60

def main():
    args = parse_arguments()
    
    # Varsayılan mod --once olarak kabul edilir
    if not args.stats and not args.daemon:
        args.once = True

    if args.stats:
        show_stats()
        sys.exit(0)

    orchestrator = TenderBotOrchestrator()

    if args.once:
        logger.info("=" * 60)
        logger.info("İHALE TAKİP BOTU - TEK SEFERLİK ÇALIŞTIRMA MODU")
        logger.info("=" * 60)
        from src.process_lock import ProcessLock
        lock = ProcessLock("scan")
        if not lock.acquire():
            logger.error("Hata: Başka bir tarama veya re-evaluation işlemi (örneğin Dashboard) çalışıyor. Çıkılıyor.")
            sys.exit(1)
        try:
            result = orchestrator.run_once()
            status_str = result.get("status", "success")
            if status_str == "success":
                sys.exit(0)
            elif status_str == "partial":
                sys.exit(2)
            else:
                sys.exit(1)
        except Exception as err:
            logger.error(f"Tek seferlik taramada hata: {err}")
            sys.exit(1)
        finally:
            lock.release()
        return

    if args.daemon:
        logger.info("=" * 60)
        logger.info("İHALE TAKİP BOTU - SÜREKLİ ÇALIŞMA (DAEMON) MODU")
        logger.info("=" * 60)
        
        # Çalışma aralığını alan helper çağrısı
        interval_minutes = get_check_interval()
        logger.info(f"Bot başlatıldı. Tarama sıklığı: {interval_minutes} dakika.")
        
        from src.process_lock import ProcessLock
        lock = ProcessLock("scan")
        
        try:
            while True:
                if lock.acquire():
                    try:
                        orchestrator.run_once()
                    except Exception as e:
                        logger.error(f"Daemon döngüsünde beklenmeyen hata: {e}")
                    finally:
                        lock.release()
                else:
                    logger.warning("Beklemede: Başka bir tarama veya re-evaluation işlemi çalışıyor. Sonraki döngüde tekrar denenecek.")
                
                logger.info(f"Bekleme moduna geçiliyor. Sonraki tarama {interval_minutes} dakika sonra.")
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            logger.info("Bot kullanıcı tarafından sonlandırıldı.")
            sys.exit(0)

if __name__ == "__main__":
    main()
