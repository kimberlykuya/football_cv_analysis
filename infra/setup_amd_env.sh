#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
ROCM_TORCH_INDEX="${ROCM_TORCH_INDEX:-https://download.pytorch.org/whl/rocm7.0}"
INSTALL_NODE="${INSTALL_NODE:-true}"
INSTALL_ROCM_TORCH="${INSTALL_ROCM_TORCH:-true}"
VLM_IMAGE_DIR="${VLM_IMAGE_DIR:-./uploads/vlm_frames}"
VLM_PRELOAD="${VLM_PRELOAD:-false}"

echo "Normalizing shell script line endings..."
sed -i 's/\r$//' infra/*.sh

echo "Creating/using Python virtualenv..."
if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
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

if [ "$VLM_PRELOAD" = "true" ]; then
  echo "Preloading local VLM model. This can take several minutes and requires GPU memory..."
  VLM_ENABLED=true python - <<'PY'
from backend.agents.visual_evidence import get_local_vlm
vlm = get_local_vlm()
print(f"vlm_device={vlm.device}")
PY
else
  echo "Skipping local VLM preload. Set VLM_PRELOAD=true to verify model download/load during setup."
fi

echo "Checking required local assets..."
if [ ! -f "yolo26x.pt" ]; then
  echo "WARN: yolo26x.pt is missing."
  echo "Copy it from your workstation:"
  echo "  scp C:\\Users\\USER\\Documents\\football_analysis\\yolo26x.pt root@<gpu-ip>:$ROOT_DIR/yolo26x.pt"
fi

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
echo "  VLM_ENABLED=${VLM_ENABLED:-false}"
echo "  VLM_MODEL=${VLM_MODEL:-Qwen/Qwen2.5-VL-7B-Instruct}"
echo "  VLM_IMAGE_DIR=$VLM_IMAGE_DIR"
echo "  QWEN_VALIDATION_ENABLED=${QWEN_VALIDATION_ENABLED:-false}"
echo "  MATCH_RAG_DIR=./flowtrace_db/match_rag"
echo "  TEAM_MEMORY_DIR=./flowtrace_db/team_memory"
echo "Next:"
echo "  source .venv/bin/activate"
echo "  set -a && source .env.amd.example && set +a"
echo "  bash infra/amd_setup.sh"
echo "  python backend/test_backend.py"
echo "  python -m pytest -q backend/test_rag_evidence.py"
echo "  python backend/test_pipeline.py"
echo "  bash infra/start_backend.sh"
echo "  bash infra/start_frontend_prod.sh"
echo "  # In a second shell after the frontend is running:"
echo "  BACKEND_URL=http://127.0.0.1:8001 FRONTEND_URL=http://127.0.0.1:3000 bash infra/smoke_check.sh"
echo "  # Optional full local VLM load check:"
echo "  VLM_ENABLED=true BACKEND_URL=http://127.0.0.1:8001 FRONTEND_URL=http://127.0.0.1:3000 bash infra/smoke_check.sh"
