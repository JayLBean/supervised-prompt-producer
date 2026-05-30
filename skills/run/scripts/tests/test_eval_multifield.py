"""Tests for the K>1 multi-field scoring path in eval.py (DESIGN §7.1.5)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spp_scripts.eval import EvalError, compute_eval_multifield


def _fixture(tmp_path: Path, predictions: list[dict]) -> tuple[Path, Path, list[str]]:
    """Baseline with a single_select `category` and a multi_select `tags` field."""
    rows = [
        {"id": "r1", "category": "Billing", "tags": '["a","b"]'},
        {"id": "r2", "category": "Other", "tags": '["x"]'},
    ]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)
    results = {
        "schema_version": "1",
        "model": "m",
        "prompt_path": "p",
        "prompt_sha256": "h",
        "predictions": predictions,
        "summary": {
            "n_rows": len(predictions),
            "n_parsed": len(predictions),
            "n_parse_failures": 0,
            "total_tokens": 0,
            "total_latency_ms": 0,
            "wall_clock_ms": 0,
        },
    }
    res = tmp_path / "results.json"
    res.write_text(json.dumps(results))
    return base, res, ["r1", "r2"]


def _pred(row_id: str, fields: dict[str, str | None]) -> dict:
    return {
        "row_id": row_id,
        "raw_response": "{}",
        "parsed_label": None,
        "parse_error": None,
        "parsed_fields": fields,
        "field_parse_errors": {},
        "latency_ms": 1,
        "tokens_used": 1,
    }


def test_multifield_per_field_and_provisional_aggregate(tmp_path: Path) -> None:
    base, res, ids = _fixture(
        tmp_path,
        [
            _pred("r1", {"category": "Billing", "tags": '["a","b"]'}),  # cat 1, tags 1
            _pred("r2", {"category": "Wrong", "tags": '["x","y"]'}),  # cat 0, tags 2/3
        ],
    )
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(
        res,
        base,
        ids,
        {"category": {"metric": "exact_match"}, "tags": {"metric": "set_f1"}},
        out,
    )
    assert e.metric == "multi_field"
    assert e.per_field is not None
    assert e.per_field["category"].primary_value == 0.5  # (1 + 0) / 2
    assert e.per_field["tags"].primary_value == pytest.approx((1.0 + 2 / 3) / 2)
    # Provisional aggregate is the unweighted mean of the two field values.
    assert e.primary_value == pytest.approx((0.5 + (1.0 + 2 / 3) / 2) / 2)

    persisted = json.loads(out.read_text())
    assert persisted["per_field"]["category"]["metric"] == "exact_match"


def test_multifield_missing_prediction_field_counts_as_failure(tmp_path: Path) -> None:
    base, res, ids = _fixture(
        tmp_path,
        [
            _pred("r1", {"category": "Billing", "tags": '["a","b"]'}),
            _pred("r2", {"category": "Other"}),  # tags missing -> "" -> mismatch
        ],
    )
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(
        res,
        base,
        ids,
        {"category": {"metric": "exact_match"}, "tags": {"metric": "set_f1"}},
        out,
    )
    assert e.per_field is not None
    assert e.per_field["category"].primary_value == 1.0  # both categories correct
    # r2 tags absent -> scored 0; r1 tags perfect -> mean 0.5.
    assert e.per_field["tags"].primary_value == 0.5
    assert e.per_field["tags"].n_parse_failures == 1


def test_multifield_missing_gold_column(tmp_path: Path) -> None:
    base, res, ids = _fixture(
        tmp_path,
        [_pred("r1", {"category": "Billing"}), _pred("r2", {"category": "Other"})],
    )
    with pytest.raises(EvalError, match="missing gold column"):
        compute_eval_multifield(
            res,
            base,
            ids,
            {"nonexistent": {"metric": "exact_match"}},
            tmp_path / "e.json",
        )


def test_multifield_unsupported_metric_wrapped(tmp_path: Path) -> None:
    base, res, ids = _fixture(
        tmp_path,
        [_pred("r1", {"category": "Billing"}), _pred("r2", {"category": "Other"})],
    )
    with pytest.raises(EvalError, match="not supported"):
        compute_eval_multifield(
            res, base, ids, {"category": {"metric": "kappa"}}, tmp_path / "e.json"
        )


def test_multifield_empty_field_metrics(tmp_path: Path) -> None:
    base, res, ids = _fixture(
        tmp_path,
        [_pred("r1", {"category": "Billing"}), _pred("r2", {"category": "Other"})],
    )
    with pytest.raises(EvalError, match="field_metrics is empty"):
        compute_eval_multifield(res, base, ids, {}, tmp_path / "e.json")
