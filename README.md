# EV Orchestrator MVP

A minimal end-to-end MVP for an EV job orchestration platform. Includes:
- FastAPI backend (jobs, estimates, matching, contracts, settlement)
- Simple frontend scaffold (Vite)
- Postgres database via Docker
- Basic ETL and model stubs

## Quickstart

1. Copy environment file:

```bash
cp .env.example .env
```

2. Start services:

```bash
docker compose up --build
```

- Backend API: http://localhost:8000 (docs at http://localhost:8000/docs)
- Frontend: http://localhost:5173
- Postgres: localhost:5432 (db: `evdb`, user: `ev`, pass: `evpass`)

## Project Structure

```text
./
├─ docker-compose.yml
├─ .env.example
├─ data/
│  └─ sample_jobs.csv
├─ backend/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ app/
│     ├─ main.py
│     ├─ config.py
│     ├─ db.py
│     ├─ models.py
│     ├─ schemas.py
│     ├─ crud.py
│     ├─ utils.py
│     ├─ routes/
│     └─ services/
└─ frontend/
   ├─ package.json
   ├─ index.html
   └─ src/
```

## Development

- Code changes in `backend/` and `frontend/` are mounted into containers via volumes for live reload.
- To seed sample data or run ETL, use scripts under `backend/scripts/` (to be added).

## Analytics: preprocess XLS and compute demand

### 1) Preprocess the XLS/XLSX to CSV
```bash
cd ev-orchestrator-mvp
python analytics/preprocess_xls.py -i "/path/to/Copy of ELERIDE IBBN Payout Sep 25 WEEK 4.xlsx" -o data/rider_week_clean.csv
```

### 2) Compute demand indicators and artifacts
```bash
python analytics/compute_demand_indicators.py -i data/rider_week_clean.csv -o artifacts/demand_store.csv -j artifacts/demand_store.json
```

### 3) (Optional) Serve demand JSON via backend
- Endpoint: GET /demand/forecast?city=PUNE
- Make sure artifacts/demand_store.json exists (generated in step 2)

## Extended analytics: preprocess XLS → compute insights

1) Preprocess the XLS/XLSX to CSV
```bash
python analytics/preprocess_xls.py -i "/path/to/Copy of ELERIDE IBBN Payout Sep 25 WEEK 4.xlsx" -o data/rider_week_clean.csv
```

2) Compute extended insights
```bash
python analytics/compute_extended_insights.py -i data/rider_week_clean.csv -o artifacts/demand_store_extended.csv -j artifacts/demand_store_extended.json
```

3) API endpoints
- GET /demand/forecast?city=PUNE (prefers extended JSON if present)
- GET /demand/insights?city=PUNE (extended-only)

## Notes

- Alembic is optional; DB schema can be created at app startup if desired.
- The ETL and model training/serving are stubs to keep scope minimal.
