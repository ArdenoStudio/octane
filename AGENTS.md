# AGENTS.md

## Cursor Cloud specific instructions

Octane is a two-part monorepo: a **FastAPI backend** (`backend/`, Python 3.12, pip) and a **React/Vite frontend** (`frontend/`, Node, npm). It needs a local **PostgreSQL** instance. Standard commands live in `README.md`, `backend/.env.example`, `frontend/package.json`, and `.github/workflows/ci.yml` — refer to those rather than duplicating.

The startup update script already refreshes dependencies (`backend/.venv` via pip, `frontend` via `npm ci`). The notes below cover the non-obvious startup/run steps the update script intentionally does NOT do.

### PostgreSQL (required, not auto-started)
- The backend needs Postgres reachable at the default DSN `postgresql://octane:octane@localhost:5432/octane` (`backend/app/config.py`).
- Start the server on a fresh boot: `sudo pg_ctlcluster 16 main start`.
- The `octane` role + `octane` database already exist in the VM snapshot. If missing (fresh install), recreate:
  - `sudo -u postgres psql -c "CREATE USER octane WITH PASSWORD 'octane';"`
  - `sudo -u postgres psql -c "CREATE DATABASE octane OWNER octane;"`
- Apply the schema (idempotent, safe to re-run): `cd backend && .venv/bin/python -m app.db.init`. The API and scrapers also auto-apply `app/db/migrations/*.sql` on startup.

### Env files
- Copy examples once: `cp backend/.env.example backend/.env` and `cp frontend/.env.example frontend/.env`. Defaults work out of the box (frontend `VITE_API_BASE=http://localhost:8000`).

### Running the services (dev)
- Backend (port 8000): `cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000`. Swagger at `/docs`.
- Frontend (port 5173): `npm --prefix frontend run dev`.

### Seeding data — important caveat
- `cd backend && .venv/bin/python -m app.scrapers.run` populates the DB. In this environment the **news, world-price, and FX scrapers succeed**, but the **CPC scraper fails** because the source site `ceypetco.gov.lk` serves an **expired TLS certificate**, and the **LIOC scraper fails** on DNS for `lankaiocoil.lk`. These are external source-site issues, not environment problems.
- Because CPC (the "official"/confirmed source) is unreachable, the frontend "live prices" cards, price-history chart, and trip calculator (all default to `source=cpc`) will show "Awaiting data" / empty until CPC-source rows exist. News-source prices only surface as "early signals" when a CPC baseline row is present.
- To get a fully populated dashboard for local dev/testing, insert representative CPC rows into `fuel_prices` (source `cpc`) — e.g. matching the news-reported figures plus a prior revision date — as a stand-in for the unreachable live CPC scrape.

### Tests / lint / build
- Backend: `cd backend && .venv/bin/python -m pytest -q` (67 tests; no DB required — scraper tests use fixtures in `tests/fixtures/`).
- Frontend: `npm --prefix frontend run lint | typecheck | test | build` (matches CI in `.github/workflows/ci.yml`). Lint currently emits 6 `react-refresh` warnings (0 errors) — expected.

### Optional / skippable
- SMTP (`SMTP_*`), Telegram, Groq AI sentiment (`GROQ_API_KEY`), and the alert-dispatch cron are all optional; empty config makes them silently no-op. Email price-alert **signup** works without SMTP (it just can't send the confirmation email). Note: the email validator rejects reserved TLDs like `.test`/`.example` — use a real-looking domain (`.com`) when testing signup.
