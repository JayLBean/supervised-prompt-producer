# spp plan — clinical-note-deidentification-flag

**Created:** 2026-04-30

**Designer session:** designer-2026-04-30-002

**Plan version:** v1

---

## 1. Task overview

**One-sentence description:** Classify clinical notes as
PHI-removed-correctly or Still-Leaky after passing through an
upstream redaction pipeline; flag Still-Leaky notes for clinician
re-review.

**Audience for the prompt's output:** internal compliance review
queue. A Still-Leaky flag triggers a clinician re-review before the
note is downstream-shared.

**Problem statement:**
The PHI redaction pipeline occasionally leaks identifiers (nested
PHI in document footers, mixed-format dates). Manual sampling shows
~3-5% leak rate but is too expensive to scale. A second-pass
classifier flags suspect notes for clinician review. False-negatives
are a regulatory issue; false-positives cost re-review time but are
not safety-critical.

---

## 2. Class definition

**Label space:** {PHI-Removed-Correctly, Still-Leaky}

**Class definitions** (one paragraph per class, with positive and
negative examples — generic shapes, not real notes):

- **PHI-Removed-Correctly:** A note where every PHI element listed
  in `data/annotation_protocol.md` has been replaced with the
  appropriate redaction marker, including PHI in document footers,
  dates with non-standard formats, and embedded structured data.
- **Still-Leaky:** A note where at least one PHI element remains
  unredacted, even partially. Includes nested PHI (e.g. a
  redacted patient name still appearing in a quoted prior note),
  mixed-format dates that escaped the date redactor, and
  identifiers in unusual fields.

**Known borderline cases:**
The user's `annotation_protocol.md` enumerates these. The
designer references the protocol rather than re-deriving its
content here; the labeler reads the protocol during Phase 1.

---

## 3. Success criteria

**Production decision rule:**
Notes flagged Still-Leaky route to clinician re-review queue;
notes flagged PHI-Removed-Correctly proceed to downstream sharing.

**Headline success criterion:**
Recall ≥ 0.95 on Still-Leaky (false-negatives are regulatory),
with precision ≥ 0.50 (false-positives cost re-review but are
acceptable).

**Acceptable trade-offs:**
The user accepts that the prompt will over-flag — many flagged
notes will turn out to be PHI-Removed-Correctly on clinician
review. The cost of re-review is acceptable; the cost of a missed
PHI leak is not.

---

## 4. Metric

**Selected metric:** recall_at_precision

**Metric rationale:**
The task economics demand a recall floor; precision can absorb
loss to satisfy it. F1 was rejected because it would be
unsatisfied to optimize for recall when the cost asymmetry is
this extreme. Precision-at-recall-floor is the symmetric
alternative; recall-at-precision-floor was selected because the
user's actual constraint is "recall ≥ 0.95, precision flexible
above ~0.50" rather than "precision fixed, recall flexible."

**Independence check:**
recall_at_precision is computed against ground-truth labels
supplied by the clinician labeler. No model judges another
model's outputs.

---

## 5. Model and lock-in posture

**Production model identifier:** `azure-gpt-4o-2024-11-20`

**Lock-in posture:** locked

**Cross-model fragility plan:**
HIPAA-eligible deployment is Azure-only in this organization's
infrastructure. There is no swap option for v1; if Azure adds
another HIPAA-eligible model, re-running /spp-loop against it is
a separate plan. The prompt's REPORT.md will document the lock-in
caveat per DESIGN.md §2.2 with explicit reference to the
HIPAA-deployment constraint as the reason lock-in is acceptable
here.

---

## 6. Baseline

**Data source:** `data/notes_unlabeled.jsonl`, sampled
stratified-uniform on `source_system` (the upstream redaction
pipeline's source flag), to capture variance across redaction
implementations.

**Target baseline size:** 30 rows
<!-- Constrained by clinician labeling cost (~20-40 minutes per
     row, ~15 hours of clinician time budgeted total). 30 is the
     ceiling, not the choice. The methodology adapts (DESIGN.md
     core principle 2; README "When to use this" notes baseline
     size is the user's call). -->

**Class balance target:** preserve production prevalence (~3-5%
Still-Leaky); the designer notes that 30 rows at this prevalence
gives only ~1-2 positive examples in expectation, which is too
few. The labeler will deliberately oversample suspected leaks
during Phase 1 — the resulting class balance will not match
production but the loop's metric is recall-floor, which tolerates
a synthetic balance.

**Label provenance:** single clinician labeler. The
`baseline-quality` adversarial review applies; given the
high-stakes domain, inter-rater calibration on ambiguous cases is
recommended even at this size — the labeler may flag any row
where their confidence is <90% for review.

**Status:** not-started

---

## 7. Splits

**Split ratios:** train 70% / dev 30% / test 0%
<!-- Test 0% because Phase 3 is replaced by shadow-deployment
     pilot — see §8 SPP_SCOPE comment. -->

**Random seed:** 42

**Stratification key:** the binary class label.

**Sacred test set acknowledgment:** acknowledged
<!-- The sacred-test-set guarantee is preserved in spirit: there
     is no test set in this plan, so there is no test set to
     touch mid-loop. The Phase-3-substitute pilot deployment is
     external to spp; its results are recorded in REPORT.md
     §7.5 (other caveats), not §2.1 (test scores). -->

---

## 8. Loop scope and stop criteria

**spp scope:** stripped-no-phase3
<!-- Phase 3 (sacred test set evaluation) is replaced by a shadow-
     deployment pilot: the frozen prompt runs against production
     traffic for 1 week with clinician spot-check, and graduates
     if observed recall ≥ 0.95 and observed precision ≥ 0.50
     across at least 20 spot-checked notes during the pilot.
     Reason: with 30 baseline rows, a 6-row test split would
     give a metric variance that swamps signal — the pilot
     produces a more honest estimate. The skip is documented in
     REPORT.md §7.4 (loop interruption / scope-stripping
     posture) at /spp-finalize time. -->

**MAX_ITERATIONS:** 8
<!-- Lower than the default 12 because the dev set is 9 rows;
     more iterations would primarily produce auditor noise rather
     than useful signal. -->

**Dev plateau threshold:** <0.01 recall improvement (at the
precision floor) for 2 consecutive iterations.
<!-- Higher threshold than fixture 1's <0.005 because of the
     small-dev-set noise floor. -->

**Overfitting early-stop guard:** train recall - dev recall >
0.08 for 2 consecutive iterations triggers EARLY_STOP.md.
<!-- Tighter than the default 0.10 because small dev sets show
     overfit divergence faster and more noisily. -->

**Auditor configuration:** per-iteration, no-score-access
<!-- Non-negotiable. Particularly load-bearing in this plan: with
     21 train rows, the loop is at high risk of accumulating
     row-specific edits dressed up as rules. The auditor's
     categorical-vs-row-specific judgment is the primary defense
     against the 30-row baseline producing a baseline-overfit
     prompt. -->

**Adversary:** on
<!-- High-stakes domain (regulatory consequences). Adversarial
     row generation between iterations probes for nested-PHI and
     mixed-format-date blind spots that the small baseline may
     not happen to contain. -->

---

## 9. Decision rules at HITL gates

| Gate | Approval phrase | Notes |
|---|---|---|
| G1 — plan approval | approved | |
| G2 — baseline review | approved | clinician confidence flags allowed |
| G3 — split confirmation | approved | |
| G4 — dry-run gate | approved | |
| G5 — finalization | approved | "graduate to pilot" or "iterate" |
| G6 — production decision | approved | "ship to pilot" or "iterate" |

---

## 10. Open questions / known unknowns

- **Is 30 rows enough not to chase labels?** Honestly unknown at
  consultation time. The auditor's per-iteration
  categorical-vs-row-specific judgment is the primary defense
  here; if the auditor flags a high proportion of edits as
  row-specific, that itself signals the baseline is too small to
  ground a generalizable prompt and the plan should be revised
  (likely "label more rows, even slowly" rather than "ship a
  potentially overfit prompt"). Recorded so this question
  resurfaces at gate G5.
- Class-imbalance strategy: the 3-5% production prevalence is
  preserved through oversampling for labeling, but the loop's
  prediction distribution may need post-hoc threshold
  calibration if recall-at-precision proves unstable across
  iterations. Defer until iteration 3-4 trajectory is visible.
- Pilot graduation criteria (recall ≥ 0.95, precision ≥ 0.50,
  ≥20 spot-checks) are estimated from the user's stated cost
  asymmetry — the actual pilot may need to revise based on what
  the first week of shadow-deployment shows.

---

## 11. Plan revision log

| Date | Plan version | Reason | By |
|---|---|---|---|
| 2026-04-30 | v1 | Initial plan via /spp-init; stripped-no-phase3 scope chosen due to 30-row labeling budget and 6-row-test honesty constraint | designer-2026-04-30-002 |
