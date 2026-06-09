"""Tests for the template-contract and plan.md validation-rule linters.

Two layers:

- The shipped templates must satisfy their frozen contracts (this is the freeze
  guard — if a future edit drops a required placeholder or section, the suite
  goes red), and ``check_template`` must actually *catch* a corrupted template.
- ``check_plan`` must pass a valid template-conformant ``plan.md`` and flag the
  specific rule for each kind of defect.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from spp_scripts._lint import (
    LintError,
    Violation,
    field_value,
    placeholders,
    section_headings,
    unresolved_placeholders,
)
from spp_scripts.lint_templates import (
    TEMPLATE_CONTRACTS,
    TemplateContract,
    _table_rows,
    check_all_templates,
    check_plan,
    check_template,
    main,
    templates_dir,
)

# --------------------------------------------------------------------------- #
# _lint harness
# --------------------------------------------------------------------------- #


def test_placeholders_and_unresolved() -> None:
    text = "a {{FOO}} b {{BAR_1}} c"
    assert placeholders(text) == {"FOO", "BAR_1"}
    assert unresolved_placeholders(text) == ["{{FOO}}", "{{BAR_1}}"]
    assert unresolved_placeholders("no braces here") == []


def test_field_value_and_headings() -> None:
    text = "## 7. Splits\n\n**Auditor configuration:** per-iteration\n"
    assert field_value(text, "Auditor configuration") == "per-iteration"
    assert field_value(text, "Absent label") is None
    assert "7. Splits" in section_headings(text)


def test_read_text_missing(tmp_path: Path) -> None:
    with pytest.raises(LintError, match="cannot read"):
        from spp_scripts._lint import read_text

        read_text(tmp_path / "nope.md")


# --------------------------------------------------------------------------- #
# Template contracts — the shipped templates must conform
# --------------------------------------------------------------------------- #


def test_shipped_templates_satisfy_contracts() -> None:
    violations = check_all_templates()
    assert violations == [], "\n".join(
        f"{v.target}: {v.rule}: {v.message}" for v in violations
    )


def test_all_six_templates_are_contracted() -> None:
    names = {c.filename for c in TEMPLATE_CONTRACTS}
    assert names == {
        "plan.md.template",
        "prompt_v01.md.template",
        "loop_spec.md.template",
        "REPORT.md.template",
        "pipeline.md.template",
        "preprocess.py.template",
    }
    # Every contracted file actually exists in the shipped templates dir.
    for name in names:
        assert (templates_dir() / name).exists()


def test_check_template_catches_missing_placeholder(tmp_path: Path) -> None:
    contract = TemplateContract(
        filename="x.template",
        required_placeholders=frozenset({"NEEDED"}),
        required_sections=("Only section",),
        required_markers=("MARKER",),
    )
    path = tmp_path / "x.template"
    path.write_text("## Only section\nMARKER and {{PRESENT}}\n", encoding="utf-8")
    rules = {v.rule for v in check_template(path, contract)}
    assert rules == {"missing-placeholder"}


def test_check_template_catches_missing_section_and_marker(tmp_path: Path) -> None:
    contract = TemplateContract(
        filename="y.template",
        required_placeholders=frozenset({"PRESENT"}),
        required_sections=("Required heading",),
        required_markers=("REQUIRED_MARKER",),
    )
    path = tmp_path / "y.template"
    path.write_text("## Other heading\n{{PRESENT}}\n", encoding="utf-8")
    rules = {v.rule for v in check_template(path, contract)}
    assert rules == {"missing-section", "missing-marker"}


def test_check_all_templates_reports_missing_file(tmp_path: Path) -> None:
    violations = check_all_templates(tmp_path)
    assert violations
    assert all(v.rule == "missing-file" for v in violations)
    assert len(violations) == len(TEMPLATE_CONTRACTS)


# --------------------------------------------------------------------------- #
# plan.md filled-instance validation
# --------------------------------------------------------------------------- #


def _valid_plan() -> str:
    return (
        "# spp plan — my-task\n\n"
        "## 1. Task overview\n\n"
        "**Task mode:** classification\n\n"
        "## 7. Splits\n\n"
        "**Split ratios:** train 60% / dev 20% / test 20%\n\n"
        "**Sacred test set acknowledgment:** acknowledged\n\n"
        "**Auditor configuration:** per-iteration, no-score-access\n\n"
        "## 9. Decision rules at HITL gates\n\n"
        "| Gate | Approval phrase | Notes |\n"
        "|---|---|---|\n"
        "| G1 — plan approval | approved, proceed | |\n"
        "| G2 — baseline review | approved | |\n"
        "| G3 — split confirmation | splits look right | |\n"
        "| G4 — dry-run gate | dry run ok | |\n"
        "| G5 — finalization | finalize it | |\n"
        "| G6 — production decision | ship it | |\n\n"
        "## 11. Plan revision log\n\n"
        "| Date | Plan version | Reason | By |\n"
        "|---|---|---|---|\n"
        "| 2026-06-08 | v1 | Initial plan via /spp-init | sess-1 |\n"
        "| 2026-06-08 | v2 | technique adoption | sess-1 |\n"
    )


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "plan.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_valid_plan_passes(tmp_path: Path) -> None:
    assert check_plan(_write(tmp_path, _valid_plan())) == []


def test_plan_rule1_unresolved_placeholder(tmp_path: Path) -> None:
    text = _valid_plan().replace("classification", "{{TASK_MODE}}")
    rules = {v.rule for v in check_plan(_write(tmp_path, text))}
    assert "rule 1" in rules


def test_plan_rule2_non_kebab_name(tmp_path: Path) -> None:
    text = _valid_plan().replace("# spp plan — my-task", "# spp plan — My Task")
    rules = {v.rule for v in check_plan(_write(tmp_path, text))}
    assert "rule 2" in rules


def test_plan_rule7_sacred_ack(tmp_path: Path) -> None:
    text = _valid_plan().replace(
        "**Sacred test set acknowledgment:** acknowledged",
        "**Sacred test set acknowledgment:** yes",
    )
    rules = {v.rule for v in check_plan(_write(tmp_path, text))}
    assert "rule 7" in rules


def test_plan_rule8_auditor_config(tmp_path: Path) -> None:
    text = _valid_plan().replace(
        "**Auditor configuration:** per-iteration, no-score-access",
        "**Auditor configuration:** per-iteration",
    )
    rules = {v.rule for v in check_plan(_write(tmp_path, text))}
    assert "rule 8" in rules


def test_plan_rule9_splits_sum(tmp_path: Path) -> None:
    text = _valid_plan().replace(
        "train 60% / dev 20% / test 20%", "train 60% / dev 20% / test 30%"
    )
    rules = {v.rule for v in check_plan(_write(tmp_path, text))}
    assert "rule 9" in rules


def test_plan_rule11_empty_gate_phrase(tmp_path: Path) -> None:
    text = _valid_plan().replace(
        "| G4 — dry-run gate | dry run ok |", "| G4 — dry-run gate |  |"
    )
    rules = {v.rule for v in check_plan(_write(tmp_path, text))}
    assert "rule 11" in rules


def test_plan_rule12_non_monotonic_versions(tmp_path: Path) -> None:
    text = _valid_plan().replace(
        "| 2026-06-08 | v2 | technique adoption | sess-1 |",
        "| 2026-06-08 | v1 | technique adoption | sess-1 |",
    )
    rules = {v.rule for v in check_plan(_write(tmp_path, text))}
    assert "rule 12" in rules


def test_plan_rule17_bad_task_mode(tmp_path: Path) -> None:
    text = _valid_plan().replace(
        "**Task mode:** classification", "**Task mode:** generation"
    )
    rules = {v.rule for v in check_plan(_write(tmp_path, text))}
    assert "rule 17" in rules


def test_plan_task_mode_absent_is_ok(tmp_path: Path) -> None:
    # Absent TASK_MODE reads as the classification default (rule 17) — no violation.
    text = _valid_plan().replace("**Task mode:** classification\n\n", "")
    rules = {v.rule for v in check_plan(_write(tmp_path, text))}
    assert "rule 17" not in rules


def test_table_rows_skips_decoy_prose_line() -> None:
    # A prose line mentioning the header phrase next to a pipe, but NOT followed
    # by a separator row, must be skipped; the scan continues to the real table.
    # This asserts on _table_rows directly because it is where old vs. new
    # behavior differs: the old code mis-anchored on the decoy and leaked the
    # header + separator in as data rows; the new code returns only the genuine
    # data rows. (check_plan's rule 11 would pass either way, so it cannot guard
    # this fix on its own.)
    text = (
        "Note: the | Approval phrase | column must never be empty.\n"
        "\n"
        "| Gate | Approval phrase | Notes |\n"
        "|---|---|---|\n"
        "| G1 | approved | |\n"
        "| G2 | ship it | |\n"
    )
    rows = _table_rows(text, "Approval phrase")
    assert rows == [["G1", "approved", ""], ["G2", "ship it", ""]]
    # The header and separator must not leak in as data rows.
    assert ["Gate", "Approval phrase", "Notes"] not in rows
    assert not any(set(cells) <= {"---", ""} for cells in rows)


def test_plan_decoy_prose_before_table_is_not_a_false_positive(tmp_path: Path) -> None:
    # End-to-end: a decoy prose line before the real gate table does not produce
    # a spurious rule 11 violation on an otherwise-valid plan.
    decoy = "Note: the | Approval phrase | column must never be empty.\n\n"
    text = _valid_plan().replace(
        "## 9. Decision rules at HITL gates\n\n",
        "## 9. Decision rules at HITL gates\n\n" + decoy,
    )
    rules = {v.rule for v in check_plan(_write(tmp_path, text))}
    assert "rule 11" not in rules


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def test_cli_templates_ok() -> None:
    assert main(["templates"]) == 0


def test_cli_plan_ok(tmp_path: Path) -> None:
    path = _write(tmp_path, _valid_plan())
    assert main(["plan", str(path)]) == 0


def test_cli_plan_flags_bad(tmp_path: Path) -> None:
    path = _write(tmp_path, _valid_plan().replace("acknowledged", "nope"))
    assert main(["plan", str(path)]) == 1


def test_violation_is_frozen() -> None:
    v = Violation("plan", "plan.md", "rule 1", "msg")
    with pytest.raises(AttributeError):
        v.rule = "rule 2"  # type: ignore[misc]
