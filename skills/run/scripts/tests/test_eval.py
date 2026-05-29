"""Smoke tests for eval.py."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spp_scripts.eval import EvalError, compute_eval


def _fixture(tmp_path: Path) -> tuple[Path, Path, list[str]]:
    """Synthetic baseline + results with known accuracy/F1."""
    rows = [
        {"id": "a", "input": "x", "label": "Relevant"},
        {"id": "b", "input": "x", "label": "Relevant"},
        {"id": "c", "input": "x", "label": "Not Relevant"},
        {"id": "d", "input": "x", "label": "Not Relevant"},
    ]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)

    # Predictions: 3 correct, 1 wrong (a, b, d correct; c wrong).
    results = {
        "schema_version": "1",
        "model": "test",
        "prompt_path": "p",
        "prompt_sha256": "h",
        "predictions": [
            {
                "row_id": "a",
                "raw_response": "Relevant",
                "parsed_label": "Relevant",
                "parse_error": None,
                "latency_ms": 1,
                "tokens_used": 10,
            },
            {
                "row_id": "b",
                "raw_response": "Relevant",
                "parsed_label": "Relevant",
                "parse_error": None,
                "latency_ms": 1,
                "tokens_used": 10,
            },
            {
                "row_id": "c",
                "raw_response": "Relevant",
                "parsed_label": "Relevant",
                "parse_error": None,
                "latency_ms": 1,
                "tokens_used": 10,
            },
            {
                "row_id": "d",
                "raw_response": "Not Relevant",
                "parsed_label": "Not Relevant",
                "parse_error": None,
                "latency_ms": 1,
                "tokens_used": 10,
            },
        ],
        "summary": {
            "n_rows": 4,
            "n_parsed": 4,
            "n_parse_failures": 0,
            "total_tokens": 40,
            "total_latency_ms": 4,
            "wall_clock_ms": 4,
        },
    }
    res = tmp_path / "results.json"
    res.write_text(json.dumps(results))
    return base, res, ["a", "b", "c", "d"]


def test_eval_accuracy(tmp_path: Path) -> None:
    base, res, ids = _fixture(tmp_path)
    out = tmp_path / "eval.json"
    e = compute_eval(res, base, ids, "accuracy", out)
    assert e.primary_value == 0.75
    assert e.n_rows_evaluated == 4
    assert e.n_parse_failures_in_input == 0


def test_eval_binary_f1(tmp_path: Path) -> None:
    base, res, ids = _fixture(tmp_path)
    out = tmp_path / "eval.json"
    e = compute_eval(
        res,
        base,
        ids,
        "f1",
        out,
        metric_kwargs={"positive_label": "Relevant"},
    )
    # Predicted Relevant 3 times; truth 2 of them. TP=2, FP=1, FN=0.
    # precision = 2/3, recall = 1.0, f1 = 2 * (2/3) * 1 / (2/3 + 1) = 0.8.
    assert e.primary_value == pytest.approx(0.8)


def test_eval_parse_failure_counts_as_misprediction(tmp_path: Path) -> None:
    base, res, ids = _fixture(tmp_path)
    # Mutate one prediction to be a parse failure.
    data = json.loads(res.read_text())
    data["predictions"][0]["parsed_label"] = None
    data["predictions"][0]["parse_error"] = "empty"
    res.write_text(json.dumps(data))

    out = tmp_path / "eval.json"
    e = compute_eval(res, base, ids, "accuracy", out)
    # Now a is misprediction (parse failure); accuracy = 2/4 = 0.5.
    assert e.primary_value == 0.5
    assert e.n_parse_failures_in_input == 1
    assert "__PARSE_FAILURE__" in e.labels


def test_eval_per_row_retained(tmp_path: Path) -> None:
    base, res, ids = _fixture(tmp_path)
    out = tmp_path / "eval.json"
    e = compute_eval(res, base, ids, "accuracy", out)

    # One PerRowScore per evaluated row, in row_ids order.
    assert [r.row_id for r in e.per_row] == ids
    by_id = {r.row_id: r for r in e.per_row}
    # a, b, d correct; c wrong (predicted Relevant, truth Not Relevant).
    assert by_id["a"].correct is True
    assert by_id["d"].correct is True
    assert by_id["c"].correct is False
    assert by_id["c"].y_true == "Not Relevant"
    assert by_id["c"].y_pred == "Relevant"

    # Persisted to disk in the same shape.
    persisted = json.loads(out.read_text())
    assert [r["row_id"] for r in persisted["per_row"]] == ids
    assert persisted["per_row"][2]["correct"] is False


def test_eval_per_row_parse_failure_marked(tmp_path: Path) -> None:
    base, res, ids = _fixture(tmp_path)
    data = json.loads(res.read_text())
    data["predictions"][0]["parsed_label"] = None
    data["predictions"][0]["parse_error"] = "empty"
    res.write_text(json.dumps(data))

    out = tmp_path / "eval.json"
    e = compute_eval(res, base, ids, "accuracy", out)
    by_id = {r.row_id: r for r in e.per_row}
    assert by_id["a"].y_pred == "__PARSE_FAILURE__"
    assert by_id["a"].correct is False


def test_eval_unknown_metric(tmp_path: Path) -> None:
    base, res, ids = _fixture(tmp_path)
    with pytest.raises(EvalError, match="not supported"):
        compute_eval(res, base, ids, "kappa", tmp_path / "e.json")


def test_eval_missing_row_ids(tmp_path: Path) -> None:
    base, res, _ = _fixture(tmp_path)
    with pytest.raises(EvalError, match="not present in results"):
        compute_eval(res, base, ["a", "b", "missing"], "accuracy", tmp_path / "e.json")
