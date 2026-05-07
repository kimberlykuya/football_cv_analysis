from __future__ import annotations

from typing import Any

import cv2
import numpy as np


# Standard pitch reference points in meters (105m x 68m pitch)
# These are the known real-world coordinates of key pitch markings.
# We map pixel positions of these markings in the video frame to compute
# the homography matrix that corrects for perspective distortion.
PITCH_REFERENCE_POINTS = np.array(
    [
        [0, 0],          # Top-left corner
        [105, 0],        # Top-right corner
        [105, 68],       # Bottom-right corner
        [0, 68],         # Bottom-left corner
        [52.5, 0],       # Top center (halfway line top)
        [52.5, 68],      # Bottom center (halfway line bottom)
        [0, 34],         # Left center
        [105, 34],       # Right center
        [11, 34],        # Left penalty spot (approximate)
        [94, 34],        # Right penalty spot (approximate)
    ],
    dtype=np.float32,
)


class PitchTransformer:
    """Converts pixel coordinates to real-world pitch coordinates (meters).

    Uses a homography matrix computed from pitch reference points to correct
    for camera perspective distortion. Falls back to linear scaling if the
    homography cannot be reliably computed.
    """

    def __init__(self, pitch_width: float = 105.0, pitch_height: float = 68.0) -> None:
        self.pitch_width = pitch_width
        self.pitch_height = pitch_height
        self._homography: np.ndarray | None = None

    def calibrate(
        self,
        pixel_points: np.ndarray,
        pitch_points: np.ndarray | None = None,
    ) -> bool:
        """Compute homography matrix from known pixel-to-pitch point pairs.

        Args:
            pixel_points: Nx2 array of pixel coordinates for known pitch markings.
            pitch_points: Nx2 array of corresponding pitch coordinates in meters.
                          Defaults to PITCH_REFERENCE_POINTS (first N points).

        Returns:
            True if homography was successfully computed.
        """
        if pitch_points is None:
            pitch_points = PITCH_REFERENCE_POINTS[: len(pixel_points)]

        if len(pixel_points) < 4:
            return False

        homography, mask = cv2.findHomography(
            pixel_points.astype(np.float32),
            pitch_points.astype(np.float32),
            method=cv2.RANSAC,
            ransacReprojThreshold=3.0,
        )

        if homography is not None:
            self._homography = homography
            return True
        return False

    def _estimate_default_homography(
        self, frame_width: int, frame_height: int
    ) -> np.ndarray:
        """Build a default homography assuming the pitch fills the frame.

        This is a rough estimate that maps the four corners of the frame
        to the four corners of the pitch. Better than pure linear scaling
        but still approximate without manual calibration.
        """
        src = np.array(
            [
                [0, 0],
                [frame_width, 0],
                [frame_width, frame_height],
                [0, frame_height],
            ],
            dtype=np.float32,
        )
        dst = np.array(
            [
                [0, 0],
                [self.pitch_width, 0],
                [self.pitch_width, self.pitch_height],
                [0, self.pitch_height],
            ],
            dtype=np.float32,
        )
        return cv2.getPerspectiveTransform(src, dst)

    def transform(
        self,
        frame_data: list[dict[str, Any]],
        frame_size: tuple[int, int] | None = None,
    ) -> list[dict[str, Any]]:
        if frame_size is None:
            return frame_data

        frame_width, frame_height = frame_size
        if frame_width <= 0 or frame_height <= 0:
            return frame_data

        # Use calibrated homography or fall back to default estimate
        homography = self._homography
        if homography is None:
            homography = self._estimate_default_homography(frame_width, frame_height)

        # Collect all pixel positions for batch transform
        pixel_positions: list[tuple[int, int]] = []
        position_refs: list[tuple[int, int]] = []  # (frame_idx, player_idx)

        for fi, frame in enumerate(frame_data):
            for pi, player in enumerate(frame["players"]):
                px = player.get("pixel_x")
                py = player.get("pixel_y")
                if px is not None and py is not None:
                    pixel_positions.append((px, py))
                    position_refs.append((fi, pi))

        if not pixel_positions:
            return frame_data

        # Batch perspective transform
        src_points = np.array(pixel_positions, dtype=np.float32).reshape(-1, 1, 2)
        dst_points = cv2.perspectiveTransform(src_points, homography)

        # Assign pitch coordinates back
        for (fi, pi), (px, py) in zip(position_refs, dst_points.reshape(-1, 2)):
            pitch_x = float(np.clip(px, 0, self.pitch_width))
            pitch_y = float(np.clip(py, 0, self.pitch_height))
            frame_data[fi]["players"][pi]["pitch_x"] = round(pitch_x, 2)
            frame_data[fi]["players"][pi]["pitch_y"] = round(pitch_y, 2)

        return frame_data

