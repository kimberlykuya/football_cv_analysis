#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f ".env.amd.local" ]; then
  # shellcheck disable=SC1091
  set -a && source .env.amd.local && set +a
elif [ -f ".env.amd.example" ]; then
  # shellcheck disable=SC1091
  set -a && source .env.amd.example && set +a
fi

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:$BACKEND_PORT}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:$FRONTEND_PORT}"
LOG_DIR="${LOG_DIR:-logs}"
mkdir -p "$LOG_DIR"

stop_pid_file() {
  local pid_file="$1"
  local name="$2"
  if [ -f "$pid_file" ]; then
    local pid
    pid="$(cat "$pid_file")"
    if [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1; then
      echo "Stopping existing $name pid=$pid ..."
      kill "$pid" >/dev/null 2>&1 || true
      for _ in 1 2 3 4 5; do
        if ! kill -0 "$pid" >/dev/null 2>&1; then
          break
        fi
        sleep 1
      done
    fi
  fi
}

if [ "${YOLO_MODEL_PATH:-}" = "yolo11x.pt" ]; then
  echo "ERROR: .env.amd.local still points at yolo11x.pt."
  echo "Set YOLO_MODEL_PATH=yolo26x.pt, then rerun setup or this launcher."
  exit 1
fi

if [ "${ALLOW_MOCK_LLM:-false}" = "false" ] && [ -z "${FEATHERLESS_API_KEY:-}" ]; then
  echo "ERROR: FEATHERLESS_API_KEY is required for final demo mode."
  echo "Set it in .env.amd.local or rerun bash infra/setup_amd_env.sh."
  exit 1
fi

stop_pid_file "$LOG_DIR/backend.pid" "backend"
stop_pid_file "$LOG_DIR/frontend.pid" "frontend"

echo "Starting backend on $BACKEND_HOST:$BACKEND_PORT ..."
nohup python -m uvicorn backend.api.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
  > "$LOG_DIR/backend.log" 2>&1 &
echo "$!" > "$LOG_DIR/backend.pid"

echo "Building frontend ..."
(cd frontend && BACKEND_URL="$BACKEND_URL" npm run build)

echo "Starting frontend on $FRONTEND_HOST:$FRONTEND_PORT ..."
nohup bash -lc "cd '$ROOT_DIR/frontend' && BACKEND_URL='$BACKEND_URL' npm start -- -H '$FRONTEND_HOST' -p '$FRONTEND_PORT'" \
  > "$LOG_DIR/frontend.log" 2>&1 &
echo "$!" > "$LOG_DIR/frontend.pid"

echo "Waiting for services ..."
for _ in $(seq 1 60); do
  if curl -fsS "$BACKEND_URL/health" >/dev/null 2>&1 && curl -fsS "$FRONTEND_URL" >/dev/null 2>&1; then
    echo "Demo ready."
    echo "Frontend: $FRONTEND_URL"
    echo "Backend:  $BACKEND_URL"
    echo "Logs:"
    echo "  tail -f $LOG_DIR/backend.log"
    echo "  tail -f $LOG_DIR/frontend.log"
    exit 0
  fi
  sleep 1
done

echo "ERROR: services did not become ready within 60 seconds."
echo "Backend log tail:"
tail -n 40 "$LOG_DIR/backend.log" || true
echo "Frontend log tail:"
tail -n 40 "$LOG_DIR/frontend.log" || true
exit 1
