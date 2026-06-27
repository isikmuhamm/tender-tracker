# Tender Tracker - Project Board

This file contains only the **active, high-impact engineering work** for Tender Tracker.

- Product and architecture decisions live in `NOTES.md`.
- Deferred hardening, productization, and optional infrastructure work also live in `NOTES.md`.
- Completed implementation evidence lives in `HISTORY.md`.
- Public behavior and the user guide live in the root `README.md`.

Do not turn this board into a general wishlist. An item belongs here only when it directly affects security, data integrity, a supported runtime path, or a core source capability.

## Product Definition

**Status:** Operational local application under active experimental development

Tender Tracker is a local-first tender intelligence and notification application that collects public procurement listings, applies deterministic and optional LLM-assisted classification, stores results locally, and presents them through a FastAPI dashboard with optional email and Telegram delivery.

Primary target:

- technical sales, presales, engineering, business development, and procurement teams;
- users who repeatedly search several public tender sources;
- users who want sector-specific filtering without sending every listing to an LLM;
- users who prefer a portable local application and bring their own provider credentials.

Current-phase non-goals:

- hosted SaaS and multi-tenancy before external demand is validated;
- payments, subscriptions, or license enforcement before a commercial distribution model is selected;
- autonomous bid preparation;
- authenticated/private procurement areas;
- guaranteed uninterrupted access to third-party websites;
- replacing the source portals.

These are phase boundaries, not permanent exclusions. Productization may later add licensed standalone, on-premises, and managed-cloud delivery modes while retaining one core ingestion and classification engine.

## How To Interpret This Board

The application owner reports that the current dashboard, configured sources, filtering, local persistence, and notification workflow are operational. The existence of P0 items does **not** mean the application is unusable. It means the prototype is being hardened before broader distribution or service-level claims.

Priority meaning:

- **P0:** fix before treating the application as a broadly distributable, security-conscious release;
- **Completed:** verified foundation already present;
- everything else belongs in `NOTES.md` until deliberately promoted.

## Current Source Of Truth

Development source of truth:

- active critical work: `business/BOARD.md`
- decisions, deferred work, and rationale: `business/NOTES.md`
- implementation history: `business/HISTORY.md`
- repository operating rules: `AGENTS.md`
- public behavior: `README.md`

Runtime source of truth:

```text
config.yaml      user-owned local runtime configuration
sectors.yaml     local sector rules
SQLite database  tenders, notification state, administrator account
events.log       local operational log
```

## Last Reviewed Status

**Review date:** 2026-06-27

| Area | Status | Notes |
|---|---|---|
| Yatırımlar Dergisi | Operational | HTML adapter and parser implemented |
| DMO | Operational | Active tender-list HTML parser implemented |
| ilan.gov.tr | Operational | JSON endpoint adapter implemented |
| EKAPv2 | Experimental | Connection path exists; public record extraction pending |
| Global exclusions | Operational | Editable local negative keyword rules |
| Sector classification | Operational | Local rules first, optional LLM fallback |
| Custom LLM filters | Operational | Sector-scoped and re-evaluable against stored tenders |
| FastAPI dashboard | Operational | Setup, login, tenders, configuration, logs |
| Email / Telegram | Operational when configured | Optional local notification channels |
| Windows packaging | Implemented | PyInstaller build and tag-based release workflow |
| Documentation governance | Implemented baseline | README, board, notes, history, agent rules |

## Current Recommended Implementation Order

Work on one item at a time unless explicitly asked to batch related fixes.

1. **P0.4 TLS And Credential Transport Cleanup (Harden / Verification Follow-up)**
2. **P0.6 Scan And Re-Evaluation Mutual Exclusion (Harden / Verification Follow-up)**
3. **P0.7 Supported Runtime Path Consistency (Harden / Verification Follow-up)**
4. **P0.2 EKAP Public Tender Extraction**

The first three items harden the already operational product. P0.2 expands source coverage after the current runtime is safer and more deterministic.

## Active Critical Work Items

### P0.2 EKAP Public Tender Extraction

**Status:** Ready for implementation

**Objective:** Convert the existing EKAPv2 connectivity skeleton into a public-list adapter that returns real tender records without requiring authenticated areas.

**Scope:**

- identify the public search/list request used by the EKAP browser application;
- document method, headers, payload, pagination, and response shape;
- parse stable tender identifiers and public detail links;
- map records to the common scraper contract;
- add captured response fixtures and deterministic tests;
- show explicit degraded status when EKAP changes or blocks requests.

**Acceptance criteria:**

- a captured public EKAP response produces at least one normalized tender in a fixture test;
- pagination or result limits are handled deliberately;
- duplicate records remain stable across repeated runs;
- no login, password, e-signature, CAPTCHA bypass, or private account flow is introduced;
- EKAP failure does not interrupt the remaining source adapters;
- README source status changes from Experimental only after tests pass.

### P0.4 TLS And Credential Transport Cleanup

**Status:** Active (In Progress — Harden / Verification Follow-up)

**Objective:** Restore normal certificate verification for trusted provider APIs and stop moving credentials through URL query parameters.

**Completed in this phase:**
- Gemini, OpenAI-compatible, and Anthropic provider APIs TLS validation enabled.
- Log secrets redacted with `HIDDEN_KEY` for exceptions.
- Local client `/api/models` uses `X-API-Key` header instead of URL parameters.
- Gemini model listings updated to pass key via secure `x-goog-api-key` header rather than URL query.
- Exception handlers in `/api/models` redact secrets in case of requests/HTTP errors.
- Mock-based test suite checks header mapping and log redaction.

**Remaining follow-up:**
- Credential validation follow-up: ensure that no new external services or endpoints introduce query-string API keys.

### P0.6 Scan And Re-Evaluation Mutual Exclusion

**Status:** Active (In Progress — Harden / Verification Follow-up)

**Objective:** Prevent overlapping manual scans, recurring scans, and stored-tender re-evaluation jobs from racing against the same local database and configuration.

**Completed in this phase:**
- Authoritative in-memory `JobState` manager and thread safety lock added to `app.py`.
- REST endpoint `/api/job/status` and active status polling (2s interval) added to the SPA UI.
- API endpoints return `409 Conflict` when meşgul.
- Structured `RunResult` (successful/failed sources, added records, notifications errors) returned by `run_once()`.
- Process-safe file lock `ProcessLock` (`tender_tracker_scan.lock` using exclusive filesystem file handle and active PID checks) coordinates dashboard scanning threads with CLI daemon iterations.
- CLI daemon respects process lock, skips iteration with warning when lock is held.

**Remaining follow-up:**
- Verification follow-up: test with actual separate running OS processes (e.g. running daemon via task scheduler and dashboard concurrently).

### P0.7 Supported Runtime Path Consistency

**Status:** Active (In Progress — Harden / Verification Follow-up)

**Objective:** Make the dashboard, CLI, daemon, tray, and packaged executable behavior explicit and internally consistent.

**Completed in this phase:**
- Resolved missing `os` import crash in `run.py`.
- Safe Ctrl+C SIGINT handling wrapping entire daemon loop (scan + sleep) to exit with `sys.exit(0)`.
- Precedence rules established: `ENV > config.yaml check_interval_minutes > check_interval > default (60 dk)`.
- CLI command arguments and run flows covered by unit tests in `tests/test_run.py`.
- Documentation updated to explicitly present `--daemon` CLI commands and default options.

**Remaining follow-up:**
- Lifecycle follow-up: verify daemon integration inside the PyInstaller packaging workflow.

## Active Decisions

### AD-001 Local-First Standalone Product

Tender Tracker remains a local application with a loopback dashboard, local SQLite persistence, and user-owned configuration. Hosted SaaS architecture is not part of the current product scope.

### AD-002 Bring Your Own LLM

LLM use is optional. Users provide their own Gemini, OpenAI-compatible, or Anthropic credentials locally. The product must remain useful through deterministic filters when no provider is configured.

### AD-003 Deterministic Work Before LLM Work

Global exclusions and local sector rules run before optional LLM classification and custom prompt evaluation. This preserves speed, explainability, and provider-cost control.

### AD-004 Independent Source Adapters

Each procurement source is an independent adapter. One broken or changed website must degrade only that source rather than stopping the complete scan.

### AD-005 Public Source Boundary

Only publicly accessible listings are in scope. Authenticated procurement areas, e-signature flows, credential automation, CAPTCHA bypass, or access-control circumvention are outside scope.

### AD-006 Single Administrator Baseline

The dashboard currently targets one local administrator. Multi-user roles, tenant separation, and enterprise identity providers are deferred.

### AD-007 Optional Notification Channels

Email and Telegram are delivery adapters, not prerequisites for ingestion. A disabled or unconfigured channel must not prevent records from being stored.

### AD-008 Honest Capability Labels

Source and feature states must be labeled as Operational, Degraded, Experimental, Disabled, or Planned. A connection test alone is not an operational scraper.

### AD-009 Documentation Separation

README explains the public product and user workflow. Board tracks active critical work. Notes preserve decisions and deferred backlog. History preserves completed implementation detail. Agent instructions define working rules.


### AD-010 Evidence-Gated Productization

Commercial hardening is conditional rather than active scope. Public posts, real users, repeated deployment requests, willingness to pay, or meaningful support demand may promote productization work from `NOTES.md` to this board.

The preferred progression is:

```text
operational local prototype
-> external signal and real usage
-> security/distribution hardening
-> licensed standalone or on-premises package
-> managed cloud service
-> optional cooperative tender-data network
```

Do not implement licensing, tenancy, cloud control-plane, or federated synchronization merely to make the prototype look mature. Promote one bounded productization slice only when the previous stage has evidence and an owner.

## Conditional Productization Gate — Inactive

This section records the trigger without turning future business ideas into current implementation tasks.

Potential promotion signals:

- repeated external requests to install or operate the application;
- users running the application beyond a short demo period;
- demand for an always-on server, team access, managed operation, or support;
- willingness to pay for deployment, maintenance, source adapters, or notification reliability;
- enough operational usage to justify a formal threat model and support policy.

When triggered, promote work in this order:

1. define delivery mode and threat model;
2. harden authentication, secret handling, network exposure, updates, backups, and auditability;
3. add Docker/Compose or an installer according to the selected delivery mode;
4. add license/entitlement only after offline, on-premises, and recovery behavior are specified;
5. introduce tenant boundaries and managed-cloud operations only for an actual hosted offer;
6. research opt-in central synchronization before any peer-to-peer or gossip design.

Detailed rationale and architecture hypotheses live in `NOTES.md`, Records 026–030.

## Open Critical Questions

- Which EKAP public request should be treated as the stable integration boundary: JSON/XHR, server-rendered HTML, or browser automation only as a last resort?
- Should recurring scans be an in-process desktop responsibility or a separate CLI/OS-scheduled responsibility?

## Completed Foundation Items

### C-001 Documentation And Project Memory Baseline
**Status:** Completed — added `AGENTS.md`, `business/BOARD.md`, `business/NOTES.md`, `business/HISTORY.md`, and a verified README/user guide.

### C-002 Modular Source Adapters
**Status:** Completed — shared scraper contract plus Yatırımlar, DMO, ilan.gov.tr, and EKAP connectivity skeleton.

### C-003 Local Persistence And Filtering
**Status:** Completed — SQLAlchemy/SQLite persistence, WAL mode, global exclusions, sector rules, and duplicate control baseline.

### C-004 Multi-Provider Classification
**Status:** Completed — local-first classification with optional Gemini, OpenAI-compatible, and Anthropic provider calls.

### C-005 Notification Adapters
**Status:** Completed — HTML email and Telegram delivery with sector grouping.

### C-006 Local Dashboard And Authentication
**Status:** Completed — FastAPI API, first-run administrator setup, JWT login, configuration, tender, and log views.

### C-007 Packaging And Delivery Pipeline
**Status:** Completed — PyInstaller build, GitHub Actions tests, Windows tag build, and release asset upload.

### C-008 Product UI And Public Documentation
**Status:** Completed — responsive themed dashboard, routing, screenshots, user guide, MIT license, and explicit active-development positioning.

### C-009 Untrusted Content Rendering Guard (P0.3)
**Status:** Completed — implemented HTML escaping (`escapeHtml`) and link scheme sanitization (`safeLink`) in the SPA UI, SMTP email client, and Telegram notifier. Handled tabnabbing via `rel="noopener noreferrer"`. Verified via HTML payloads unit tests and DOM extraction Node.js tests.

### C-010 Persistence And Transaction Integrity (P0.5)
**Status:** Completed — isolated record database commits inside per-tender try-except blocks, ensured immediate commits for excluded-only runs, and decoupled notification delivery errors from database transactions. Verified via multi-scenario tests.
