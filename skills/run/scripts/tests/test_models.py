"""Tests for the model->family resolver and the cross-family gate.

The gate is the load-bearing lock of the v0.7 label panel (DESIGN.md
§7.1.8): it must hard-block a same-family panel, must never guess an
unknown model, and a recognized model must classify itself regardless of
any declared family.
"""

from __future__ import annotations

import pytest

from spp_scripts._models import (
    SameFamilyError,
    UnknownModelFamilyError,
    assert_cross_family,
    resolve_family,
)


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("claude-opus-4-8", "anthropic"),
        ("claude-3-5-sonnet-20241022", "anthropic"),
        ("gpt-4o", "openai"),
        ("gpt-4.1-mini", "openai"),
        ("o3-mini", "openai"),
        ("gemini-1.5-pro", "google"),
        ("gemma-2-9b", "google"),
        ("llama-3.1-70b", "meta"),
        ("mistral-large", "mistral"),
        ("mixtral-8x7b", "mistral"),
        ("command-r-plus", "cohere"),
        ("deepseek-chat", "deepseek"),
        ("grok-2", "xai"),
        ("qwen2.5-72b", "qwen"),
    ],
)
def test_resolve_known_models(model: str, expected: str) -> None:
    assert resolve_family(model) == expected


def test_resolution_is_case_insensitive_and_trims() -> None:
    assert resolve_family("  GPT-4o  ") == "openai"
    assert resolve_family("Claude-Opus-4-8") == "anthropic"


def test_recognized_match_wins_over_declared_family() -> None:
    # A human cannot relabel a known model to slip past the gate.
    assert resolve_family("claude-opus-4-8", declared_family="openai") == "anthropic"


def test_unknown_model_requires_declared_family() -> None:
    with pytest.raises(UnknownModelFamilyError):
        resolve_family("acme-llm-v9")


def test_unknown_model_uses_declared_family_fallback() -> None:
    assert resolve_family("acme-llm-v9", declared_family="OpenAI") == "openai"


def test_empty_declared_family_does_not_count() -> None:
    with pytest.raises(UnknownModelFamilyError):
        resolve_family("acme-llm-v9", declared_family="   ")


def test_gate_blocks_same_family_claude() -> None:
    with pytest.raises(SameFamilyError):
        assert_cross_family("claude-opus-4-8")


def test_gate_blocks_declared_anthropic_unknown_model() -> None:
    with pytest.raises(SameFamilyError):
        assert_cross_family("acme-llm-v9", declared_family="anthropic")


def test_gate_passes_cross_family_and_returns_family() -> None:
    assert assert_cross_family("gpt-4o") == "openai"
    assert assert_cross_family("gemini-1.5-pro") == "google"


def test_gate_unknown_model_no_declaration_raises() -> None:
    with pytest.raises(UnknownModelFamilyError):
        assert_cross_family("acme-llm-v9")


def test_custom_judge_family_gate() -> None:
    # If the panel were ever a non-Anthropic family, the gate would block
    # that family instead. A Claude production model then passes.
    assert assert_cross_family("claude-opus-4-8", judge_family="openai") == "anthropic"
    with pytest.raises(SameFamilyError):
        assert_cross_family("gpt-4o", judge_family="openai")
