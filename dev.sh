#!/usr/bin/env bash
# Runs the backend (FastAPI, :8000) and frontend (Vite, :5173) together.
# Ctrl+C stops both. Usage: ./dev.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

if [[ ! -x "$BACKEND/venv/bin/uvicorn" ]]; then
  echo "Backend dependencies missing. Run:" >&2
  echo "  cd backend && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi
if [[ ! -f "$BACKEND/.env" ]]; then
  echo "backend/.env not found. Run: cp backend/.env.example backend/.env and set your own MAPS_API_KEY (see README: "API keys")" >&2
  exit 1
fi
if [[ ! -f "$FRONTEND/.env" ]]; then
  echo "note: frontend/.env not found; set your own VITE_GOOGLE_MAPS_API_KEY there for maps and place search (see README: "API keys")" >&2
fi
if [[ ! -d "$FRONTEND/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd "$FRONTEND" && npm install)
fi

pids=()
cleanup() {
  trap - INT TERM EXIT
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# Prefix each line of output so the two logs are distinguishable.
prefix() { awk -v p="[$1]" '{ print p, $0; fflush() }'; }

# exec so the PID we track is the server itself, not a wrapper shell.
(cd "$BACKEND" && exec ./venv/bin/uvicorn app.main:app --reload --port 8000) \
  > >(prefix backend) 2>&1 &
pids+=($!)
# --strictPort: the backend's CORS only allows http://localhost:5173
(cd "$FRONTEND" && exec ./node_modules/.bin/vite --port 5173 --strictPort) \
  > >(prefix frontend) 2>&1 &
pids+=($!)

echo "Backend:  http://localhost:8000  (docs: /docs)"
echo "Frontend: http://localhost:5173"

# Exit as soon as either server dies (works on macOS's bash 3.2, which lacks wait -n).
while kill -0 "${pids[0]}" 2>/dev/null && kill -0 "${pids[1]}" 2>/dev/null; do
  sleep 1
done
