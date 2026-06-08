"""Tests for the v0.11 decomposition pipeline mechanics (DESIGN §7.1.12).

Covers the model-free building blocks the phases compose: spec load/validation
(the pipeline.md validation rules enforced in code), node-input materialization
(the frozen-upstream-output-as-input data-plane step), and composite scoring.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spp_scripts._pipeline import (
    COMPOSITE_METRICS,
    PipelineError,
    PipelineNodeSpec,
    compose_node_input,
    compute_composite,
    extract_node_outputs,
    load_pipeline_spec,
    main,
    materialize_node_inputs,
)

# --------------------------------------------------------------------------- #
# load_pipeline_spec
# --------------------------------------------------------------------------- #


def _two_node() -> dict:
    return {
        "nodes": [
            {"id": "craft", "input_columns": ["user_query"]},
            {
                "id": "respond",
                "input_columns": ["user_query"],
                "upstream_inputs": {"llm_request": "craft.llm_request"},
            },
        ],
        "composite_metric": "terminal",
    }


def test_load_valid_linear_chain() -> None:
    spec = load_pipeline_spec(_two_node())
    assert [n.id for n in spec.nodes] == ["craft", "respond"]
    assert spec.composite_metric == "terminal"
    assert spec.nodes[1].upstream_inputs == {"llm_request": "craft.llm_request"}


def test_load_requires_at_least_two_nodes() -> None:
    with pytest.raises(PipelineError, match="at least two nodes"):
        load_pipeline_spec({"nodes": [{"id": "solo"}]})


def test_load_rejects_duplicate_ids() -> None:
    data = {"nodes": [{"id": "a"}, {"id": "a", "upstream_inputs": {"x": "a.y"}}]}
    with pytest.raises(PipelineError, match="unique"):
        load_pipeline_spec(data)


def test_load_node1_must_have_no_upstream() -> None:
    data = {
        "nodes": [
            {"id": "a", "upstream_inputs": {"x": "b.y"}},
            {"id": "b"},
        ]
    }
    with pytest.raises(PipelineError, match="node 1"):
        load_pipeline_spec(data)


def test_load_rejects_self_reference() -> None:
    # a node referencing its own output is not an *earlier* node -> rejected.
    data = {"nodes": [{"id": "a"}, {"id": "b", "upstream_inputs": {"x": "b.y"}}]}
    with pytest.raises(PipelineError, match="not an earlier node"):
        load_pipeline_spec(data)


def test_load_rejects_forward_or_unknown_upstream_ref() -> None:
    # 'respond' references 'late', which appears AFTER it -> not an earlier node.
    data = {
        "nodes": [
            {"id": "craft"},
            {"id": "respond", "upstream_inputs": {"z": "late.f"}},
            {"id": "late"},
        ]
    }
    with pytest.raises(PipelineError, match="not an earlier node"):
        load_pipeline_spec(data)


def test_load_rejects_malformed_upstream_ref() -> None:
    data = {
        "nodes": [
            {"id": "a"},
            {"id": "b", "upstream_inputs": {"x": "no_dot_ref"}},
        ]
    }
    with pytest.raises(PipelineError, match="<node_id>.<output_field>"):
        load_pipeline_spec(data)


def test_load_rejects_unknown_composite_metric() -> None:
    data = _two_node()
    data["composite_metric"] = "median"
    with pytest.raises(PipelineError, match="not supported"):
        load_pipeline_spec(data)


def test_load_weighted_requires_weights() -> None:
    data = _two_node()
    data["composite_metric"] = "weighted"
    with pytest.raises(PipelineError, match="requires composite_weights"):
        load_pipeline_spec(data)
    data["composite_weights"] = {"craft": 1.0, "respond": 2.0}
    spec = load_pipeline_spec(data)
    assert spec.composite_weights == {"craft": 1.0, "respond": 2.0}


def test_composite_metrics_constant() -> None:
    assert COMPOSITE_METRICS == {"terminal", "mean", "weighted", "min"}


# --------------------------------------------------------------------------- #
# materialize_node_inputs
# --------------------------------------------------------------------------- #


def test_materialize_attaches_upstream_by_row_id() -> None:
    base = pd.DataFrame(
        [
            {"row_id": "r1", "user_query": "q1", "gold": "g1"},
            {"row_id": "r2", "user_query": "q2", "gold": "g2"},
        ]
    )
    node = PipelineNodeSpec(
        id="respond",
        input_columns=["user_query"],
        upstream_inputs={"llm_request": "craft.llm_request"},
    )
    upstream = {"craft.llm_request": {"r1": "redacted-1", "r2": "redacted-2"}}
    df = materialize_node_inputs(base, node, upstream)
    assert df["llm_request"].tolist() == ["redacted-1", "redacted-2"]
    # original columns and gold untouched; base not mutated in place.
    assert df["user_query"].tolist() == ["q1", "q2"]
    assert "llm_request" not in base.columns


def test_materialize_node1_no_upstream_is_copy() -> None:
    base = pd.DataFrame([{"row_id": "r1", "user_query": "q1"}])
    node = PipelineNodeSpec(id="craft", input_columns=["user_query"])
    df = materialize_node_inputs(base, node, {})
    assert df.equals(base)
    assert df is not base


def test_materialize_missing_upstream_output_raises() -> None:
    base = pd.DataFrame([{"row_id": "r1", "user_query": "q1"}])
    node = PipelineNodeSpec(id="respond", upstream_inputs={"x": "craft.f"})
    with pytest.raises(PipelineError, match="no materialized upstream output"):
        materialize_node_inputs(base, node, {})


def test_materialize_missing_row_value_raises() -> None:
    base = pd.DataFrame(
        [{"row_id": "r1", "user_query": "q1"}, {"row_id": "r2", "user_query": "q2"}]
    )
    node = PipelineNodeSpec(id="respond", upstream_inputs={"x": "craft.f"})
    upstream = {"craft.f": {"r1": "only-r1"}}  # r2 missing
    with pytest.raises(PipelineError, match="no upstream value for 1 row"):
        materialize_node_inputs(base, node, upstream)


def test_materialize_column_collision_raises() -> None:
    # an upstream input column that collides with an existing baseline column
    # would silently clobber it — a spec misconfiguration, caught hard.
    base = pd.DataFrame([{"row_id": "r1", "user_query": "q1"}])
    node = PipelineNodeSpec(id="respond", upstream_inputs={"user_query": "craft.f"})
    upstream = {"craft.f": {"r1": "x"}}
    with pytest.raises(PipelineError, match="already exists in"):
        materialize_node_inputs(base, node, upstream)


# --------------------------------------------------------------------------- #
# compute_composite
# --------------------------------------------------------------------------- #


def test_composite_terminal_is_last_node() -> None:
    assert compute_composite([("a", 0.9), ("b", 0.6)], "terminal") == 0.6


def test_composite_mean() -> None:
    assert compute_composite([("a", 1.0), ("b", 0.5)], "mean") == pytest.approx(0.75)


def test_composite_min() -> None:
    assert compute_composite([("a", 0.9), ("b", 0.4)], "min") == 0.4


def test_composite_weighted() -> None:
    # (0.9*1 + 0.6*3) / (1+3) = 2.7/4 = 0.675
    val = compute_composite([("a", 0.9), ("b", 0.6)], "weighted", {"a": 1.0, "b": 3.0})
    assert val == pytest.approx(0.675)


def test_composite_weighted_missing_weight_defaults_to_one() -> None:
    # b's weight defaults to 1.0 -> plain mean 0.75
    val = compute_composite([("a", 1.0), ("b", 0.5)], "weighted", {"a": 1.0})
    assert val == pytest.approx(0.75)


def test_composite_empty_raises() -> None:
    with pytest.raises(PipelineError, match="no per-node values"):
        compute_composite([], "terminal")


def test_composite_unknown_strategy_raises() -> None:
    with pytest.raises(PipelineError, match="not supported"):
        compute_composite([("a", 1.0)], "median")


def test_composite_zero_total_weight_raises() -> None:
    # an all-zero weights dict passes spec load (non-empty) but fails at compute.
    with pytest.raises(PipelineError, match="zero total weight"):
        compute_composite([("a", 1.0), ("b", 0.5)], "weighted", {"a": 0.0, "b": 0.0})


# --------------------------------------------------------------------------- #
# extract_node_outputs / compose_node_input
# --------------------------------------------------------------------------- #


def _results(predictions: list[dict]) -> dict:
    return {"predictions": predictions}


def test_extract_node_outputs_keys_by_ref_and_row() -> None:
    results = _results(
        [
            {"row_id": "r1", "parsed_fields": {"llm_request": "a", "note": "n1"}},
            {"row_id": "r2", "parsed_fields": {"llm_request": "b", "note": "n2"}},
        ]
    )
    out = extract_node_outputs(results, "craft")
    assert out["craft.llm_request"] == {"r1": "a", "r2": "b"}
    assert out["craft.note"] == {"r1": "n1", "r2": "n2"}


def test_compose_node_input_single_is_raw() -> None:
    df = pd.DataFrame([{"row_id": "r1", "user_query": "hello"}])
    node = PipelineNodeSpec(id="craft", input_columns=["user_query"])
    out = compose_node_input(df, node)
    assert out["input"].tolist() == ["hello"]


def test_compose_node_input_multi_is_labeled_block() -> None:
    df = pd.DataFrame([{"row_id": "r1", "user_query": "q", "llm_request": "r"}])
    node = PipelineNodeSpec(
        id="respond",
        input_columns=["user_query"],
        upstream_inputs={"llm_request": "craft.llm_request"},
    )
    out = compose_node_input(df, node)
    assert out["input"].tolist() == ["user_query:\nq\n\nllm_request:\nr"]


def test_compose_node_input_missing_column_raises() -> None:
    df = pd.DataFrame([{"row_id": "r1"}])
    node = PipelineNodeSpec(id="craft", input_columns=["user_query"])
    with pytest.raises(PipelineError, match="missing input columns"):
        compose_node_input(df, node)


# --------------------------------------------------------------------------- #
# CLI: materialize / composite
# --------------------------------------------------------------------------- #


def _write_pipeline(tmp_path: Path) -> Path:
    p = tmp_path / "pipeline.json"
    p.write_text(json.dumps(_two_node()))
    return p


def test_cli_materialize_attaches_and_composes(tmp_path: Path) -> None:
    pipeline = _write_pipeline(tmp_path)
    base = tmp_path / "respond_base.csv"
    pd.DataFrame(
        [
            {"row_id": "r1", "user_query": "q1", "gold": "g1"},
            {"row_id": "r2", "user_query": "q2", "gold": "g2"},
        ]
    ).to_csv(base, index=False)
    craft_results = tmp_path / "craft_results.json"
    craft_results.write_text(
        json.dumps(
            _results(
                [
                    {"row_id": "r1", "parsed_fields": {"llm_request": "red1"}},
                    {"row_id": "r2", "parsed_fields": {"llm_request": "red2"}},
                ]
            )
        )
    )
    out = tmp_path / "respond_materialized.csv"
    rc = main(
        [
            "materialize",
            "--pipeline",
            str(pipeline),
            "--node",
            "respond",
            "--base",
            str(base),
            "--upstream",
            f"craft={craft_results}",
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    df = pd.read_csv(out)
    assert df["llm_request"].tolist() == ["red1", "red2"]  # materialized column
    assert df["gold"].tolist() == ["g1", "g2"]  # node-local gold preserved
    # composed input is a labeled block of user_query + llm_request.
    assert df["input"].tolist()[0] == "user_query:\nq1\n\nllm_request:\nred1"


def test_cli_composite_reads_per_node_eval(tmp_path: Path) -> None:
    pipeline = _write_pipeline(tmp_path)
    craft_eval = tmp_path / "craft_eval.json"
    craft_eval.write_text(json.dumps({"primary_value": 0.9}))
    respond_eval = tmp_path / "respond_eval.json"
    respond_eval.write_text(json.dumps({"primary_value": 0.6}))
    out = tmp_path / "composite.json"
    rc = main(
        [
            "composite",
            "--pipeline",
            str(pipeline),
            "--node-eval",
            f"craft={craft_eval}",
            "--node-eval",
            f"respond={respond_eval}",
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    result = json.loads(out.read_text())
    # _two_node() uses composite_metric "terminal" -> the respond node's value.
    assert result["composite_metric"] == "terminal"
    assert result["composite_value"] == 0.6
    assert result["per_node"] == {"craft": 0.9, "respond": 0.6}


def test_cli_materialize_malformed_kv_exits(tmp_path: Path) -> None:
    pipeline = _write_pipeline(tmp_path)
    base = tmp_path / "b.csv"
    pd.DataFrame([{"row_id": "r1", "user_query": "q1"}]).to_csv(base, index=False)
    # a malformed --upstream item (no '=') routes a PipelineError through
    # parser.error -> SystemExit, not an uncaught traceback.
    with pytest.raises(SystemExit):
        main(
            [
                "materialize",
                "--pipeline",
                str(pipeline),
                "--node",
                "respond",
                "--base",
                str(base),
                "--upstream",
                "no_equals_sign",
                "--out",
                str(tmp_path / "o.csv"),
            ]
        )


def test_cli_composite_missing_node_eval_exits(tmp_path: Path) -> None:
    pipeline = _write_pipeline(tmp_path)
    craft_eval = tmp_path / "craft_eval.json"
    craft_eval.write_text(json.dumps({"primary_value": 0.9}))
    # respond's eval is not supplied -> clean SystemExit, not KeyError.
    with pytest.raises(SystemExit):
        main(
            [
                "composite",
                "--pipeline",
                str(pipeline),
                "--node-eval",
                f"craft={craft_eval}",
            ]
        )


def test_cli_composite_malformed_eval_exits(tmp_path: Path) -> None:
    pipeline = _write_pipeline(tmp_path)
    craft_eval = tmp_path / "craft_eval.json"
    craft_eval.write_text(json.dumps({"primary_value": 0.9}))
    bad = tmp_path / "respond_eval.json"
    bad.write_text(json.dumps({"no_primary": 1}))  # missing primary_value
    with pytest.raises(SystemExit):
        main(
            [
                "composite",
                "--pipeline",
                str(pipeline),
                "--node-eval",
                f"craft={craft_eval}",
                "--node-eval",
                f"respond={bad}",
            ]
        )


def test_cli_materialize_missing_pipeline_file_exits(tmp_path: Path) -> None:
    base = tmp_path / "b.csv"
    pd.DataFrame([{"row_id": "r1", "user_query": "q1"}]).to_csv(base, index=False)
    # a nonexistent pipeline config -> clean SystemExit, not FileNotFoundError.
    with pytest.raises(SystemExit):
        main(
            [
                "materialize",
                "--pipeline",
                str(tmp_path / "nope.json"),
                "--node",
                "respond",
                "--base",
                str(base),
                "--out",
                str(tmp_path / "o.csv"),
            ]
        )


def test_cli_composite_missing_eval_file_exits(tmp_path: Path) -> None:
    pipeline = _write_pipeline(tmp_path)
    craft_eval = tmp_path / "craft_eval.json"
    craft_eval.write_text(json.dumps({"primary_value": 0.9}))
    # respond's eval file does not exist -> clean SystemExit, not FileNotFoundError.
    with pytest.raises(SystemExit):
        main(
            [
                "composite",
                "--pipeline",
                str(pipeline),
                "--node-eval",
                f"craft={craft_eval}",
                "--node-eval",
                f"respond={tmp_path / 'missing.json'}",
            ]
        )
