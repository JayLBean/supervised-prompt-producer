"""Pydantic models for the JSON artifacts the scripts produce.

Schemas are operationalizations of the prose in /spp-baseline.md §4
step 9 (splits) and /spp-loop.md §4 steps 6-7 (results, eval). Schema
drift between these models and the docs is a methodology-affecting
event; surface in a PR description rather than silently amending.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------- splits.json ----------------------------------------------------


class SplitsRowIds(BaseModel):
    train: list[str]
    dev: list[str]
    test: list[str]


class SplitsJSON(BaseModel):
    schema_version: str = "1"
    stratification_key: str
    seed: int
    ratios: dict[str, float]
    row_ids: SplitsRowIds


# ---------- results.json ---------------------------------------------------


class PredictionRow(BaseModel):
    row_id: str
    raw_response: str
    parsed_label: str | None
    parse_error: str | None
    latency_ms: int
    tokens_used: int | None


class ResultsSummary(BaseModel):
    n_rows: int
    n_parsed: int
    n_parse_failures: int
    total_tokens: int
    total_latency_ms: int
    wall_clock_ms: int


class ResultsJSON(BaseModel):
    schema_version: str = "1"
    model: str
    prompt_path: str
    prompt_sha256: str
    predictions: list[PredictionRow]
    summary: ResultsSummary


# ---------- eval.json ------------------------------------------------------


class PerClassMetrics(BaseModel):
    precision: float
    recall: float
    f1: float
    support: int


class PerRowScore(BaseModel):
    """One row's scoring outcome, retained for the v0.3 finalize statistics.

    The per-row ``(y_true, y_pred)`` vector is what ``/spp-finalize``'s
    bootstrap CI (``DESIGN.md`` §7.1.4) resamples; ``correct`` is the
    convenience flag for accuracy-style aggregation.
    Carried inside ``eval.json``, which is already withheld from the auditor
    and rule-edit stages, so retaining it changes no per-stage isolation
    allow-list.
    """

    row_id: str
    y_true: str
    y_pred: str
    correct: bool


class BootstrapCI(BaseModel):
    """Percentile bootstrap CI on a bootstrapped scalar.

    Holds either the interval on one sample's aggregate metric
    (``aggregate_ci``; ``point_estimate`` is that aggregate) or on the dev−test
    gap (``dev_test_gap_ci``; ``point_estimate`` is ``dev_aggregate -
    test_aggregate``, ``n_rows`` the test-partition size).

    Computed only at ``/spp-finalize`` (``DESIGN.md`` §7.1.4) by resampling the
    per-row score vectors already in the eval files — an in-memory resample
    over already-read score arrays, never a second read of the sacred test set.
    ``/spp-finalize`` scores one prompt on the test set, so the aggregate CI is
    a single-sample interval, not a two-prompt comparison. Descriptive only:
    surfaced to the human in ``REPORT.md`` §2, it never gates the loop or
    weights a verdict (invariant #14).
    """

    metric: str
    point_estimate: float
    ci_low: float
    ci_high: float
    confidence: float
    n_resamples: int
    seed: int
    n_rows: int


class EvalJSON(BaseModel):
    schema_version: str = "1"
    metric: str
    metric_kwargs: dict[str, Any] = Field(default_factory=dict)
    primary_value: float
    n_rows_evaluated: int
    n_parse_failures_in_input: int
    confusion_matrix: list[list[int]]
    labels: list[str]
    per_class: dict[str, PerClassMetrics]
    per_row: list[PerRowScore] = Field(default_factory=list)
    aggregate_ci: BootstrapCI | None = None
    dev_test_gap_ci: BootstrapCI | None = None
    auxiliary_metrics: dict[str, Any] = Field(default_factory=dict)
