# REPORT — feature-group-split-urgency

**Task:** feature-group-split-urgency
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

Placeholder run for the urgency sub-task of the
`feature-group-split` parent example. See
[`../../README.md`](../../README.md) for decomposition rationale.

---

## 2. Final scores

### 2.1 Per-field scores

#### Field `urgency`

Primary metric: `macro_F1`

| Partition | Value | N rows |
|---|---|---|
| Test (sacred) | 0.91 | 16 |
| Dev (final iter) | 0.93 | 16 |
| Train (final iter) | 0.95 | 48 |

Confusion matrix (test, rows = ground truth):

```
            immediate  normal  low
immediate         4        0    0
normal            0        5    1
low               0        0    6
```

Per-class recall (test): `immediate` = 1.00; `normal` = 0.83;
`low` = 1.00. Per-class recall on `immediate` is what the
escalation engine depends on; the placeholder reaches the
class-level bar.

### 2.2 Aggregate scores

| Partition | Aggregate metric | Value |
|---|---|---|
| Test (sacred) | `macro` (K=1 identity) | 0.91 |
| Dev (final iter) | `macro` (K=1 identity) | 0.93 |
| Train (final iter) | `macro` (K=1 identity) | 0.95 |

**Aggregate strategy:** `macro` (trivial K=1 identity).
**Train–dev aggregate divergence:** 0.02.

### 2.3 Floor compliance (per-field)

| Field | Floor | Status |
|---|---|---|
| `urgency` | 0.90 | met (test 0.91 ≥ 0.90) |

---

## 3. Loop trajectory

### 3.1 Per-field trajectories

```
Field `urgency` (macro_F1, dev):
  run_01: 0.82
  run_02: 0.87
  run_03: 0.91
  run_04: 0.93  ← best dev
```

### 3.2 Aggregate trajectory

```
run_01: 0.82
run_02: 0.87
run_03: 0.91
run_04: 0.93  ← best dev, frozen as PROMPT_FROZEN_v01.md
```

---

## 4. Persistent failure modes

**4.1 High-tone-low-impact boundary** — primary field: `urgency`.
One test row where the customer is angry about a routine issue
(`normal`) was predicted `immediate` because the prompt over-
weighted the tone signal. Addressed in iterations 2 and 3 with
rule edits separating affect from impact; residual is one row.
Anticipated in plan.md §6 `BASELINE_QUALITY_NOTE` and §10. This is
the canonical example of why splitting urgency from sentiment
matters — combining them into one prompt invites this exact
confusion at the rules layer.

---

## 5. Prompt-edit audit

**Per-stage information-isolation invariants:** preserved.

- Discrepancy subagent: allow-list honored, no prior-iteration leakage.
- Rule-edit subagent: allow-list honored, no row-content exposure.
- Auditor subagent: allow-list honored, no score access.
- Adversary subagent (when invoked): allow-list honored, non-persistence honored.

**Auditor verdict counts:** placeholder. All edits across
iterations 2-4 came back `categorical` on `(edit-N, urgency)`;
no overrides recorded.

**Auditor information-isolation invariant: preserved.**

---

## 6. Decision and recommendation

**Recommendation:** `ship`

**Reasoning:** test aggregate (0.91) ≥ headline criterion (0.85);
the `urgency` floor (0.90) is met on test; persistent failure
cluster (§4.1) was anticipated; per-class recall on `immediate`
reaches 1.00 on the placeholder test partition.

---

## 7. Limitations and caveats

### 7.1 Model lock-in

Optimized against `placeholder-model-v1`.

### 7.2 Baseline scope and provenance

80 rows; placeholder data. K=1 per-field calibration on `urgency`.
The high-tone-low-impact boundary was the focus of §3.3
calibration.

### 7.3 Persistent failure clusters

See §4.

### 7.4 Loop interruption posture (v1)

Clean termination via SUCCESS.md.

### 7.5 Acknowledged-risk overrides

None recorded.

### 7.6 Other caveats

This is the urgency sub-task of the `feature-group-split` parent
example. The high-tone-low-impact pattern is the clearest
demonstration of why splitting affect (sentiment) from impact
(urgency) matters — a unified prompt would invite the rules layer
to conflate the two.

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
