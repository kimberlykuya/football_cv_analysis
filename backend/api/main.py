from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AliasChoices, BaseModel, Field

from backend.graph.flowtrace_graph import get_match_rag, get_tactical_memory, run_pipeline
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
    team_id: str = Form(...),
    match_label: str = Form(default=""),
):
    team_id = _require_non_empty(team_id, "team_id")
    match_id = str(uuid.uuid4())[:8]
    video_path = UPLOAD_DIR / f"{match_id}_{video.filename}"

    with video_path.open("wb") as destination:
        shutil.copyfileobj(video.file, destination)

    result = run_pipeline(
        video_path=str(video_path),
        match_id=match_id,
        team_id=team_id,
    )
    if result.get("error"):
        raise HTTPException(
            status_code=500,
            detail=result["error"],
        )

    analysis_output = result["analysis_output"]
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
