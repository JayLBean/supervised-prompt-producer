# spp plan — support-billing-triage

**Created:** 2026-04-30

**Designer session:** designer-2026-04-30-001

**Plan version:** v1

---

## 1. Task overview

**One-sentence description:** Classify incoming support tickets as
Billing-relevant or Not Billing-relevant for queue routing, replacing
the existing rule-based heuristic that has plateaued at ~73%
accuracy.

**Audience for the prompt's output:** internal triage queue routing
service; the classification drives a routing decision between the
Billing team and the General queue.

**Problem statement** (2–3 sentences on why this task matters and
what currently goes wrong without it):
The heuristic classifier in `src/triage/heuristic.py` has plateaued
at ~73% accuracy. Mis-routed billing tickets cost the support team
roughly 2x what mis-routed general tickets cost (billing tickets are
time-sensitive). Replacing the heuristic with a defensible LLM
classifier is the goal.

---

## 2. Class definition

**Label space:** {Billing, Not Billing}

**Class definitions** (one paragraph per class, with positive and
negative examples — generic, not real data):

- **Billing:** A ticket whose primary intent involves a payment,
  invoice, charge, refund, subscription billing dispute, or any
  monetary transaction with the company. Positive shape: "I was
  charged twice for last month's subscription, please refund the
  duplicate." Negative shape (Not Billing despite mentioning a
  charge): "Can you tell me when my plan renews?" — a question
  about timing, not a billing dispute.
- **Not Billing:** Everything else. Includes feature questions,
  account access, technical issues, customer-success conversations,
  and feedback. Positive shape: "How do I export my data?" Negative
  shape (Billing despite a non-billing surface): "I can't access my
  account because the system says payment failed" — payment-failure
  context makes this Billing.

**Known borderline cases:**
- "Subscription cancelled without charge dispute" — a cancellation
  request with no monetary dispute is Not Billing (customer-success
  work). Decided during consultation; surprisingly common per the
  user.
- Bilingual (English/Spanish) tickets: scope still open — see §10.

---

## 3. Success criteria

**Production decision rule** (the threshold or rule the prompt's
output drives):
Tickets classified Billing route to the Billing team queue; everything
else stays in the General queue (existing routing).

**Headline success criterion** (the single number the user cares
about most):
F1 ≥ 0.85 on test, with precision ≥ 0.80 (precision-leaning given
the cost asymmetry).

**Acceptable trade-offs:**
The user is willing to accept lower recall in exchange for precision,
because mis-routing a non-billing ticket to the Billing team costs
roughly 2x what missing a billing ticket costs (billing team
context-switch cost is high; general queue catches missed billing
tickets within ~1 day).

---

## 4. Metric

**Selected metric:** F1

**Metric rationale** (why this metric, derived from the task
economics in §3):
F1 is the right balance for a 2:1 FP:FN asymmetry with a fixed
production prevalence around 20% billing. A pure precision-at-recall-
floor metric was considered but rejected because the recall floor
the user could articulate was not stable (~0.7 ± a lot); F1 with a
documented precision-leaning posture is more honest about the
trade-off.

**Independence check** (per DESIGN.md §5; required):
F1 is computed against ground-truth labels supplied by the user's
labeler. No model judges another model's outputs. Multi-judge
subjective metrics are forbidden in v1 (DESIGN.md §7.1).

---

## 5. Model and lock-in posture

**Production model identifier:** `gpt-4o-mini-2024-07-18`

**Lock-in posture:** locked

**Cross-model fragility plan:**
We do not plan to swap models for cost reasons. If we ever do, we
re-run /spp-loop against the new model and treat the resulting
prompt as a separate artifact. The prompt's REPORT.md will document
the lock-in caveat per DESIGN.md §2.2.

---

## 6. Baseline

**Data source:** `data/tickets.csv`, sampled stratified-uniform
jointly on `closed_by` (the team that closed the ticket) and the
target class (Billing / Not Billing). Stratifying on `closed_by`
captures team-by-team variance the user has observed historically.

**Target baseline size:** 80 rows

**Class balance target:** preserve production prevalence (~20%
billing); within each class, stratify on `closed_by` to ensure
team-balance.

**Label provenance:** solo labeler (one named team member) with the
`baseline-quality` adversarial review applied. Borderline cases
recorded with rationale; inter-rater calibration spot-checks not
required at this size but available if the labeler flags
uncertainty.

**Status:** not-started

---

## 7. Splits

**Split ratios:** train 60% / dev 20% / test 20%

**Random seed:** 42

**Stratification key:** the binary class label (joint
stratification on `closed_by` is applied at sampling time, not at
split time).

**Sacred test set acknowledgment:** acknowledged

---

## 8. Loop scope and stop criteria

**spp scope:** full
<!-- canonical Phase 1 + 1.5 + 2 + 3; no constraints argue for
     stripping. -->

**MAX_ITERATIONS:** 12

**Dev plateau threshold:** <0.005 F1 improvement for 3 consecutive
iterations.

**Overfitting early-stop guard:** train F1 - dev F1 > 0.10 for 2
consecutive iterations triggers EARLY_STOP.md.

**Auditor configuration:** per-iteration, no-score-access

**Adversary:** off
<!-- Standard-stakes task; the auditor + dev metric are sufficient.
     If post-launch regressions show fragility, can revisit. -->

---

## 9. Decision rules at HITL gates

| Gate | Approval phrase | Notes |
|---|---|---|
| G1 — plan approval | approved | |
| G2 — baseline review | approved | row-specific corrections allowed |
| G3 — split confirmation | approved | |
| G4 — dry-run gate | approved | |
| G5 — finalization | approved | |
| G6 — production decision | ship it | "send back" for iterate-further |

---

## 10. Open questions / known unknowns

- Bilingual ticket handling: the production stream includes a small
  English/Spanish slice. For v1, the baseline samples from the full
  population (both languages); a follow-up question is whether the
  prompt should be evaluated separately on the Spanish slice for
  fairness, or whether a Spanish-specific prompt is the right
  follow-on. Defer to baseline review — if the labeler flags this
  as a high-error class, we treat it as a v2 concern.

---

## 11. Plan revision log

| Date | Plan version | Reason | By |
|---|---|---|---|
| 2026-04-30 | v1 | Initial plan via /spp-init | designer-2026-04-30-001 |
