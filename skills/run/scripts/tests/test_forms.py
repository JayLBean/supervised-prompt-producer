"""Tests for output-form reconstruction (one-vs-rest, gated-boolean)."""

from __future__ import annotations

import json

import pytest

from skills.run.scripts._forms import (
    FormError,
    constituent_keys,
    reconstruct_field,
)


def _as_list(encoded: str) -> list[str]:
    return json.loads(encoded)


# --- per_label_binary (one-vs-rest) ------------------------------------------


def test_per_label_binary_unions_truthy() -> None:
    form = {
        "type": "per_label_binary",
        "labels": {"tag_urgent": "urgent", "tag_vip": "vip", "tag_docs": "docs"},
    }
    parsed = {"tag_urgent": "true", "tag_vip": "false", "tag_docs": "true"}
    assert sorted(_as_list(reconstruct_field(form, parsed))) == ["docs", "urgent"]


def test_per_label_binary_all_false_is_empty() -> None:
    form = {"type": "per_label_binary", "labels": {"a": "a", "b": "b"}}
    assert _as_list(reconstruct_field(form, {"a": "false", "b": "no"})) == []


def test_per_label_binary_missing_key_is_negative() -> None:
    # An absent per-label key counts as "not present", not a crash.
    form = {"type": "per_label_binary", "labels": {"a": "a", "b": "b"}}
    assert _as_list(reconstruct_field(form, {"a": "yes"})) == ["a"]


def test_per_label_binary_requires_labels() -> None:
    with pytest.raises(FormError):
        reconstruct_field({"type": "per_label_binary"}, {})


# --- gated_single_select -----------------------------------------------------


def test_gated_single_select_open_gate_returns_sub() -> None:
    form = {"type": "gated_single_select", "gate": "has_issue", "sub_field": "issue"}
    parsed = {"has_issue": "true", "issue": "billing"}
    assert reconstruct_field(form, parsed) == "billing"


def test_gated_single_select_closed_gate_is_empty() -> None:
    form = {"type": "gated_single_select", "gate": "has_issue", "sub_field": "issue"}
    # Gate false → "not addressed" regardless of the (hallucinated) sub-field.
    parsed = {"has_issue": "false", "issue": "billing"}
    assert reconstruct_field(form, parsed) == ""


def test_gated_single_select_missing_gate_is_closed() -> None:
    form = {"type": "gated_single_select", "gate": "has_issue", "sub_field": "issue"}
    assert reconstruct_field(form, {"issue": "billing"}) == ""


# --- gated_per_label_binary --------------------------------------------------


def test_gated_per_label_binary_open_gate_unions() -> None:
    form = {
        "type": "gated_per_label_binary",
        "gate": "has_tags",
        "labels": {"t_a": "a", "t_b": "b"},
    }
    parsed = {"has_tags": "true", "t_a": "true", "t_b": "false"}
    assert _as_list(reconstruct_field(form, parsed)) == ["a"]


def test_gated_per_label_binary_closed_gate_is_empty() -> None:
    form = {
        "type": "gated_per_label_binary",
        "gate": "has_tags",
        "labels": {"t_a": "a", "t_b": "b"},
    }
    parsed = {"has_tags": "no", "t_a": "true", "t_b": "true"}
    assert _as_list(reconstruct_field(form, parsed)) == []


# --- errors and bookkeeping --------------------------------------------------


def test_unsupported_form_raises() -> None:
    with pytest.raises(FormError):
        reconstruct_field({"type": "chain_of_thought"}, {})


def test_constituent_keys_per_label() -> None:
    form = {"type": "per_label_binary", "labels": {"a": "a", "b": "b"}}
    assert sorted(constituent_keys(form)) == ["a", "b"]


def test_constituent_keys_gated() -> None:
    form = {"type": "gated_single_select", "gate": "g", "sub_field": "s"}
    assert sorted(constituent_keys(form)) == ["g", "s"]
