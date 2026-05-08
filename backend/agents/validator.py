"""Feature-flagged Qwen validation for tactical events."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from backend.agents.llm import qwen_chat


def qwen_validation_enabled() -> bool:
    return os.getenv("QWEN_VALIDATION_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class QwenValidator:
    def validate_and_score_events(
        self,
        events: list[dict[str, Any]],
        frame_data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not qwen_validation_enabled() or not events:
            return [self._fallback_enhance(event, frame_data) for event in events]

        try:
            model_scores = self._model_validate(events, frame_data)
        except Exception as error:
            print(f"[WARN Qwen validation failed, using heuristic scores] {error}", file=sys.stderr)
            model_scores = {}

        return [
            self._merge_model_score(event, model_scores.get(str(index)), frame_data)
            for index, event in enumerate(events)
        ]

    def add_new_event_types(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        enhanced = list(events)
        for event in events:
            if event.get("type") == "pressing":
                enhanced.append(
                    {
                        "type": "pressing_intensity",
                        "team": event.get("team"),
                        "timestamp": event.get("timestamp"),
                        "description": "Pressing intensity detected from clustered pressure behavior",
                        "confidence": 62,
                        "model_source": "heuristic",
                    }
                )

        for previous, current in zip(events, events[1:]):
            time_delta = float(current.get("timestamp", 0)) - float(previous.get("timestamp", 0))
            if 2 <= time_delta <= 5 and previous.get("type") != current.get("type"):
                enhanced.append(
                    {
                        "type": "transition",
                        "team": current.get("team", previous.get("team")),
                        "timestamp": previous.get("timestamp"),
                        "description": f"Transition from {previous.get('type')} to {current.get('type')}",
                        "confidence": 70,
                        "model_source": "heuristic",
                    }
                )

        return enhanced

    def _model_validate(
        self,
        events: list[dict[str, Any]],
        frame_data: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        compact_events = [
            {
                "index": index,
                "type": event.get("type"),
                "team": event.get("team"),
                "timestamp": event.get("timestamp"),
                "zone": event.get("zone"),
                "description": event.get("description"),
            }
            for index, event in enumerate(events[:50])
        ]
        frame_sample = [
            {
                "timestamp": frame.get("timestamp"),
                "player_count": len(frame.get("players", [])),
            }
            for frame in frame_data[:: max(1, len(frame_data) // 20 or 1)]
        ]
        prompt = f"""
Validate these football tactical events against the frame sample.
Return strict JSON only:
{{
  "events": [
    {{"index": 0, "confidence": 0-100, "valid": true, "explanation": "short reason"}}
  ]
}}

EVENTS:
{json.dumps(compact_events)}

FRAME_SAMPLE:
{json.dumps(frame_sample)}
"""
        raw = qwen_chat([{"role": "user", "content": prompt}], temperature=0.0)
        if not raw:
            return {}

        data = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        return {str(item["index"]): item for item in data.get("events", []) if "index" in item}

    def _merge_model_score(
        self,
        event: dict[str, Any],
        model_score: dict[str, Any] | None,
        frame_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        fallback = self._fallback_enhance(event, frame_data)
        if not model_score:
            return fallback

        confidence = float(model_score.get("confidence", fallback["confidence"]))
        return {
            **fallback,
            "confidence": max(0.0, min(100.0, confidence)),
            "model_source": "qwen",
            "validation": {
                "valid": bool(model_score.get("valid", True)),
                "explanation": str(model_score.get("explanation", fallback["explanation"])),
            },
            "explanation": str(model_score.get("explanation", fallback["explanation"])),
        }

    def _fallback_enhance(
        self,
        event: dict[str, Any],
        frame_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        timestamp = float(event.get("timestamp", 0))
        context_frames = [
            frame for frame in frame_data if abs(float(frame.get("timestamp", 0)) - timestamp) <= 5
        ]
        confidence = self._fallback_confidence(event, len(context_frames))
        description = str(event.get("description", "Tactical event detected"))
        return {
            **event,
            "confidence": confidence,
            "model_source": "heuristic",
            "explanation": f"{description} ({confidence:.0f}% confidence)",
        }

    def _fallback_confidence(self, event: dict[str, Any], context_count: int) -> float:
        base_scores = {
            "overload": 78.0,
            "high_line": 65.0,
            "counter_attack": 72.0,
            "pressing": 58.0,
            "possession_zone": 68.0,
            "pressing_intensity": 55.0,
            "transition": 70.0,
        }
        base = base_scores.get(str(event.get("type", "unknown")), 60.0)
        if context_count > 3:
            base += 8.0
        if event.get("zone"):
            base += 4.0
        return max(0.0, min(100.0, base))
