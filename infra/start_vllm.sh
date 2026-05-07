#!/usr/bin/env bash
set -euo pipefail

export SAFETENSORS_FAST_GPU=1
export VLLM_ROCM_USE_AITER=1
export AITER_ENABLE_VSKIP=0
export VLLM_USE_V1=1

vllm serve deepseek-ai/DeepSeek-V4-Pro \
  --tensor-parallel-size 1 \
  --max-model-len 32768 \
  --block-size 1 \
  --max-seq-len-to-capture 32768 \
  --no-enable-prefix-caching \
  --max-num-batched-tokens 32768 \
  --gpu-memory-utilization 0.90 \
  --trust-remote-code \
  --host 0.0.0.0 \
  --port 8000

