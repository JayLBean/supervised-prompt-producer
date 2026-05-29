"""Inferential statistics for /spp-finalize (DESIGN.md §7.1.4).

Computes a percentile bootstrap confidence interval on the aggregate metric of
a single scored partition, by resampling the per-row score vector already
materialized in an ``eval.json`` (the ``per_row`` array added in the v0.3
retention bucket). ``/spp-finalize`` scores one prompt — the frozen
``PROMPT_FROZEN_v01`` — on the sacred test set, so this is a single-sample
interval around that prompt's test aggregate, not a two-prompt comparison.

The estimator lives here, outside ``/spp-loop``, on purpose: a confidence
interval is a score-derived quantity, and score-derived quantities must never
enter a loop subagent's context (auditor score-blindness, invariant #2). It is
computed only at finalize, after the loop has terminated, and resamples an
already-read in-memory vector — it never re-reads the sacred test partition
(invariants #6/#7). The result is descriptive only; it never gates the loop or
weights a verdict (invariant #14).

Pure stdlib plus the numeric stack ``eval.py`` already uses; no new dependency
(no ``scipy``).
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
from pathlib import Path
from typing import Any

from ._io import atomic_write_json
from ._schemas import BootstrapCI, EvalJSON
from .eval import compute_primary_metric

log = logging.getLogger(__name__)

_PARSE_FAILURE = "__PARSE_FAILURE__"


class StatsError(RuntimeError):
    """Fatal error during statistics; message is user-facing."""


def _percentile(sorted_vals: list[float], q: float) -> float:
    """Linear-interpolation percentile of an ascending-sorted list; q in [0, 100]."""
    if not sorted_vals:
        raise StatsError("cannot take a percentile of an empty distribution")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = (q / 100.0) * (len(sorted_vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = rank - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def bootstrap_aggregate_ci(
    y_true: list[str],
    y_pred: list[str],
    metric: str,
    metric_kwargs: dict[str, Any],
    label_space: list[str],
    *,
    n_resamples: int = 10_000,
    seed: int = 0,
    confidence: float = 0.95,
) -> BootstrapCI:
    """Percentile bootstrap CI on the aggregate metric of one scored sample.

    Each resample draws ``n`` row indices with replacement and recomputes the
    metric via ``compute_primary_metric`` — the same function that produced the
    headline number — so the interval brackets the reported aggregate rather
    than an averaged per-row proxy (which would be wrong for set-level metrics
    like F1). Resampling operates on the in-memory vectors only; it never reads
    the test partition.
    """
    n = len(y_true)
    if n != len(y_pred):
        raise StatsError("y_true and y_pred must be the same length")
    if n == 0:
        raise StatsError("no rows to bootstrap")
    if not 0.0 < confidence < 1.0:
        raise StatsError(f"confidence must be in (0, 1); got {confidence}")
    if n_resamples < 1:
        raise StatsError(f"n_resamples must be >= 1; got {n_resamples}")

    point = compute_primary_metric(y_true, y_pred, metric, metric_kwargs, label_space)

    rng = random.Random(seed)
    population = range(n)
    estimates: list[float] = []
    for _ in range(n_resamples):
        idx = rng.choices(population, k=n)
        estimates.append(
            compute_primary_metric(
                [y_true[i] for i in idx],
                [y_pred[i] for i in idx],
                metric,
                metric_kwargs,
                label_space,
            )
        )
    estimates.sort()

    alpha = 1.0 - confidence
    return BootstrapCI(
        metric=metric,
        point_estimate=point,
        ci_low=_percentile(estimates, 100.0 * (alpha / 2.0)),
        ci_high=_percentile(estimates, 100.0 * (1.0 - alpha / 2.0)),
        confidence=confidence,
        n_resamples=n_resamples,
        seed=seed,
        n_rows=n,
    )


def attach_aggregate_ci(
    eval_path: Path,
    *,
    n_resamples: int = 10_000,
    seed: int = 0,
    confidence: float = 0.95,
) -> BootstrapCI:
    """Bootstrap the aggregate CI from an ``eval.json``; write it back into that file.

    Reads the retained ``per_row`` vector, computes the interval, sets
    ``aggregate_ci``, and rewrites the file via atomic checkpoint. No model
    calls and no test-partition read — the input is a score artifact produced
    earlier in finalize.
    """
    if not eval_path.exists():
        raise StatsError(f"eval not found at {eval_path}")
    eval_json = EvalJSON.model_validate_json(eval_path.read_text(encoding="utf-8"))
    if not eval_json.per_row:
        raise StatsError(
            f"{eval_path} has no per_row vector to resample (needs the v0.3 "
            "retention bucket); re-run scoring with a current eval.py"
        )

    y_true = [r.y_true for r in eval_json.per_row]
    y_pred = [r.y_pred for r in eval_json.per_row]
    label_space = [lbl for lbl in eval_json.labels if lbl != _PARSE_FAILURE]

    ci = bootstrap_aggregate_ci(
        y_true,
        y_pred,
        eval_json.metric,
        eval_json.metric_kwargs,
        label_space,
        n_resamples=n_resamples,
        seed=seed,
        confidence=confidence,
    )
    eval_json.aggregate_ci = ci
    atomic_write_json(eval_path, eval_json.model_dump())
    log.info(
        "bootstrap CI: %s=%.4f [%.4f, %.4f] (%.0f%%, B=%d, seed=%d, n=%d) -> %s",
        ci.metric,
        ci.point_estimate,
        ci.ci_low,
        ci.ci_high,
        ci.confidence * 100,
        ci.n_resamples,
        ci.seed,
        ci.n_rows,
        eval_path,
    )
    return ci


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap CI on the aggregate metric of a scored partition "
            "(DESIGN.md §7.1.4). Finalize-only; resamples the retained per-row "
            "scores in an eval.json and writes the interval back into it."
        )
    )
    parser.add_argument("--eval", type=Path, required=True)
    parser.add_argument("--n-resamples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--confidence", type=float, default=0.95)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        attach_aggregate_ci(
            args.eval,
            n_resamples=args.n_resamples,
            seed=args.seed,
            confidence=args.confidence,
        )
    except StatsError as e:
        log.error("stats failed: %s", e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
