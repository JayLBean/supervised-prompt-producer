"""Tests for the sacred-test-set access ledger (v0.8, DESIGN.md §7.1.9).

Two layers: the ledger's own state machine, and the end-to-end agreement
between the writer (`_ledger`, used by `/spp-finalize`) and the independent
reader (the `PreToolUse` hook). The e2e tests are what prove the handshake
makes the guard *live* and *read-once*: the hook denies a `data/test.csv`
read until `authorize`, allows it while authorized, and denies again after
`consume` — and `authorize` after `consume` refuses outright.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from spp_scripts._ledger import (
    AUTHORIZED,
    CONSUMED,
    SEALED,
    LedgerError,
    authorize,
    consume,
    ledger_path,
    read_status,
    seal,
)

_HOOK = Path(__file__).resolve().parents[4] / "hooks" / "sacred_test_guard.py"


def _load_guard() -> Any:
    spec = importlib.util.spec_from_file_location("sacred_test_guard", _HOOK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = _load_guard()


def _data(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir(exist_ok=True)
    return d


def _hook_denies_test_read(data_dir: Path) -> bool:
    event = {
        "tool_name": "Read",
        "tool_input": {"file_path": str(data_dir / "test.csv")},
        "cwd": str(data_dir.parent),
    }
    payload = guard.decide(event)
    return (
        payload is not None
        and payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    )


# --------------------------------------------------------------------------- #
# ledger state machine
# --------------------------------------------------------------------------- #


def test_absent_ledger_reads_sealed(tmp_path: Path) -> None:
    assert read_status(_data(tmp_path)) == SEALED


def test_malformed_ledger_reads_sealed(tmp_path: Path) -> None:
    d = _data(tmp_path)
    ledger_path(d).write_text("{ not json", encoding="utf-8")
    assert read_status(d) == SEALED


def test_unknown_status_reads_sealed(tmp_path: Path) -> None:
    d = _data(tmp_path)
    ledger_path(d).write_text(json.dumps({"status": "weird"}), encoding="utf-8")
    assert read_status(d) == SEALED


def test_seal_authorize_consume_transitions(tmp_path: Path) -> None:
    d = _data(tmp_path)
    seal(d)
    assert read_status(d) == SEALED
    authorize(d)
    assert read_status(d) == AUTHORIZED
    consume(d)
    assert read_status(d) == CONSUMED


def test_authorize_from_absent_is_allowed(tmp_path: Path) -> None:
    d = _data(tmp_path)
    authorize(d)  # no prior ledger
    assert read_status(d) == AUTHORIZED


def test_reauthorize_interrupted_window_is_allowed(tmp_path: Path) -> None:
    d = _data(tmp_path)
    authorize(d)
    authorize(d)  # idempotent re-open of a not-yet-consumed window
    assert read_status(d) == AUTHORIZED


def test_authorize_after_consume_refuses(tmp_path: Path) -> None:
    d = _data(tmp_path)
    authorize(d)
    consume(d)
    with pytest.raises(LedgerError, match="already evaluated"):
        authorize(d)
    # the refusal does not silently re-open the window
    assert read_status(d) == CONSUMED


# --------------------------------------------------------------------------- #
# end-to-end: writer (_ledger) <-> reader (hook) agreement
# --------------------------------------------------------------------------- #


def test_hook_denies_until_authorized_then_allows_then_denies(tmp_path: Path) -> None:
    d = _data(tmp_path)
    # sealed/absent -> the loop's world: denied.
    assert _hook_denies_test_read(d)

    # /spp-finalize opens the window -> allowed.
    authorize(d)
    assert not _hook_denies_test_read(d)

    # evaluation done -> sealed -> denied again (read-once).
    consume(d)
    assert _hook_denies_test_read(d)


def test_hook_denies_when_sealed(tmp_path: Path) -> None:
    d = _data(tmp_path)
    seal(d)
    assert _hook_denies_test_read(d)
