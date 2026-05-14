# REPORT — multi-field-extraction-example

**Task:** multi-field-extraction-example
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
`EARLY_STOP.md/early_stop_floor_unmet`), and `auditor_review.md`
files.

---

## 2. Final scores

§2's structure under v0.2 ([`DESIGN.md`](../../../../DESIGN.md)
§7.1.1 per-field methodology application layer) carries three
blocks: per-field scores, aggregate scores, and floor compliance.

### 2.1 Per-field scores

#### Field `title`

Primary metric: `exact_match`

| Partition | Value | N rows |
|---|---|---|
| Test (sacred) | 0.92 | 16 |
| Dev (final iter) | 0.94 | 16 |
| Train (final iter) | 0.96 | 48 |

Auxiliary structures: top-3 most-common-error categories on
test were title canonicalization edge cases (variant naming;
promotional-tagline stripping).

#### Field `price`

Primary metric: `MAE`

| Partition | Value | N rows |
|---|---|---|
| Test (sacred) | $3.20 | 16 |
| Dev (final iter) | $2.80 | 16 |
| Train (final iter) | $2.10 | 48 |

Auxiliary structures: residual distribution on test is
right-skewed; the 95th percentile residual is $9.50, driven
by descriptions with strikethrough/sale-price ambiguity.

#### Field `category`

Primary metric: `macro_F1`

| Partition | Value | N rows |
|---|---|---|
| Test (sacred) | 0.83 | 16 |
| Dev (final iter) | 0.88 | 16 |
| Train (final iter) | 0.91 | 48 |

Confusion matrix (test, rows = ground truth, columns = predictions):

```
              apparel  electronics  home  media  outdoor
apparel           5            0     0      0        1
electronics       0            4     1      0        0
home              0            1     3      0        0
media             0            0     0      1        0
outdoor           0            0     0      0        0
```

(N=16 rows; one outdoor row is missing because the placeholder
test partition has no outdoor row at this seed — illustrative
only.)

Per-class precision/recall/F1 omitted in skeleton.

#### Field `in_stock`

Primary metric: `F1`

| Partition | Value | N rows |
|---|---|---|
| Test (sacred) | 0.95 | 16 |
| Dev (final iter) | 0.93 | 16 |
| Train (final iter) | 0.94 | 48 |

Confusion matrix (test, 2x2): `tp=12 fp=0 fn=1 tn=3`.

### 2.2 Aggregate scores

| Partition | Aggregate metric | Value |
|---|---|---|
| Test (sacred) | `min` of per-field metrics | 0.83 |
| Dev (final iter) | `min` of per-field metrics | 0.88 |
| Train (final iter) | `min` of per-field metrics | 0.91 |

(Per-field metrics normalized to [0, 1] before applying `min`
per [`config/plan.md`](../../config/plan.md) §4
`AGGREGATE_RATIONALE`.)

**Aggregate strategy:** `min`

**Train–dev aggregate divergence (final iteration):** 0.03
(small; suggests the prompt is generalizing within the labeled
distribution).

### 2.3 Floor compliance (per-field)

| Field | Floor | Status |
|---|---|---|
| `title` | — | not_specified |
| `price` | — | not_specified |
| `category` | 0.85 | unmet (test 0.83 < 0.85) |
| `in_stock` | — | not_specified |

The `category` floor was unmet on test (0.83 < 0.85). This
surfaces under §7.5 acknowledged-risk overrides below; the §6
recommendation reflects the unmet-floor signal.

---

## 3. Loop trajectory

§3 carries one trajectory table per OUTPUT_SCHEMA field plus one
trajectory table for the aggregate metric. Per-field movement is
informational; the aggregate gates `/spp-loop`'s stop discipline.

### 3.1 Per-field trajectories

```
Field `title` (exact_match, dev):
  run_01: 0.81
  run_02: 0.86
  run_03: 0.91
  run_04: 0.94  ← best dev for `title`

Field `price` (MAE, dev):
  run_01: $5.40
  run_02: $4.10
  run_03: $3.20
  run_04: $2.80  ← best dev for `price`

Field `category` (macro_F1, dev):
  run_01: 0.74
  run_02: 0.81
  run_03: 0.85
  run_04: 0.88  ← best dev for `category`

Field `in_stock` (F1, dev):
  run_01: 0.85
  run_02: 0.89
  run_03: 0.91
  run_04: 0.93  ← best dev for `in_stock`
```

### 3.2 Aggregate trajectory

```
run_01: 0.74
run_02: 0.81
run_03: 0.85
run_04: 0.88  ← best dev, frozen as PROMPT_FROZEN_v01.md
```

(MAE-bearing field's contribution to the aggregate is the
normalized form `1 - MAE/MAX_PRICE` per [`config/plan.md`](../../config/plan.md)
§4 `AGGREGATE_RATIONALE`; the trajectory above shows the
post-normalization aggregate value.)

**Best dev iteration (aggregate):** run_04 (`min` = 0.88)

**Frozen prompt source:** `runs/placeholder-model/run_04/prompt_v04.md`
(would be present in a real run; not shipped in this skeleton).

---

## 4. Persistent failure modes

Three placeholder failure clusters from test-set evaluation
(per bucket 3, each cluster names a primary OUTPUT_SCHEMA
field).

**4.1 Smart-home / electronics misclassification**

- **Primary field:** `category`
- **Rows in cluster:** row_017, row_023 (test partition; placeholder)
- **Description:** Wi-Fi-enabled home appliances where the
  description leads with the smart-feature framing ("Wi-Fi
  coffee maker") rather than the appliance framing ("coffee
  maker with Wi-Fi"). The prompt routes to `electronics` on
  the smart-feature lead; ground truth is `home` per the
  primary-use-case rule.
- **Why this cluster persists:** addressed in iterations 2 and
  3 with rule edits about "primary use case decides," but the
  rule edits depend on lexical pattern recognition that the
  prompt's rules section captures imperfectly. Auditor verdicts
  on the rule edits were `categorical` for `(edit-2, category)`
  and `(edit-3, category)`.

**4.2 Strikethrough-price extraction errors**

- **Primary field:** `price`
- **Rows in cluster:** row_019 (test partition; placeholder)
- **Description:** descriptions where the strikethrough
  formatting was lost in the input pipeline; the prompt
  extracts the strikethrough price as the current price.
- **Why this cluster persists:** the rule "extract the current
  price, not the strikethrough" depends on the input preserving
  the strikethrough formatting; when the input pipeline strips
  it, the prompt has no signal. Out-of-scope for prompt
  optimization; flagged for the data-pipeline team.

**4.3 Title canonicalization edge cases**

- **Primary field:** `title`
- **Rows in cluster:** row_021 (test partition; placeholder)
- **Description:** product-line + variant naming where the
  catalog publishes the variant's canonical name but the
  description leads with the product-line name.
- **Why this cluster persists:** addressed in iteration 4 with
  a rule edit; the residual is one row where the canonical
  name itself is contested (the catalog and the description
  disagree on capitalization). Auditor verdict on the edit
  was `categorical` for `(edit-4, title)`.

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
run_02     1     category       categorical
run_02     2     category       categorical
run_03     3     category       categorical
run_03     3     in_stock       row-specific
run_04     4     title          categorical
```

(One edit-3 across iteration 3 affected both `category` and
`in_stock`; the auditor returned per-edit-per-field verdicts
per [`DESIGN.md`](../../../../DESIGN.md) §7.1.1 per-field
methodology application layer. The `(edit-3, in_stock)`
verdict was `row-specific`; the user added a `plan.md` §11
entry with `auditor override [edit-3.in_stock]` per the
v0.2 bracketed-token convention; the override propagates
into §7.5 below.)

**Auditor information-isolation invariant: preserved.**

---

## 6. Decision and recommendation

**Recommendation:** `ship-with-caveats`

**Reasoning (deterministic decision tree per
[`phases/spp-finalize.md`](../../../../skills/run/phases/spp-finalize.md)
§4 step 7):**

- Test aggregate (0.83) < headline criterion (`aggregate (min) ≥
  0.85`).
- BUT `dev_test_delta` is 0.05; the dev set was a borderline-
  fair estimator.
- Per-field floor compliance: `category` is `unmet` on test
  (0.83 < 0.85).

The deterministic tree's branches: test-aggregate < headline +
dev_test_delta ≤ 0.05 → `do-not-ship`. The placeholder values
land on this branch.

The user revises at G6 to `ship-with-caveats` with the
rationale that the smart-home cluster (§4.1) is a known
class the catalog team can mitigate downstream via the
manual-review queue, and the price cluster (§4.2) is
out-of-scope for prompt optimization. The category floor
unmet status surfaces in §7.5 below.

(Real REPORTs use the deterministic tree's recommendation as
drafted; the user's revision at G6 — when warranted — replaces
it with the rationale prepended to this section.)

---

## 7. Limitations and caveats

### 7.1 Model lock-in

Optimized against `placeholder-model-v1`. Cross-model fragility
per [`DESIGN.md`](../../../../DESIGN.md) §2.2.

### 7.2 Baseline scope and provenance

80 rows; placeholder data per `BASELINE_QUALITY_NOTE` in
[`config/plan.md`](../../config/plan.md) §6. Per-field
calibration ran on each of the four OUTPUT_SCHEMA fields per
[`baseline-quality`](../../../../skills/run/sub-skills/baseline-quality/SKILL.md)
SKILL.md §3 v0.2 per-field application; consolidated verdict
is `ready` after one revise-then-re-validate cycle on the
`category` field's per-field definition.

### 7.3 Persistent failure clusters

See §4.

### 7.4 Loop interruption posture (v1)

v1 does not support mid-iteration resumption per
[`DESIGN.md`](../../../../DESIGN.md) §7.1; this loop terminated
cleanly via SUCCESS.md.

### 7.5 Acknowledged-risk overrides

- **`category` floor unmet on test** (`macro_F1` = 0.83;
  floor = 0.85). Surfaced per
  [`templates/REPORT.md.template`](../../../../skills/run/templates/REPORT.md.template)
  §7.5; the catalog team accepts the risk because the
  smart-home misclassification cluster (§4.1) is mitigable
  downstream via the manual-review queue.
- **`auditor override [edit-3.in_stock]`** (run_03). Reason
  recorded in [`config/plan.md`](../../config/plan.md) §11
  (placeholder; in a real run this would carry the user's
  rationale for accepting the row-specific edit on `in_stock`).

### 7.6 Other caveats

The price-extraction cluster (§4.2) is out-of-scope for prompt
optimization; the data-pipeline team owns the strikethrough-
preservation work.

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

(Real REPORTs carry git commit hashes computed at the named
moments; this skeleton's placeholders are pedagogical.)
