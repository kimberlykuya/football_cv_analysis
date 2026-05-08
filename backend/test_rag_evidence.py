from __future__ import annotations

from backend.memory import match_rag
from backend.memory.match_rag import MatchRAG


def test_match_rag_indexes_visual_evidence_and_returns_cards(tmp_path, monkeypatch):
    rag = MatchRAG(storage_path=str(tmp_path / "rag"))

    def fake_embed(documents: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for document in documents:
            text = document.lower()
            vectors.append(
                [
                    1.0 if "visual" in text or "pressure" in text else 0.1,
                    1.0 if "overload" in text else 0.1,
                    1.0 if "player" in text else 0.1,
                ]
            )
        return vectors

    rag._embed = fake_embed  # type: ignore[method-assign]
    monkeypatch.setattr(match_rag, "deepseek_chat", lambda _messages: "Use the overload cue at [1.0s].")

    rag.index_match(
        match_id="match-test",
        frame_data=[
            {
                "frame_id": 30,
                "timestamp": 1.0,
                "players": [
                    {"id": 7, "team": "team_a", "pitch_x": 50.0, "pitch_y": 30.0}
                ],
            }
        ],
        tactical_summary="Team A created overloads.",
        events=[
            {
                "frame_id": 30,
                "timestamp": 1.0,
                "type": "overload",
                "zone": "zone_55m",
                "description": "Team A overload in the middle third.",
                "confidence": 82,
            }
        ],
        visual_evidence=[
            {
                "timestamp": 1.0,
                "frame_id": 30,
                "source_image_path": "./uploads/vlm_frames/match-test/frame_30.jpg",
                "event_type": "overload",
                "event_description": "Team A overload in the middle third.",
                "caption": "Visual evidence shows a compact overload.",
                "visible_shape": "Three attackers around one defender.",
                "pressure_cue": "Pressure is concentrated centrally.",
                "team_context": "team_a",
                "uncertainty": "low",
                "tags": ["visual", "overload"],
                "confidence": 82,
            }
        ],
    )

    answer = rag.answer("match-test", "Where is the visual pressure overload?")

    assert answer["answer"] == "Use the overload cue at [1.0s]."
    assert answer["evidence_count"] > 0
    assert answer["evidence_cards"]
    assert any(card["type"] == "visual" for card in answer["evidence_cards"])
    assert 1.0 in answer["cited_timestamps"]
