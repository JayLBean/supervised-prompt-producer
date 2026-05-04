"""Smoke tests for discrepancy.py."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spp_scripts.discrepancy import DiscrepancyError, generate_discrepancy


def _fixtures(tmp_path: Path) -> tuple[Path, Path, Path, list[str]]:
    rows = [
        {"id": "a", "input": "first text", "label": "Relevant"},
        {"id": "b", "input": "second text", "label": "Not Relevant"},
        {"id": "c", "input": "third text", "label": "Relevant"},
    ]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)

    results = {
        "schema_version": "1",
        "model": "t",
        "prompt_path": "p",
        "prompt_sha256": "h",
        "predictions": [
            {
                "row_id": "a",
                "raw_response": "Relevant",
                "parsed_label": "Relevant",
                "parse_error": None,
                "latency_ms": 1,
                "tokens_used": 5,
            },
            {
                "row_id": "b",
                "raw_response": "Relevant",
                "parsed_label": "Relevant",
                "parse_error": None,
                "latency_ms": 1,
                "tokens_used": 5,
            },
            {
                "row_id": "c",
                "raw_response": "garbage",
                "parsed_label": None,
                "parse_error": "no JSON",
                "latency_ms": 1,
                "tokens_used": 5,
            },
        ],
        "summary": {
            "n_rows": 3,
            "n_parsed": 2,
            "n_parse_failures": 1,
            "total_tokens": 15,
            "total_latency_ms": 3,
            "wall_clock_ms": 3,
        },
    }
    res = tmp_path / "results.json"
    res.write_text(json.dumps(results))

    eval_data = {
        "schema_version": "1",
        "metric": "accuracy",
        "metric_kwargs": {},
        "primary_value": 0.333,
        "n_rows_evaluated": 3,
        "n_parse_failures_in_input": 1,
        "confusion_matrix": [[1, 1, 0], [0, 1, 0], [0, 0, 1]],
        "labels": ["Relevant", "Not Relevant", "__PARSE_FAILURE__"],
        "per_class": {},
        "auxiliary_metrics": {},
    }
    ev = tmp_path / "eval.json"
    ev.write_text(json.dumps(eval_data))

    return base, res, ev, ["a", "b", "c"]


def test_discrepancy_structure(tmp_path: Path) -> None:
    base, res, ev, ids = _fixtures(tmp_path)
    out = tmp_path / "discrepancy_analysis.md"
    text = generate_discrepancy(res, base, ev, ids, out, iteration=2)
    assert out.exists()
    assert "# Discrepancy Analysis — Iteration 2" in text
    assert "## Summary" in text
    assert "## Disagreed Rows" in text
    assert "## Aggregate Patterns" in text
    # Two rows disagreed (b: predicted Relevant, truth Not Relevant; c: parse failure).
    assert "### Row b" in text
    assert "### Row c" in text
    # a was correct, should not appear.
    assert "### Row a" not in text
    # Aggregate patterns section is empty (LLM populates).
    assert "LLM running `/spp-loop`" in text


def test_discrepancy_no_disagreements(tmp_path: Path) -> None:
    base, res, ev, _ = _fixtures(tmp_path)
    # Override results so all predictions match.
    data = json.loads(res.read_text())
    data["predictions"][1]["parsed_label"] = "Not Relevant"
    data["predictions"][1]["raw_response"] = "Not Relevant"
    data["predictions"][2]["parsed_label"] = "Relevant"
    data["predictions"][2]["raw_response"] = "Relevant"
    data["predictions"][2]["parse_error"] = None
    res.write_text(json.dumps(data))

    out = tmp_path / "d.md"
    text = generate_discrepancy(res, base, ev, ["a", "b", "c"], out)
    assert "0 predictions disagreed" in text
    assert "(none)" in text


def test_discrepancy_missing_input(tmp_path: Path) -> None:
    with pytest.raises(DiscrepancyError, match="input not found"):
        generate_discrepancy(
            tmp_path / "no.json",
            tmp_path / "no.csv",
            tmp_path / "no.json",
            ["a"],
            tmp_path / "out.md",
        )
