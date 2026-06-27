import os
import sys
import time
import ctypes
import threading
import webbrowser
import logging
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

class SystemTrayManager:
    """
    Windows üzerinde uygulamayı sistem tepsisine (system tray) küçülten ve yöneten sınıf.
    """
    def __init__(self, port=8000, host="127.0.0.1"):
        self.port = port
        self.host = host
        self.hwnd = None
        self.icon = None
        self.running = False
        
        # Windows Console pencere tutamacını al
        if sys.platform.startswith("win"):
            self.hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            
    def generate_icon_image(self):
        # Dinamik olarak radyo dalgası / yayın kulesi benzeri mavi renkli bir ikon çizer
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        # Dış halka
        draw.ellipse((8, 8, 56, 56), outline="#38bdf8", width=5)
        # İç halka
        draw.ellipse((20, 20, 44, 44), outline="#0284c7", width=5)
        # Merkez nokta
        draw.ellipse((28, 28, 36, 36), fill="#0ea5e9")
        return image
        
    def show_console(self):
        if self.hwnd:
            # SW_RESTORE = 9
            ctypes.windll.user32.ShowWindow(self.hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(self.hwnd)
            logger.info("Konsol penceresi geri yüklendi.")
            
    def hide_console(self):
        if self.hwnd:
            # SW_HIDE = 0
            ctypes.windll.user32.ShowWindow(self.hwnd, 0)
            logger.info("Konsol penceresi gizlendi (sistem tepsisinde çalışmaya devam ediyor).")
            
    def open_dashboard(self):
        try:
            webbrowser.open(f"http://{self.host}:{self.port}/")
        except Exception as e:
            logger.error(f"Dashboard açılırken hata oluştu: {e}")
            
    def stop_app(self):
        logger.info("Uygulama kapatılıyor...")
        if self.icon:
            self.icon.stop()
        # Ana süreci tamamen sonlandır
        os._exit(0)
        
    def setup_tray(self):
        import pystray
        
        menu = pystray.Menu(
            pystray.MenuItem("Arayüzü Aç (Dashboard)", self.open_dashboard, default=True),
            pystray.MenuItem("Konsolu Göster", self.show_console),
            pystray.MenuItem("Konsolu Gizle", self.hide_console),
            pystray.MenuItem("Kapat (Çıkış)", self.stop_app)
        )
        
        self.icon = pystray.Icon(
            "TenderTracker",
            self.generate_icon_image(),
            title="Tender Tracker - İhale Takip Botu",
            menu=menu
        )
        
    def monitor_console(self):
        if not self.hwnd:
            return
            
        first_hide = True
        while self.running:
            try:
                # IsIconic: Pencere simge durumuna küçültülmüşse (minimize) True döner
                is_minimized = ctypes.windll.user32.IsIconic(self.hwnd)
                # IsWindowVisible: Pencere görünür durumdaysa True döner
                is_visible = ctypes.windll.user32.IsWindowVisible(self.hwnd)
                
                if is_minimized and is_visible:
                    # Pencereyi görev çubuğundan tamamen gizle
                    self.hide_console()
                    if first_hide and self.icon:
                        self.icon.notify(
                            "Tender Tracker sistem tepsisine küçültüldü. Yönetmek için simgeye sağ tıklayabilirsiniz.",
                            title="İhale Takip Botu"
                        )
                        first_hide = False
            except Exception as e:
                logger.error(f"Pencere durumu izlenirken hata: {e}")
            time.sleep(1)
            
    def run(self):
        self.running = True
        self.setup_tray()
        
        # Konsol küçültme durumunu izleyen arka plan iş parçacığı
        monitor_thread = threading.Thread(target=self.monitor_console, daemon=True)
        monitor_thread.start()
        
        logger.info("Sistem tepsisi servisi aktif edildi.")
        self.icon.run()
