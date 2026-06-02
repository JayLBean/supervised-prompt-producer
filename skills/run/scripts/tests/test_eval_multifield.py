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


def _scored_fixture(tmp_path: Path) -> tuple[Path, Path, list[str], dict]:
    """Fixture where category scores 0.5 and tags (set_f1) scores 0.8333."""
    base, res, ids = _fixture(
        tmp_path,
        [
            _pred("r1", {"category": "Billing", "tags": '["a","b"]'}),
            _pred("r2", {"category": "Wrong", "tags": '["x","y"]'}),
        ],
    )
    fm = {"category": {"metric": "exact_match"}, "tags": {"metric": "set_f1"}}
    return base, res, ids, fm


def test_aggregate_macro_section(tmp_path: Path) -> None:
    base, res, ids, fm = _scored_fixture(tmp_path)
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(res, base, ids, fm, out)  # default macro
    assert e.aggregate is not None
    assert e.aggregate.strategy == "macro"
    expected = (0.5 + (1.0 + 2 / 3) / 2) / 2
    assert e.aggregate.value == pytest.approx(expected)
    assert e.primary_value == pytest.approx(expected)  # top-level == aggregate
    persisted = json.loads(out.read_text())
    assert persisted["aggregate"]["strategy"] == "macro"


def test_aggregate_weighted(tmp_path: Path) -> None:
    base, res, ids, fm = _scored_fixture(tmp_path)
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(
        res,
        base,
        ids,
        fm,
        out,
        aggregate={"strategy": "weighted", "weights": {"category": 3, "tags": 1}},
    )
    tags = (1.0 + 2 / 3) / 2
    assert e.aggregate is not None
    assert e.aggregate.value == pytest.approx((0.5 * 3 + tags * 1) / 4)


def test_aggregate_min(tmp_path: Path) -> None:
    base, res, ids, fm = _scored_fixture(tmp_path)
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(res, base, ids, fm, out, aggregate={"strategy": "min"})
    assert e.aggregate is not None
    assert e.aggregate.value == 0.5  # worst field (category)


# ---- v0.6 per-language slice (DESIGN.md §7.1.7) ---------------------------


def _ml_fixture(tmp_path: Path) -> tuple[Path, Path, list[str], dict]:
    """2 en + 2 es rows; category exact_match is 0.5 on en, 1.0 on es."""
    rows = [
        {"id": "r1", "category": "Billing", "tags": '["a","b"]', "language": "en"},
        {"id": "r2", "category": "Other", "tags": '["x"]', "language": "en"},
        {"id": "r3", "category": "Billing", "tags": '["a","b"]', "language": "es"},
        {"id": "r4", "category": "Other", "tags": '["x"]', "language": "es"},
    ]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)
    preds = [
        _pred("r1", {"category": "Billing", "tags": '["a","b"]'}),  # cat ✓
        _pred("r2", {"category": "Wrong", "tags": '["x"]'}),  # cat ✗ (en)
        _pred("r3", {"category": "Billing", "tags": '["a","b"]'}),  # cat ✓
        _pred("r4", {"category": "Other", "tags": '["x"]'}),  # cat ✓
    ]
    results = {
        "schema_version": "1",
        "model": "m",
        "prompt_path": "p",
        "prompt_sha256": "h",
        "predictions": preds,
        "summary": {
            "n_rows": 4,
            "n_parsed": 4,
            "n_parse_failures": 0,
            "total_tokens": 0,
            "total_latency_ms": 0,
            "wall_clock_ms": 0,
        },
    }
    res = tmp_path / "results.json"
    res.write_text(json.dumps(results))
    fm = {"category": {"metric": "exact_match"}, "tags": {"metric": "set_f1"}}
    return base, res, ["r1", "r2", "r3", "r4"], fm


def test_multifield_per_language_slice(tmp_path: Path) -> None:
    base, res, ids, fm = _ml_fixture(tmp_path)
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(res, base, ids, fm, out)  # macro
    assert set(e.per_language) == {"en", "es"}
    en = e.per_language["en"]
    assert en.n_rows == 2
    assert en.per_field["category"] == 0.5
    assert en.per_field["tags"] == 1.0
    assert en.primary_value == pytest.approx(0.75)  # macro of 0.5, 1.0
    assert e.per_language["es"].primary_value == 1.0
    # Round-trips through eval.json.
    persisted = json.loads(out.read_text())
    assert persisted["per_language"]["en"]["per_field"]["category"] == 0.5


def test_multifield_monolingual_empty_per_language(tmp_path: Path) -> None:
    base, res, ids, fm = _scored_fixture(tmp_path)  # no language column
    e = compute_eval_multifield(res, base, ids, fm, tmp_path / "eval.json")
    assert e.per_language == {}


def test_aggregate_refuses_error_family_mix(tmp_path: Path) -> None:
    base = tmp_path / "baseline.csv"
    pd.DataFrame(
        [
            {"id": "r1", "cat": "A", "price": "10"},
            {"id": "r2", "cat": "B", "price": "20"},
        ]
    ).to_csv(base, index=False)
    res = tmp_path / "results.json"
    res.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "model": "m",
                "prompt_path": "p",
                "prompt_sha256": "h",
                "predictions": [
                    _pred("r1", {"cat": "A", "price": "11"}),
                    _pred("r2", {"cat": "B", "price": "20"}),
                ],
                "summary": {
                    "n_rows": 2,
                    "n_parsed": 2,
                    "n_parse_failures": 0,
                    "total_tokens": 0,
                    "total_latency_ms": 0,
                    "wall_clock_ms": 0,
                },
            }
        )
    )
    with pytest.raises(EvalError, match="error-family"):
        compute_eval_multifield(
            res,
            base,
            ["r1", "r2"],
            {"cat": {"metric": "exact_match"}, "price": {"metric": "mae"}},
            tmp_path / "e.json",
        )


def test_floor_compliance_met_and_unmet(tmp_path: Path) -> None:
    base, res, ids, fm = _scored_fixture(tmp_path)  # category 0.5, tags 0.8333
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(
        res, base, ids, fm, out, floors={"category": 0.9, "tags": 0.5}
    )
    assert e.floor_compliance is not None
    assert e.floor_compliance["category"].status == "unmet"  # 0.5 < 0.9
    assert e.floor_compliance["category"].floor == 0.9
    assert e.floor_compliance["tags"].status == "met"  # 0.8333 >= 0.5
    persisted = json.loads(out.read_text())
    assert persisted["floor_compliance"]["category"]["status"] == "unmet"


def test_floor_compliance_not_specified_without_floors(tmp_path: Path) -> None:
    base, res, ids, fm = _scored_fixture(tmp_path)
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(res, base, ids, fm, out)
    assert e.floor_compliance is not None
    assert e.floor_compliance["category"].status == "not_specified"
    assert e.floor_compliance["category"].floor is None
    assert e.floor_compliance["tags"].status == "not_specified"


def test_floor_compliance_met_at_boundary(tmp_path: Path) -> None:
    base, res, ids, fm = _scored_fixture(tmp_path)
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(res, base, ids, fm, out, floors={"category": 0.5})
    assert e.floor_compliance is not None
    assert e.floor_compliance["category"].status == "met"  # 0.5 >= 0.5
    # tags has no floor specified.
    assert e.floor_compliance["tags"].status == "not_specified"
