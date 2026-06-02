"""Tests for the v0.6 truncation pre-flight (DESIGN.md §7.1.7).

Both functions are pure and dependency-free, so these need no API client.
"""

from __future__ import annotations

from spp_scripts.inference import estimate_tokens, truncation_preflight


def test_estimate_tokens_ascii_quarter() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1  # 4 ascii / 4
    assert estimate_tokens("abcde") == 2  # ceil(5 / 4)
    assert estimate_tokens("a" * 40) == 10


def test_estimate_tokens_non_ascii_heavier() -> None:
    # Non-ASCII counts ~1 token/char, far heavier than ASCII of equal length.
    assert estimate_tokens("中文") == 2
    assert estimate_tokens("中" * 10) == 10
    assert estimate_tokens("中" * 10) > estimate_tokens("a" * 10)


def test_preflight_flags_only_over_budget() -> None:
    # budget = context_window - max_tokens = 10 - 4 = 6 (prompt is empty).
    rows = [("a", "x" * 40), ("b", "short")]  # a ~10 tok, b ~2 tok
    at_risk = truncation_preflight(rows, "", max_tokens=4, context_window=10)
    assert at_risk == [("a", 10)]


def test_preflight_includes_prompt_tokens() -> None:
    # A short input becomes at-risk once the shared prompt eats the budget.
    rows = [("a", "short")]  # input ~2 tok
    prompt = "p" * 40  # ~10 tok
    at_risk = truncation_preflight(rows, prompt, max_tokens=2, context_window=8)
    assert len(at_risk) == 1
    assert at_risk[0][0] == "a"


def test_preflight_sorted_worst_first() -> None:
    rows = [("small", "x" * 28), ("big", "x" * 80)]
    at_risk = truncation_preflight(rows, "", max_tokens=0, context_window=5)
    assert [rid for rid, _ in at_risk] == ["big", "small"]


def test_preflight_empty_when_all_fit() -> None:
    rows = [("a", "tiny"), ("b", "also small")]
    assert truncation_preflight(rows, "", max_tokens=10, context_window=100000) == []
