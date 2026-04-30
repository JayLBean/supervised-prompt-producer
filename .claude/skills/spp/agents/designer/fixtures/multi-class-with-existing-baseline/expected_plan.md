# spp plan — issue-categorization-v2

**Created:** 2026-04-30

**Designer session:** designer-2026-04-30-003

**Plan version:** v1

---

## 1. Task overview

**One-sentence description:** Categorize incoming GitHub issues across
4 classes (Bug, Feature, Question, Other) for routing to the right
team, replacing the v1 regex-based triage that achieved 67% accuracy.

**Audience for the prompt's output:** internal team-routing service;
each category routes to a different on-call rotation (engineering for
Bug, product for Feature, support for Question, triage for Other).

**Problem statement:**
The v1 regex-based triage plateaued at 67% accuracy and consistently
mis-classified issues that did not contain triage-relevant keywords.
The user has labeled 200 issues across the 4 classes and wants to
produce an LLM prompt that improves on the regex baseline.

---

## 2. Class definition

**Label space:** {Bug, Feature, Question, Other}

**Class definitions** (one paragraph per class, with positive and
negative examples — generic shapes, not real issues):

- **Bug:** A reported defect — observed behavior that contradicts
  documented or intended behavior. Positive shape: "Calling
  `compute()` with an empty list raises a TypeError instead of
  returning [] like the docs say."
- **Feature:** A request for new capability or extension. Positive
  shape: "Add a JSON output mode to the CLI."
- **Question:** A request for clarification or help understanding
  existing behavior, where the user has not asserted a defect.
  Positive shape: "Does `compute()` handle Unicode keys?"
- **Other:** Documentation issues, build/CI breakage reports, repo
  hygiene, or any issue that does not fit the first three. Positive
  shape: "Typo in README." Negative shape (Bug, not Other):
  "README example produces wrong output" — the README example is a
  documentation contract; producing the wrong output is a defect.

**Known borderline cases:**
Question vs Bug: when the user describes confusing or unexpected
behavior without explicitly asserting it's a defect. The labeler
called these by gut; the prompt should aim for a more articulable
rule. Defer to baseline-quality and the auditor's
categorical-vs-row-specific judgment in Phase 2.

---

## 3. Success criteria

**Production decision rule:**
Each issue is routed to one of four team queues based on the
prediction.

**Headline success criterion:**
macro-F1 ≥ 0.80 on test, with no individual class F1 below 0.65
(prevents a class-balanced metric from masking a single failed
class).

**Acceptable trade-offs:**
The user is willing to accept some confusion between Question and
Bug (the labeler-articulated borderline) so long as no class falls
below the 0.65 floor. There is no other strong asymmetry between
classes — mis-routing is a wasted-attention cost, not a regulatory
or revenue cost, and is roughly symmetric across pairs.

---

## 4. Metric

**Selected metric:** macro_F1

**Metric rationale:**
macro-F1 weights all four classes equally regardless of class
frequency. Balanced accuracy was the alternative (weights per-class
recall equally); macro-F1 was chosen because the user's stated
constraint includes a precision component ("no individual class F1
below 0.65"), and balanced accuracy does not.

**Independence check:**
macro-F1 is computed against ground-truth labels supplied by the
labeler. No model judges another model's outputs. Multi-judge
subjective metrics are forbidden in v1 (DESIGN.md §7.1).

---

## 5. Model and lock-in posture

**Production model identifier:** `claude-haiku-4-5-20251001`

**Lock-in posture:** locked

**Cross-model fragility plan:**
The user has chosen Anthropic's Haiku 4.5 for cost reasons. If we
ever swap (e.g. to Sonnet 4.6), we re-run /spp-loop against the new
model. The prompt's REPORT.md will document the lock-in caveat per
DESIGN.md §2.2.

---

## 6. Baseline

**Data source:** `data/labels.csv` (200 rows, columns
`issue_id, label, labeler, labeled_at`). Issues themselves are in
`data/issues_unlabeled.csv` (1,200 rows); the baseline joins
`labels.csv` to `issues_unlabeled.csv` on `issue_id`.

**Target baseline size:** 200 rows
<!-- Existing labels — the user is bringing their own labels, per
     README "When to use this." Phase 1 in this plan is an audit of
     existing labels, not a fresh labeling pass. -->

**Class balance target:** preserve the existing distribution
(roughly 40% Bug, 25% Feature, 25% Question, 10% Other), since
that is closer to production prevalence than a synthetic balance
would be.

**Label provenance:** single SRE labeler over a multi-week sprint
(see `labeler` and `labeled_at` columns). The
`baseline-quality` adversarial review applies as an *audit* of
the existing labels rather than a fresh-labeling sub-skill.
Specific concern flagged for the audit: the `Other` class may
have drifted across the labeling timeline (from the user's open
question in §10).

**Status:** complete
<!-- Labels exist on initial entry. /spp-baseline runs the
     audit-mode of baseline-quality and the stratified split;
     it does NOT redo labeling. -->

---

## 7. Splits

**Split ratios:** train 60% / dev 20% / test 20%

**Random seed:** 42

**Stratification key:** the 4-class label.

**Sacred test set acknowledgment:** acknowledged

---

## 8. Loop scope and stop criteria

**spp scope:** full

**MAX_ITERATIONS:** 12

**Dev plateau threshold:** <0.005 macro_F1 improvement for 3
consecutive iterations.

**Overfitting early-stop guard:** train macro_F1 - dev macro_F1 >
0.10 for 2 consecutive iterations triggers EARLY_STOP.md.

**Auditor configuration:** per-iteration, no-score-access

**Adversary:** off

---

## 9. Decision rules at HITL gates

| Gate | Approval phrase | Notes |
|---|---|---|
| G1 — plan approval | approved | |
| G2 — baseline review | approved | label-audit findings (drift in Other) |
| G3 — split confirmation | approved | |
| G4 — dry-run gate | approved | |
| G5 — finalization | approved | |
| G6 — production decision | ship | "send back" for iterate-further |

---

## 10. Open questions / known unknowns

- **`Other`-class consistency drift.** The labeler did the work in
  multiple batches over a few weeks; the user is not confident the
  `Other` class label was applied consistently across the
  timeline. The `baseline-quality` audit pass at /spp-baseline
  must spot-check at least 5 `Other`-labeled rows from each
  `labeled_at` batch and flag any apparent definition shift.
  Resolved via baseline-review at G2 — relabel rows where drift
  is detected.
- **Question-vs-Bug borderline articulation.** The labeler called
  these by gut. The Phase 2 loop must produce an articulable rule
  rather than relying on the labeler's intuition; the auditor's
  per-iteration review is particularly important here for keeping
  the rule categorical rather than row-specific.
- Whether macro_F1's per-class floor (0.65) is achievable given
  ~20 `Other` test rows is unclear; small per-class N at test time
  may produce metric noise. Defer to /spp-finalize for honest
  reporting.

---

## 11. Plan revision log

| Date | Plan version | Reason | By |
|---|---|---|---|
| 2026-04-30 | v1 | Initial plan via /spp-init; existing labels in data/labels.csv set BASELINE_STATUS = complete on initial entry | designer-2026-04-30-003 |
