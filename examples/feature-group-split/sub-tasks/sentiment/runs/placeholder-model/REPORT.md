# REPORT — feature-group-split-sentiment

**Task:** feature-group-split-sentiment
**Model:** placeholder-model-v1
**Plan version:** v1
**Loop start:** 2026-05-14 (placeholder)
**Loop end:** 2026-05-14 (placeholder)
**Finalize start:** 2026-05-14 (placeholder)
**Finalize end:** 2026-05-14 (placeholder)

This REPORT is a skeleton per [`DESIGN.md`](../../../../../DESIGN.md)
§7.2; all numbers are placeholder. Per
[`templates/REPORT.md.template`](../../../../../skills/run/templates/REPORT.md.template)
v0.2 shape (post-bucket-3). K=1 collapses the per-field block to
one entry and the aggregate trajectory equals the per-field
trajectory.

---

## 1. Run metadata

Placeholder run for the sentiment sub-task of the
`feature-group-split` parent example. See
[`../../README.md`](../../README.md) for the decomposition
rationale.

---

## 2. Final scores

### 2.1 Per-field scores

#### Field `sentiment`

Primary metric: `macro_F1`

| Partition | Value | N rows |
|---|---|---|
| Test (sacred) | 0.87 | 16 |
| Dev (final iter) | 0.89 | 16 |
| Train (final iter) | 0.92 | 48 |

Confusion matrix (test, rows = ground truth):

```
            positive  negative  neutral
positive         6         0        0
negative         0         5        1
neutral          0         1        3
```

### 2.2 Aggregate scores

| Partition | Aggregate metric | Value |
|---|---|---|
| Test (sacred) | `macro` (K=1 identity) | 0.87 |
| Dev (final iter) | `macro` (K=1 identity) | 0.89 |
| Train (final iter) | `macro` (K=1 identity) | 0.92 |

**Aggregate strategy:** `macro` (trivial K=1 identity).
**Train–dev aggregate divergence:** 0.03 (small).

### 2.3 Floor compliance (per-field)

| Field | Floor | Status |
|---|---|---|
| `sentiment` | — | not_specified |

(No floor configured for this sub-task.)

---

## 3. Loop trajectory

### 3.1 Per-field trajectories

```
Field `sentiment` (macro_F1, dev):
  run_01: 0.78
  run_02: 0.84
  run_03: 0.87
  run_04: 0.89  ← best dev
```

### 3.2 Aggregate trajectory

```
run_01: 0.78
run_02: 0.84
run_03: 0.87
run_04: 0.89  ← best dev, frozen as PROMPT_FROZEN_v01.md
```

(Under K=1 the aggregate trajectory equals the per-field
trajectory by construction.)

---

## 4. Persistent failure modes

One placeholder cluster:

**4.1 Sarcasm boundary** — primary field: `sentiment`. Two rows on
test where the surface tone is positive but the content is
sarcastic; the prompt classified them `positive` but ground truth
is `negative`. Addressed in iteration 3 with a rule edit on
sarcasm cues; residual is small. Anticipated in plan.md §6
`BASELINE_QUALITY_NOTE`.

---

## 5. Prompt-edit audit

**Per-stage information-isolation invariants:** preserved.

- Discrepancy subagent: allow-list honored, no prior-iteration leakage.
- Rule-edit subagent: allow-list honored, no row-content exposure.
- Auditor subagent: allow-list honored, no score access.
- Adversary subagent (when invoked): allow-list honored, non-persistence honored.

**Auditor verdict counts:** placeholder. All edits across
iterations 2-4 came back `categorical` on `(edit-N, sentiment)`;
no overrides recorded.

**Auditor information-isolation invariant: preserved.**

---

## 6. Decision and recommendation

**Recommendation:** `ship`

**Reasoning:** test aggregate (0.87) ≥ headline criterion (0.85);
no per-field floor configured (so floor-compliance is
`not_specified`); persistent failure cluster (§4.1) was
anticipated in `BASELINE_QUALITY_NOTE`; `train_test_delta` is 0.05,
within the 1.5× `dev_test_delta` band.

---

## 7. Limitations and caveats

### 7.1 Model lock-in

Optimized against `placeholder-model-v1`. Cross-model fragility per
[`DESIGN.md`](../../../../../DESIGN.md) §2.2.

### 7.2 Baseline scope and provenance

80 rows; placeholder data. Per-field calibration ran on the lone
`sentiment` field per
[`baseline-quality`](../../../../../skills/run/sub-skills/baseline-quality/SKILL.md)
SKILL.md §3 v0.2 per-field application (K=1 collapses to v0.1.0's
single-field flow).

### 7.3 Persistent failure clusters

See §4.

### 7.4 Loop interruption posture (v1)

v1 does not support mid-iteration resumption; this loop terminated
cleanly via SUCCESS.md.

### 7.5 Acknowledged-risk overrides

None recorded.

### 7.6 Other caveats

This is the sentiment sub-task of the `feature-group-split` parent
example; cross-sub-task coordination (topic + urgency) is the
user's responsibility at the production-pipeline layer per
[`DESIGN.md`](../../../../../DESIGN.md) §10 glossary entry
"Feature-group prompt splitting." See
[`../../walkthrough.md`](../../walkthrough.md) for the
composition framing.

---

## 8. Cost at scale

Per-row API cost: placeholder. Projections omitted in skeleton.

---

## 9. Production prompt artifact

**SHA-256 hash of frozen prompt:** placeholder-hash-not-real

**File path:** `runs/placeholder-model/PROMPT_FROZEN_v01.md`

---

## 10. Reproducibility checklist

- Commit hash at loop start: placeholder
- Commit hash at finalize: placeholder
- `splits.json` seed: 42
- OUTPUT_SCHEMA: see [`../../config/plan.md`](../../config/plan.md) §2
