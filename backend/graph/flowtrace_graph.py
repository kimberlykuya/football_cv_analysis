from __future__ import annotations

import time
from functools import lru_cache
from typing import Any, Iterator, Optional, TypedDict


class FlowTraceState(TypedDict):
    video_path: str
    match_id: str
    team_id: str
    perception_output: Optional[dict]
    analysis_output: Optional[dict]
    visual_evidence: Optional[list[dict]]
    cross_match_report: Optional[str]
    error: Optional[str]


@lru_cache(maxsize=1)
def get_perceiver() -> Any:
    from backend.pipeline.perceiver import PerceiverAgent

    return PerceiverAgent()


@lru_cache(maxsize=1)
def get_analyst() -> Any:
    from backend.agents.analyst import AnalystAgent

    return AnalystAgent()


@lru_cache(maxsize=1)
def get_visual_evidence_agent() -> Any:
    from backend.agents.visual_evidence import VisualEvidenceAgent

    return VisualEvidenceAgent()


def get_tactical_memory() -> Any:
    from backend.memory.tactical_memory import TacticalMemory

    return TacticalMemory()


def get_match_rag() -> Any:
    from backend.memory.match_rag import MatchRAG

    return MatchRAG()


def perceive(state: FlowTraceState) -> FlowTraceState:
    if state.get("error"):
        return state
    try:
        output = get_perceiver().process_video(state["video_path"], state["match_id"])
        return {**state, "perception_output": output}
    except Exception as error:
        return {**state, "error": str(error)}


def analyze(state: FlowTraceState) -> FlowTraceState:
    if state.get("error"):
        return state
    try:
        output = get_analyst().analyze(state["perception_output"] or {})
        return {**state, "analysis_output": output}
    except Exception as error:
        return {**state, "error": str(error)}


def enrich_visual_evidence(state: FlowTraceState) -> FlowTraceState:
    if state.get("error"):
        return state
    try:
        evidence = get_visual_evidence_agent().generate(
            video_path=state["video_path"],
            match_id=state["match_id"],
            perception_output=state["perception_output"] or {},
            events=(state["analysis_output"] or {}).get("tactical_events", []),
        )
        return {**state, "visual_evidence": evidence}
    except Exception as error:
        return {**state, "error": str(error)}


def store_memory(state: FlowTraceState) -> FlowTraceState:
    if state.get("error"):
        return state
    try:
        events = state["analysis_output"]["tactical_events"]
        tactical_memory = get_tactical_memory()
        cross_report = tactical_memory.generate_cross_match_report(state["team_id"], events)
        tactical_memory.store_events(state["team_id"], state["match_id"], events)
        return {**state, "cross_match_report": cross_report}
    except Exception as error:
        return {**state, "error": str(error)}


def index_for_qa(state: FlowTraceState) -> FlowTraceState:
    if state.get("error"):
        return state
    try:
        get_match_rag().index_match(
            match_id=state["match_id"],
            frame_data=state["perception_output"]["frame_data"],
            tactical_summary=state["analysis_output"]["summary"],
            events=state["analysis_output"]["tactical_events"],
            visual_evidence=state.get("visual_evidence") or [],
        )
        return state
    except Exception as error:
        return {**state, "error": str(error)}


def build_graph():
    from langgraph.graph import END, StateGraph

    graph = StateGraph(FlowTraceState)
    graph.add_node("perceive", perceive)
    graph.add_node("analyze", analyze)
    graph.add_node("enrich_visual_evidence", enrich_visual_evidence)
    graph.add_node("store_memory", store_memory)
    graph.add_node("index_for_qa", index_for_qa)

    graph.set_entry_point("perceive")
    graph.add_edge("perceive", "analyze")
    graph.add_edge("analyze", "enrich_visual_evidence")
    graph.add_edge("enrich_visual_evidence", "store_memory")
    graph.add_edge("store_memory", "index_for_qa")
    graph.add_edge("index_for_qa", END)

    return graph.compile()


@lru_cache(maxsize=1)
def get_flowtrace_graph() -> Any:
    return build_graph()


def run_pipeline(video_path: str, match_id: str, team_id: str) -> dict:
    return get_flowtrace_graph().invoke(
        {
            "video_path": video_path,
            "match_id": match_id,
            "team_id": team_id,
            "perception_output": None,
            "analysis_output": None,
            "visual_evidence": None,
            "cross_match_report": None,
            "error": None,
        }
    )


def run_pipeline_streaming(video_path: str, match_id: str, team_id: str) -> Iterator[dict]:
    """Run pipeline with SSE-ready streaming events."""
    def _evt(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": event_type,
            "ts": time.time(),
            "analysis_id": match_id,
            "payload": payload,
        }

    state = {
        "video_path": video_path,
        "match_id": match_id,
        "team_id": team_id,
        "perception_output": None,
        "analysis_output": None,
        "visual_evidence": None,
        "cross_match_report": None,
        "error": None,
    }

    try:
        yield _evt("progress", {"stage": "perceive", "progress_pct": 0})
        perceiver = get_perceiver()
        state["perception_output"] = perceiver.process_video(video_path, match_id)
        yield _evt("progress", {"stage": "perceive", "progress_pct": 100})
    except Exception as e:
        state["error"] = str(e)
        yield _evt("error", {"message": str(e), "stage": "perceive"})
        return

    try:
        yield _evt("progress", {"stage": "analyze", "progress_pct": 0})
        analyst = get_analyst()
        state["analysis_output"] = analyst.analyze(
            state["perception_output"],
            generate_summary=False,
        )
        yield _evt("progress", {"stage": "analyze", "progress_pct": 100})

        for event in state["analysis_output"].get("tactical_events", []):
            yield _evt("tactical_event", event)

        yield _evt("progress", {"stage": "deepseek", "progress_pct": 0})
        summary_parts: list[str] = []
        for chunk in analyst.stream_tactical_analysis(
            state["analysis_output"]["formations"],
            state["analysis_output"]["pressure_zones"],
            state["analysis_output"]["tactical_events"],
            state["analysis_output"]["metrics"],
        ):
            summary_parts.append(chunk)
            yield _evt("summary_chunk", {"chunk": chunk})
        state["analysis_output"]["summary"] = "".join(summary_parts).strip()
        yield _evt("progress", {"stage": "deepseek", "progress_pct": 100})
    except Exception as e:
        state["error"] = str(e)
        yield _evt("error", {"message": str(e), "stage": "analyze"})
        return

    try:
        yield _evt("progress", {"stage": "visual_evidence", "progress_pct": 0})
        state["visual_evidence"] = get_visual_evidence_agent().generate(
            video_path=video_path,
            match_id=match_id,
            perception_output=state["perception_output"],
            events=state["analysis_output"].get("tactical_events", []),
        )
        yield _evt(
            "progress",
            {
                "stage": "visual_evidence",
                "progress_pct": 100,
                "evidence_count": len(state["visual_evidence"] or []),
            },
        )
    except Exception as e:
        state["error"] = str(e)
        yield _evt("error", {"message": str(e), "stage": "visual_evidence"})
        return

    try:
        yield _evt("progress", {"stage": "store_memory", "progress_pct": 50})
        events = state["analysis_output"]["tactical_events"]
        tactical_memory = get_tactical_memory()
        cross_report = tactical_memory.generate_cross_match_report(team_id, events)
        tactical_memory.store_events(team_id, match_id, events)
        state["cross_match_report"] = cross_report
        yield _evt("progress", {"stage": "store_memory", "progress_pct": 100})
    except Exception as e:
        state["error"] = str(e)
        yield _evt("error", {"message": str(e), "stage": "store_memory"})
        return

    try:
        yield _evt("progress", {"stage": "index_for_qa", "progress_pct": 50})
        get_match_rag().index_match(
            match_id=match_id,
            frame_data=state["perception_output"]["frame_data"],
            tactical_summary=state["analysis_output"]["summary"],
            events=state["analysis_output"]["tactical_events"],
            visual_evidence=state.get("visual_evidence") or [],
        )
        yield _evt("progress", {"stage": "index_for_qa", "progress_pct": 100})
    except Exception as e:
        state["error"] = str(e)
        yield _evt("error", {"message": str(e), "stage": "index_for_qa"})
        return

    yield _evt(
        "complete",
        {
            "success": True,
            "match_id": match_id,
            "team_id": team_id,
            "tactical_summary": state["analysis_output"]["summary"],
            "cross_match_report": state["cross_match_report"],
            "metrics": state["analysis_output"]["metrics"],
            "pressure_zones": state["analysis_output"]["pressure_zones"],
            "formations": state["analysis_output"]["formations"],
            "events_detected": len(state["analysis_output"]["tactical_events"]),
            "annotated_video_path": state["perception_output"].get("annotated_video_path"),
        },
    )
