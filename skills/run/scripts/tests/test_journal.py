"""Tests for the iteration state journal (v0.8 loop resumption).

The journal is what makes per-step resumption safe (DESIGN.md §7.1.9): a
step counts as complete only when it is recorded AND every artifact it
produced is present with a matching hash, so torn writes and post-hoc
edits are re-run rather than trusted. The journal records completion and
artifact identity only — never a stage's inputs — so it cannot widen an
allow-list on resume.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from spp_scripts._journal import (
    journal_path,
    load_journal,
    record_step,
    sha256_file,
    step_is_complete,
)


def _artifact(d: Path, name: str, content: str) -> Path:
    p = d / name
    p.write_text(content, encoding="utf-8")
    return p


def test_load_missing_journal_is_none(tmp_path: Path) -> None:
    assert load_journal(tmp_path) is None


def test_record_creates_journal_and_hashes_artifacts(tmp_path: Path) -> None:
    art = _artifact(tmp_path, "eval.json", '{"primary_value": 1.0}')
    journal = record_step(tmp_path, 1, "scoring", [art])

    assert journal_path(tmp_path).exists()
    assert journal.iteration == 1
    assert [r.step for r in journal.completed_steps] == ["scoring"]
    assert journal.completed_steps[0].artifacts == {"eval.json": sha256_file(art)}


def test_record_uses_relative_keys_for_absolute_and_relative_paths(
    tmp_path: Path,
) -> None:
    _artifact(tmp_path, "a.json", "a")
    _artifact(tmp_path, "b.json", "b")
    journal = record_step(tmp_path, 0, "scoring", [tmp_path / "a.json", Path("b.json")])
    assert set(journal.completed_steps[0].artifacts) == {"a.json", "b.json"}


def test_record_is_idempotent_replacing_in_place(tmp_path: Path) -> None:
    art = _artifact(tmp_path, "eval.json", "v1")
    record_step(tmp_path, 1, "scoring", [art])
    art.write_text("v2", encoding="utf-8")
    journal = record_step(tmp_path, 1, "scoring", [art])

    # one record for the step, updated to the new hash
    assert [r.step for r in journal.completed_steps] == ["scoring"]
    assert journal.completed_steps[0].artifacts["eval.json"] == sha256_file(art)


def test_completion_order_preserved_across_steps(tmp_path: Path) -> None:
    record_step(tmp_path, 2, "scoring", [_artifact(tmp_path, "eval.json", "e")])
    record_step(tmp_path, 2, "discrepancy", [_artifact(tmp_path, "disc.md", "d")])
    record_step(tmp_path, 2, "auditor", [_artifact(tmp_path, "aud.md", "a")])
    journal = load_journal(tmp_path)
    assert journal is not None
    assert [r.step for r in journal.completed_steps] == [
        "scoring",
        "discrepancy",
        "auditor",
    ]


def test_iteration_mismatch_raises(tmp_path: Path) -> None:
    record_step(tmp_path, 1, "scoring", [_artifact(tmp_path, "eval.json", "e")])
    with pytest.raises(ValueError, match="does not match"):
        record_step(tmp_path, 2, "discrepancy", [_artifact(tmp_path, "d.md", "d")])


def test_record_rejects_empty_artifacts(tmp_path: Path) -> None:
    # An empty artifact list would make the step vacuously "complete" with no
    # integrity backing — reject it at the source (reviewer finding, PR #92).
    with pytest.raises(ValueError, match="at least one artifact"):
        record_step(tmp_path, 1, "scoring", [])


def test_record_rejects_artifact_outside_iteration_dir(tmp_path: Path) -> None:
    outside = tmp_path.parent / "stray.json"
    outside.write_text("x", encoding="utf-8")
    iter_dir = tmp_path / "run_01"
    iter_dir.mkdir()
    with pytest.raises(ValueError, match="outside the iteration directory"):
        record_step(iter_dir, 1, "scoring", [outside])


def test_step_is_complete_true_when_present_and_integral(tmp_path: Path) -> None:
    art = _artifact(tmp_path, "eval.json", "ok")
    journal = record_step(tmp_path, 1, "scoring", [art])
    assert step_is_complete(tmp_path, journal, "scoring") is True


def test_step_is_complete_false_when_unrecorded(tmp_path: Path) -> None:
    journal = record_step(tmp_path, 1, "scoring", [_artifact(tmp_path, "e.json", "e")])
    assert step_is_complete(tmp_path, journal, "auditor") is False


def test_step_is_complete_false_when_artifact_edited(tmp_path: Path) -> None:
    art = _artifact(tmp_path, "eval.json", "original")
    journal = record_step(tmp_path, 1, "scoring", [art])
    art.write_text("tampered", encoding="utf-8")  # hash now mismatches
    assert step_is_complete(tmp_path, journal, "scoring") is False


def test_step_is_complete_false_when_artifact_deleted(tmp_path: Path) -> None:
    art = _artifact(tmp_path, "eval.json", "original")
    journal = record_step(tmp_path, 1, "scoring", [art])
    art.unlink()
    assert step_is_complete(tmp_path, journal, "scoring") is False


def test_round_trip_through_disk(tmp_path: Path) -> None:
    record_step(tmp_path, 3, "scoring", [_artifact(tmp_path, "eval.json", "e")])
    record_step(tmp_path, 3, "rule_edit", [_artifact(tmp_path, "prompt.md", "p")])
    reloaded = load_journal(tmp_path)
    assert reloaded is not None
    assert reloaded.iteration == 3
    assert step_is_complete(tmp_path, reloaded, "scoring") is True
    assert step_is_complete(tmp_path, reloaded, "rule_edit") is True
