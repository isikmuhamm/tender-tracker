import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# Çevresel değişkenleri yükle
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tenders.db")

Base = declarative_base()

class Tender(Base):
    __tablename__ = 'tenders'

    link = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    source = Column(String, nullable=False)  # 'yatirimlar', 'dmo', 'ilan_gov_tr'
    sector = Column(String, nullable=True)  # Sektör sınıflandırması
    classification_method = Column(String, nullable=True)  # 'rule' veya 'ai'
    first_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Bildirim gönderim durumları
    email_sent = Column(Boolean, default=False)
    telegram_sent = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Tender(title='{self.title[:30]}...', source='{self.source}', sector='{self.sector}')>"

# Engine ve Session tanımları
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Veritabanı tablolarını oluşturur."""
    # SQLite için WAL modunu aktif edelim (concurrency iyileştirmesi)
    if DATABASE_URL.startswith("sqlite"):
        # sqlite connection alıp WAL modunu ayarlıyoruz
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
    Base.metadata.create_all(bind=engine)

def get_db():
    """Veritabanı oturumu sağlayan generator."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
