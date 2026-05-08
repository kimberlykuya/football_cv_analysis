from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import Any, Iterator

from openai import OpenAI

DEFAULT_BASE_URL = "https://api.featherless.ai/v1"
DEFAULT_API_KEY = ""
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Pro"
DEFAULT_QWEN_MODEL = "Qwen/Qwen3-235B-A22B"


@lru_cache(maxsize=1)
def get_deepseek_client() -> OpenAI:
    base_url = os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.getenv(
        "DEEPSEEK_API_KEY",
        os.getenv("FEATHERLESS_API_KEY", DEFAULT_API_KEY),
    )
    return OpenAI(base_url=base_url, api_key=api_key)


@lru_cache(maxsize=1)
def get_qwen_client() -> OpenAI:
    base_url = os.getenv("QWEN_BASE_URL", os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL))
    api_key = os.getenv(
        "QWEN_API_KEY",
        os.getenv("FEATHERLESS_API_KEY", DEFAULT_API_KEY),
    )
    return OpenAI(base_url=base_url, api_key=api_key)


def strip_reasoning(content: str) -> str:
    if "</think>" in content:
        return content.split("</think>", 1)[-1].strip()
    return content.strip()


def deepseek_chat(messages: list[dict[str, Any]], temperature: float = 0.3) -> str:
    try:
        model = os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL)
        print(f"[LLM] DeepSeek request model={model}", file=sys.stderr)
        response = get_deepseek_client().chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=4096,
        )
        content = response.choices[0].message.content or ""
        print(f"[LLM] DeepSeek response chars={len(content)}", file=sys.stderr)
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


def qwen_chat(messages: list[dict[str, Any]], temperature: float = 0.1) -> str:
    try:
        response = get_qwen_client().chat.completions.create(
            model=os.getenv("QWEN_MODEL", DEFAULT_QWEN_MODEL),
            messages=messages,
            temperature=temperature,
            max_tokens=int(os.getenv("QWEN_MAX_TOKENS", "2048")),
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
            raise RuntimeError("Qwen request failed and ALLOW_MOCK_LLM is disabled") from e

        import sys

        print(f"[WARN Qwen unavailable, using heuristic validation] {e}", file=sys.stderr)
        return ""



def deepseek_chat_stream(
    messages: list[dict[str, Any]],
    temperature: float = 0.3,
) -> Iterator[str]:
    """Stream chat completions token by token from DeepSeek."""
    try:
        model = os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL)
        print(f"[LLM] DeepSeek streaming request model={model}", file=sys.stderr)
        response = get_deepseek_client().chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=4096,
            stream=True,
        )
        yielded = 0
        reasoning = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                reasoning += token
                if "</think>" in reasoning:
                    reasoning = reasoning.split("</think>", 1)[-1].strip()
                    reasoning = ""
                elif "<think>" not in reasoning:
                    yielded += len(token)
                    yield token
        print(f"[LLM] DeepSeek streaming response chars={yielded}", file=sys.stderr)
    except Exception as e:
        allow_mock = os.getenv("ALLOW_MOCK_LLM", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if not allow_mock:
            raise RuntimeError(
                "DeepSeek-V4 streaming failed and ALLOW_MOCK_LLM is disabled"
            ) from e

        print(f"[WARN DeepSeek-V4 unavailable, using mock streaming response] {e}", file=sys.stderr)
        
        mock_text = (
            "Based on the match analysis, Team A demonstrated a strong 4-3-3 formation "
            "with consistent territorial control. Key tactical observations include solid "
            "midfield positioning and effective transitions. Team B employed a high-line "
            "defensive strategy with aggressive pressing in the attacking third. "
            "The recommended tactical adjustment focuses on exploiting space between "
            "the defensive lines through targeted through-ball sequences."
        )

        # Stream words with small delays
        import time
        for word in mock_text.split():
            yield word + " "
            time.sleep(0.02)  # Small delay to simulate streaming


def deepseek_health_check() -> str:
    response = get_deepseek_client().chat.completions.create(
        model=os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL),
        messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        temperature=0,
        max_tokens=8,
    )
    return strip_reasoning(response.choices[0].message.content or "")
