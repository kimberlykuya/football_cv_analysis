from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.cluster import KMeans

from backend.agents.llm import deepseek_chat, deepseek_chat_stream
from backend.agents.validator import QwenValidator


class AnalystAgent:
    def __init__(self):
        """Initialize with validator."""
        self.validator = QwenValidator()

    def analyze(self, perception_output: dict[str, Any], generate_summary: bool = True) -> dict[str, Any]:
        frame_data = perception_output["frame_data"]

        formations = self._detect_formations(frame_data)
        pressure_zones = self._compute_pressure_zones(frame_data)
        tactical_events = self._detect_events(frame_data)
        tactical_events = self.validator.validate_and_score_events(tactical_events, frame_data)
        tactical_events = self.validator.add_new_event_types(tactical_events)

        metrics = self._compute_metrics(frame_data)

        tactical_summary = ""
        if generate_summary:
            tactical_summary = self._generate_tactical_analysis(
                formations,
                pressure_zones,
                tactical_events,
                metrics,
            )

        return {
            "formations": formations,
            "pressure_zones": pressure_zones,
            "tactical_events": tactical_events,
            "metrics": metrics,
            "summary": tactical_summary,
        }

    def _detect_formations(self, frame_data: list[dict[str, Any]]) -> dict[str, list[list[int]]]:
        formations: dict[str, list[list[int]]] = {"team_a": [], "team_b": []}

        for frame in frame_data[::30]:
            for team in ("team_a", "team_b"):
                players = [
                    player
                    for player in frame["players"]
                    if player.get("team") == team and player.get("pitch_y") is not None
                ]
                if len(players) < 4:
                    continue

                y_positions = sorted(float(player["pitch_y"]) for player in players)
                formations[team].append(self._cluster_into_lines(y_positions))

        return formations

    def _cluster_into_lines(self, positions: list[float]) -> list[int]:
        if not positions:
            return []
        if len(positions) == 1:
            return [1]

        cluster_count = min(4, len(positions))
        model = KMeans(n_clusters=cluster_count, n_init=5, random_state=42)
        labels = model.fit_predict(np.array(positions).reshape(-1, 1))
        line_counts = [int(np.sum(labels == index)) for index in range(cluster_count)]
        return sorted(line_counts, reverse=True)

    def _compute_pressure_zones(self, frame_data: list[dict[str, Any]]) -> dict[str, list[list[float]]]:
        zones = {
            "team_a": np.zeros((3, 2), dtype=float),
            "team_b": np.zeros((3, 2), dtype=float),
        }

        for frame in frame_data:
            for player in frame["players"]:
                team = player.get("team")
                pitch_x = player.get("pitch_x")
                pitch_y = player.get("pitch_y")
                if team not in zones or pitch_x is None or pitch_y is None:
                    continue

                col = min(int(float(pitch_x) / 35), 2)
                row = min(int(float(pitch_y) / 34), 1)
                zones[team][col][row] += 1

        for team, grid in zones.items():
            total = grid.sum()
            if total > 0:
                zones[team] = (grid / total * 100).round(1)

        return {team: grid.tolist() for team, grid in zones.items()}

    def _detect_events(self, frame_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []

        for frame in frame_data:
            team_a = [
                player
                for player in frame["players"]
                if player.get("team") == "team_a" and player.get("pitch_x") is not None
            ]
            team_b = [
                player
                for player in frame["players"]
                if player.get("team") == "team_b" and player.get("pitch_x") is not None
            ]

            for zone_x in (25, 55, 80):
                a_in_zone = [player for player in team_a if abs(float(player["pitch_x"]) - zone_x) < 15]
                b_in_zone = [player for player in team_b if abs(float(player["pitch_x"]) - zone_x) < 15]
                if len(a_in_zone) >= 3 and len(b_in_zone) <= 1:
                    events.append(
                        {
                            "type": "overload",
                            "team": "team_a",
                            "frame_id": frame["frame_id"],
                            "timestamp": frame["timestamp"],
                            "zone": f"zone_{zone_x}m",
                            "description": f"Team A 3v1 overload in zone around {zone_x}m at {frame['timestamp']}s",
                        }
                    )

            if team_b:
                avg_b_x = float(np.mean([float(player["pitch_x"]) for player in team_b]))
                if avg_b_x > 63:
                    events.append(
                        {
                            "type": "high_line",
                            "team": "team_b",
                            "frame_id": frame["frame_id"],
                            "timestamp": frame["timestamp"],
                            "zone": "defensive_third",
                            "description": f"Team B high defensive line at {frame['timestamp']}s — avg position {avg_b_x:.1f}m",
                        }
                    )

        deduped: list[dict[str, Any]] = []
        last_type = None
        last_timestamp = None
        for event in events:
            if event["type"] != last_type or event["timestamp"] != last_timestamp:
                deduped.append(event)
                last_type = event["type"]
                last_timestamp = event["timestamp"]

        return deduped

    def _compute_metrics(self, frame_data: list[dict[str, Any]]) -> dict[str, float]:
        all_a = [
            player
            for frame in frame_data
            for player in frame["players"]
            if player.get("team") == "team_a" and player.get("pitch_x") is not None
        ]
        all_b = [
            player
            for frame in frame_data
            for player in frame["players"]
            if player.get("team") == "team_b" and player.get("pitch_x") is not None
        ]

        def _values(players: list[dict[str, Any]]) -> list[float]:
            return [float(player["pitch_x"]) for player in players]

        return {
            "team_a_avg_defensive_line": round(float(np.mean(_values(all_a))), 1) if all_a else 0.0,
            "team_b_avg_defensive_line": round(float(np.mean(_values(all_b))), 1) if all_b else 0.0,
            "team_a_compactness": round(float(np.std(_values(all_a))), 1) if all_a else 0.0,
            "team_b_compactness": round(float(np.std(_values(all_b))), 1) if all_b else 0.0,
        }

    def _build_tactical_prompt(
        self,
        formations: dict[str, list[list[int]]],
        pressure_zones: dict[str, list[list[float]]],
        events: list[dict[str, Any]],
        metrics: dict[str, float],
    ) -> str:
        event_descriptions = "\n".join(event["description"] for event in events[:20]) or "No major events detected."
        return f"""
You are an elite football tactical analyst.

METRICS:
- Team A avg defensive line height: {metrics['team_a_avg_defensive_line']}m
- Team B avg defensive line height: {metrics['team_b_avg_defensive_line']}m
- Team A compactness (std dev): {metrics['team_a_compactness']}m
- Team B compactness (std dev): {metrics['team_b_compactness']}m

FORMATIONS:
- Team A samples: {formations.get('team_a', [])[:5]}
- Team B samples: {formations.get('team_b', [])[:5]}

PRESSURE ZONES:
- Team A: {pressure_zones.get('team_a')}
- Team B: {pressure_zones.get('team_b')}

KEY EVENTS DETECTED:
{event_descriptions}

Generate a tactical analysis report covering:
1. Formation and shape assessment for both teams
2. Dominant pressure zones and territorial control
3. Key tactical patterns and recurring behaviors
4. Identified vulnerabilities and exploitable spaces
5. Recommended counter-tactical adjustments

Be specific. Reference timestamps and zones. Write like a professional scout report.
"""

    def _generate_tactical_analysis(
        self,
        formations: dict[str, list[list[int]]],
        pressure_zones: dict[str, list[list[float]]],
        events: list[dict[str, Any]],
        metrics: dict[str, float],
    ) -> str:
        prompt = self._build_tactical_prompt(formations, pressure_zones, events, metrics)
        return deepseek_chat([{"role": "user", "content": prompt}])

    def stream_tactical_analysis(
        self,
        formations: dict[str, list[list[int]]],
        pressure_zones: dict[str, list[list[float]]],
        events: list[dict[str, Any]],
        metrics: dict[str, float],
    ):
        prompt = self._build_tactical_prompt(formations, pressure_zones, events, metrics)
        yield from deepseek_chat_stream([{"role": "user", "content": prompt}])

