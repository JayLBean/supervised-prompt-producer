"""End-to-end extraction scoring through compute_eval_multifield (DESIGN §7.1.11).

Extraction fields carry a JSON-encoded item array in both the gold cell and the
prediction (inference.py's _parse_structured JSON-encodes list/object values),
and _metrics parses either a JSON string or a real list — so the existing K>1
scoring path scores extraction with no special-casing beyond the gold_column
override that the leakage metric needs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spp_scripts.eval import EvalError, compute_eval_multifield


def _results(predictions: list[dict]) -> dict:
    return {
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


def _arr(items: list[dict]) -> str:
    # Mirror inference.py: list values are JSON-encoded for stable scoring.
    return json.dumps(items, separators=(",", ":"), sort_keys=True)


def test_extraction_f1_end_to_end(tmp_path: Path) -> None:
    # Gold column `entities` holds JSON item arrays; predictions hold the same.
    rows = [
        {"id": "r1", "entities": _arr([{"text": "Acme", "type": "org"}])},
        {
            "id": "r2",
            "entities": _arr(
                [{"text": "Acme", "type": "org"}, {"text": "Drill", "type": "product"}]
            ),
        },
    ]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)
    res = tmp_path / "results.json"
    res.write_text(
        json.dumps(
            _results(
                [
                    # r1 perfect (F1=1.0); r2 finds 1 of 2 with 1 pred (F1=2/3).
                    _pred("r1", {"entities": _arr([{"text": "Acme", "type": "org"}])}),
                    _pred("r2", {"entities": _arr([{"text": "Acme", "type": "org"}])}),
                ]
            )
        )
    )
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(
        res, base, ["r1", "r2"], {"entities": {"metric": "extraction_f1"}}, out
    )
    assert e.per_field is not None
    assert e.per_field["entities"].primary_value == pytest.approx((1.0 + 2 / 3) / 2)
    assert e.per_field["entities"].n_parse_failures == 0


def test_span_f1_end_to_end_with_threshold(tmp_path: Path) -> None:
    rows = [
        {
            "id": "r1",
            "spans": _arr([{"text": "acme corp", "type": "org", "start": 0, "end": 9}]),
        },
    ]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)
    res = tmp_path / "results.json"
    res.write_text(
        json.dumps(
            _results(
                [  # predicted [0,5) vs gold [0,9): IoU = 5/9 ≈ 0.556
                    _pred(
                        "r1",
                        {
                            "spans": _arr(
                                [{"text": "acme ", "type": "org", "start": 0, "end": 5}]
                            )
                        },
                    ),
                ]
            )
        )
    )
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(
        res,
        base,
        ["r1"],
        {"spans": {"metric": "span_f1", "kwargs": {"iou_threshold": 0.5}}},
        out,
    )
    assert e.per_field is not None
    assert e.per_field["spans"].primary_value == 1.0  # 0.556 >= 0.5 → match


def test_leakage_uses_gold_column_override(tmp_path: Path) -> None:
    # The model predicts a rewritten text in `llm_request`; gold (forbidden
    # tokens) lives in a separate `pii_units` column. gold_column wires it up.
    rows = [
        {
            "id": "r1",
            "pii_units": _arr(["Alice", "acme@x.com"]),
            "llm_request": "ignored",
        },
        {"id": "r2", "pii_units": _arr(["Bob"]), "llm_request": "ignored"},
    ]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)
    res = tmp_path / "results.json"
    res.write_text(
        json.dumps(
            _results(
                [
                    # r1: "alice" leaks, email does not → 1 - 1/2 = 0.5
                    _pred("r1", {"llm_request": "draft an email for alice please"}),
                    # r2: clean → 1.0
                    _pred("r2", {"llm_request": "draft a polite note"}),
                ]
            )
        )
    )
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(
        res,
        base,
        ["r1", "r2"],
        {"llm_request": {"metric": "leakage", "gold_column": "pii_units"}},
        out,
    )
    assert e.per_field is not None
    assert e.per_field["llm_request"].primary_value == pytest.approx((0.5 + 1.0) / 2)


def test_extraction_human_shaped_gold_json_scores(tmp_path: Path) -> None:
    # Gold is human-authored in baseline.csv: unsorted keys, spaces — NOT the
    # runner's compact sort_keys form. _as_items reads items by key name, so the
    # encoding difference must not affect scoring (regression guard for the
    # key-based-parsing guarantee). Pred is the runner's compact form.
    human_gold = '[{"type": "org", "text": "Acme",  "end": 4, "start": 0}]'
    rows = [{"id": "r1", "entities": human_gold}]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)
    res = tmp_path / "results.json"
    res.write_text(
        json.dumps(
            _results(
                [
                    _pred(
                        "r1",
                        {
                            "entities": _arr(
                                [{"text": "Acme", "type": "org", "start": 0, "end": 4}]
                            )
                        },
                    )
                ]
            )
        )
    )
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(
        res, base, ["r1"], {"entities": {"metric": "span_f1"}}, out
    )
    assert e.per_field is not None
    assert e.per_field["entities"].primary_value == 1.0


def test_missing_gold_column_raises(tmp_path: Path) -> None:
    rows = [{"id": "r1", "entities": _arr([{"text": "a"}])}]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)
    res = tmp_path / "results.json"
    res.write_text(json.dumps(_results([_pred("r1", {"out": _arr([])})])))
    out = tmp_path / "eval.json"
    with pytest.raises(EvalError, match="missing gold column 'nope'"):
        compute_eval_multifield(
            res,
            base,
            ["r1"],
            {"out": {"metric": "extraction_f1", "gold_column": "nope"}},
            out,
        )


def test_extraction_empty_array_is_valid_not_failure(tmp_path: Path) -> None:
    # A correct "nothing to extract" row: gold [] and pred [] → F1 1.0, not a
    # parse failure (an empty array parses; only a missing/null field fails).
    rows = [{"id": "r1", "entities": _arr([])}]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)
    res = tmp_path / "results.json"
    res.write_text(json.dumps(_results([_pred("r1", {"entities": _arr([])})])))
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(
        res, base, ["r1"], {"entities": {"metric": "extraction_f1"}}, out
    )
    assert e.per_field is not None
    assert e.per_field["entities"].primary_value == 1.0
    assert e.per_field["entities"].n_parse_failures == 0
