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
    assert "## Disagreed Rows (IDs only)" in text
    assert "## Aggregate Patterns" in text
    # Two rows disagreed (b: predicted Relevant, truth Not Relevant; c: parse failure).
    assert "`b`:" in text
    assert "`c`:" in text
    # a was correct, should not appear.
    assert "`a`:" not in text
    # Aggregate patterns section names the discrepancy subagent (per
    # the per-stage isolation revision).
    assert "discrepancy subagent" in text
    # Row content must NOT appear in the persistent artifact.
    assert "first text" not in text
    assert "second text" not in text
    assert "third text" not in text
    # Raw response also must not appear (would carry indirect content).
    assert "garbage" not in text


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


def test_discrepancy_monolingual_no_language_section(tmp_path: Path) -> None:
    base, res, ev, ids = _fixtures(tmp_path)  # no `language` column
    text = generate_discrepancy(res, base, ev, ids, tmp_path / "d.md")
    assert "Per-language failure rate" not in text


# ---- v0.6 per-language attribution (DESIGN.md §7.1.7) ---------------------


def _ml_fixtures(tmp_path: Path) -> tuple[Path, Path, Path, list[str]]:
    """2 en + 2 es rows; one disagreement in each language (50% each)."""
    rows = [
        {"id": "a", "input": "t", "label": "Relevant", "language": "en"},
        {"id": "b", "input": "t", "label": "Not Relevant", "language": "en"},
        {"id": "c", "input": "t", "label": "Relevant", "language": "es"},
        {"id": "d", "input": "t", "label": "Relevant", "language": "es"},
    ]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)
    preds = {"a": "Relevant", "b": "Relevant", "c": None, "d": "Relevant"}
    results = {
        "schema_version": "1",
        "model": "t",
        "prompt_path": "p",
        "prompt_sha256": "h",
        "predictions": [
            {
                "row_id": rid,
                "raw_response": lbl or "x",
                "parsed_label": lbl,
                "parse_error": None if lbl else "no JSON",
                "latency_ms": 1,
                "tokens_used": 1,
            }
            for rid, lbl in preds.items()
        ],
        "summary": {
            "n_rows": 4,
            "n_parsed": 3,
            "n_parse_failures": 1,
            "total_tokens": 4,
            "total_latency_ms": 4,
            "wall_clock_ms": 4,
        },
    }
    res = tmp_path / "results.json"
    res.write_text(json.dumps(results))
    eval_data = {
        "schema_version": "1",
        "metric": "accuracy",
        "metric_kwargs": {},
        "primary_value": 0.5,
        "n_rows_evaluated": 4,
        "n_parse_failures_in_input": 1,
        "confusion_matrix": [],
        "labels": ["Relevant", "Not Relevant", "__PARSE_FAILURE__"],
        "per_class": {},
    }
    ev = tmp_path / "eval.json"
    ev.write_text(json.dumps(eval_data))
    return base, res, ev, ["a", "b", "c", "d"]


def test_discrepancy_per_language_section(tmp_path: Path) -> None:
    base, res, ev, ids = _ml_fixtures(tmp_path)
    text = generate_discrepancy(res, base, ev, ids, tmp_path / "d.md")
    assert "Per-language failure rate" in text
    # b disagrees (en), c is a parse failure (es) -> 50% each.
    assert "`en`: 1/2 disagreed (50.0%)" in text
    assert "`es`: 1/2 disagreed (50.0%)" in text
    # Still no row content in the persistent artifact.
    assert "Relevant" in text  # labels are fine; input content is not
    assert ids == ["a", "b", "c", "d"]


def test_discrepancy_missing_input(tmp_path: Path) -> None:
    with pytest.raises(DiscrepancyError, match="input not found"):
        generate_discrepancy(
            tmp_path / "no.json",
            tmp_path / "no.csv",
            tmp_path / "no.json",
            ["a"],
            tmp_path / "out.md",
        )
