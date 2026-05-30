"""Metric computation for /spp-loop and /spp-finalize.

Implements the EvalJSON schema from /spp-loop.md §4 step 7. Performs
canonical label matching on the parsed_label field of results.json
(inference.py does minimal parsing only).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
)

from ._io import atomic_write_json
from ._metrics import (
    ERROR_METRICS,
    MetricError,
    compute_aggregate,
    compute_field_metric,
)
from ._schemas import (
    Aggregate,
    EvalJSON,
    FieldEval,
    FloorCompliance,
    PerClassMetrics,
    PerRowScore,
)

log = logging.getLogger(__name__)

SUPPORTED_METRICS = {"f1", "accuracy", "precision", "recall"}


class EvalError(RuntimeError):
    """Fatal error during eval; message is user-facing."""


def _canonical_label_match(parsed: str | None, label_space: list[str]) -> str | None:
    """Match parsed_label against LABEL_SPACE (case-insensitive, trim)."""
    if parsed is None:
        return None
    p = parsed.strip().lower()
    for canonical in label_space:
        if p == canonical.strip().lower():
            return canonical
    return None


def compute_primary_metric(
    y_true: list[str],
    y_pred: list[str],
    metric: str,
    metric_kwargs: dict[str, Any],
    label_space: list[str],
) -> float:
    """Compute the scalar primary metric for one (y_true, y_pred) pair.

    Extracted so that ``compute_eval`` and the bootstrap resampler in
    ``_stats.py`` score a resample identically — a resample must be scored by
    the same function as the headline number, or the confidence interval would
    not be an interval around that number.
    """
    binary = len(label_space) == 2
    positive_label = metric_kwargs.get("positive_label")

    if metric == "accuracy":
        return float(accuracy_score(y_true, y_pred))
    if metric == "f1":
        if binary:
            if positive_label is None:
                raise EvalError("binary f1 requires metric_kwargs['positive_label']")
            return float(
                f1_score(y_true, y_pred, pos_label=positive_label, zero_division=0)
            )
        return float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    if metric == "precision":
        if binary:
            if positive_label is None:
                raise EvalError(
                    "binary precision requires metric_kwargs['positive_label']"
                )
            return float(
                precision_score(
                    y_true, y_pred, pos_label=positive_label, zero_division=0
                )
            )
        return float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    if metric == "recall":
        if binary:
            if positive_label is None:
                raise EvalError(
                    "binary recall requires metric_kwargs['positive_label']"
                )
            return float(
                recall_score(y_true, y_pred, pos_label=positive_label, zero_division=0)
            )
        return float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    raise EvalError(  # pragma: no cover - callers guard against this
        f"metric '{metric}' not supported; supported: {sorted(SUPPORTED_METRICS)}"
    )


def compute_eval(
    results_path: Path,
    baseline_path: Path,
    row_ids: list[str],
    metric: str,
    out_path: Path,
    metric_kwargs: dict[str, Any] | None = None,
    label_column: str = "label",
    id_column: str = "id",
    label_space: list[str] | None = None,
) -> EvalJSON:
    """Compute metric, build EvalJSON, atomic-write to ``out_path``."""
    metric_kwargs = metric_kwargs or {}
    if metric not in SUPPORTED_METRICS:
        raise EvalError(
            f"metric '{metric}' not supported; supported: {sorted(SUPPORTED_METRICS)}"
        )

    if not results_path.exists():
        raise EvalError(f"results not found at {results_path}")
    if not baseline_path.exists():
        raise EvalError(f"baseline not found at {baseline_path}")

    results = json.loads(results_path.read_text(encoding="utf-8"))
    df = pd.read_csv(baseline_path)
    if label_column not in df.columns:
        raise EvalError(f"baseline missing label column '{label_column}'")
    df_idx = df.set_index(df[id_column].astype(str))

    # Match the partition's row IDs against what's in results.json.
    pred_by_row = {p["row_id"]: p for p in results["predictions"]}
    missing = [rid for rid in row_ids if rid not in pred_by_row]
    if missing:
        raise EvalError(
            f"{len(missing)} row IDs in partition not present in results.json; "
            f"first missing: {missing[:5]}"
        )

    if label_space is None:
        label_space = sorted(df[label_column].astype(str).unique().tolist())

    y_true: list[str] = []
    y_pred: list[str] = []
    n_parse_failures = 0

    for rid in row_ids:
        truth = str(df_idx.loc[rid][label_column])
        pred_row = pred_by_row[rid]
        canonical = _canonical_label_match(pred_row.get("parsed_label"), label_space)
        if canonical is None:
            n_parse_failures += 1
            # Treat unparseable predictions as a sentinel mismatch by using
            # a "__PARSE_FAILURE__" pseudo-label that will never match truth.
            # Counts as misprediction in metric computation.
            canonical = "__PARSE_FAILURE__"
        y_true.append(truth)
        y_pred.append(canonical)

    # Compute primary metric (shared with the bootstrap resampler).
    primary = compute_primary_metric(y_true, y_pred, metric, metric_kwargs, label_space)

    # Confusion matrix + per-class.
    cm_labels = list(label_space)
    if "__PARSE_FAILURE__" in y_pred:
        cm_labels = list(label_space) + ["__PARSE_FAILURE__"]
    cm = confusion_matrix(y_true, y_pred, labels=cm_labels).tolist()

    p_arr, r_arr, f_arr, supp_arr = precision_recall_fscore_support(
        y_true, y_pred, labels=cm_labels, zero_division=0
    )
    per_class: dict[str, PerClassMetrics] = {}
    for i, lbl in enumerate(cm_labels):
        per_class[lbl] = PerClassMetrics(
            precision=float(p_arr[i]),
            recall=float(r_arr[i]),
            f1=float(f_arr[i]),
            support=int(supp_arr[i]),
        )

    # Retain the per-row score vector for the v0.3 finalize statistics
    # (DESIGN.md §7.1.4). row_ids, y_true, y_pred are built in lockstep.
    per_row = [
        PerRowScore(row_id=rid, y_true=truth, y_pred=pred, correct=truth == pred)
        for rid, truth, pred in zip(row_ids, y_true, y_pred, strict=True)
    ]

    eval_json = EvalJSON(
        metric=metric,
        metric_kwargs=metric_kwargs,
        primary_value=primary,
        n_rows_evaluated=len(row_ids),
        n_parse_failures_in_input=n_parse_failures,
        confusion_matrix=cm,
        labels=cm_labels,
        per_class=per_class,
        per_row=per_row,
    )
    atomic_write_json(out_path, eval_json.model_dump())
    log.info(
        "eval complete: %s=%.4f (n=%d, parse_failures=%d) -> %s",
        metric,
        primary,
        len(row_ids),
        n_parse_failures,
        out_path,
    )
    return eval_json


def compute_eval_multifield(
    results_path: Path,
    baseline_path: Path,
    row_ids: list[str],
    field_metrics: dict[str, dict[str, Any]],
    out_path: Path,
    aggregate: dict[str, Any] | None = None,
    floors: dict[str, float] | None = None,
    id_column: str = "id",
) -> EvalJSON:
    """Score a K>1 multi-field run: each field's metric over its own column.

    ``field_metrics`` maps a field name to ``{"metric": <name>, "kwargs": {...}}``
    (the field's METRIC_NAME from ``plan.md`` §4 plus any metric options). Gold
    comes from the ``baseline.csv`` column named after the field; predictions
    from ``results.json``'s per-row ``parsed_fields`` (an absent field scores as
    a mismatch and is counted as a parse failure). Emits ``EvalJSON.per_field``
    by delegating to ``_metrics.compute_field_metric``, and the ``aggregate``
    section per ``aggregate`` = ``{"strategy": macro|weighted|min, "weights":
    {...}}`` (default ``macro``). The top-level ``primary_value`` is that
    aggregate (the number the loop's stop-discipline reads). Averaging across
    incompatible metric families is refused (see below); ``floor_compliance`` is
    a later bucket.
    """
    if not field_metrics:
        raise EvalError("field_metrics is empty; nothing to score")
    if not results_path.exists():
        raise EvalError(f"results not found at {results_path}")
    if not baseline_path.exists():
        raise EvalError(f"baseline not found at {baseline_path}")

    results = json.loads(results_path.read_text(encoding="utf-8"))
    df = pd.read_csv(baseline_path)
    df_idx = df.set_index(df[id_column].astype(str))

    pred_by_row = {p["row_id"]: p for p in results["predictions"]}
    missing = [rid for rid in row_ids if rid not in pred_by_row]
    if missing:
        raise EvalError(
            f"{len(missing)} row IDs in partition not present in results.json; "
            f"first missing: {missing[:5]}"
        )

    per_field: dict[str, FieldEval] = {}
    for fname, spec in field_metrics.items():
        if "metric" not in spec:
            raise EvalError(f"field '{fname}' has no 'metric' in field_metrics")
        if fname not in df.columns:
            raise EvalError(f"baseline missing gold column '{fname}'")
        metric = str(spec["metric"])
        kwargs = spec.get("kwargs", {})
        y_true: list[Any] = []
        y_pred: list[str] = []
        n_fail = 0
        for rid in row_ids:
            y_true.append(df_idx.loc[rid][fname])
            parsed = pred_by_row[rid].get("parsed_fields") or {}
            val = parsed.get(fname)
            if val is None:
                n_fail += 1
                val = ""  # absent prediction scores as a mismatch
            y_pred.append(str(val))
        try:
            value = compute_field_metric(metric, y_true, y_pred, kwargs)
        except MetricError as e:
            raise EvalError(f"field '{fname}': {e}") from e
        per_field[fname] = FieldEval(
            metric=metric,
            primary_value=value,
            n_rows=len(row_ids),
            n_parse_failures=n_fail,
        )

    # Aggregate (metric-design §3.2). Refuse to average across incompatible
    # metric families — a bounded [0,1]-higher-better score with an unbounded
    # lower-better error — as defense-in-depth behind metric-design's plan-time
    # dimensional-nonsense revise signal (DESIGN §7.1.5).
    error_fields = [f for f, fe in per_field.items() if fe.metric in ERROR_METRICS]
    if error_fields:
        raise EvalError(
            "cannot compute a cross-field aggregate: the error-family metrics "
            f"(mae/rmse) on {error_fields} are unbounded and lower-is-better; "
            "score numeric fields with within_tolerance to include them in the "
            "composite, or keep them on a per-field floor and report per-field"
        )
    agg_spec = aggregate or {"strategy": "macro"}
    strategy = str(agg_spec.get("strategy", "macro"))
    weights = agg_spec.get("weights")
    field_values = {f: fe.primary_value for f, fe in per_field.items()}
    try:
        agg_value = compute_aggregate(field_values, strategy, weights)
    except MetricError as e:
        raise EvalError(f"aggregate: {e}") from e

    # Floor compliance (metric-design §3.3). Per-field floor on the field's
    # primary metric: met if value >= floor, else unmet; not_specified when no
    # floor is given. An unmet floor with the aggregate at target drives the
    # loop's EARLY_STOP_FLOOR_UNMET branch (the loop reads this; eval emits it).
    floors = floors or {}
    floor_compliance: dict[str, FloorCompliance] = {}
    for fname, fe in per_field.items():
        fl = floors.get(fname)
        if fl is None:
            status = "not_specified"
        elif fe.primary_value >= fl:
            status = "met"
        else:
            status = "unmet"
        floor_compliance[fname] = FloorCompliance(floor=fl, status=status)

    eval_json = EvalJSON(
        metric="multi_field",
        primary_value=agg_value,
        n_rows_evaluated=len(row_ids),
        n_parse_failures_in_input=sum(fe.n_parse_failures for fe in per_field.values()),
        confusion_matrix=[],
        labels=[],
        per_class={},
        per_field=per_field,
        aggregate=Aggregate(strategy=strategy, value=agg_value, weights=weights),
        floor_compliance=floor_compliance,
    )
    atomic_write_json(out_path, eval_json.model_dump())
    log.info(
        "multi-field eval: %d fields, %s aggregate=%.4f (n=%d) -> %s",
        len(per_field),
        strategy,
        agg_value,
        len(row_ids),
        out_path,
    )
    return eval_json


def _row_ids_from_splits(splits_path: Path, partitions: list[str]) -> list[str]:
    data = json.loads(splits_path.read_text(encoding="utf-8"))
    out: list[str] = []
    for p in partitions:
        if p not in data["row_ids"]:
            raise EvalError(f"partition '{p}' not in splits.json")
        out.extend(data["row_ids"][p])
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute eval metrics.")
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)

    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--row-ids", type=str)
    src.add_argument("--row-ids-from", type=Path)
    parser.add_argument("--partition", type=str, default="dev")

    parser.add_argument("--metric", type=str, default="f1")
    parser.add_argument("--positive-label", type=str, default=None)
    parser.add_argument("--label-column", type=str, default="label")
    parser.add_argument("--id-column", type=str, default="id")
    parser.add_argument(
        "--field-metrics",
        type=Path,
        default=None,
        help="JSON map {field: {metric, kwargs}}; enables K>1 multi-field scoring.",
    )
    parser.add_argument(
        "--aggregate",
        type=Path,
        default=None,
        help='JSON {"strategy": macro|weighted|min, "weights": {...}} for K>1.',
    )
    parser.add_argument(
        "--floors",
        type=Path,
        default=None,
        help="JSON map {field: floor_value} of per-field floors for K>1.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        if args.row_ids:
            row_ids = [s.strip() for s in args.row_ids.split(",") if s.strip()]
        else:
            partitions = [s.strip() for s in args.partition.split(",") if s.strip()]
            row_ids = _row_ids_from_splits(args.row_ids_from, partitions)

        if args.field_metrics is not None:
            field_metrics = json.loads(args.field_metrics.read_text(encoding="utf-8"))
            aggregate = (
                json.loads(args.aggregate.read_text(encoding="utf-8"))
                if args.aggregate is not None
                else None
            )
            floors = (
                json.loads(args.floors.read_text(encoding="utf-8"))
                if args.floors is not None
                else None
            )
            compute_eval_multifield(
                results_path=args.results,
                baseline_path=args.baseline,
                row_ids=row_ids,
                field_metrics=field_metrics,
                out_path=args.out,
                aggregate=aggregate,
                floors=floors,
                id_column=args.id_column,
            )
        else:
            kwargs: dict[str, Any] = {}
            if args.positive_label:
                kwargs["positive_label"] = args.positive_label
            compute_eval(
                results_path=args.results,
                baseline_path=args.baseline,
                row_ids=row_ids,
                metric=args.metric,
                metric_kwargs=kwargs,
                out_path=args.out,
                label_column=args.label_column,
                id_column=args.id_column,
            )
    except EvalError as e:
        log.error("eval failed: %s", e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
