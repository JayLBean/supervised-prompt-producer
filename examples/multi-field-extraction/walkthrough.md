# Walkthrough — multi-field-extraction

A narrative walk through `spp`'s four phases for a multi-field
structured-output classification task. The placeholder domain is
product-listing extraction: each input is a product description
(`body` column in the baseline) and the prompt produces a
structured object with four fields. All numbers, examples, and
specific decisions in this walkthrough are illustrative; the
example is a skeleton per [`DESIGN.md`](../../DESIGN.md) §7.2.

---

## Task framing

Each row is a product description in plain text. The prompt's
output is a JSON object with four fields:

- **`title`** (`string`) — the product's display title as it
  should appear in the catalog.
- **`price`** (`number`) — the product's price in the catalog's
  primary currency.
- **`category`** (`enum`) — one of `apparel`, `electronics`,
  `home`, `media`, `outdoor`. Drives downstream search routing
  and filtering.
- **`in_stock`** (`boolean`) — whether the listing is currently
  available for purchase.

This shape is structured-output classification, not single-output
classification: the unit of extraction per row is the four-field
object, not a single label. The methodology principles are
unchanged from v0.1.0; the bookkeeping generalizes per
[`DESIGN.md`](../../DESIGN.md) §7.1.1's seven-bucket sequence.

---

## `/spp-init` walkthrough

The designer agent walks the user through the v0.2 consultation
flow. Two sub-skills produce the `plan.md` content for §2 and
§4; per [`DESIGN.md`](../../DESIGN.md) §7.1.1 sub-skill ordering
layer (bucket 4), `schema-designer` runs first because
`metric-design`'s per-field protocol consumes OUTPUT_SCHEMA's
fields.

**`schema-designer` consultation (Path 1 — consultative).** The
user describes the task in prose. The designer reads the repo
context, builds a strawman OUTPUT_SCHEMA, and the user corrects.
The result is a JSON Schema document (draft 2020-12) rendered
as YAML inside [`config/plan.md`](config/plan.md) §2. The
schema declares all four fields as `required`, with `type` on
each, an `enum` on `category`, and an example output that
validates against the schema (mechanical-layer rule 5 per
[`schema-designer`](../../skills/run/sub-skills/schema-designer/SKILL.md)
SKILL.md §3.4). The judgment-driven layer (`schema-designer`
SKILL.md §3.5) confirms the field names are clear, borderline
examples are concrete, and the schema is no broader than the
task needs. Verdict: `ready`. G1's dual check
(approval-substring + schema-designer verdict; per
[`DESIGN.md`](../../DESIGN.md) §7.1.1 sub-skill ordering layer)
advances on the user's approval phrase.

**`metric-design` consultation (per-field protocol).** Per
[`metric-design`](../../skills/run/sub-skills/metric-design/SKILL.md)
SKILL.md §3, the per-field metric selection runs once per
OUTPUT_SCHEMA field:

- `title` is a `string` field with no enumerable value space;
  the §3.1 type-suggestion path lands on `exact_match`.
- `price` is a `number` field; the user accepts the
  type-suggestion `MAE` (residual matters more than squared
  residual for this catalog's price range).
- `category` is a small `enum` (5 values); the §3.1 decision-
  tree branch lands on `macro_F1` (more than two classes;
  per-class recall matters because misroutes are unrecoverable
  downstream).
- `in_stock` is a `boolean`; the §3.1 type-suggestion path
  lands on `F1` (binary; positive class is "in stock").

**Aggregate-strategy consultation (§3.2).** The four metrics
are heterogeneous — `exact_match` ∈ {0, 1}, `MAE` ∈ [0, ∞),
`macro_F1` ∈ [0, 1], `F1` ∈ [0, 1]. `metric-design` §3.2's
strawman recommends `min` for heterogeneous types because
`macro` would dimensionally mismatch (averaging a value in
[0, ∞) with values in [0, 1] produces a meaningless number).
The user accepts; `AGGREGATE_STRATEGY` is `min`.
`AGGREGATE_RATIONALE` documents the dimensional-mismatch
finding. The headline criterion (`plan.md` §3) is
`aggregate (min) ≥ 0.85` on dev — the worst-performing
field's normalized metric must be ≥ 0.85 to clear the
target.

**Per-field-floor consultation (§3.3).** Most fields don't
warrant a floor. The user identifies `category` as
required-and-unrecoverable: a wrong category routes the
listing to the wrong downstream search index, and there's no
post-hoc correction step. Floor on `category`:
`macro_F1 ≥ 0.85`. Other fields carry no floor.

**G1 advances.** [`config/plan.md`](config/plan.md) is
written via the v0.2 template surface ([`DESIGN.md`](../../DESIGN.md)
§7.1.1 compat layer): §2 holds OUTPUT_SCHEMA + per-field
definitions; §3 holds the aggregate-metric headline target;
§4 holds the AGGREGATE_STRATEGY block, four per-field metric
sub-blocks, and one per-field floor sub-block on `category`.

---

## `/spp-baseline` walkthrough

The phase reads `plan.md` §2's OUTPUT_SCHEMA and per-field
definitions. The user labels ~80 rows; each row gets a value
per field, persisted as four columns in `data/baseline.csv`
(plus `row_id` and `body`). At step 7 the phase invokes
[`baseline-quality`](../../skills/run/sub-skills/baseline-quality/SKILL.md)
with per-field calibration ([`baseline-quality`](../../skills/run/sub-skills/baseline-quality/SKILL.md)
SKILL.md §1 v0.2 paragraph; bucket 5).

The §3 review questions run per OUTPUT_SCHEMA field:

- §3.1 (drift) on `title`: sample 8 rows; all articulations
  match the field's per-field definition. ✓
- §3.1 (drift) on `category`: sample 8 rows; one row's
  articulation diverges (the labeler used "user-perceived
  category" rather than the field's "catalog category"
  rule). 1 of 8 = 12.5%, below the 25% threshold; field
  signal is `revise`.
- §3.1 (drift) on `in_stock` and `price`: clean.
- §3.3 (intuition-vs-rule) on `category`: of the 8
  borderlines, 5 are rule-based, 3 are intuition-based.
  3 of 8 = 37.5%, above the 25% threshold; field signal
  is `not-ready`.
- §3.5 (calibration, solo) per field: clean for `title`,
  `price`, `in_stock`; `category` self-disagreement is
  3 of 15 = 20% (`revise` range, corroborates §3.3).

**Within-field synthesis** (per [`baseline-quality`](../../skills/run/sub-skills/baseline-quality/SKILL.md)
SKILL.md §3.7):

| Field | Within-field verdict |
|---|---|
| `title` | `ready` |
| `price` | `ready` |
| `category` | `not-ready` |
| `in_stock` | `ready` |

**Cross-field consolidation:** any `not-ready` field
dominates → baseline-as-a-whole verdict is `not-ready`. G2
does not advance on the user's G2 approval phrase alone.

The user refines the `category` field's per-field definition
in [`config/plan.md`](config/plan.md) §2 (adds an explicit
"catalog category, not user-perceived category" clause) and
relabels the 3 affected rows. Re-invoking
`baseline-quality`: per-field re-runs return `ready` for
`category`; baseline verdict is `ready`. G2 advances.

Splits generated per `plan.md` §7; G3 advances on the user's
G3 approval phrase.

---

## `/spp-loop` walkthrough

Per [`DESIGN.md`](../../DESIGN.md) §7.1.1 per-field methodology
application layer (bucket 3), the loop is per-field-aware
end-to-end.

**Per-iteration scoring (`/spp-loop` step 7).** Each iteration
computes per-field metrics on dev: `exact_match` for `title`,
`MAE` for `price`, `macro_F1` for `category`, `F1` for
`in_stock`. The aggregate is `min(exact_match_title, 1 -
MAE_price/MAX_PRICE, macro_F1_category, F1_in_stock)` — each
field's metric normalized to [0, 1] before applying `min`.
[`runs/placeholder-model/run_NN/eval.json`](runs/placeholder-model/)
carries the v0.2 shape: `per_field` (one entry per field with
auxiliary structures — confusion matrix for `macro_F1`,
residual distribution for `MAE`, etc.); `aggregate` (the `min`
value, strategy, weights `null`); `floor_compliance` (one
row, `category`, met/unmet).

**Discrepancy clustering (step 8).** The discrepancy subagent
reads any-field-disagreed dev rows. Clusters are field-
attributed: a cluster might surface as "rows where `category`
was wrong because of brand-name confusion" (primary field:
`category`; rows in cluster: by `row_id`); another might
surface as "rows where `price` was extracted from a strikethrough
sale price rather than the current price" (primary field:
`price`). Cross-field correlations are visible in the
discrepancy subagent's analysis prose (e.g., when `category =
electronics` errors correlate with `in_stock = false` —
listings that are out-of-stock often have decayed
descriptions).

**Auditor verdicts (step 11).** The auditor runs per-edit-per-
field. A rule edit that adds a "if the description mentions
'tee', label as `apparel` regardless of brand-name confusion"
clause has `target_fields: [category]`; the auditor returns
one verdict (e.g., `categorical`) for `(edit-1, category)`.
A rule edit that affects multiple fields gets multiple
verdicts. Mixed verdicts trigger gate-blocking on the non-
`categorical` (edit, field) pairs.

**Gate G4 (step 12).** Advances iff every (edit, field) pair
is `categorical` OR has a `plan.md` §11 entry whose Reason
contains `auditor override` plus the bracketed `[edit-N.field-
name]` token covering that pair (per
[`DESIGN.md`](../../DESIGN.md) §7.1.1 per-field methodology
application layer; bucket 3). K=1 backward compat: an
unscoped `auditor override` covers the lone field implicitly;
under K=4 each non-`categorical` pair must be explicitly
named.

**Stop conditions (step 13).** Plateau and overfitting-guard
checks run on the aggregate `min` value across iterations.
Per-field movement is informational only; per-field metrics
do not gate the stop discipline (per
[`DESIGN.md`](../../DESIGN.md) §7.1.1 metrics layer).

**Termination (step 15).** If the aggregate plateaus at-or-
above target AND every per-field floor is met, the runner
writes `SUCCESS.md`. If the aggregate plateaus at-or-above
target BUT the `category` floor is unmet, the runner writes
`EARLY_STOP.md` with reason `early_stop_floor_unmet` per
bucket 3, listing `category` as the unmet floor.

---

## `/spp-finalize` walkthrough

The phase reads `plan.md` §2 OUTPUT_SCHEMA, §3 aggregate
target, §4 per-field metric sub-blocks + aggregate-strategy
block + per-field floor sub-blocks (per [`DESIGN.md`](../../DESIGN.md)
§7.1.1 compat layer; bucket 5). Pre-condition 6 accepts
`SUCCESS.md` directly; if the loop terminated as
`EARLY_STOP.md/early_stop_floor_unmet`, pre-condition 6's
v0.2 advancement branch surfaces the unmet floors and asks
the user to confirm sacred-test-set advancement.

**Step 4 — test-set metrics.** Per-field metrics computed on
the test partition; the aggregate `min` value computed across
the four per-field test metrics; floor compliance checked
(`category` met or unmet on test). `test_eval.json` carries
the v0.2 shape.

**Step 5 — failure clusters.** Tagged with primary field per
bucket 3.

**Step 7 — REPORT generation.** Per
[`templates/REPORT.md.template`](../../skills/run/templates/REPORT.md.template)
§2.1 / §2.2 / §2.3, the REPORT carries per-field final
scores (one subsection per field with the field's primary
metric for test/dev/train, plus auxiliary structures), the
aggregate scores (with strategy and weights), and the
floor-compliance table. §3 carries per-field trajectories
plus the aggregate trajectory. §4 carries failure clusters
with primary-field tags. §6's deterministic decision tree
reads aggregate + floor compliance; if the `category` floor
was unmet on test, `ship-with-caveats` is the natural
recommendation, with the unmet floor surfaced in §7.5
acknowledged-risk overrides.

**Gates G5 / G6** are unchanged in shape; literal-string
matching per [`templates/plan.md.template`](../../skills/run/templates/plan.md.template)
§9.

---

## What this example teaches about the methodology

The v0.2 generalization is **bookkeeping** (the unit of
record is the per-field metric and the aggregate; the unit
of explanation is the field-attributed cluster), not
**methodology** (per-stage isolation, sacred test set,
verdict-enforced gates, six-section prompt structure all
carry over from v0.1.0 unchanged). The locked-invariants
inventory in [`DESIGN.md`](../../DESIGN.md) §7.1.1 (bucket 6)
documents exactly which guarantees survive verbatim and
which carry shape changes that preserve substance — this
example is the operational form of those preserved
substance commitments. A reader walking the four phases
above sees v0.1.0's discipline applied to a structured-
output task; the only new vocabulary is per-field /
aggregate / floor compliance, all of which collapse cleanly
to v0.1.0 under K=1 (single-output classification).
