"""End-to-end fixture tests: the v0.2 multi-field examples run through the K>1
runner (DESIGN §7.1.5 bucket 7).

Each example ships runnable scoring configs (config/{schema,field_metrics,
aggregate,floors}.json) derived from its plan.md. These tests build a synthetic
results.json from the example's baseline.csv and run the real
compute_eval_multifield against the real configs, proving the configs are wired
correctly end-to-end without any network/model call.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spp_scripts.eval import compute_eval_multifield
from spp_scripts.inference import _output_schema_field_names

REPO = Path(__file__).resolve().parents[4]
EXAMPLES = REPO / "examples"


def _config(example: str) -> tuple[Path, dict, dict, dict, list[str]]:
    base = EXAMPLES / example / "config"
    schema = base / "schema.json"
    field_metrics = json.loads((base / "field_metrics.json").read_text())
    aggregate = json.loads((base / "aggregate.json").read_text())
    floors = json.loads((base / "floors.json").read_text())
    fields = _output_schema_field_names(schema)
    return schema, field_metrics, aggregate, floors, fields


def _synth_results(
    baseline: Path, fields: list[str], overrides: dict[str, dict[str, str]]
) -> dict:
    """Predictions = gold for every field, except per-row `overrides` (row_id ->
    {field: wrong_value}). Yields a deterministic, mostly-correct run."""
    df = pd.read_csv(baseline)
    preds = []
    for _, row in df.iterrows():
        rid = str(row["row_id"])
        parsed = {f: str(row[f]) for f in fields}
        for f, v in overrides.get(rid, {}).items():
            parsed[f] = v
        preds.append(
            {
                "row_id": rid,
                "raw_response": "{}",
                "parsed_label": None,
                "parse_error": None,
                "parsed_fields": parsed,
                "field_parse_errors": {},
                "latency_ms": 1,
                "tokens_used": 1,
            }
        )
    return {
        "schema_version": "1",
        "model": "fixture",
        "prompt_path": "p",
        "prompt_sha256": "h",
        "predictions": preds,
        "summary": {
            "n_rows": len(preds),
            "n_parsed": len(preds),
            "n_parse_failures": 0,
            "total_tokens": len(preds),
            "total_latency_ms": len(preds),
            "wall_clock_ms": len(preds),
        },
    }


def _run(tmp_path: Path, example: str, overrides: dict[str, dict[str, str]]):
    schema, field_metrics, aggregate, floors, fields = _config(example)
    baseline = EXAMPLES / example / "data" / "baseline.csv"
    row_ids = [str(r) for r in pd.read_csv(baseline)["row_id"]]
    results = tmp_path / "results.json"
    results.write_text(json.dumps(_synth_results(baseline, fields, overrides)))
    out = tmp_path / "eval.json"
    return compute_eval_multifield(
        results,
        baseline,
        row_ids,
        field_metrics,
        out,
        aggregate=aggregate,
        floors=floors,
        id_column="row_id",
    ), out


def test_multi_field_extraction_perfect_run(tmp_path: Path) -> None:
    e, out = _run(tmp_path, "multi-field-extraction", {})
    # Perfect predictions -> every field 1.0, min aggregate 1.0, category floor met.
    assert e.per_field is not None
    assert {f: fe.primary_value for f, fe in e.per_field.items()} == {
        "title": 1.0,
        "price": 1.0,
        "category": 1.0,
        "in_stock": 1.0,
    }
    assert e.aggregate is not None
    assert e.aggregate.strategy == "min"
    assert e.aggregate.value == 1.0
    assert e.floor_compliance is not None
    assert e.floor_compliance["category"].status == "met"
    # The three-section eval.json is on disk.
    persisted = json.loads(out.read_text())
    assert set(persisted["per_field"]) == {"title", "price", "category", "in_stock"}
    assert persisted["aggregate"]["strategy"] == "min"
    assert persisted["floor_compliance"]["category"]["floor"] == 0.85


def test_multi_field_extraction_price_within_tolerance(tmp_path: Path) -> None:
    # row_001 price gold 89.50; predict 92.00 -> within $5 tolerance -> still 1.0.
    e, _ = _run(tmp_path, "multi-field-extraction", {"row_001": {"price": "92.00"}})
    assert e.per_field is not None
    assert e.per_field["price"].primary_value == 1.0
    # Predict way off on another row -> drags the within_tolerance mean below 1.
    e2, _ = _run(tmp_path, "multi-field-extraction", {"row_002": {"price": "999.00"}})
    assert e2.per_field is not None
    assert e2.per_field["price"].primary_value < 1.0


def test_nested_schema_perfect_run(tmp_path: Path) -> None:
    e, out = _run(tmp_path, "nested-schema", {})
    assert e.per_field is not None
    assert e.per_field["top_level"].primary_value == 1.0
    assert e.per_field["sub_category"].primary_value == 1.0
    assert e.aggregate is not None
    assert e.aggregate.strategy == "macro"
    assert e.aggregate.value == 1.0
    assert e.floor_compliance is not None
    assert e.floor_compliance["top_level"].status == "met"  # 1.0 >= 0.90
    assert e.floor_compliance["sub_category"].status == "not_specified"


def test_nested_schema_top_level_floor_can_go_unmet(tmp_path: Path) -> None:
    # Misroute several top_level values so macro_F1 falls under the 0.90 floor.
    overrides = {
        "row_001": {"top_level": "other"},
        "row_004": {"top_level": "other"},
        "row_007": {"top_level": "billing"},
    }
    e, _ = _run(tmp_path, "nested-schema", overrides)
    assert e.per_field is not None
    assert e.per_field["top_level"].primary_value < 0.90
    assert e.floor_compliance is not None
    assert e.floor_compliance["top_level"].status == "unmet"


# --------------------------------------------------------------------------- #
# entity-extraction (TASK_MODE = extraction; DESIGN §7.1.11)
# --------------------------------------------------------------------------- #


def test_entity_extraction_perfect_run(tmp_path: Path) -> None:
    # Predictions = gold -> span_f1 and extraction_f1 both 1.0, macro 1.0,
    # entities floor (0.80) met. Proves the extraction configs wire end to end.
    e, out = _run(tmp_path, "entity-extraction", {})
    assert e.per_field is not None
    assert e.per_field["entities"].primary_value == 1.0
    assert e.per_field["topics"].primary_value == 1.0
    assert e.aggregate is not None
    assert e.aggregate.strategy == "macro"
    assert e.aggregate.value == 1.0
    assert e.floor_compliance is not None
    assert e.floor_compliance["entities"].status == "met"
    persisted = json.loads(out.read_text())
    assert set(persisted["per_field"]) == {"entities", "topics"}


def test_entity_extraction_boundary_failure_drops_span_f1(tmp_path: Path) -> None:
    # row_001 gold span is "Acme Drill" [4,14). Predict [4,8) ("Acme"): IoU =
    # 4/10 = 0.4 < 0.5 threshold -> no match -> that row's span_f1 = 0.0. With
    # the other four rows perfect (incl. row_004's empty-both), the field mean
    # is 4/5 = 0.80 — still exactly at the floor, but below the perfect 1.0.
    bad = json.dumps(
        [{"text": "Acme", "type": "product", "start": 4, "end": 8}],
        separators=(",", ":"),
        sort_keys=True,
    )
    e, _ = _run(tmp_path, "entity-extraction", {"row_001": {"entities": bad}})
    assert e.per_field is not None
    assert e.per_field["entities"].primary_value == pytest.approx(0.80)
    assert e.floor_compliance is not None
    assert e.floor_compliance["entities"].status == "met"  # 0.80 >= 0.80


def test_entity_extraction_topics_text_alignment(tmp_path: Path) -> None:
    # Drop one of row_001's two topics -> recall 1/2 on that row -> field mean
    # below 1.0. (topics uses extraction_f1, match_type False: text alignment.)
    one = json.dumps(["returns"], separators=(",", ":"))
    e, _ = _run(tmp_path, "entity-extraction", {"row_001": {"topics": one}})
    assert e.per_field is not None
    assert e.per_field["topics"].primary_value < 1.0
    # entities untouched -> still perfect.
    assert e.per_field["entities"].primary_value == 1.0
