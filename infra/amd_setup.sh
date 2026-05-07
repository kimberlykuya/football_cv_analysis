#!/usr/bin/env bash
set -euo pipefail

echo "Checking ROCm GPU visibility..."
rocm-smi --showproductname

echo "Checking PyTorch ROCm availability..."
python3 - <<'PY'
import torch
print("cuda_available=", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device_name=", torch.cuda.get_device_name(0))
PY

