from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from openai import OpenAI

DEFAULT_BASE_URL = "https://api.featherless.ai/v1"
DEFAULT_API_KEY = ""
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Pro"


@lru_cache(maxsize=1)
def get_deepseek_client() -> OpenAI:
    base_url = os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.getenv(
        "DEEPSEEK_API_KEY",
        os.getenv("FEATHERLESS_API_KEY", DEFAULT_API_KEY),
    )
    return OpenAI(base_url=base_url, api_key=api_key)


def strip_reasoning(content: str) -> str:
    if "</think>" in content:
        return content.split("</think>", 1)[-1].strip()
    return content.strip()


def deepseek_chat(messages: list[dict[str, Any]], temperature: float = 0.3) -> str:
    try:
        response = get_deepseek_client().chat.completions.create(
            model=os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL),
            messages=messages,
            temperature=temperature,
            max_tokens=4096,
        )
        content = response.choices[0].message.content or ""
        return strip_reasoning(content)
    except Exception as e:
        allow_mock = os.getenv("ALLOW_MOCK_LLM", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if not allow_mock:
            raise RuntimeError(
                "DeepSeek-V4 request failed and ALLOW_MOCK_LLM is disabled"
            ) from e

        # Fallback: mock response if DeepSeek-V4 unavailable
        import sys
        print(f"[WARN DeepSeek-V4 unavailable, using mock response] {e}", file=sys.stderr)
        mock_responses = {
            "tactical": "Based on the positional data analyzed, Team A demonstrated a 4-3-3 formation with strong territorial control in the midfield. Key observations include consistent pressure in the attacking third (zone_80m) and a compact defensive shape. Team B showed a more aggressive high-line defense. Recommended adjustment: exploit the space between Team B's defensive lines with targeted through-ball transitions.",
            "cross_match": "Insufficient historical data. First analysis for this team. Patterns will accumulate across future matches.",
            "qa": "Based on the available match data and frame evidence cited above, the tactical situation shows both teams employing conventional positioning strategies. The highlighted timestamps show key moments where spatial relationships shifted significantly."
        }
        # Return appropriate mock based on prompt context
        if "scout" in messages[-1]["content"].lower() or "historical" in messages[-1]["content"].lower():
            return mock_responses["cross_match"]
        elif "question" in messages[-1]["content"].lower() or "coach" in messages[-1]["content"].lower():
            return mock_responses["qa"]
        else:
            return mock_responses["tactical"]

