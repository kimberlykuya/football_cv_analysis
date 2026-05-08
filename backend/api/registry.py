"""Upload and analysis registry using SQLite."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


REGISTRY_DB = Path("./flowtrace_db/analyses_registry.db")


def _init_db() -> None:
    """Initialize database schema if it doesn't exist."""
    REGISTRY_DB.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(REGISTRY_DB)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS analyses (
            match_id TEXT PRIMARY KEY,
            team_id TEXT NOT NULL,
            match_label TEXT,
            video_filename TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL,
            events_detected INTEGER DEFAULT 0,
            duration_seconds REAL DEFAULT 0.0,
            error_message TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def register_analysis(
    match_id: str,
    team_id: str,
    video_filename: str,
    match_label: str = "",
) -> None:
    """Register a new analysis in the registry."""
    _init_db()
    conn = sqlite3.connect(REGISTRY_DB)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO analyses
        (match_id, team_id, match_label, video_filename, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (match_id, team_id, match_label or "", video_filename, datetime.utcnow().isoformat(), "processing"),
    )
    conn.commit()
    conn.close()


def update_status(
    match_id: str,
    status: str,
    events_detected: int = 0,
    duration_seconds: float = 0.0,
    error_message: str | None = None,
) -> None:
    """Update analysis status and metadata."""
    _init_db()
    conn = sqlite3.connect(REGISTRY_DB)
    cursor = conn.cursor()

    completed_at = datetime.utcnow().isoformat() if status in ("done", "error") else None

    cursor.execute(
        """
        UPDATE analyses
        SET status = ?, events_detected = ?, duration_seconds = ?, error_message = ?, completed_at = ?
        WHERE match_id = ?
        """,
        (status, events_detected, duration_seconds, error_message, completed_at, match_id),
    )
    conn.commit()
    conn.close()


def get_analysis(match_id: str) -> dict[str, Any] | None:
    """Retrieve a single analysis record."""
    _init_db()
    conn = sqlite3.connect(REGISTRY_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM analyses WHERE match_id = ?", (match_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return dict(row)


def list_analyses(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """List all analyses, sorted by created_at DESC."""
    _init_db()
    conn = sqlite3.connect(REGISTRY_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM analyses
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_total_count() -> int:
    """Get total number of analyses."""
    _init_db()
    conn = sqlite3.connect(REGISTRY_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM analyses")
    count = cursor.fetchone()[0]
    conn.close()

    return count
