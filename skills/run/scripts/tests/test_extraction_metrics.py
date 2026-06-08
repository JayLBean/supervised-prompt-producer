"""Tests for the extraction metric primitives (DESIGN §7.1.11).

These cover the variable-cardinality alignment metrics added for the v0.10
extraction mode: text-alignment precision/recall/F1, offset-overlap span F1,
and the deterministic redaction leakage metric. Every metric is a pure
function of (prediction, gold) — no model in the scoring path (invariant #13).
"""

from __future__ import annotations

import json

import pytest

from spp_scripts._metrics import (
    EXTRACTION_METRICS,
    SUPPORTED_FIELD_METRICS,
    MetricError,
    compute_field_metric,
    extraction_f1,
    extraction_precision,
    extraction_recall,
    leakage,
    span_f1,
)

# --------------------------------------------------------------------------- #
# text-alignment extraction (offset-agnostic)
# --------------------------------------------------------------------------- #


def test_extraction_f1_perfect_and_empty_both() -> None:
    gold = [{"text": "Acme", "type": "org"}, {"text": "Drill", "type": "product"}]
    assert extraction_f1(gold, list(gold)) == 1.0
    # empty-both is a correct answer ("nothing to extract") → 1.0
    assert extraction_f1([], []) == 1.0
    assert extraction_f1(None, None) == 1.0


def test_extraction_f1_one_empty_is_zero() -> None:
    gold = [{"text": "Acme", "type": "org"}]
    assert extraction_f1(gold, []) == 0.0
    assert extraction_f1([], gold) == 0.0


def test_extraction_precision_recall_asymmetry() -> None:
    # gold has 2 items; pred has 1 correct + 1 spurious.
    gold = [{"text": "a"}, {"text": "b"}]
    pred = [{"text": "a"}, {"text": "zzz"}]
    assert extraction_precision(gold, pred) == 0.5  # 1 of 2 predicted correct
    assert extraction_recall(gold, pred) == 0.5  # 1 of 2 gold found
    assert extraction_f1(gold, pred) == pytest.approx(0.5)


def test_extraction_f1_normalizes_text() -> None:
    # strip + case-fold: a correct mention is not penalized on casing.
    assert extraction_f1([{"text": "Acme Corp"}], [{"text": " acme corp "}]) == 1.0


def test_extraction_type_aware_toggle() -> None:
    gold = [{"text": "acme", "type": "org"}]
    pred_wrong_type = [{"text": "acme", "type": "product"}]
    # match_type=True (default): type must agree → no match.
    assert extraction_f1(gold, pred_wrong_type) == 0.0
    # match_type=False: type ignored → text match suffices.
    assert extraction_f1(gold, pred_wrong_type, False) == 1.0


def test_extraction_gold_without_type_does_not_constrain() -> None:
    # gold item carries no type; a typed prediction still matches on text.
    assert extraction_f1([{"text": "acme"}], [{"text": "acme", "type": "org"}]) == 1.0


def test_extraction_greedy_one_to_one() -> None:
    # one gold item, two identical predictions → exactly one true positive.
    gold = [{"text": "acme"}]
    pred = [{"text": "acme"}, {"text": "acme"}]
    assert extraction_precision(gold, pred) == 0.5  # tp=1, n_pred=2
    assert extraction_recall(gold, pred) == 1.0  # tp=1, n_gold=1


def test_extraction_bare_string_items() -> None:
    # text-only spans expressed as bare strings.
    assert extraction_f1(["apple", "pear"], ["pear", "apple"]) == 1.0


def test_extraction_json_string_input() -> None:
    # inference.py emits arrays as compact JSON strings.
    gold = json.dumps([{"text": "acme", "type": "org"}])
    pred = json.dumps([{"text": "acme", "type": "org"}])
    assert extraction_f1(gold, pred) == 1.0


# --------------------------------------------------------------------------- #
# span alignment (offset overlap)
# --------------------------------------------------------------------------- #


def _span(text: str, type_: str, start: int, end: int) -> dict[str, object]:
    return {"text": text, "type": type_, "start": start, "end": end}


def test_span_f1_exact_offsets() -> None:
    g = [_span("acme", "org", 0, 4)]
    assert span_f1(g, [dict(g[0])]) == 1.0


def test_span_f1_iou_threshold_boundary() -> None:
    gold = [_span("acme corp", "org", 0, 9)]
    # predicted span [0,5) overlaps gold [0,9): inter=5, union=9 → IoU≈0.556.
    pred = [_span("acme ", "org", 0, 5)]
    assert span_f1(gold, pred, True, 0.5) == 1.0  # 0.556 >= 0.5 → match
    assert span_f1(gold, pred, True, 0.6) == 0.0  # 0.556 < 0.6 → no match


def test_span_f1_type_must_agree_when_requested() -> None:
    gold = [_span("acme", "org", 0, 4)]
    pred = [_span("acme", "product", 0, 4)]
    assert span_f1(gold, pred, True) == 0.0
    assert span_f1(gold, pred, False) == 1.0


def test_span_f1_empty_both() -> None:
    assert span_f1([], []) == 1.0


def test_span_f1_requires_gold_offsets() -> None:
    # gold item lacks start/end → configuration error, not a silent zero.
    with pytest.raises(MetricError, match="character offsets"):
        span_f1([{"text": "acme", "type": "org"}], [{"text": "acme"}])


def test_span_f1_pred_without_offsets_does_not_match() -> None:
    gold = [_span("acme", "org", 0, 4)]
    # pred has no offsets → cannot overlap → recall 0 → F1 0 (no error).
    assert span_f1(gold, [{"text": "acme", "type": "org"}]) == 0.0


# --------------------------------------------------------------------------- #
# leakage (deterministic redaction; spp-ex Module 1)
# --------------------------------------------------------------------------- #


def test_leakage_nothing_leaked() -> None:
    # forbidden tokens absent from the rewritten text → 1.0.
    assert (
        leakage(["John Smith", "acme@example.com"], "Please draft a polite email.")
        == 1.0
    )


def test_leakage_all_leaked() -> None:
    assert leakage(["secret"], "the secret is out") == 0.0


def test_leakage_partial() -> None:
    # one of two forbidden tokens survives → 1 - 1/2.
    assert leakage(["alice", "bob"], "hello alice") == pytest.approx(0.5)


def test_leakage_no_forbidden_is_one() -> None:
    assert leakage([], "anything") == 1.0


def test_leakage_case_insensitive() -> None:
    assert leakage(["Alice"], "hello alice") == 0.0


# --------------------------------------------------------------------------- #
# dispatch through compute_field_metric (the per-field scorer entry point)
# --------------------------------------------------------------------------- #


def test_extraction_metrics_registered() -> None:
    expected = {
        "extraction_f1",
        "extraction_precision",
        "extraction_recall",
        "span_f1",
        "leakage",
    }
    assert expected <= SUPPORTED_FIELD_METRICS
    assert expected == set(EXTRACTION_METRICS)


def test_compute_field_metric_extraction_f1_means_across_rows() -> None:
    # row 1 perfect (F1=1.0); row 2 finds 1 of 2 gold with 1 prediction
    # (tp=1, gold=2, pred=1 → F1 = 2/3). Mean = (1 + 2/3) / 2 = 5/6.
    y_true = [[{"text": "a"}], [{"text": "a"}, {"text": "b"}]]
    y_pred = [[{"text": "a"}], [{"text": "a"}]]
    assert compute_field_metric("extraction_f1", y_true, y_pred) == pytest.approx(5 / 6)


def test_compute_field_metric_span_f1_threshold_kwarg() -> None:
    y_true = [[_span("acme corp", "org", 0, 9)]]
    y_pred = [[_span("acme ", "org", 0, 5)]]  # IoU ≈ 0.556
    assert (
        compute_field_metric("span_f1", y_true, y_pred, {"iou_threshold": 0.5}) == 1.0
    )
    assert (
        compute_field_metric("span_f1", y_true, y_pred, {"iou_threshold": 0.6}) == 0.0
    )


def test_compute_field_metric_match_type_kwarg() -> None:
    y_true = [[{"text": "acme", "type": "org"}]]
    y_pred = [[{"text": "acme", "type": "product"}]]
    assert compute_field_metric("extraction_f1", y_true, y_pred) == 0.0
    assert (
        compute_field_metric("extraction_f1", y_true, y_pred, {"match_type": False})
        == 1.0
    )


def test_compute_field_metric_leakage() -> None:
    y_true = [["alice", "bob"], ["x"]]
    y_pred = ["hello alice", "clean"]  # row1: 1/2 leaked → 0.5; row2: 0 → 1.0
    assert compute_field_metric("leakage", y_true, y_pred) == pytest.approx(0.75)


def test_compute_field_metric_extraction_precision_recall_dispatch() -> None:
    # exercise the precision/recall branches through compute_field_metric,
    # not just the functions directly. One gold of two found, one spurious
    # prediction: tp=1, n_gold=2, n_pred=2 → precision 0.5, recall 0.5.
    y_true = [[{"text": "a"}, {"text": "b"}]]
    y_pred = [[{"text": "a"}, {"text": "zzz"}]]
    assert compute_field_metric("extraction_precision", y_true, y_pred) == 0.5
    assert compute_field_metric("extraction_recall", y_true, y_pred) == 0.5
