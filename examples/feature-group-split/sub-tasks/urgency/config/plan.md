# spp plan — feature-group-split-urgency

**Created:** 2026-05-14

**Designer session:** placeholder-designer-session

**Plan version:** v1

---

## 1. Task overview

**One-sentence description:** Classify each customer-feedback
excerpt's operational urgency — immediate, normal, or low — so
escalation rules can be triggered automatically.

**Audience for the prompt's output:** the escalation engine that
pages on-call staff when high-urgency feedback arrives outside
business hours.

**Problem statement** (placeholder; this sub-task is a skeleton
per DESIGN.md §7.2):
On-call escalation currently relies on a regex matching outage
keywords; the regex misses urgent-but-non-keyword feedback ("we
can't ship orders right now") and over-fires on calm mentions of
outage history ("last week's outage was handled well"). Migrating
urgency classification to a prompt under `spp`'s discipline
removes the regex maintenance burden and gives the on-call team a
defensible per-feedback urgency decision.

This sub-task is one of three under the `feature-group-split`
parent example.

---

## 2. Output schema and per-field definitions

**Output schema** (K=1):

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "FeedbackUrgency"
type: "object"
additionalProperties: false
required: ["urgency"]
properties:
  urgency:
    type: "string"
    enum: ["immediate", "normal", "low"]
    description: "Operational urgency; gates escalation rules."
examples:
  - urgency: "immediate"
```

**Per-field definitions** (one sub-block; K=1):

- **`urgency`:** how quickly the feedback needs operational
  response. Read for severity markers — explicit blockers
  ("can't process orders," "can't log in"), time-pressure cues
  ("before tomorrow," "right now"), customer-impact language,
  and historical-reference framing (which inverts urgency —
  past-tense references are not active blockers).
  - Positive examples: "service has been unavailable for 30
    minutes; we can't process orders" → `immediate`; "could you
    add a dark mode option" → `low`; "invoice line items don't
    match" → `normal`.
  - Borderline examples: complaints with strong tone but no
    actual block (e.g., angry feedback about a minor UI
    annoyance); rule: **operational impact** decides, not
    affect — high-tone-low-impact is `normal` or `low`, not
    `immediate`.
  - Edge cases: feedback referencing past outages without an
    active block ("last week's outage was handled well") →
    `low`; questions framed as urgent that are actually routine
    ("urgent: how do I reset my password") → `normal` unless
    the user is genuinely blocked.

**Known borderline cases:**
High-tone-low-impact feedback (angry tone, minor concrete impact)
is the dominant known borderline. The urgency sub-task is the
clearest demonstration of why splitting from sentiment matters —
the sentiment prompt would correctly label such feedback
`negative`, and the urgency prompt must correctly label it
`normal` rather than `immediate`. Combining the two into one
prompt would invite the rules to conflate affect with urgency.

---

## 3. Success criteria

**Production decision rule:**
Feedback labeled `immediate` triggers an on-call page outside
business hours; `normal` enters the standard queue with a
4-hour SLA; `low` enters the standard queue without SLA.

**Headline success criterion:**
`aggregate (macro) ≥ 0.85` on dev. Under K=1 this equals
`urgency`'s `macro_F1` directly.

**Acceptable trade-offs:**
False-positive `immediate` (page on-call when feedback is
actually `normal`) is costly to the on-call team's morale.
False-negative `immediate` (miss an actual outage signal) is
costlier to customers. The floor below reflects this asymmetry.

---

## 4. Per-field metrics, aggregate strategy, and floors

**Aggregate strategy:**

- **`AGGREGATE_STRATEGY`:** `macro`
- **`AGGREGATE_WEIGHTS`:** `null`
- **`AGGREGATE_RATIONALE`:** K=1 trivially.

**Per-field metrics** (one sub-block; K=1):

- **Field `urgency`:**
  - `METRIC_NAME`: `macro_F1`
  - `METRIC_RATIONALE`: `urgency` is an `enum` with 3 values;
    `metric-design` §3.1 routes multi-class enums to
    `macro_F1`. Per-class recall matters because the
    `immediate` class is operationally load-bearing — its
    recall is what the escalation engine depends on.
  - `METRIC_INDEPENDENCE_NOTE`: `macro_F1` against ground-truth
    `urgency` labels — model-agnostic.

**Per-field floors:**

- **Field `urgency`:**
  - `FLOOR`: `0.90` (on `macro_F1`)
  - `FLOOR_RATIONALE`: the `immediate` class's recall is what
    the escalation engine depends on; false-negative
    `immediate` misses an active outage signal and customers
    pay the cost. The 0.90 floor is tighter than the aggregate
    target (0.85) to reflect this asymmetry. Per-class-within-
    field floors (e.g., `recall_on_immediate ≥ 0.95`) would
    be a tighter expression of the operational concern but
    `metric-design` SKILL.md §3.3 routes per-class floor needs
    through the metric choice itself — if the team wants
    tighter per-class control, the metric becomes
    `recall_on_immediate` rather than `macro_F1`.

---

## 5. Model and lock-in posture

**Production model identifier:** `placeholder-model-v1`

**Lock-in posture:** locked

**Cross-model fragility plan:** placeholder.

---

## 6. Baseline

**Data source:** placeholder.

**Target baseline size:** 80 rows

**Class balance target:** preserve production prevalence (~15%
immediate, 60% normal, 25% low; the baseline oversamples
`immediate` to N≥20 for stable per-class statistics).

**Label provenance:** single labeler from the on-call team.

**Status:** complete (placeholder).

**baseline-quality review:** placeholder; K=1 calibration on
`urgency`. The high-tone-low-impact boundary is the focus of
§3.3 intuition-vs-rule calibration.

---

## 7. Splits

**Split ratios:** train 60% / dev 20% / test 20%

**Random seed:** 42

**Stratification key:** `urgency`

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

The high-tone-low-impact boundary is the dominant known borderline
— and the clearest example of why splitting urgency from
sentiment matters.

---

## 11. Plan revision log

| Date | Plan version | Reason | By |
|---|---|---|---|
| 2026-05-14 | v1 | Initial plan via /spp-init | placeholder-designer-session |
