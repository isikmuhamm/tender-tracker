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

1. **P0.3 Untrusted Content Rendering Guard**
2. **P0.4 TLS And Credential Transport Cleanup**
3. **P0.5 Persistence And Transaction Integrity**
4. **P0.6 Scan And Re-Evaluation Mutual Exclusion**
5. **P0.7 Supported Runtime Path Consistency**
6. **P0.2 EKAP Public Tender Extraction**

The first five items harden the already operational product. P0.2 expands source coverage after the current runtime is safer and more deterministic.

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

### P0.3 Untrusted Content Rendering Guard

**Status:** Ready for implementation

**Objective:** Treat tender titles, summaries, categories, sectors, source labels, custom-filter labels, and links as untrusted external data.

**Why this is critical:** Scraped content is rendered inside an authenticated local dashboard that can access configuration and provider credentials. Raw HTML insertion creates a stored-XSS path even in a local-first application.

**Acceptance criteria:**

- dashboard uses safe DOM construction or explicit escaping rather than inserting source values into raw `innerHTML`;
- only `http:` and `https:` tender links are rendered as clickable URLs;
- email and Telegram HTML fields are escaped;
- malicious title, summary, sector, source, and link fixtures render as text and never execute;
- existing visual layout and user workflow remain intact.

### P0.4 TLS And Credential Transport Cleanup

**Status:** Ready for implementation

**Objective:** Restore normal certificate verification for trusted provider APIs and stop moving credentials through URL query parameters.

**Why this is critical:** Disabling TLS verification for LLM providers weakens the confidentiality of user-owned API keys and prompt content. Query-string keys can also appear in browser history, proxies, or access logs.

**Acceptance criteria:**

- Gemini, OpenAI-compatible, Anthropic, and Telegram calls use normal TLS verification;
- global suppression of certificate warnings is removed;
- any legacy source compatibility mode is isolated to that source, explicit, and logged;
- `/api/models` does not require an API key in a URL query string;
- provider keys are never included in logs or exception messages;
- existing BYO-LLM configuration continues to work locally.

### P0.5 Persistence And Transaction Integrity

**Status:** Ready for implementation

**Objective:** Ensure every accepted or excluded tender is committed predictably and notification failures cannot discard ingestion results.

**Why this is critical:** The current control flow can add an excluded record and continue before an explicit commit. If no later commit occurs, a run containing only excluded records can finish without persisting them. Persistence and notification side effects also need a clear boundary.

**Acceptance criteria:**

- an ingestion run containing only excluded tenders persists those records;
- one source failure does not roll back successfully processed records from another source;
- notification failure does not remove or roll back stored tenders;
- transaction boundaries are explicit and covered by behavior tests;
- duplicate handling remains stable across repeated runs;
- tests cover excluded-only, notifier-disabled, notifier-failed, and partial-source-failure scenarios.

### P0.6 Scan And Re-Evaluation Mutual Exclusion

**Status:** Ready for implementation

**Objective:** Prevent overlapping manual scans, recurring scans, and stored-tender re-evaluation jobs from racing against the same local database and configuration.

**Why this is critical:** The dashboard can start background threads without one authoritative job state. Repeated clicks or concurrent job types can create duplicate work, inconsistent status, and avoidable SQLite contention.

**Acceptance criteria:**

- one authoritative local job state exists;
- a second conflicting start is rejected or deliberately queued;
- scan and re-evaluation cannot mutate the same records concurrently;
- UI shows actual running, completed, and failed states rather than a fixed-delay assumption;
- job failure returns the system to a recoverable state and remains visible in logs;
- clean application shutdown does not leave a job marked permanently active.

### P0.7 Supported Runtime Path Consistency

**Status:** Ready for implementation

**Objective:** Make the dashboard, CLI, daemon, tray, and packaged executable behavior explicit and internally consistent.

**Why this is critical:** A supported command must either work or be removed from public guidance. The daemon path currently references `os.getenv` without importing `os`, and recurring execution behavior is not unified with the packaged dashboard lifecycle.

**Acceptance criteria:**

- `run.py --once` works and exits predictably;
- `run.py --stats` works without initializing unrelated runtime services;
- `run.py --daemon` either works with a documented interval source or is deliberately removed/deprecated;
- missing imports and guaranteed runtime exceptions are fixed;
- README commands match actual entry-point behavior;
- packaged desktop behavior does not claim recurring scans unless that behavior is verified;
- targeted tests or a smoke harness cover each supported entry path.

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
- Should scan and re-evaluation be mutually exclusive through a process lock, a shared job manager, or both?

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
