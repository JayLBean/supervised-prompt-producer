"""End-to-end: label-panel frozen labels flow into split -> eval.

Proves the v0.7 panel composes with the existing scoring pipeline
(DESIGN.md §7.1.8): a panel synthesizes labels into the canonical
baseline, `split.py` splits on those frozen labels, and `eval.py` scores
against them with the same mechanical metric as any other baseline — never
reading `label_panel.json`. This is invariant #13 demonstrated in
practice: the judge creates the baseline, then exits the loop entirely.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from spp_scripts.eval import compute_eval
from spp_scripts.label_panel import aggregate_votes, write_labeled_baseline
from spp_scripts.split import make_splits

SPACE = ["Empathetic", "Neutral", "Curt"]


def _unanimous_votes(label: str) -> list[dict[str, str]]:
    return [
        {"judge_id": f"judge_{i + 1}", "label": label, "rationale": "clear"}
        for i in range(5)
    ]


def test_panel_labels_flow_into_split_and_eval(tmp_path: Path) -> None:
    # 36 rows, 3 balanced classes, all confident consensus -> a clean
    # labeled baseline produced entirely by the real panel pipeline.
    raw_rows = []
    raw_votes: dict[str, list[dict[str, str]]] = {}
    i = 0
    for label in SPACE:
        for _ in range(12):
            rid = f"r{i:03d}"
            raw_rows.append({"id": rid, "input": f"text {i}"})
            raw_votes[rid] = _unanimous_votes(label)
            i += 1

    baseline = tmp_path / "baseline.csv"
    pd.DataFrame(raw_rows).to_csv(baseline, index=False)

    # 1) panel: gate passes (gpt-4o -> openai), all rows auto-accept.
    panel = aggregate_votes(raw_votes, "gpt-4o", SPACE)
    assert panel.production_family == "openai"
    assert panel.summary.n_auto_accepted == 36
    assert panel.summary.n_escalated == 0

    # 2) freeze the labels into the canonical baseline.
    write_labeled_baseline(panel, baseline, baseline)
    labeled = pd.read_csv(baseline)
    assert set(labeled.columns) == {"id", "input", "label"}
    assert set(labeled["label"]) == set(SPACE)

    # 3) split on the frozen labels (every class in every partition).
    splits_path = tmp_path / "splits.json"
    splits = make_splits(baseline, "label", 42, (0.6, 0.2, 0.2), splits_path)
    df = pd.read_csv(baseline)
    df.index = df["id"].astype(str)
    for ids in (splits.row_ids.train, splits.row_ids.dev, splits.row_ids.test):
        assert set(df.loc[ids]["label"]) == set(SPACE)

    # 4) eval: perfect predictions against the frozen labels -> 1.0. eval
    #    reads baseline.csv + results.json + the dev ids only; it never
    #    opens label_panel.json (which is not even written here).
    preds = [
        {
            "row_id": rid,
            "raw_response": lbl,
            "parsed_label": lbl,
            "parse_error": None,
            "latency_ms": 1,
            "tokens_used": 1,
        }
        for rid, lbl in zip(df["id"].astype(str), df["label"].astype(str), strict=True)
    ]
    results_path = tmp_path / "results.json"
    results_path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "model": "gpt-4o",
                "prompt_path": "p",
                "prompt_sha256": "h",
                "predictions": preds,
                "summary": {
                    "n_rows": len(preds),
                    "n_parsed": len(preds),
                    "n_parse_failures": 0,
                    "total_tokens": len(preds),
                    "total_latency_ms": len(preds),
                    "wall_clock_ms": 1,
                },
            }
        )
    )
    e = compute_eval(
        results_path, baseline, splits.row_ids.dev, "accuracy", tmp_path / "eval.json"
    )
    assert e.primary_value == 1.0
    assert not (tmp_path / "label_panel.json").exists()
