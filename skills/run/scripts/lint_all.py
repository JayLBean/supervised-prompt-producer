"""Run the whole spp linter family against the shipped artifacts (DESIGN §7.1.13).

A single entry point that aggregates every "Phase 4" linter so a contributor (or
CI) can check the frozen surface with one command:

    python -m scripts.lint_all

It runs, against the shipped templates and catalogs:

- the template-contract linter (all six templates carry their placeholders /
  sections / markers),
- the ENTRY_SCHEMA catalog linter (both advisor catalogs),
- the REPORT.md §5 invariant-block check (invariant #21), and
- the loop_spec.md literal-block immutability check (invariant #18),

returning the union of their violations. The filled-instance checks
(``check_plan`` / ``check_prompt``) take a specific artifact path and so stay in
``lint_templates``; this aggregator covers the frozen-surface freeze guards.
"""

from __future__ import annotations

import argparse
import sys

from ._lint import LintError, Violation, format_violations
from .lint_catalogs import check_all_catalogs
from .lint_templates import (
    check_all_templates,
    check_loop_spec,
    check_report,
    templates_dir,
)


def run_all() -> list[Violation]:
    """Return the union of every shipped-artifact linter's violations."""
    violations: list[Violation] = []
    violations.extend(check_all_templates())
    violations.extend(check_all_catalogs())
    tdir = templates_dir()
    violations.extend(check_report(tdir / "REPORT.md.template"))
    violations.extend(check_loop_spec(tdir / "loop_spec.md.template"))
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run every spp linter against the shipped artifacts."
    )
    parser.parse_args(argv)
    try:
        violations = run_all()
    except LintError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if violations:
        print(format_violations(violations), file=sys.stderr)
        return 1
    print("all linters OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
