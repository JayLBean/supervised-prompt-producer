"""Async OpenAI-compatible inference for /spp-loop and /spp-finalize.

Implements the ResultsJSON schema from /spp-loop.md §4 step 6. The
script does *minimal* parsing — whitespace strip plus JSON extraction
when the response looks like JSON; canonical label matching is eval.py's
job. This separates "did the model say something parseable" from "is
the parsed output the right label" (see PR open question).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ._io import atomic_write_json
from ._schemas import PredictionRow, ResultsJSON, ResultsSummary

log = logging.getLogger(__name__)

DEFAULT_RETRY_POLICY: dict[str, Any] = {
    "max_attempts": 3,
    "initial_wait_s": 1.0,
    "max_wait_s": 30.0,
    "exponent": 2.0,
    # Retryable error class names (matched by class name to avoid hard
    # imports of OpenAI's exception hierarchy at module load).
    "retry_on": ("RateLimitError", "APIConnectionError", "APITimeoutError"),
    "no_retry_on": ("BadRequestError", "AuthenticationError", "PermissionDeniedError"),
}


class InferenceError(RuntimeError):
    """Fatal error during inference; message is user-facing."""


@dataclass
class _InferenceConfig:
    prompt_text: str
    prompt_path: str
    prompt_sha256: str
    model: str
    max_tokens: int
    timeout: float
    temperature: float
    retry_policy: dict[str, Any]


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_retryable(exc: BaseException, policy: dict[str, Any]) -> bool:
    name = type(exc).__name__
    if name in policy.get("no_retry_on", ()):
        return False
    return name in policy.get("retry_on", ())


def _parse_response(raw: str) -> tuple[str | None, str | None]:
    """Minimal parsing: try JSON-extract, else use stripped text.

    Returns (parsed_label, parse_error). parsed_label is None on
    failure. eval.py performs canonical label matching against
    LABEL_SPACE.
    """
    s = raw.strip()
    if not s:
        return None, "empty response"

    # Strip markdown code fences if present (common with chat models).
    fence = re.match(r"^```(?:json)?\s*\n(.*?)\n```\s*$", s, flags=re.DOTALL)
    if fence:
        s = fence.group(1).strip()

    # Try JSON first.
    if s.startswith("{") or s.startswith("["):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict) and "label" in obj:
                label = obj["label"]
                if isinstance(label, str):
                    return label.strip(), None
                return None, f"label field is not a string: {type(label).__name__}"
            return None, "JSON parsed but no 'label' field"
        except json.JSONDecodeError as e:
            return None, f"JSON decode error: {e}"

    # Otherwise treat the stripped text as the label.
    return s, None


async def _call_one(
    client: Any,
    config: _InferenceConfig,
    row_id: str,
    user_input: str,
    semaphore: asyncio.Semaphore,
) -> PredictionRow:
    """One row's inference call with retry + minimal parsing."""
    policy = config.retry_policy
    last_exc: BaseException | None = None

    async with semaphore:
        for attempt in range(1, policy["max_attempts"] + 1):
            t0 = time.monotonic()
            try:
                resp = await client.chat.completions.create(
                    model=config.model,
                    messages=[
                        {"role": "system", "content": config.prompt_text},
                        {"role": "user", "content": user_input},
                    ],
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    timeout=config.timeout,
                )
                latency_ms = int((time.monotonic() - t0) * 1000)
                raw = resp.choices[0].message.content or ""
                parsed_label, parse_error = _parse_response(raw)
                tokens_used = (
                    resp.usage.total_tokens if getattr(resp, "usage", None) else None
                )
                return PredictionRow(
                    row_id=row_id,
                    raw_response=raw,
                    parsed_label=parsed_label,
                    parse_error=parse_error,
                    latency_ms=latency_ms,
                    tokens_used=tokens_used,
                )
            except BaseException as exc:  # noqa: BLE001 - we re-raise non-retryable
                last_exc = exc
                if not _is_retryable(exc, policy) or attempt >= policy["max_attempts"]:
                    raise
                wait = min(
                    policy["initial_wait_s"] * (policy["exponent"] ** (attempt - 1)),
                    policy["max_wait_s"],
                )
                wait *= 0.5 + random.random()  # jitter
                log.warning(
                    "row %s attempt %d failed (%s); retrying in %.1fs",
                    row_id,
                    attempt,
                    type(exc).__name__,
                    wait,
                )
                await asyncio.sleep(wait)

    # Unreachable: we either return or re-raise above.
    raise last_exc  # type: ignore[misc]


async def _run_inference_async(
    client: Any,
    config: _InferenceConfig,
    rows: list[tuple[str, str]],
    concurrency: int,
) -> list[PredictionRow]:
    semaphore = asyncio.Semaphore(concurrency)
    tasks = [_call_one(client, config, rid, inp, semaphore) for rid, inp in rows]
    return await asyncio.gather(*tasks)


def run_inference(
    prompt_path: Path,
    baseline_path: Path,
    row_ids: list[str],
    model: str,
    api_endpoint: str,
    concurrency: int,
    max_tokens: int,
    timeout: float,
    temperature: float,
    out_path: Path,
    input_column: str = "input",
    id_column: str = "id",
    retry_policy: dict[str, Any] | None = None,
    api_key_env: str = "OPENAI_API_KEY",
    client: Any = None,
) -> ResultsJSON:
    """Run inference on the named rows and atomic-write results.

    ``client`` overrides the default ``openai.AsyncOpenAI`` construction;
    used for tests.
    """
    if not prompt_path.exists():
        raise InferenceError(f"prompt not found at {prompt_path}")
    if not baseline_path.exists():
        raise InferenceError(f"baseline not found at {baseline_path}")
    prompt_text = prompt_path.read_text(encoding="utf-8")

    df = pd.read_csv(baseline_path)
    if id_column not in df.columns:
        raise InferenceError(f"baseline missing id column '{id_column}'")
    if input_column not in df.columns:
        raise InferenceError(f"baseline missing input column '{input_column}'")

    df_idx = df.set_index(df[id_column].astype(str))
    missing = [rid for rid in row_ids if rid not in df_idx.index]
    if missing:
        raise InferenceError(
            f"row IDs not present in baseline: {missing[:5]}"
            f"{'…' if len(missing) > 5 else ''} ({len(missing)} total)"
        )

    if client is None:
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise InferenceError(
                f"environment variable {api_key_env} not set; "
                f"inference requires an API key"
            )
        try:
            from openai import AsyncOpenAI  # type: ignore[import-not-found]
        except ImportError as e:
            raise InferenceError(f"openai package not importable: {e}") from e
        client = AsyncOpenAI(base_url=api_endpoint, api_key=api_key)

    config = _InferenceConfig(
        prompt_text=prompt_text,
        prompt_path=str(prompt_path),
        prompt_sha256=_hash_text(prompt_text),
        model=model,
        max_tokens=max_tokens,
        timeout=timeout,
        temperature=temperature,
        retry_policy=retry_policy or DEFAULT_RETRY_POLICY,
    )

    rows = [(rid, str(df_idx.loc[rid][input_column])) for rid in row_ids]

    t0 = time.monotonic()
    predictions = asyncio.run(_run_inference_async(client, config, rows, concurrency))
    wall_clock_ms = int((time.monotonic() - t0) * 1000)

    n_parsed = sum(1 for p in predictions if p.parsed_label is not None)
    summary = ResultsSummary(
        n_rows=len(predictions),
        n_parsed=n_parsed,
        n_parse_failures=len(predictions) - n_parsed,
        total_tokens=sum((p.tokens_used or 0) for p in predictions),
        total_latency_ms=sum(p.latency_ms for p in predictions),
        wall_clock_ms=wall_clock_ms,
    )

    results = ResultsJSON(
        model=model,
        prompt_path=config.prompt_path,
        prompt_sha256=config.prompt_sha256,
        predictions=predictions,
        summary=summary,
    )
    atomic_write_json(out_path, results.model_dump())
    log.info(
        "inference complete: %d rows, %d parsed, %d parse failures, %dms wall",
        summary.n_rows,
        summary.n_parsed,
        summary.n_parse_failures,
        wall_clock_ms,
    )
    return results


def _row_ids_from_splits(splits_path: Path, partitions: list[str]) -> list[str]:
    data = json.loads(splits_path.read_text(encoding="utf-8"))
    out: list[str] = []
    for p in partitions:
        if p not in data["row_ids"]:
            raise InferenceError(f"partition '{p}' not in splits.json")
        out.extend(data["row_ids"][p])
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenAI-compatible inference.")
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--api-endpoint", type=str, default="https://api.openai.com/v1")

    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--row-ids", type=str, help="Comma-separated row IDs.")
    src.add_argument("--row-ids-from", type=Path, help="Path to splits.json.")
    parser.add_argument(
        "--partition",
        type=str,
        default="train,dev",
        help="Comma-separated partitions when using --row-ids-from.",
    )

    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--input-column", type=str, default="input")
    parser.add_argument("--id-column", type=str, default="id")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        if args.row_ids:
            row_ids = [s.strip() for s in args.row_ids.split(",") if s.strip()]
        else:
            partitions = [s.strip() for s in args.partition.split(",") if s.strip()]
            row_ids = _row_ids_from_splits(args.row_ids_from, partitions)

        run_inference(
            prompt_path=args.prompt,
            baseline_path=args.baseline,
            row_ids=row_ids,
            model=args.model,
            api_endpoint=args.api_endpoint,
            concurrency=args.concurrency,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
            temperature=args.temperature,
            out_path=args.out,
            input_column=args.input_column,
            id_column=args.id_column,
        )
    except InferenceError as e:
        log.error("inference failed: %s", e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
