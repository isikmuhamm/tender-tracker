import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Text, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

# Çevresel değişkenleri yükle
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tenders.db")

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<User(username='{self.username}')>"

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
    
    # Varsayılan kullanıcı kontrolü ve oluşturulması
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            import bcrypt
            # Varsayılan şifre: admin
            hashed = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode("utf-8")
            default_admin = User(username="admin", password_hash=hashed)
            db.add(default_admin)
            db.commit()
    except Exception as e:
        print(f"Varsayılan admin kullanıcısı oluşturulurken hata: {e}")
    finally:
        db.close()

def get_db():
    """Veritabanı oturumu sağlayan generator."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
