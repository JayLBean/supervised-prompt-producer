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
from ._schemas import EvalJSON, PerClassMetrics

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
    y_pred: list[str | None] = []
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

    # Compute primary metric.
    binary = len(label_space) == 2
    positive_label = metric_kwargs.get("positive_label")

    if metric == "accuracy":
        primary = float(accuracy_score(y_true, y_pred))
    elif metric == "f1":
        if binary:
            if positive_label is None:
                raise EvalError("binary f1 requires metric_kwargs['positive_label']")
            primary = float(
                f1_score(y_true, y_pred, pos_label=positive_label, zero_division=0)
            )
        else:
            primary = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    elif metric == "precision":
        if binary:
            if positive_label is None:
                raise EvalError(
                    "binary precision requires metric_kwargs['positive_label']"
                )
            primary = float(
                precision_score(
                    y_true, y_pred, pos_label=positive_label, zero_division=0
                )
            )
        else:
            primary = float(
                precision_score(y_true, y_pred, average="macro", zero_division=0)
            )
    elif metric == "recall":
        if binary:
            if positive_label is None:
                raise EvalError(
                    "binary recall requires metric_kwargs['positive_label']"
                )
            primary = float(
                recall_score(y_true, y_pred, pos_label=positive_label, zero_division=0)
            )
        else:
            primary = float(
                recall_score(y_true, y_pred, average="macro", zero_division=0)
            )
    else:  # pragma: no cover - guarded above
        raise EvalError(f"unreachable: metric {metric}")

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

    eval_json = EvalJSON(
        metric=metric,
        metric_kwargs=metric_kwargs,
        primary_value=primary,
        n_rows_evaluated=len(row_ids),
        n_parse_failures_in_input=n_parse_failures,
        confusion_matrix=cm,
        labels=cm_labels,
        per_class=per_class,
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
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        if args.row_ids:
            row_ids = [s.strip() for s in args.row_ids.split(",") if s.strip()]
        else:
            partitions = [s.strip() for s in args.partition.split(",") if s.strip()]
            row_ids = _row_ids_from_splits(args.row_ids_from, partitions)

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
