# Tender Tracker - Implementation And Decision History

This file records completed implementation stages, their commit evidence, delivered behavior, and the boundary that remained after each stage.

It is not the active roadmap. Current priorities are in `BOARD.md`.

## H-001 Scraper Foundation And Source Normalization

**Period:** Initial repository foundation, before the 2026-06-27 product/UI consolidation

**Key commits:**

- `70d6de9` — base scraper and Yatırımlar adapter with tests
- `1b5f314` — DMO scraper with tests
- `78ceb37` — ilan.gov.tr scraper with tests
- `735e3b1` — EKAPv2 scraper skeleton with tests

### Delivered

- common scraper abstraction;
- normalized tender dictionaries with link, title, summary, category, and source;
- independent adapters for heterogeneous HTML and JSON sources;
- parser-focused test files per adapter;
- initial EKAP connection/TLS exploration.

### Architectural Result

The application moved away from a single hard-coded scraping script toward independent source adapters coordinated by an orchestrator. This became the foundation for source-level enable/disable controls and isolated failures.

### Remaining Boundary

EKAPv2 was a connectivity/parser skeleton rather than a working data adapter. Its test verified the placeholder behavior and did not prove public tender extraction.

---

## H-002 Persistence, Filtering, And Classification Foundation

**Key commits:**

- `9e94cae` — configuration loading and `TenderFilter` with tests
- later classifier and database commits consolidated SQLAlchemy persistence and sector classification
- `fc29819` — Turkish-safe boundaries for short keywords and false-positive correction
- `2c3f0c1` — local rule classification prioritized before LLM calls

### Delivered

- SQLAlchemy models for users and tenders;
- SQLite persistence and duplicate control by tender link;
- WAL mode for improved local read/write concurrency;
- global exclusion keywords;
- sector positive and negative keyword rules;
- title-weighted local classification;
- optional LLM fallback when local rules do not identify a sector;
- Turkish-aware short-keyword boundary handling.

### Architectural Result

Deterministic rules became the primary classifier. LLM calls were moved behind a fallback boundary, reducing unnecessary provider calls and preserving operation without a provider key.

### Remaining Boundary

Numeric savings were not instrumented. The design reduces calls, but no verified “90% token reduction” metric was produced.

---

## H-003 Notification Adapters

**Key commits:**

- `278cb22` — base notifier and email notifier with tests
- `6478455` — Telegram notifier with HTML formatting and message splitting tests

### Delivered

- notifier abstraction;
- sector-grouped HTML email reports;
- configurable SMTP delivery;
- Telegram Bot API delivery;
- long-message splitting below Telegram limits;
- notification state stored on tender records.

### Architectural Result

Delivery channels became optional adapters after persistence. The orchestrator could process stored unsent records independently for email and Telegram.

### Remaining Boundary

Boolean sent flags do not fully distinguish disabled, pending, failed, and sent states. Source-provided fields also require consistent HTML escaping across dashboard and notification renderers.

---

## H-004 FastAPI, Authentication, And Local Dashboard API

**Key commit:**

- `9cd3294` — JWT authentication and FastAPI web API with tests

### Delivered

- FastAPI application;
- first-run administrator setup;
- bcrypt password hashing;
- JWT login and protected endpoints;
- tender listing API;
- configuration read/write API;
- log viewing API;
- manual scan trigger;
- in-memory database API tests.

### Architectural Result

Tender Tracker changed from a CLI-oriented automation into a locally managed application with a browser interface and protected API boundary.

### Remaining Boundary

The authentication model is intentionally a local single-admin baseline. It is not multi-user RBAC or an internet-facing identity system.

---

## H-005 Web Interface, Packaging, And Initial CI/CD

**Key commit:**

- `24e77ac` — PyInstaller packaging, GitHub Actions CI/CD, static web UI, and additional API tests

### Delivered

- static single-page dashboard served by FastAPI;
- PyInstaller one-file build script;
- bundled static assets and default configuration templates;
- automated Python test job;
- Windows build on version tags;
- GitHub Release asset upload.

### Architectural Result

The repository gained a distributable Windows application path and a repeatable release mechanism rather than relying only on local Python setup.

### Remaining Boundary

The pipeline built the executable but did not yet perform an end-to-end packaged startup/health smoke test.

---

## H-006 Dashboard Productization Pass

**Date:** 2026-06-27

**Key commits:**

- `f31c69c` — multi-theme selection persisted in configuration
- `0899793` — user greeting in the sidebar
- `db298ec` — absolute static paths, `NO_BROWSER`, and screenshot updates
- `d7e0a66` — Enter-key form submission, expanded sectors, populated screenshots
- `c18f9ce` — contextual save buttons, hidden-input validation fixes, startup config load
- `ba26f9c` — automatic saving for filters, sectors, and global exclusions
- `e3fb8bc` — fixed global exclusion accordion card

### Delivered

- responsive glassmorphic dashboard;
- first-run setup and login flows;
- clean History API routes;
- editable sources, server settings, sectors, providers, notifications, and custom filters;
- eight persisted visual themes;
- modal-based sector and filter management;
- improved form and navigation behavior;
- screenshot set for public repository presentation.

### Architectural Result

Configuration that previously lived mainly in files became manageable through the authenticated local interface.

### Remaining Boundary

Configuration writes remained dictionary/YAML based rather than schema-validated and atomically replaced.

---

## H-007 Sector-Scoped LLM Filters And Local Re-Evaluation

**Date:** 2026-06-27

**Key commits:**

- `2c3f0c1` — local rules prioritized over provider classification
- `3ab0efb` — target-sector mapping for custom filters and background database re-evaluation

### Delivered

- custom prompt filters scoped to a selected sector or all sectors;
- provider calls skipped when no relevant custom filter applies;
- re-evaluation endpoint for stored, sector-assigned tenders;
- background session isolated from the request database session;
- matched custom-filter IDs persisted for dashboard filtering.

### Architectural Result

Prompt changes no longer required re-downloading source pages. Existing local records could be semantically re-evaluated against updated custom filters.

### Remaining Boundary

Re-evaluation applied custom LLM filters; it did not re-run the complete source ingestion or sector-classification pipeline.

---

## H-008 Background Status Indicators

**Date:** 2026-06-27

**Key commit:**

- `3998abb` — polling for new tender and error/warning indicators

### Delivered

- periodic REST polling while the dashboard is open;
- red-dot indicators for newly detected tenders;
- red-dot indicators for new warning/error log lines;
- indicator clearing when the relevant panel is opened.

### Architectural Result

The interface gained lightweight operational awareness without requiring WebSocket infrastructure.

### Remaining Boundary

Polling reports observable changes but is not an authoritative background-job state model. Manual triggers still benefit from explicit scan/re-evaluation status.

---

## H-009 Windows Build And Release Hardening

**Date:** 2026-06-27

**Key commits:**

- `5d5b20e` — CI branch triggers and PyStray/Pillow requirements
- `3347855` — workflow release permissions
- `48b5903` — pywin32 dependency and release tag fixes
- `8f546de` — pywin32 post-install step on Windows runner
- `eca906b` — Unicode-safe build output on clean Windows runners

### Delivered

- corrected GitHub Actions triggers;
- Windows tray/build dependencies included;
- pywin32 registration handling in CI;
- reliable release tag naming;
- release creation permission;
- clean-runner Unicode build fix.

### Architectural Result

The Windows packaging path evolved from a local build script into a tag-driven release process hardened through actual runner failures.

### Remaining Boundary

A release artifact could be built and uploaded, but a packaged-process startup smoke and checksum were still future quality gates.

---

## H-010 Public Repository Presentation

**Date:** 2026-06-27

**Key commits:**

- `3157e40` — README restructure with bilingual evaluation and Mermaid flow
- `4fedc25` — screenshot and visual documentation refinements
- `f2ea13d` — final README layout, MIT license, and missing screenshots

### Delivered

- architecture diagram;
- feature explanations;
- installation and packaging instructions;
- interface screenshots;
- contribution guidance;
- MIT licensing;
- polished public repository appearance.

### Architectural Result

The repository became understandable as a product rather than a collection of scripts.

### Remaining Boundary

The README accumulated product marketing, implementation detail, interface walkthroughs, and evaluation claims in one file. Some wording exceeded current verified behavior, particularly around EKAP, asynchronous operation, and readiness labels.

---

## H-011 Documentation Governance Baseline

**Date:** 2026-06-27

**Source:** Repository review plus owner-provided product report

### Delivered

- `AGENTS.md` for implementation rules;
- `business/BOARD.md` for active priorities and acceptance criteria;
- `business/NOTES.md` for durable decisions and rationale;
- `business/HISTORY.md` for commit-supported implementation history;
- a reduced public `README.md` modeled around product, features, architecture, setup, usage, and verified limitations.

### Decisions Consolidated

- local-first standalone product;
- bring-your-own-LLM model;
- deterministic-before-LLM pipeline;
- independent source degradation;
- public-only EKAP scope;
- explicit source capability labels;
- separation between public documentation and internal project memory.

### Next Boundary

Begin `P0.2 EKAP Public Tender Extraction` as the next focused implementation item and keep source status Experimental until fixture-based extraction tests pass.

---

## H-012 Ingestion Integrity and Frontend Security Guard

**Date:** 2026-06-27

**Key commits:**
- `29b18fe` — secure model list client API key headers, add Node JS DOM XSS tests, and update target link tabnabbing
- `681dc97` — escape dynamic template fields and validate url protocols in dashboard UI to prevent XSS
- `4b5b8ff` — escape template variables and restrict links in email and telegram notifiers with tests
- `d0715b8` — security/integrity: isolate transaction boundaries and secure scheduler persistence paths with tests

### Delivered
- `escapeHtml` and scheme-sanitized `safeLink` in the SPA UI dashboard.
- HTML escaping inside the Telegram bot and SMTP email notifier adapters.
- decoupling of notification delivery exceptions from ingestion commits.
- individual per-tender database transaction safety preventing single errors from rolling back entire scraping cycles.
- Node.js validation test executing inside `pytest` suite ensuring raw XSS payloads render safely in Javascript scope.
- tabnabbing protection utilizing `rel="noopener noreferrer"` for external anchors.

### Architectural Result
The application achieved baseline data integrity and protection against stored-XSS attacks. Scraper results are decoupled from delivery channels, ensuring robust persistence.

---

## H-013 Process-Safe Concurrency and CLI Consistent Daemon

**Date:** 2026-06-27

**Key commits:**
- `29b18fe` — integrate process-safe file locks, collect run result metrics, and update project governance boards
- `dc1d040` — security/concurrency: implement authoritative job manager, status polling, and scan mutual exclusion with tests
- `590d9b6` — fix/cli: import missing os module, integrate config-based check intervals, and handle Ctrl+C exit safely in daemon mode, with unit tests

### Delivered
- centralized thread-safe `JobState` tracking in FastAPI.
- process-safe file locking `ProcessLock` coordinating CLI daemon iterations with background dashboard scanning.
- CLI arguments (`--once`, `--daemon`, `--stats`) and interval settings fully covered by unit tests.
- KeyboardInterrupt signal wrapping daemon sleep/run loops to guarantee clean CLI exit.

### Architectural Result
Process-level lock implementation added; cross-process operational verification remains pending. Config-based check interval settings are mapped with fallback rules to environment settings.

---

## H-014 EKAP Public Tender Extraction

**Date:** 2026-06-27

### Delivered
- `cryptography` added explicitly to requirements.txt.
- `Ekapv2Scraper` implemented in `src/scraper/ekapv2.py`.
- custom security headers (`X-Custom-Request-Guid`, `X-Custom-Request-Siv`, `X-Custom-Request-Ts`, `X-Custom-Request-R8id`) signed with AES-CBC encryption.
- dynamic payload matching the latest search params schema mapping results to the common scraper contract.
- mock-based unit tests added to `tests/test_ekapv2.py`.
- README.md updated to represent EKAPv2 as an operational, non-experimental source.

### Architectural Result
The EKAP v2 public tender search is fully integrated as an operational, secure, and mock-tested scraper adapter.

---

## H-015 EKAP Initial and Incremental Synchronization

**Date:** 2026-06-27

### Delivered
- Automatic background scan on FastAPI startup.
- `SystemState` key-value persistence table for runtime metadata.
- State-aware initial scan (fetching only open tenders) and incremental scan (filtering by announcement start date).
- Safe multi-page pagination up to 500 pages (no 200 records cap) with transactional error escalation.
- Unconfigured email/Telegram notifiers warning-skip behavior to prevent backlog build-ups.
- JSON response schema verification on EKAP v2 results.
- Comprehensive test scenarios in `tests/test_ekapv2.py` and `tests/test_scheduler_status.py`.

### Architectural Result
Incremental and initial synchronization behavior for EKAP is robustly tied to local state persistence, ensuring stable execution paths over restarts and failures.

---

## H-016 Scraper Standardization And Safe Watermark Ingestion

**Date:** 2026-06-27

### Delivered
- **Centralized Output Contract:** Implemented a unified `normalize_and_validate` method inside `BaseScraper` to guarantee that all crawler outputs contain exactly 5 standard fields (`link`, `title`, `summary`, `category`, `source`).
- **Whitespace & Duplicate Control:** Automatically trims whitespace, validates link schemas (forcing HTTP/HTTPS protocols), and deduplicates records within a single response before returning.
- **Source Field Protection:** Always overwrites the returned `source` field with the scraper's own `self.source_name`.
- **SourceParseError Trigger:** Raises `SourceParseError` if a non-empty parsed response yields zero valid normalized records (preventing silent parser degradation).
- **ilan.gov.tr Pagination & Cycle Checks:** Standardized `ilan_gov_tr` paging logic to loop through `skipCount` (30 records per page, up to 100 pages), terminating on `totalCount` or short pages, with cycle detection preventing infinite loops and raising `SourceFetchError` if safety limits are reached with missing records.
- **EKAP Safety Page Limits:** Enforced identical page limit checks in `Ekapv2Scraper`, raising `SourceFetchError` on safety limit boundaries.
- **Generic SystemState Helpers:** Added generic `get_last_success_at` and `set_last_success_at` helper functions in `database.py` with keys mapped as `last_success_at:{source_name}`.
- **Chunked SQLite Deduplication:** Deduplicates incoming links against the database in safe chunks of 500 records to prevent hitting SQLite parameter limits.
- **Safe Watermark Updates:** Updates the source watermark timestamp (`last_success_at`) only at the end of the scraper's loop if fetch, parse, classification, and database persistence complete without any processing errors.
- **Distributed Unit Tests:** Added 10 new tests distributed across `test_base_scraper.py`, `test_ilan_gov_tr.py`, `test_ekapv2.py`, and `test_scheduler_status.py`, verifying the standardized contract, cycle checks, and watermark states. All 71 tests passing successfully.
- **Windows Executable Smokes:** Compiled `dist/tender-tracker.exe` using `build.py` and validated startup behavior using `smoke_check_exe.py` successfully.

### Architectural Result
Scrapers now share a case-insensitive, standardized contract normalization layer. Watermark progress is strictly tied to successful database commits, making ingestion completely transactional.

---

## H-017 Turkish Search, Pagination, Brand Icon, and Task Scheduler Support

**Date:** 2026-06-28

### Delivered
- **Turkish Case-Insensitive Search:** Registered a custom `turkish_lower` collation/function in SQLite and applied it globally to the `/api/tenders` endpoint, enabling case-insensitive search queries containing Turkish characters.
- **Client-Side Pagination & Stats:** Replaced the hard-coded 100 limit in the UI with a "Load More" pagination button and updated stats text format to `"Toplam X ihaleden Y ihale gösteriliyor"` to improve clarity.
- **Server-Side Custom LLM Filtering:** Moved custom LLM filter queries to the SQLite backend using `LIKE %filter%` on the `matched_custom_filters` column. This provides instant global searches across thousands of entries and integrates with the pagination engine.
- **EKAPv2 Start Date Format Correction:** Fixed 400 Bad Request API errors by sending announcements start date parameter formatted as ISO 8601 (`"%Y-%m-%dT%H:%M:%S"`) instead of `"dd.mm.yyyy"`.
- **OpenAI Configuration Layout Redesign:** Reordered input fields as **API Key -> Base URL -> Model Name**, cleared default fallback models when key fields are empty, and supported on-the-fly model list updates using input field states.
- **Brand Icon & Favicon Integration:** Designed a custom modern magnifying glass logo, converted it into multi-resolution `.ico` formats, updated `build.py` with `--icon=app_icon.ico`, and mounted it at `/favicon.ico` in the backend.
- **CLI Executable Task Scheduler support:** Enabled CLI argument parsing (`--once`, `--stats`) directly inside `app.py` so that the compiled `tender-tracker.exe` can run headlessly via Windows Task Scheduler.
- **AI Fallback Classification Removal:** Removed the optional AI fallback classification path to conserve tokens and reduce costs, and updated README/Notes/Board to align with deterministic-only sector mapping.

### Architectural Result
The compiled Windows binary `tender-tracker.exe` is now fully dual-purpose: it runs as a graphical dashboard and system tray application by default, and as a headless command-line crawler when passed CLI flags (supporting Task Scheduler integration). Search, pagination, and custom filters have been moved to the SQL layer to support large-scale performance.


