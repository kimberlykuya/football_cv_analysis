from __future__ import annotations

from typing import Any

import chromadb

from backend.agents.llm import deepseek_chat


class TacticalMemory:
    def __init__(self, storage_path: str = "./flowtrace_db/team_memory") -> None:
        import os
        os.makedirs(storage_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=storage_path)
        self.collection = self.client.get_or_create_collection(
            "team_tactics",
            metadata={"hnsw:space": "cosine"},
        )
        self.embedder: Any | None = None

    def store_events(self, team_id: str, clip_id: str, events: list[dict]) -> None:
        if not events:
            return

        documents = [event["description"] for event in events]
        embeddings = self._embed(documents)
        metadatas = [
            {
                "team_id": team_id,
                "clip_id": clip_id,
                "event_type": event["type"],
                "zone": event["zone"],
                "timestamp": str(event["timestamp"]),
            }
            for event in events
        ]
        ids = [f"{team_id}_{clip_id}_{index}" for index in range(len(events))]

        existing_ids = set(self.collection.get(ids=ids).get("ids", []))
        new_items = [
            (doc, meta, item_id, embedding)
            for doc, meta, item_id, embedding in zip(documents, metadatas, ids, embeddings)
            if item_id not in existing_ids
        ]

        if not new_items:
            return

        new_documents, new_metadatas, new_ids, new_embeddings = zip(*new_items)
        self.collection.add(
            documents=list(new_documents),
            metadatas=list(new_metadatas),
            ids=list(new_ids),
            embeddings=list(new_embeddings),
        )

    def get_team_profile(self, team_id: str, n_results: int = 30) -> dict[str, Any]:
        return self.collection.get(where={"team_id": team_id})

    def find_patterns(self, team_id: str, query: str, n_results: int = 15) -> dict[str, Any]:
        query_embedding = self._embed([query])[0]
        return self.collection.query(
            query_embeddings=[query_embedding],
            where={"team_id": team_id},
            n_results=n_results,
        )

    def generate_cross_match_report(self, team_id: str, new_events: list) -> str:
        historical = self.get_team_profile(team_id)
        historical_docs = historical.get("documents", [])

        if not historical_docs:
            return "Insufficient historical data. Analyze more clips to build a team profile."

        current = "\n".join(event["description"] for event in new_events)
        history = "\n".join(historical_docs[-40:])

        return deepseek_chat(
            [
                {
                    "role": "user",
                    "content": f"""
You are an elite football scout who has watched multiple matches of the same team.

HISTORICAL PATTERNS ({len(historical_docs)} events across previous clips):
{history}

CURRENT MATCH EVENTS:
{current}

Provide a cross-match scouting report identifying:
1. RECURRING PATTERNS: Behaviors seen in 2+ clips (mark frequency)
2. NEW BEHAVIORS: Tactics not observed before
3. CONSISTENT WEAKNESSES: Exploitable patterns that repeat
4. RECOMMENDED COUNTER-TACTICS: Specific adjustments to exploit patterns

Format as a professional scouting report. Reference specific zones and player roles.
""",
                }
            ]
        )

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

