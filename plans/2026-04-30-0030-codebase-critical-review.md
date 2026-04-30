# Critical Codebase Review — Resume Readiness

> Snapshot date: 2026-04-30. Severity: 🔴 Critical / 🟠 High / 🟡 Medium / 🔵 Low.

---

## Summary

This is a **working prototype deployed before hardening**. Real functionality exists (scoring engine, PCS scraper, Supabase integration, Fly.io deploy), but the codebase has systemic gaps that disqualify it from "production-ready" status: zero tests, plaintext admin password, no CSRF protection, and silent error swallowing throughout.

---

## Findings

### 🔴 CRITICAL

#### C1 — Zero test coverage
No `tests/` directory, no `pytest`, no test dependencies. 3,454+ lines of production code with no verification layer. The scoring engine, ranking algorithms, and auth logic are unexercised. Any refactor is a leap of faith.

**Impact:** Single biggest red flag for a resume. Every other issue compounds because there's no safety net.

**Files affected:** entire codebase.

#### C2 — Plaintext admin password (`auth.py:51-52`, `config.py:6-7`)
```python
return username == ADMIN_USERNAME and password == ADMIN_PASSWORD
```
No hashing, no bcrypt, no salt. Password stored as a plain env var and compared as string. `bcrypt` is already in `pyproject.toml` but unused.

#### C3 — No CSRF protection (all `routers/admin/*.py` POST handlers)
Admin endpoints create users, delete races, modify results. No CSRF token. A malicious link clicked by a logged-in admin executes with full privilege.

#### C4 — Global DB singleton with no injection path (`database.py:7-11`)
`get_db()` returns a module-level cached singleton. No way to inject a test client, a mock, or a transaction scope. Makes unit testing structurally impossible without monkey-patching.

#### C5 — Bare `except Exception` swallowing errors (`routers/admin/*.py` — 10+ occurrences)
```python
except Exception as exc:
    return _redir("/admin/users", f"Errore: {exc}")
```
Catches syntax errors, DB constraint violations, and real bugs identically. Leaks internal error messages to the UI. Logs nothing. Production has zero visibility.

---

### 🟠 HIGH

#### H1 — God module: `queries/detail.py` (504 lines, 0 classes)
Mixes DB queries, ranking algorithms, H2H computation, data transformation, and HTML generation. Cannot unit-test ranking logic without mocking the DB. Cannot reuse ranking in scripts.

#### H2 — God module: `queries/dashboard.py` (288 lines)
Leaderboard computation, chart data, trend calculation, and narrative generation all inline. No extracted domain concepts.

#### H3 — No input validation on admin forms (`routers/admin/races.py:34-66`, `athletes.py:86-114`)
- `race_type` accepts any string (no enum check)
- `year` accepts "026" or negative values
- `difficulty`/`prestige` accept out-of-range integers
- No max-length check on any string field

#### H4 — No request logging; production is blind
No FastAPI middleware for request/response logging. Errors are caught and redirected silently. The Fly.io deployment has no observability.

#### H5 — Missing Pydantic models for request/response
All form data arrives as raw strings and is cast inline (`int(year)`, `name.strip()`). FastAPI's Pydantic validation layer is entirely bypassed. No schema guarantees at boundaries.

#### H6 — Optional context re-loading pattern creates hidden DB round-trips (`queries/dashboard.py:17-18`)
```python
ctx = ctx or load_season_context()
```
Repeated across 8+ functions. If any caller omits `ctx`, it silently fires 4 extra DB queries. No enforcement, no warning.

#### H7 — AGENTS.md self-update is an honour system with no tooling
Protocol says "update AGENTS.md after architecture changes" but there's no CI hook, no linter, no diff check. Sub-package AGENTS.md files (`queries/AGENTS.md`, `routers/admin/AGENTS.md`) diverge silently. Stale entries include `db_queries.py` still listed as the module after the split.

---

### 🟡 MEDIUM

#### M1 — Unused dependencies (`pyproject.toml:5-24`)
`openai`, `numpy`, `pandas` declared as required dependencies, none imported anywhere. Adds install bloat and signals cargo-cult dependency management.

#### M2 — No pinned dependency versions
All packages listed without version constraints. A `pip install` six months from now may pull incompatible versions. No `requirements.lock` or equivalent.

#### M3 — Vague commit messages
```
fe37a0d images
b470b81 Increase font sizes & improved UI dashboard
c3b3b94 phase 1
22c4157 flyio setup
425c7ab begin
```
No conventional commit format. No plan references. No issue links. Commit history is not a useful audit trail.

#### M4 — Incomplete features masquerading as done
- **FirstCycling import** (`routers/admin/athletes.py:39-52`): URL parsed, `firstcycling_id` returned, data never fetched ("Cloudflare protected"). Dead field in DB.
- **Stage results** (`scoring.py`, `queries/context.py`): scoring logic exists, admin can enter data, dashboard never displays it.
- **Difficulty/prestige** (`races` table, admin forms): stored but never used in scoring.

#### M5 — Duplicated logic across modules
- `slugify()` called in three different files
- Country code → name mapping duplicated in `utils.py` and referenced from old import paths
- HTTP caching/sleep/headers pattern repeated in `importers/pcs.py` and `scripts/fetch_athlete_photos.py`

#### M6 — `session["user_id"]` KeyError risk (`routers/dashboard.py:204`)
```python
user_id = session["user_id"] if session else None
```
If session dict exists but lacks `"user_id"` key (e.g., data migration, schema change), this raises `KeyError`, not a graceful 401.

#### M7 — Plans have no status tracking
29 plan files exist with no indication of which are complete, in progress, superseded, or abandoned. No `status:` field, no archive folder. A reader cannot distinguish shipped work from aspirational notes.

---

### 🔵 LOW

#### L1 — Magic numbers in scoring config (`config.py:23-28`)
Stage thresholds `[1, 4, 8, 14, 999]` have no comments explaining what they map to (day races, short stage races, week races, grand tours, etc.). Future maintainers must reverse-engineer the domain.

#### L2 — Inconsistent abbreviations throughout
`ua` (user_athletes), `rr` (race_results), `ath` (athlete) used ubiquitously with no glossary. Not self-documenting.

#### L3 — Open redirect footgun in `_redir()` (`routers/admin/shared.py:19-21`)
`path` parameter is not validated against a whitelist. Safe today because all callers use hardcoded strings, but the API is dangerous by design.

#### L4 — `sys.path` hacks in scripts (`scripts/import_athletes.py:1-3`)
`sys.path.insert(0, ...)` to import from parent package. Indicates the project isn't installed as a package; scripts run outside the project's module system.

#### L5 — No `__all__` exports; public API is undefined
No module in the codebase defines `__all__`. Any name is importable from any module. No enforced separation of public vs. internal API.

---

## Process Observations

### What works well
- **Mandatory planning protocol** (`AGENTS.md` rule 1): every significant change has a plan file with clear steps and file references. This is genuinely useful.
- **AGENTS.md hierarchy**: main + sub-package AGENTS.md is a good idea; execution is inconsistent but the structure is right.
- **SeasonContext pattern**: loading context once per request and threading it through is an explicit architectural decision, documented and (mostly) followed.

### What doesn't
- **No automated verification** for any protocol: no CI, no pre-commit hooks, no test runner.
- **Plans don't track completion**: impossible to tell from the repo state which plans are done vs aspirational.
- **Git history doesn't reference plans**: commit messages never mention `plans/yyyy-mm-dd-NNNN-*`, so the link between intent and execution is invisible.
- **AGENTS.md update is the last thing that happens** (if at all): architecture diverges from documentation silently between tasks.

---

## Recommended Priority Order

1. **Add tests** — even 10 tests covering `scoring.py`, `utils.py`, and one route. Signal counts more than coverage %.
2. **Fix plaintext password** — `bcrypt.hashpw` is already in the dependencies; use it.
3. **Add CSRF tokens** — one middleware, applies everywhere.
4. **Fix bare except clauses** — catch specific exceptions; log with `logging.exception()`.
5. **Add a `status:` field to plans** — `status: done | in-progress | draft`. Small change, large signal.
6. **Adopt conventional commits** — `feat:`, `fix:`, `docs:`, `refactor:`. Enforce with a pre-commit hook.
7. **Remove unused deps** — delete `openai`, `numpy`, `pandas` from `pyproject.toml`.
8. **Pin dependency versions** — run `pip freeze > requirements.lock` or use `uv lock`.

---

## Codebase Metrics (snapshot)

| Metric | Value |
|---|---|
| Total Python files | ~35 |
| Estimated LOC | ~3,500 |
| Test files | **0** |
| Test coverage | **0%** |
| Plan files | 30 |
| Open security issues | 5 (C2, C3, H3, M6, L3) |
| Unused dependencies | 3 (`openai`, `numpy`, `pandas`) |
