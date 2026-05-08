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

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8001}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:3000}"

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "Checking Python imports..."
python - <<'PY'
import os

from backend.api.main import app
from backend.graph.flowtrace_graph import run_pipeline_streaming
from backend.agents.validator import qwen_validation_enabled
from backend.agents.visual_evidence import vlm_enabled
print(f"fastapi_app={app.title}")
print(f"streaming_callable={callable(run_pipeline_streaming)}")
print(f"qwen_validation_enabled={qwen_validation_enabled()}")
print(f"vlm_enabled={vlm_enabled()}")

if os.getenv("ALLOW_MOCK_LLM", "false").strip().lower() in {"0", "false", "no", "off"}:
    if not os.getenv("FEATHERLESS_API_KEY"):
        raise SystemExit("FEATHERLESS_API_KEY is required when ALLOW_MOCK_LLM=false")
print(f"deepseek_model={os.getenv('DEEPSEEK_MODEL', '')}")
PY

if [ "${VLM_ENABLED:-false}" = "true" ]; then
  echo "Checking local VLM imports/model load..."
  python - <<'PY'
from backend.agents.visual_evidence import get_local_vlm
vlm = get_local_vlm()
print(f"vlm_device={vlm.device}")
PY
fi

echo "Checking GPU runtime..."
python infra/check_gpu_runtime.py

echo "Checking DeepSeek/Featherless API..."
python - <<'PY'
from backend.agents.llm import deepseek_health_check

reply = deepseek_health_check()
if "OK" not in reply.upper():
    raise SystemExit(f"Unexpected DeepSeek smoke response: {reply!r}")
print("deepseek_api=ok")
PY

echo "Building frontend..."
(cd frontend && npm run build)

echo "Checking backend health at $BACKEND_URL ..."
curl -fsS "$BACKEND_URL/health" >/dev/null
curl -fsS "$BACKEND_URL/api/gpu/status" >/dev/null
curl -fsS "$BACKEND_URL/api/analyses" >/dev/null

echo "Checking frontend at $FRONTEND_URL ..."
curl -fsS "$FRONTEND_URL" >/dev/null

echo "Smoke checks passed."
