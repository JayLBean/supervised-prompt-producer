# spp plan — nested-schema-example

**Created:** 2026-05-10

**Designer session:** placeholder-designer-session

**Plan version:** v1

---

## 1. Task overview

**One-sentence description:** Categorize each support-ticket body
into a top-level team-routing label plus a sub-category whose
value space depends on the top-level.

**Audience for the prompt's output:** the support-routing service
that dispatches incoming tickets to the correct team's queue.

**Problem statement** (placeholder; this example is a skeleton per
DESIGN.md §7.2):
The support-routing service currently uses keyword-based rules
for top-level team routing and leaves sub-category as a
post-routing manual step. Keyword routing is brittle to phrasing
changes; manual sub-categorization at the team level adds latency
the team-leads have flagged as a top operational pain point.
Combining both into a single prompt-driven structured extraction
moves the routing decision out of brittle rules and the
sub-categorization off the team's queue.

---

## 2. Output schema and per-field definitions

**Output schema** (per DESIGN.md §7.1.1 schema layer; JSON Schema
draft 2020-12; YAML surface chosen during schema-designer
consultation):

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "SupportTicketCategorization"
type: "object"
additionalProperties: false
required: ["top_level", "sub_category"]
properties:
  top_level:
    type: "string"
    enum: ["billing", "technical", "account", "other"]
    description: "Coarse-grained ticket category; routes to the correct support team."
  sub_category:
    type: "string"
    description: "Sub-category whose value space depends on top_level (see allOf)."
allOf:
  - if:
      properties:
        top_level:
          const: "billing"
      required: ["top_level"]
    then:
      properties:
        sub_category:
          enum: ["invoice_question", "payment_failed", "refund_request"]
  - if:
      properties:
        top_level:
          const: "technical"
      required: ["top_level"]
    then:
      properties:
        sub_category:
          enum: ["login_issue", "feature_bug", "performance_complaint"]
  - if:
      properties:
        top_level:
          const: "account"
      required: ["top_level"]
    then:
      properties:
        sub_category:
          enum: ["password_reset", "profile_update", "subscription_change"]
  - if:
      properties:
        top_level:
          const: "other"
      required: ["top_level"]
    then:
      properties:
        sub_category:
          enum: ["feedback", "uncategorized"]
examples:
  - top_level: "billing"
    sub_category: "invoice_question"
  - top_level: "technical"
    sub_category: "login_issue"
```

**Per-field definitions** (one sub-block per OUTPUT_SCHEMA field;
placeholder examples per DESIGN.md §7.2):

- **`top_level`:** the coarse-grained team-routing category. The
  routing decision is the most operationally costly to get
  wrong — once a ticket lands in a team's queue, the team's
  process doesn't include re-routing.
  - Positive examples: invoice question → `billing`; login
    failure → `technical`; password reset request → `account`;
    "I love your product, just wanted to say thanks" →
    `other`.
  - Borderline examples: tickets that mention multiple concerns
    (e.g., "my password reset email never arrived and now I
    can't log in to dispute the invoice"); the rule: route by
    the **primary blocking concern** — what does the user need
    resolved first?
  - Edge cases: tickets that don't fit any of `billing /
    technical / account` cleanly (product feedback, general
    questions, vendor pitches); route to `other`.
- **`sub_category`:** the team-specific sub-category. The value
  space depends on `top_level`'s value (see the OUTPUT_SCHEMA's
  `allOf` block):
  - For `top_level = billing`: one of `invoice_question`
    (questions about an invoice's contents or charges),
    `payment_failed` (payment attempt failed; user needs help
    completing payment), `refund_request` (user is requesting
    a refund).
  - For `top_level = technical`: one of `login_issue` (user
    cannot authenticate or session-management problems),
    `feature_bug` (a feature does the wrong thing — the
    behavior diverges from documented expectation),
    `performance_complaint` (a feature does the right thing
    but slowly or unreliably).
  - For `top_level = account`: one of `password_reset`
    (explicit password-reset request), `profile_update`
    (changes to profile data — name, email, preferences),
    `subscription_change` (plan upgrade, downgrade, or
    cancellation).
  - For `top_level = other`: one of `feedback` (user is
    sending unsolicited feedback or product praise) or
    `uncategorized` (residual; review in the unrouted-bucket
    weekly).

**Known borderline cases:**
The `feature_bug` vs. `performance_complaint` boundary inside
`technical` is the largest known borderline class. The
distinguishing rule is "wrong thing" vs. "right thing slowly";
flagged for `baseline-quality` calibration. The "primary
blocking concern" rule for multi-concern tickets at the
`top_level` decision is the second known borderline class;
also flagged.

---

## 3. Success criteria

**Production decision rule** (placeholder):
The support-routing service routes the ticket to the team named
by `top_level` and pre-tags it with the `sub_category`.
Misroutes (wrong team) trigger a manual escalation; the team
that received the misrouted ticket flags it back to the
routing service via a one-click "wrong team" button, but the
re-routing latency is the cost the user pays.

**Headline success criterion:**
`aggregate (macro) ≥ 0.85` on dev — the macro mean of
`top_level` and `sub_category` macro_F1.

**Acceptable trade-offs:**
A `sub_category` macro_F1 of 0.78 is acceptable in exchange for
`top_level` macro_F1 ≥ 0.90 (top-level floor). Sub-category
errors are recoverable inside the right team; top-level errors
are not. The team-leads agreed at consultation time that
top-level routing accuracy is the dominant operational
priority.

---

## 4. Per-field metrics, aggregate strategy, and floors

Per DESIGN.md §7.1.1 metrics layer.

**Aggregate strategy:**

- **`AGGREGATE_STRATEGY`:** `macro`
- **`AGGREGATE_WEIGHTS`:** `null`
- **`AGGREGATE_RATIONALE`:** both fields produce values in
  [0, 1] — homogeneous metric types. `metric-design` SKILL.md
  §3.2's strawman recommendation for homogeneous metrics is
  `macro`. The macro mean is `(macro_F1_top_level +
  macro_F1_sub_category) / 2`. Per-field-floor enforcement on
  `top_level` (see below) ensures that even if the aggregate
  passes its target, the loop cannot declare success when the
  unrecoverable field falls short.

**Per-field metrics** (one sub-block per OUTPUT_SCHEMA field):

- **Field `top_level`:**
  - `METRIC_NAME`: `macro_F1`
  - `METRIC_RATIONALE`: `top_level` is an `enum` with 4 values;
    `metric-design` SKILL.md §3.1's decision-tree branch for
    multi-class enums lands on `macro_F1` because per-class
    recall matters — the team-leads care about the worst-
    served class, not the average. The `other` class is
    expected to be small but its routing accuracy still
    matters; macro-averaging gives it equal weight.
  - `METRIC_INDEPENDENCE_NOTE`: `macro_F1` against ground-
    truth `top_level` labels — model-agnostic.
- **Field `sub_category`:**
  - `METRIC_NAME`: `macro_F1`
  - `METRIC_RATIONALE`: `sub_category` is conceptually an
    `enum` with conditional value space. The metric is
    computed over the ground-truth sub-category values
    directly, treating the conditional structure as a
    schema-validation concern rather than a metric concern.
    The decision-tree branch is the same as `top_level`'s;
    macro-averaging is the right shape for the per-team-enum
    case.
  - `METRIC_INDEPENDENCE_NOTE`: `macro_F1` against ground-
    truth `sub_category` labels — model-agnostic.

**Per-field floors** (optional; one sub-block per field that
carries a floor):

- **Field `top_level`:**
  - `FLOOR`: `0.90` (on `macro_F1`)
  - `FLOOR_RATIONALE`: `top_level` routes the ticket to the
    correct team's queue; misroutes are unrecoverable
    without re-running through the routing service (the team
    that received the misrouted ticket flags it back, but
    the re-routing latency is the cost the user pays). The
    0.90 floor reflects the team-leads' stated bar:
    "routing has to be at least as good as the keyword-based
    rules it replaces, which currently land around 0.88
    macro_F1."

(No floor on `sub_category` — sub-category errors are
recoverable inside the right team via the team's
re-categorization workflow.)

---

## 5. Model and lock-in posture

**Production model identifier:** `placeholder-model-v1`

**Lock-in posture:** locked

**Cross-model fragility plan:** the routing service locks to
one model per release; if a swap is required, the team re-runs
`/spp-loop` against the new model and re-finalizes.

---

## 6. Baseline

**Data source:** placeholder — the example does not ship real
data per DESIGN.md §7.2.

**Target baseline size:** 80 rows

**Class balance target:** preserve ticket-queue prevalence per
`top_level` (approximately 35% billing, 30% technical, 25%
account, 10% other; the baseline oversamples `other` to N≥10
for stable per-class statistics).

**Label provenance:** single labeler from the support
operations team with documented criteria; the criteria are
the per-field definitions in §2 above.

**Status:** complete (placeholder for this example).

**baseline-quality review:** placeholder; in a real run this
section would carry the `BASELINE_QUALITY_NOTE` from the
sub-skill's per-field calibration (see [`walkthrough.md`](../walkthrough.md)
`/spp-baseline` section).

---

## 7. Splits

**Split ratios:** train 60% / dev 20% / test 20%

**Random seed:** 42

**Stratification key:** `top_level` (sub-category respects the
conditional structure within each top-level branch).

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

**Adversary:** off (this example focuses on the conditional-
schema shape; adversary is exercised by the hair-loss-
relevance example).

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

The `feature_bug` vs. `performance_complaint` boundary in
`technical` is the dominant known borderline. Resolved in §2's
per-field definition; flagged for `baseline-quality`
calibration. The "primary blocking concern" rule for
multi-concern tickets at `top_level` is the second known
borderline; also flagged.

---

## 11. Plan revision log

| Date | Plan version | Reason | By |
|---|---|---|---|
| 2026-05-10 | v1 | Initial plan via /spp-init | placeholder-designer-session |

---

## Validation rules

A `plan.md` is **correctly filled** when all of the following hold.
The Phase 4 template linter verifies these mechanically; the
designer agent verifies them at gate G1.

1. All `{{...}}` placeholders are resolved.
2. `TASK_NAME` is kebab-case.
3. `OUTPUT_SCHEMA` passes the mechanical layer (per
   `schema-designer` SKILL.md §3.4).
4. `METRIC_NAME[f]` for each OUTPUT_SCHEMA field `f` is one of
   the allowed values listed in `metric-design` SKILL.md §6.
5. `METRIC_INDEPENDENCE_NOTE[f]` is present and non-empty for
   each OUTPUT_SCHEMA field.
6. `MODEL_IDENTIFIER` is the exact env-var string with no
   aliasing.
7. `SACRED_TEST_ACK` literally equals `acknowledged`.
8. `AUDITOR_CONFIG` literally equals
   `per-iteration, no-score-access`.
9. `TRAIN_PCT + DEV_PCT + TEST_PCT == 100`.
10. `SPP_SCOPE` is one of the documented values.
11. Every gate row in §9 has a non-empty `Approval phrase`
    cell.
12. The plan revision log has at least one row.
