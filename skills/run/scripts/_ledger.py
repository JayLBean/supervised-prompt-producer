"""Sacred-test-set access ledger (v0.8, DESIGN.md §7.1.9).

The ledger (`data/.test_access.json`) is the handshake between
`/spp-finalize` and spp's `PreToolUse` sacred-test-set hook
(`hooks/sacred_test_guard.py`). `/spp-finalize` **authorizes** its single
held-out read, then **consumes** (seals) the ledger when the evaluation is
done; the hook reads the same file and allows a `data/test.csv` read only
while the status is ``authorized``.

States:

- ``sealed`` — the default (also the meaning of an absent or malformed
  ledger): the test set is closed; the hook denies every `test.csv` read.
- ``authorized`` — `/spp-finalize` has opened its single read window; the
  hook allows `test.csv` reads.
- ``consumed`` — the evaluation is complete; the test set is permanently
  sealed. Re-authorizing raises, so a second `/spp-finalize` cannot re-read
  the sacred test set.

This module is the writer side; the hook is an independent reader (kept
standalone so it ships as a plugin hook), and the two agree on the file
name and the ``status`` field. Reads are fail-closed: anything unparseable
is reported as ``sealed`` (deny), never as authorized.
"""

from __future__ import annotations

import json
from pathlib import Path

from ._io import atomic_write_json

LEDGER_NAME = ".test_access.json"
SEALED = "sealed"
AUTHORIZED = "authorized"
CONSUMED = "consumed"
_VALID = (SEALED, AUTHORIZED, CONSUMED)


class LedgerError(RuntimeError):
    """Raised when an operation would violate the read-once discipline."""


def ledger_path(data_dir: Path) -> Path:
    """The access-ledger path inside a task's data directory."""
    return data_dir / LEDGER_NAME


def read_status(data_dir: Path) -> str:
    """Return the ledger status, fail-closed to ``sealed``.

    An absent, unreadable, malformed, or unrecognized ledger reads as
    ``sealed`` — the safe direction for the sacred test set, and the same
    default the hook applies.
    """
    try:
        data = json.loads(ledger_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return SEALED
    if not isinstance(data, dict):
        return SEALED
    status = data.get("status")
    return status if status in _VALID else SEALED


def _write(data_dir: Path, status: str) -> None:
    atomic_write_json(ledger_path(data_dir), {"status": status})


def seal(data_dir: Path) -> None:
    """Seal the ledger (the default closed state)."""
    _write(data_dir, SEALED)


def authorize(data_dir: Path) -> None:
    """Open the single read window for `/spp-finalize`.

    Refuses when the ledger is already ``consumed`` — the test set has been
    evaluated, and re-reading it would invalidate the held-out guarantee.
    Authorizing from ``sealed`` (or an absent ledger) or re-authorizing an
    interrupted, not-yet-consumed window is allowed and idempotent.
    """
    if read_status(data_dir) == CONSUMED:
        raise LedgerError(
            "test set already evaluated (ledger consumed); re-authorizing "
            "would re-read the sacred test set. Start a new test partition "
            "instead of re-finalizing (DESIGN.md §7.1.9)."
        )
    _write(data_dir, AUTHORIZED)


def consume(data_dir: Path) -> None:
    """Seal the ledger permanently after the single evaluation completes."""
    _write(data_dir, CONSUMED)
