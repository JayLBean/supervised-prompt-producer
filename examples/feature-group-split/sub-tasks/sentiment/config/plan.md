# spp plan — feature-group-split-sentiment

**Created:** 2026-05-14

**Designer session:** placeholder-designer-session

**Plan version:** v1

---

## 1. Task overview

**One-sentence description:** Classify each customer-feedback
excerpt's affect as positive, negative, or neutral.

**Audience for the prompt's output:** the customer-satisfaction
dashboard that aggregates feedback by week and team.

**Problem statement** (placeholder; this sub-task is a skeleton
per DESIGN.md §7.2):
The dashboard currently relies on a keyword sentiment rule that
mis-labels hedged or sarcastic feedback at a rate the satisfaction
team has flagged. Migrating sentiment classification to a prompt
under `spp`'s discipline removes the keyword-rule maintenance burden
and gives the team a defensible per-week sentiment metric.

This sub-task is one of three under the `feature-group-split`
parent example; see `../../README.md` for the decomposition
rationale (DESIGN.md §10 glossary "Feature-group prompt
splitting").

---

## 2. Output schema and per-field definitions

**Output schema** (JSON Schema draft 2020-12; YAML surface; K=1
for this sub-task):

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "FeedbackSentiment"
type: "object"
additionalProperties: false
required: ["sentiment"]
properties:
  sentiment:
    type: "string"
    enum: ["positive", "negative", "neutral"]
    description: "Affect classification of the feedback excerpt."
examples:
  - sentiment: "positive"
```

**Per-field definitions** (one sub-block; K=1):

- **`sentiment`:** the affect of the feedback excerpt as a whole.
  Read for tone signals — word choice, exclamation density, hedging,
  and emoji where present.
  - Positive examples: explicit praise ("love this"); enthusiastic
    feature requests framed as compliments; thank-you notes.
  - Borderline examples: mixed reviews where the user praises one
    aspect and criticizes another; the rule: **net affect** decides
    — if the overall tone leans positive, label `positive`.
  - Edge cases: feedback with no affect signal (e.g., bare
    factual reports of an event); default to `neutral`.

**Known borderline cases:**
Sarcastic positive-toned text that's actually negative is the
dominant known borderline class. Approximately 5-8% of rows;
flagged for `baseline-quality` calibration.

---

## 3. Success criteria

**Production decision rule** (placeholder):
The dashboard aggregates sentiment counts per week per team and
flags weeks where the negative-share crosses a configurable
threshold for investigation.

**Headline success criterion:**
`aggregate (macro) ≥ 0.85` on dev. Under K=1 the aggregate equals
this sub-task's `sentiment` field's `macro_F1` directly.

**Acceptable trade-offs** (placeholder):
A 5pp drop in `positive` recall is acceptable in exchange for
better `negative` precision — false-negative customer complaints
are costlier than false-positive praise.

---

## 4. Per-field metrics, aggregate strategy, and floors

**Aggregate strategy:**

- **`AGGREGATE_STRATEGY`:** `macro`
- **`AGGREGATE_WEIGHTS`:** `null`
- **`AGGREGATE_RATIONALE`:** K=1 trivially — any aggregate
  strategy is the identity on a single field. `macro` chosen as the
  default. Per `metric-design` SKILL.md §3.2's K=1 collapse.

**Per-field metrics** (one sub-block; K=1):

- **Field `sentiment`:**
  - `METRIC_NAME`: `macro_F1`
  - `METRIC_RATIONALE`: `sentiment` is an `enum` with 3 values;
    `metric-design` §3.1 routes multi-class enums to `macro_F1`.
    Per-class recall matters — the dashboard shouldn't be biased
    by class prevalence at the optimization stage.
  - `METRIC_INDEPENDENCE_NOTE`: `macro_F1` against ground-truth
    `sentiment` labels — model-agnostic.

**Per-field floors:**

(No floor on `sentiment`. The dashboard treats sentiment as a
soft signal aggregated over a week; per-week noise is recoverable
in the aggregate.)

---

## 5. Model and lock-in posture

**Production model identifier:** `placeholder-model-v1`

**Production model family:** auto

**Lock-in posture:** locked

**Cross-model fragility plan:** placeholder.

---

## 6. Baseline

**Data source:** placeholder; see [`../../README.md`](../../README.md)
for the parent example's framing.

**Language coverage:** monolingual

**Preprocess mapping:** identity (data already canonical)

**Target baseline size:** 80 rows

**Class balance target:** preserve production prevalence (~40%
positive, 35% neutral, 25% negative per the satisfaction team's
historical sample).

**Label provenance:** single labeler from the satisfaction team
with documented criteria; criteria are the per-field definition in
§2.

**Label synthesis:** none (labels human-provided or already present)

**Status:** complete (placeholder for this skeleton).

**baseline-quality review:** placeholder; under K=1 the per-field
calibration runs once on the lone `sentiment` field and produces
v0.1.0-equivalent findings.

---

## 7. Splits

**Split ratios:** train 60% / dev 20% / test 20%

**Random seed:** 42

**Stratification key:** `sentiment`

**Sacred test set acknowledgment:** acknowledged

---

## 8. Loop scope and stop criteria

**spp scope:** full

**MAX_ITERATIONS:** 12

**Dev plateau threshold:** `<0.005 aggregate-metric improvement
for 3 consecutive iterations`

**Overfitting early-stop guard:** `train aggregate - dev
aggregate > 0.10 for 2 consecutive iterations`

**Auditor configuration:** `per-iteration, no-score-access`

**Adversary:** off

---

## 9. Decision rules at HITL gates

| Gate | Approval phrase | Notes |
|---|---|---|
| G1 — plan approval | `approved, proceed to baseline` | placeholder |
| G2 — baseline review | `approved` | placeholder |
| G3 — split confirmation | `splits approved` | placeholder |
| G4 — dry-run gate | `dry-run approved, start loop` | placeholder |
| G5 — finalization | `test approved, generate report` | placeholder |
| G6 — production decision | `ship approved` | placeholder |

---

## 10. Open questions / known unknowns

The sarcasm edge case is the dominant known borderline. Flagged for
`baseline-quality` calibration. No other open questions surfaced
during consultation.

---

## 11. Plan revision log

| Date | Plan version | Reason | By |
|---|---|---|---|
| 2026-05-14 | v1 | Initial plan via /spp-init | placeholder-designer-session |
