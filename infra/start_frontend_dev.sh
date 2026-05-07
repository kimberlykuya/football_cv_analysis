#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/frontend"

export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8001}"

if [ -z "${NEXT_ALLOWED_DEV_ORIGINS:-}" ]; then
  PUBLIC_IP="${PUBLIC_IP:-}"
  if [ -n "$PUBLIC_IP" ]; then
    export NEXT_ALLOWED_DEV_ORIGINS="$PUBLIC_IP,http://$PUBLIC_IP:3000"
  fi
fi

npm run dev -- -H 0.0.0.0
