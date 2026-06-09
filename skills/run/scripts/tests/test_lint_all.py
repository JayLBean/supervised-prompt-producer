"""Tests for the aggregate linter entry point.

``run_all`` runs every shipped-artifact linter; against the real repo it must be
clean, which makes it the single freeze guard CI runs.
"""

from __future__ import annotations

from spp_scripts.lint_all import main, run_all


def test_run_all_clean_on_shipped_artifacts() -> None:
    violations = run_all()
    assert violations == [], "\n".join(
        f"{v.target}: [{v.linter}/{v.rule}] {v.message}" for v in violations
    )


def test_cli_exit_zero() -> None:
    assert main([]) == 0
