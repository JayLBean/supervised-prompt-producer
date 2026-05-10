# REPORT — nested-schema-example

**Task:** nested-schema-example
**Model:** placeholder-model-v1
**Plan version:** v1
**Loop start:** 2026-05-10 (placeholder)
**Loop end:** 2026-05-10 (placeholder)
**Finalize start:** 2026-05-10 (placeholder)
**Finalize end:** 2026-05-10 (placeholder)

This REPORT is a skeleton per [`DESIGN.md`](../../../../DESIGN.md)
§7.2; all numbers below are placeholder. The shape follows the
post-bucket-3 v0.2 [`templates/REPORT.md.template`](../../../../skills/run/templates/REPORT.md.template).

---

## 1. Run metadata

Placeholder run; the example does not represent a real
optimization run. The shape below is what `/spp-finalize`
populates from a real run's `test_eval.json`,
`runs/<model>/run_NN/eval.json`, `SUCCESS.md` (or
`EARLY_STOP.md`), and `auditor_review.md` files.

---

## 2. Final scores

§2's structure under v0.2: per-field scores, aggregate scores,
and floor compliance.

### 2.1 Per-field scores

#### Field `top_level`

Primary metric: `macro_F1`

| Partition | Value | N rows |
|---|---|---|
| Test (sacred) | 0.91 | 16 |
| Dev (final iter) | 0.93 | 16 |
| Train (final iter) | 0.95 | 48 |

Confusion matrix (test, rows = ground truth, columns = predictions):

```
              billing  technical  account  other
billing            5          0         1      0
technical          0          5         0      0
account            0          0         3      0
other              0          0         0      2
```

Per-class F1 (test): billing 0.91, technical 1.00, account 0.86,
other 1.00. Macro F1 = 0.94 (placeholder; arithmetic in
this skeleton is illustrative).

#### Field `sub_category`

Primary metric: `macro_F1`

| Partition | Value | N rows |
|---|---|---|
| Test (sacred) | 0.79 | 16 |
| Dev (final iter) | 0.83 | 16 |
| Train (final iter) | 0.87 | 48 |

Confusion matrix (test): omitted in skeleton — the matrix is
sparse per branch (each row's `sub_category` is constrained to
the branch enum, so cross-branch confusions are zero by schema
construction; intra-branch confusions are the relevant signal).

Intra-branch confusion patterns (test, illustrative):

- `billing` branch: one `payment_failed` confused as
  `invoice_question` (the ticket mentioned both an invoice and
  a failed payment; the prompt picked the invoice frame).
- `technical` branch: one `feature_bug` confused as
  `performance_complaint` (a "blank PDF" report could be read
  as either; the rule is "feature does the wrong thing" →
  `feature_bug`, but the prompt landed on
  `performance_complaint` because the user said "always slow
  to fail").

### 2.2 Aggregate scores

| Partition | Aggregate metric | Value |
|---|---|---|
| Test (sacred) | `macro` mean of per-field metrics | 0.85 |
| Dev (final iter) | `macro` mean of per-field metrics | 0.88 |
| Train (final iter) | `macro` mean of per-field metrics | 0.91 |

**Aggregate strategy:** `macro`

**Train–dev aggregate divergence (final iteration):** 0.03
(small; suggests the prompt is generalizing within the labeled
distribution).

### 2.3 Floor compliance (per-field)

| Field | Floor | Status |
|---|---|---|
| `top_level` | 0.90 | met (test 0.91 ≥ 0.90) |
| `sub_category` | — | not_specified |

The `top_level` floor is met on test. The deterministic decision
tree's recommendation can land in the `ship` or `ship-with-
caveats` band (see §6).

---

## 3. Loop trajectory

### 3.1 Per-field trajectories

```
Field `top_level` (macro_F1, dev):
  run_01: 0.82
  run_02: 0.88
  run_03: 0.91
  run_04: 0.93  ← best dev for `top_level`

Field `sub_category` (macro_F1, dev):
  run_01: 0.71
  run_02: 0.77
  run_03: 0.81
  run_04: 0.83  ← best dev for `sub_category`
```

### 3.2 Aggregate trajectory

```
run_01: 0.77
run_02: 0.83
run_03: 0.86
run_04: 0.88  ← best dev, frozen as PROMPT_FROZEN_v01.md
```

**Best dev iteration (aggregate):** run_04 (`macro` = 0.88)

**Frozen prompt source:** `runs/placeholder-model/run_04/prompt_v04.md`
(would be present in a real run; not shipped in this skeleton).

---

## 4. Persistent failure modes

Two placeholder failure clusters from test-set evaluation (per
bucket 3, each cluster names a primary OUTPUT_SCHEMA field).

**4.1 Multi-concern top-level routing**

- **Primary field:** `top_level`
- **Rows in cluster:** row_023 (test partition; placeholder)
- **Description:** tickets that mention multiple concerns
  (a billing issue blocked by an account issue blocked by a
  technical issue) where the "primary blocking concern" rule
  is ambiguous — multiple orderings are defensible. The
  prompt picks one; ground truth picks another.
- **Why this cluster persists:** addressed in iterations 2 and
  3 with rule edits clarifying "primary blocking concern" with
  examples; the rule is a heuristic, not a deterministic
  function. Auditor verdicts on the rule edits were
  `categorical` for `(edit-2, top_level)` and `(edit-3,
  top_level)`. The residual is small (1-2 rows on test out of
  ~3 multi-concern rows) and the team-leads accept this as
  the cost of the heuristic.

**4.2 `feature_bug` vs. `performance_complaint` boundary**

- **Primary field:** `sub_category`
- **Rows in cluster:** row_019, row_021 (test partition;
  placeholder)
- **Description:** tickets in the `technical` branch where
  the boundary between "does the wrong thing" and "does the
  right thing slowly" is genuinely fuzzy — a feature that
  intermittently produces wrong output reads as both
  `feature_bug` (sometimes wrong) and `performance_complaint`
  (sometimes slow/unreliable). The prompt and the labeler
  disagree on which framing dominates.
- **Why this cluster persists:** anticipated in
  `BASELINE_QUALITY_NOTE` (plan.md §6 flagged this boundary
  as the dominant known borderline class); the rule edits
  could not reduce the residual below ~2 rows on test. The
  cluster is a known limitation; the team-leads accept that
  intra-branch sub-category errors are recoverable inside
  the right team's workflow.

---

## 5. Prompt-edit audit

**Per-stage information-isolation invariants:** preserved.

- Discrepancy subagent: allow-list honored, no prior-iteration leakage.
- Rule-edit subagent: allow-list honored, no row-content exposure.
- Auditor subagent: allow-list honored, no score access.
- Adversary subagent (when invoked): allow-list honored, non-persistence honored.

**Auditor verdict counts (per-edit-per-field):** placeholder.

```
Iteration  Edit  Field          Verdict
run_02     1     top_level      categorical
run_02     2     sub_category   categorical
run_03     3     top_level      categorical
run_03     4     sub_category   categorical
run_04     5     sub_category   categorical
```

(All five edits across iterations 2-4 came back `categorical`;
no overrides recorded in `plan.md` §11.)

**Auditor information-isolation invariant: preserved.**

---

## 6. Decision and recommendation

**Recommendation:** `ship-with-caveats`

**Reasoning (deterministic decision tree per
[`phases/spp-finalize.md`](../../../../skills/run/phases/spp-finalize.md)
§4 step 7):**

- Test aggregate (0.85) ≥ headline criterion (`aggregate
  (macro) ≥ 0.85`). ✓
- Per-field floor compliance: `top_level` is `met` (0.91 ≥
  0.90); `sub_category` is `not_specified`. ✓
- Persistent failure clusters exist (§4.1, §4.2) but were
  anticipated in `BASELINE_QUALITY_NOTE` (the
  `feature_bug`/`performance_complaint` boundary was
  flagged at consultation time as a known borderline; the
  multi-concern routing was flagged in plan.md §10 open
  questions). → `ship-with-caveats`.
- `train_test_delta` is 0.06; within the 1.5× `dev_test_delta`
  band (which is 0.03 × 1.5 = 0.045). The 0.06 vs 0.045
  comparison would technically push to a stronger
  caveat, but the `ship-with-caveats` band already covers
  the anticipated-clusters case.

The user accepts the draft `ship-with-caveats` recommendation
at G6.

---

## 7. Limitations and caveats

### 7.1 Model lock-in

Optimized against `placeholder-model-v1`. Cross-model
fragility per [`DESIGN.md`](../../../../DESIGN.md) §2.2.

### 7.2 Baseline scope and provenance

80 rows; placeholder data per `BASELINE_QUALITY_NOTE` in
[`config/plan.md`](../../config/plan.md) §6. Per-field
calibration ran on both OUTPUT_SCHEMA fields per
[`baseline-quality`](../../../../skills/run/sub-skills/baseline-quality/SKILL.md)
SKILL.md §3 v0.2 per-field application; consolidated verdict
is `ready` after one revise-then-re-validate cycle on the
`technical` branch's `sub_category` definition.

### 7.3 Persistent failure clusters

See §4. Both clusters are anticipated per
`BASELINE_QUALITY_NOTE`.

### 7.4 Loop interruption posture (v1)

v1 does not support mid-iteration resumption per
[`DESIGN.md`](../../../../DESIGN.md) §7.1; this loop terminated
cleanly via SUCCESS.md.

### 7.5 Acknowledged-risk overrides

None recorded. (The five rule edits across iterations 2-4 all
came back `categorical`; no `auditor override` entries in
`plan.md` §11. The `top_level` floor was met on test, so no
`early_stop_floor_unmet` override applies.)

### 7.6 Other caveats

The `feature_bug`/`performance_complaint` boundary inside
`technical` is the dominant residual ambiguity. The team-leads
accept this as a recoverable error mode inside the technical
team's workflow.

---

## 8. Cost at scale

Per-row API cost: placeholder. Projections at 1K / 10K / 100K
rows omitted in skeleton.

---

## 9. Production prompt artifact

**SHA-256 hash of frozen prompt:** placeholder-hash-not-real

**File path:** `runs/placeholder-model/PROMPT_FROZEN_v01.md`
(would be present in a real run; not shipped in this skeleton).

**Hash verification command:** `shasum -a 256
runs/placeholder-model/PROMPT_FROZEN_v01.md`

---

## 10. Reproducibility checklist

- Commit hash at loop start: placeholder
- Commit hash at finalize: placeholder
- `splits.json` seed: 42
- OUTPUT_SCHEMA: see [`config/plan.md`](../../config/plan.md) §2
  (note the `allOf` conditional clauses)
