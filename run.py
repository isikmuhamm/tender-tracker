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
        classified = total - excluded
        
        # Sektör dağılımı
        print("=" * 60)
        print("İHALE TAKİP BOTU - VERİTABANI İSTATİSTİKLERİ")
        print("=" * 60)
        print(f"Toplam Taranan İhale: {total}")
        print(f"Elenen İhale (Küresel Filtre): {excluded}")
        print(f"Sınıflandırılan Aktif İhale: {classified}")
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
    finally:
        db.close()

def get_check_interval() -> int:
    """Tarama aralığını config.yaml settings.check_interval, env veya varsayılan 60 dakika olarak belirler."""
    import yaml
    interval = None
    
    # 1. config.yaml settings.check_interval okumayı dene
    config_path = get_data_path("config.yaml")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                interval = config.get("settings", {}).get("check_interval")
        except Exception:
            pass
            
    # 2. CHECK_INTERVAL_MINUTES env okumayı dene
    if interval is None:
        try:
            env_val = os.getenv("CHECK_INTERVAL_MINUTES")
            if env_val:
                interval = int(env_val)
        except Exception:
            pass
            
    # 3. Varsayılan değer
    if interval is None:
        interval = 60
        
    return int(interval)

def main():
    args = parse_arguments()
    
    # Varsayılan mod --once olarak kabul edilir
    if not args.stats and not args.daemon:
        args.once = True

    if args.stats:
        show_stats()
        return

    orchestrator = TenderBotOrchestrator()

    if args.once:
        logger.info("=" * 60)
        logger.info("İHALE TAKİP BOTU - TEK SEFERLİK ÇALIŞTIRMA MODU")
        logger.info("=" * 60)
        orchestrator.run_once()
        return

    if args.daemon:
        logger.info("=" * 60)
        logger.info("İHALE TAKİP BOTU - SÜREKLİ ÇALIŞMA (DAEMON) MODU")
        logger.info("=" * 60)
        
        # Çalışma aralığını alan helper çağrısı
        interval_minutes = get_check_interval()
        logger.info(f"Bot başlatıldı. Tarama sıklığı: {interval_minutes} dakika.")
        
        try:
            while True:
                try:
                    orchestrator.run_once()
                except Exception as e:
                    logger.error(f"Daemon döngüsünde beklenmeyen hata: {e}")
                
                logger.info(f"Bekleme moduna geçiliyor. Sonraki tarama {interval_minutes} dakika sonra.")
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            logger.info("Bot kullanıcı tarafından sonlandırıldı.")
            sys.exit(0)

if __name__ == "__main__":
    main()
