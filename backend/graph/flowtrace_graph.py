from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional, TypedDict


class FlowTraceState(TypedDict):
    video_path: str
    match_id: str
    team_id: str
    perception_output: Optional[dict]
    analysis_output: Optional[dict]
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
        )
        return state
    except Exception as error:
        return {**state, "error": str(error)}


def build_graph():
    from langgraph.graph import END, StateGraph

    graph = StateGraph(FlowTraceState)
    graph.add_node("perceive", perceive)
    graph.add_node("analyze", analyze)
    graph.add_node("store_memory", store_memory)
    graph.add_node("index_for_qa", index_for_qa)

    graph.set_entry_point("perceive")
    graph.add_edge("perceive", "analyze")
    graph.add_edge("analyze", "store_memory")
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
            "cross_match_report": None,
            "error": None,
        }
    )

