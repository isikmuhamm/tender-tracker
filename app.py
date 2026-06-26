import os
import sys
import threading
import yaml
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from src.database import init_db, get_db, Tender, User
from src.auth import verify_password, create_access_token, get_current_user
from src.scheduler import TenderBotOrchestrator

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
    if not os.path.exists(filename):
        src_path = get_resource_path(filename)
        if os.path.exists(src_path):
            try:
                import shutil
                shutil.copy(src_path, filename)
                print(f"Varsayılan {filename} kopyalandı.")
            except Exception as e:
                print(f"{filename} kopyalanırken hata: {e}")

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
                "first_seen": t.first_seen.isoformat() if t.first_seen else None
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
    """Mevcut config.yaml ve sectors.yaml içeriğini okur."""
    config_yaml = ""
    sectors_yaml = ""
    
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r", encoding="utf-8") as f:
            config_yaml = f.read()
    if os.path.exists("sectors.yaml"):
        with open("sectors.yaml", "r", encoding="utf-8") as f:
            sectors_yaml = f.read()
            
    return {
        "config_yaml": config_yaml,
        "sectors_yaml": sectors_yaml
    }

@app.post("/api/config")
def save_config(
    payload: dict,
    current_user: User = Depends(get_current_user)
):
    """Gönderilen config.yaml ve sectors.yaml içeriğini doğrular ve kaydeder."""
    config_yaml = payload.get("config_yaml")
    sectors_yaml = payload.get("sectors_yaml")
    
    # YAML geçerlilik doğrulaması
    try:
        if config_yaml:
            yaml.safe_load(config_yaml)
        if sectors_yaml:
            yaml.safe_load(sectors_yaml)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Geçersiz YAML formatı: {e}"
        )
        
    try:
        if config_yaml:
            with open("config.yaml", "w", encoding="utf-8") as f:
                f.write(config_yaml)
        if sectors_yaml:
            with open("sectors.yaml", "w", encoding="utf-8") as f:
                f.write(sectors_yaml)
        return {"success": True, "message": "Yapılandırma başarıyla güncellendi."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dosya yazma hatası: {e}"
        )

# =========================================================
# LOGS API
# =========================================================
@app.get("/api/logs")
def get_logs(current_user: User = Depends(get_current_user)):
    """Son 100 satır olay loglarını döner."""
    if not os.path.exists("events.log"):
        return {"logs": "Log dosyası henüz oluşturulmadı."}
    try:
        with open("events.log", "r", encoding="utf-8") as f:
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
    
    port = int(os.getenv("PORT", 8000))
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

