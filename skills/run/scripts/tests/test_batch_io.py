"""Batched I/O runner path + per-row-independence guard (DESIGN.md §7.1.10).

Covers the wire-contract parsing (results array mapped by index, with
missing / duplicate / malformed degrading to per-row failures and lead-row
latency/token attribution) and the batch-invariance guard (a batched run
that matches single-row is kept; one that diverges falls back to single-row
scoring, keeping invariant #13's score faithful to deployed behavior).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from spp_scripts.inference import (
    InferenceError,
    _count_divergent,
    _parse_batch_response,
    run_inference,
)


# ---------- _parse_batch_response unit tests -------------------------------

CHUNK = [("a", "first"), ("b", "second")]


def _results(raw_obj: Any) -> str:
    return json.dumps(raw_obj)


def test_parse_batch_maps_by_index() -> None:
    raw = _results(
        {"results": [{"index": 0, "label": "P"}, {"index": 1, "label": "Q"}]}
    )
    rows = _parse_batch_response(raw, CHUNK, None, 120, 30)
    by_id = {r.row_id: r for r in rows}
    assert by_id["a"].parsed_label == "P"
    assert by_id["b"].parsed_label == "Q"
    assert all(r.parse_error is None for r in rows)


def test_parse_batch_lead_row_attribution() -> None:
    raw = _results(
        {"results": [{"index": 0, "label": "P"}, {"index": 1, "label": "Q"}]}
    )
    rows = _parse_batch_response(raw, CHUNK, None, 120, 30)
    # Lead row carries the batch's latency/tokens; the rest carry 0 / None.
    assert rows[0].latency_ms == 120
    assert rows[0].tokens_used == 30
    assert rows[1].latency_ms == 0
    assert rows[1].tokens_used is None


def test_parse_batch_out_of_order_index() -> None:
    raw = _results(
        {"results": [{"index": 1, "label": "Q"}, {"index": 0, "label": "P"}]}
    )
    rows = _parse_batch_response(raw, CHUNK, None, 1, 1)
    by_id = {r.row_id: r for r in rows}
    assert by_id["a"].parsed_label == "P"
    assert by_id["b"].parsed_label == "Q"


def test_parse_batch_missing_index_is_per_row_failure() -> None:
    raw = _results({"results": [{"index": 0, "label": "P"}]})  # index 1 absent
    rows = _parse_batch_response(raw, CHUNK, None, 1, 1)
    by_id = {r.row_id: r for r in rows}
    assert by_id["a"].parsed_label == "P"
    assert by_id["b"].parsed_label is None
    assert by_id["b"].parse_error is not None and "missing" in by_id["b"].parse_error


def test_parse_batch_duplicate_index_is_failure() -> None:
    raw = _results(
        {
            "results": [
                {"index": 0, "label": "P"},
                {"index": 0, "label": "Z"},
                {"index": 1, "label": "Q"},
            ]
        }
    )
    rows = _parse_batch_response(raw, CHUNK, None, 1, 1)
    by_id = {r.row_id: r for r in rows}
    assert by_id["a"].parse_error is not None and "duplicate" in by_id["a"].parse_error
    assert by_id["b"].parsed_label == "Q"


def test_parse_batch_non_json_fails_all_rows() -> None:
    rows = _parse_batch_response("not json at all", CHUNK, None, 1, 1)
    assert all(r.parse_error is not None for r in rows)
    assert all("decode error" in r.parse_error for r in rows)  # type: ignore[operator]


def test_parse_batch_missing_results_array_fails_all_rows() -> None:
    rows = _parse_batch_response(_results({"foo": 1}), CHUNK, None, 1, 1)
    assert all(r.parse_error is not None and "results" in r.parse_error for r in rows)


def test_parse_batch_structured_fields() -> None:
    fields = ["sentiment", "topic"]
    raw = _results(
        {
            "results": [
                {"index": 0, "sentiment": "pos", "topic": "a"},
                {"index": 1, "sentiment": "neg", "topic": "b"},
            ]
        }
    )
    rows = _parse_batch_response(raw, CHUNK, fields, 1, 1)
    by_id = {r.row_id: r for r in rows}
    assert by_id["a"].parsed_fields == {"sentiment": "pos", "topic": "a"}
    assert by_id["b"].parsed_fields == {"sentiment": "neg", "topic": "b"}


# ---------- batch-invariance guard integration tests -----------------------


@dataclass
class _FakeUsage:
    total_tokens: int


@dataclass
class _FakeMessage:
    content: str


@dataclass
class _FakeChoice:
    message: _FakeMessage


@dataclass
class _FakeResponse:
    choices: list[_FakeChoice]
    usage: _FakeUsage | None


def _label_for(inp: str) -> str:
    return f"lbl-{inp}"


def _make_batch_client(contaminate: bool) -> Any:
    """Fake client speaking the batched wire format.

    Returns one result per input. When ``contaminate`` and the call carries
    more than one row (a real batch), each label is altered — modelling
    cross-row contamination that a single-row (len-1) call cannot show.
    """

    async def _create(**kwargs: Any) -> _FakeResponse:
        items = json.loads(kwargs["messages"][1]["content"])
        batched = len(items) > 1
        results = []
        for it in items:
            label = _label_for(it["input"])
            if batched and contaminate:
                label = f"{label}-X"
            results.append({"index": it["index"], "label": label})
        content = json.dumps({"results": results})
        return _FakeResponse(
            choices=[_FakeChoice(message=_FakeMessage(content=content))],
            usage=_FakeUsage(total_tokens=5 * len(items)),
        )

    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=_create)
    return client


def _fixtures(tmp_path: Path, n: int) -> tuple[Path, Path, list[str]]:
    prompt = tmp_path / "prompt.md"
    prompt.write_text("<rules>batched classify</rules>")
    rows = [
        {"id": f"r{i}", "input": f"row{i}", "label": _label_for(f"row{i}")}
        for i in range(n)
    ]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)
    return prompt, base, [f"r{i}" for i in range(n)]


def _run(
    tmp_path: Path, client: Any, ids: list[str], prompt: Path, base: Path, **kw: Any
) -> dict:
    out = tmp_path / "results.json"
    run_inference(
        prompt_path=prompt,
        baseline_path=base,
        row_ids=ids,
        model="m",
        api_endpoint="http://t",
        concurrency=2,
        max_tokens=64,
        timeout=10.0,
        temperature=0.0,
        out_path=out,
        client=client,
        **kw,
    )
    return json.loads(out.read_text())


def test_batched_invariance_pass_keeps_batched(tmp_path: Path) -> None:
    prompt, base, ids = _fixtures(tmp_path, 6)
    client = _make_batch_client(contaminate=False)
    data = _run(
        tmp_path,
        client,
        ids,
        prompt,
        base,
        batch_size=3,
        invariance_sample=3,
        invariance_threshold=0.1,
    )
    inv = data["batch_invariance"]
    assert inv is not None
    assert inv["passed"] is True
    assert inv["fell_back_to_single_row"] is False
    assert inv["divergent_rows"] == 0
    # All rows present and correctly labelled.
    by_id = {p["row_id"]: p for p in data["predictions"]}
    assert len(by_id) == 6
    for i in range(6):
        assert by_id[f"r{i}"]["parsed_label"] == _label_for(f"row{i}")


def test_batched_invariance_fail_falls_back(tmp_path: Path) -> None:
    prompt, base, ids = _fixtures(tmp_path, 6)
    client = _make_batch_client(contaminate=True)
    data = _run(
        tmp_path,
        client,
        ids,
        prompt,
        base,
        batch_size=3,
        invariance_sample=3,
        invariance_threshold=0.1,
    )
    inv = data["batch_invariance"]
    assert inv["passed"] is False
    assert inv["fell_back_to_single_row"] is True
    assert inv["divergent_rows"] == 3  # the whole sample diverged
    assert inv["divergence_rate"] == pytest.approx(1.0)
    # Fallback scored single-row, so labels are the un-contaminated ones.
    by_id = {p["row_id"]: p for p in data["predictions"]}
    assert len(by_id) == 6
    for i in range(6):
        assert by_id[f"r{i}"]["parsed_label"] == _label_for(f"row{i}")


def test_batched_token_attribution_in_summary(tmp_path: Path) -> None:
    prompt, base, ids = _fixtures(tmp_path, 6)
    client = _make_batch_client(contaminate=False)
    data = _run(
        tmp_path,
        client,
        ids,
        prompt,
        base,
        batch_size=3,
        invariance_sample=3,
        invariance_threshold=0.1,
    )
    # Scored predictions = test sample (chunk of 3) + remaining (chunk of 3):
    # two batch calls, 5*3 tokens each -> 30; only the two lead rows carry it.
    assert data["summary"]["total_tokens"] == 30
    non_null = [p for p in data["predictions"] if p["tokens_used"] is not None]
    assert len(non_null) == 2


def test_single_row_has_no_invariance_block(tmp_path: Path) -> None:
    prompt, base, ids = _fixtures(tmp_path, 3)
    # Single-row legacy path uses a plain (non-array) user message.
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()

    async def _create(**kwargs: Any) -> _FakeResponse:
        inp = kwargs["messages"][1]["content"]
        return _FakeResponse(
            choices=[_FakeChoice(message=_FakeMessage(content=_label_for(inp)))],
            usage=_FakeUsage(total_tokens=3),
        )

    client.chat.completions.create = AsyncMock(side_effect=_create)
    data = _run(tmp_path, client, ids, prompt, base)  # batch_size defaults to 1
    assert data["batch_invariance"] is None


def test_invalid_batch_params_raise(tmp_path: Path) -> None:
    prompt, base, ids = _fixtures(tmp_path, 2)
    client = _make_batch_client(contaminate=False)
    out = tmp_path / "r.json"
    with pytest.raises(InferenceError, match="batch_size"):
        run_inference(
            prompt_path=prompt,
            baseline_path=base,
            row_ids=ids,
            model="m",
            api_endpoint="x",
            concurrency=1,
            max_tokens=8,
            timeout=1.0,
            temperature=0.0,
            out_path=out,
            client=client,
            batch_size=0,
        )
    with pytest.raises(InferenceError, match="threshold"):
        run_inference(
            prompt_path=prompt,
            baseline_path=base,
            row_ids=ids,
            model="m",
            api_endpoint="x",
            concurrency=1,
            max_tokens=8,
            timeout=1.0,
            temperature=0.0,
            out_path=out,
            client=client,
            batch_size=2,
            invariance_threshold=1.5,
        )


def test_count_divergent_helper() -> None:
    # Build two small prediction sets via the parser and compare.
    chunk = [("a", "x"), ("b", "y")]
    ref = _parse_batch_response(
        _results({"results": [{"index": 0, "label": "P"}, {"index": 1, "label": "Q"}]}),
        chunk,
        None,
        1,
        1,
    )
    test = _parse_batch_response(
        _results({"results": [{"index": 0, "label": "P"}, {"index": 1, "label": "Z"}]}),
        chunk,
        None,
        1,
        1,
    )
    assert _count_divergent(ref, test, None) == 1
