#!/usr/bin/env python3
"""spp's sacred-test-set PreToolUse guard (v0.8, DESIGN.md §7.1.9).

spp's first shipped hook. It makes the read-once protection of the sacred
test set **mechanical** instead of disciplinary: it intercepts every `Read`
and `Bash` tool call and **denies** any read of a task's `data/test.csv`
unless the co-located access ledger authorizes it. The loop reads
`data/train_dev.csv` (which contains no test rows), so a test-set read
during optimization is always a mistake — and now a blocked one.

The one legitimate reader is `/spp-finalize`, which performs an
authorization handshake (writes `data/.test_access.json` with
`status: "authorized"`) before its single held-out evaluation, then seals
the ledger afterward. This script only *reads* that ledger; the handshake
and the actual test read are `/spp-finalize`'s job (a later bucket).

**Fail-closed.** Anything ambiguous about a `data/test.csv` read — a
missing, unreadable, or non-`authorized` ledger — results in a deny. The
sacred test set is the one place spp errs toward refusing.

**Honest boundary (DESIGN.md §7.1.9).** This is a guardrail, not a sandbox.
It blocks the realistic leak paths — the `Read` tool and shell reads that
name the path — but a determined *indirect* read (a script that computes
the path at runtime without the string appearing in the command) can evade
string matching. It raises test-set protection from discipline to a
harness that refuses the common paths; it does not claim more.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

TEST_CSV_NAME = "test.csv"
DATA_DIR_NAME = "data"
LEDGER_NAME = ".test_access.json"
_GUARDED = f"{DATA_DIR_NAME}/{TEST_CSV_NAME}"
_BASH_PATH = re.compile(r"(\S*" + re.escape(_GUARDED) + r")")

_DENY_REASON = (
    "spp sacred-test-set guard: reading the test partition "
    "(data/test.csv) is blocked. The test set may be read only during "
    "/spp-finalize's single authorized evaluation (DESIGN.md §7.1.9); the "
    "optimization loop reads data/train_dev.csv, which excludes test rows. "
    "If this is /spp-finalize, run its authorization handshake first. "
    "Otherwise this read would contaminate the held-out evaluation."
)


def _resolve(path_str: str, cwd: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else Path(cwd) / p


def test_csv_target(
    tool_name: str, tool_input: dict[str, Any], cwd: str
) -> Path | None:
    """Return the `data/test.csv` path this call would read, or None.

    A `Read` is guarded when its `file_path` is a `test.csv` directly inside
    a `data/` directory. A `Bash` call is guarded when its command names a
    `.../data/test.csv` path (best-effort string match; see the honest
    boundary in the module docstring).
    """
    if tool_name == "Read":
        fp = tool_input.get("file_path")
        if not isinstance(fp, str) or not fp:
            return None
        p = _resolve(fp, cwd)
        if p.name == TEST_CSV_NAME and p.parent.name == DATA_DIR_NAME:
            return p
        return None
    if tool_name == "Bash":
        cmd = tool_input.get("command")
        if not isinstance(cmd, str):
            return None
        m = _BASH_PATH.search(cmd)
        if m:
            return _resolve(m.group(1), cwd)
        return None
    return None


def ledger_authorizes(test_csv_path: Path) -> bool:
    """True iff the ledger co-located with test.csv grants authorization.

    Fail-closed: a missing, unreadable, or malformed ledger, or any status
    other than ``"authorized"``, returns False (deny).
    """
    ledger = test_csv_path.parent / LEDGER_NAME
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and data.get("status") == "authorized"


def decide(event: dict[str, Any]) -> dict[str, Any] | None:
    """Return a deny payload for a guarded, unauthorized read; else None.

    None means "do not interfere" — either the call does not read
    test.csv, or the ledger authorizes it.
    """
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    cwd = event.get("cwd") or "."
    if not isinstance(tool_input, dict):
        return None
    target = test_csv_target(tool_name, tool_input, cwd)
    if target is None or ledger_authorizes(target):
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": _DENY_REASON,
        }
    }


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except ValueError:
        # Not a parseable hook event — not our call to make.
        return 0
    if not isinstance(event, dict):
        return 0
    payload = decide(event)
    if payload is not None:
        print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
