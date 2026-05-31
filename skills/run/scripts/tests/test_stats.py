"""Tests for _stats.py — bootstrap CI on the test aggregate (DESIGN.md §7.1.4)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import pytest

from spp_scripts._stats import (
    StatsError,
    attach_aggregate_ci,
    attach_dev_test_gap_ci,
    bootstrap_aggregate_ci,
    bootstrap_gap_ci,
    bootstrap_multifield_aggregate_ci,
    main,
)
from spp_scripts.eval import compute_eval


def _make_eval(
    tmp_path: Path,
    ids: list[str],
    truths: list[str],
    preds: list[str],
    metric: str = "accuracy",
    metric_kwargs: dict[str, str] | None = None,
) -> Path:
    """Build a baseline + results pair, score it, return the eval.json path."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    rows = [
        {"id": i, "input": "x", "label": t} for i, t in zip(ids, truths, strict=True)
    ]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)
    results = {
        "schema_version": "1",
        "model": "m",
        "prompt_path": "p",
        "prompt_sha256": "h",
        "predictions": [
            {
                "row_id": i,
                "raw_response": p,
                "parsed_label": p,
                "parse_error": None,
                "latency_ms": 1,
                "tokens_used": 1,
            }
            for i, p in zip(ids, preds, strict=True)
        ],
        "summary": {
            "n_rows": len(ids),
            "n_parsed": len(ids),
            "n_parse_failures": 0,
            "total_tokens": len(ids),
            "total_latency_ms": len(ids),
            "wall_clock_ms": len(ids),
        },
    }
    res = tmp_path / "results.json"
    res.write_text(json.dumps(results))
    out = tmp_path / "eval.json"
    compute_eval(res, base, list(ids), metric, out, metric_kwargs=metric_kwargs or {})
    return out


def test_ci_brackets_the_point_estimate(tmp_path: Path) -> None:
    ids = [str(i) for i in range(10)]
    truths = ["A"] * 5 + ["B"] * 5
    # 8/10 correct -> accuracy 0.8 (rows 8, 9 wrong).
    preds = ["A"] * 5 + ["B"] * 3 + ["A", "A"]
    out = _make_eval(tmp_path, ids, truths, preds)

    ci = attach_aggregate_ci(out, n_resamples=500, seed=0, confidence=0.95)

    assert ci.metric == "accuracy"
    assert ci.point_estimate == pytest.approx(0.8)
    assert ci.n_rows == 10
    assert ci.n_resamples == 500
    assert ci.seed == 0
    assert ci.confidence == 0.95
    # A percentile bootstrap interval contains its point estimate and stays in range.
    assert ci.ci_low <= ci.point_estimate <= ci.ci_high
    assert 0.0 <= ci.ci_low <= ci.ci_high <= 1.0

    # Written back into the eval.json.
    persisted = json.loads(out.read_text())
    assert persisted["aggregate_ci"]["point_estimate"] == pytest.approx(0.8)
    assert persisted["aggregate_ci"]["n_resamples"] == 500


def test_bootstrap_is_deterministic_for_a_fixed_seed() -> None:
    y_true = ["A", "A", "B", "B", "A", "B", "A", "B"]
    y_pred = ["A", "B", "B", "B", "A", "A", "A", "B"]
    args = (y_true, y_pred, "accuracy", {}, ["A", "B"])

    a = bootstrap_aggregate_ci(*args, n_resamples=300, seed=7)
    b = bootstrap_aggregate_ci(*args, n_resamples=300, seed=7)
    assert (a.ci_low, a.ci_high, a.point_estimate) == (
        b.ci_low,
        b.ci_high,
        b.point_estimate,
    )


def test_f1_metric_recomputed_on_resamples(tmp_path: Path) -> None:
    ids = [str(i) for i in range(8)]
    truths = ["Relevant", "Relevant", "Relevant", "Relevant", "No", "No", "No", "No"]
    preds = ["Relevant", "Relevant", "Relevant", "No", "No", "No", "No", "Relevant"]
    out = _make_eval(
        tmp_path,
        ids,
        truths,
        preds,
        metric="f1",
        metric_kwargs={"positive_label": "Relevant"},
    )
    ci = attach_aggregate_ci(out, n_resamples=400, seed=1)
    # Point estimate matches the metric eval.py computed on the full sample.
    persisted = json.loads(out.read_text())
    assert ci.point_estimate == pytest.approx(persisted["primary_value"])
    assert 0.0 <= ci.ci_low <= ci.ci_high <= 1.0


def test_attach_requires_per_row(tmp_path: Path) -> None:
    out = _make_eval(tmp_path, ["a", "b"], ["A", "B"], ["A", "B"])
    data = json.loads(out.read_text())
    data["per_row"] = []  # simulate a legacy eval.json without the retained vector
    out.write_text(json.dumps(data))
    with pytest.raises(StatsError, match="no per_row vector"):
        attach_aggregate_ci(out, n_resamples=100)


def test_bootstrap_rejects_bad_arguments() -> None:
    args = (["A", "B"], ["A", "B"], "accuracy", {}, ["A", "B"])
    with pytest.raises(StatsError, match="confidence"):
        bootstrap_aggregate_ci(*args, confidence=1.5)
    with pytest.raises(StatsError, match="n_resamples"):
        bootstrap_aggregate_ci(*args, n_resamples=0)
    with pytest.raises(StatsError, match="no rows"):
        bootstrap_aggregate_ci([], [], "accuracy", {}, ["A", "B"])


def test_gap_ci_point_estimate_is_dev_minus_test() -> None:
    # dev accuracy 1.0, test accuracy 0.5 -> gap 0.5.
    dev_t, dev_p = ["A", "B", "A", "B"], ["A", "B", "A", "B"]
    test_t, test_p = ["A", "B", "A", "B"], ["A", "B", "B", "A"]
    ci = bootstrap_gap_ci(
        dev_t,
        dev_p,
        test_t,
        test_p,
        "accuracy",
        {},
        ["A", "B"],
        n_resamples=300,
        seed=3,
    )
    assert ci.point_estimate == pytest.approx(0.5)
    assert ci.ci_low <= ci.point_estimate <= ci.ci_high
    assert ci.n_rows == 4  # records the test-partition size

    # Deterministic for a fixed seed.
    again = bootstrap_gap_ci(
        dev_t,
        dev_p,
        test_t,
        test_p,
        "accuracy",
        {},
        ["A", "B"],
        n_resamples=300,
        seed=3,
    )
    assert (ci.ci_low, ci.ci_high) == (again.ci_low, again.ci_high)


def test_attach_dev_test_gap_ci_writes_to_test_eval(tmp_path: Path) -> None:
    dev = _make_eval(
        tmp_path / "dev",
        [str(i) for i in range(6)],
        ["A"] * 3 + ["B"] * 3,
        ["A"] * 3 + ["B"] * 3,
    )
    test = _make_eval(
        tmp_path / "test",
        [str(i) for i in range(6)],
        ["A"] * 3 + ["B"] * 3,
        ["A"] * 3 + ["B", "B", "A"],  # 5/6 correct
    )
    ci = attach_dev_test_gap_ci(dev, test, n_resamples=300, seed=0)
    # dev acc 1.0, test acc 5/6 -> gap ~0.1667.
    assert ci.point_estimate == pytest.approx(1.0 - 5 / 6)
    persisted = json.loads(test.read_text())
    assert persisted["dev_test_gap_ci"]["point_estimate"] == pytest.approx(1.0 - 5 / 6)
    # The aggregate CI field is untouched by the gap computation.
    assert persisted["aggregate_ci"] is None


def test_cli_finalize_path_k1(tmp_path: Path) -> None:
    """End-to-end fixture: the _stats CLI on a K=1 test + dev eval writes both
    intervals into the test eval — the shape /spp-finalize invokes."""
    ids = [str(i) for i in range(8)]
    truths = ["A"] * 4 + ["B"] * 4
    dev = _make_eval(tmp_path / "dev", ids, truths, truths)  # dev accuracy 1.0
    # test accuracy 6/8 = 0.75 (rows 6, 7 wrong) -> dev−test gap 0.25.
    test = _make_eval(tmp_path / "test", ids, truths, ["A"] * 4 + ["B", "B", "A", "A"])

    rc = main(
        [
            "--eval",
            str(test),
            "--dev-eval",
            str(dev),
            "--n-resamples",
            "200",
            "--seed",
            "0",
        ]
    )
    assert rc == 0

    persisted = json.loads(test.read_text())
    assert persisted["aggregate_ci"]["metric"] == "accuracy"
    assert persisted["aggregate_ci"]["point_estimate"] == pytest.approx(0.75)
    assert persisted["dev_test_gap_ci"]["point_estimate"] == pytest.approx(0.25)


def test_cli_reports_error_on_missing_per_row(tmp_path: Path) -> None:
    out = _make_eval(tmp_path, ["a", "b"], ["A", "B"], ["A", "B"])
    data = json.loads(out.read_text())
    data["per_row"] = []
    out.write_text(json.dumps(data))
    assert main(["--eval", str(out), "--n-resamples", "50"]) == 2


# --- multi-field aggregate bootstrap (v0.5 rider, DESIGN §7.1.6) --------------


def _mf_columns() -> dict[str, tuple[list[str], list[str]]]:
    """category (exact_match 0.75) + flag (f1 pos=yes, 2/3)."""
    return {
        "category": (["a", "b", "a", "c"], ["a", "b", "c", "c"]),
        "flag": (["yes", "no", "yes", "no"], ["yes", "no", "no", "no"]),
    }


_MF_METRICS = {
    "category": {"metric": "exact_match"},
    "flag": {"metric": "f1", "kwargs": {"positive_label": "yes"}},
}


def test_bootstrap_multifield_aggregate_point_matches_full_data() -> None:
    ci = bootstrap_multifield_aggregate_ci(
        _mf_columns(),
        _MF_METRICS,
        aggregate={"strategy": "macro"},
        n_resamples=300,
        seed=7,
    )
    assert ci.metric == "aggregate:macro"
    assert ci.point_estimate == pytest.approx((0.75 + 2 / 3) / 2)
    assert ci.ci_low <= ci.point_estimate <= ci.ci_high
    assert ci.n_rows == 4


def test_bootstrap_multifield_aggregate_min_strategy() -> None:
    ci = bootstrap_multifield_aggregate_ci(
        _mf_columns(),
        _MF_METRICS,
        aggregate={"strategy": "min"},
        n_resamples=300,
        seed=7,
    )
    assert ci.metric == "aggregate:min"
    assert ci.point_estimate == pytest.approx(2 / 3)  # worse field (flag)


def test_bootstrap_multifield_aggregate_seed_deterministic() -> None:
    a = bootstrap_multifield_aggregate_ci(
        _mf_columns(), _MF_METRICS, n_resamples=300, seed=7
    )
    b = bootstrap_multifield_aggregate_ci(
        _mf_columns(), _MF_METRICS, n_resamples=300, seed=7
    )
    assert a.ci_low == b.ci_low and a.ci_high == b.ci_high
    assert a.point_estimate == b.point_estimate
    assert a.metric == "aggregate:macro"  # default strategy


def test_bootstrap_multifield_aggregate_perfect_is_degenerate() -> None:
    cols = {"f": (["a", "b", "a"], ["a", "b", "a"])}
    ci = bootstrap_multifield_aggregate_ci(
        cols, {"f": {"metric": "exact_match"}}, n_resamples=100, seed=1
    )
    assert ci.point_estimate == 1.0 and ci.ci_low == 1.0 and ci.ci_high == 1.0


def test_bootstrap_multifield_aggregate_unequal_rows_raise() -> None:
    cols = {"a": (["x", "y"], ["x", "y"]), "b": (["x"], ["x"])}
    with pytest.raises(StatsError, match="unequal row counts"):
        bootstrap_multifield_aggregate_ci(
            cols,
            {"a": {"metric": "exact_match"}, "b": {"metric": "exact_match"}},
            n_resamples=10,
            seed=1,
        )


def test_bootstrap_multifield_aggregate_empty_raises() -> None:
    with pytest.raises(StatsError, match="no fields"):
        bootstrap_multifield_aggregate_ci({}, {}, n_resamples=10, seed=1)
