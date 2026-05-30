"""Tests for the per-field metric primitives (DESIGN §7.1.5)."""

from __future__ import annotations

import pytest

from spp_scripts._metrics import (
    MetricError,
    compute_field_metric,
    exact_match,
    set_f1,
    set_jaccard,
    within_tolerance,
)

# --------------------------------------------------------------------------- #
# per-row primitives (mirror the genuine spp annotation scorer)
# --------------------------------------------------------------------------- #


def test_exact_match_normalizes() -> None:
    assert exact_match("Billing", " billing ") == 1.0
    assert exact_match("A", "B") == 0.0
    assert exact_match(True, "true") == 1.0  # booleans normalize to strings


def test_set_jaccard_basics() -> None:
    assert set_jaccard(["a", "b"], ["a", "b"]) == 1.0
    assert set_jaccard(["a", "b"], ["a"]) == 0.5  # 1 / 2
    assert set_jaccard([], []) == 1.0  # both empty = agreement on "nothing"
    assert set_jaccard(["a"], []) == 0.0


def test_set_jaccard_parses_json_strings_and_accepted() -> None:
    # inference.py emits arrays as compact JSON strings.
    assert set_jaccard('["a","b"]', '["b","a"]') == 1.0
    # accepted maps a predicted value onto its gold alternative.
    assert set_jaccard(["minoxidil"], ["rogaine"], {"rogaine": "minoxidil"}) == 1.0


def test_set_f1() -> None:
    assert set_f1(["a", "b"], ["a", "b"]) == 1.0
    # g={a,b}, p={a}: 2*1/(2+1) = 0.666...
    assert set_f1(["a", "b"], ["a"]) == pytest.approx(2 / 3)
    assert set_f1([], []) == 1.0
    assert set_f1(["a"], []) == 0.0


def test_within_tolerance() -> None:
    assert within_tolerance(3, 3) == 1.0
    assert within_tolerance("3.0", "3.2", tol=0.5) == 1.0
    assert within_tolerance(3, 5, tol=1.0) == 0.0
    assert within_tolerance(3, "not a number") == 0.0


# --------------------------------------------------------------------------- #
# compute_field_metric dispatcher
# --------------------------------------------------------------------------- #


def test_field_metric_exact_match_is_mean() -> None:
    # 3 of 4 correct -> 0.75.
    yt = ["A", "B", "C", "D"]
    yp = ["A", "B", "C", "X"]
    assert compute_field_metric("exact_match", yt, yp) == 0.75


def test_field_metric_accuracy_matches_exact_match() -> None:
    yt = ["A", "B", "C", "D"]
    yp = ["A", "B", "C", "X"]
    assert compute_field_metric("accuracy", yt, yp) == 0.75


def test_field_metric_set_metrics_mean() -> None:
    yt = [["a", "b"], ["x"]]
    yp = [["a", "b"], []]  # row 1 perfect, row 2 empty-vs-nonempty = 0
    assert compute_field_metric("set_jaccard", yt, yp) == 0.5
    assert compute_field_metric("iou", yt, yp) == 0.5  # iou aliases set_jaccard


def test_field_metric_binary_f1_requires_positive_label() -> None:
    yt = ["yes", "no"]
    yp = ["yes", "no"]
    with pytest.raises(MetricError, match="positive_label"):
        compute_field_metric("f1", yt, yp)
    assert compute_field_metric(
        "f1", yt, yp, {"positive_label": "yes"}
    ) == pytest.approx(1.0)


def test_field_metric_macro_f1_and_balanced_accuracy() -> None:
    yt = ["a", "b", "c", "a"]
    yp = ["a", "b", "c", "a"]
    assert compute_field_metric("macro_f1", yt, yp) == pytest.approx(1.0)
    assert compute_field_metric("balanced_accuracy", yt, yp) == pytest.approx(1.0)


def test_field_metric_mae_rmse() -> None:
    yt = ["1", "2", "3"]
    yp = ["1", "2", "5"]  # errors 0, 0, 2
    assert compute_field_metric("mae", yt, yp) == pytest.approx(2 / 3)
    assert compute_field_metric("rmse", yt, yp) == pytest.approx((4 / 3) ** 0.5)


def test_field_metric_within_tolerance_mean() -> None:
    yt = ["1.0", "2.0"]
    yp = ["1.1", "9.0"]
    assert compute_field_metric("within_tolerance", yt, yp, {"tolerance": 0.2}) == 0.5


def test_field_metric_unsupported() -> None:
    with pytest.raises(MetricError, match="not supported"):
        compute_field_metric("kappa", ["a"], ["a"])


def test_field_metric_length_mismatch_and_empty() -> None:
    with pytest.raises(MetricError, match="same length"):
        compute_field_metric("exact_match", ["a", "b"], ["a"])
    with pytest.raises(MetricError, match="no rows"):
        compute_field_metric("exact_match", [], [])


def test_field_metric_mae_no_numeric_rows() -> None:
    with pytest.raises(MetricError, match="no numeric-parseable rows"):
        compute_field_metric("mae", ["x", "y"], ["a", "b"])
