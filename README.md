# 📡 Tender Tracker

### Automated Ingestion, Hybrid Filtering, and Intelligent Notification Engine

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PyInstaller](https://img.shields.io/badge/PyInstaller-Executable-FF7F00?style=for-the-badge&logo=pyinstaller&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Production_Ready-success?style=for-the-badge)

> **Architectural Abstract:** A modular, enterprise-ready notification and intelligence platform designed to scrape, filter, classify, and notify tenders from public and corporate procurement portals. It features a two-stage hybrid filter (local rule-based suffix matching coupled with targeted Large Language Model evaluation), dynamic multi-theme Single Page Application dashboard, and a background scheduler running seamlessly from a Windows system tray utility.

---

## 📑 Table of Contents
1. [Technical Evaluation / Teknik Değerlendirme](#-technical-evaluation--teknik-değerlendirme)
2. [System Architecture](#-system-architecture)
3. [Project Directory Structure](#-project-directory-structure)
4. [Interface Showcases & Visual Walkthrough](#-interface-showcases--visual-walkthrough)
5. [Installation, Setup & Deployment](#-installation-setup--deployment)

---

## 📌 Technical Evaluation / Teknik Değerlendirme

### **EN | Technical Evaluation and Pipeline Architecture**
Tender Tracker is architected as an asynchronous data harvesting and processing pipeline optimized for tracking public and private tender platforms across Turkey.
* **Asynchronous Scraper Engine:** 
  * The system bypasses SSL/TLS handshake limitations on target public gateways by utilizing a custom `TLSAdapter` with custom cipher suites, maintaining persistent HTTP sessions.
  * Web scraping routines query raw JSON API endpoints where available to minimize network payloads and speed up processing. Unstructured HTML data feeds are parsed using optimized regular expressions and BeautifulSoup tokenizers.
* **Hybrid Two-Stage Filtering Strategy:**
  * **Stage 1 (Rule-Based Matching):** Ingested tenders are parsed against local keyword definitions (positive/negative suffixes) and global exclusions. Tenders matching local criteria are categorized immediately (0ms latency, zero API token costs).
  * **Stage 2 (Sector-Bound LLM Inference):** To optimize Large Language Model (LLM) query costs, custom prompt filters (Gemini, OpenAI, Claude) are bound to target sectors. The system only triggers LLM evaluation if a tender falls within the specified sector, decreasing monthly API costs by up to 90%.
* **Database Background Re-evaluation:** 
  To prevent re-hitting external websites when custom LLM filters are updated, the platform spawns background worker threads using dedicated database sessions to asynchronously evaluate already stored tenders locally.

### **TR | Teknik Değerlendirme ve Boru Hattı Mimarisi**
Tender Tracker, Türkiye'deki kamu ve özel ihale platformlarından veri toplamak üzere optimize edilmiş asenkron bir veri toplama ve işleme boru hattı mimarisidir.
* **Asenkron Tarayıcı Motoru:**
  * Sistem, hedef kamu portallarındaki SSL/TLS el sıkışma sınırlamalarını, özel şifreleme süitleri barındıran bir `TLSAdapter` ve kalıcı HTTP oturumları kullanarak aşar.
  * Ağ yükünü azaltmak amacıyla veri çekme işlemleri JSON API uç noktalarından doğrudan çekilir; yapılandırılmamış HTML bültenleri ise optimize edilmiş düzenli ifadeler ve BeautifulSoup kullanılarak SQLite modellerine dönüştürülür.
* **Hibrit İki Aşamalı Filtreleme Stratejisi:**
  * **1. Aşama (Kural Tabanlı Eşleşme):** İhaleler yerel sektörel kelimelere ve küresel yasaklı kelimelere göre taranır. Yerel kurallarla eşleşen ihaleler anında sınıflandırılır (0ms gecikme, sıfır token maliyeti).
  * **2. Aşama (Sektör Sınırlı LLM Analizi):** Yapay Zeka maliyetlerini minimize etmek adına özel LLM süzgeçleri belirli sektörlerle eşleştirilir. LLM API çağrısı yalnızca ihale ilgili sektörle eşleştiğinde tetiklenir, böylece token tüketimi %90'a varan oranda düşürülür.
* **Veritabanı Arka Plan Yeniden Değerlendirmesi:**
  * Yeni bir LLM filtresi eklendiğinde veya promptlar değiştirildiğinde, dış kaynakları tekrar taramamak için sistem arka planda asenkron iş parçacıkları (`threading.Thread`) başlatarak kayıtlı ihaleleri yerel olarak yeniden analiz eder.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph WebSources["🌐 Public & Private Portals"]
        EKAP["EKAPv2 (TLSAdapter)"]
        ILAN["ilan.gov.tr (JSON API)"]
        YAT["Yatırımlar Dergisi (HTML)"]
        DMO["DMO Platform"]
    end

    subgraph CoreEngine["🧠 Processing & Filtering"]
        Scraper["Scheduler / Scraper Engine"]
        DB[(SQLite Database)]
        LocalFilter{"Stage 1: Local Rule Check<br/>(Exclude / Keyword Matching)"}
        LLMFilter{"Stage 2: LLM Evaluation<br/>(Sector-Bound Prompting)"}
    end

    subgraph Config["⚙️ Settings & Dynamic Configuration"]
        CYAM["config.yaml (General & API Keys)"]
        SYAM["sectors.yaml (Local Sector Rules)"]
    end

    subgraph Outputs["📢 Target Notification Channels"]
        Mail["SMTP HTML Email Reports"]
        Telegram["Telegram HTML Bot Integration"]
    end

    WebSources -->|Fetch Raw Feeds| Scraper
    Scraper -->|Relational Storage| DB
    DB --> LocalFilter
    CYAM & SYAM -.-> LocalFilter & LLMFilter
    LocalFilter -->|Passed & Sector Scoped| LLMFilter
    LocalFilter -->|Locally Matches Sector| Outputs
    LLMFilter -->|Meets Semantic Rules| Outputs
```

---

## 📦 Project Structure

```
tender-tracker/
│
├── .github/workflows/           # CI/CD pipelines (PyInstaller remote runner)
├── screenshots/                 # Application dashboard captures
├── src/                         # Backend source files
│   ├── classifier.py            # AI (Gemini, OpenAI, Claude) and Rule engine
│   ├── database.py              # SQLite configuration and schema models
│   ├── filter.py                # Local suffix matching and exclusion rules
│   ├── scheduler.py             # Background timer scheduler
│   └── scrapers/                # Web scraping scripts
│
├── static/                      # Frontend single page application
│   ├── index.html               # Main dashboard UI
│   ├── css/                     # Vanilla CSS style guide
│   └── js/                      # App routing and UI interactive logic
│
├── app.py                       # FastAPI application & server REST endpoints
├── run.py                       # System entry point (Windows System Tray App)
├── build.py                     # Portable PyInstaller executable compiler
├── config.yaml                  # System credentials and server configurations
└── sectors.yaml                 # Sector definitions and keywords dictionary
```

---

## 📸 Interface Showcases & Visual Walkthrough

### 1. Active Tenders Tab (Aktif İhaleler Paneli)

This is the main application interface displaying all tenders harvested from the enabled sources. Users can view the titles, publication dates, and source platform tags, as well as apply client-side text searches and filter results dynamically by sector or active custom smart filters. A real-time notification indicator flashes in the sidebar if new matches are detected while away.

![Aktif İhaleler](screenshots/tenders.png)

<br/>

### 2. Multi-Theme Configurator (Arayüz Renk Temaları)

The system configuration panel features a responsive interface theme selector. Users can switch between 8 pre-designed color palettes (Turkuaz, Zümrüt, Turuncu, Mor, Gül, Kehribar, Gümüş, Kırmızı) dynamically. The chosen theme settings are written to the server's configuration file in real-time, preserving style selections across system restarts.

![Arayüz Renk Temaları](screenshots/config_general.png)

<br/>

### 3. Custom AI Filters & Re-evaluation (Akıllı Süzgeçler)

This panel allows users to create targeted LLM evaluation prompts. By scoping a prompt to a specific sector, you can control where the LLM evaluates the tender description, optimizing response times and token costs. The "Yeniden Değerlendir" button triggers an asynchronous background thread that applies newly created custom prompt rules to the existing SQLite database.

![Akıllı Süzgeçler](screenshots/config_filters.png)

<br/>

### 4. Sectors & Global Exclusion Manager (Sektörler ve Küresel Süzgeçler)

Sectors are managed as collapsible cards showing positive matching suffixes and negative exclusion keywords. In addition, a static, editable card at the very top provides control over global exclusion phrases. Tenders containing any global negative keywords are filtered out immediately during stage 1 before being logged.

![Sektörler ve Filtreler](screenshots/config_sectors.png)

<br/>

### 5. SMTP and Telegram Settings (Bildirim Entegrasyonu)

From this tab, the user configures SMTP mail delivery parameters and Telegram bot variables (Token and Chat ID). Tenders that pass the classification checks are grouped by sector and sent immediately. System logs will warn of missing credentials if fields are left blank.

![Bildirim Ayarları](screenshots/config_notifications.png)

<br/>

### 6. System Logs Terminal (Olay Günlüğü)

Provides an inline terminal window rendering the last 100 entries of the server log file (`events.log`). It displays active scraping cycles, classification steps, and connection errors, and is useful for real-time diagnostics. If an error is caught, a blinking warning dot appears next to the logs link on the sidebar menu.

![Sistem Logları](screenshots/logs.png)

---

## 🚀 Installation, Setup & Deployment

### 1. Local Environment Setup (Python)
To run the server and task scheduler natively from Python:
1. Clone the repository:
   ```bash
   git clone https://github.com/isikmuhamm/tender-tracker.git
   cd tender-tracker
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the tray controller app:
   ```bash
   python run.py
   ```
*Access the local web panel at `http://127.0.0.1:8000` from your browser.*

### 2. PyInstaller Standalone Compilation
To compile the system into a single executable that operates without Python dependencies:
1. Run the build script:
   ```bash
   python build.py
   ```
2. Retrieve the finished executable binary from the newly generated `dist/` directory:
   * **Windows:** `dist/tender-tracker.exe`

### 3. Troubleshooting Guide
* **Windows Defender / SmartScreen Warnings:** Because the standalone binary lacks an expensive commercial digital certificate, Windows Defender might identify it as untrusted. Click *"More Info"* on the popup window and select *"Run Anyway"* to start the system.
* **Server Port Conflicts:** By default, the FastAPI web panel runs on port `8000`. If this port is occupied by another application, open the local `config.yaml` with a text editor, change the value of `server_port` to an open port (e.g. `8085`), and restart.
* **Portable Directory Structure:** All active configurations, logs, and database records reside inside the directory containing the executable:
  * `tenders.db` (SQLite records)
  * `events.log` (Diagnostic outputs)
  * `config.yaml` / `sectors.yaml` (Active parameters)
  You can move the app to a different workstation by copying the `.exe` file along with these configuration and database files.
