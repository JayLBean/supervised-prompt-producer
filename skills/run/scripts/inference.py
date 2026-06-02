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
    field_names: list[str] | None = None


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    """Conservative, dependency-free token estimate (DESIGN.md §7.1.7).

    ASCII text is counted at ~4 characters per token (typical of byte-level
    BPE on English); every non-ASCII character is counted as one token,
    because non-Latin scripts (CJK, Thai, Devanagari, …) tokenize far
    heavier — often one or more tokens per character. The estimate
    deliberately errs high: over-warning costs a log line, a silently
    truncated row costs a wrong prediction. It is a safeguard heuristic,
    not an exact count — ``spp`` ships no tokenizer dependency.
    """
    ascii_n = sum(1 for ch in text if ch.isascii())
    non_ascii_n = len(text) - ascii_n
    return -(-ascii_n // 4) + non_ascii_n  # ceil(ascii_n / 4) + non_ascii_n


def truncation_preflight(
    rows: list[tuple[str, str]],
    prompt_text: str,
    max_tokens: int,
    context_window: int,
) -> list[tuple[str, int]]:
    """Rows whose estimated prompt risks truncation, worst first.

    A row is at risk when the estimated tokens of the system prompt plus
    the row's user input exceed the space left in ``context_window`` after
    reserving ``max_tokens`` for the response — a silently truncated input
    yields a wrong prediction (DESIGN.md §7.1.7). Keyed on token count, not
    language: this is a correctness safeguard for any long row, and it
    bites verbose-tokenizing scripts hardest. Returns ``(row_id,
    estimated_prompt_tokens)`` sorted by estimate descending; empty when
    none are at risk.
    """
    budget = context_window - max_tokens
    prompt_tokens = estimate_tokens(prompt_text)
    at_risk = [
        (rid, prompt_tokens + estimate_tokens(user_input))
        for rid, user_input in rows
        if prompt_tokens + estimate_tokens(user_input) > budget
    ]
    at_risk.sort(key=lambda pair: pair[1], reverse=True)
    return at_risk


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


def _strip_fence(s: str) -> str:
    """Strip a leading/trailing markdown code fence if present."""
    fence = re.match(r"^```(?:json)?\s*\n(.*?)\n```\s*$", s, flags=re.DOTALL)
    return fence.group(1).strip() if fence else s


def _output_schema_field_names(schema_path: Path) -> list[str]:
    """Top-level OUTPUT_SCHEMA field names, in declared order.

    Reads the JSON Schema (draft 2020-12) document the task's OUTPUT_SCHEMA
    renders to (``plan.md`` §2). Nested objects are scored by recursion in a
    later bucket; this layer parses the top-level ``properties`` keys.
    """
    if not schema_path.exists():
        raise InferenceError(f"schema not found at {schema_path}")
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise InferenceError(f"schema is not valid JSON: {e}") from e
    props = schema.get("properties")
    if not isinstance(props, dict) or not props:
        raise InferenceError("schema has no non-empty 'properties' object")
    return list(props.keys())


def _parse_structured(
    raw: str, field_names: list[str]
) -> tuple[dict[str, str | None], dict[str, str], str | None]:
    """Extract each OUTPUT_SCHEMA field from a K>1 JSON response (DESIGN §7.1.5).

    Returns ``(parsed_fields, field_parse_errors, row_error)``. Minimal parsing
    only: each field's value is pulled as a string (scalars stringified,
    arrays/objects JSON-encoded with sorted keys for stable scoring), missing
    or null values get a per-field error, and ``row_error`` is set when the
    response is not a JSON object. eval.py canonicalizes and scores.
    """
    parsed: dict[str, str | None] = {f: None for f in field_names}
    errors: dict[str, str] = {}
    s = raw.strip()
    if not s:
        for f in field_names:
            errors[f] = "empty response"
        return parsed, errors, "empty response"

    s = _strip_fence(s)
    try:
        obj = json.loads(s)
    except json.JSONDecodeError as e:
        msg = f"JSON decode error: {e}"
        for f in field_names:
            errors[f] = msg
        return parsed, errors, msg
    if not isinstance(obj, dict):
        msg = f"expected a JSON object, got {type(obj).__name__}"
        for f in field_names:
            errors[f] = msg
        return parsed, errors, msg

    for f in field_names:
        if f not in obj:
            errors[f] = "missing field"
            continue
        val = obj[f]
        if val is None:
            errors[f] = "null value"
        elif isinstance(val, str):
            parsed[f] = val.strip()
        elif isinstance(val, bool):
            parsed[f] = "true" if val else "false"
        elif isinstance(val, (int, float)):
            parsed[f] = str(val)
        else:  # list / dict — JSON-encode for stable downstream parsing
            parsed[f] = json.dumps(val, separators=(",", ":"), sort_keys=True)
    return parsed, errors, None


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
                tokens_used = (
                    resp.usage.total_tokens if getattr(resp, "usage", None) else None
                )
                if config.field_names is not None:
                    parsed_fields, field_errors, row_error = _parse_structured(
                        raw, config.field_names
                    )
                    return PredictionRow(
                        row_id=row_id,
                        raw_response=raw,
                        parsed_label=None,
                        parse_error=row_error,
                        parsed_fields=parsed_fields,
                        field_parse_errors=field_errors,
                        latency_ms=latency_ms,
                        tokens_used=tokens_used,
                    )
                parsed_label, parse_error = _parse_response(raw)
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
    schema_path: Path | None = None,
    retry_policy: dict[str, Any] | None = None,
    api_key_env: str = "OPENAI_API_KEY",
    context_window: int | None = None,
    client: Any = None,
) -> ResultsJSON:
    """Run inference on the named rows and atomic-write results.

    ``client`` overrides the default ``openai.AsyncOpenAI`` construction;
    used for tests. When ``context_window`` is given, a pre-flight warns
    about rows whose estimated prompt risks truncation (DESIGN.md §7.1.7);
    it is advisory only and never blocks the run.
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

    field_names = (
        _output_schema_field_names(schema_path) if schema_path is not None else None
    )

    config = _InferenceConfig(
        prompt_text=prompt_text,
        prompt_path=str(prompt_path),
        prompt_sha256=_hash_text(prompt_text),
        model=model,
        max_tokens=max_tokens,
        timeout=timeout,
        temperature=temperature,
        retry_policy=retry_policy or DEFAULT_RETRY_POLICY,
        field_names=field_names,
    )

    rows = [(rid, str(df_idx.loc[rid][input_column])) for rid in row_ids]

    # Truncation pre-flight (DESIGN.md §7.1.7): advisory, never blocks.
    # Only computed when a context window is supplied — spp does not guess
    # a model's window.
    if context_window is not None:
        at_risk = truncation_preflight(rows, prompt_text, max_tokens, context_window)
        if at_risk:
            preview = ", ".join(f"{rid} (~{est} tok)" for rid, est in at_risk[:5])
            log.warning(
                "truncation risk: %d of %d rows have an estimated prompt "
                "exceeding the %d-token context window minus %d reserved for "
                "the response; worst: %s%s. A truncated row yields a wrong "
                "prediction; non-Latin scripts tokenize heavier (DESIGN §7.1.7).",
                len(at_risk),
                len(rows),
                context_window,
                max_tokens,
                preview,
                "…" if len(at_risk) > 5 else "",
            )

    t0 = time.monotonic()
    predictions = asyncio.run(_run_inference_async(client, config, rows, concurrency))
    wall_clock_ms = int((time.monotonic() - t0) * 1000)

    if field_names is not None:
        n_parsed = sum(
            1 for p in predictions if not p.field_parse_errors and p.parse_error is None
        )
    else:
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
    parser.add_argument(
        "--context-window",
        type=int,
        default=None,
        help=(
            "Model context window in tokens. When set, a pre-flight warns "
            "about rows whose estimated prompt risks truncation (advisory; "
            "DESIGN.md §7.1.7). Omitted = no truncation check."
        ),
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--input-column", type=str, default="input")
    parser.add_argument("--id-column", type=str, default="id")
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="Path to the OUTPUT_SCHEMA JSON; enables K>1 multi-field parsing.",
    )
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
            schema_path=args.schema,
            context_window=args.context_window,
        )
    except InferenceError as e:
        log.error("inference failed: %s", e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
