# İhale Takip Botu & Dashboard (Tender Tracker)

Bu proje, farklı kaynaklardan (Yatırımlar Dergisi, DMO, ilan.gov.tr, EKAPv2) ihaleleri otomatik olarak toplayan, kural tabanlı yerel filtrelerden ve LLM (Gemini, OpenAI, Claude) tabanlı akıllı süzgeçlerden geçirerek ilgili ihaleleri e-posta ve Telegram üzerinden anlık bildiren modüler bir kurumsal takip sistemidir.


## 1. Kullanım Kılavuzu & Çalıştırma Yöntemleri

### A. Masaüstü / Yerel Kullanıcılar
Masaüstü kullanıcıları programı iki şekilde çalıştırabilir:

1. **Grafik Arayüz (Dashboard) ile Çalıştırma:**
   * `dist/tender-tracker.exe` dosyasına çift tıklayarak çalıştırın.
   * Program açıldığında otomatik olarak arka planda web sunucusunu (`Uvicorn`) başlatacak ve varsayılan tarayıcınızda `http://127.0.0.1:8000` adresini açacaktır.
   * Ayarlar sekmesinden portu değiştirebilir, LLM ve bildirim kanallarını yapılandırabilirsiniz.

2. **Konsol / Daemon Modu (Arayüzsüz Arka Plan):**
   * Konsoldan botu arka planda sürekli çalışacak şekilde başlatmak için:
     ```bash
     tender-tracker.exe --daemon
     ```
   * Sadece bir kerelik tarama yapıp çıkması için:
     ```bash
     tender-tracker.exe --once
     ```

### B. Sistem Tepsisinde (System Tray) Çalıştırma
Uygulama konsol tabanlı bir exe olduğu için arka planda çalışırken komut satırı penceresinin açık kalmasını istemiyorsanız şu yöntemleri kullanabilirsiniz:

1. **RBTray veya Window To Tray (Önerilen Basit Yöntem):**
   * **RBTray** gibi küçük ve ücretsiz bir Windows aracı kullanarak, açık olan `tender-tracker.exe` konsol penceresinin **Sağ Tık / Kapat (Minimize)** butonuna sağ tıklayarak pencereyi doğrudan Sistem Tepsisine (System Tray) gizleyebilirsiniz.
2. **VBScript ile Görünmez Çalıştırma:**
   * Masaüstünde `run_hidden.vbs` adında bir dosya oluşturup içine suyu yazın:
     ```vbs
     CreateObject("Wscript.Shell").Run "tender-tracker.exe --daemon", 0, True
     ```
     Bu script çalıştırıldığında, konsol penceresi tamamen görünmez olarak arka planda çalışacaktır. İşlemi sonlandırmak için Görev Yöneticisi'nden `tender-tracker.exe` işlemini kapatabilirsiniz.

---

## 2. Sunucuya Kurulum ve Canlıya Alma (Deployment)

Uygulamanın kesintisiz 7/24 çalışması için sunucu ortamına (Windows Server veya Linux Server) kurulması önerilir.

### A. Windows Server Üzerine Kurulum

Windows sunucularda en kararlı yöntem uygulamayı bir **Windows Servisi (Windows Service)** olarak kaydetmektir.

1. **NSSM (Non-Sucking Service Manager) Kullanarak Servis Kurma:**
   * [nssm.cc](https://nssm.cc/) adresinden NSSM aracını indirin.
   * Yönetici komut satırını açın ve şu komutu çalıştırın:
     ```bash
     nssm install TenderTracker
     ```
   * Açılan grafik arayüzde:
     * **Path:** `C:\path\to\dist\tender-tracker.exe`
     * **Arguments:** `__main__` (FastAPI Web API ve Botu beraber başlatır) veya sadece arka plan taraması için `--daemon`.
     * **Startup type:** Automatic
   * "Install service" butonuna basın. Servisiniz başarıyla kurulacaktır.
   * Windows Hizmetler (`services.msc`) panelinden `TenderTracker` hizmetini başlatın. Artık sunucu yeniden başlasa bile servis arka planda otomatik çalışacaktır.

2. **IIS (Internet Information Services) Arkasında Çalıştırma (Reverse Proxy):**
   * IIS kurulu ise **Application Request Routing (ARR)** ve **URL Rewrite** modüllerini yükleyin.
   * IIS üzerinde yeni bir web site tanımlayıp, gelen istekleri programın çalıştığı porta (Örn: `http://127.0.0.1:8000`) yönlendiren bir reverse proxy kuralı yazın (`web.config`):
     ```xml
     <configuration>
       <system.webServer>
         <rewrite>
           <rules>
             <rule name="TenderTrackerProxy" stopProcessing="true">
               <match url="(.*)" />
               <action type="Rewrite" url="http://127.0.0.1:8000/{R:1}" />
             </rule>
           </rules>
         </rewrite>
       </system.webServer>
     </configuration>
     ```

---

### B. Linux Server Üzerine Kurulum

Linux sunucularda (Örn: Ubuntu) systemd servis yöneticisi kullanılması en kararlı yöntemdir.

1. **Systemd Servis Dosyası Oluşturma:**
   * `/etc/systemd/system/tender-tracker.service` adında bir dosya oluşturun:
     ```ini
     [Unit]
     Description=Tender Tracker FastAPI Service
     After=network.target

     [Service]
     User=root
     WorkingDirectory=/var/www/tender-tracker
     ExecStart=/usr/bin/python3 app.py
     Restart=always
     Environment=PORT=8000 HOST=127.0.0.1

     [Install]
     WantedBy=multi-user.target
     ```
2. **Servisi Aktifleştirme:**
     ```bash
     sudo systemctl daemon-reload
     ```
     ```bash
     sudo systemctl enable tender-tracker.service
     ```
     ```bash
     sudo systemctl start tender-tracker.service
     ```
3. **Nginx ile Reverse Proxy Kurulumu:**
   * Nginx yapılandırma dosyasına (`/etc/nginx/sites-available/default`) proxy kurallarını ekleyin:
     ```nginx
     server {
         listen 80;
         server_name ihale.sirketiniz.com;

         location / {
             proxy_pass http://127.0.0.1:8000;
             proxy_set_header Host $host;
             proxy_set_header X-Real-IP $remote_addr;
             proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
         }
     }
     ```
   * Nginx servisini yeniden başlatın: `sudo systemctl restart nginx`

---

## 3. Token Tasarrufu ve LLM Maliyet Optimizasyonu

* **Sektörel Kelime Eşleşmesi (Phase 1):** Yapay zeka maliyetlerini ve token tüketimini minimumda tutmak için, **Sektörler** sekmesindeki yerel anahtar kelime tanımlarını olabildiğince daraltın.
* **LLM Ön Elemesi:** Sistem, gelen ihaleleri önce yerel anahtar kelimelere (Phase 1) göre eler. Yalnızca bu yerel filtreyi geçen ihaleler LLM'e (Phase 2) gönderilir. Bu sayede ilgisiz ihaleler için API ücreti ödemezsiniz.
