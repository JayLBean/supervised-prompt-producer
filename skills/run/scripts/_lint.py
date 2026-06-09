"""Shared harness for the spp linter family (DESIGN §7.1.13).

The linters mechanically enforce contracts that v1.0 froze and that were
previously checked only by review — template placeholders and sections, the
``plan.md`` validation rules, ``ENTRY_SCHEMA`` catalog conformance, the
six-section prompt, the ``REPORT.md`` §5 invariant block, and the
``loop_spec.md`` literal blocks. This module is the common scaffolding they
share: a ``Violation`` record, placeholder/section helpers over raw text, a
clean read wrapper, and a human-readable report formatter.

It runs no model and parses no scores; every function is a pure transform of
text already in hand. Each linter module (``lint_templates`` and the rest)
imports these helpers and returns ``list[Violation]``; callers decide whether a
non-empty list is a test failure (pytest) or a non-zero CLI exit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# A ``{{PLACEHOLDER}}`` token. Names are upper snake case with optional ``[f]``
# field-index suffixes (e.g. ``FIELD_1_NAME``, ``METRIC_NAME[f]``).
_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z0-9_\[\]]+)\s*\}\}")

# Any residual brace pair, used to detect a filled instance that still carries
# an unresolved placeholder (a stray ``{{`` or ``}}`` counts).
_UNRESOLVED_RE = re.compile(r"\{\{[^}]*\}\}|\{\{|\}\}")


class LintError(RuntimeError):
    """A linter could not run (e.g. a target file is missing); user-facing."""


@dataclass(frozen=True)
class Violation:
    """One contract violation found by a linter.

    ``linter`` names the check family (e.g. ``"template"``, ``"plan"``).
    ``target`` is the file (or file:section) the violation is about. ``rule`` is
    a short stable code — a plan rule number (``"rule 8"``) or a check name
    (``"missing-placeholder"``). ``message`` is the human-readable detail.
    """

    linter: str
    target: str
    rule: str
    message: str


def read_text(path: Path) -> str:
    """Read ``path`` as UTF-8, raising :class:`LintError` with a clean message."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:  # missing file, permissions, etc.
        raise LintError(f"cannot read {path}: {exc}") from exc


def placeholders(text: str) -> set[str]:
    """Return the set of ``{{PLACEHOLDER}}`` names present in ``text``."""
    return {m.group(1) for m in _PLACEHOLDER_RE.finditer(text)}


def unresolved_placeholders(text: str) -> list[str]:
    """Return residual ``{{...}}`` fragments, in order — empty when fully filled.

    Used by the filled-instance checks: a finished ``plan.md`` / ``prompt_v01.md``
    must carry no remaining placeholder (plan rule 1).
    """
    return [m.group(0) for m in _UNRESOLVED_RE.finditer(text)]


def section_headings(text: str) -> list[str]:
    """Return Markdown ATX headings (``#``..``######``) in document order.

    The leading hashes are stripped; the heading text is returned verbatim so a
    caller can match on a prefix like ``"## 7. Splits"``.
    """
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            out.append(stripped.lstrip("#").strip())
    return out


def field_value(text: str, label: str) -> str | None:
    """Return the value of a ``**Label:** value`` field line, or ``None``.

    spp's filled artifacts render single-value fields as a bold label followed by
    the value on the same line (e.g. ``**Auditor configuration:** ...``). Matching
    on the label keeps the check robust to section reordering. The returned value
    is stripped; an empty value returns the empty string (distinct from ``None``,
    which means the label is absent).
    """
    pattern = re.compile(
        r"^\*\*" + re.escape(label) + r":\*\*[ \t]*(.*?)[ \t]*$",
        re.MULTILINE,
    )
    m = pattern.search(text)
    return m.group(1) if m else None


def normalize_ws(text: str) -> str:
    """Collapse every run of whitespace (including newlines) to one space.

    Lets a check match a multi-line, line-wrapped prose block against a
    single-line canonical phrase without depending on where the wraps fall.
    """
    return re.sub(r"\s+", " ", text).strip()


def format_violations(violations: list[Violation]) -> str:
    """Render violations as one line each, grouped readably; empty -> ``""``."""
    return "\n".join(
        f"{v.target}: [{v.linter}/{v.rule}] {v.message}" for v in violations
    )
