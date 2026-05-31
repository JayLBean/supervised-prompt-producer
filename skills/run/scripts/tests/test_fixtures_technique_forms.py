"""End-to-end fixture: a suggested→adopted technique runs through the K>1 runner
(DESIGN §7.1.6 bucket 7).

Models the payoff of the full v0.5 path: the user adopted one-vs-rest on a
multi-select field and gated-boolean on a single-select field (a `plan.md` /
OUTPUT_SCHEMA revision), so the model now emits each logical field across several
constituent keys. These tests build a synthetic `results.json` whose
`parsed_fields` carry the constituent keys, point `field_metrics` at each field
with a `"form"` block, and run the real `compute_eval_multifield` — proving an
adopted technique scores end-to-end without any network/model call, the same way
`test_examples_multifield` proves the plain multi-field configs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spp_scripts.eval import compute_eval_multifield


def _pred(row_id: str, fields: dict[str, str]) -> dict:
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


def _fixture(tmp_path: Path, predictions: list[dict]) -> tuple[Path, Path, list[str]]:
    """Baseline with a one-vs-rest `tags` field and a gated `status` field.

    Gold `tags` is a JSON list (the logical multi-select); gold `status` is a
    single select. Predictions arrive as the *constituent* keys an adopted form
    emits (per-label booleans; an is-addressed gate plus a sub-field).
    """
    rows = [
        {"id": "r1", "tags": '["a","b"]', "status": "open"},
        {"id": "r2", "tags": '["c"]', "status": "closed"},
        {"id": "r3", "tags": "[]", "status": "open"},
    ]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)
    results = {
        "schema_version": "1",
        "model": "fixture",
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
    return base, res, ["r1", "r2", "r3"]


# field_metrics with adopted-form blocks: tags via one-vs-rest, status via gate.
_FIELD_METRICS = {
    "tags": {
        "metric": "set_f1",
        "form": {
            "type": "per_label_binary",
            "labels": {"tag_a": "a", "tag_b": "b", "tag_c": "c"},
        },
    },
    "status": {
        "metric": "exact_match",
        "form": {
            "type": "gated_single_select",
            "gate": "has_status",
            "sub_field": "status_kind",
        },
    },
}


def test_adopted_forms_score_end_to_end(tmp_path: Path) -> None:
    base, res, ids = _fixture(
        tmp_path,
        [
            # r1: tags {a,b}==gold -> 1.0; gate open, status "open"==gold -> 1.0
            _pred(
                "r1",
                {
                    "tag_a": "true",
                    "tag_b": "true",
                    "tag_c": "false",
                    "has_status": "true",
                    "status_kind": "open",
                },
            ),
            # r2: tags {a,c} vs gold {c} -> set_f1 2/3; gate wrongly closed -> ""
            # vs "closed" -> 0.0 (the gate-closed reconstruction path, a miss)
            _pred(
                "r2",
                {
                    "tag_a": "true",
                    "tag_b": "false",
                    "tag_c": "true",
                    "has_status": "false",
                    "status_kind": "billing",
                },
            ),
            # r3: tags {} vs gold [] -> empty-both 1.0; gate open, "open" -> 1.0
            _pred(
                "r3",
                {
                    "tag_a": "false",
                    "tag_b": "false",
                    "tag_c": "false",
                    "has_status": "true",
                    "status_kind": "open",
                },
            ),
        ],
    )
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(
        res, base, ids, _FIELD_METRICS, out, aggregate={"strategy": "macro"}
    )
    assert e.per_field is not None
    # one-vs-rest tags: (1.0 + 2/3 + 1.0) / 3
    assert e.per_field["tags"].primary_value == pytest.approx((1.0 + 2 / 3 + 1.0) / 3)
    # gated status: (1.0 + 0.0 + 1.0) / 3
    assert e.per_field["status"].primary_value == pytest.approx(2 / 3)
    assert e.aggregate is not None
    assert e.aggregate.value == pytest.approx(((1.0 + 2 / 3 + 1.0) / 3 + 2 / 3) / 2)


def test_adopted_form_all_constituent_keys_absent_is_parse_failure(
    tmp_path: Path,
) -> None:
    base, res, ids = _fixture(
        tmp_path,
        [
            _pred(
                "r1",
                {
                    "tag_a": "true",
                    "tag_b": "true",
                    "tag_c": "false",
                    "has_status": "true",
                    "status_kind": "open",
                },
            ),
            _pred(
                "r2",
                {
                    "tag_a": "false",
                    "tag_b": "false",
                    "tag_c": "true",
                    "has_status": "true",
                    "status_kind": "closed",
                },
            ),
            # r3: none of tags' constituent keys present -> tags is a parse failure
            # for this row; status keys present so status is not.
            _pred("r3", {"has_status": "true", "status_kind": "open"}),
        ],
    )
    out = tmp_path / "eval.json"
    e = compute_eval_multifield(res, base, ids, _FIELD_METRICS, out)
    assert e.per_field is not None
    assert e.per_field["tags"].n_parse_failures == 1
    assert e.per_field["status"].n_parse_failures == 0
