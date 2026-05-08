from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2


DEFAULT_VLM_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"
DEFAULT_IMAGE_DIR = "./uploads/vlm_frames"


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def vlm_enabled() -> bool:
    return _env_bool("VLM_ENABLED", False)


def vlm_strict() -> bool:
    return not _env_bool("ALLOW_VLM_FALLBACK", True)


@dataclass(frozen=True)
class EventFrame:
    event: dict[str, Any]
    frame_id: int
    timestamp: float
    image_path: str


class LocalQwenVLM:
    def __init__(self) -> None:
        import torch
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

        model_name = os.getenv("VLM_MODEL", DEFAULT_VLM_MODEL)
        device = os.getenv("VLM_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
        dtype_name = os.getenv("VLM_DTYPE", "bfloat16")
        dtype = getattr(torch, dtype_name, torch.bfloat16)

        self.device = device
        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=dtype,
            device_map="auto" if device == "cuda" else None,
        )
        if device != "cuda":
            self.model.to(device)

    def describe(self, image_path: str, event: dict[str, Any]) -> dict[str, Any]:
        from qwen_vl_utils import process_vision_info

        prompt = f"""
You are analyzing one football match frame near a detected tactical event.
Return strict JSON only with these keys:
caption, visible_shape, pressure_cue, team_context, uncertainty, tags.

Detected event:
{json.dumps(event, default=str)}
"""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image_path},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        text = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.model.device)
        generated_ids = self.model.generate(
            **inputs,
            max_new_tokens=_env_int("VLM_MAX_NEW_TOKENS", 512),
        )
        generated_ids = [
            output_ids[len(input_ids) :]
            for input_ids, output_ids in zip(inputs.input_ids, generated_ids)
        ]
        raw = self.processor.batch_decode(
            generated_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        return _parse_vlm_json(raw)


@lru_cache(maxsize=1)
def get_local_vlm() -> LocalQwenVLM:
    return LocalQwenVLM()


class VisualEvidenceAgent:
    def generate(
        self,
        video_path: str,
        match_id: str,
        perception_output: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not vlm_enabled() or not events:
            return []

        try:
            event_frames = self._extract_event_frames(
                video_path=video_path,
                match_id=match_id,
                fps=float(perception_output.get("fps") or 30.0),
                events=events,
            )
            return [self._describe_event_frame(frame) for frame in event_frames]
        except Exception as error:
            if vlm_strict():
                raise
            print(f"[WARN VLM evidence disabled for this match] {error}", file=sys.stderr)
            return []

    def _extract_event_frames(
        self,
        video_path: str,
        match_id: str,
        fps: float,
        events: list[dict[str, Any]],
    ) -> list[EventFrame]:
        image_dir = Path(os.getenv("VLM_IMAGE_DIR", DEFAULT_IMAGE_DIR)) / match_id
        image_dir.mkdir(parents=True, exist_ok=True)

        selected = self._select_events(events)
        if not selected:
            return []

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Could not open video for VLM frame extraction: {video_path}")

        outputs: list[EventFrame] = []
        try:
            for event in selected:
                frame_id = int(event.get("frame_id") or round(float(event.get("timestamp", 0)) * fps))
                timestamp = float(event.get("timestamp", frame_id / fps))
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
                ok, frame = cap.read()
                if not ok:
                    if vlm_strict():
                        raise RuntimeError(f"Could not read event frame {frame_id}")
                    continue

                path = image_dir / f"frame_{frame_id}.jpg"
                cv2.imwrite(str(path), frame)
                outputs.append(
                    EventFrame(
                        event=event,
                        frame_id=frame_id,
                        timestamp=timestamp,
                        image_path=str(path),
                    )
                )
        finally:
            cap.release()

        return outputs

    def _select_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        max_events = _env_int("VLM_MAX_EVENT_FRAMES", 40)
        seen: set[int] = set()
        selected: list[dict[str, Any]] = []
        for event in events:
            frame_id = int(event.get("frame_id") or int(float(event.get("timestamp", 0)) * 30))
            if frame_id in seen:
                continue
            seen.add(frame_id)
            selected.append(event)
            if len(selected) >= max_events:
                break
        return selected

    def _describe_event_frame(self, frame: EventFrame) -> dict[str, Any]:
        if _env_bool("VLM_MOCK", False):
            payload = _mock_visual_payload(frame)
        else:
            payload = get_local_vlm().describe(frame.image_path, frame.event)

        return _normalize_visual_payload(payload, frame)


def _parse_vlm_json(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()
    return json.loads(cleaned)


def _normalize_visual_payload(payload: dict[str, Any], frame: EventFrame) -> dict[str, Any]:
    tags = payload.get("tags", [])
    if not isinstance(tags, list):
        tags = [str(tags)]
    uncertainty = payload.get("uncertainty", "medium")
    return {
        "type": "visual",
        "timestamp": frame.timestamp,
        "frame_id": frame.frame_id,
        "source_image_path": frame.image_path,
        "event_type": str(frame.event.get("type", "unknown")),
        "event_description": str(frame.event.get("description", "")),
        "caption": str(payload.get("caption", "")),
        "visible_shape": str(payload.get("visible_shape", "")),
        "pressure_cue": str(payload.get("pressure_cue", "")),
        "team_context": str(payload.get("team_context", "")),
        "uncertainty": str(uncertainty),
        "tags": [str(tag) for tag in tags],
        "confidence": float(frame.event.get("confidence", 60.0)),
    }


def _mock_visual_payload(frame: EventFrame) -> dict[str, Any]:
    event_type = frame.event.get("type", "event")
    return {
        "caption": f"Frame shows visual context around a {event_type} event.",
        "visible_shape": "Team structure is visible around the detected event area.",
        "pressure_cue": "Pressure cue inferred from nearby player density.",
        "team_context": str(frame.event.get("team", "unknown")),
        "uncertainty": "mock",
        "tags": [str(event_type), "visual-evidence"],
    }
