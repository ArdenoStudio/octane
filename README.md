<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./frontend/public/octane-logo-nav-white.svg" />
    <img src="./frontend/public/octane-logo-nav.svg" alt="Octane" height="60" />
  </picture>
</p>

<p align="center">
  Live Sri Lanka fuel price intelligence — built by <strong>Ardeno Studio</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-live-f59e0b?style=flat-square" />
  <img src="https://img.shields.io/badge/API-free%20%26%20open-f59e0b?style=flat-square" />
  <img src="https://img.shields.io/badge/stack-FastAPI%20%2B%20React-1b1b1b?style=flat-square" />
  <img src="https://img.shields.io/badge/deployed-Vercel%20%2B%20Fly.io-1b1b1b?style=flat-square" />
  <a href="https://wakatime.com/badge/user/c81e86af-3873-4c76-b802-f7f42fd0c090/project/4e90dc24-711f-4562-9f3a-28794ba04e5e"><img src="https://wakatime.com/badge/user/c81e86af-3873-4c76-b802-f7f42fd0c090/project/4e90dc24-711f-4562-9f3a-28794ba04e5e.svg?style=flat-square" alt="wakatime" /></a>
  <br/>
  <img src="https://github.com/ArdenoStudio/octane/actions/workflows/ci.yml/badge.svg" alt="CI" />
  <img src="https://github.com/ArdenoStudio/octane/actions/workflows/deploy-backend.yml/badge.svg" alt="Deploy backend" />
  <img src="https://github.com/ArdenoStudio/octane/actions/workflows/scrape.yml/badge.svg" alt="Scrape fuel prices" />
  <img src="https://github.com/ArdenoStudio/octane/actions/workflows/digest.yml/badge.svg" alt="Digest" />
  <img src="https://github.com/ArdenoStudio/octane/actions/workflows/dispatch-alerts.yml/badge.svg" alt="Dispatch alerts" />
  <img src="https://github.com/ArdenoStudio/octane/actions/workflows/sentiment.yml/badge.svg" alt="Sentiment" />
</p>

---

Octane tracks CPC fuel prices daily the moment they're revised, and presents them with historical charts, a world comparison, a trip cost calculator, email price alerts, an embeddable widget, and a free public API.

## Features

- **Live prices** — scraped daily at 8am from CPC and LIOC
- **Price history** — up to 10 years of revision events with delta indicators
- **World comparison** — Sri Lanka vs global average and regional neighbours
- **Trip calculator** — distance + efficiency → exact cost at today's prices
- **Price alerts** — one email the moment a fuel crosses your threshold
- **Embed widget** — drop a live price badge into any site, no key needed
- **Free API** — open REST endpoints, no auth required for reads

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI · PostgreSQL · Fly.io |
| Scrapers | `httpx` + `BeautifulSoup` · daily 8am cron |
| Frontend | React 18 · Vite · Tailwind CSS · Recharts |
| Hosting | Vercel (frontend) · Fly.io (backend + DB) |
| Sources | `ceypetco.gov.lk` · `lankaiocoil.lk` · `globalpetrolprices.com` |

## Project layout

```
octane/
├── .github/        GitHub Actions — CI, deploy, scrape, digest
├── backend/        FastAPI app, scrapers, DB schema, alert mailer
└── frontend/       React dashboard, embed widget, Fly/Vercel configs
```

## Local dev

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # set DATABASE_URL
python -m app.db.init         # create tables
python -m app.scrapers.run    # seed prices
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev                   # → http://localhost:5173
```

## API endpoints

All endpoints are free to use with no API key.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/v1/prices/latest` | Current prices for all fuel types |
| `GET` | `/v1/prices/history?fuel=92&days=730` | Historical revisions for charting |
| `GET` | `/v1/prices/changes` | All revision events with price deltas |
| `GET` | `/v1/comparison/world?fuel=95` | Sri Lanka vs world average + neighbours |
| `GET` | `/v1/calculator/trip?distance=30&efficiency=12&fuel=92` | Trip cost at today's prices |
| `POST` | `/v1/alerts/subscribe` | Subscribe to a price threshold alert |
| `GET` | `/v1/embed/widget?fuel=92&theme=light` | Embeddable HTML price widget |

Interactive docs available at `/docs` (Swagger UI).

---

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./frontend/public/octane-o-white.svg" />
    <img src="./frontend/public/octane-o.svg" alt="" height="24" />
  </picture>
  <br/>
  <sub>An <strong>Ardeno Studio</strong> production · <a href="https://octane-smoky.vercel.app/">octane.lk</a></sub>
</p>
