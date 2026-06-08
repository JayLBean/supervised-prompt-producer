"""End-to-end fixture: an adopted batch-I/O structure runs inference → eval
(DESIGN.md §7.1.10 bucket 6).

Models the payoff of adopting the v0.9 batch-I/O structure. A batched run's
`results.json` has the same per-row prediction shape a single-row run does
(plus the `batch_invariance` block and lead-row latency/token attribution),
so it scores through the real `compute_eval` unchanged — proving the adopted
structure is scorable end-to-end without any network/model call, the same
way `test_fixtures_technique_forms` proves an adopted output form is.

The second test is the guard's payoff: when batching would contaminate
predictions, the invariance check falls back to single-row, so the eval that
drives stop/ship decisions reflects honest single-row behavior — invariant
#13 held mechanically, not by trust.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pandas as pd

from spp_scripts.eval import compute_eval
from spp_scripts.inference import run_inference


def _label_for(inp: str) -> str:
    return f"lbl-{inp}"


@dataclass
class _Usage:
    total_tokens: int


@dataclass
class _Msg:
    content: str


@dataclass
class _Choice:
    message: _Msg


@dataclass
class _Resp:
    choices: list[_Choice]
    usage: _Usage | None


def _batch_client(contaminate: bool) -> Any:
    """Batched-wire fake; contaminates only on a real (len>1) batch."""

    async def _create(**kwargs: Any) -> _Resp:
        items = json.loads(kwargs["messages"][1]["content"])
        batched = len(items) > 1
        results = []
        for it in items:
            label = _label_for(it["input"])
            if batched and contaminate:
                label = f"{label}-X"  # would not match gold -> would tank eval
            results.append({"index": it["index"], "label": label})
        return _Resp(
            choices=[_Choice(_Msg(json.dumps({"results": results})))],
            usage=_Usage(total_tokens=5 * len(items)),
        )

    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=_create)
    return client


def _fixture(tmp_path: Path, n: int) -> tuple[Path, Path, list[str]]:
    prompt = tmp_path / "prompt.md"
    prompt.write_text("<rules>batched classify</rules>")
    rows = [
        {"id": f"r{i}", "input": f"row{i}", "label": _label_for(f"row{i}")}
        for i in range(n)
    ]
    base = tmp_path / "baseline.csv"
    pd.DataFrame(rows).to_csv(base, index=False)
    return prompt, base, [f"r{i}" for i in range(n)]


def _infer_batched(
    tmp_path: Path, client: Any, prompt: Path, base: Path, ids: list[str]
) -> Path:
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
        batch_size=3,
        invariance_sample=3,
        invariance_threshold=0.1,
    )
    return out


def test_adopted_batch_io_scores_end_to_end(tmp_path: Path) -> None:
    """A clean batched run scores through compute_eval like any other run."""
    prompt, base, ids = _fixture(tmp_path, 6)
    res = _infer_batched(tmp_path, _batch_client(contaminate=False), prompt, base, ids)

    # The batched results.json carries the guard outcome and still scores.
    results = json.loads(res.read_text())
    assert results["batch_invariance"]["passed"] is True
    assert results["batch_invariance"]["fell_back_to_single_row"] is False

    out = tmp_path / "eval.json"
    e = compute_eval(res, base, ids, "accuracy", out)
    assert e.primary_value == 1.0  # every batched prediction matched gold
    assert e.n_rows_evaluated == 6
    assert e.n_parse_failures_in_input == 0


def test_batch_io_fallback_keeps_eval_honest(tmp_path: Path) -> None:
    """Guard payoff: contamination → single-row fallback → eval stays honest.

    The contaminating client would emit ``lbl-rowN-X`` on a real batch, which
    does not match gold ``lbl-rowN``; scoring those would tank accuracy. The
    invariance guard catches the divergence and scores single-row instead, so
    the eval that drives decisions reflects deployed behavior (#13).
    """
    prompt, base, ids = _fixture(tmp_path, 6)
    res = _infer_batched(tmp_path, _batch_client(contaminate=True), prompt, base, ids)

    results = json.loads(res.read_text())
    assert results["batch_invariance"]["passed"] is False
    assert results["batch_invariance"]["fell_back_to_single_row"] is True
    # Defence-in-depth: no contaminated label ("…-X", emitted only on a real
    # batch) survives into the scored predictions — the batched set is dropped.
    labels = [p["parsed_label"] for p in results["predictions"]]
    assert all(label is not None and not label.endswith("-X") for label in labels)

    out = tmp_path / "eval.json"
    e = compute_eval(res, base, ids, "accuracy", out)
    # Honest single-row labels were scored, not the contaminated batched ones.
    assert e.primary_value == 1.0
    assert e.n_rows_evaluated == 6
