import os
import sys
import shutil
import PyInstaller.__main__

# Ensure stdout encodes UTF-8 characters correctly on runners
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def build():
    print("Ihale Takip Botu - Tekil Calistirilabilir (.exe) Derleme Islemi")
    print("=" * 60)
    
    # Mevcut build ve dist klasörlerini temizle
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"Eski '{folder}' klasoru temizlendi.")
            except Exception as e:
                print(f"'{folder}' klasoru temizlenirken hata: {e}")
                
    # İşletim sistemine uygun yol ayracını belirle (Windows için ;, Unix için :)
    sep = ";" if sys.platform.startswith("win") else ":"
    
    args = [
        "app.py",
        "--onefile",
        "--name=tender-tracker",
        f"--add-data=static{sep}static",
        f"--add-data=config.yaml{sep}.",
        f"--add-data=sectors.yaml{sep}.",
        # console modda çalıştırıyoruz ki kullanıcı logları görebilsin
        "--console",
        "--icon=app_icon.ico",
        # Uvicorn ve FastAPI için gizli importlar
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.loops.asyncio",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.http.h11_impl",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.protocols.websockets.wsproto_impl",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=uvicorn.lifespan.off",
        "--hidden-import=bcrypt",
        "--hidden-import=sqlite3",
        "--hidden-import=pystray",
        "--hidden-import=PIL",
    ]
    
    print(f"PyInstaller su parametrelerle calistiriliyor: {' '.join(args)}")
    print("=" * 60)
    
    try:
        PyInstaller.__main__.run(args)
        print("=" * 60)
        print("Derleme islemi BASARIYLA tamamlandi!")
        print("Calistirilabilir dosya: dist/tender-tracker.exe (veya ilgili OS uzantisi)")
    except Exception as e:
        print("=" * 60)
        print(f"Derleme sirasinda HATA olustu: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()
