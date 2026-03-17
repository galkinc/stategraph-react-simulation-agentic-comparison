# src/research/metrics_helpers.py
"""
Helpers for computing research-specific metrics.
Reusable by both ReAct and StateGraph strategies.
"""
import numpy as np
from typing import Literal, Sequence
import time

from src.domain.strategy_models import ConversationTurn


def calculate_percentiles(values: list[float], targets: list[int] = [50, 90, 95]) -> dict[str, float]:
    """Calculate percentiles — generic utility."""
    if not values:
        return {f"p{p}": 0.0 for p in targets} | {"mean": 0.0, "min": 0.0, "max": 0.0, "count": 0, "median": 0.0}

    result = {
        "mean": float(np.mean(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "count": len(values),
        "median": float(np.median(values)),
    }
    for p in targets:
        result[f"p{p}"] = float(np.percentile(values, p))
    return result


def detect_repeated_question(
    current: str,
    history: Sequence[ConversationTurn] | list[dict],
    threshold: float = 0.8
) -> bool:
    """
    Light fuzzy check for repeated questions.
    Uses simple keyword overlap — good enough for research.

    Works with both ConversationTurn history and raw Bedrock dict format.
    """
    if not history:
        return False

    def _keywords(text: str) -> set[str]:
        return {w.lower() for w in text.split() if len(w) > 3}

    current_kw = _keywords(current)

    for turn in history:
        # Handle both ConversationTurn and dict formats
        if isinstance(turn, dict):
            # Bedrock format: {"role": "assistant", "content": [...]}
            if turn.get("role") != "assistant":
                continue
            content_list = turn.get("content", [])
        else:
            # ConversationTurn format
            if turn.role != "assistant":
                continue
            content_list = turn.content

        # Extract question from toolUse blocks
        for content in content_list:
            if isinstance(content, dict) and "toolUse" in content:
                tool_input = content["toolUse"].get("input", {})
                # Handle both dict and pydantic models
                if hasattr(tool_input, "get"):
                    prev_question = tool_input.get("question", "")
                else:
                    prev_question = getattr(tool_input, "question", "")
                if not prev_question:
                    continue

                prev_kw = _keywords(prev_question)
                if not current_kw or not prev_kw:
                    continue

                overlap = len(current_kw & prev_kw) / min(len(current_kw), len(prev_kw))
                if overlap >= threshold:
                    return True

    return False


def detect_stall(inter_token_latencies: list[float], threshold_ms: float = 2000.0) -> int:
    """Count stalls (gaps >= threshold_ms) in a sequence of inter-token latencies."""
    return sum(1 for lat in inter_token_latencies if lat >= threshold_ms)


def normalize_stop_reason(reason: str | None) -> str | None:
    """Normalize Bedrock stop reasons — reused from old metrics.py."""
    if not reason:
        return None
    sr = reason.lower()
    if sr in {"max_tokens", "maxtokens", "length", "max_length"}:
        return "max_tokens"
    elif sr in {"end_turn", "stop_sequence"}:
        return "end_turn"
    elif sr in {"error", "timeout"}:
        return "error"
    return sr

def count_words(text: str | None) -> int:
    """Count words in text — safe for None."""
    if not text:
        return 0
    return len(text.split())

def count_latency_ms(start: float | None) -> float :
    """return latency in ms (float)"""
    if not start:
        return 0.0
    return ((time.perf_counter() - start) * 1000)

def is_compliant(word_count: int, min_words: int = 10, max_words: int = 100) -> bool:
    """Check if word count is within compliant range."""
    return min_words <= word_count <= max_words