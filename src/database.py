import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Text, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

# Çevresel değişkenleri yükle
load_dotenv()

def get_data_path(filename: str) -> str:
    """PyInstaller ile derlendiğinde exe dosyasının yanındaki dosya yolunu,
    geliştirme modunda ise mevcut çalışma dizinindeki yolu döner."""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(".")
    return os.path.join(base_dir, filename)

db_url = os.getenv("DATABASE_URL")
if not db_url:
    DATABASE_URL = f"sqlite:///{get_data_path('tenders.db')}"
else:
    DATABASE_URL = db_url

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
    
    # Akıllı süzgeç etiketleri (virgülle ayrılmış ID'ler)
    matched_custom_filters = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Tender(title='{self.title[:30]}...', source='{self.source}', sector='{self.sector}')>"

class SystemState(Base):
    __tablename__ = 'system_states'

    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Engine ve Session tanımları
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Veritabanı tablolarını oluşturur."""
    # SQLite için WAL modunu aktif edelim (concurrency iyileştirmesi)
    if DATABASE_URL.startswith("sqlite"):
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

def get_last_success_at(db, source_name: str):
    """
    Belirtilen kaynak için veritabanından en son başarılı tarama tarihini çeker.
    Dönen değer datetime nesnesi veya None'dır.
    """
    state = db.query(SystemState).filter_by(key=f"last_success_at:{source_name}").first()
    if state and state.value:
        try:
            from datetime import datetime
            return datetime.fromisoformat(state.value)
        except Exception:
            return None
    return None

def set_last_success_at(db, source_name: str, scan_started_at):
    """
    Belirtilen kaynak için en son başarılı tarama tarihini veritabanında günceller.
    """
    key = f"last_success_at:{source_name}"
    state = db.query(SystemState).filter_by(key=key).first()
    val_str = scan_started_at.isoformat()
    if not state:
        state = SystemState(key=key, value=val_str)
        db.add(state)
    else:
        state.value = val_str
        from datetime import datetime, timezone
        state.updated_at = datetime.now(timezone.utc)
    db.commit()

