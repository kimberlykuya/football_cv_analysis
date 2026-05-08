from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import AliasChoices, BaseModel, Field

from backend.api.gpu_monitor import get_monitor
from backend.api.registry import (
    get_analysis,
    get_total_count,
    list_analyses,
    register_analysis,
    update_status as update_analysis_status,
)
from backend.graph.flowtrace_graph import (
    get_match_rag,
    get_tactical_memory,
    run_pipeline,
    run_pipeline_streaming,
)
from backend.memory.errors import MatchEvidenceNotFoundError

app = FastAPI(title="FlowTrace API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class CoachQARequest(BaseModel):
    match_id: str = Field(validation_alias=AliasChoices("match_id", "matchId"))
    question: str


class AnalyzeResponse(BaseModel):
    success: bool
    match_id: str
    team_id: str
    match_label: str
    tactical_summary: str
    cross_match_report: str
    metrics: dict[str, float]
    pressure_zones: dict[str, list[list[float]]]
    formations: dict[str, list[list[int]]]
    events_detected: int
    annotated_video_path: str | None = None


class CoachQAResponse(BaseModel):
    answer: str
    cited_timestamps: list[float]
    evidence_count: int
    evidence_cards: list[dict] = Field(default_factory=list)


class TeamProfileResponse(BaseModel):
    team_id: str
    profile: dict


def _require_non_empty(value: str, field_name: str) -> str:
    if not value.strip():
        raise HTTPException(status_code=400, detail=f"{field_name} is required")
    return value.strip()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_video(
    video: UploadFile = File(...),
    team_id: str = Form(default="demo-team"),
    match_label: str = Form(default=""),
):
    team_id = team_id.strip() or "demo-team"
    match_id = str(uuid.uuid4())[:8]
    if not match_label.strip():
        match_label = video.filename or match_id
    video_path = UPLOAD_DIR / f"{match_id}_{video.filename}"

    with video_path.open("wb") as destination:
        shutil.copyfileobj(video.file, destination)

    register_analysis(match_id, team_id, video.filename or "video.mp4", match_label)
    started_at = time.time()

    result = run_pipeline(
        video_path=str(video_path),
        match_id=match_id,
        team_id=team_id,
    )
    if result.get("error"):
        update_analysis_status(match_id, "error", error_message=result["error"])
        raise HTTPException(
            status_code=500,
            detail=result["error"],
        )

    analysis_output = result["analysis_output"]
    update_analysis_status(
        match_id,
        "done",
        events_detected=len(analysis_output["tactical_events"]),
        duration_seconds=time.time() - started_at,
    )

    return AnalyzeResponse(
        success=True,
        match_id=match_id,
        team_id=team_id,
        match_label=match_label,
        tactical_summary=analysis_output["summary"],
        cross_match_report=result["cross_match_report"],
        metrics=analysis_output["metrics"],
        pressure_zones=analysis_output["pressure_zones"],
        formations=analysis_output["formations"],
        events_detected=len(analysis_output["tactical_events"]),
        annotated_video_path=result["perception_output"].get("annotated_video_path"),
    )


@app.post("/api/coach-qa", response_model=CoachQAResponse)
def coach_qa(payload: CoachQARequest):
    match_id = _require_non_empty(payload.match_id, "match_id")
    question = _require_non_empty(payload.question, "question")
    try:
        return CoachQAResponse(**get_match_rag().answer(match_id, question))
    except MatchEvidenceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/api/analyze/stream")
async def analyze_video_stream(
    request: Request,
    video: UploadFile = File(...),
    team_id: str = Form(default="demo-team"),
    match_label: str = Form(default=""),
):
    """Analyze video with real-time SSE streaming of results."""
    team_id = team_id.strip() or "demo-team"
    match_id = str(uuid.uuid4())[:8]
    if not match_label.strip():
        match_label = video.filename or match_id
    video_path = UPLOAD_DIR / f"{match_id}_{video.filename}"

    with video_path.open("wb") as destination:
        shutil.copyfileobj(video.file, destination)

    register_analysis(match_id, team_id, video.filename or "video.mp4", match_label)
    started_at = time.time()

    async def event_generator():
        try:
            for event_dict in run_pipeline_streaming(str(video_path), match_id, team_id):
                if await request.is_disconnected():
                    update_analysis_status(
                        match_id,
                        "error",
                        error_message="Client disconnected during streaming analysis",
                        duration_seconds=time.time() - started_at,
                    )
                    break

                event_type = event_dict.get("type")
                payload = event_dict.get("payload", {})

                if event_type == "error":
                    update_analysis_status(
                        match_id,
                        "error",
                        error_message=str(payload.get("message", "Unknown error")),
                        duration_seconds=time.time() - started_at,
                    )
                elif event_type == "complete":
                    update_analysis_status(
                        match_id,
                        "done",
                        events_detected=int(payload.get("events_detected", 0)),
                        duration_seconds=time.time() - started_at,
                    )
                yield f"data: {json.dumps(event_dict)}\n\n"
        except Exception as error:
            update_analysis_status(
                match_id,
                "error",
                error_message=str(error),
                duration_seconds=time.time() - started_at,
            )
            yield f"data: {json.dumps({'type': 'error', 'ts': time.time(), 'analysis_id': match_id, 'payload': {'message': str(error)}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/team/{team_id}/profile")
def team_profile(team_id: str):
    team_id = _require_non_empty(team_id, "team_id")
    try:
        profile = get_tactical_memory().get_team_profile(team_id)
        safe_profile = json.loads(json.dumps(profile, default=str))
        return {
            "team_id": team_id,
            "profile": safe_profile,
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/analyses")
def list_all_analyses(limit: int = 50, offset: int = 0):
    """List all analyses with optional pagination."""
    analyses = list_analyses(limit=limit, offset=offset)
    total_count = get_total_count()
    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "analyses": analyses,
    }


@app.get("/api/analyses/{match_id}")
def get_single_analysis(match_id: str):
    """Get a single analysis by match_id."""
    analysis = get_analysis(match_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis {match_id} not found")
    return analysis


@app.get("/api/gpu/status")
def gpu_status():
    """Get current GPU status."""
    monitor = get_monitor()
    status = monitor.get_status()
    return {
        "gpu_util_pct": status.gpu_util_pct,
        "vram_used_mb": status.vram_used_mb,
        "vram_total_mb": status.vram_total_mb,
        "temperature_c": status.temperature_c,
        "device_name": status.device_name,
        "cuda_available": status.cuda_available,
        "timestamp": status.timestamp,
    }


@app.get("/api/gpu/history")
def gpu_history(limit: int = 300):
    """Get GPU monitoring history (last N samples)."""
    monitor = get_monitor()
    return {"history": monitor.get_history(limit=limit)}
