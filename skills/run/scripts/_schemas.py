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
    # v0.6 (DESIGN.md §7.1.7): True when the split was additionally
    # stratified by the per-row `language` column (multilingual data with
    # >=2 distinct languages). Additive and backward-compatible — absent in
    # pre-v0.6 files, where it reads as the default False.
    language_stratified: bool = False
    row_ids: SplitsRowIds


# ---------- results.json ---------------------------------------------------


class PredictionRow(BaseModel):
    row_id: str
    raw_response: str
    parsed_label: str | None
    parse_error: str | None
    # Multi-field (K>1) parse outputs (DESIGN.md §7.1.5). For K=1 these stay
    # None/empty and parsed_label/parse_error carry the single-field result.
    # For K>1, parsed_fields holds one raw string value per OUTPUT_SCHEMA field
    # (scalars stringified, arrays/objects JSON-encoded) or None when absent,
    # and field_parse_errors records per-field extraction failures. eval.py
    # canonicalizes and scores; inference does minimal parsing only.
    parsed_fields: dict[str, str | None] | None = None
    field_parse_errors: dict[str, str] = Field(default_factory=dict)
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


class FieldEval(BaseModel):
    """One OUTPUT_SCHEMA field's evaluation under K>1 (DESIGN.md §7.1.5).

    ``primary_value`` is the field's ``METRIC_NAME`` computed over its column by
    ``_metrics.compute_field_metric``. The cross-field aggregate and the
    ``floor_compliance`` section are added in later v0.4 buckets; this layer
    emits the ``per_field`` breakdown only.
    """

    metric: str
    primary_value: float
    n_rows: int
    n_parse_failures: int = 0


class Aggregate(BaseModel):
    """The cross-field aggregate of a K>1 run (metric-design §3.2; DESIGN §7.1.5).

    ``strategy`` is ``macro`` (unweighted mean), ``weighted`` (weighted mean), or
    ``min`` (worst field / bottleneck). ``value`` is the aggregate the loop's
    stop-discipline reads. ``weights`` is present only for ``weighted``.
    """

    strategy: str
    value: float
    weights: dict[str, float] | None = None


class FloorCompliance(BaseModel):
    """One field's floor check (metric-design §3.3; DESIGN §7.1.5).

    ``floor`` is the field's minimum acceptable primary-metric value (``None``
    if unspecified). ``status`` is ``met`` / ``unmet`` / ``not_specified``. An
    ``unmet`` floor while the aggregate sits at-or-above target is what drives
    the loop's ``EARLY_STOP_FLOOR_UNMET`` branch — the loop reads this section;
    ``eval.py`` only emits it.
    """

    floor: float | None = None
    status: str


class LanguageEval(BaseModel):
    """One language's metric slice (v0.6, DESIGN.md §7.1.7).

    A descriptive per-language breakdown — the same kind of slice as
    ``per_class`` — of the field's chosen metric computed over the rows
    tagged with this language. For K=1 ``primary_value`` is the top-level
    metric on this language's rows; for K>1 it is the cross-field aggregate
    and ``per_field`` carries each field's metric on this language's rows.
    Emitted only for multilingual data (the ``language`` column present with
    >=2 distinct values among the evaluated rows); empty otherwise.

    It reuses the field's existing mechanical metric — no new metric family,
    no LLM judge (invariant #13 intact) — and is carried inside
    ``eval.json``, already withheld from the auditor and rule-edit stages,
    so it changes no per-stage isolation allow-list.
    """

    primary_value: float
    n_rows: int
    n_parse_failures: int = 0
    per_field: dict[str, float] = Field(default_factory=dict)


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
    # K>1 multi-field breakdown (DESIGN.md §7.1.5). None for K=1 (the top-level
    # fields above carry the single-field result); populated for multi-field
    # runs, where the top-level `metric` is "multi_field" and `primary_value` is
    # a provisional unweighted mean until the aggregate bucket formalizes it.
    per_field: dict[str, FieldEval] | None = None
    aggregate: Aggregate | None = None
    floor_compliance: dict[str, FloorCompliance] | None = None
    per_row: list[PerRowScore] = Field(default_factory=list)
    # Per-language breakdown (v0.6, DESIGN.md §7.1.7). Empty for monolingual
    # data; populated only when the baseline carries a `language` column with
    # >=2 distinct values among the evaluated rows. Additive and
    # backward-compatible — absent in pre-v0.6 files, where it reads as {}.
    per_language: dict[str, LanguageEval] = Field(default_factory=dict)
    aggregate_ci: BootstrapCI | None = None
    dev_test_gap_ci: BootstrapCI | None = None
    auxiliary_metrics: dict[str, Any] = Field(default_factory=dict)


# ---------- label_panel.json -----------------------------------------------


class LabelVote(BaseModel):
    """One judge's vote on one row (v0.7, DESIGN.md §7.1.8).

    A single score-blind judge returns exactly one ``label`` from the fixed
    ``OUTPUT_SCHEMA`` output space plus a brief ``rationale``. ``judge_id`` is
    a stable index within the panel (``"judge_1"`` .. ``"judge_5"``) for the
    audit trail; it carries no model identity beyond the panel's single
    (cross-family) judge family recorded at the top level. Votes are cast
    independently — no judge's input contains another judge's vote — so the
    per-row tally measures genuine agreement.
    """

    judge_id: str
    label: str
    rationale: str


class LabelPanelRow(BaseModel):
    """One row's panel outcome (v0.7, DESIGN.md §7.1.8).

    ``vote_counts`` (label -> number of judges) is the source of truth;
    ``n_agree`` is the plurality count and ``winning_label`` the plurality
    label. ``final_label`` is the frozen gold value: equal to
    ``winning_label`` for an auto-accepted row, the human's choice for an
    escalated split, or the human's override otherwise; ``None`` until an
    escalated row is resolved.

    ``disposition`` is one of:

    - ``auto_accepted`` — >=``consensus_threshold`` judges agreed; frozen
      without human sign-off.
    - ``escalated`` — the panel split below threshold; awaiting human
      adjudication (``final_label`` is ``None``).
    - ``human_resolved`` — an escalated split the human adjudicated.
    - ``human_overridden`` — a frozen label the human later changed via the
      audit trail (authority as override-plus-visibility, §7.1.8).

    ``language`` carries the row's tag when the data is multilingual
    (§7.1.7), so a low-resource language's elevated escalation rate is
    visible in the trail; ``None`` for monolingual data.
    """

    row_id: str
    language: str | None = None
    votes: list[LabelVote]
    vote_counts: dict[str, int]
    n_agree: int
    winning_label: str | None
    disposition: str
    final_label: str | None = None


class LabelPanelSummary(BaseModel):
    """Aggregate dispositions across the panel run (v0.7, DESIGN.md §7.1.8).

    ``per_language_escalation`` (language -> escalated count) is the
    disclosed-limitation surface: a language whose rows escalate
    disproportionately is the judge-language-coupling signal the human reads,
    not a silent weakness. Empty for monolingual data.
    """

    n_rows: int
    n_auto_accepted: int
    n_escalated: int
    n_human_resolved: int
    n_human_overridden: int
    per_language_escalation: dict[str, int] = Field(default_factory=dict)


class LabelPanelJSON(BaseModel):
    """The label-panel audit trail (v0.7, DESIGN.md §7.1.8).

    Written by the ``label-panel`` sub-skill when it synthesizes labels for a
    dataset whose canonical ``label`` column is absent. It records the
    cross-family gate decision (``production_family`` vs ``judge_family`` — the
    gate passes only when they differ), the panel configuration, and every
    row's votes and disposition.

    This artifact is created **before any split exists** and feeds **no**
    scoring path: ``eval.py`` never reads it. The labels it freezes are read
    downstream by the same mechanical metric as any other baseline, so the
    panel creates ground truth without ever judging a prompt (invariant #13;
    ``metric-design`` §5).
    """

    schema_version: str = "1"
    production_model: str
    production_family: str
    judge_family: str = "anthropic"
    panel_size: int
    consensus_threshold: int
    label_space: list[str]
    rows: list[LabelPanelRow]
    summary: LabelPanelSummary
