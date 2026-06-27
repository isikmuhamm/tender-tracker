# Tender Tracker - Agent Instructions

## Operating Mode

> **CRITICAL:** Treat `business/BOARD.md` as the active development source of truth.

- Read the relevant board item before changing code, tests, configuration, CI, or public documentation.
- Use `business/NOTES.md` for the rationale behind product and architecture decisions.
- Use `business/HISTORY.md` only when past implementation details or the reason behind an existing design are required.
- Keep each implementation run focused on one active P0 item unless the user explicitly requests a broader batch.
- Do not promote audit output, chat summaries, or generated reports into a parallel roadmap. Convert accepted findings into the board and notes first.

## Continuation Bootstrap

At the beginning of a new implementation session:

1. Run `git status --short` and preserve unrelated user work.
2. Read `README.md` for current public behavior and supported installation paths.
3. Read this file for repository rules.
4. Read the first section of `business/BOARD.md`, then the specific active item.
5. Search `business/NOTES.md` only for the matching decision or record ID.
6. Inspect only the code, tests, and configuration related to that item.

Do not start with a broad repository rewrite when a targeted inspection is enough.

## Product Boundary

Tender Tracker is a local-first, single-administrator tender intelligence application.

Current product intent:

- collect public tender listings from independent source adapters;
- apply deterministic exclusions and sector rules before optional LLM work;
- support user-provided Gemini, OpenAI-compatible, or Anthropic credentials;
- store operational state locally in SQLite and YAML;
- expose a local FastAPI dashboard;
- notify through optional SMTP email and Telegram channels;
- distribute as source code and a portable Windows executable.

The product is not currently:

- a hosted SaaS platform;
- a multi-tenant procurement suite;
- a paid subscription or licensing service;
- a replacement for EKAP or other procurement portals;
- a guarantee that every source remains scrapeable when the source changes;
- a remote secret-management service.

## Architecture Boundaries

- Keep source-specific fetching and parsing under `src/scraper/` and behind `BaseScraper`.
- Keep provider-specific LLM HTTP behavior inside `src/llm_client.py` or a future provider layer.
- Keep orchestration in `src/scheduler.py`; source adapters and notifiers must not coordinate each other directly.
- Keep database access behind `src/database.py` sessions and explicit transaction boundaries.
- Keep frontend mutations behind authenticated API endpoints.
- Do not add source-specific conditions to unrelated scrapers, notifiers, or frontend views.
- Treat each external source as independently degradable: one source failure must not stop the remaining sources.
- Do not describe EKAP as operational until public-list extraction produces real records and fixture-based tests verify the parser.
- Do not implement licensing, tenancy, managed cloud, or federated synchronization unless the relevant promotion gate in `business/NOTES.md` has been explicitly moved to `business/BOARD.md`.
- Keep the reusable ingestion/classification engine independent from future deployment, entitlement, and tenant-control layers.

## Processing Contract

The canonical processing order is:

```text
source ingestion
-> duplicate check
-> global exclusions
-> local sector classification
-> optional fallback LLM sector classification
-> sector-scoped custom LLM filters
-> database persistence
-> optional email and Telegram notification
```

Changes that alter this order, classification semantics, notification eligibility, or persistence behavior require a matching update in `business/BOARD.md` and `business/NOTES.md`.

## Configuration And Credentials

Tender Tracker follows a bring-your-own-LLM model.

- Repository defaults and release templates must not contain real credentials.
- Credentials entered through the local dashboard are user-owned runtime data.
- Never write API keys, SMTP passwords, Telegram tokens, JWT secrets, or real recipient addresses to tests, screenshots, logs, commit messages, or public documentation.
- Avoid placing credentials in URL query strings.
- Do not log full request headers or provider URLs containing credentials.
- Preserve the local-first model unless the board explicitly approves a hosted secret boundary.

## Source Adapter Standard

Every source adapter should provide:

- an explicit `source_name`;
- bounded connection and read timeouts;
- isolated error handling;
- deterministic parsing from captured HTML or JSON fixtures;
- stable record fields: `link`, `title`, `summary`, `category`, `source`;
- duplicate-safe links or source identifiers;
- a visible operational status: operational, degraded, experimental, or disabled.

Default tests must not depend on live public websites. Live probes should be opt-in and must tolerate temporary source unavailability without making the normal suite flaky.

## Execution Habits

Before substantial edits, state or record:

- active board item;
- intended behavior change;
- affected modules;
- risks and compatibility concerns;
- targeted tests;
- public documentation impact.

Implementation rules:

- Prefer a small durable slice over a broad speculative rewrite.
- Do not silently change data formats, config keys, database columns, or notification semantics.
- Add or update tests with behavior changes.
- Preserve backward compatibility for existing portable installations when practical.
- If a migration is required, add an explicit migration or compatibility path; `create_all()` is not a migration strategy.
- Do not perform destructive git operations or force-push unless explicitly requested.
- Always treat git push as a sensitive/elevated operation; request explicit approval (elevation) from the user before executing any push command and never push autonomously.

## Test And Verification Standards

Run targeted tests first, then the full suite.

Baseline commands:

```bash
python -m pytest tests/test_target.py -q
python -m pytest -q
```

For release or packaging changes:

```bash
python build.py
```

Critical behavior should not rely only on mocks. Prefer fixtures and real local boundaries for:

- SQLite persistence and transaction behavior;
- authentication and protected API routes;
- configuration read/write behavior;
- scraper parsing;
- notification rendering and escaping;
- scheduler/job-state behavior;
- packaged executable startup.

Live provider or public-source tests must be opt-in and require explicit environment flags and credentials.

## Documentation Discipline

Document roles are intentionally separate:

- `README.md`: public product explanation, verified features, installation, usage, architecture, limits.
- `business/BOARD.md`: active status, priorities, acceptance criteria, current recommended next step.
- `business/NOTES.md`: decisions, rationale, trade-offs, known risks, product memory.
- `business/HISTORY.md`: completed implementation stages, commit evidence, verification, remaining boundaries.
- `AGENTS.md`: repository working rules and engineering guardrails.

Rules:

- Do not let `README.md` claim behavior that the current release does not provide.
- Keep the board concise; move completed implementation detail to history.
- `BOARD.md` contains only active critical work. Keep non-critical hardening, productization, deployment, and convenience backlog in `NOTES.md` until the owner deliberately promotes an item.
- Notes may contain a curated deferred backlog, but not raw audit dumps or unreviewed chat output.
- Update history after a completed milestone, not after every small edit.
- Distinguish operational, tested, packaged, released, and production-ready states.

## Current Work Order

Current priority and implementation order are delegated to `business/BOARD.md`. Do not duplicate the active roadmap here.
