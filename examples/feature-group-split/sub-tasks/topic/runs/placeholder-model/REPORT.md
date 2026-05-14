# REPORT — feature-group-split-topic

**Task:** feature-group-split-topic
**Model:** placeholder-model-v1
**Plan version:** v1
**Loop start:** 2026-05-14 (placeholder)
**Loop end:** 2026-05-14 (placeholder)
**Finalize start:** 2026-05-14 (placeholder)
**Finalize end:** 2026-05-14 (placeholder)

Skeleton per [`DESIGN.md`](../../../../../DESIGN.md) §7.2; numbers
are placeholder. K=1 collapses the per-field block to one entry.

---

## 1. Run metadata

Placeholder run for the topic sub-task of the
`feature-group-split` parent example. See
[`../../README.md`](../../README.md) for decomposition rationale.

---

## 2. Final scores

### 2.1 Per-field scores

#### Field `topic`

Primary metric: `macro_F1`

| Partition | Value | N rows |
|---|---|---|
| Test (sacred) | 0.88 | 16 |
| Dev (final iter) | 0.91 | 16 |
| Train (final iter) | 0.93 | 48 |

Confusion matrix (test, rows = ground truth):

```
          product  service  billing  other
product        6        0        0      0
service        0        4        0      0
billing        1        0        3      0
other          0        0        0      2
```

### 2.2 Aggregate scores

| Partition | Aggregate metric | Value |
|---|---|---|
| Test (sacred) | `macro` (K=1 identity) | 0.88 |
| Dev (final iter) | `macro` (K=1 identity) | 0.91 |
| Train (final iter) | `macro` (K=1 identity) | 0.93 |

**Aggregate strategy:** `macro` (trivial K=1 identity).
**Train–dev aggregate divergence:** 0.02.

### 2.3 Floor compliance (per-field)

| Field | Floor | Status |
|---|---|---|
| `topic` | 0.85 | met (test 0.88 ≥ 0.85) |

---

## 3. Loop trajectory

### 3.1 Per-field trajectories

```
Field `topic` (macro_F1, dev):
  run_01: 0.79
  run_02: 0.85
  run_03: 0.89
  run_04: 0.91  ← best dev
```

### 3.2 Aggregate trajectory

```
run_01: 0.79
run_02: 0.85
run_03: 0.89
run_04: 0.91  ← best dev, frozen as PROMPT_FROZEN_v01.md
```

(Under K=1 the aggregate equals the per-field trajectory.)

---

## 4. Persistent failure modes

**4.1 Billing-portal hybrid** — primary field: `topic`. One test
row labeled `product` (UI concern about the billing portal) was
predicted `billing`. Addressed in iteration 3 with a rule edit on
"primary content concern"; residual is one row. Anticipated in
plan.md §10 open questions.

---

## 5. Prompt-edit audit

**Per-stage information-isolation invariants:** preserved.

- Discrepancy subagent: allow-list honored, no prior-iteration leakage.
- Rule-edit subagent: allow-list honored, no row-content exposure.
- Auditor subagent: allow-list honored, no score access.
- Adversary subagent (when invoked): allow-list honored, non-persistence honored.

**Auditor verdict counts:** placeholder. All edits across
iterations 2-4 came back `categorical` on `(edit-N, topic)`; no
overrides recorded.

**Auditor information-isolation invariant: preserved.**

---

## 6. Decision and recommendation

**Recommendation:** `ship`

**Reasoning:** test aggregate (0.88) ≥ headline criterion (0.85);
the `topic` floor (0.85) is met on test; persistent failure
cluster (§4.1) was anticipated.

---

## 7. Limitations and caveats

### 7.1 Model lock-in

Optimized against `placeholder-model-v1`.

### 7.2 Baseline scope and provenance

80 rows; placeholder data. K=1 per-field calibration on `topic`.

### 7.3 Persistent failure clusters

See §4.

### 7.4 Loop interruption posture (v1)

Clean termination via SUCCESS.md.

### 7.5 Acknowledged-risk overrides

None recorded.

### 7.6 Other caveats

This is the topic sub-task of the `feature-group-split` parent
example; cross-sub-task coordination is the user's responsibility
per [`DESIGN.md`](../../../../../DESIGN.md) §10 glossary entry
"Feature-group prompt splitting."

---

## 8. Cost at scale

Per-row API cost: placeholder.

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
