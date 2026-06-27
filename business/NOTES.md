# Tender Tracker - Decision Archive And Product Memory

This file preserves product decisions and the reasoning that should survive chat history.

The active roadmap is `BOARD.md`. Completed implementation detail is `HISTORY.md`. Public behavior is documented in the root `README.md`.

## Working Protocol

- A report, audit, or conversation is advisory until its findings are accepted into `BOARD.md` or this file.
- For every claim, distinguish implemented behavior, partially implemented behavior, experimental code, and future intent.
- Record decisions, trade-offs, boundaries, risks, and reasons here; do not copy routine task lists or raw logs.
- When the board and notes disagree, the board is the active authority and the notes should be corrected.
- Public README claims must remain narrower than or equal to verified runtime behavior.

## Document Roles

`BOARD.md`

Active status, priorities, acceptance criteria, open questions, and the recommended next step.

`NOTES.md`

Decision archive, rationale, trade-offs, known risks, and durable product memory.

`HISTORY.md`

Completed implementation stages, commit references, verification evidence, and the boundary that remained after each stage.

`README.md`

External product explanation: what the application does, how it works, how to install it, supported sources, current limitations, and how to contribute.

`AGENTS.md`

Repository operating rules for coding agents and future implementation sessions.

---

## Record 001 - Local-First Product Boundary

**Related:** AD-001, AD-006, AD-007

Tender Tracker is intentionally a local-first application rather than a hosted tender-data service. The user owns the database, credentials, configuration, source selection, and notification destinations.

Reasons:

- tender monitoring may involve company-specific sectors, prompts, and recipient lists;
- local storage reduces deployment and recurring hosting requirements;
- a portable executable matches the initial internal-use and small-team use case;
- the product can deliver value without accounts, billing, tenant management, or central infrastructure.

Consequences:

- loopback access is the default;
- SQLite and YAML are acceptable baseline storage choices;
- a single local administrator is sufficient for the current scope;
- SaaS payments, multi-tenancy, enterprise SSO, and hosted key storage remain outside scope;
- public claims should describe a standalone application, not an enterprise procurement platform.

**Status:** Accepted and active.

---

## Record 002 - Bring Your Own LLM

**Related:** AD-002, AD-003

LLM functionality is optional and provider-neutral at the product level. Users enter their own provider credentials in their local installation.

Supported provider shapes:

- Gemini;
- OpenAI-compatible chat-completions endpoints;
- Anthropic Claude.

The application must still provide useful deterministic filtering when no provider is configured.

Reasons:

- avoids operating a central credential and billing service;
- lets the user select cost, privacy, latency, and model trade-offs;
- prevents a single model vendor from becoming a product dependency;
- keeps the standalone distribution model coherent.

Security boundary:

- release templates contain no real credentials;
- runtime credentials are local user data;
- credentials must not appear in logs, screenshots, tests, commit history, or URL query strings;
- moving to hosted secret storage would be a new product decision, not a routine refactor.

**Status:** Accepted and implemented baseline.

---

## Record 003 - Canonical Processing Pipeline

**Related:** AD-003, AD-004

The system is more accurately described as a staged hybrid pipeline than a simple two-stage filter.

```text
1. Source ingestion
2. Duplicate check
3. Global exclusion rules
4. Local sector classification
5. Optional fallback LLM sector classification
6. Sector-scoped custom LLM filters
7. Database persistence
8. Optional notification delivery
```

Key distinction:

- local sector classification determines a sector cheaply and deterministically;
- fallback LLM classification is used only when local rules do not identify a sector and an LLM is enabled;
- custom LLM filters are a separate user-defined semantic evaluation after a sector is known;
- database re-evaluation currently targets custom LLM filters for already stored, sector-assigned tenders. It is not a complete re-scrape or full sector reclassification.

Reasons:

- deterministic rules are faster and explainable;
- LLM calls remain optional and targeted;
- custom filters can evolve without repeating external network ingestion;
- the separation supports future measurement of rule hits, fallback classification, and custom-filter matches.

**Status:** Accepted; public diagrams should use this sequence.

---

## Record 004 - Cost Claims Require Measurement

**Related:** AD-003, AD-008

Sector scoping and local-first classification clearly reduce unnecessary LLM calls. However, a numeric claim such as “up to 90% token savings” is not a verified product metric without request and token telemetry across a representative workload.

Decision:

- describe the mechanism and expected direction of improvement;
- do not publish a percentage until measured;
- if future telemetry is added, record local-match rate, provider-call count, input tokens, output tokens, latency, and failure rate without storing sensitive prompt content unnecessarily.

**Status:** Accepted documentation rule.

---

## Record 005 - Independent Source Adapter Model

**Related:** AD-004, AD-005, AD-008

Each source is an independent integration with its own fetch and parse behavior.

Current source state:

| Source | Integration method | Current state |
|---|---|---|
| Yatırımlar Dergisi | HTML parsing | Operational |
| DMO | HTML parsing | Operational |
| ilan.gov.tr | Direct JSON request | Operational |
| EKAPv2 | Custom TLS connection path; parser placeholder | Experimental |

A source must not be called operational merely because a connection returns HTML. Operational means that a stable public response is normalized into real tender records and protected by deterministic fixtures/tests.

Failure policy:

- one adapter failure is logged and isolated;
- the remaining adapters continue;
- source status should be visible rather than silently presented as success;
- authenticated or access-controlled areas are outside scope.

**Status:** Accepted and active.

---

## Record 006 - EKAP Public Access Boundary

**Related:** AD-005, P0.2

The product owner expects public EKAP listings to be readable without login. The current adapter solves only part of the problem: it establishes a connection path but does not extract listings from the SPA response.

Implementation decision:

1. Prefer the public JSON/XHR request used by the browser.
2. Reproduce only the minimum required public request headers and payload.
3. Use server-rendered public HTML if a stable listing exists.
4. Treat browser automation as a last resort because it increases packaging weight and fragility.
5. Do not automate login, e-signature, private accounts, CAPTCHA bypass, or restricted endpoints.

Definition of done:

- captured response fixture;
- parsed records with stable identifiers/links;
- pagination decision;
- duplicate stability;
- isolated failure behavior;
- README status updated only after verification.

**Status:** Open; highest-priority source work.

---

## Record 007 - SQLite And WAL Semantics

**Related:** C-002, P1.4

SQLite is appropriate for a single-machine, local-first application. WAL mode improves concurrent read/write behavior between the dashboard and background operations, but it does not guarantee that lock contention cannot occur.

Current advantages:

- portable deployment;
- no separate database service;
- simple backup and inspection;
- sufficient scale for the expected local workload.

Required discipline:

- explicit transaction boundaries;
- no assumption that `Base.metadata.create_all()` migrates existing schemas;
- future model changes require a migration/version strategy;
- database and configuration backup should precede destructive schema changes;
- concurrent scan/re-evaluation jobs require application-level coordination.

**Status:** SQLite/WAL accepted; migration and backup remain P1.

---

## Record 008 - Runtime And Job Lifecycle

**Related:** P0.5

The application exposes manual scan and database re-evaluation paths that can start background threads. A durable runtime model should make job state explicit instead of relying on a fixed UI delay or unconstrained thread creation.

Target states:

```text
idle | scanning | re_evaluating | completed | failed
```

Required behavior:

- no overlapping scan against the same local database unless explicitly designed;
- no scan/re-evaluation collision;
- current state and last error visible to the dashboard;
- configuration reload behavior defined rather than implicit;
- clean shutdown of background work;
- recurring execution architecture explicitly selected: in-process scheduler or separate CLI/OS scheduler.

This is a hardening decision, not evidence that the currently reported working application is unusable.

**Status:** Planned.

---

## Record 009 - Notification Channels Are Optional Adapters

**Related:** AD-007, P1.3

Email and Telegram are delivery channels after persistence. They must not determine whether a tender can be ingested and stored.

Current product behavior groups notifications by sector and supports HTML rendering. Telegram splits long payloads near platform message limits.

Target state model:

```text
disabled | pending | sent | failed
```

Why boolean flags are eventually insufficient:

- disabled and successfully sent are different business states;
- retry policy needs attempt count and last error;
- a channel may be enabled after tenders were collected;
- support diagnostics should distinguish configuration absence from provider failure.

Rendering safety:

- source-provided title, summary, sector, category, and links are untrusted;
- dashboard, email, and Telegram representations must escape or safely construct output.

**Status:** Baseline implemented; explicit state and escaping planned.

---

## Record 010 - Configuration Is Local Runtime State

**Related:** AD-001, AD-002, P1.1

The committed configuration template is intentionally credential-free. A user who downloads or builds Tender Tracker enters provider and notification credentials locally.

This means the local `config.yaml` model is not itself a product defect. The improvement area is robustness:

- schema validation;
- atomic writes;
- backup of the last valid configuration;
- credential masking in API responses;
- preserving existing credentials when a masked field is submitted unchanged;
- avoiding credentials in query parameters and logs.

A future developer workflow may separate `config.example.yaml` from untracked `config.yaml`, but that is repository hygiene rather than a change to the BYO-LLM product model.

**Status:** Product model accepted; robustness work planned.

---

## Record 011 - Authentication Boundary

**Related:** AD-006

The current JWT and bcrypt implementation protects a local single-administrator dashboard. It should not be presented as an enterprise identity system.

Security posture depends on deployment:

- default loopback binding materially limits exposure;
- exposing the service to a LAN or public tunnel changes the threat model;
- a generated local JWT secret, stronger password policy, safer browser token handling, and request abuse controls become more important when exposure expands.

Decision:

- preserve simple first-run setup for the local product;
- keep `127.0.0.1` as the default host;
- treat non-local exposure as an explicit advanced configuration with warnings;
- do not add RBAC or multi-user complexity without a product need.

**Status:** Baseline implemented; hardening remains incremental.

---

## Record 012 - Release And CI Boundary

**Related:** C-006, P1.2

The repository has a real delivery pipeline:

- tests run on pushes and pull requests;
- version tags trigger a Windows PyInstaller build;
- the executable is uploaded to GitHub Releases.

This is a useful CI/CD baseline, but release confidence should eventually include:

- executable startup/health smoke;
- lint and formatting gates;
- dependency audit;
- coverage threshold;
- release checksum;
- least-privilege workflow permissions.

Passing unit tests and producing an executable are different verification levels. Documentation should distinguish tested, packaged, released, and field-verified.

**Status:** Baseline implemented; stronger release gates planned.

---

## Record 013 - Public README And User Guide Discipline

**Related:** AD-008, AD-009

The README serves two public roles for this repository:

1. a concise technical product entry point for developers and evaluators;
2. a practical Turkish user guide for people running the local application.

The upper section should contain:

- active-development notice;
- concise product overview;
- verified key features;
- real processing pipeline and architecture;
- supported-source status;
- installation, configuration, test, and build paths;
- current engineering boundaries.

The lower section should preserve:

- the existing application screenshots;
- screen-by-screen usage guidance;
- setup and configuration steps;
- operational warnings;
- common error causes and solutions;
- portable data and update guidance.

The README should not contain:

- unsupported performance percentages;
- implementation claims that exceed the code;
- obsolete commands;
- internal audit prose presented as product behavior;
- “production ready” as a substitute for release evidence.

Screenshots are not decorative duplication in this repository. They form part of the user manual and should remain synchronized with the current UI.

**Status:** Accepted and applied in the documentation package.

---

## Record 014 - Default Tests Must Be Deterministic

**Related:** P0.2, P1.2

Public websites and LLM providers are volatile. The normal test suite must not fail because a source is temporarily unavailable, a provider changes a model name, or a rate limit is reached.

Test policy:

- parser behavior uses captured HTML/JSON fixtures;
- API behavior uses local test databases and mocked external boundaries where appropriate;
- critical persistence/auth/config behavior exercises real local boundaries;
- live source/provider probes are opt-in;
- live tests report degraded external conditions separately from code regressions.

**Status:** Accepted test policy.

---

## Deferred Engineering Backlog Index

The following items are intentionally **not active board blockers**. They are useful productization, maintainability, observability, or future deployment work. Promote one to `BOARD.md` only when the owner deliberately chooses it as current implementation scope.

| Ref | Deferred item | Why it is not currently critical |
|---|---|---|
| D-001 | Validated and atomic configuration writes | Current local configuration works; this improves resilience against malformed or interrupted writes |
| D-002 | Credential masking in config responses | Valuable hardening after XSS and query-string cleanup; local authenticated scope reduces immediate priority |
| D-003 | Stronger auth and generated JWT secret | Important before LAN/public exposure; current default product boundary is loopback/local |
| D-004 | SMTP username semantics | Affects SMTP servers where login identity differs from sender address; not a core ingestion blocker |
| D-005 | Explicit notification delivery states and retry | Improves diagnostics and reliability; current boolean baseline is usable |
| D-006 | Database schema migrations and backup workflow | Required before meaningful schema evolution or service use, not before current local operation |
| D-007 | Per-source operational status dashboard | Improves observability; logs already provide a baseline |
| D-008 | Release smoke, lint, coverage, audit, checksum | Raises release confidence; current CI/test/build baseline already functions |
| D-009 | Log rotation and log download | Prevents long-term growth; not urgent for short experimental runs |
| D-010 | Runtime config hot reload | Improves UX; restart/re-instantiation remains acceptable during experimental development |
| D-011 | Docker and Compose deployment | Useful for always-on/server deployment, outside the current portable Windows focus |
| D-012 | WebSocket or Server-Sent Events | Polling is acceptable for one local user |
| D-013 | Automatic update | Depends on a stable executable/data/config lifecycle |
| D-014 | Installer and `%LOCALAPPDATA%` mode | Portable mode is currently intentional and functional |
| D-015 | True async/concurrent source harvesting | Potential performance work; source volume does not currently justify the added complexity |
| D-016 | Token/cost telemetry | Needed only before publishing measured savings claims |
| D-017 | Expanded re-evaluation semantics | Current stored-tender custom-filter re-evaluation is useful; full sector-rule replay is optional |
| D-018 | Dependency version pinning and update policy | Improves reproducibility; can be addressed with broader release hardening |
| D-019 | Productization trigger metrics and external-signal review | Prevents premature platform work and defines when commercial hardening should be promoted |
| D-020 | Docker/Compose on-premises deployment profile | Supports repeatable always-on customer deployment after a real server-use case exists |
| D-021 | License and entitlement architecture | Needed for paid distribution; must support offline/on-premises recovery and must not be confused with application security |
| D-022 | Managed-cloud tenancy and control plane | Required only for a hosted multi-customer service with explicit operational ownership |
| D-023 | Opt-in tender record synchronization | Potential shared intelligence layer; requires provenance, validation, consent, and abuse controls |
| D-024 | Formal threat model and security review | Required before non-local, licensed, on-premises, or cloud service claims |

---

## Record 015 - Experimental Development And Productization Boundary

Tender Tracker was assembled rapidly as a working local product prototype. The current goal is not to simulate the process burden of a mature hosted service before the product direction is proven.

Decision:

- retain working local behavior and iterate in small durable slices;
- keep genuinely dangerous or correctness-critical issues on the active board;
- keep service-level, enterprise, deployment, and convenience improvements in this notes backlog;
- do not interpret every deferred item as evidence that the current application is broken;
- do not describe the product as production-ready, enterprise-ready, or operationally guaranteed while these boundaries remain experimental.

A future hosted or separately commercialized service would require a new productization phase covering deployment, monitoring, backups, migrations, support policy, security review, and service ownership.

**Status:** Accepted development policy.

---

## Record 016 - Configuration Robustness Is Deferred Hardening

The local `config.yaml` model remains accepted. Users intentionally enter their own provider, SMTP, and Telegram credentials on their own machine.

Deferred improvements:

- Pydantic or equivalent schema validation;
- temporary-file write followed by atomic replacement;
- recovery from the last valid configuration;
- masked secret fields in configuration responses;
- preserving an existing secret when a masked field is submitted unchanged;
- optional separation of tracked example config and runtime config for developer hygiene.

These improvements increase durability but do not invalidate the current BYO-LLM model.

**Status:** Deferred; promote only when configuration reliability becomes active scope.

---

## Record 017 - Authentication Hardening Depends On Exposure

The present product is a loopback-bound, single-administrator local application. Authentication requirements change materially if it is exposed to a LAN, public tunnel, reverse proxy, shared server, or hosted service.

Deferred local improvements:

- generate a random persistent JWT secret on first run;
- align the configured token lifetime with the actual token creation path;
- increase minimum password length;
- consider HttpOnly/SameSite cookies after frontend rendering risks are closed;
- add request abuse protection if non-local exposure is supported.

Decision:

- keep `127.0.0.1` as the default;
- do not add RBAC, tenants, SSO, or enterprise IAM without a product requirement;
- treat non-local exposure as a separate deployment mode with explicit documentation and hardening.

**Status:** Deferred while local-only remains the default boundary.

---

## Record 018 - Notification Reliability And SMTP Identity

The existing notification adapters provide usable email and Telegram delivery. Several refinements are deferred:

- honor a distinct SMTP login username when it differs from the sender address;
- distinguish `disabled`, `pending`, `sent`, and `failed` instead of relying only on booleans;
- record attempt count, last attempt, and last error;
- define whether old pending tenders should be delivered when a channel is enabled later;
- add manual retry and bounded backoff;
- prevent duplicate sends when a retry follows an uncertain network outcome.

Persistence of the tender remains authoritative. Notification failure must never remove the record; that boundary is covered by active P0.5.

**Status:** Deferred adapter hardening.

---

## Record 019 - Release Confidence Improvements

The current GitHub Actions flow tests the repository and builds a Windows executable for release tags. This is a valid CI/CD baseline for the current experimental phase.

Deferred confidence improvements:

- start the built executable with `NO_BROWSER=true` and probe a health endpoint;
- test dashboard root, setup status, and static assets from the packaged binary;
- run lint and format checks;
- establish a practical coverage threshold;
- run dependency/security auditing;
- restrict `contents: write` to the release job;
- publish SHA256 checksums;
- optionally pin third-party GitHub Actions to immutable commit SHAs.

These items become more important before distributing the application to users who do not inspect source or logs themselves.

**Status:** Deferred release hardening.

---

## Record 020 - Database Evolution And Backup

SQLite remains appropriate for the current local product. `Base.metadata.create_all()` creates missing tables but is not a migration system for changing existing schemas.

Deferred work before significant model evolution:

- schema version field;
- Alembic or a smaller explicit migration mechanism;
- automatic pre-migration backup;
- configuration export/import;
- compatibility test using a database created by an older release;
- documented rollback expectations.

For the current experimental phase, users should keep copies of `tenders.db`, `config.yaml`, and `sectors.yaml` before replacing builds that alter storage behavior.

**Status:** Deferred until schema evolution requires it.

---

## Record 021 - Source Observability

Each source should eventually expose a visible operational summary:

- enabled/disabled state;
- last attempt;
- last success;
- last error;
- records discovered and records newly stored;
- current state: operational, degraded, experimental, or disabled.

The current logs are an acceptable experimental baseline. A dedicated source-health dashboard is a product usability improvement rather than a prerequisite for current local operation.

**Status:** Deferred observability improvement.

---

## Record 022 - Deployment Options Remain Optional

Potential future deployment modes:

- portable Windows executable;
- installed Windows application using `%LOCALAPPDATA%`;
- Docker/Compose for an always-on local or server deployment;
- hosted multi-user service as a separate productization effort.

Docker should not be added merely to make the repository appear mature. It should be introduced when an always-on process, remote access, repeatable server deployment, or integration with external infrastructure becomes a real requirement.

Auto-update similarly depends on stable separation between executable, runtime data, migrations, rollback, and release trust.

**Status:** Optional future architecture.

---

## Record 023 - Polling, Push Updates, And Async Terminology

The current local single-user UI can use REST polling without material product harm. WebSocket or Server-Sent Events should be added only when real-time job progress or multiple connected clients justify the additional state management.

Similarly, the current use of background threads does not make the whole ingestion engine an asynchronous crawler. Documentation should use precise terms:

- synchronous HTTP adapters;
- background-thread execution;
- optional future concurrent or async harvesting.

A true async/concurrent rewrite should be driven by measured source latency or scale, not by terminology alone.

**Status:** Deferred performance and UX work.

---

## Record 024 - Runtime Configuration Reload

Some settings are loaded when orchestrators, classifiers, scrapers, or notifiers are instantiated. A future configuration service could define and centralize hot-reload behavior.

Possible target behavior:

- new scan reads current enabled sources and rules;
- provider and notifier credentials refresh before their next use;
- interval changes affect the next scheduling decision;
- the UI clearly marks settings that require restart.

Restarting or recreating the runtime object remains acceptable in the current experimental workflow.

**Status:** Deferred usability improvement.

---

## Record 025 - Measurement Before Optimization Claims

Future telemetry may record:

- local-rule match rate;
- LLM fallback-call count;
- custom-filter-call count;
- provider latency and failure rate;
- input/output tokens where providers report them;
- per-source processing time.

Telemetry should avoid persisting sensitive prompt or tender content unnecessarily. Until representative measurements exist, public documentation should explain the deterministic-first mechanism without attaching percentage savings or performance guarantees.

**Status:** Deferred measurement work and active documentation rule.

---

## Record 026 - Evidence-Gated Commercialization Path

Tender Tracker can evolve from a rapidly built local application into a commercial product, but the order matters. The current working prototype should first produce external evidence: people install it, continue using it, request deployment help, ask for team access, or show willingness to pay.

Decision:

- do not front-load SaaS, licensing, tenancy, or enterprise operations before demand is visible;
- use public posts, demonstrations, early users, support conversations, and repeated feature requests as product signals;
- promote only the next bounded productization slice to `BOARD.md`;
- keep one core tender ingestion/classification codebase and add delivery-specific boundaries around it;
- separate "interesting response" from real validation: durable usage, deployment requests, or willingness to pay are stronger evidence than likes alone.

Suggested stage model:

```text
Stage 0 - Operational local prototype
Stage 1 - Public demonstration and external usage signal
Stage 2 - Distributable security-conscious standalone release
Stage 3 - Supported on-premises deployment
Stage 4 - Managed cloud service
Stage 5 - Cooperative/federated tender intelligence
```

Each stage must define its own owner, support expectation, threat model, data boundary, and acceptance gate. The later stages are possibilities, not commitments.

**Status:** Strategic direction accepted; inactive until external evidence promotes it.

---

## Record 027 - One Core Engine, Multiple Delivery Modes

The same source adapters, normalization contract, deterministic filters, optional LLM evaluation, database model, and notification logic can support several delivery modes. This does not mean every mode should share the same operational shell.

Possible modes:

1. **Portable local edition**
   - current single-user baseline;
   - local SQLite, YAML configuration, and BYO credentials;
   - lowest operational burden.

2. **Licensed standalone edition**
   - signed release, installer or portable package;
   - update and rollback policy;
   - offline-capable entitlement where required;
   - optional paid source adapters or support agreement.

3. **On-premises service**
   - Docker/Compose or managed Windows/Linux service;
   - customer-controlled database, credentials, network, and backups;
   - reverse proxy, persistent volumes, health checks, and documented recovery;
   - suitable for organizations that cannot send tender or LLM data to a shared cloud.

4. **Managed cloud service**
   - tenant isolation, centralized operations, monitoring, backups, rate controls, billing, and support;
   - provider credential strategy must be explicit: customer BYO key, platform-managed key, or both;
   - a separate control plane may be needed, but source adapters should remain reusable.

Decision:

- preserve the reusable domain engine;
- keep deployment, identity, licensing, and tenancy concerns outside scraper/parser logic;
- do not force cloud assumptions into the current local data model;
- choose Docker because a deployment requirement exists, not as repository decoration.

**Status:** Future delivery architecture hypothesis.

---

## Record 028 - Authentication, Licensing, And Security Are Different Boundaries

Authentication answers who may use an installation. Authorization answers what that identity may do. Licensing or entitlement answers whether a commercial feature or installation is permitted. None of these alone makes the application "unhackable."

Before a paid or remotely exposed edition, define:

- deployment boundary: loopback, LAN, customer VPN, public internet, or managed cloud;
- identity model: local administrator, organization users, SSO, service accounts;
- secret boundary: local file, OS credential store, environment secret, customer vault, or managed secret service;
- update trust: signed artifacts, version manifest, rollback, and revoked release handling;
- data boundary: local database, customer database, central database, or synchronized subset;
- audit and recovery: login events, configuration changes, backups, restore, and incident handling.

License architecture must also specify:

- offline grace and air-gapped on-premises use;
- clock changes and machine replacement;
- lost license server connectivity;
- backup/restore and hardware migration;
- feature entitlement versus installation entitlement;
- privacy-preserving activation telemetry;
- a failure mode that does not destroy customer data.

Decision:

- complete the active rendering, TLS, persistence, concurrency, and runtime-path hardening first;
- introduce a formal threat model before non-local distribution;
- add licensing after the intended delivery mode is chosen;
- never present license enforcement as a substitute for application security.

**Status:** Deferred productization security policy.

---

## Record 029 - Cooperative Tender Intelligence And Federated Synchronization

A future network may allow customer installations to contribute normalized public tender observations to a shared intelligence layer. This could reduce repeated source traffic, improve detection speed, provide cross-customer source resilience, and create a richer historical dataset.

The safe first interpretation is **not** an anonymous torrent network. A practical first version would be an opt-in client-to-service synchronization model:

```text
customer scraper
-> local normalization and duplicate check
-> consent and field-level redaction policy
-> signed client submission
-> central validation/provenance store
-> deduplicated shared tender record
-> clients receive permitted updates
```

Potential synchronized fields:

- source name and stable public identifier;
- canonical public link;
- normalized title, organization, dates, and category;
- content hash and first/last observed timestamps;
- parser/source version;
- provenance and confidence metadata.

Fields that should not be synchronized by default:

- provider API keys or notification credentials;
- customer-specific sectors, prompts, matches, notes, or commercial interests;
- private/authenticated procurement data;
- local user identities and operational logs.

Required controls:

- explicit customer opt-in and transparent data policy;
- source terms/legal review and rate-limit respect;
- authenticated installations and signed submissions;
- schema validation, canonicalization, and duplicate control;
- poisoning/spam/replay detection;
- provenance retained for every contributed observation;
- confidence or quorum rules before one client can overwrite shared truth;
- revocation and deletion workflows;
- central service compromise and client compromise considered separately.

Architecture progression:

1. central opt-in synchronization;
2. regional/cache replication if scale requires it;
3. append-only or signed event exchange where provenance benefits justify it;
4. peer-to-peer/gossip only if central bottlenecks, censorship resistance, or offline mesh requirements are demonstrated.

Decentralization can reduce a single operational bottleneck, but it does not automatically prevent hacking. It increases the number of trust boundaries and can make poisoned-data propagation harder to contain. Security comes from identity, signatures, validation, least privilege, isolation, monitoring, and recoverability.

**Status:** Research hypothesis; not approved for implementation.

---

## Record 030 - Promotion Gates For Productization Work

Future work should move from `NOTES.md` to `BOARD.md` only when a concrete trigger exists.

Suggested promotion gates:

### Gate A - Distribution Hardening

Trigger examples:

- several external users run the application independently;
- release installation or update issues repeat;
- users ask for a supported binary rather than source execution.

Promote:

- executable smoke test;
- signed release/checksum;
- installer or stable portable data directory;
- backup/restore and migration baseline;
- formal security review for the selected exposure boundary.

### Gate B - On-Premises Service

Trigger examples:

- customer requests an always-on server;
- multiple internal users need the same dataset;
- customer requires local data and credential control.

Promote:

- Docker/Compose or system-service deployment;
- reverse proxy and TLS termination;
- externalized persistent database/configuration;
- health checks, backups, restore, and operational documentation;
- organization identity and audit requirements.

### Gate C - Managed Cloud

Trigger examples:

- customers request operation without managing infrastructure;
- recurring revenue can fund monitoring, support, and incident ownership;
- tenant isolation requirements are understood.

Promote:

- tenant model and authorization;
- managed database and secret strategy;
- observability, queues, rate limits, backup/restore, and incident policy;
- billing and entitlement;
- source access/caching strategy that respects public portal constraints.

### Gate D - Shared Tender Network

Trigger examples:

- the same source is repeatedly scraped by many installations;
- customers explicitly value faster shared discovery or historical coverage;
- legal, consent, provenance, and data-poisoning questions have owners.

Promote:

- a narrow central synchronization proof of concept;
- field-level data contract;
- signed client identity and validation;
- opt-in controls and a deletion/revocation path;
- measurable benefit before distributed/P2P expansion.

**Status:** Accepted promotion framework; all gates currently inactive.

