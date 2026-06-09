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
    normalize_ws,
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

# The locked six-section prompt structure (invariant #12), in canonical order.
SIX_SECTIONS = (
    "persona",
    "task",
    "rules",
    "output_format",
    "example_input",
    "example_output",
)

# prompt_v01.md rules that are manual PR-time review gates, not mechanical (per
# the template's "Validation rules"): the linter checks structure and
# non-emptiness, not semantic correctness.
PROMPT_RULES_DELEGATED = (
    "rule 5 correspondence (example output follows from the rules — manual PR gate)",
    "rule 6 (example_output matches the output_format — manual PR gate)",
    "rule 7 (model-directive semantics — model-specific, manual)",
    "rule 8 (no real source-project data — manual PR gate, DESIGN.md §7.2)",
)

# The REPORT.md §5 invariant block (invariant #21): the header plus the four
# per-stage sub-statements, all required verbatim.
REPORT_INVARIANT_HEADER = "**Per-stage information-isolation invariants:** preserved."
REPORT_INVARIANT_LINES = (
    "- Discrepancy subagent: allow-list honored, no prior-iteration leakage.",
    "- Rule-edit subagent: allow-list honored, no row-content exposure.",
    "- Auditor subagent: allow-list honored, no score access.",
    "- Adversary subagent (when invoked): allow-list honored, non-persistence honored.",
)

# The loop_spec.md non-negotiable literal lines (invariant #18): §3 per-stage
# isolation (nine lines) and §7 sacred-test posture (two lines). Matched
# verbatim, since they ship in fenced code blocks (no line-wrapping).
LOOP_SPEC_REQUIRED_LINES = (
    "discrepancy_subagent: per-iteration",
    "discrepancy_score_access: forbidden",
    "discrepancy_prior_iteration_access: forbidden",
    "rule_edit_subagent: per-iteration",
    "rule_edit_baseline_access: forbidden",
    "rule_edit_score_access: forbidden",
    "auditor: per-iteration",
    "auditor_score_access: forbidden",
    "auditor_frequency_reduction: forbidden",
    "test_set_access_during_loop: forbidden",
    "test_set_first_use: /spp-finalize only",
)

# The loop_spec.md §4 adversary-boundary guarantees. These ship as wrapped
# prose, so they are matched after whitespace normalization.
LOOP_SPEC_REQUIRED_PHRASES = (
    "are **not** added to `baseline.csv`, `splits.json`, or any tracked "
    "artifact under `runs/`.",
    "they are not persisted.",
    "Promoting synthetic rows is forbidden.",
)


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
# prompt_v01.md six-section validation
# --------------------------------------------------------------------------- #

_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+\S", re.MULTILINE)


def _open_tag_count(text: str, tag: str) -> int:
    """Count ``<tag>`` opening tags that stand alone on their own line.

    Section delimiters in a prompt are on their own line; an inline mention in a
    comment or in prose (``the <task> content``) is not a section and must not be
    counted.
    """
    return len(re.findall(rf"^[ \t]*<{tag}>[ \t]*$", text, re.MULTILINE))


def _close_tag_count(text: str, tag: str) -> int:
    return len(re.findall(rf"^[ \t]*</{tag}>[ \t]*$", text, re.MULTILINE))


def _open_tag_pos(text: str, tag: str) -> int:
    """Byte offset of the standalone opening ``<tag>`` line, or ``-1``."""
    m = re.search(rf"^[ \t]*<{tag}>[ \t]*$", text, re.MULTILINE)
    return m.start() if m else -1


def _section_block(text: str, tag: str) -> str | None:
    """Return the inner text between a standalone ``<tag>`` and ``</tag>``, or
    ``None``. Anchoring to standalone lines avoids matching an inline mention of
    the tag in a comment or in prose."""
    m = re.search(
        rf"^[ \t]*<{tag}>[ \t]*$(.*?)^[ \t]*</{tag}>[ \t]*$",
        text,
        re.DOTALL | re.MULTILINE,
    )
    return m.group(1) if m else None


def check_prompt(path: Path) -> list[Violation]:
    """Validate a filled ``prompt_v01.md`` against the mechanically checkable
    six-section rules (the template's validation rules 1-4 and the non-emptiness
    of the example sections). Rules 5-8 (semantic correspondence, output-format
    compliance, model-directive validity, no-real-data) are manual PR gates,
    recorded in :data:`PROMPT_RULES_DELEGATED`.
    """
    text = read_text(path)
    target = path.name
    violations: list[Violation] = []

    # rule 1 — no unresolved placeholders.
    unresolved = unresolved_placeholders(text)
    if unresolved:
        violations.append(
            Violation(
                "prompt",
                target,
                "rule 1",
                f"{len(unresolved)} unresolved placeholder(s): "
                + ", ".join(sorted(set(unresolved))[:5]),
            )
        )

    # rules 2 + 3 — each section opens exactly once with a matching close.
    # Tags are counted only when they stand alone on a line, so an inline mention
    # of a tag name in a comment or in prose is not mistaken for a section.
    first_pos: dict[str, int] = {}
    for tag in SIX_SECTIONS:
        opens = _open_tag_count(text, tag)
        closes = _close_tag_count(text, tag)
        if opens != 1:
            violations.append(
                Violation(
                    "prompt",
                    target,
                    "rule 2",
                    f"<{tag}> appears {opens} time(s), expected exactly 1",
                )
            )
        if opens != closes:
            violations.append(
                Violation(
                    "prompt",
                    target,
                    "rule 3",
                    f"<{tag}> has {opens} open / {closes} close tag(s) (orphaned)",
                )
            )
        idx = _open_tag_pos(text, tag)
        if idx != -1:
            first_pos[tag] = idx

    # rule 2 (order) — only meaningful when all six are present.
    if len(first_pos) == len(SIX_SECTIONS):
        actual = sorted(first_pos, key=lambda t: first_pos[t])
        if actual != list(SIX_SECTIONS):
            violations.append(
                Violation(
                    "prompt",
                    target,
                    "rule 2",
                    f"sections out of order: {actual}",
                )
            )

    # rule 4 — <rules> carries at least one enumerated rule.
    rules_block = _section_block(text, "rules")
    if rules_block is not None and not _LIST_ITEM_RE.search(rules_block):
        violations.append(
            Violation(
                "prompt",
                target,
                "rule 4",
                "<rules> has no enumerated rule (bullet or numbered list)",
            )
        )

    # rule 5 (mechanical part) — the example sections are non-empty.
    for tag in ("example_input", "example_output"):
        block = _section_block(text, tag)
        if block is not None and not block.strip():
            violations.append(
                Violation("prompt", target, "rule 5", f"<{tag}> is empty")
            )

    return violations


# --------------------------------------------------------------------------- #
# REPORT.md §5 invariant block (invariant #21)
# --------------------------------------------------------------------------- #


def check_report(path: Path) -> list[Violation]:
    """Verify the REPORT.md §5 per-stage information-isolation invariant block is
    present verbatim — the header and all four sub-statements (invariant #21).
    Works on the template (the block ships literal) and on a filled REPORT.
    """
    text = read_text(path)
    target = path.name
    violations: list[Violation] = []
    if REPORT_INVARIANT_HEADER not in text:
        violations.append(
            Violation(
                "report",
                target,
                "invariant-block",
                f"missing the §5 invariant header {REPORT_INVARIANT_HEADER!r}",
            )
        )
    for line in REPORT_INVARIANT_LINES:
        if line not in text:
            violations.append(
                Violation(
                    "report",
                    target,
                    "invariant-block",
                    f"missing §5 invariant sub-statement: {line!r}",
                )
            )
    return violations


# --------------------------------------------------------------------------- #
# loop_spec.md literal-block immutability (invariant #18)
# --------------------------------------------------------------------------- #


def check_loop_spec(path: Path) -> list[Violation]:
    """Verify the loop_spec.md non-negotiable literal blocks are present and
    unmodified (invariant #18): the §3 per-stage isolation lines and §7
    sacred-test lines verbatim, and the §4 adversary-boundary guarantees (matched
    after whitespace normalization, since they ship as wrapped prose).
    """
    text = read_text(path)
    normalized = normalize_ws(text)
    target = path.name
    violations: list[Violation] = []
    for line in LOOP_SPEC_REQUIRED_LINES:
        if line not in text:
            violations.append(
                Violation(
                    "loop_spec",
                    target,
                    "literal-block",
                    f"missing or altered non-negotiable line: {line!r}",
                )
            )
    for phrase in LOOP_SPEC_REQUIRED_PHRASES:
        if normalize_ws(phrase) not in normalized:
            violations.append(
                Violation(
                    "loop_spec",
                    target,
                    "literal-block",
                    f"missing or altered §4 adversary-boundary guarantee: {phrase!r}",
                )
            )
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


def _cmd_prompt(args: argparse.Namespace) -> int:
    violations = check_prompt(args.path)
    return _report(violations, f"{args.path.name} OK")


def _cmd_report(args: argparse.Namespace) -> int:
    violations = check_report(args.path)
    return _report(violations, f"{args.path.name} OK")


def _cmd_loop_spec(args: argparse.Namespace) -> int:
    violations = check_loop_spec(args.path)
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

    pr = sub.add_parser("prompt", help="validate a filled prompt_v01.md")
    pr.add_argument("path", type=Path, help="path to the prompt_v01.md to validate")
    pr.set_defaults(func=_cmd_prompt)

    rp = sub.add_parser("report", help="check a REPORT.md §5 invariant block")
    rp.add_argument("path", type=Path, help="path to the REPORT.md to validate")
    rp.set_defaults(func=_cmd_report)

    ls = sub.add_parser("loop-spec", help="check a loop_spec.md literal blocks")
    ls.add_argument("path", type=Path, help="path to the loop_spec.md to validate")
    ls.set_defaults(func=_cmd_loop_spec)

    args = parser.parse_args(argv)
    try:
        result: int = args.func(args)
        return result
    except LintError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
