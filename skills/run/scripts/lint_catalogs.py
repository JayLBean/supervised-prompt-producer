"""ENTRY_SCHEMA catalog linter (DESIGN §7.1.13).

The two advisor catalogs — ``technique-advisor/techniques/*.yaml`` and
``structure-advisor/structures/*.yaml`` — are extensible, but each entry must
conform to its ``ENTRY_SCHEMA.md`` contract. This linter checks the *mechanical*
part of that contract: every required top-level field is present and non-empty,
the ``id`` matches the filename stem, and ids are unique within a catalog. The
ENTRY_SCHEMA "eligibility rules" (symptom checkable, recommendation categorical,
the ``independence`` guard for #13, no six-section change) stay review-enforced,
as both ENTRY_SCHEMA documents state — a linter cannot judge them.

To avoid adding a YAML dependency for a presence check, the entries' controlled
flat-key format (top-level ``key:`` or ``key: >`` block scalars, 2-space indent
per ``CLAUDE.md`` §2) is parsed directly: a field is "present and non-empty" when
a top-level key carries inline text or indented continuation lines. No model, no
scores — pure text checks.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from ._lint import LintError, Violation, format_violations, read_text

# A top-level YAML key (no leading whitespace), capturing any inline value.
_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$")
# Catalog ids are kebab-case: lowercase alnum segments separated by single dashes.
_KEBAB_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Block-scalar indicators that mean "the value is on the following lines".
_BLOCK_INDICATORS = frozenset({">", "|", ">-", "|-", ">+", "|+"})


@dataclass(frozen=True)
class CatalogContract:
    """A catalog directory and the required top-level fields of each entry."""

    label: str
    subdir: str  # relative to skills/run/sub-skills
    required_fields: tuple[str, ...]


CATALOGS: tuple[CatalogContract, ...] = (
    CatalogContract(
        label="technique",
        subdir="technique-advisor/techniques",
        required_fields=(
            "id",
            "name",
            "symptom",
            "recommendation",
            "output_form",
            "runner_support",
            "citation",
        ),
    ),
    CatalogContract(
        label="structure",
        subdir="structure-advisor/structures",
        required_fields=(
            "id",
            "name",
            "symptom",
            "recommendation",
            "structure_form",
            "runner_support",
            "independence",
            "citation",
        ),
    ),
)


def subskills_dir() -> Path:
    """The shipped sub-skills directory, relative to this script."""
    return Path(__file__).resolve().parents[1] / "sub-skills"


def entry_fields(text: str) -> dict[str, str]:
    """Parse a catalog entry's top-level fields to ``{key: value}``.

    A value is the inline text after ``key:`` plus any indented continuation
    lines up to the next top-level key (block scalars). A block-scalar indicator
    (``>`` / ``|``) on the key line contributes no inline text. The returned
    value is stripped, so an empty string means the field is present but empty.
    """
    lines = text.splitlines()
    keyed: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines):
        m = _KEY_RE.match(line)
        if m:
            keyed.append((i, m.group(1), m.group(2)))

    fields: dict[str, str] = {}
    for j, (i, key, inline) in enumerate(keyed):
        end = keyed[j + 1][0] if j + 1 < len(keyed) else len(lines)
        inline_val = inline.strip()
        if inline_val in _BLOCK_INDICATORS:
            inline_val = ""
        block = "\n".join(lines[i + 1 : end])
        fields[key] = (inline_val + "\n" + block).strip()
    return fields


def check_entry(
    path: Path, required_fields: tuple[str, ...], label: str
) -> list[Violation]:
    """Validate one catalog entry's required fields and id/filename agreement."""
    fields = entry_fields(read_text(path))
    target = f"{label}/{path.name}"
    violations: list[Violation] = []
    for name in required_fields:
        if name not in fields:
            violations.append(
                Violation(
                    "catalog",
                    target,
                    "missing-field",
                    f"required field {name!r} absent",
                )
            )
        elif not fields[name]:
            violations.append(
                Violation(
                    "catalog",
                    target,
                    "empty-field",
                    f"required field {name!r} is empty",
                )
            )
    entry_id = fields.get("id", "")
    if entry_id and not _KEBAB_ID_RE.fullmatch(entry_id):
        violations.append(
            Violation(
                "catalog",
                target,
                "id-not-kebab",
                f"id {entry_id!r} must be kebab-case",
            )
        )
    if entry_id and entry_id != path.stem:
        violations.append(
            Violation(
                "catalog",
                target,
                "id-mismatch",
                f"id {entry_id!r} does not match filename stem {path.stem!r}",
            )
        )
    return violations


def check_catalog(directory: Path, contract: CatalogContract) -> list[Violation]:
    """Validate every ``*.yaml`` entry in one catalog, including id uniqueness."""
    violations: list[Violation] = []
    seen: dict[str, str] = {}
    for path in sorted(directory.glob("*.yaml")):
        violations.extend(check_entry(path, contract.required_fields, contract.label))
        entry_id = entry_fields(read_text(path)).get("id", "")
        if entry_id:
            if entry_id in seen:
                violations.append(
                    Violation(
                        "catalog",
                        f"{contract.label}/{path.name}",
                        "duplicate-id",
                        f"id {entry_id!r} already used by {seen[entry_id]}",
                    )
                )
            else:
                seen[entry_id] = path.name
    return violations


def check_all_catalogs(base: Path | None = None) -> list[Violation]:
    """Validate both shipped advisor catalogs (default: the shipped sub-skills)."""
    root = base if base is not None else subskills_dir()
    violations: list[Violation] = []
    for contract in CATALOGS:
        directory = root / contract.subdir
        if not directory.is_dir():
            violations.append(
                Violation(
                    "catalog",
                    contract.label,
                    "missing-dir",
                    f"catalog directory not found: {directory}",
                )
            )
            continue
        violations.extend(check_catalog(directory, contract))
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint the technique/structure advisor catalogs against ENTRY_SCHEMA."
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="sub-skills directory (default: the shipped skills/run/sub-skills)",
    )
    args = parser.parse_args(argv)
    try:
        violations = check_all_catalogs(args.dir)
    except LintError as exc:
        parser.error(str(exc))
    if violations:
        print(format_violations(violations), file=sys.stderr)
        return 1
    print("catalogs OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
