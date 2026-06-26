import requests
import sqlite3
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import sys
import argparse

# =========================================================
# LOGGING SETUP
# =========================================================

BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "events.log"

# Terminal handler - tüm detayları gösterir
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# File handler - sadece özet loglar
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.CRITICAL)  # Sadece manuel olarak ekleyeceğimiz özetler
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler]
)

logger = logging.getLogger(__name__)

# Dosyaya özet yazmak için ayrı logger
file_logger = logging.getLogger('file_summary')
file_logger.setLevel(logging.CRITICAL)
file_logger.addHandler(file_handler)
file_logger.propagate = False

# =========================================================
# PATHS
# =========================================================

DB = BASE_DIR / "yatirimlar.db"
CONFIG_FILE = BASE_DIR / "config.env"
URL = "https://yatirimlar.com"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================================================
# LOAD CONFIG
# =========================================================

def load_config():
    logger.info(f"Config dosyası okunuyor: {CONFIG_FILE}")
    try:
        config = {}
        with open(CONFIG_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()
        logger.info(f"Config başarıyla yüklendi. {len(config)} ayar okundu.")
        return config
    except FileNotFoundError:
        logger.error(f"Config dosyası bulunamadı: {CONFIG_FILE}")
        raise
    except Exception as e:
        logger.error(f"Config yüklenirken hata: {e}")
        raise

CFG = load_config()

SMTP_HOST = CFG["SMTP_HOST"]
SMTP_PORT = int(CFG["SMTP_PORT"])
SMTP_USE_TLS = CFG["SMTP_USE_TLS"].lower() == "true"

MAIL_FROM = CFG["MAIL_FROM"]
MAIL_PASSWORD = CFG["MAIL_PASSWORD"]
MAIL_TO = [m.strip() for m in CFG["MAIL_TO"].split(",")]

# =========================================================
# DEMİRYOLU KEYWORDS
# =========================================================

RAIL_KEYWORDS = [
    "tcdd", "tcdd taşımacılık", "aygm", "dlh",
    "demiryolu", "demir yolu", "raylı", "raylı sistem",
    "sinyalizasyon", "elektrifikasyon", "katener",
    "makas", "hat kesimi","tren",
    "yüksek hızlı tren", "yht",
    "banliyö", "metro", "tramvay",
    "istasyon", "gar", "depo sahası"
]

# =========================================================
# DB
# =========================================================

def init_db():
    logger.info(f"Veritabanı başlatılıyor: {DB}")
    try:
        with sqlite3.connect(DB) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    link TEXT PRIMARY KEY,
                    title TEXT,
                    category TEXT,
                    summary TEXT,
                    first_seen DATE,
                    mail_sent INTEGER DEFAULT 0
                )
            """)
            # Eski tabloya mail_sent sütunu ekle (eğer yoksa)
            try:
                c.execute("ALTER TABLE news ADD COLUMN mail_sent INTEGER DEFAULT 0")
                logger.info("mail_sent sütunu eklendi.")
            except sqlite3.OperationalError:
                pass  # Sütun zaten var
        logger.info("Veritabanı başarıyla hazırlandı.")
    except Exception as e:
        logger.error(f"Veritabanı başlatma hatası: {e}")
        raise

# =========================================================
# FETCH
# =========================================================

def fetch_html():
    logger.info(f"HTML çekiliyor: {URL}")
    try:
        r = requests.get(URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        logger.info(f"HTML başarıyla alındı. Boyut: {len(r.text)} karakter")
        return r.text
    except requests.exceptions.Timeout:
        logger.error("İstek zaman aşımına uğradı (30 saniye)")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP isteği başarısız: {e}")
        raise

# =========================================================
# RAIL SCORE
# =========================================================

def rail_score(title, summary):
    t = title.lower()
    s = (summary or "").lower()
    score = 0
    for kw in RAIL_KEYWORDS:
        if kw in t:
            score += 2
        elif kw in s:
            score += 1
    return score

# =========================================================
# PARSE + STORE
# =========================================================

def process(html):
    logger.info("HTML parse ediliyor ve yeni haberler aranıyor...")
    try:
        soup = BeautifulSoup(html, "html.parser")
        today = datetime.today().date().isoformat()

        conn = sqlite3.connect(DB)
        cur = conn.cursor()

        new_items = []
        
        links = soup.select("a[href*='/haber/']")
        logger.info(f"Toplam {len(links)} haber linki bulundu.")

        for a in links:
            title = a.get_text(strip=True)
            link = a["href"]

            if not title or len(title) < 10:
                continue

            container = a.find_parent(["div", "article"])
            if not container:
                continue

            cat = container.select_one(".post-category")
            category = cat.get_text(strip=True) if cat else ""

            p = container.find("p")
            summary = p.get_text(strip=True) if p else ""

            cur.execute("SELECT summary FROM news WHERE link = ?", (link,))
            row = cur.fetchone()

            if row is None:
                cur.execute("""
                    INSERT INTO news (link, title, category, summary, first_seen, mail_sent)
                    VALUES (?, ?, ?, ?, ?, 0)
                """, (link, title, category, summary, today))

                new_items.append({
                    "Kategori": category,
                    "Başlık": title,
                    "Açıklama": summary,
                    "Link": link
                })

            else:
                old_summary = row[0] or ""
                if not old_summary and summary:
                    cur.execute(
                        "UPDATE news SET summary=? WHERE link=?",
                        (summary, link)
                    )

        conn.commit()
        conn.close()
        logger.info(f"İşlem tamamlandı. {len(new_items)} yeni haber bulundu.")
        return new_items
    except Exception as e:
        logger.error(f"HTML işleme hatası: {e}", exc_info=True)
        raise

def get_unsent_news():
    """Mail gönderilmemiş haberleri getir (yeni + eski başarısızlar)"""
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT link, title, category, summary 
            FROM news 
            WHERE mail_sent = 0
            ORDER BY first_seen DESC
        """)
        
        rows = cur.fetchall()
        conn.close()
        
        items = []
        for row in rows:
            items.append({
                "Link": row[0],
                "Başlık": row[1],
                "Kategori": row[2],
                "Açıklama": row[3]
            })
        
        return items
    except Exception as e:
        logger.error(f"Gönderilmemiş haberler alınırken hata: {e}")
        return []

def mark_as_sent(items):
    """Başarıyla gönderilen haberleri işaretle"""
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        
        links = [item["Link"] for item in items]
        placeholders = ','.join('?' * len(links))
        
        cur.execute(f"""
            UPDATE news 
            SET mail_sent = 1 
            WHERE link IN ({placeholders})
        """, links)
        
        conn.commit()
        conn.close()
        logger.info(f"{len(items)} haber gönderildi olarak işaretlendi.")
    except Exception as e:
        logger.error(f"Haberler işaretlenirken hata: {e}")

# =========================================================
# GET ALL NEWS (for report)
# =========================================================

def get_all_news():
    """Tüm haberleri getir (rapor için)"""
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT link, title, category, summary, first_seen
            FROM news 
            ORDER BY first_seen DESC
        """)
        
        rows = cur.fetchall()
        conn.close()
        
        items = []
        for row in rows:
            items.append({
                "Link": row[0],
                "Başlık": row[1],
                "Kategori": row[2],
                "Açıklama": row[3],
                "Tarih": row[4]
            })
        
        logger.info(f"Toplam {len(items)} haber bulundu.")
        return items
    except Exception as e:
        logger.error(f"Tüm haberler alınırken hata: {e}")
        return []

# =========================================================
# MAIL
# =========================================================

def build_subject(rail_count, total, is_full_report=False):
    today = datetime.now().strftime("%d.%m.%Y")
    icon = "🚆 " if rail_count > 0 else ""
    if is_full_report:
        return f"{icon}Yatırımlar Dergisi – {today} – TÜM HABERLER RAPORU ({total})"
    return f"{icon}Yatırımlar Dergisi Script – {today} – Günlük Yeni Haberler ({total})"

def send_mail(items, recipient_override=None, is_full_report=False):
    if not items:
        logger.info("Gönderilecek haber yok.")
        return

    recipients = [recipient_override] if recipient_override else MAIL_TO
    logger.info(f"Mail hazırlanıyor. Toplam {len(items)} haber var. Alıcı: {', '.join(recipients)}")
    
    try:
        rail, other = [], []

        for i in items:
            if rail_score(i["Başlık"], i["Açıklama"]) >= 2:
                rail.append(i)
            else:
                other.append(i)

        logger.info(f"Demiryolu haberleri: {len(rail)}, Diğer: {len(other)}")

        def rows(data, highlight=False):
            r = ""
            for i in data:
                bg = "background-color:#eef6ff;" if highlight else ""
                tarih_col = f"<td>{i.get('Tarih', '')}</td>" if is_full_report else ""
                r += f"""
                <tr style="{bg}">
                    <td>{i['Kategori']}</td>
                    <td><b>{i['Başlık']}</b></td>
                    <td>{i['Açıklama']}</td>
                    {tarih_col}
                    <td><a href="{i['Link']}">Haber</a></td>
                </tr>
                """
            return r

        tarih_header = "<th>Tarih</th>" if is_full_report else ""
        colspan = "5" if is_full_report else "4"
        
        report_note = "<p style='color:#c00;'><b>📋 Bu mail, tüm haberlerin tam raporunu içermektedir.</b></p>" if is_full_report else ""

        body = f"""
        <html><body style="font-family:Arial;font-size:13px;">
        <p style="margin-bottom:20px;">
            Merhaba,<br><br>
            Yatırımlar dergisi internet sitesinde taranan {"tüm haberler" if is_full_report else "bugünün öne çıkan haberleri"} aşağıdaki gibidir.
        </p>
        {report_note}
        <br><br>

        <h3>🚆 Demiryolu Haberleri ({len(rail)})</h3>
        <table border="1" cellpadding="6">
        <tr><th>Kategori</th><th>Başlık</th><th>Açıklama</th>{tarih_header}<th>Link</th></tr>
        {rows(rail, True) if rail else f"<tr><td colspan='{colspan}'>Yok</td></tr>"}
        </table>

        <br><br>
        
        <h3>📄 Diğer Haberler ({len(other)})</h3>
        <table border="1" cellpadding="6">
        <tr><th>Kategori</th><th>Başlık</th><th>Açıklama</th>{tarih_header}<th>Link</th></tr>
        {rows(other) if other else f"<tr><td colspan='{colspan}'>Yok</td></tr>"}
        </table>
        
        <br><br>
        
        <div style="border-top:1px solid #ccc;padding-top:15px;margin-top:30px;">
            <p style="margin:0;font-size:12px;color:#666;">
                Bu mail, Muhammet Işık tarafından hazırlanan sistem ile otomatik olarak gönderilmektedir.<br>
                Sorun bildirmek için <a href="mailto:muhammet.isik@netmuhendislik.com.tr">muhammet.isik@netmuhendislik.com.tr</a> adresine mail atınız.
            </p>
        </div>
        </body></html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = build_subject(len(rail), len(items), is_full_report)
        msg["From"] = MAIL_FROM
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(body, "html"))

        logger.info(f"Mail gönderiliyor: {SMTP_HOST}:{SMTP_PORT}")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            if SMTP_USE_TLS:
                s.starttls()
                logger.debug("TLS başlatıldı")
            s.login(MAIL_FROM, MAIL_PASSWORD)
            logger.debug("SMTP login başarılı")
            s.send_message(msg)
        
        logger.info(f"Mail başarıyla gönderildi: {', '.join(recipients)}")
        
        # Sadece normal modda işaretle (full report modunda işaretleme)
        if not is_full_report:
            mark_as_sent(items)
        
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP kimlik doğrulama hatası. Mail/şifre kontrol edin.")
        raise
    except smtplib.SMTPException as e:
        logger.error(f"SMTP hatası: {e}")
        raise
    except Exception as e:
        logger.error(f"Mail gönderme hatası: {e}", exc_info=True)
        raise

# =========================================================
# ARGUMENT PARSER
# =========================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Yatırımlar Bülten - Haber takip ve mail gönderme scripti",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=""":
Örnekler:
  python yatirimlar_bulten.py                          Normal çalışma (yeni haberler)
  python yatirimlar_bulten.py -reportall -to xx@mail.com   Tüm haberleri belirtilen maile gönder
        """
    )
    parser.add_argument(
        '-reportall', 
        action='store_true',
        help='Veritabanındaki tüm haberleri raporla'
    )
    parser.add_argument(
        '-to',
        type=str,
        metavar='EMAIL',
        help='Rapor gönderilecek mail adresi (sadece -reportall ile kullanılır)'
    )
    return parser.parse_args()

# =========================================================
# MAIN
# =========================================================

def main():
    args = parse_args()
    
    logger.info("=" * 60)
    if args.reportall:
        logger.info("Yatırımlar Bülten - TAM RAPOR MODU")
    else:
        logger.info("Yatırımlar Bülten başlatılıyor...")
    logger.info("=" * 60)
    
    try:
        init_db()
        
        # Tam rapor modu
        if args.reportall:
            if not args.to:
                logger.error("-reportall kullanırken -to ile mail adresi belirtmelisiniz!")
                logger.error("Örnek: python yatirimlar_bulten.py -reportall -to ornek@mail.com")
                sys.exit(1)
            
            # Önce yeni haberleri çekmeyi dene (hata olursa devam et)
            try:
                logger.info("Rapor öncesi yeni haberler kontrol ediliyor...")
                html = fetch_html()
                new_items = process(html)
                if new_items:
                    logger.info(f"{len(new_items)} yeni haber bulundu ve veritabanına kaydedildi (sent=0)")
                    logger.info("Bu haberler bir sonraki normal çalıştırmada abonelere gönderilecek.")
                else:
                    logger.info("Yeni haber bulunamadı.")
            except Exception as e:
                logger.warning(f"Yeni haber çekme başarısız (mevcut verilerle devam ediliyor): {e}")
            
            # Şimdi tüm haberleri raporla
            all_news = get_all_news()
            if all_news:
                send_mail(all_news, recipient_override=args.to, is_full_report=True)
                logger.info("=" * 60)
                logger.info(f"Tam rapor başarıyla gönderildi: {args.to}")
                logger.info("=" * 60)
                file_logger.critical(f"✓ Tam rapor gönderildi - {len(all_news)} haber -> {args.to}")
            else:
                logger.info("Veritabanında haber bulunamadı.")
            return
        
        # Normal mod
        html = fetch_html()
        new_items = process(html)
        
        # Tüm gönderilmemiş haberleri al (yeni + eski başarısızlar)
        all_unsent = get_unsent_news()
        
        if all_unsent:
            if len(all_unsent) > len(new_items):
                logger.info(f"Toplam {len(all_unsent)} haber gönderilecek ({len(new_items)} yeni, {len(all_unsent)-len(new_items)} tekrar deneme)")
            
            send_mail(all_unsent)
            
            logger.info("=" * 60)
            logger.info("İşlem başarıyla tamamlandı!")
            logger.info("=" * 60)
            
            file_logger.critical(f"✓ İşlem başarılı - {len(all_unsent)} haber gönderildi (Yeni: {len(new_items)}, Tekrar: {len(all_unsent)-len(new_items)})")
        else:
            logger.info("=" * 60)
            logger.info("İşlem tamamlandı - Gönderilecek haber yok")
            logger.info("=" * 60)
            file_logger.critical(f"✓ İşlem başarılı - Yeni haber bulunamadı")
            
    except smtplib.SMTPAuthenticationError as e:
        logger.error("=" * 60)
        logger.error("HATA: SMTP Kimlik Doğrulama Hatası")
        logger.error("Mail gönderimi başarısız. Lütfen aşağıdakileri kontrol edin:")
        logger.error("  - Mail adresi ve şifre doğru mu?")
        logger.error("  - SMTP Authentication tenant için aktif mi?")
        logger.error(f"  - Detay: {str(e)}")
        logger.error("=" * 60)
        file_logger.critical(f"✗ İşlem başarısız - SMTP kimlik doğrulama hatası (Haberler veritabanında bekliyor)")
        sys.exit(1)
        
    except smtplib.SMTPException as e:
        logger.error("=" * 60)
        logger.error("HATA: Mail Gönderme Hatası")
        logger.error(f"SMTP sunucusu ile iletişim kurulamadı: {str(e)}")
        logger.error("=" * 60)
        file_logger.critical(f"✗ İşlem başarısız - SMTP hatası (Haberler veritabanında bekliyor)")
        sys.exit(1)
        
    except requests.exceptions.RequestException as e:
        logger.error("=" * 60)
        logger.error("HATA: Web Sitesine Erişim Hatası")
        logger.error(f"Yatırımlar.com sitesine bağlanılamadı: {str(e)}")
        logger.error("=" * 60)
        file_logger.critical(f"✗ İşlem başarısız - Web sitesi erişim hatası")
        sys.exit(1)
        
    except FileNotFoundError as e:
        logger.error("=" * 60)
        logger.error("HATA: Dosya Bulunamadı")
        logger.error(f"Gerekli dosya bulunamadı: {str(e)}")
        logger.error("=" * 60)
        file_logger.critical(f"✗ İşlem başarısız - Dosya bulunamadı")
        sys.exit(1)
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("HATA: Beklenmeyen Bir Hata Oluştu")
        logger.error(f"Hata detayı: {str(e)}")
        logger.error("=" * 60)
        file_logger.critical(f"✗ İşlem başarısız - {str(e)[:100]}")
        sys.exit(1)

if __name__ == "__main__":
    main()
