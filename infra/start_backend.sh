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

PORT="${BACKEND_PORT:-8001}"
HOST="${BACKEND_HOST:-0.0.0.0}"
LOG_DIR="${LOG_DIR:-logs}"
PID_FILE="$LOG_DIR/backend.pid"
LOG_FILE="$LOG_DIR/backend.log"

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
  old_pid="$(cat "$PID_FILE")"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" >/dev/null 2>&1; then
    echo "Backend already running with pid $old_pid"
    exit 0
  fi
fi

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

nohup python -m uvicorn backend.api.main:app --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
echo "$!" > "$PID_FILE"

echo "Backend started on $HOST:$PORT"
echo "pid=$(cat "$PID_FILE")"
echo "log=$LOG_FILE"
