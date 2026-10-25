# Roadtrip Planner

Full-stack app with a FastAPI backend and a React (Vite) frontend.

## Structure

```
backend/   FastAPI app
frontend/  React app (Vite)
```

## Run everything locally

```
./dev.sh
```

Starts the backend on http://localhost:8000 and the frontend on http://localhost:5173 (Ctrl+C stops both). It expects the one-time setup below (backend venv, `.env` files, and your own [API keys](#api-keys-you-need-your-own)) to be done.

## API keys (you need your own)

This repo does **not** include any API keys. To run the app locally you must create your own and put them in the git-ignored `.env` files (copy each `.env.example`). Without them, routes, maps, and place search won't work.

| Key | Where it goes | Required? | Where to get it |
| --- | --- | --- | --- |
| **Google Maps Platform key (backend)** | `backend/.env` → `MAPS_API_KEY` | **Yes** | [Google Cloud Console](https://console.cloud.google.com/google/maps-apis) → enable **Routes API** and **Places API (New)** |
| **Google Maps Platform key (frontend)** | `frontend/.env` → `VITE_GOOGLE_MAPS_API_KEY` | **Yes** | Same console → enable **Maps JavaScript API** and **Places API (New)** |
| **NREL / NLR API key** | `backend/.env` → `NREL_API_KEY` | Only for EV trips | [developer.nlr.gov/signup](https://developer.nlr.gov/signup/) (free). The default `DEMO_KEY` works but is heavily rate limited. |

Notes:
- **To keep setup simple, you can use one Google key for both the backend and the frontend.** Create a single key with **Routes API**, **Places API (New)**, and **Maps JavaScript API** enabled, and paste the same value into `MAPS_API_KEY` and `VITE_GOOGLE_MAPS_API_KEY`. (Separate, restricted keys are the better practice for anything beyond local development.)
- Google Maps Platform requires a Google Cloud project with billing enabled (there is a monthly free credit).
- Never commit real keys. `.env` files are git-ignored; only the `.env.example` templates are tracked.

## Database

Requires Docker.

```
docker compose up -d
```

This starts Postgres on `localhost:5432` (user/password/db: `postgres`/`postgres`/`roadtrip_planner`).

## Backend

```
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env   # then set MAPS_API_KEY (see API keys above)
./venv/bin/alembic upgrade head
./venv/bin/uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Changing the database schema

1. Edit/add models in `backend/app/models/`.
2. Generate a migration: `./venv/bin/alembic revision --autogenerate -m "describe the change"`
3. Check the generated file in `backend/alembic/versions/`, then apply it: `./venv/bin/alembic upgrade head`
4. Commit the migration file along with your model changes.

## Frontend

```
cd frontend
npm install
cp .env.example .env   # then set VITE_GOOGLE_MAPS_API_KEY (see API keys above)
npm run dev
```

App: http://localhost:5173
