#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LOCAL_ENV_FILE=".env.amd.local"

PYTHON_BIN="${PYTHON_BIN:-}"
ROCM_TORCH_INDEX="${ROCM_TORCH_INDEX:-https://download.pytorch.org/whl/rocm7.0}"
INSTALL_NODE="${INSTALL_NODE:-true}"
INSTALL_ROCM_TORCH="${INSTALL_ROCM_TORCH:-true}"
VLM_IMAGE_DIR="${VLM_IMAGE_DIR:-./uploads/vlm_frames}"
VLM_MODEL="${VLM_MODEL:-Qwen/Qwen3-VL-8B-Instruct}"
YOLO_MODEL_PATH="${YOLO_MODEL_PATH:-yolo26x.pt}"
EMBED_MODEL="${EMBED_MODEL:-sentence-transformers/all-MiniLM-L6-v2}"
HF_HOME="${HF_HOME:-$ROOT_DIR/.hf_cache}"

echo "Normalizing shell script line endings..."
sed -i 's/\r$//' infra/*.sh

if [ -f ".env.amd.example" ] && [ ! -f "$LOCAL_ENV_FILE" ]; then
  cp .env.amd.example "$LOCAL_ENV_FILE"
fi

if [ -f "$LOCAL_ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a && source "$LOCAL_ENV_FILE" && set +a
fi

prompt_if_empty() {
  local var_name="$1"
  local prompt="$2"
  local current_value="${!var_name:-}"
  if [ -z "$current_value" ] && [ -t 0 ]; then
    read -r -p "$prompt" current_value
    export "$var_name=$current_value"
  fi
}

write_env_value() {
  local key="$1"
  local value="${!key:-}"
  local escaped
  escaped="$(printf '%s' "$value" | sed 's/[\/&]/\\&/g')"
  if grep -q "^${key}=" "$LOCAL_ENV_FILE"; then
    sed -i "s/^${key}=.*/${key}=\"${escaped}\"/" "$LOCAL_ENV_FILE"
  else
    printf '%s="%s"\n' "$key" "$value" >> "$LOCAL_ENV_FILE"
  fi
}

echo "Configuring persistent AMD environment in $LOCAL_ENV_FILE ..."
prompt_if_empty "FEATHERLESS_API_KEY" "Featherless API key (press Enter to leave blank for setup only): "
prompt_if_empty "HF_TOKEN" "Hugging Face token (press Enter if public download works without it): "
prompt_if_empty "PUBLIC_IP" "Public GPU IP or hostname for frontend access (press Enter to skip): "

if [ -n "${PUBLIC_IP:-}" ]; then
  NEXT_ALLOWED_DEV_ORIGINS="${NEXT_ALLOWED_DEV_ORIGINS:-$PUBLIC_IP,http://$PUBLIC_IP:3000}"
  export NEXT_ALLOWED_DEV_ORIGINS
fi

VLM_ENABLED="${VLM_ENABLED:-true}"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8001}"
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
export VLM_ENABLED BACKEND_URL BACKEND_HOST BACKEND_PORT

for key in FEATHERLESS_API_KEY HF_TOKEN PUBLIC_IP NEXT_ALLOWED_DEV_ORIGINS VLM_ENABLED VLM_MODEL VLM_DEVICE VLM_DTYPE VLM_IMAGE_DIR YOLO_MODEL_PATH EMBED_MODEL HF_HOME BACKEND_URL BACKEND_HOST BACKEND_PORT; do
  write_env_value "$key"
done

if [ -z "$PYTHON_BIN" ]; then
  for candidate in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi

if [ -z "$PYTHON_BIN" ]; then
  echo "ERROR: No Python interpreter found. Install Python 3.10+ or rerun with PYTHON_BIN=/path/to/python."
  exit 1
fi

echo "Using Python interpreter: $PYTHON_BIN"
"$PYTHON_BIN" --version

echo "Creating/using Python virtualenv..."
if [ ! -d ".venv" ]; then
  if ! "$PYTHON_BIN" -m venv .venv; then
    echo "Python venv creation failed. Attempting to install the matching venv package..."
    PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    if command -v apt-get >/dev/null 2>&1; then
      apt-get update
      apt-get install -y "python${PY_VERSION}-venv" python3-venv
      "$PYTHON_BIN" -m venv .venv
    else
      echo "ERROR: Could not create .venv and apt-get is not available."
      echo "Install the Python venv package for $PYTHON_BIN, then rerun setup."
      exit 1
    fi
  fi
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing backend dependencies..."
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

if [ "$INSTALL_ROCM_TORCH" = "true" ]; then
  echo "Installing ROCm PyTorch from $ROCM_TORCH_INDEX ..."
  python -m pip uninstall -y torch torchvision torchaudio || true
  python -m pip install --index-url "$ROCM_TORCH_INDEX" torch torchvision torchaudio
fi

echo "Checking ROCm visibility..."
if command -v rocm-smi >/dev/null 2>&1; then
  rocm-smi --showproductname
else
  echo "WARN: rocm-smi not found on PATH"
fi

echo "Checking PyTorch GPU runtime..."
python infra/check_gpu_runtime.py

echo "Preparing runtime directories..."
mkdir -p uploads "$VLM_IMAGE_DIR" flowtrace_db/team_memory flowtrace_db/match_rag

echo "Checking VLM/RAG dependency imports..."
python - <<'PY'
import importlib

required = [
    "chromadb",
    "sentence_transformers",
    "transformers",
    "accelerate",
    "huggingface_hub",
    "qwen_vl_utils",
    "PIL",
]

missing = []
for module in required:
    try:
        importlib.import_module(module)
    except Exception as error:
        missing.append(f"{module}: {error}")

if missing:
    raise SystemExit("Missing VLM/RAG dependencies:\n" + "\n".join(missing))

print("VLM/RAG imports OK")
PY

echo "Downloading local VLM model from Hugging Face: $VLM_MODEL"
export HF_HOME
hf download "$VLM_MODEL" --type model --cache-dir "$HF_HOME"

echo "Downloading embedding model from Hugging Face: $EMBED_MODEL"
hf download "$EMBED_MODEL" --type model --cache-dir "$HF_HOME"

echo "Downloading YOLO detector model: $YOLO_MODEL_PATH"
YOLO_MODEL_PATH="$YOLO_MODEL_PATH" python - <<'PY'
import os
from pathlib import Path

from ultralytics import YOLO

model_path = os.environ["YOLO_MODEL_PATH"]
try:
    model = YOLO(model_path)
except Exception as error:
    if model_path == "yolo26x.pt" and not Path(model_path).exists():
        raise SystemExit(
            "Could not load yolo26x.pt. Keep YOLO_MODEL_PATH=yolo26x.pt and place "
            "the YOLOv26-X weights at the repo root before rerunning setup."
        ) from error
    raise
print(f"yolo_model_ready={model_path}")
PY

echo "Checking local VLM model load..."
VLM_ENABLED=true VLM_MODEL="$VLM_MODEL" python - <<'PY'
from backend.agents.visual_evidence import get_local_vlm
vlm = get_local_vlm()
print(f"vlm_device={vlm.device}")
PY

if [ ! -f "test_video.mp4" ]; then
  echo "WARN: test_video.mp4 is missing."
  echo "Create a synthetic smoke test clip with:"
  echo "  python infra/create_test_video.py"
  echo "For final demo quality, copy a real football clip to $ROOT_DIR/test_video.mp4."
fi

if [ "$INSTALL_NODE" = "true" ]; then
  if ! command -v node >/dev/null 2>&1 || ! node -e "process.exit(Number(process.versions.node.split('.')[0]) >= 20 ? 0 : 1)"; then
    echo "Installing Node 20.x..."
    if command -v curl >/dev/null 2>&1 && command -v apt-get >/dev/null 2>&1; then
      curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
      apt-get install -y nodejs
    else
      echo "WARN: cannot install Node automatically; install Node >=20.9.0 manually."
    fi
  fi

  echo "Installing frontend dependencies..."
  (cd frontend && npm install)
fi

echo "AMD setup complete."
echo "Configured runtime defaults:"
echo "  VLM_ENABLED=true"
echo "  VLM_MODEL=$VLM_MODEL"
echo "  VLM_IMAGE_DIR=$VLM_IMAGE_DIR"
echo "  YOLO_MODEL_PATH=$YOLO_MODEL_PATH"
echo "  EMBED_MODEL=$EMBED_MODEL"
echo "  HF_HOME=$HF_HOME"
echo "  QWEN_VALIDATION_ENABLED=${QWEN_VALIDATION_ENABLED:-false}"
echo "  MATCH_RAG_DIR=./flowtrace_db/match_rag"
echo "  TEAM_MEMORY_DIR=./flowtrace_db/team_memory"
echo "Next:"
echo "  source .venv/bin/activate"
echo "  bash infra/amd_setup.sh"
echo "  python backend/test_backend.py"
echo "  python -m pytest -q backend/test_rag_evidence.py"
echo "  python backend/test_pipeline.py"
echo "  bash infra/start_backend.sh"
echo "  bash infra/start_frontend_prod.sh"
echo "  # In a second shell after the frontend is running:"
echo "  VLM_ENABLED=true BACKEND_URL=http://127.0.0.1:8001 FRONTEND_URL=http://127.0.0.1:3000 bash infra/smoke_check.sh"

