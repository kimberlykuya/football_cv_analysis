from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2


class VideoWriter:
    def write(
        self,
        source_video_path: str,
        frame_data: list[dict[str, Any]],
        output_dir: str,
        output_name: str,
    ) -> str:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        destination = output_path / output_name

        cap = cv2.VideoCapture(source_video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Could not open video: {source_video_path}")

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        writer = cv2.VideoWriter(
            str(destination),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )

        frame_lookup = {frame["frame_id"]: frame for frame in frame_data}
        frame_index = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            payload = frame_lookup.get(frame_index)
            if payload is not None:
                self._draw_frame_overlay(frame, payload)

            writer.write(frame)
            frame_index += 1

        cap.release()
        writer.release()
        return str(destination)

    def _draw_frame_overlay(self, frame, payload: dict[str, Any]) -> None:
        for player in payload.get("players", []):
            bbox = player.get("bbox")
            if not bbox:
                continue

            x1, y1, x2, y2 = [int(v) for v in bbox]
            team = player.get("team") or "unknown"
            label = f"#{player.get('id', '?')} {team}"
            if player.get("pitch_x") is not None and player.get("pitch_y") is not None:
                label += f" ({player['pitch_x']:.1f}m,{player['pitch_y']:.1f}m)"

            color = self._team_color(team)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                frame,
                label,
                (x1, max(0, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1,
                cv2.LINE_AA,
            )

        cv2.putText(
            frame,
            f"t={payload.get('timestamp', 0):.3f}s",
            (12, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    def _team_color(self, team: str) -> tuple[int, int, int]:
        palette = {
            "team_a": (255, 128, 0),
            "team_b": (0, 200, 255),
            "referee": (180, 180, 180),
            "unknown": (0, 255, 0),
        }
        return palette.get(team, palette["unknown"])

