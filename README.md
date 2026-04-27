# Octane

Live Sri Lanka fuel price intelligence — current prices, history, world comparison, trip calculator, alerts, embed widget, free public API.

> An Ardeno Studio production.

## Stack

- **Backend** — FastAPI + PostgreSQL on Railway
- **Scrapers** — `httpx` + `BeautifulSoup`, daily 8am cron
- **Frontend** — React + Vite + Tailwind + Recharts on Vercel
- **Sources** — `ceypetco.gov.lk`, `lankaiocoil.lk`, `globalpetrolprices.com`

## Layout

```
backend/   FastAPI app, scrapers, DB schema
frontend/  React dashboard + embed widget
infra/     Railway + Vercel deploy configs
```

## Local dev

```bash
# Backend
cd backend
python -m venv .venv && source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # set DATABASE_URL
python -m app.db.init        # create tables
python -m app.scrapers.run   # seed prices
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/v1/prices/latest` | Current price, all fuel types, both sources |
| GET | `/v1/prices/history?fuel=92&days=730` | Historical for charting |
| GET | `/v1/prices/changes` | All revision events with deltas |
| GET | `/v1/comparison/world?fuel=95` | Sri Lanka vs world average + neighbors |
| GET | `/v1/calculator/trip?distance=30&efficiency=12&fuel=92` | Trip cost calculation |
| POST | `/v1/alerts/subscribe` | Email + threshold |
| GET | `/v1/embed/widget?fuel=92&theme=light` | Embeddable HTML widget |

Swagger docs at `/docs`.
