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

    def index_match(self, match_id: str, frame_data: list, tactical_summary: str, events: list) -> None:
        collection = self.client.get_or_create_collection(f"match_{match_id}")

        documents: list[str] = []
        metadatas: list[dict[str, str]] = []
        ids: list[str] = []

        for frame in frame_data:
            description = self._build_frame_description(frame)
            frame["description"] = description
            documents.append(description)
            metadatas.append(
                {
                    "frame_id": str(frame["frame_id"]),
                    "timestamp": str(frame["timestamp"]),
                    "type": "frame",
                }
            )
            ids.append(f"frame_{frame['frame_id']}")

        for index, event in enumerate(events):
            documents.append(event["description"])
            metadatas.append(
                {
                    "frame_id": str(event["frame_id"]),
                    "timestamp": str(event["timestamp"]),
                    "type": "event",
                    "event_type": event["type"],
                    "zone": event["zone"],
                }
            )
            ids.append(f"event_{index}_{event['frame_id']}")

        documents.append(tactical_summary)
        metadatas.append({"type": "summary", "timestamp": "0", "frame_id": "0"})
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

        results = collection.query(query_embeddings=[self._embed([question])[0]], n_results=12)

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        if not docs:
            raise MatchEvidenceNotFoundError(f"No evidence indexed for match {match_id}")

        evidence = sorted(
            zip(docs, metas),
            key=lambda item: float(item[1].get("timestamp", 0)),
        )

        context = "\n".join([f"[{meta.get('timestamp')}s] {doc}" for doc, meta in evidence])
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
                float(meta.get("timestamp", 0))
                for _, meta in evidence
                if meta.get("timestamp") and meta.get("type") in {"frame", "event"}
            }
        )[:8]

        return {
            "answer": answer_text,
            "cited_timestamps": cited_timestamps,
            "evidence_count": len(docs),
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
            self.embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2").to(device)
        return self.embedder.encode(
            documents,
            batch_size=batch_size,
            device=str(device),
            normalize_embeddings=True,
        ).tolist()

