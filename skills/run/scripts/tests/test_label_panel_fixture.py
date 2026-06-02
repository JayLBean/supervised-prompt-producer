"""End-to-end exercise of the label-panel support-tone fixture.

Drives the committed fixture through the real pipeline — aggregate -> queue
-> resolve -> write — and asserts it reproduces the golden labeled
baseline. The fixture is a subjective-label task (support-reply tone) whose
canonical baseline arrives with no label column, the case the v0.7
`label-panel` sub-skill exists for (DESIGN.md §7.1.8).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from spp_scripts.label_panel import (
    aggregate_votes,
    apply_decisions,
    build_escalation_queue,
    write_labeled_baseline,
)

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "sub-skills"
    / "label-panel"
    / "fixtures"
    / "support-tone"
)


def _votes_doc() -> dict[str, object]:
    return json.loads((_FIXTURE / "votes.json").read_text(encoding="utf-8"))


def test_fixture_aggregate_routes_two_escalations() -> None:
    v = _votes_doc()
    panel = aggregate_votes(
        v["votes"],
        str(v["production_model"]),
        [str(x) for x in v["label_space"]],
        declared_family=v["model_family"],
    )
    # gpt-4o-mini -> openai, cross-family with the Claude panel: gate passes.
    assert panel.production_family == "openai"
    assert panel.summary.n_auto_accepted == 8
    assert panel.summary.n_escalated == 2


def test_fixture_queue_lists_escalated_rows_with_input() -> None:
    v = _votes_doc()
    panel = aggregate_votes(
        v["votes"],
        str(v["production_model"]),
        [str(x) for x in v["label_space"]],
        declared_family=v["model_family"],
    )
    queue = build_escalation_queue(panel, _FIXTURE / "baseline_unlabeled.csv")
    ids = {item["row_id"] for item in queue["items"]}  # type: ignore[union-attr]
    assert ids == {"r07", "r08"}
    for item in queue["items"]:  # type: ignore[union-attr]
        assert item["input"]  # the human sees the row text
        assert len(item["votes"]) == 5


def test_fixture_pipeline_reproduces_golden(tmp_path: Path) -> None:
    v = _votes_doc()
    panel = aggregate_votes(
        v["votes"],
        str(v["production_model"]),
        [str(x) for x in v["label_space"]],
        declared_family=v["model_family"],
    )
    decisions = json.loads((_FIXTURE / "decisions.json").read_text(encoding="utf-8"))[
        "decisions"
    ]
    panel = apply_decisions(panel, {str(k): str(v_) for k, v_ in decisions.items()})
    assert panel.summary.n_human_resolved == 2
    assert panel.summary.n_escalated == 0

    out = tmp_path / "baseline.csv"
    write_labeled_baseline(panel, _FIXTURE / "baseline_unlabeled.csv", out)
    got = pd.read_csv(out)
    expected = pd.read_csv(_FIXTURE / "expected_baseline.csv")
    pd.testing.assert_frame_equal(got, expected)
