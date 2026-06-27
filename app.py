import os
import sys
import threading
import yaml
import logging
import urllib3
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from src.database import init_db, get_db, Tender, User, get_data_path
from src.auth import verify_password, create_access_token, get_current_user
from src.scheduler import TenderBotOrchestrator

# Urllib3 HTTPS sertifika uyarılarını kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

app = FastAPI(title="Tender Tracker API", version="1.0.0")

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
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Filtrelenebilir ihale listesini döner."""
    query = db.query(Tender)
    if sector:
        query = query.filter_by(sector=sector)
    if source:
        query = query.filter_by(source=source)
        
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

@app.post("/api/tenders/trigger")
def trigger_scraper(current_user: User = Depends(get_current_user)):
    """Tarayıcı botunu arka planda tek seferlik tetikler."""
    def run_scraper_bg():
        try:
            orch = TenderBotOrchestrator()
            orch.run_once()
        except Exception as e:
            print(f"Arka plan tarama hatası: {e}")
            
    threading.Thread(target=run_scraper_bg).start()
    return {"success": True, "message": "Tarama işlemi arka planda başlatıldı."}

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
def get_models(provider: str, api_key: str = None, current_user: User = Depends(get_current_user)):
    """
    Belirtilen LLM sağlayıcısı ve API key için kullanılabilecek model listesini çeker.
    Eğer API key sağlanmamışsa, kayıtlı config.yaml dosyasından okumayı dener.
    Eğer hata oluşursa veya API key geçersizse varsayılan model listesini döner.
    """
    import requests
    defaults = {
        "gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
        "openai": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        "claude": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]
    }
    
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
        return {"models": defaults.get(provider, [])}
        
    try:
        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                models = [m["name"].split("/")[-1] for m in data.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
                if models:
                    return {"models": models}
        elif provider == "openai":
            base_url = "https://api.openai.com/v1"
            config_path = get_data_path("config.yaml")
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                        base_url = cfg.get("settings", {}).get("llm_providers", {}).get("openai", {}).get("base_url", base_url)
                except Exception:
                    pass
            url = f"{base_url.rstrip('/')}/models"
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
        logging.error(f"Modeller çekilirken hata: {e}")
        
    return {"models": defaults.get(provider, [])}

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
        time.sleep(1.5)
        try:
            webbrowser.open(f"http://{host}:{port}/")
        except Exception as e:
            print(f"Tarayıcı açılırken hata oluştu: {e}")
            
    threading.Thread(target=open_browser, daemon=True).start()
    
    print(f"Sunucu başlatılıyor: http://{host}:{port}/")
    uvicorn.run(app, host=host, port=port)

