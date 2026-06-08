"""End-to-end fixture test: the v0.11 decomposition-pipeline example
(DESIGN §7.1.12) scored through the real pipeline mechanics.

Walks the two-node `extract -> classify` pipeline the way the phases do —
score node 1, materialize node 2's baseline from node 1's frozen output, score
node 2, compute the composite — using the real `compute_eval_multifield` and
`_pipeline` functions with synthetic predictions (no model call). Proves the
fixture configs and the chain wiring agree end to end, and that each node is
scored on its own node-local gold (no model in the scoring path, #13).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from spp_scripts._pipeline import (
    compute_composite,
    extract_node_outputs,
    load_pipeline_spec,
    materialize_node_inputs,
)
from spp_scripts.eval import compute_eval_multifield

REPO = Path(__file__).resolve().parents[4]
PIPE = REPO / "examples" / "decomposition-pipeline"


def _field_metrics(node: str) -> dict:
    return json.loads(
        (PIPE / "sub-tasks" / node / "config" / "field_metrics.json").read_text()
    )


def _baseline(node: str) -> Path:
    return PIPE / "sub-tasks" / node / "data" / "baseline.csv"


def _synth_results(
    baseline: Path, fields: list[str], overrides: dict[str, dict[str, str]]
) -> dict:
    """Predictions = gold for each field, except per-row `overrides`."""
    df = pd.read_csv(baseline)
    preds = []
    for _, row in df.iterrows():
        rid = str(row["row_id"])
        parsed = {f: str(row[f]) for f in fields}
        parsed.update(overrides.get(rid, {}))
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


def _score(tmp_path: Path, node: str, baseline: Path, results: dict) -> float:
    row_ids = [str(r) for r in pd.read_csv(baseline)["row_id"]]
    res = tmp_path / f"{node}_results.json"
    res.write_text(json.dumps(results))
    out = tmp_path / f"{node}_eval.json"
    e = compute_eval_multifield(
        res, baseline, row_ids, _field_metrics(node), out, id_column="row_id"
    )
    return e.primary_value


def test_pipeline_config_is_valid() -> None:
    spec = load_pipeline_spec(json.loads((PIPE / "pipeline.json").read_text()))
    assert [n.id for n in spec.nodes] == ["extract", "classify"]
    assert spec.nodes[1].upstream_inputs == {"products": "extract.products"}
    assert spec.composite_metric == "mean"


def test_pipeline_perfect_run_composite(tmp_path: Path) -> None:
    spec = load_pipeline_spec(json.loads((PIPE / "pipeline.json").read_text()))

    # Node 1: extract — perfect predictions -> extraction_f1 1.0.
    ex_results = _synth_results(_baseline("extract"), ["products"], {})
    ex_val = _score(tmp_path, "extract", _baseline("extract"), ex_results)
    assert ex_val == 1.0

    # Materialize node 2's input from node 1's frozen output (the data-plane
    # step): classify's baseline gains a `products` column from extract.
    upstream = extract_node_outputs(ex_results, "extract")
    classify_base = pd.read_csv(_baseline("classify"))
    materialized = materialize_node_inputs(classify_base, spec.nodes[1], upstream)
    assert "products" in materialized.columns  # frozen upstream output attached
    assert materialized["products"].tolist()[0]  # non-empty for r1

    # Node 2: classify — perfect predictions -> macro_f1 1.0. (Scored on its own
    # node-local sentiment gold; the materialized products is only an input.)
    cl_results = _synth_results(_baseline("classify"), ["sentiment"], {})
    cl_val = _score(tmp_path, "classify", _baseline("classify"), cl_results)
    assert cl_val == 1.0

    composite = compute_composite(
        [("extract", ex_val), ("classify", cl_val)], spec.composite_metric
    )
    assert composite == 1.0  # mean of (1.0, 1.0)


def test_pipeline_upstream_failure_drops_composite(tmp_path: Path) -> None:
    spec = load_pipeline_spec(json.loads((PIPE / "pipeline.json").read_text()))

    # Node 1 misses a product on r4 (drop "Initech Mouse"): r4 extraction_f1
    # = 2*1/(2+1) = 2/3; other 3 rows perfect -> mean (1+1+1+2/3)/4 = 11/12.
    one_product = json.dumps(["Initech Laptop"], separators=(",", ":"))
    ex_results = _synth_results(
        _baseline("extract"), ["products"], {"r4": {"products": one_product}}
    )
    ex_val = _score(tmp_path, "extract", _baseline("extract"), ex_results)
    assert ex_val < 1.0

    cl_results = _synth_results(_baseline("classify"), ["sentiment"], {})
    cl_val = _score(tmp_path, "classify", _baseline("classify"), cl_results)
    assert cl_val == 1.0

    composite = compute_composite(
        [("extract", ex_val), ("classify", cl_val)], spec.composite_metric
    )
    assert composite < 1.0  # the upstream miss pulls the mean composite down
