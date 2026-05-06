"""Smoke tests for inference.py — mocks the OpenAI client."""

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
    _parse_response,
    run_inference,
)


# ---------- _parse_response unit tests -------------------------------------


def test_parse_response_plain_label() -> None:
    label, err = _parse_response("Relevant")
    assert label == "Relevant"
    assert err is None


def test_parse_response_whitespace_strip() -> None:
    label, err = _parse_response("  Relevant\n")
    assert label == "Relevant"
    assert err is None


def test_parse_response_json_label_field() -> None:
    label, err = _parse_response('{"label": "Relevant", "rationale": "x"}')
    assert label == "Relevant"
    assert err is None


def test_parse_response_markdown_fence() -> None:
    label, err = _parse_response('```json\n{"label": "Not Relevant"}\n```')
    assert label == "Not Relevant"
    assert err is None


def test_parse_response_json_missing_label() -> None:
    label, err = _parse_response('{"foo": "bar"}')
    assert label is None
    assert err is not None and "no 'label'" in err


def test_parse_response_empty() -> None:
    label, err = _parse_response("   ")
    assert label is None
    assert err == "empty response"


def test_parse_response_bad_json() -> None:
    label, err = _parse_response('{"label": broken')
    assert label is None
    assert err is not None and "JSON decode error" in err


# ---------- run_inference integration test (mocked client) -----------------


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


def _fake_response(content: str, tokens: int = 12) -> _FakeResponse:
    return _FakeResponse(
        choices=[_FakeChoice(message=_FakeMessage(content=content))],
        usage=_FakeUsage(total_tokens=tokens),
    )


def _make_client(responses_by_input: dict[str, str]) -> Any:
    """Mock client whose chat.completions.create returns canned responses."""
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()

    async def _create(**kwargs: Any) -> _FakeResponse:
        user_msg = kwargs["messages"][1]["content"]
        return _fake_response(responses_by_input.get(user_msg, "Relevant"))

    client.chat.completions.create = AsyncMock(side_effect=_create)
    return client


def _setup_fixtures(tmp_path: Path) -> tuple[Path, Path]:
    prompt = tmp_path / "prompt.md"
    prompt.write_text("<rules>classify</rules>")
    rows = [
        {"id": "a", "input": "first row", "label": "Relevant"},
        {"id": "b", "input": "second row", "label": "Not Relevant"},
    ]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)
    return prompt, base


def test_run_inference_basic(tmp_path: Path) -> None:
    prompt, base = _setup_fixtures(tmp_path)
    client = _make_client({"first row": "Relevant", "second row": "Not Relevant"})
    out = tmp_path / "results.json"

    results = run_inference(
        prompt_path=prompt,
        baseline_path=base,
        row_ids=["a", "b"],
        model="test-model",
        api_endpoint="http://test",
        concurrency=2,
        max_tokens=16,
        timeout=10.0,
        temperature=0.0,
        out_path=out,
        client=client,
    )
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["model"] == "test-model"
    assert len(data["predictions"]) == 2
    assert data["summary"]["n_parsed"] == 2
    assert data["summary"]["n_parse_failures"] == 0
    by_id = {p["row_id"]: p for p in data["predictions"]}
    assert by_id["a"]["parsed_label"] == "Relevant"
    assert by_id["b"]["parsed_label"] == "Not Relevant"
    assert results.prompt_sha256  # non-empty hash


def test_run_inference_parse_failure_recorded(tmp_path: Path) -> None:
    prompt, base = _setup_fixtures(tmp_path)
    client = _make_client({"first row": "", "second row": "Not Relevant"})
    out = tmp_path / "results.json"

    run_inference(
        prompt_path=prompt,
        baseline_path=base,
        row_ids=["a", "b"],
        model="test-model",
        api_endpoint="http://test",
        concurrency=1,
        max_tokens=16,
        timeout=10.0,
        temperature=0.0,
        out_path=out,
        client=client,
    )
    data = json.loads(out.read_text())
    assert data["summary"]["n_parse_failures"] == 1
    assert data["summary"]["n_parsed"] == 1


def test_run_inference_retries_on_retryable(tmp_path: Path) -> None:
    """A retryable error should be retried, not fatal."""
    prompt, base = _setup_fixtures(tmp_path)
    out = tmp_path / "results.json"

    # Define a custom error class with the right name.
    class RateLimitError(Exception):
        pass

    call_count = {"n": 0}

    async def _create(**kwargs: Any) -> _FakeResponse:
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise RateLimitError("rate limited")
        return _fake_response("Relevant")

    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=_create)

    run_inference(
        prompt_path=prompt,
        baseline_path=base,
        row_ids=["a"],
        model="t",
        api_endpoint="http://t",
        concurrency=1,
        max_tokens=8,
        timeout=5.0,
        temperature=0.0,
        out_path=out,
        client=client,
        retry_policy={
            "max_attempts": 3,
            "initial_wait_s": 0.0,
            "max_wait_s": 0.0,
            "exponent": 2.0,
            "retry_on": ("RateLimitError",),
            "no_retry_on": (),
        },
    )
    assert call_count["n"] == 2
    data = json.loads(out.read_text())
    assert data["predictions"][0]["parsed_label"] == "Relevant"


def test_run_inference_missing_prompt(tmp_path: Path) -> None:
    _, base = _setup_fixtures(tmp_path)
    with pytest.raises(InferenceError, match="prompt not found"):
        run_inference(
            prompt_path=tmp_path / "nope.md",
            baseline_path=base,
            row_ids=["a"],
            model="t",
            api_endpoint="x",
            concurrency=1,
            max_tokens=8,
            timeout=5.0,
            temperature=0.0,
            out_path=tmp_path / "out.json",
            client=MagicMock(),
        )


def test_run_inference_unknown_row_id(tmp_path: Path) -> None:
    prompt, base = _setup_fixtures(tmp_path)
    with pytest.raises(InferenceError, match="not present in baseline"):
        run_inference(
            prompt_path=prompt,
            baseline_path=base,
            row_ids=["a", "missing_row"],
            model="t",
            api_endpoint="x",
            concurrency=1,
            max_tokens=8,
            timeout=5.0,
            temperature=0.0,
            out_path=tmp_path / "out.json",
            client=MagicMock(),
        )
