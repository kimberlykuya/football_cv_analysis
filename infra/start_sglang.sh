#!/usr/bin/env bash
set -euo pipefail

export INFERENCE_MODEL="deepseek-ai/DeepSeek-V4-Pro"
export API_KEY="flowtrace-key"
export SGLANG_DIMG="lmsysorg/sglang:v0.4.5.post3-rocm630"

docker run -d --rm \
  --ipc=host --privileged --shm-size 16g \
  --device=/dev/kfd --device=/dev/dri \
  --group-add video \
  --cap-add=SYS_PTRACE --cap-add=CAP_SYS_ADMIN \
  --security-opt seccomp=unconfined \
  -p 8000:3000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --name deepseek_server "$SGLANG_DIMG" \
  python3 -m sglang.launch_server \
  --model "$INFERENCE_MODEL" \
  --port 3000 \
  --trust-remote-code \
  --disable-radix-cache \
  --host 0.0.0.0 \
  --api-key "$API_KEY"
