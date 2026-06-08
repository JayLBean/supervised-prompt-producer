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
numeric stack. Extraction metrics (DESIGN §7.1.11 — ``extraction_f1`` /
``extraction_precision`` / ``extraction_recall`` / ``span_f1`` / ``leakage``)
score a row's variable-cardinality item set by greedy alignment and average
per-row, pure-function over (prediction, gold) with no model in the scoring
path (invariant #13). No new dependency.

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
# Extraction metrics (DESIGN §7.1.11) score a row's variable-cardinality item
# set against gold by greedy one-to-one alignment, then average per-row F1/P/R
# across rows — the same per-row-mean convention the multi-select metrics use.
_EXTRACTION = {
    "extraction_f1",
    "extraction_precision",
    "extraction_recall",
    "span_f1",
    "leakage",
}
# Span metrics align by character-offset overlap and require start/end on gold
# items; the others align by normalized text.
SPAN_METRICS = frozenset({"span_f1"})
_PER_ROW_MEAN = {
    "exact_match",
    "set_f1",
    "set_jaccard",
    "iou",
    "within_tolerance",
} | _EXTRACTION
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
EXTRACTION_METRICS = frozenset(_EXTRACTION)

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


# ---------------------------------------------------------------------------
# Extraction metrics (DESIGN §7.1.11)
#
# An extraction field's value is a variable-cardinality set of items, each a
# bare string (text-only span) or an object with ``text`` and optional
# ``type`` / ``start`` / ``end``. The metric aligns predicted items to gold
# items one-to-one (greedy), counts the matches as true positives, and reports
# per-row precision / recall / F1. All functions are pure (prediction, gold) →
# float; no model runs in the scoring path (invariant #13).
# ---------------------------------------------------------------------------


def _as_items(value: Any) -> list[dict[str, Any]]:
    """Parse a row's extraction value into a list of normalized item dicts.

    Accepts a real list, a JSON-array string (``inference.py`` emits arrays as
    compact JSON), or ``None``. Each element is either a string (text-only
    span) or an object with a ``text`` field and optional ``type`` / ``start``
    / ``end``. Returns dicts with a normalized ``text``, a normalized ``type``
    when present, and integer ``start`` / ``end`` when both parse as integers.
    """
    raw: Iterable[Any]
    if value is None:
        raw = []
    elif isinstance(value, list):
        raw = value
    elif isinstance(value, str):
        s = value.strip()
        if not s:
            raw = []
        else:
            try:
                parsed = json.loads(s)
                raw = parsed if isinstance(parsed, list) else [parsed]
            except json.JSONDecodeError:
                raw = [s]
    else:
        raw = [value]
    items: list[dict[str, Any]] = []
    for el in raw:
        if isinstance(el, dict):
            item: dict[str, Any] = {"text": _norm(el.get("text", ""))}
            if el.get("type") is not None:
                item["type"] = _norm(el["type"])
            start, end = el.get("start"), el.get("end")
            if start is not None and end is not None:
                try:
                    item["start"] = int(start)
                    item["end"] = int(end)
                except (TypeError, ValueError):
                    pass
            items.append(item)
        else:
            items.append({"text": _norm(el)})
    return items


def _span_iou(g: dict[str, Any], p: dict[str, Any]) -> float:
    inter = max(0, min(g["end"], p["end"]) - max(g["start"], p["start"]))
    union = (g["end"] - g["start"]) + (p["end"] - p["start"]) - inter
    return inter / union if union > 0 else 0.0


def _types_ok(g: dict[str, Any], p: dict[str, Any], match_type: bool) -> bool:
    """Type agreement: only constrained when match_type and gold carries a type.

    A gold item with a ``type`` requires the predicted item to carry the same
    type; a gold item with no type does not constrain the prediction's type.
    """
    if not match_type or "type" not in g:
        return True
    return g.get("type") == p.get("type")


def _text_match(g: dict[str, Any], p: dict[str, Any], match_type: bool) -> bool:
    return g["text"] == p["text"] and _types_ok(g, p, match_type)


def _span_match(
    g: dict[str, Any], p: dict[str, Any], match_type: bool, iou_threshold: float
) -> bool:
    if "start" not in g or "start" not in p:
        return False
    return _span_iou(g, p) >= iou_threshold and _types_ok(g, p, match_type)


def _align_count(
    gold_items: list[dict[str, Any]],
    pred_items: list[dict[str, Any]],
    match: Any,
) -> int:
    """Greedy one-to-one alignment: count predicted items that match a unique gold item."""
    used = [False] * len(gold_items)
    tp = 0
    for p in pred_items:
        for i, g in enumerate(gold_items):
            if used[i]:
                continue
            if match(g, p):
                used[i] = True
                tp += 1
                break
    return tp


def _prf(tp: int, n_gold: int, n_pred: int) -> tuple[float, float, float]:
    """Precision / recall / F1 from a true-positive count; empty-both = (1, 1, 1)."""
    if n_gold == 0 and n_pred == 0:
        return 1.0, 1.0, 1.0
    precision = tp / n_pred if n_pred else 0.0
    recall = tp / n_gold if n_gold else 0.0
    denom = n_gold + n_pred
    f1 = 2 * tp / denom if denom else 0.0
    return precision, recall, f1


def extraction_prf(
    gold: Any, pred: Any, match_type: bool = True
) -> tuple[float, float, float]:
    """Per-row (precision, recall, F1) by text alignment; empty-both = (1, 1, 1).

    Items align on normalized ``text`` (and ``type`` when ``match_type`` and the
    gold item carries one). Offset-agnostic — the workhorse for entity/phrase
    extraction without reliable character spans.
    """
    g = _as_items(gold)
    p = _as_items(pred)
    tp = _align_count(g, p, lambda a, b: _text_match(a, b, match_type))
    return _prf(tp, len(g), len(p))


def extraction_f1(gold: Any, pred: Any, match_type: bool = True) -> float:
    """Per-row text-alignment F1 (extraction)."""
    return extraction_prf(gold, pred, match_type)[2]


def extraction_precision(gold: Any, pred: Any, match_type: bool = True) -> float:
    """Per-row text-alignment precision (extraction)."""
    return extraction_prf(gold, pred, match_type)[0]


def extraction_recall(gold: Any, pred: Any, match_type: bool = True) -> float:
    """Per-row text-alignment recall (extraction)."""
    return extraction_prf(gold, pred, match_type)[1]


def span_f1(
    gold: Any, pred: Any, match_type: bool = True, iou_threshold: float = 0.5
) -> float:
    """Per-row F1 by character-offset overlap; empty-both = 1.0 (span/NER).

    A predicted item matches a gold item when their spans overlap with
    Intersection-over-Union at or above ``iou_threshold`` (and types agree when
    ``match_type`` and the gold item carries a type). Gold items must carry
    integer ``start`` / ``end`` offsets — a span metric on offset-less gold is a
    configuration error (raises ``MetricError``).
    """
    g = _as_items(gold)
    for it in g:
        if "start" not in it:
            raise MetricError(
                "span_f1 requires character offsets (start/end) on gold items; "
                "use extraction_f1 for offset-less extraction"
            )
    p = _as_items(pred)
    tp = _align_count(g, p, lambda a, b: _span_match(a, b, match_type, iou_threshold))
    return _prf(tp, len(g), len(p))[2]


def leakage(gold: Any, pred: Any) -> float:
    """1 − fraction of forbidden gold items surviving as substrings of pred text.

    The deterministic redaction metric (the spp-ex Module 1 pattern): ``gold``
    is the set of forbidden tokens (e.g. PII units), ``pred`` is the rewritten
    output text. Higher is better (1.0 = nothing leaked); no forbidden tokens =
    1.0. Case-folded substring containment, so it is a pure function of
    (prediction, gold).
    """
    forbidden = [it["text"] for it in _as_items(gold) if it["text"]]
    if not forbidden:
        return 1.0
    text = _norm(pred)
    survived = sum(1 for t in forbidden if t in text)
    return 1.0 - survived / len(forbidden)


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

    if metric in _EXTRACTION:
        match_type = bool(metric_kwargs.get("match_type", True))
        if metric == "extraction_f1":
            return _mean_per_row(extraction_f1, y_true, y_pred, match_type)
        if metric == "extraction_precision":
            return _mean_per_row(extraction_precision, y_true, y_pred, match_type)
        if metric == "extraction_recall":
            return _mean_per_row(extraction_recall, y_true, y_pred, match_type)
        if metric == "span_f1":
            tau = float(metric_kwargs.get("iou_threshold", 0.5))
            return _mean_per_row(span_f1, y_true, y_pred, match_type, tau)
        return _mean_per_row(leakage, y_true, y_pred)  # leakage

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
