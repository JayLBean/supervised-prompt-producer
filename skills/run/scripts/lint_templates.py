"""Template-contract and plan.md validation-rule linters (DESIGN §7.1.13).

Two mechanical checks that v1.0 promised as "Phase 4" work:

- ``check_template`` validates a shipped ``.template`` against a frozen contract:
  every required ``{{PLACEHOLDER}}`` and every required section heading (and, for
  the Python template, required code markers) must be present. This guards the
  templates, which are part of the frozen surface — a future edit that drops a
  placeholder or renames a section is caught instead of silently shipping.

- ``check_plan`` validates a *filled* ``plan.md`` against the mechanically
  robust subset of the template's "Validation rules" list: no unresolved
  placeholders (rule 1), kebab-case task name (rule 2), the sacred-test
  acknowledgment and auditor-isolation literals (rules 7, 8 — invariant #4/#6
  guards), the split percentages summing to 100 (rule 9), every HITL gate
  carrying a non-placeholder approval phrase (rule 11), a monotonic revision log
  (rule 12), and a valid task mode (rule 17). The rules that need a JSON-Schema
  parse or the metric catalog (3, 4, 5) stay the schema-designer / metric-design
  job at gate G1; this linter is the mechanical safety net, documented in
  ``PLAN_RULES_DELEGATED``.

No model, no scores — pure text checks. Both return ``list[Violation]``; the CLI
turns a non-empty list into a non-zero exit, the pytest suite into a failure.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from ._lint import (
    LintError,
    Violation,
    field_value,
    format_violations,
    placeholders,
    read_text,
    section_headings,
    unresolved_placeholders,
)

# Rules whose full check needs context this text-only linter does not have; they
# remain the schema-designer / metric-design responsibility, verified at G1.
PLAN_RULES_DELEGATED = (
    "rule 3 (OUTPUT_SCHEMA JSON-Schema validity — schema-designer §3.4)",
    "rule 4 (METRIC_NAME in the allowed set — metric-design §6)",
    "rule 5 (METRIC_INDEPENDENCE_NOTE present — metric-design §5)",
)

VALID_TASK_MODES = frozenset({"classification", "extraction"})


@dataclass(frozen=True)
class TemplateContract:
    """The frozen contract a single ``.template`` must satisfy."""

    filename: str
    required_placeholders: frozenset[str]
    required_sections: tuple[str, ...] = ()
    # Literal substrings that must appear verbatim (e.g. Python defs, XML tags).
    required_markers: tuple[str, ...] = ()


# The six templates and their frozen contracts. Placeholder/section lists are the
# load-bearing subset — enough to catch a corrupted or truncated template without
# pinning every repeated field-index placeholder.
TEMPLATE_CONTRACTS: tuple[TemplateContract, ...] = (
    TemplateContract(
        filename="plan.md.template",
        required_placeholders=frozenset(
            {
                "TASK_NAME",
                "TASK_MODE",
                "OUTPUT_SCHEMA",
                "MODEL_IDENTIFIER",
                "SACRED_TEST_ACK",
                "AUDITOR_CONFIG",
                "PLAN_VERSION",
                "TRAIN_PCT",
                "DEV_PCT",
                "TEST_PCT",
                "G1_APPROVAL",
                "G2_APPROVAL",
                "G3_APPROVAL",
                "G4_APPROVAL",
                "G5_APPROVAL",
                "G6_APPROVAL",
            }
        ),
        required_sections=(
            "1. Task overview",
            "2. Output schema and per-field definitions",
            "3. Success criteria",
            "4. Per-field metrics, aggregate strategy, and floors",
            "5. Model and lock-in posture",
            "6. Baseline",
            "7. Splits",
            "8. Loop scope and stop criteria",
            "9. Decision rules at HITL gates",
            "10. Open questions / known unknowns",
            "11. Plan revision log",
            "Validation rules",
        ),
    ),
    TemplateContract(
        filename="prompt_v01.md.template",
        required_placeholders=frozenset(
            {
                "PERSONA_CONTENT",
                "TASK_CONTENT",
                "RULES_CONTENT",
                "OUTPUT_FORMAT_CONTENT",
                "EXAMPLE_INPUT_CONTENT",
                "EXAMPLE_OUTPUT_CONTENT",
            }
        ),
        required_sections=("Validation rules",),
        required_markers=(
            "<persona>",
            "</persona>",
            "<task>",
            "</task>",
            "<rules>",
            "</rules>",
            "<output_format>",
            "</output_format>",
            "<example_input>",
            "</example_input>",
            "<example_output>",
            "</example_output>",
        ),
    ),
    TemplateContract(
        filename="loop_spec.md.template",
        required_placeholders=frozenset(
            {
                "TASK_NAME",
                "PLAN_VERSION",
                "MAX_ITERATIONS",
                "DEV_PLATEAU_THRESHOLD",
                "OVERFIT_GUARD",
                "MODEL_IDENTIFIER",
            }
        ),
        required_sections=(
            "1. Scope and budget",
            "2. Stop criteria",
            "3. Per-stage subagent configuration (non-negotiable)",
            "4. Adversary configuration",
            "5. Model and execution",
            "6. Run output paths",
            "7. Sacred test set posture (non-negotiable)",
            "Validation rules",
        ),
    ),
    TemplateContract(
        filename="REPORT.md.template",
        required_placeholders=frozenset(
            {
                "TASK_NAME",
                "MODEL_IDENTIFIER",
                "SPP_VERSION",
                "PLAN_VERSION",
                "TOTAL_ITERATIONS",
                "AGGREGATE_STRATEGY",
                "PROMPT_FROZEN_SHA256",
            }
        ),
        required_sections=(
            "1. Run metadata",
            "2. Final scores",
            "3. Loop trajectory",
            "4. Persistent failure modes",
            "5. Prompt-edit audit",
            "6. Decision and recommendation",
            "7. Limitations and caveats (mandatory section)",
            "8. Cost at scale",
            "9. Production prompt artifact",
            "10. Reproducibility checklist",
            "Validation rules",
        ),
    ),
    TemplateContract(
        filename="pipeline.md.template",
        required_placeholders=frozenset(
            {
                "PIPELINE_NAME",
                "PIPELINE_VERSION",
                "NODE_BLOCKS",
                "COMPOSITE_METRIC",
            }
        ),
        required_sections=(
            "1. Pipeline overview",
            "2. Nodes (in execution order)",
            "3. Composite scoring",
            "4. Sequencing and freezing",
            "5. Pipeline revision log",
            "Validation rules",
        ),
    ),
    TemplateContract(
        filename="preprocess.py.template",
        required_placeholders=frozenset(
            {
                "LABEL_COLUMNS",
                "HAS_LANGUAGE",
                "RAW_READER",
                "ID_MAPPING",
                "INPUT_MAPPING",
                "LABEL_MAPPING",
            }
        ),
        required_markers=(
            "class PreprocessError",
            "def preprocess(",
            "def main(",
            'if __name__ == "__main__"',
        ),
    ),
)


def check_template(path: Path, contract: TemplateContract) -> list[Violation]:
    """Validate one shipped ``.template`` against its frozen contract."""
    text = read_text(path)
    present = placeholders(text)
    headings = set(section_headings(text))
    violations: list[Violation] = []

    for name in sorted(contract.required_placeholders - present):
        violations.append(
            Violation(
                "template",
                contract.filename,
                "missing-placeholder",
                f"required placeholder {{{{{name}}}}} is absent",
            )
        )
    for heading in contract.required_sections:
        if heading not in headings:
            violations.append(
                Violation(
                    "template",
                    contract.filename,
                    "missing-section",
                    f"required section heading {heading!r} is absent",
                )
            )
    for marker in contract.required_markers:
        if marker not in text:
            violations.append(
                Violation(
                    "template",
                    contract.filename,
                    "missing-marker",
                    f"required marker {marker!r} is absent",
                )
            )
    return violations


def templates_dir() -> Path:
    """The shipped templates directory, relative to this script."""
    return Path(__file__).resolve().parents[1] / "templates"


def check_all_templates(directory: Path | None = None) -> list[Violation]:
    """Validate every contracted template under ``directory`` (default: shipped)."""
    base = directory if directory is not None else templates_dir()
    violations: list[Violation] = []
    for contract in TEMPLATE_CONTRACTS:
        path = base / contract.filename
        if not path.exists():
            violations.append(
                Violation(
                    "template",
                    contract.filename,
                    "missing-file",
                    f"contracted template not found under {base}",
                )
            )
            continue
        violations.extend(check_template(path, contract))
    return violations


# --------------------------------------------------------------------------- #
# plan.md filled-instance validation
# --------------------------------------------------------------------------- #

_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_H1_RE = re.compile(r"^#\s+spp plan\s+[—-]\s+(.+?)\s*$", re.MULTILINE)
_SPLIT_RE = re.compile(
    r"train\s+(\d+)%\s*/\s*dev\s+(\d+)%\s*/\s*test\s+(\d+)%", re.IGNORECASE
)


def _check_task_name(text: str, target: str) -> list[Violation]:
    m = _H1_RE.search(text)
    if not m:
        return [
            Violation("plan", target, "rule 2", "no '# spp plan — <name>' H1 found")
        ]
    name = m.group(1).strip()
    if not _KEBAB_RE.match(name):
        return [
            Violation("plan", target, "rule 2", f"task name {name!r} is not kebab-case")
        ]
    return []


def _check_literal_field(
    text: str, target: str, label: str, expected: str, rule: str
) -> list[Violation]:
    value = field_value(text, label)
    if value is None:
        return [Violation("plan", target, rule, f"field {label!r} is absent")]
    if value != expected:
        return [
            Violation(
                "plan",
                target,
                rule,
                f"{label!r} is {value!r}, must be {expected!r}",
            )
        ]
    return []


def _check_splits(text: str, target: str) -> list[Violation]:
    m = _SPLIT_RE.search(text)
    if not m:
        return [Violation("plan", target, "rule 9", "no 'train X% / dev Y% / test Z%'")]
    total = sum(int(g) for g in m.groups())
    if total != 100:
        return [
            Violation(
                "plan", target, "rule 9", f"split percentages sum to {total}, not 100"
            )
        ]
    return []


def _check_task_mode(text: str, target: str) -> list[Violation]:
    value = field_value(text, "Task mode")
    # Absent reads as the backward-compatible default (rule 17) — not a violation.
    if value is None or value == "":
        return []
    if value not in VALID_TASK_MODES:
        return [
            Violation(
                "plan",
                target,
                "rule 17",
                f"TASK_MODE {value!r} not in {sorted(VALID_TASK_MODES)}",
            )
        ]
    return []


# A Markdown table separator row, e.g. ``|---|---|`` or ``| :--- | ---: |``.
_SEPARATOR_RE = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$")


def _table_rows(text: str, header_contains: str) -> list[list[str]]:
    """Return data rows (as cell lists) of the first genuine Markdown table whose
    header row contains ``header_contains``. Empty if no such table is found.

    A candidate header line must be immediately followed by a separator row
    (``|---|...``) to count — this rejects a prose line that merely mentions the
    header phrase next to a pipe, and keeps scanning for the real table.
    """
    rows: list[list[str]] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "|" not in line or header_contains.lower() not in line.lower():
            continue
        if i + 1 >= len(lines) or not _SEPARATOR_RE.match(lines[i + 1]):
            continue  # not a real table header; keep looking
        for body in lines[i + 2 :]:
            if "|" not in body or not body.strip():
                break
            cells = [c.strip() for c in body.strip().strip("|").split("|")]
            rows.append(cells)
        break
    return rows


def _check_gate_phrases(text: str, target: str) -> list[Violation]:
    rows = _table_rows(text, "Approval phrase")
    if not rows:
        return [Violation("plan", target, "rule 11", "no HITL gate table found")]
    violations: list[Violation] = []
    for cells in rows:
        if len(cells) < 2:
            continue
        gate, phrase = cells[0], cells[1]
        if not phrase or unresolved_placeholders(phrase):
            violations.append(
                Violation(
                    "plan",
                    target,
                    "rule 11",
                    f"gate {gate!r} has an empty/unresolved approval phrase",
                )
            )
    return violations


def _check_revision_log(text: str, target: str) -> list[Violation]:
    rows = _table_rows(text, "Plan version")
    if not rows:
        return [Violation("plan", target, "rule 12", "no plan revision log table")]
    versions: list[int] = []
    for cells in rows:
        if len(cells) < 2:
            continue
        m = re.search(r"v?(\d+)", cells[1])
        if m:
            versions.append(int(m.group(1)))
    if not versions:
        return [
            Violation("plan", target, "rule 12", "revision log has no version rows")
        ]
    if versions != sorted(versions) or len(set(versions)) != len(versions):
        return [
            Violation(
                "plan",
                target,
                "rule 12",
                f"PLAN_VERSION values {versions} are not strictly increasing",
            )
        ]
    return []


def check_plan(path: Path) -> list[Violation]:
    """Validate a filled ``plan.md`` against the mechanically robust rule subset."""
    text = read_text(path)
    target = path.name
    violations: list[Violation] = []

    unresolved = unresolved_placeholders(text)
    if unresolved:
        violations.append(
            Violation(
                "plan",
                target,
                "rule 1",
                f"{len(unresolved)} unresolved placeholder(s): "
                + ", ".join(sorted(set(unresolved))[:5]),
            )
        )
    violations.extend(_check_task_name(text, target))
    violations.extend(
        _check_literal_field(
            text, target, "Sacred test set acknowledgment", "acknowledged", "rule 7"
        )
    )
    violations.extend(
        _check_literal_field(
            text,
            target,
            "Auditor configuration",
            "per-iteration, no-score-access",
            "rule 8",
        )
    )
    violations.extend(_check_splits(text, target))
    violations.extend(_check_gate_phrases(text, target))
    violations.extend(_check_revision_log(text, target))
    violations.extend(_check_task_mode(text, target))
    return violations


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _cmd_templates(args: argparse.Namespace) -> int:
    directory: Path | None = args.dir
    violations = check_all_templates(directory)
    return _report(violations, "templates OK")


def _cmd_plan(args: argparse.Namespace) -> int:
    violations = check_plan(args.path)
    return _report(violations, f"{args.path.name} OK")


def _report(violations: list[Violation], ok_message: str) -> int:
    if violations:
        print(format_violations(violations), file=sys.stderr)
        return 1
    print(ok_message)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint spp templates and filled plan.md files."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("templates", help="check the shipped templates' contracts")
    t.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="templates directory (default: the shipped skills/run/templates)",
    )
    t.set_defaults(func=_cmd_templates)

    p = sub.add_parser("plan", help="validate a filled plan.md")
    p.add_argument("path", type=Path, help="path to the plan.md to validate")
    p.set_defaults(func=_cmd_plan)

    args = parser.parse_args(argv)
    try:
        result: int = args.func(args)
        return result
    except LintError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
