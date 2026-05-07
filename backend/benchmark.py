from __future__ import annotations

import argparse
import time
from pathlib import Path

import torch
from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark YOLOv26 throughput on AMD MI300X")
    parser.add_argument("--model", default="yolo26x.pt", help="Ultralytics model path")
    parser.add_argument("--iterations", type=int, default=100, help="Timing iterations per batch size")
    parser.add_argument("--warmup", type=int, default=10, help="Warmup iterations per batch size")
    parser.add_argument(
        "--batch-sizes",
        default="1,4,8,16",
        help="Comma-separated batch sizes to test",
    )
    return parser.parse_args()


def run_benchmark(model_path: str, batch_sizes: list[int], iterations: int, warmup: int) -> None:
    import numpy as np
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    path = Path(model_path)
    if not path.is_absolute():
        repo_root = Path(__file__).resolve().parents[1]
        path = (repo_root / path).resolve()
    model = YOLO(str(path)).to(device)

    for batch_size in batch_sizes:
        # Create batch of numpy arrays (YOLO expects numpy, not torch tensors)
        frames = [np.zeros((640, 640, 3), dtype=np.uint8) for _ in range(batch_size)]

        # Warmup
        for _ in range(warmup):
            with torch.no_grad():
                _ = model(frames, device=device, verbose=False, conf=0.3)

        if device.type == "cuda":
            torch.cuda.synchronize()

        # Timed run
        start = time.perf_counter()
        for _ in range(iterations):
            with torch.no_grad():
                _ = model(frames, device=device, verbose=False, conf=0.3)

        if device.type == "cuda":
            torch.cuda.synchronize()

        elapsed = time.perf_counter() - start
        fps = (iterations * batch_size) / elapsed
        device_name = torch.cuda.get_device_name(0) if device.type == "cuda" else "CPU"
        print(f"Batch {batch_size:2d}: {fps:.1f} frames/sec on {device_name}")


def main() -> None:
    args = parse_args()
    batch_sizes = [int(value.strip()) for value in args.batch_sizes.split(",") if value.strip()]
    run_benchmark(args.model, batch_sizes, args.iterations, args.warmup)


if __name__ == "__main__":
    main()

