from __future__ import annotations

from typing import Any

import chromadb

from backend.agents.llm import deepseek_chat
from backend.memory.errors import MatchEvidenceNotFoundError


class MatchRAG:
    def __init__(self, storage_path: str = "./flowtrace_db/match_rag") -> None:
        import os

        os.makedirs(storage_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=storage_path)
        self.embedder: Any | None = None

    def index_match(
        self,
        match_id: str,
        frame_data: list,
        tactical_summary: str,
        events: list,
        visual_evidence: list[dict[str, Any]] | None = None,
    ) -> None:
        collection = self.client.get_or_create_collection(f"match_{match_id}")

        documents: list[str] = []
        metadatas: list[dict[str, str | int | float | bool]] = []
        ids: list[str] = []

        for frame in frame_data:
            description = self._build_frame_description(frame)
            frame["description"] = description
            documents.append(description)
            metadatas.append(
                {
                    "frame_id": str(frame.get("frame_id", "")),
                    "timestamp": str(frame.get("timestamp", 0)),
                    "type": "frame",
                    "title": "Frame positioning",
                    "confidence": 50.0,
                }
            )
            ids.append(f"frame_{frame.get('frame_id')}")

        for index, event in enumerate(events):
            frame_id = str(event.get("frame_id", ""))
            event_type = str(event.get("type", "event"))
            documents.append(str(event.get("description", event_type)))
            metadatas.append(
                {
                    "frame_id": frame_id,
                    "timestamp": str(event.get("timestamp", 0)),
                    "type": "event",
                    "title": event_type.replace("_", " "),
                    "event_type": event_type,
                    "zone": str(event.get("zone", "")),
                    "confidence": float(event.get("confidence", 60.0)),
                }
            )
            ids.append(f"event_{index}_{frame_id or index}")

        for index, evidence in enumerate(visual_evidence or []):
            document = self._build_visual_description(evidence)
            frame_id = str(evidence.get("frame_id", ""))
            documents.append(document)
            metadatas.append(
                {
                    "frame_id": frame_id,
                    "timestamp": str(evidence.get("timestamp", 0)),
                    "type": "visual",
                    "title": "Visual evidence",
                    "event_type": str(evidence.get("event_type", "")),
                    "source_image_path": str(evidence.get("source_image_path", "")),
                    "confidence": float(evidence.get("confidence", 60.0)),
                    "uncertainty": str(evidence.get("uncertainty", "")),
                    "tags": ",".join(str(tag) for tag in evidence.get("tags", [])),
                }
            )
            ids.append(f"visual_{index}_{frame_id or index}")

        documents.append(tactical_summary)
        metadatas.append(
            {
                "type": "summary",
                "timestamp": "0",
                "frame_id": "0",
                "title": "Tactical summary",
                "confidence": 50.0,
            }
        )
        ids.append("summary")

        embeddings = self._embed(documents)
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids, embeddings=embeddings)

    def answer(self, match_id: str, question: str) -> dict[str, Any]:
        try:
            collection = self.client.get_collection(f"match_{match_id}")
        except Exception as error:
            raise MatchEvidenceNotFoundError(
                f"No evidence indexed for match {match_id}"
            ) from error

        evidence = self._retrieve_hybrid(collection, question)
        if not evidence:
            raise MatchEvidenceNotFoundError(f"No evidence indexed for match {match_id}")

        context = "\n".join(
            [
                f"[{item['metadata'].get('timestamp')}s] "
                f"{item['metadata'].get('type')} - {item['document']}"
                for item in evidence
            ]
        )
        answer_text = deepseek_chat(
            [
                {
                    "role": "user",
                    "content": f"""
You are a football tactical analyst reviewing footage with a coach.

COACH QUESTION: {question}

RELEVANT MATCH EVIDENCE (with timestamps):
{context}

Answer the coach's question:
1. Give a direct answer in 1-2 sentences
2. Walk through the tactical breakdown citing specific timestamps like [12.4s]
3. Identify the root positional/tactical cause
4. Suggest one specific adjustment to address it

Always cite timestamps so the coach can jump to the exact moment.
""",
                }
            ]
        )

        cited_timestamps = sorted(
            {
                float(item["metadata"].get("timestamp", 0))
                for item in evidence
                if item["metadata"].get("timestamp")
                and item["metadata"].get("type") in {"frame", "event", "visual"}
            }
        )[:8]

        return {
            "answer": answer_text,
            "cited_timestamps": cited_timestamps,
            "evidence_count": len(evidence),
            "evidence_cards": [self._build_evidence_card(item) for item in evidence],
        }

    def _retrieve_hybrid(self, collection: Any, question: str, n_results: int = 12) -> list[dict[str, Any]]:
        collection_count = int(collection.count())
        if collection_count <= 0:
            return []
        results = collection.query(
            query_embeddings=[self._embed([question])[0]],
            n_results=min(max(n_results * 3, 24), collection_count),
        )
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0] if results.get("distances") else [0.0] * len(docs)

        ranked: list[dict[str, Any]] = []
        question_lower = question.lower()
        for doc, meta, distance in zip(docs, metas, distances):
            evidence_type = meta.get("type", "")
            score = 1.0 - float(distance or 0.0)
            if evidence_type == "visual":
                score += 0.18
            elif evidence_type == "event":
                score += 0.12
            if str(meta.get("event_type", "")).lower() in question_lower:
                score += 0.1
            if str(meta.get("title", "")).lower() in question_lower:
                score += 0.05
            ranked.append({"document": doc, "metadata": meta, "score": score})

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return self._diversify_by_timestamp(ranked, n_results)

    def _diversify_by_timestamp(self, ranked: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        bucket_counts: dict[int, int] = {}
        for item in ranked:
            timestamp = float(item["metadata"].get("timestamp", 0) or 0)
            bucket = int(timestamp // 2)
            if bucket_counts.get(bucket, 0) >= 2:
                continue
            selected.append(item)
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
            if len(selected) >= limit:
                break
        return sorted(selected, key=lambda item: float(item["metadata"].get("timestamp", 0) or 0))

    def _build_evidence_card(self, item: dict[str, Any]) -> dict[str, Any]:
        meta = item["metadata"]
        timestamp = float(meta.get("timestamp", 0) or 0)
        return {
            "timestamp": timestamp,
            "type": str(meta.get("type", "evidence")),
            "title": str(meta.get("title", meta.get("type", "Evidence"))),
            "excerpt": str(item["document"]),
            "confidence": float(meta.get("confidence", 0) or 0),
            "frame_id": str(meta.get("frame_id", "")),
            "source_image_path": str(meta.get("source_image_path", "")),
        }

    def _build_frame_description(self, frame: dict[str, Any]) -> str:
        players = frame.get("players", [])
        observed_players: list[str] = []
        for player in players:
            pitch_x = player.get("pitch_x")
            pitch_y = player.get("pitch_y")
            if pitch_x is None or pitch_y is None:
                continue
            observed_players.append(
                f"Player {player.get('id', '?')} ({player.get('team') or 'unknown'}) at ({float(pitch_x):.1f}m, {float(pitch_y):.1f}m)"
            )

        timestamp = frame.get("timestamp", 0)
        if not observed_players:
            return f"[{timestamp}s] No players with pitch coordinates detected."
        return f"[{timestamp}s] " + ", ".join(observed_players)

    def _build_visual_description(self, evidence: dict[str, Any]) -> str:
        parts = [
            str(evidence.get("caption", "")),
            f"Visible shape: {evidence.get('visible_shape', '')}",
            f"Pressure cue: {evidence.get('pressure_cue', '')}",
            f"Team context: {evidence.get('team_context', '')}",
            f"Event: {evidence.get('event_description', '')}",
            f"Uncertainty: {evidence.get('uncertainty', '')}",
        ]
        return " ".join(part for part in parts if part.strip())

    def _embed(self, documents: list[str]) -> list[list[float]]:
        import os

        import torch
        from sentence_transformers import SentenceTransformer

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if device.type != "cuda" and os.getenv("ALLOW_CPU_FALLBACK", "true").strip().lower() in {"0", "false", "no", "off"}:
            raise RuntimeError(
                "ROCm PyTorch is not active for embeddings and ALLOW_CPU_FALLBACK=false"
            )
        default_batch_size = 256 if device.type == "cuda" else 64
        batch_size = int(os.getenv("EMBED_BATCH_SIZE", str(default_batch_size)))
        if self.embedder is None:
            model_name = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
            self.embedder = SentenceTransformer(model_name).to(device)
        return self.embedder.encode(
            documents,
            batch_size=batch_size,
            device=str(device),
            normalize_embeddings=True,
        ).tolist()
