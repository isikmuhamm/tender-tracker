import os
import sys
import threading
import yaml
import logging
import urllib3
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from src.database import init_db, get_db, Tender, User, get_data_path, turkish_lower
from src.auth import verify_password, create_access_token, get_current_user
from src.scheduler import TenderBotOrchestrator
import datetime
from threading import Lock

class JobState:
    def __init__(self):
        self.lock = Lock()
        self.status = "idle"  # "idle", "scanning", "re_evaluating"
        self.last_run_time = None
        self.last_run_status = "idle"  # "idle", "success", "failed", "partial"
        self.error_message = None
        self.last_result = None

    def start_job(self, job_type: str) -> bool:
        with self.lock:
            if self.status != "idle":
                return False
            self.status = job_type
            self.error_message = None
            self.last_result = None
            return True

    def finish_job(self, success: bool, error_msg: str = None, result: dict = None):
        with self.lock:
            self.status = "idle"
            self.last_run_time = datetime.datetime.now().isoformat()
            if result:
                self.last_run_status = result.get("status", "success")
            else:
                self.last_run_status = "success" if success else "failed"
            self.error_message = error_msg
            self.last_result = result

job_state = JobState()

# Global logging yapılandırması
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Dosya handler (events.log)
log_path = get_data_path("events.log")
file_handler = logging.FileHandler(log_path, encoding="utf-8")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

# Stream handler (Konsol)
if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in logger.handlers):
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

app = FastAPI(title="Tender Tracker API", version="1.3.1")

def run_startup_scan():
    """Uygulama başladığında otomatik taramayı arka planda başlatır."""
    if "pytest" in sys.modules:
        logger.info("Otomatik başlangıç taraması atlandı: Test ortamındayız.")
        return
        
    from src.process_lock import ProcessLock
    
    if not job_state.start_job("scanning"):
        logger.info("Otomatik başlangıç taraması atlandı: Sistem zaten meşgul.")
        return
        
    lock = ProcessLock("scan")
    if not lock.acquire():
        job_state.finish_job(False, "Başka bir tarama işlemi (CLI daemon veya eşzamanlı istek) çalışıyor.")
        logger.info("Otomatik başlangıç taraması atlandı: ProcessLock alınamadı.")
        return
        
    def run_scraper_bg():
        try:
            logger.info("Otomatik başlangıç taraması başlatılıyor...")
            orch = TenderBotOrchestrator()
            result = orch.run_once()
            job_state.finish_job(True, result=result)
            logger.info("Otomatik başlangıç taraması başarıyla tamamlandı.")
        except Exception as e:
            logger.error(f"Otomatik başlangıç tarama hatası: {e}", exc_info=True)
            job_state.finish_job(False, str(e))
        finally:
            lock.release()
            
    threading.Thread(target=run_scraper_bg, daemon=True).start()

@app.on_event("startup")
def startup_event():
    run_startup_scan()

def get_resource_path(relative_path):
    """PyInstaller geçici klasöründeki veya çalışma dizinindeki dosya yolunu çözümler."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

static_dir = get_resource_path("static")

# Geliştirme modunda static klasörü oluşturulabilir
if not getattr(sys, 'frozen', False):
    os.makedirs(static_dir, exist_ok=True)
    os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
    os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)

# Varsayılan konfigürasyon dosyalarını kopyala (yerelde yoksa)
for filename in ["config.yaml", "sectors.yaml"]:
    dest_path = get_data_path(filename)
    if not os.path.exists(dest_path):
        src_path = get_resource_path(filename)
        if os.path.exists(src_path):
            try:
                import shutil
                shutil.copy(src_path, dest_path)
                logging.info(f"Varsayılan {filename} kopyalandı -> {dest_path}")
            except Exception as e:
                logging.error(f"{filename} kopyalanırken hata: {e}")

# Static dosyaları yönlendir
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Arayüz dosyaları bulunamadı. Lütfen static/index.html'i yükleyin."}

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    favicon_path = os.path.join(static_dir, "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return {"message": "Favicon not found"}

# =========================================================
# AUTH API
# =========================================================
@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Kullanıcı adı ve şifre ile giriş yapıp JWT token döner."""
    user = db.query(User).filter_by(username=form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adı veya şifre hatalı.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/setup-status")
def get_setup_status(db: Session = Depends(get_db)):
    """Yönetici hesabı kurulu mu kontrol eder."""
    user_count = db.query(User).count()
    return {"setup_required": user_count == 0}

@app.post("/api/auth/setup")
def setup_admin(payload: dict, db: Session = Depends(get_db)):
    """İlk açılışta yönetici hesabı oluşturur."""
    if db.query(User).count() > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kurulum zaten tamamlanmış. Yeni yönetici eklenemez."
        )
        
    username = payload.get("username")
    password = payload.get("password")
    
    if not username or not password or len(password) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kullanıcı adı ve şifre gereklidir. Şifre en az 4 karakter olmalıdır."
        )
        
    from src.auth import get_password_hash
    hashed_password = get_password_hash(password)
    user = User(username=username, password_hash=hashed_password)
    db.add(user)
    db.commit()
    
    return {"success": True, "message": "Yönetici hesabı başarıyla oluşturuldu."}

@app.post("/api/auth/change-password")
def change_password(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aktif kullanıcının şifresini değiştirir."""
    old_password = payload.get("old_password")
    new_password = payload.get("new_password")
    
    if not old_password or not new_password or len(new_password) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mevcut ve yeni şifre gereklidir. Yeni şifre en az 4 karakter olmalıdır."
        )
        
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mevcut şifre hatalı."
        )
        
    from src.auth import get_password_hash
    current_user.password_hash = get_password_hash(new_password)
    db.commit()
    
    return {"success": True, "message": "Şifre başarıyla güncellendi."}

# =========================================================
# TENDERS API
# =========================================================
@app.get("/api/tenders")
def get_tenders(
    sector: str = None,
    source: str = None,
    search: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Filtrelenebilir ihale listesini döner."""
    from sqlalchemy import or_
    query = db.query(Tender)
    if sector:
        query = query.filter_by(sector=sector)
    if source:
        query = query.filter_by(source=source)
    if search:
        from sqlalchemy import func, or_
        search_filter = f"%{turkish_lower(search)}%"
        query = query.filter(
            or_(
                func.turkish_lower(Tender.title).like(search_filter),
                func.turkish_lower(Tender.summary).like(search_filter),
                func.turkish_lower(Tender.category).like(search_filter)
            )
        )
        
    total = query.count()
    # En son görülen ihale en üstte olacak şekilde sırala
    items = query.order_by(Tender.first_seen.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "items": [
            {
                "link": t.link,
                "title": t.title,
                "summary": t.summary,
                "category": t.category,
                "source": t.source,
                "sector": t.sector,
                "first_seen": t.first_seen.isoformat() if t.first_seen else None,
                "matched_custom_filters": t.matched_custom_filters
            }
            for t in items
        ]
    }

@app.get("/api/job/status")
def get_job_status(current_user: User = Depends(get_current_user)):
    """Arka planda çalışan tarama veya yeniden değerlendirme işlemlerinin durumunu döner."""
    return {
        "status": job_state.status,
        "last_run_time": job_state.last_run_time,
        "last_run_status": job_state.last_run_status,
        "error_message": job_state.error_message,
        "result": job_state.last_result
    }

@app.post("/api/tenders/trigger")
def trigger_scraper(current_user: User = Depends(get_current_user)):
    """Tarayıcı botunu arka planda tek seferlik tetikler."""
    from src.process_lock import ProcessLock
    
    if not job_state.start_job("scanning"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Sistem zaten meşgul: Arka planda {job_state.status} işlemi çalışıyor."
        )
        
    lock = ProcessLock("scan")
    if not lock.acquire():
        job_state.finish_job(False, "Başka bir tarama işlemi (CLI daemon veya eşzamanlı istek) çalışıyor.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sistem zaten meşgul: Arka planda CLI daemon veya başka bir tarama çalışıyor."
        )
        
    def run_scraper_bg():
        try:
            orch = TenderBotOrchestrator()
            result = orch.run_once()
            job_state.finish_job(True, result=result)
        except Exception as e:
            logger.error(f"Arka plan tarama hatası: {e}", exc_info=True)
            job_state.finish_job(False, str(e))
        finally:
            lock.release()
            
    threading.Thread(target=run_scraper_bg).start()
    return {"success": True, "message": "Tarama işlemi arka planda başlatıldı."}

@app.post("/api/tenders/re-evaluate")
def re_evaluate_tenders(current_user: User = Depends(get_current_user)):
    """Veritabanındaki mevcut ihaleleri yeni süzgeç kurallarına göre arka planda yeniden değerlendirir."""
    from src.process_lock import ProcessLock
    
    if not job_state.start_job("re_evaluating"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Sistem zaten meşgul: Arka planda {job_state.status} işlemi çalışıyor."
        )
        
    lock = ProcessLock("scan")
    if not lock.acquire():
        job_state.finish_job(False, "Başka bir tarama işlemi (CLI daemon veya eşzamanlı istek) çalışıyor.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sistem zaten meşgul: Arka planda CLI daemon veya başka bir tarama çalışıyor."
        )
        
    def run_re_evaluation_bg():
        from src.database import SessionLocal
        from src.classifier import TenderClassifier
        
        db_session = SessionLocal()
        try:
            # 1. Config'i yükle
            config_path = get_data_path("config.yaml")
            if not os.path.exists(config_path):
                raise ValueError("config.yaml bulunamadı.")
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
                
            filters = config_data.get("filters", {})
            custom_filters = filters.get("custom_llm_filters", [])
            
            # 2. Sınıflandırıcıyı başlat
            classifier = TenderClassifier()
            if not classifier.ai_enabled:
                logger.warning("LLM aktif değil, yeniden değerlendirme yapılmadı.")
                # Her ihalenin süzgecini temizleyelim
                tenders = db_session.query(Tender).all()
                for t in tenders:
                    t.matched_custom_filters = None
                db_session.commit()
                job_state.finish_job(True, result={"status": "success", "records_added": 0})
                return
                
            # 3. Veritabanından elenmemiş ihaleleri çek
            tenders = db_session.query(Tender).filter(Tender.sector.isnot(None), Tender.sector != "Excluded").all()
            logger.info(f"{len(tenders)} ihale akıllı süzgeçlerle yeniden değerlendiriliyor...")
            
            for t in tenders:
                matched_ids = classifier.evaluate_custom_filters(
                    t.title, t.summary, custom_filters, sector=t.sector
                )
                if matched_ids:
                    t.matched_custom_filters = ",".join(matched_ids)
                else:
                    t.matched_custom_filters = None
                db_session.commit()
                
            logger.info("İhalelerin akıllı süzgeç değerlendirmeleri başarıyla güncellendi.")
            job_state.finish_job(True, result={"status": "success", "records_added": len(tenders)})
        except Exception as e:
            logger.error(f"İhaleler yeniden değerlendirilirken hata: {e}")
            job_state.finish_job(False, str(e))
        finally:
            db_session.close()
            lock.release()
            
    threading.Thread(target=run_re_evaluation_bg).start()
    return {"success": True, "message": "Yeniden değerlendirme işlemi arka planda başlatıldı."}

# =========================================================
# CONFIG API
# =========================================================
@app.get("/api/config")
def get_config(current_user: User = Depends(get_current_user)):
    """Mevcut yapılandırma (config.yaml ve sectors.yaml) verilerini JSON olarak okur."""
    config_data = {}
    sectors_data = {}
    
    config_path = get_data_path("config.yaml")
    sectors_path = get_data_path("sectors.yaml")
    
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            try:
                config_data = yaml.safe_load(f) or {}
            except Exception as e:
                logging.error(f"config.yaml ayrıştırılırken hata: {e}")
                
    if os.path.exists(sectors_path):
        with open(sectors_path, "r", encoding="utf-8") as f:
            try:
                sectors_data = yaml.safe_load(f) or {}
            except Exception as e:
                logging.error(f"sectors.yaml ayrıştırılırken hata: {e}")
                
    return {
        "config": config_data,
        "sectors": sectors_data
    }

@app.post("/api/config")
def save_config(
    payload: dict,
    current_user: User = Depends(get_current_user)
):
    """Gönderilen JSON yapılandırma verilerini doğrular ve YAML dosyalarına kaydeder."""
    config_data = payload.get("config")
    sectors_data = payload.get("sectors")
    
    config_path = get_data_path("config.yaml")
    sectors_path = get_data_path("sectors.yaml")
    
    try:
        if config_data is not None:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(config_data, f, allow_unicode=True, sort_keys=False)
                
        if sectors_data is not None:
            with open(sectors_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(sectors_data, f, allow_unicode=True, sort_keys=False)
                
        return {"success": True, "message": "Yapılandırma başarıyla güncellendi."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dosyalar kaydedilirken hata oluştu: {e}"
        )

@app.get("/api/models")
def get_models(
    provider: str,
    base_url: Optional[str] = None,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    current_user: User = Depends(get_current_user)
):
    """
    Belirtilen LLM sağlayıcısı ve API key için kullanılabilecek model listesini çeker.
    Eğer API key sağlanmamışsa, kayıtlı config.yaml dosyasından okumayı dener.
    Eğer hata oluşursa veya API key geçersizse boş liste döner.
    """
    import requests
    
    api_key = x_api_key
    if not api_key:
        config_path = get_data_path("config.yaml")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                    providers = cfg.get("settings", {}).get("llm_providers", {})
                    p_cfg = providers.get(provider, {})
                    api_key = p_cfg.get("api_key")
            except Exception:
                pass
                
    if not api_key:
        return {"models": []}
        
    try:
        if provider == "gemini":
            url = "https://generativelanguage.googleapis.com/v1beta/models"
            res = requests.get(url, headers={"x-goog-api-key": api_key}, timeout=5)
            if res.status_code == 200:
                data = res.json()
                models = [m["name"].split("/")[-1] for m in data.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
                if models:
                    return {"models": models}
        elif provider == "openai":
            api_base = base_url
            if not api_base:
                api_base = "https://api.openai.com/v1"
                config_path = get_data_path("config.yaml")
                if os.path.exists(config_path):
                    try:
                        with open(config_path, "r", encoding="utf-8") as f:
                            cfg = yaml.safe_load(f) or {}
                            api_base = cfg.get("settings", {}).get("llm_providers", {}).get("openai", {}).get("base_url", api_base)
                    except Exception:
                        pass
            url = f"{api_base.rstrip('/')}/models"
            res = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=5)
            if res.status_code == 200:
                data = res.json()
                models = [m["id"] for m in data.get("data", [])]
                if models:
                    return {"models": sorted(models)}
        elif provider == "claude":
            url = "https://api.anthropic.com/v1/models"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                models = [m["id"] for m in data.get("data", [])]
                if models:
                    return {"models": models}
    except Exception as e:
        err_msg = str(e)
        if api_key:
            err_msg = err_msg.replace(api_key, "HIDDEN_KEY")
        logging.error(f"Modeller çekilirken hata: {err_msg}")
        
    return {"models": []}

# =========================================================
# LOGS API
# =========================================================
@app.get("/api/logs")
def get_logs(current_user: User = Depends(get_current_user)):
    """Son 100 satır olay loglarını döner."""
    log_path = get_data_path("events.log")
    if not os.path.exists(log_path):
        return {"logs": "Log dosyası henüz oluşturulmadı."}
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return {"logs": "".join(lines[-100:])}
    except Exception as e:
        return {"logs": f"Loglar okunurken hata: {e}"}

@app.get("/{catchall:path}")
def catch_all(catchall: str):
    if catchall.startswith("api/") or catchall.startswith("static/"):
        raise HTTPException(status_code=404, detail="Bulunamadı")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Arayüz dosyaları bulunamadı. Lütfen static/index.html'i yükleyin."}

# Veritabanını uygulama başlarken hazırla
init_db()

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import time
    
    # Port bilgisini config.yaml'dan okumayı dene
    port = 8000
    config_path = get_data_path("config.yaml")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                if cfg and "settings" in cfg:
                    port = int(cfg["settings"].get("server_port", port))
        except Exception:
            pass
            
    port = int(os.getenv("PORT", port))
    host = os.getenv("HOST", "127.0.0.1")
    
    def open_browser():
        if os.getenv("NO_BROWSER") == "true":
            return
        time.sleep(1.5)
        try:
            webbrowser.open(f"http://{host}:{port}/")
        except Exception as e:
            print(f"Tarayıcı açılırken hata oluştu: {e}")
            
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Sistem tepsisi (system tray) simgesini arka planda başlat (yalnızca Windows)
    if sys.platform.startswith("win"):
        try:
            from src.tray import SystemTrayManager
            tray_mgr = SystemTrayManager(port=port, host=host)
            threading.Thread(target=tray_mgr.run, daemon=True).start()
        except Exception as e:
            print(f"Sistem tepsisi simgesi başlatılamadı: {e}")
            
    print(f"Sunucu başlatılıyor: http://{host}:{port}/")
    uvicorn.run(app, host=host, port=port)

