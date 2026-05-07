#!/usr/bin/env python3
from __future__ import annotations

import os
import sys


def _strict_cpu_disabled() -> bool:
    return os.getenv("ALLOW_CPU_FALLBACK", "true").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }


def main() -> int:
    try:
        import torch
    except Exception as error:
        print(f"torch_import_error={error}", file=sys.stderr)
        return 1

    cuda_available = torch.cuda.is_available()
    print(f"torch_version={torch.__version__}")
    print(f"torch_hip={torch.version.hip}")
    print(f"cuda_available={cuda_available}")
    print(f"device_count={torch.cuda.device_count()}")

    for index in range(torch.cuda.device_count()):
        try:
            props = torch.cuda.get_device_properties(index)
            print(
                f"device_{index}={props.name}; "
                f"memory_gb={props.total_memory / (1024 ** 3):.1f}"
            )
        except Exception as error:
            print(f"device_{index}_error={error}")

    if _strict_cpu_disabled() and not cuda_available:
        print(
            "ROCm PyTorch is not active: torch.cuda.is_available() is false "
            "and ALLOW_CPU_FALLBACK=false",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
