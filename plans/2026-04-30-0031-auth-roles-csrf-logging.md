# Auth roles, CSRF protection, and logging

## Problems addressed

1. **Hardcoded admin credentials** — `ADMIN_USERNAME`/`ADMIN_PASSWORD` env vars bypass DB entirely; plaintext comparison
2. **No user roles** — single `is_admin` boolean; no super_admin concept
3. **No CSRF protection** — all admin POST endpoints are vulnerable to cross-site request forgery
4. **Silent errors** — bare `except Exception` swallows tracebacks, exposes internal messages to UI, nothing goes to logs
5. **No request visibility** — zero logging in routers or middleware; Fly.io deployment is blind
6. **Unused env vars** — `OPENAI_API_KEY` declared but never used

## DB migration (run in Supabase before deploying)

```sql
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'user'
  CHECK (role IN ('user', 'admin', 'super_admin'));

UPDATE users SET role = 'admin' WHERE is_admin = true;
```

`is_admin` column stays in DB for now — still in sync, still used by templates.

## Steps

1. **`config.py`** — remove `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `OPENAI_API_KEY`

2. **`auth.py`**:
   - Remove `check_admin_credentials`
   - `create_session_token(user_id, role, username)` — derives `is_admin` from role for template compat; session now carries `role` too
   - Add `make_csrf_token(user_id)` / `verify_csrf_token(token, user_id)` using existing `_serializer`

3. **`scripts/create_super_admin.py`** — CLI script to seed the first super_admin from the command line (username + password prompt)

4. **`routers/auth.py`** — remove env var check; DB-only login; role-based redirect (admin/super_admin → `/admin`, user → `/dashboard`)

5. **`routers/admin/shared.py`**:
   - Register `csrf_token` as a Jinja2 global on the `templates` instance
   - Add `async _guard_post(request)` — calls `_guard` then validates `_csrf` from form; returns 403 on failure
   - Keep `_guard` for GET routes unchanged

6. **All admin POST handlers** (`overview.py`, `users.py`, `athletes.py`, `races.py`, `seasons.py`) — replace `_guard` with `await _guard_post`; replace `except Exception as exc: return _redir(..., f"Errore: {exc}")` with `logger.exception(...)` + `return _redir(..., "Errore interno")`; add per-module `logger = logging.getLogger(__name__)`

7. **`routers/admin/users.py`** — replace `is_admin` checkbox with `role` dropdown (user/admin only; super_admin not creatable from UI); sync both `role` and `is_admin` on DB writes

8. **`routers/dashboard.py`** — add CSRF validation on `POST /account`; update `create_session_token` call to use `role` from session

9. **Templates** — add `<input type="hidden" name="_csrf" value="{{ csrf_token(session.user_id) }}">` to every POST form in admin templates and `account.html`; update `users.html` to show role badge and use role dropdown

10. **`main.py`** — `logging.basicConfig(stream=sys.stdout)` once at startup; HTTP request/response logging middleware

11. **`AGENTS.md`** — update auth section to reflect new role system
