from __future__ import annotations

from typing import Any

import cv2
import numpy as np
from sklearn.cluster import KMeans


class TeamClassifier:
    def assign_teams(self, frame_data: list[dict[str, Any]], raw_frames: list) -> list[dict[str, Any]]:
        all_colors: list[list[float]] = []
        player_refs: list[tuple[int, int]] = []

        for frame_index, (frame_info, frame) in enumerate(zip(frame_data, raw_frames)):
            for player_index, player in enumerate(frame_info["players"]):
                color = self._extract_jersey_color(frame, player["bbox"])
                if color is not None:
                    all_colors.append(color)
                    player_refs.append((frame_index, player_index))

        if len(all_colors) < 2:
            return frame_data

        cluster_count = 3 if len(all_colors) >= 6 else 2
        kmeans = KMeans(n_clusters=cluster_count, random_state=42, n_init=10)
        labels = kmeans.fit_predict(np.array(all_colors))
        centers = kmeans.cluster_centers_
        label_map = self._build_label_map(centers)

        for (frame_index, player_index), label in zip(player_refs, labels):
            frame_data[frame_index]["players"][player_index]["team"] = label_map.get(int(label), "unknown")

        return frame_data

    def _build_label_map(self, centers: np.ndarray) -> dict[int, str]:
        if len(centers) == 2:
            ordered = sorted(range(2), key=lambda idx: centers[idx][0])
            return {ordered[0]: "team_a", ordered[1]: "team_b"}

        referee_idx = int(np.argmin(centers[:, 1] + centers[:, 2]))
        team_indices = [idx for idx in range(len(centers)) if idx != referee_idx]
        team_indices = sorted(team_indices, key=lambda idx: centers[idx][0])
        return {
            team_indices[0]: "team_a",
            team_indices[1]: "team_b",
            referee_idx: "referee",
        }

    def _extract_jersey_color(self, frame, bbox) -> list[float] | None:
        x1, y1, x2, y2 = [int(v) for v in bbox]
        height, width = frame.shape[:2]
        x1 = max(0, min(x1, width - 1))
        x2 = max(0, min(x2, width))
        y1 = max(0, min(y1, height - 1))
        y2 = max(0, min(y2, height))

        torso_y1 = y1 + int((y2 - y1) * 0.3)
        torso_y2 = y1 + int((y2 - y1) * 0.7)
        torso = frame[torso_y1:torso_y2, x1:x2]

        if torso.size == 0:
            return None

        hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
        return hsv.reshape(-1, 3).mean(axis=0).tolist()

