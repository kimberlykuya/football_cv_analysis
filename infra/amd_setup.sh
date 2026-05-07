#!/usr/bin/env bash
set -euo pipefail

echo "Checking ROCm GPU visibility..."
rocm-smi --showproductname

echo "Checking PyTorch ROCm availability..."
python infra/check_gpu_runtime.py

