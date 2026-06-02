"""Per-field metric primitives for the K>1 multi-field runner (DESIGN §7.1.5).

These implement the canonical metric set (``metric-design`` SKILL.md §3.1) that
the per-field scorer dispatches over. The per-row primitives — ``exact_match``,
``set_jaccard`` / ``iou``, ``set_f1``, ``within_tolerance`` — mirror the scoring
used by spp's genuine multi-field annotation runs: normalized (stripped,
Unicode case-folded, NFC) comparison, empty-both = 1.0 ("both say nothing"),
and optional
accepted-alternative partial credit for multi-select fields. Corpus metrics
(``f1`` / ``macro_f1`` / ``balanced_accuracy`` / ``precision`` / ``recall`` /
``mae`` / ``rmse``) are computed over the field's full column via the existing
numeric stack. No new dependency.

This module is the single source of per-field metric computation; ``eval.py``
delegates to it in the per-field scoring wiring (the next bucket).
"""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Iterable
from typing import Any

from sklearn.metrics import (
    balanced_accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
)


class MetricError(RuntimeError):
    """Unsupported metric or malformed metric inputs; message is user-facing."""


# Per-field metric names (metric-design §3.1), grouped by computation kind.
_PER_ROW_MEAN = {"exact_match", "set_f1", "set_jaccard", "iou", "within_tolerance"}
_CORPUS_CLASS = {
    "f1",
    "accuracy",
    "precision",
    "recall",
    "macro_f1",
    "balanced_accuracy",
}
_CORPUS_NUMERIC = {"mae", "rmse"}
SUPPORTED_FIELD_METRICS = _PER_ROW_MEAN | _CORPUS_CLASS | _CORPUS_NUMERIC

# Error-family metrics are unbounded and lower-is-better; they cannot be
# averaged into a [0,1]-higher-better cross-field aggregate (DESIGN §7.1.5
# dimensional-nonsense refusal). eval.py refuses such a mix upstream.
ERROR_METRICS = frozenset(_CORPUS_NUMERIC)
AGGREGATE_STRATEGIES = frozenset({"macro", "weighted", "min"})


def _norm(s: Any) -> str:
    """Canonicalize a scalar to a normalized string for comparison.

    Stringify, strip, Unicode case-fold, then NFC-normalize (DESIGN.md
    §7.1.7). Case-folding plus NFC means visually identical text compares
    equal regardless of composed/decomposed accents (``café`` written two
    ways) or non-ASCII case (German ``ß`` ↔ ``SS``, Turkish ``İ`` ↔ ``i``) —
    so a correct prediction is never scored wrong on an invisible encoding
    difference. On ASCII this is identical to the previous
    strip-and-lowercase, so K=1 and monolingual scoring are unchanged for
    ASCII data. NFC is applied after case-folding because case-folding can
    itself denormalize.
    """
    return unicodedata.normalize("NFC", str(s).strip().casefold())


def _as_set(value: Any, accepted: dict[str, str] | None = None) -> set[str]:
    """Normalize a multi-select value (list or JSON-encoded list) to a string set.

    inference.py emits arrays as compact JSON strings; gold columns may be a
    real list or a JSON string. ``accepted`` maps a predicted value onto the
    gold value it is a documented alternative for (partial credit).
    """
    items: Iterable[Any]
    if value is None:
        items = []
    elif isinstance(value, list):
        items = value
    elif isinstance(value, str):
        s = value.strip()
        if not s:
            items = []
        else:
            try:
                parsed = json.loads(s)
                items = parsed if isinstance(parsed, list) else [parsed]
            except json.JSONDecodeError:
                items = [s]
    else:
        items = [value]
    out = {_norm(x) for x in items}
    if accepted:
        out = {accepted.get(x, x) for x in out}
    return out


def exact_match(gold: Any, pred: Any) -> float:
    """1.0 if normalized scalars match, else 0.0 (single_select / enum / boolean)."""
    return 1.0 if _norm(gold) == _norm(pred) else 0.0


def set_jaccard(gold: Any, pred: Any, accepted: dict[str, str] | None = None) -> float:
    """|g ∩ p| / |g ∪ p| over normalized sets; empty-both = 1.0 (multi-select / IoU)."""
    g = _as_set(gold)
    p = _as_set(pred, accepted)
    if not g and not p:
        return 1.0
    if not g or not p:
        return 0.0
    return len(g & p) / len(g | p)


def set_f1(gold: Any, pred: Any, accepted: dict[str, str] | None = None) -> float:
    """Set-level F1: 2|g ∩ p| / (|g| + |p|); empty-both = 1.0 (multi-select)."""
    g = _as_set(gold)
    p = _as_set(pred, accepted)
    if not g and not p:
        return 1.0
    denom = len(g) + len(p)
    if denom == 0:
        return 0.0
    return 2 * len(g & p) / denom


def _to_float(x: Any) -> float | None:
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return None


def within_tolerance(gold: Any, pred: Any, tol: float = 0.0) -> float:
    """1.0 if |gold - pred| <= tol, else 0.0; non-numeric pred = 0.0 (number)."""
    g = _to_float(gold)
    p = _to_float(pred)
    if g is None or p is None:
        return 0.0
    return 1.0 if abs(g - p) <= tol else 0.0


def _mean_per_row(fn: Any, y_true: list[Any], y_pred: list[Any], *args: Any) -> float:
    pairs = zip(y_true, y_pred, strict=True)
    return sum(fn(g, p, *args) for g, p in pairs) / len(y_true)


def compute_field_metric(
    metric: str,
    y_true: list[Any],
    y_pred: list[Any],
    metric_kwargs: dict[str, Any] | None = None,
) -> float:
    """Compute one field's primary metric over its full column (DESIGN §7.1.5).

    ``metric`` is the field's ``METRIC_NAME`` (``metric-design`` §3.1). Per-row
    metrics return the mean per-row score; corpus metrics are computed over the
    normalized column. Numeric metrics (``mae`` / ``rmse``) are taken over the
    rows whose gold and prediction both parse as numbers; rows that do not parse
    are surfaced separately as parse failures by the caller, not silently scored.
    """
    metric_kwargs = metric_kwargs or {}
    if metric not in SUPPORTED_FIELD_METRICS:
        raise MetricError(
            f"field metric '{metric}' not supported; supported: "
            f"{sorted(SUPPORTED_FIELD_METRICS)}"
        )
    if len(y_true) != len(y_pred):
        raise MetricError("y_true and y_pred must be the same length")
    if not y_true:
        raise MetricError("no rows to score")

    accepted = metric_kwargs.get("accepted")
    if metric == "exact_match":
        return _mean_per_row(exact_match, y_true, y_pred)
    if metric == "set_f1":
        return _mean_per_row(set_f1, y_true, y_pred, accepted)
    if metric in ("set_jaccard", "iou"):
        return _mean_per_row(set_jaccard, y_true, y_pred, accepted)
    if metric == "within_tolerance":
        tol = float(metric_kwargs.get("tolerance", 0.0))
        return _mean_per_row(within_tolerance, y_true, y_pred, tol)

    if metric in _CORPUS_CLASS:
        yt = [_norm(x) for x in y_true]
        yp = [_norm(x) for x in y_pred]
        if metric == "accuracy":
            return sum(1.0 for a, b in zip(yt, yp, strict=True) if a == b) / len(yt)
        if metric == "balanced_accuracy":
            return float(balanced_accuracy_score(yt, yp))
        if metric == "macro_f1":
            return float(f1_score(yt, yp, average="macro", zero_division=0))
        pos = metric_kwargs.get("positive_label")
        if pos is None:
            raise MetricError(
                f"binary metric '{metric}' requires metric_kwargs['positive_label']"
            )
        pos = _norm(pos)
        if metric == "f1":
            return float(f1_score(yt, yp, pos_label=pos, zero_division=0))
        if metric == "precision":
            return float(precision_score(yt, yp, pos_label=pos, zero_division=0))
        return float(recall_score(yt, yp, pos_label=pos, zero_division=0))

    # Numeric corpus metrics over numeric-parseable pairs.
    pairs = [(_to_float(g), _to_float(p)) for g, p in zip(y_true, y_pred, strict=True)]
    valid = [(g, p) for g, p in pairs if g is not None and p is not None]
    if not valid:
        raise MetricError(f"metric '{metric}' has no numeric-parseable rows")
    gs = [g for g, _ in valid]
    ps = [p for _, p in valid]
    if metric == "mae":
        return float(mean_absolute_error(gs, ps))
    return float(mean_squared_error(gs, ps) ** 0.5)  # rmse


def compute_aggregate(
    values: dict[str, float],
    strategy: str,
    weights: dict[str, float] | None = None,
) -> float:
    """Roll per-field primary values into one aggregate (metric-design §3.2).

    ``macro`` = unweighted mean; ``min`` = worst field (the bottleneck);
    ``weighted`` = weighted mean (a field's missing weight defaults to 1.0,
    mirroring spp's genuine annotation scorer). Callers must ensure the fields
    share a metric family — averaging a bounded [0,1]-higher-better score with
    an unbounded lower-better error is refused upstream (eval.py), not here.
    """
    if not values:
        raise MetricError("no per-field values to aggregate")
    if strategy not in AGGREGATE_STRATEGIES:
        raise MetricError(
            f"aggregate strategy '{strategy}' not supported; "
            f"supported: {sorted(AGGREGATE_STRATEGIES)}"
        )
    vals = list(values.values())
    if strategy == "macro":
        return sum(vals) / len(vals)
    if strategy == "min":
        return min(vals)
    w = {f: float((weights or {}).get(f, 1.0)) for f in values}
    total = sum(w.values())
    if total == 0:
        raise MetricError("weighted aggregate has zero total weight")
    return sum(values[f] * w[f] for f in values) / total
