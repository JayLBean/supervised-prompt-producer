"""Tests for label-panel consensus aggregation and I/O (DESIGN.md §7.1.8).

The script does only the mechanical part: gate, tally, escalate, write. The
load-bearing behaviors under test are the cross-family gate running first,
the 4-of-5 consensus boundary, escalation of splits, the stable
per-language escalation disclosure, and the all-or-nothing labeled-baseline
write.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from spp_scripts._models import SameFamilyError
from spp_scripts._schemas import LabelPanelJSON
from spp_scripts.label_panel import (
    LabelPanelError,
    aggregate_votes,
    apply_decisions,
    build_escalation_queue,
    write_labeled_baseline,
)

SPACE = ["Empathetic", "Neutral", "Curt"]


def _votes(*labels: str) -> list[dict[str, str]]:
    return [
        {"judge_id": f"judge_{i + 1}", "label": lab, "rationale": f"r{i}"}
        for i, lab in enumerate(labels)
    ]


def _raw(**rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    return dict(rows)


def test_unanimous_auto_accepts() -> None:
    panel = aggregate_votes(
        _raw(r1=_votes("Neutral", "Neutral", "Neutral", "Neutral", "Neutral")),
        "gpt-4o",
        SPACE,
    )
    row = panel.rows[0]
    assert row.disposition == "auto_accepted"
    assert row.n_agree == 5
    assert row.winning_label == "Neutral"
    assert row.final_label == "Neutral"


def test_four_one_auto_accepts() -> None:
    panel = aggregate_votes(
        _raw(r1=_votes("Curt", "Curt", "Curt", "Curt", "Neutral")),
        "gpt-4o",
        SPACE,
    )
    row = panel.rows[0]
    assert row.disposition == "auto_accepted"
    assert row.n_agree == 4
    assert row.final_label == "Curt"


def test_three_two_escalates() -> None:
    panel = aggregate_votes(
        _raw(r1=_votes("Neutral", "Neutral", "Neutral", "Curt", "Curt")),
        "gpt-4o",
        SPACE,
    )
    row = panel.rows[0]
    assert row.disposition == "escalated"
    assert row.n_agree == 3
    assert row.final_label is None
    assert row.winning_label == "Neutral"  # plurality still recorded


def test_three_way_split_escalates_deterministic_plurality() -> None:
    panel = aggregate_votes(
        _raw(r1=_votes("Empathetic", "Empathetic", "Neutral", "Neutral", "Curt")),
        "gpt-4o",
        SPACE,
    )
    row = panel.rows[0]
    assert row.disposition == "escalated"
    assert row.n_agree == 2
    # tie on count 2 between Empathetic and Neutral -> sorted order wins
    assert row.winning_label == "Empathetic"


def test_gate_blocks_same_family_before_tally() -> None:
    with pytest.raises(SameFamilyError):
        aggregate_votes(
            _raw(r1=_votes("Neutral", "Neutral", "Neutral", "Neutral", "Neutral")),
            "claude-opus-4-8",
            SPACE,
        )


def test_wrong_vote_count_raises() -> None:
    with pytest.raises(LabelPanelError):
        aggregate_votes(_raw(r1=_votes("Neutral", "Neutral")), "gpt-4o", SPACE)


def test_vote_outside_label_space_raises() -> None:
    with pytest.raises(LabelPanelError):
        aggregate_votes(
            _raw(r1=_votes("Neutral", "Neutral", "Neutral", "Neutral", "Angry")),
            "gpt-4o",
            SPACE,
        )


def test_threshold_above_panel_size_raises() -> None:
    with pytest.raises(LabelPanelError):
        aggregate_votes(
            _raw(r1=_votes("Neutral", "Neutral", "Neutral", "Neutral", "Neutral")),
            "gpt-4o",
            SPACE,
            consensus_threshold=6,
        )


def test_summary_counts() -> None:
    panel = aggregate_votes(
        _raw(
            r1=_votes("Neutral", "Neutral", "Neutral", "Neutral", "Neutral"),
            r2=_votes("Curt", "Curt", "Curt", "Neutral", "Neutral"),
            r3=_votes("Curt", "Curt", "Curt", "Curt", "Empathetic"),
        ),
        "gpt-4o",
        SPACE,
    )
    assert panel.summary.n_rows == 3
    assert panel.summary.n_auto_accepted == 2
    assert panel.summary.n_escalated == 1
    assert panel.production_family == "openai"


def test_per_language_escalation_only_when_multilingual() -> None:
    row_language = {"r1": "en", "r2": "es", "r3": "es"}
    panel = aggregate_votes(
        _raw(
            r1=_votes("Neutral", "Neutral", "Neutral", "Curt", "Curt"),  # escalate
            r2=_votes("Curt", "Curt", "Neutral", "Neutral", "Empathetic"),  # escalate
            r3=_votes("Neutral", "Neutral", "Neutral", "Neutral", "Neutral"),  # auto
        ),
        "gpt-4o",
        SPACE,
        row_language=row_language,
    )
    assert panel.summary.per_language_escalation == {"en": 1, "es": 1}


def test_per_language_empty_when_monolingual() -> None:
    row_language = {"r1": "en", "r2": "en"}
    panel = aggregate_votes(
        _raw(
            r1=_votes("Neutral", "Neutral", "Neutral", "Curt", "Curt"),
            r2=_votes("Curt", "Curt", "Curt", "Curt", "Curt"),
        ),
        "gpt-4o",
        SPACE,
        row_language=row_language,
    )
    assert panel.summary.per_language_escalation == {}


def test_write_labeled_baseline_round_trip(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.csv"
    pd.DataFrame({"id": ["r1", "r2"], "input": ["a", "b"]}).to_csv(
        baseline, index=False
    )
    panel = aggregate_votes(
        _raw(
            r1=_votes("Neutral", "Neutral", "Neutral", "Neutral", "Neutral"),
            r2=_votes("Curt", "Curt", "Curt", "Curt", "Neutral"),
        ),
        "gpt-4o",
        SPACE,
    )
    out = tmp_path / "labeled.csv"
    write_labeled_baseline(panel, baseline, out)
    df = pd.read_csv(out)
    assert dict(zip(df["id"], df["label"], strict=True)) == {
        "r1": "Neutral",
        "r2": "Curt",
    }


def test_write_labeled_baseline_blocks_unresolved(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.csv"
    pd.DataFrame({"id": ["r1"], "input": ["a"]}).to_csv(baseline, index=False)
    panel = aggregate_votes(
        _raw(r1=_votes("Neutral", "Neutral", "Neutral", "Curt", "Curt")),
        "gpt-4o",
        SPACE,
    )
    with pytest.raises(LabelPanelError, match="escalated and unresolved"):
        write_labeled_baseline(panel, baseline, tmp_path / "out.csv")


def test_write_labeled_baseline_detects_drift(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.csv"
    pd.DataFrame({"id": ["r1", "r2", "r3"], "input": ["a", "b", "c"]}).to_csv(
        baseline, index=False
    )
    panel = aggregate_votes(
        _raw(r1=_votes("Neutral", "Neutral", "Neutral", "Neutral", "Neutral")),
        "gpt-4o",
        SPACE,
    )
    with pytest.raises(LabelPanelError, match="absent from the panel"):
        write_labeled_baseline(panel, baseline, tmp_path / "out.csv")


def test_human_overridden_counts_as_resolved_for_write(tmp_path: Path) -> None:
    # An escalated row the human resolved (final_label set, disposition
    # updated) writes cleanly; the artifact round-trips through the schema.
    baseline = tmp_path / "baseline.csv"
    pd.DataFrame({"id": ["r1"], "input": ["a"]}).to_csv(baseline, index=False)
    panel = aggregate_votes(
        _raw(r1=_votes("Neutral", "Neutral", "Neutral", "Curt", "Curt")),
        "gpt-4o",
        SPACE,
    )
    panel.rows[0].final_label = "Neutral"
    panel.rows[0].disposition = "human_resolved"
    reloaded = LabelPanelJSON(**panel.model_dump())
    out = tmp_path / "labeled.csv"
    write_labeled_baseline(reloaded, baseline, out)
    assert pd.read_csv(out)["label"].tolist() == ["Neutral"]


# --------------------------------------------------------------------------- #
# adjudication workflow (bucket 6): escalation queue + resolve/override
# --------------------------------------------------------------------------- #


def _panel_for_adjudication() -> LabelPanelJSON:
    return aggregate_votes(
        _raw(
            r1=_votes("Neutral", "Neutral", "Neutral", "Neutral", "Neutral"),  # auto
            r2=_votes("Curt", "Curt", "Neutral", "Neutral", "Empathetic"),  # escalate
        ),
        "gpt-4o",
        SPACE,
    )


def test_queue_contains_only_escalated_rows(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.csv"
    pd.DataFrame({"id": ["r1", "r2"], "input": ["polite reply", "terse reply"]}).to_csv(
        baseline, index=False
    )
    queue = build_escalation_queue(_panel_for_adjudication(), baseline)
    assert queue["n_escalated"] == 1
    items = queue["items"]
    assert isinstance(items, list)
    only = items[0]
    assert only["row_id"] == "r2"
    assert only["input"] == "terse reply"
    assert only["plurality"] == "Curt"  # sorted tie-break on count 2
    assert len(only["votes"]) == 5


def test_resolve_escalated_row_marks_human_resolved() -> None:
    panel = _panel_for_adjudication()
    updated = apply_decisions(panel, {"r2": "Neutral"})
    r2 = next(r for r in updated.rows if r.row_id == "r2")
    assert r2.disposition == "human_resolved"
    assert r2.final_label == "Neutral"
    assert updated.summary.n_human_resolved == 1
    assert updated.summary.n_escalated == 0


def test_override_frozen_label_marks_human_overridden() -> None:
    panel = _panel_for_adjudication()
    # r1 auto-froze as Neutral; the human overrides it (e.g. a test-set row).
    updated = apply_decisions(panel, {"r1": "Curt"})
    r1 = next(r for r in updated.rows if r.row_id == "r1")
    assert r1.disposition == "human_overridden"
    assert r1.final_label == "Curt"
    assert updated.summary.n_human_overridden == 1
    assert updated.summary.n_auto_accepted == 0


def test_decision_equal_to_frozen_label_is_noop() -> None:
    panel = _panel_for_adjudication()
    updated = apply_decisions(panel, {"r1": "Neutral"})
    r1 = next(r for r in updated.rows if r.row_id == "r1")
    assert r1.disposition == "auto_accepted"  # unchanged
    assert updated.summary.n_auto_accepted == 1


def test_resolve_unknown_row_raises() -> None:
    with pytest.raises(LabelPanelError, match="unknown row"):
        apply_decisions(_panel_for_adjudication(), {"r99": "Neutral"})


def test_resolve_out_of_space_label_raises() -> None:
    with pytest.raises(LabelPanelError, match="outside the label space"):
        apply_decisions(_panel_for_adjudication(), {"r2": "Angry"})


def test_resolve_then_write_round_trip(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.csv"
    pd.DataFrame({"id": ["r1", "r2"], "input": ["a", "b"]}).to_csv(
        baseline, index=False
    )
    panel = apply_decisions(_panel_for_adjudication(), {"r2": "Empathetic"})
    out = tmp_path / "labeled.csv"
    write_labeled_baseline(panel, baseline, out)
    df = pd.read_csv(out)
    assert dict(zip(df["id"], df["label"], strict=True)) == {
        "r1": "Neutral",
        "r2": "Empathetic",
    }
