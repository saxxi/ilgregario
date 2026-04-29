# IlGregario

A fantasy cycling web app built with FastAPI and Supabase. Users pick real professional cyclists and score points based on actual race results from the WorldTour calendar.

## Stack

- **Backend:** Python / FastAPI
- **Database:** Supabase (Postgres)
- **Deployment:** Fly.io
- **Data:** sourced from [procyclingstats.com](https://www.procyclingstats.com)

## Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- A Supabase project

### Install

```bash
uv sync
```

### Environment

Copy `.env` and fill in your Supabase credentials:

```bash
cp .env .env.local
```

Required variables:

```
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=<anon or service role key>
SECRET_KEY=<random string for session signing>
```

### Run locally

```bash
uv run uvicorn main:app --reload
```

### Database migrations

Apply migrations via the Supabase dashboard or CLI:

```bash
supabase db push
```

### Seed demo data

```bash
uv run python scripts/seed.py
```

### Sync race results

```bash
uv run python scripts/sync_races.py
```

Or trigger via the web UI at `/sync-races` (requires login).

## Deployment

Deployed on Fly.io. See `fly.toml` for configuration.

```bash
fly deploy
```

---

## Data attribution & disclaimer

Cycling data (race results, rider profiles, race calendars) is sourced from
**[procyclingstats.com](https://www.procyclingstats.com)**.

- This project is **non-commercial and for educational purposes only**.
- Data is stored privately and used solely to power the fantasy game — it is
  not redistributed publicly.
- Please respect [procyclingstats.com's Terms of Service](https://www.procyclingstats.com/info/terms-of-service.php).

The **MIT license** in this repository covers the source code only. It does
not grant any rights over third-party data.

---

## License

[MIT](./LICENSE) — source code only. See data disclaimer above.
