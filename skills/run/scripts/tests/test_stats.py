"""Tests for _stats.py — bootstrap CI on the test aggregate (DESIGN.md §7.1.4)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import pytest

from spp_scripts._stats import (
    StatsError,
    attach_aggregate_ci,
    bootstrap_aggregate_ci,
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
