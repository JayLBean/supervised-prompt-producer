# spp plan — feature-group-split-topic

**Created:** 2026-05-14

**Designer session:** placeholder-designer-session

**Plan version:** v1

---

## 1. Task overview

**One-sentence description:** Categorize each customer-feedback
excerpt's topic — product, service, billing, or other — so it can
be routed to the correct team's queue.

**Audience for the prompt's output:** the feedback-routing service
that dispatches incoming feedback to product / customer-support /
billing teams.

**Problem statement** (placeholder; this sub-task is a skeleton
per DESIGN.md §7.2):
Routing currently relies on a keyword rule that mis-routes hybrid
feedback (e.g., "billing portal is slow" — product complaint about
the billing UI vs. billing-team concern). Migrating routing to a
prompt removes the keyword-rule maintenance burden and gives a
defensible per-feedback routing decision.

This sub-task is one of three under the `feature-group-split`
parent example; see [`../../README.md`](../../README.md) for the
decomposition rationale (DESIGN.md §10 glossary "Feature-group
prompt splitting").

---

## 2. Output schema and per-field definitions

**Output schema** (K=1):

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "FeedbackTopic"
type: "object"
additionalProperties: false
required: ["topic"]
properties:
  topic:
    type: "string"
    enum: ["product", "service", "billing", "other"]
    description: "Top-level content category; routes to the correct team."
examples:
  - topic: "product"
```

**Per-field definitions** (one sub-block; K=1):

- **`topic`:** what the feedback is *about*, not how the customer
  feels about it. Read for content signals — product names, feature
  references, support-interaction language, billing terminology.
  - Positive examples: feedback mentioning a feature →
    `product`; feedback about a support agent's handling →
    `service`; invoice questions → `billing`; thank-you notes
    that don't name a product or service → `other`.
  - Borderline examples: hybrid mentions where two topics could
    apply (e.g., "the billing portal is slow"); rule: route by
    the **primary content concern** — UI/UX issues are
    `product` even when the UI happens to be the billing
    portal; team-handling issues are `service` regardless of
    subject.
  - Edge cases: meta-feedback about the company itself, vendor
    pitches, or questions about policy → `other`.

**Known borderline cases:**
"Billing portal" hybrid (product UI vs. billing concern) is the
dominant known borderline class. Flagged for `baseline-quality`
calibration.

---

## 3. Success criteria

**Production decision rule:**
The routing service dispatches the feedback to the team named by
`topic`. Misroutes trigger a manual re-route via the receiving
team's "wrong team" flag, but the latency is the cost the
customer pays.

**Headline success criterion:**
`aggregate (macro) ≥ 0.85` on dev. Under K=1 this equals
`topic`'s `macro_F1` directly.

**Acceptable trade-offs:**
A slight under-prediction of `other` is acceptable in exchange for
high precision on the three named teams — misroutes between
teams are costlier than absorbing some `other` feedback into the
nearest team queue.

---

## 4. Per-field metrics, aggregate strategy, and floors

**Aggregate strategy:**

- **`AGGREGATE_STRATEGY`:** `macro`
- **`AGGREGATE_WEIGHTS`:** `null`
- **`AGGREGATE_RATIONALE`:** K=1 trivially. Per `metric-design`
  SKILL.md §3.2's K=1 collapse.

**Per-field metrics** (one sub-block; K=1):

- **Field `topic`:**
  - `METRIC_NAME`: `macro_F1`
  - `METRIC_RATIONALE`: `topic` is an `enum` with 4 values;
    `metric-design` §3.1 routes multi-class enums to `macro_F1`
    because per-class recall matters — the team-leads care that
    each team's feedback class is routed accurately, not just the
    aggregate accuracy.
  - `METRIC_INDEPENDENCE_NOTE`: `macro_F1` against ground-truth
    `topic` labels — model-agnostic.

**Per-field floors:**

- **Field `topic`:**
  - `FLOOR`: `0.85` (on `macro_F1`)
  - `FLOOR_RATIONALE`: routing accuracy is the unrecoverable
    decision; once feedback lands in a team's queue, the team's
    process doesn't include systematic re-routing. The 0.85
    floor reflects the team-leads' stated bar.

---

## 5. Model and lock-in posture

**Production model identifier:** `placeholder-model-v1`

**Production model family:** auto

**Lock-in posture:** locked

**Cross-model fragility plan:** placeholder.

---

## 6. Baseline

**Data source:** placeholder; see [`../../README.md`](../../README.md).

**Language coverage:** monolingual

**Preprocess mapping:** identity (data already canonical)

**Target baseline size:** 80 rows

**Class balance target:** preserve production prevalence (~45%
product, 25% service, 20% billing, 10% other).

**Label provenance:** single labeler from the support-operations
team with documented criteria.

**Label synthesis:** none (labels human-provided or already present)

**Status:** complete (placeholder).

**baseline-quality review:** placeholder; K=1 per-field calibration
runs once on the lone `topic` field.

---

## 7. Splits

**Split ratios:** train 60% / dev 20% / test 20%

**Random seed:** 42

**Stratification key:** `topic`

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

The "billing portal" hybrid (product UI vs. billing concern) is
the dominant known borderline. Flagged for `baseline-quality`
calibration.

---

## 11. Plan revision log

| Date | Plan version | Reason | By |
|---|---|---|---|
| 2026-05-14 | v1 | Initial plan via /spp-init | placeholder-designer-session |
