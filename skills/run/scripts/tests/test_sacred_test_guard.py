"""Tests for the sacred-test-set PreToolUse guard (v0.8, DESIGN.md §7.1.9).

The guard is spp's first shipped hook. These tests pin its load-bearing
behavior: it denies any `data/test.csv` read unless the co-located ledger
authorizes it (fail-closed), passes everything else untouched, and speaks
the PreToolUse stdin/stdout contract correctly. The guard lives at
``hooks/sacred_test_guard.py`` (plugin root), outside the scripts package,
so it is loaded here by path.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_HOOK = Path(__file__).resolve().parents[4] / "hooks" / "sacred_test_guard.py"


def _load_guard() -> Any:
    spec = importlib.util.spec_from_file_location("sacred_test_guard", _HOOK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = _load_guard()


def _data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir(exist_ok=True)
    return d


def _write_ledger(tmp_path: Path, status: str | None) -> None:
    d = _data_dir(tmp_path)
    if status is None:
        return  # no ledger
    (d / ".test_access.json").write_text(
        json.dumps({"status": status}), encoding="utf-8"
    )


def _read_event(tmp_path: Path, name: str = "test.csv") -> dict[str, Any]:
    return {
        "tool_name": "Read",
        "tool_input": {"file_path": str(_data_dir(tmp_path) / name)},
        "cwd": str(tmp_path),
    }


def _is_deny(payload: dict[str, Any] | None) -> bool:
    return (
        payload is not None
        and payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    )


# --------------------------------------------------------------------------- #
# decision logic (decide / test_csv_target / ledger_authorizes)
# --------------------------------------------------------------------------- #


def test_read_test_csv_no_ledger_denies(tmp_path: Path) -> None:
    assert _is_deny(guard.decide(_read_event(tmp_path)))


def test_read_test_csv_authorized_allows(tmp_path: Path) -> None:
    _write_ledger(tmp_path, "authorized")
    assert guard.decide(_read_event(tmp_path)) is None


def test_read_test_csv_sealed_denies(tmp_path: Path) -> None:
    _write_ledger(tmp_path, "sealed")
    assert _is_deny(guard.decide(_read_event(tmp_path)))


def test_read_test_csv_consumed_denies(tmp_path: Path) -> None:
    _write_ledger(tmp_path, "consumed")
    assert _is_deny(guard.decide(_read_event(tmp_path)))


def test_malformed_ledger_fails_closed(tmp_path: Path) -> None:
    _data_dir(tmp_path).joinpath(".test_access.json").write_text(
        "{not json", encoding="utf-8"
    )
    assert _is_deny(guard.decide(_read_event(tmp_path)))


def test_read_baseline_passes(tmp_path: Path) -> None:
    assert guard.decide(_read_event(tmp_path, name="baseline.csv")) is None


def test_read_train_dev_passes(tmp_path: Path) -> None:
    assert guard.decide(_read_event(tmp_path, name="train_dev.csv")) is None


def test_test_csv_outside_data_dir_passes(tmp_path: Path) -> None:
    # A test.csv NOT directly inside a data/ dir is not the spp sacred file.
    event = {
        "tool_name": "Read",
        "tool_input": {"file_path": str(tmp_path / "test.csv")},
        "cwd": str(tmp_path),
    }
    assert guard.decide(event) is None


def test_bash_cat_test_csv_denies(tmp_path: Path) -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "cat data/test.csv"},
        "cwd": str(tmp_path),
    }
    assert _is_deny(guard.decide(event))


def test_bash_authorized_allows(tmp_path: Path) -> None:
    _write_ledger(tmp_path, "authorized")
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": f"head {_data_dir(tmp_path) / 'test.csv'}"},
        "cwd": str(tmp_path),
    }
    assert guard.decide(event) is None


def test_bash_grep_abs_path_denies(tmp_path: Path) -> None:
    abs_path = _data_dir(tmp_path) / "test.csv"
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": f"grep secret {abs_path}"},
        "cwd": str(tmp_path),
    }
    assert _is_deny(guard.decide(event))


def test_bash_without_test_csv_passes(tmp_path: Path) -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "ls data/ && wc -l data/train_dev.csv"},
        "cwd": str(tmp_path),
    }
    assert guard.decide(event) is None


def _bash(cmd: str, tmp_path: Path) -> dict[str, Any]:
    return {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(tmp_path)}


def test_bash_relative_dot_path_denies(tmp_path: Path) -> None:
    assert _is_deny(guard.decide(_bash("cat ./data/test.csv", tmp_path)))


def test_bash_nested_dir_path_denies(tmp_path: Path) -> None:
    assert _is_deny(guard.decide(_bash("cat spp/task/data/test.csv", tmp_path)))


def test_bash_adjacent_extension_passes(tmp_path: Path) -> None:
    # data/test.csv.gz / .bak are DIFFERENT files — not the sacred test set.
    assert guard.decide(_bash("gunzip data/test.csv.gz", tmp_path)) is None
    assert guard.decide(_bash("cat data/test.csv.bak", tmp_path)) is None


def test_bash_other_data_segment_passes(tmp_path: Path) -> None:
    # `mydata/` is a different directory; `data` must begin a path segment.
    assert guard.decide(_bash("cat mydata/test.csv", tmp_path)) is None


def test_unrelated_tool_passes(tmp_path: Path) -> None:
    event = {"tool_name": "Edit", "tool_input": {"file_path": "x"}, "cwd": "."}
    assert guard.decide(event) is None


# --------------------------------------------------------------------------- #
# stdin/stdout contract (run the script as the harness would)
# --------------------------------------------------------------------------- #


def _run(event: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(event) if not isinstance(event, str) else event,
        capture_output=True,
        text=True,
    )


def test_subprocess_deny_emits_json(tmp_path: Path) -> None:
    r = _run(_read_event(tmp_path))
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_subprocess_allow_is_silent(tmp_path: Path) -> None:
    _write_ledger(tmp_path, "authorized")
    r = _run(_read_event(tmp_path))
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_subprocess_pass_other_file_is_silent(tmp_path: Path) -> None:
    r = _run(_read_event(tmp_path, name="baseline.csv"))
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_subprocess_malformed_stdin_is_silent() -> None:
    r = _run("not json at all")
    assert r.returncode == 0
    assert r.stdout.strip() == ""
