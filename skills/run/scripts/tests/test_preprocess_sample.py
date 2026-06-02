"""Runs the preprocess sub-skill's sample script end-to-end.

Executes the worked-example `preprocess.py`
(sub-skills/preprocess/fixtures/multilingual-reviews/) as a subprocess on
its raw input, and checks that the canonical output matches the committed
expected_baseline.csv and that re-running is byte-identical (the
determinism contract, preprocess/SKILL.md §5).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "sub-skills"
    / "preprocess"
    / "fixtures"
    / "multilingual-reviews"
)


def _run(out_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(_FIXTURE / "preprocess.py"),
            "--raw",
            str(_FIXTURE / "inputs" / "raw.csv"),
            "--out",
            str(out_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_sample_matches_expected(tmp_path: Path) -> None:
    out = tmp_path / "baseline.csv"
    _run(out)
    produced = pd.read_csv(out)
    expected = pd.read_csv(_FIXTURE / "expected_baseline.csv")
    pd.testing.assert_frame_equal(produced, expected)


def test_sample_is_deterministic(tmp_path: Path) -> None:
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    _run(a)
    _run(b)
    assert a.read_bytes() == b.read_bytes()


def test_sample_canonical_columns(tmp_path: Path) -> None:
    out = tmp_path / "baseline.csv"
    _run(out)
    cols = list(pd.read_csv(out).columns)
    assert cols == ["id", "input", "label", "language"]
