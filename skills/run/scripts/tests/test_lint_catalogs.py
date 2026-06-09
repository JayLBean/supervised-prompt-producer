"""Tests for the ENTRY_SCHEMA catalog linter.

The shipped technique/structure catalogs must conform; the linter must catch a
missing or empty required field, an id that disagrees with the filename, and a
duplicate id across a catalog. The flat-key parser must read both inline and
block-scalar values.
"""

from __future__ import annotations

from pathlib import Path

from spp_scripts.lint_catalogs import (
    CATALOGS,
    check_all_catalogs,
    check_catalog,
    check_entry,
    entry_fields,
    subskills_dir,
)

_TECHNIQUE_FIELDS = next(c.required_fields for c in CATALOGS if c.label == "technique")
_STRUCTURE = next(c for c in CATALOGS if c.label == "structure")


def _valid_technique(stem: str = "demo") -> str:
    return (
        f"id: {stem}\n"
        "name: Demo Technique\n"
        "symptom: >\n"
        "  A checkable failure-class property stated about a field.\n"
        "recommendation: >\n"
        "  A categorical suggestion about the class, not specific rows.\n"
        "output_form: per_label_binary\n"
        "runner_support: none\n"
        "citation: >\n"
        "  Some Author, Some Year.\n"
    )


# --------------------------------------------------------------------------- #
# entry_fields parser
# --------------------------------------------------------------------------- #


def test_entry_fields_inline_and_block() -> None:
    fields = entry_fields(
        "id: foo\nsymptom: >\n  line one\n  line two\nempty_block: >\ncitation: x\n"
    )
    assert fields["id"] == "foo"
    assert "line one" in fields["symptom"] and "line two" in fields["symptom"]
    assert fields["citation"] == "x"
    # A block-scalar key with no following content is present-but-empty.
    assert fields["empty_block"] == ""


def test_entry_fields_ignores_indented_lines_as_keys() -> None:
    # An indented "key: value" inside a block scalar is content, not a field.
    fields = entry_fields("id: foo\nsymptom: >\n  note: not a real field\n")
    assert set(fields) == {"id", "symptom"}


# --------------------------------------------------------------------------- #
# Shipped catalogs must conform
# --------------------------------------------------------------------------- #


def test_shipped_catalogs_conform() -> None:
    violations = check_all_catalogs()
    assert violations == [], "\n".join(
        f"{v.target}: {v.rule}: {v.message}" for v in violations
    )


def test_two_catalogs_contracted() -> None:
    labels = {c.label for c in CATALOGS}
    assert labels == {"technique", "structure"}
    for contract in CATALOGS:
        assert (subskills_dir() / contract.subdir).is_dir()


# --------------------------------------------------------------------------- #
# check_entry / check_catalog
# --------------------------------------------------------------------------- #


def test_valid_entry_passes(tmp_path: Path) -> None:
    path = tmp_path / "demo.yaml"
    path.write_text(_valid_technique("demo"), encoding="utf-8")
    assert check_entry(path, _TECHNIQUE_FIELDS, "technique") == []


def test_missing_field_flagged(tmp_path: Path) -> None:
    path = tmp_path / "demo.yaml"
    path.write_text(
        _valid_technique("demo").replace(
            "citation: >\n  Some Author, Some Year.\n", ""
        ),
        encoding="utf-8",
    )
    rules = {v.rule for v in check_entry(path, _TECHNIQUE_FIELDS, "technique")}
    assert rules == {"missing-field"}


def test_empty_field_flagged(tmp_path: Path) -> None:
    path = tmp_path / "demo.yaml"
    path.write_text(
        _valid_technique("demo").replace(
            "output_form: per_label_binary", "output_form:"
        ),
        encoding="utf-8",
    )
    rules = {v.rule for v in check_entry(path, _TECHNIQUE_FIELDS, "technique")}
    assert "empty-field" in rules


def test_id_mismatch_flagged(tmp_path: Path) -> None:
    path = tmp_path / "other.yaml"
    path.write_text(_valid_technique("demo"), encoding="utf-8")  # id=demo != other
    rules = {v.rule for v in check_entry(path, _TECHNIQUE_FIELDS, "technique")}
    assert "id-mismatch" in rules


def test_duplicate_id_flagged(tmp_path: Path) -> None:
    # Both files declare id "a"; a.yaml matches its stem, b.yaml does not. Since
    # filenames are unique, a duplicate id necessarily also trips id-mismatch.
    (tmp_path / "a.yaml").write_text(_valid_technique("a"), encoding="utf-8")
    (tmp_path / "b.yaml").write_text(_valid_technique("a"), encoding="utf-8")
    contract = next(c for c in CATALOGS if c.label == "technique")
    rules = {v.rule for v in check_catalog(tmp_path, contract)}
    assert "duplicate-id" in rules


def test_structure_requires_independence(tmp_path: Path) -> None:
    # A structure entry missing the extra `independence` field is flagged.
    entry = (
        "id: demo\nname: Demo\nsymptom: >\n  s\nrecommendation: >\n  r\n"
        "structure_form: batched_io\nrunner_support: none\ncitation: >\n  c\n"
    )
    path = tmp_path / "demo.yaml"
    path.write_text(entry, encoding="utf-8")
    rules = {
        (v.rule, "independence" in v.message)
        for v in check_entry(path, _STRUCTURE.required_fields, "structure")
    }
    assert ("missing-field", True) in rules


def test_missing_dir_flagged(tmp_path: Path) -> None:
    violations = check_all_catalogs(tmp_path)
    assert violations
    assert all(v.rule == "missing-dir" for v in violations)
    assert len(violations) == len(CATALOGS)
