"""Audit: per-step resume does not weaken the §4.2 isolation contract.

v0.8 loop resumption (DESIGN.md §7.1.9) re-enters an interrupted iteration
at its first incomplete step. The load-bearing guarantee is that this
re-entry changes *when* a stage runs, never *what it sees*: a resumed
discrepancy subagent still gets no prior-iteration artifacts, a resumed
rule-edit still gets no row content, a resumed auditor stays score-blind.

That guarantee rests on two structural facts, which these tests pin as
executable assertions rather than prose promises:

1. **The journal is consumed only by the orchestrator, for control flow.**
   Its public surface (`first_incomplete`, `load_journal`) returns a step
   *name* or a journal of names + hashes — never artifact content. Stages
   are re-invoked by the orchestrator, which rebuilds each stage's
   allow-list from current-iteration sources; no stage reads the journal.

2. **The journal records artifact *identity* (a SHA-256), never artifact
   *content*.** So even when a journaled artifact is score-bearing
   (`eval.json`) or row-bearing (a baseline slice), the journal cannot leak
   that content — there is no field for it to live in.

If a future change tried to smuggle a stage input into the journal (an
``inputs`` field, an inlined artifact body, a cached score), the structural
test below fails. That is the regression guard the resume-isolation
guarantee needs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from spp_scripts._journal import (
    LOOP_STEPS,
    first_incomplete,
    journal_path,
    load_journal,
    record_step,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")

# A marker standing in for the kind of content the isolation contract keeps
# out of stages: a gold label / score that the auditor and rule-edit stages
# must never see, and row content the rule-edit stage must never see.
_SECRET = "SCORE_y_true_POSITIVE_and_raw_row_text"


def _score_bearing_artifact(d: Path, name: str) -> Path:
    p = d / name
    p.write_text(
        json.dumps({"per_row": [{"row_id": "r1", "secret": _SECRET}]}),
        encoding="utf-8",
    )
    return p


def test_journal_stores_hash_not_artifact_content(tmp_path: Path) -> None:
    # Journal a score-bearing artifact, then read the raw state.json text.
    art = _score_bearing_artifact(tmp_path, "eval.json")
    record_step(tmp_path, 1, "metrics", [art])

    raw = journal_path(tmp_path).read_text(encoding="utf-8")
    # The artifact's content is NOT in the journal...
    assert _SECRET not in raw
    # ...only its identity (a sha256) is.
    journal = load_journal(tmp_path)
    assert journal is not None
    digest = journal.completed_steps[0].artifacts["eval.json"]
    assert _SHA256.match(digest)
    assert _SECRET not in digest


def test_journal_serialized_shape_is_identity_only(tmp_path: Path) -> None:
    # A structural guard: the journal's keys are limited to identity/control
    # fields. No place for a stage input to hide. If someone adds an
    # input-carrying field, this fails.
    record_step(tmp_path, 1, "inference", [_score_bearing_artifact(tmp_path, "r.json")])
    data = json.loads(journal_path(tmp_path).read_text(encoding="utf-8"))

    assert set(data) == {"schema_version", "iteration", "completed_steps"}
    for record in data["completed_steps"]:
        assert set(record) == {"step", "artifacts"}
        assert isinstance(record["step"], str)
        # every artifact value is a bare sha256 digest — never content
        for path, digest in record["artifacts"].items():
            assert isinstance(path, str)
            assert _SHA256.match(digest), f"{path!r} maps to non-digest {digest!r}"


def test_resume_point_surface_is_control_flow_only(tmp_path: Path) -> None:
    # The orchestrator's resume query returns a step NAME (or None), never
    # anything derived from artifact content.
    art = _score_bearing_artifact(tmp_path, "eval.json")
    record_step(
        tmp_path, 1, "inference", [_score_bearing_artifact(tmp_path, "res.json")]
    )
    record_step(tmp_path, 1, "metrics", [art])
    journal = load_journal(tmp_path)

    resume = first_incomplete(tmp_path, journal)
    assert resume == "discrepancy"  # the next step name, nothing more
    assert resume in LOOP_STEPS
    assert _SECRET not in (resume or "")


def test_loaded_journal_exposes_no_artifact_content(tmp_path: Path) -> None:
    # Even fully deserialized in memory, the journal carries names + hashes
    # only — the property that lets the orchestrator use it for control flow
    # without it ever becoming a stage-input vector.
    record_step(
        tmp_path, 2, "metrics", [_score_bearing_artifact(tmp_path, "eval.json")]
    )
    journal = load_journal(tmp_path)
    assert journal is not None
    blob = journal.model_dump_json()
    assert _SECRET not in blob
