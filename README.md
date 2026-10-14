# Travel Cost Optimizer

Full-stack app with a FastAPI backend and a React (Vite) frontend.

## Structure

```
backend/   FastAPI app
frontend/  React app (Vite)
```

## Database

Requires Docker.

```
docker compose up -d
```

This starts Postgres on `localhost:5432` (user/password/db: `postgres`/`postgres`/`travel_cost_optimizer`).

## Backend

```
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
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
cp .env.example .env
npm run dev
```

App: http://localhost:5173
