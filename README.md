# İhale Takip Sistemi (Tender Tracker) Kullanım ve Dağıtım Kılavuzu

Tender Tracker; farklı kaynaklardan (Yatırımlar Dergisi, DMO, ilan.gov.tr, EKAPv2) ihaleleri otomatik olarak toplayan, kural tabanlı yerel filtrelerden ve LLM (Gemini, OpenAI, Claude) tabanlı akıllı süzgeçlerden geçirerek ilgili ihaleleri e-posta ve Telegram üzerinden anlık bildiren modüler bir kurumsal takip sistemidir.

---

## 📸 Ekran Görüntüleri (Arayüz Panelleri)

Uygulamanın arayüz tasarımı modern ve kullanıcı dostu bir glassmorphism stiline sahiptir. Aşağıda temel sekmelerin görünümleri yer almaktadır:

### 1. Aktif İhaleler Paneli
Sistem tarafından taranıp sınıflandırılan tüm ihalelerin listelendiği, sektöre ve kaynağa göre filtrelenebildiği ana ekrandır.
![Aktif İhaleler](screenshots/tenders.png)

### 2. Genel ve LLM Yapılandırma Paneli
Sunucu portu, tarama sıklığı, aktif kazıyıcılar, yapay zeka sağlayıcısı (Gemini, OpenAI, Claude) ve arayüz tema seçimi bu sekmeden ayarlanır.
![Genel Ayarlar](screenshots/config_general.png)

### 3. Akıllı Süzgeçler (LLM Prompts) Paneli
Yapay zeka analizinde kullanılacak olan prompt yönergelerinin tanımlandığı ve yönetildiği sekmedir.
![Akıllı Süzgeçler](screenshots/config_filters.png)

### 4. Sektörler ve Küresel Filtreler Paneli
İşletmenizin faaliyet alanlarına göre pozitif/negatif kelimelerin ve ihaleleri tamamen eleyen küresel yasaklı kelimelerin yönetildiği alandır.
![Sektörler ve Filtreler](screenshots/config_sectors.png)

### 5. Bildirim Ayarları Paneli
SMTP e-posta gönderici/alıcı bilgileri ve Telegram Bot entegrasyonu (Token, Chat ID) bilgileri bu sekmeden düzenlenir.
![Bildirim Ayarları](screenshots/config_notifications.png)

### 6. Sistem Logları Paneli
Arka planda çalışan tarayıcı botun ve sunucunun log kayıtlarını (hata ve durum analizleri) canlı olarak takip edebileceğiniz konsoldur.
![Sistem Logları](screenshots/logs.png)

---

## 🌟 Temel Özellikler

1. **Çoklu Kaynak Desteği:**
   * **Yatırımlar Dergisi:** bülten üzerindeki ihale verileri HTML parser ile çekilir.
   * **DMO:** Aktif ilan listesi taranır.
   * **ilan.gov.tr:** Platformun JSON API uçları doğrudan sorgulanarak yüksek performansla veri çekilir.
   * **EKAPv2:** SSL el sıkışma engelleri özel `TLSAdapter` ile aşılarak kamu ilanları takip edilir.

2. **İki Aşamalı Hibrit Filtreleme:**
   * **1. Aşama (Kural Tabanlı Eleme):** İhaleler önce küresel yasaklı kelimelere ve sektör kurallarına göre elenir.
   * **2. Aşama (LLM Anlamsal Analiz):** Sektör filtrelerini geçen ihaleler seçilen LLM modeline (Gemini, OpenAI, Claude) gönderilerek prompt süzgecine alınır. Bu sayede gereksiz API maliyetleri önlenir.

3. **Çok Kanallı Bildirim:**
   * **E-posta:** Sektörlere göre gruplanmış, Outlook ve mobil uyumlu HTML e-posta raporları.
   * **Telegram:** Karakter sınırı aşımında otomatik bölünerek HTML formatında anlık bildirimler.

4. **Kullanıcı Dostu Web Dashboard:**
   * **Dinamik Rota (History API):** Yönlendirmelerde `#` işareti içermeyen temiz URL'ler kullanılır. Sayfayı yenilediğinizde kaldığınız alt sekme otomatik olarak korunur.
   * **Dinamik Model Listesi:** API anahtarınızı girdiğinizde sağlayıcının güncel modelleri sunucudan otomatik olarak çekilip listelenir.
   * **8 Farklı Renk Teması:** Turkuaz, Zümrüt, Turuncu, Mor, Gül, Kehribar, Gümüş ve Kırmızı renk paletleri arasından seçim yapabilirsiniz. Seçilen tema doğrudan `config.yaml` dosyasına sunucu taraflı kaydedilir.

5. **Windows Sistem Tepsisi (System Tray) Entegrasyonu:**
   * Program çalışırken görev çubuğunda yer kaplamaz. Minimize edildiğinde sistem tepsisine gizlenir. Simgeye sağ tıklayarak arayüze erişebilir, konsolu gösterebilir veya kapatabilirsiniz.

---

## 🛠️ Sorun Giderme (Troubleshooting) Kılavuzu

Uygulamanın çalıştırılması veya yapılandırılması esnasında karşılaşabileceğiniz olası durumlar ve çözümleri aşağıda listelenmiştir:

### 1. Uygulama Açılırken "Windows SmartScreen / Defender" Uyarısı Veriyor
* **Sebep:** Derlenen `.exe` dosyası bağımsız geliştirildiği ve dijital sertifika imzasına sahip olmadığı için Windows bunu potansiyel risk olarak algılar.
* **Çözüm:** Çıkan uyarı penceresinde **"Ek Bilgi" (More Info)** yazısına tıklayın, ardından aktifleşen **"Yine de Çalıştır" (Run Anyway)** butonuna basarak uygulamayı başlatın.

### 2. Sunucu Başlatılamıyor / Port Hatası Alınıyor
* **Sebep:** Programın çalıştığı port (varsayılan `8000`) bilgisayarınızdaki başka bir program (IIS, Docker, XAMPP vb.) tarafından kullanılıyor olabilir.
* **Çözüm:** Programın bulunduğu dizindeki `config.yaml` dosyasını not defteri ile açın, `settings` altındaki `server_port` değerini boşta olan başka bir portla (örneğin `8085`) değiştirip kaydedin ve programı yeniden başlatın.

### 3. Yasaklı/Negatif Kelimeler Girilmesine Rağmen İhaleler Elenmiyor
* **Sebep:** Küresel yasaklı kelimeleri kaydettikten sonra tarayıcı botun bunları hafızaya alması için sunucunun yeniden başlaması veya bir sonraki tarama periyodunun beklenmesi gerekir.
* **Çözüm:** Arayüzden *"Taramayı Tetikle"* butonuna basarak filtrelerin güncel halini anlık çalıştırabilir veya konsol ekranını kapatıp uygulamayı yeniden başlatarak ayarları tazeleyebilirsiniz.

### 4. Yapay Zeka (LLM) Modelleri Çekilirken Hata Alınıyor
* **Sebep:** Yanlış API anahtarı girilmiş, internet bağlantısı kopmuş veya kurumsal ağınızdaki firewall API uçlarını engelliyor olabilir.
* **Çözüm:** API anahtarınızın doğruluğunu teyit edin. Eğer proxy veya VPN kullanıyorsanız kapatıp tekrar deneyin. Loglar sekmesinden API isteklerinin detaylı hata kodlarını inceleyin.

### 5. Veritabanı veya Log Dosyası Nerede?
* Uygulama taşınabilir (portable) çalıştığı için tüm veriler `.exe` dosyasının bulunduğu dizinde saklanır:
  * `tenders.db` (SQLite Veritabanı)
  * `app.log` (Sistem Günlük Dosyası)
  * `config.yaml` ve `sectors.yaml` (Yapılandırma Dosyaları)
  Dosyaları başka bir bilgisayara taşımak isterseniz exe dosyasıyla beraber bu dosyaları da kopyalamanız yeterlidir.
