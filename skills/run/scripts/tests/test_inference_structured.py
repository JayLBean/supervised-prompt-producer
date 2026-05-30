"""Tests for the K>1 structured-parse layer in inference.py (DESIGN §7.1.5)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from spp_scripts.inference import (
    InferenceError,
    _output_schema_field_names,
    _parse_structured,
    run_inference,
)

# --------------------------------------------------------------------------- #
# _parse_structured
# --------------------------------------------------------------------------- #


def test_parse_structured_happy() -> None:
    parsed, errors, row_error = _parse_structured('{"a": "X", "b": "Y"}', ["a", "b"])
    assert parsed == {"a": "X", "b": "Y"}
    assert errors == {}
    assert row_error is None


def test_parse_structured_missing_field() -> None:
    parsed, errors, row_error = _parse_structured('{"a": "X"}', ["a", "b"])
    assert parsed == {"a": "X", "b": None}
    assert errors == {"b": "missing field"}
    assert row_error is None


def test_parse_structured_non_object() -> None:
    parsed, errors, row_error = _parse_structured('["x"]', ["a"])
    assert parsed == {"a": None}
    assert "expected a JSON object" in errors["a"]
    assert row_error is not None and "expected a JSON object" in row_error


def test_parse_structured_decode_error() -> None:
    parsed, errors, row_error = _parse_structured("{not json", ["a"])
    assert parsed == {"a": None}
    assert "JSON decode error" in errors["a"]
    assert row_error is not None


def test_parse_structured_empty() -> None:
    parsed, errors, row_error = _parse_structured("   ", ["a", "b"])
    assert parsed == {"a": None, "b": None}
    assert errors == {"a": "empty response", "b": "empty response"}
    assert row_error == "empty response"


def test_parse_structured_type_stringification() -> None:
    raw = '{"n": 3, "f": 1.5, "flag": true, "tags": ["y", "x"], "s": "  hi  "}'
    parsed, errors, row_error = _parse_structured(raw, ["n", "f", "flag", "tags", "s"])
    assert errors == {}
    assert row_error is None
    assert parsed["n"] == "3"
    assert parsed["f"] == "1.5"
    assert parsed["flag"] == "true"  # bool, not "1"
    assert parsed["tags"] == '["y","x"]'  # list preserved as compact JSON
    assert parsed["s"] == "hi"  # strings are stripped


def test_parse_structured_null_value() -> None:
    parsed, errors, _ = _parse_structured('{"a": null}', ["a"])
    assert parsed == {"a": None}
    assert errors == {"a": "null value"}


def test_parse_structured_code_fence() -> None:
    parsed, errors, row_error = _parse_structured(
        '```json\n{"a": "X", "b": "Z"}\n```', ["a", "b"]
    )
    assert parsed == {"a": "X", "b": "Z"}
    assert errors == {}
    assert row_error is None


# --------------------------------------------------------------------------- #
# _output_schema_field_names
# --------------------------------------------------------------------------- #


def _write_schema(tmp_path: Path, schema: dict[str, Any]) -> Path:
    p = tmp_path / "schema.json"
    p.write_text(json.dumps(schema))
    return p


def test_output_schema_field_names_order(tmp_path: Path) -> None:
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "price": {"type": "number"},
            "in_stock": {"type": "boolean"},
        },
    }
    assert _output_schema_field_names(_write_schema(tmp_path, schema)) == [
        "title",
        "price",
        "in_stock",
    ]


def test_output_schema_field_names_missing_file(tmp_path: Path) -> None:
    with pytest.raises(InferenceError, match="schema not found"):
        _output_schema_field_names(tmp_path / "nope.json")


def test_output_schema_field_names_no_properties(tmp_path: Path) -> None:
    with pytest.raises(InferenceError, match="no non-empty 'properties'"):
        _output_schema_field_names(_write_schema(tmp_path, {"type": "object"}))


def test_output_schema_field_names_bad_json(tmp_path: Path) -> None:
    p = tmp_path / "schema.json"
    p.write_text("{not json")
    with pytest.raises(InferenceError, match="not valid JSON"):
        _output_schema_field_names(p)


# --------------------------------------------------------------------------- #
# run_inference, structured path (offline fake client)
# --------------------------------------------------------------------------- #


class _FakeCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})})]
        self.usage = type("U", (), {"total_tokens": 5})


class _FakeCompletions:
    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = mapping

    async def create(self, **kwargs: Any) -> _FakeCompletion:
        user = kwargs["messages"][1]["content"]
        return _FakeCompletion(self._mapping.get(user, ""))


class _FakeClient:
    def __init__(self, mapping: dict[str, str]) -> None:
        self.chat = type("Chat", (), {"completions": _FakeCompletions(mapping)})


def test_run_inference_structured_path(tmp_path: Path) -> None:
    base = tmp_path / "baseline.csv"
    pd.DataFrame([{"id": "a", "input": "foo"}, {"id": "b", "input": "bar"}]).to_csv(
        base, index=False
    )
    prompt = tmp_path / "p.md"
    prompt.write_text("system prompt")
    schema = _write_schema(
        tmp_path,
        {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "urgent": {"type": "boolean"},
            },
        },
    )
    out = tmp_path / "results.json"

    # Row "foo" parses fully; row "bar" is missing the `urgent` field.
    client = _FakeClient(
        {
            "foo": '{"category": "Billing", "urgent": true}',
            "bar": '{"category": "Other"}',
        }
    )
    results = run_inference(
        prompt_path=prompt,
        baseline_path=base,
        row_ids=["a", "b"],
        model="m",
        api_endpoint="http://x",
        concurrency=2,
        max_tokens=10,
        timeout=5.0,
        temperature=0.0,
        out_path=out,
        schema_path=schema,
        client=client,
    )

    assert results.summary.n_rows == 2
    assert results.summary.n_parsed == 1  # only "foo" parsed every field

    by_id = {p.row_id: p for p in results.predictions}
    assert by_id["a"].parsed_label is None  # structured path leaves label unset
    assert by_id["a"].parsed_fields == {"category": "Billing", "urgent": "true"}
    assert by_id["a"].field_parse_errors == {}
    assert by_id["b"].parsed_fields == {"category": "Other", "urgent": None}
    assert by_id["b"].field_parse_errors == {"urgent": "missing field"}

    # Persisted to disk in the same shape.
    persisted = json.loads(out.read_text())
    assert persisted["predictions"][0]["parsed_fields"]["category"] == "Billing"
