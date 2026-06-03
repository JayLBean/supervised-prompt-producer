"""Iteration state journal for v0.8 loop resumption (DESIGN.md §7.1.9).

The loop's unit of recovery is the cognitive *step*, not the whole
iteration. Each iteration directory (``run_NN/``) carries a
``state.json`` journal recording which steps completed and the SHA-256 of
the artifacts each produced. On resume the orchestrator re-enters at the
first step that is not present-and-integral.

This module owns only the journal's data plumbing — hashing, recording a
completion, loading, and integrity-verifying a step. It records step
*completion and artifact identity only*; it never stores a stage's inputs
and never widens a stage's allow-list, so resuming from it cannot leak
score access to the auditor, row content to rule-edit, or prior-iteration
artifacts to discrepancy (the §4.2 isolation contract holds on resume).
Choosing the resume point from a journal is the orchestrator's job
(later bucket), not this module's.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ._io import atomic_write_json
from ._schemas import IterationJournal, StepRecord

JOURNAL_NAME = "state.json"


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 of a file, read in chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def journal_path(iteration_dir: Path) -> Path:
    """The ``state.json`` path inside an iteration directory."""
    return iteration_dir / JOURNAL_NAME


def load_journal(iteration_dir: Path) -> IterationJournal | None:
    """Load the iteration journal, or ``None`` if it does not exist yet.

    A missing journal means the iteration has no recorded progress — the
    resume point is its first step. A present journal is parsed and
    validated; a malformed journal raises rather than being silently
    treated as empty, so corruption is surfaced, not skipped.
    """
    path = journal_path(iteration_dir)
    if not path.exists():
        return None
    return IterationJournal(**json.loads(path.read_text(encoding="utf-8")))


def record_step(
    iteration_dir: Path,
    iteration: int,
    step: str,
    artifact_paths: list[Path],
) -> IterationJournal:
    """Record ``step`` as completed and atomically rewrite the journal.

    Hashes each artifact (paths may be absolute or relative to
    ``iteration_dir``) and stores them keyed by their path *relative to the
    iteration directory*, so the journal is location-independent. Re-running
    a step replaces its prior record in place — completion order is
    preserved and there is never more than one record per step name. The
    journal is written under the atomic ``tmp + fsync + rename`` discipline
    (#16); a torn write leaves the prior journal intact.
    """
    journal = load_journal(iteration_dir) or IterationJournal(iteration=iteration)
    if journal.iteration != iteration:
        raise ValueError(
            f"journal iteration {journal.iteration} does not match {iteration}"
        )

    artifacts: dict[str, str] = {}
    for p in artifact_paths:
        abs_path = p if p.is_absolute() else iteration_dir / p
        rel = abs_path.relative_to(iteration_dir).as_posix()
        artifacts[rel] = sha256_file(abs_path)

    record = StepRecord(step=step, artifacts=artifacts)
    existing = next(
        (i for i, r in enumerate(journal.completed_steps) if r.step == step),
        None,
    )
    if existing is None:
        journal.completed_steps.append(record)
    else:
        journal.completed_steps[existing] = record

    atomic_write_json(journal_path(iteration_dir), journal.model_dump())
    return journal


def step_is_complete(iteration_dir: Path, journal: IterationJournal, step: str) -> bool:
    """True iff ``step`` is recorded and every artifact is present-and-integral.

    A step counts as complete only when it appears in the journal *and* each
    artifact it recorded still exists with a matching SHA-256. A torn write,
    a deleted artifact, or a post-hoc edit fails the check, so the step is
    re-run rather than trusted — the property that makes per-step resumption
    safe (DESIGN.md §7.1.9).
    """
    record = next((r for r in journal.completed_steps if r.step == step), None)
    if record is None:
        return False
    for rel, expected in record.artifacts.items():
        artifact = iteration_dir / rel
        if not artifact.exists() or sha256_file(artifact) != expected:
            return False
    return True
