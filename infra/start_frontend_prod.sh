#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/frontend"

export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8001}"

npm run build
npm start -- -H 0.0.0.0 -p 3000
