from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from backend.pipeline.perspective import PitchTransformer
from backend.pipeline.team_classifier import TeamClassifier
from backend.pipeline.video_writer import VideoWriter

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DEFAULT_MODEL_PATH = "yolo26x.pt"
DEFAULT_TRACKER = "bytetrack.yaml"
DEFAULT_BATCH_SIZE = 16


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer, got {value!r}") from error


class PerceiverAgent:
    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        if DEVICE.type != "cuda" and not _env_bool("ALLOW_CPU_FALLBACK", True):
            raise RuntimeError(
                "ROCm PyTorch is not active: torch.cuda.is_available() is false "
                "and ALLOW_CPU_FALLBACK=false"
            )

        selected_model_path = os.getenv("YOLO_MODEL_PATH", model_path)
        resolved_model_path = self._resolve_model_path(selected_model_path)
        self.model = YOLO(str(resolved_model_path))
        self.model.to(DEVICE)
        self.batch_size = _env_int(
            "YOLO_BATCH_SIZE",
            64 if DEVICE.type == "cuda" else batch_size,
        )
        self.imgsz = _env_int("YOLO_IMGSZ", 640)
        self.half = _env_bool("YOLO_HALF", DEVICE.type == "cuda")
        self.team_classifier = TeamClassifier()
        self.pitch_transformer = PitchTransformer()
        self.video_writer = VideoWriter()

    def _resolve_model_path(self, model_path: str) -> Path:
        path = Path(model_path)
        if path.is_absolute():
            return path
        repo_root = Path(__file__).resolve().parents[2]
        return (repo_root / path).resolve()

    def process_video(
        self,
        video_path: str,
        match_id: str,
        output_dir: str | None = None,
    ) -> dict[str, Any]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Could not open video: {video_path}")

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

        frame_data: list[dict[str, Any]] = []
        raw_frames: list[np.ndarray] = []
        batch_frames: list[np.ndarray] = []
        frame_indices: list[int] = []
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            raw_frames.append(frame.copy())
            batch_frames.append(frame)
            frame_indices.append(frame_count)
            frame_count += 1

            if len(batch_frames) == self.batch_size:
                self._process_batch(batch_frames, frame_indices, fps, frame_data)
                batch_frames = []
                frame_indices = []

        if batch_frames:
            self._process_batch(batch_frames, frame_indices, fps, frame_data)

        cap.release()

        frame_data = self.team_classifier.assign_teams(frame_data, raw_frames)
        frame_data = self.pitch_transformer.transform(
            frame_data,
            frame_size=(frame_width, frame_height),
        )

        annotated_video_path = None
        if output_dir:
            annotated_video_path = self.video_writer.write(
                source_video_path=video_path,
                frame_data=frame_data,
                output_dir=output_dir,
                output_name=f"{match_id}_annotated.mp4",
            )

        return {
            "match_id": match_id,
            "fps": fps,
            "total_frames": frame_count,
            "frame_size": {"width": frame_width, "height": frame_height},
            "frame_data": frame_data,
            "annotated_video_path": annotated_video_path,
        }

    def _process_batch(
        self,
        frames: list[np.ndarray],
        indices: list[int],
        fps: float,
        frame_data: list[dict[str, Any]],
    ) -> None:
        with torch.no_grad():
            results = self.model.track(
                frames,
                persist=True,
                tracker=DEFAULT_TRACKER,
                classes=[0],
                conf=0.3,
                device=DEVICE,
                imgsz=self.imgsz,
                half=self.half and DEVICE.type == "cuda",
                verbose=False,
            )

        for result, frame_idx in zip(results, indices):
            timestamp = frame_idx / fps
            players: list[dict[str, Any]] = []

            if result.boxes is not None and result.boxes.id is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                track_ids = result.boxes.id.int().cpu().numpy()
                confidences = result.boxes.conf.cpu().numpy()

                for box, track_id, conf in zip(boxes, track_ids, confidences):
                    x1, y1, x2, y2 = [float(v) for v in box]
                    players.append(
                        {
                            "id": int(track_id),
                            "team": None,
                            "pixel_x": float((x1 + x2) / 2),
                            "pixel_y": float(y2),
                            "pitch_x": None,
                            "pitch_y": None,
                            "bbox": [x1, y1, x2, y2],
                            "confidence": float(conf),
                        }
                    )

            description = self._generate_frame_description(
                frame_idx, timestamp, players
            )
            frame_data.append(
                {
                    "frame_id": frame_idx,
                    "timestamp": round(timestamp, 3),
                    "players": players,
                    "description": description,
                }
            )

    def _generate_frame_description(
        self,
        frame_idx: int,
        timestamp: float,
        players: list[dict[str, Any]],
    ) -> str:
        """Generate a natural-language description of the frame's player positions.

        Used by MatchRAG for semantic retrieval during Coach Q&A.
        """
        if not players:
            return f"[{timestamp:.1f}s] Frame {frame_idx}: no players detected."

        team_a = [p for p in players if p.get("team") == "team_a"]
        team_b = [p for p in players if p.get("team") == "team_b"]
        refs = [p for p in players if p.get("team") == "referee"]
        unassigned = [p for p in players if p.get("team") is None]

        parts: list[str] = [f"[{timestamp:.1f}s] Frame {frame_idx}:"]

        if team_a:
            parts.append(
                f"Team A has {len(team_a)} players"
                f" (IDs: {', '.join(str(p['id']) for p in team_a[:6])}"
                f"{'...' if len(team_a) > 6 else ''})"
            )
        if team_b:
            parts.append(
                f"Team B has {len(team_b)} players"
                f" (IDs: {', '.join(str(p['id']) for p in team_b[:6])}"
                f"{'...' if len(team_b) > 6 else ''})"
            )
        if refs:
            parts.append(f"{len(refs)} referee(s) present")
        if unassigned:
            parts.append(f"{len(unassigned)} unassigned player(s)")

        return ". ".join(parts) + "."


