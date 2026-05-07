#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    destination = Path("test_video.mp4")
    fps = 30
    width, height = 1280, 720
    writer = cv2.VideoWriter(
        str(destination),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    for frame_index in range(fps * 10):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (28, 70, 48)
        cv2.line(frame, (0, height // 2), (width, height // 2), (240, 240, 240), 2)
        cv2.circle(frame, (width // 2, height // 2), 90, (240, 240, 240), 2)
        cv2.putText(
            frame,
            f"FlowTrace smoke test frame {frame_index}",
            (70, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (255, 255, 255),
            3,
            cv2.LINE_AA,
        )
        for player_index in range(8):
            x = 120 + ((frame_index * 5 + player_index * 115) % 1040)
            y = 210 + (player_index % 4) * 85
            color = (30, 60, 230) if player_index < 4 else (40, 210, 90)
            cv2.rectangle(frame, (x, y), (x + 42, y + 96), color, -1)
        writer.write(frame)

    writer.release()
    print(f"created={destination.resolve()}")


if __name__ == "__main__":
    main()
