# spp plan — multi-field-extraction-example

**Created:** 2026-05-10

**Designer session:** placeholder-designer-session

**Plan version:** v1

---

## 1. Task overview

**One-sentence description:** Extract a four-field structured object
(title, price, category, in_stock) from each product description in
the catalog ingest pipeline.

**Audience for the prompt's output:** the catalog-ingest service that
indexes new product listings into the search backend.

**Problem statement** (placeholder; this example is a skeleton per
DESIGN.md §7.2):
The ingest pipeline currently lands new listings as unstructured
descriptions and needs structured fields to drive search filters,
stock checks, and price-range routing. Manual extraction by the
catalog team is too slow at the volume the pipeline now sees;
inconsistent field values block the search relevance work
downstream.

---

## 2. Output schema and per-field definitions

**Output schema** (per DESIGN.md §7.1.1 schema layer; JSON Schema
draft 2020-12; YAML surface chosen during schema-designer
consultation):

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "ProductListingExtraction"
type: "object"
additionalProperties: false
required: ["title", "price", "category", "in_stock"]
properties:
  title:
    type: "string"
    description: "Display title for the catalog listing."
  price:
    type: "number"
    minimum: 0
    description: "Listing price in the catalog's primary currency."
  category:
    type: "string"
    enum: ["apparel", "electronics", "home", "media", "outdoor"]
    description: "Top-level catalog category; routes downstream search."
  in_stock:
    type: "boolean"
    description: "Whether the listing is currently available for purchase."
examples:
  - title: "Lightweight Hooded Jacket"
    price: 89.50
    category: "apparel"
    in_stock: true
```

**Per-field definitions** (one sub-block per OUTPUT_SCHEMA field;
placeholder examples per DESIGN.md §7.2):

- **`title`:** the product's catalog display title. Should be the
  canonical product name as the catalog publishes it, not a
  promotional tagline or a SKU.
  - Positive examples: `"Lightweight Hooded Jacket"`,
    `"Stainless Steel French Press 8-Cup"`.
  - Borderline examples: descriptions that lead with a promotional
    tagline (e.g., `"Best-selling — Lightweight Hooded Jacket"`);
    extract the canonical name without the tagline.
  - Edge cases: descriptions that name a product line and a
    specific variant separately (e.g., `"Hood Series jacket,
    lightweight variant"`); the catalog title is the variant's
    canonical name.
- **`price`:** current listing price. If the description shows a
  strikethrough or sale-through price, extract the currently-
  applicable price (the one a customer would pay), not the
  strikethrough.
  - Positive examples: `89.50`, `12.99`.
  - Borderline examples: descriptions with a price range
    (e.g., `"$80–$100"`); extract the lower bound.
  - Edge cases: descriptions with no price stated; in this case
    the row is malformed and should be flagged at labeling time
    rather than extracted.
- **`category`:** one of `apparel`, `electronics`, `home`,
  `media`, `outdoor`. The catalog's top-level taxonomy. Routes
  downstream search — a misroute is unrecoverable without
  re-running extraction on the whole catalog.
  - Positive examples: jacket → `apparel`; french press → `home`;
    paperback book → `media`.
  - Borderline examples: smart-home electronics (e.g., a
    Wi-Fi-enabled coffee maker); the rule: primary use case
    decides — if it's a coffee maker first, `home`; if it's a
    smart-hub first, `electronics`.
  - Edge cases: dual-purpose items (e.g., a camping stove that
    doubles as a kitchen burner); the rule: primary marketed
    use decides.
- **`in_stock`:** boolean. `true` if the description names current
  availability or shipping; `false` if the description names
  back-order, sold-out, or coming-soon status.
  - Positive examples: descriptions with phrases like "ships in
    2 days" → `true`; "back-order, expected June" → `false`.
  - Borderline examples: descriptions with "limited stock";
    treat as `true` unless explicitly marked sold-out.
  - Edge cases: descriptions with no availability information;
    default to `true` (the catalog's most common state) and
    flag at labeling time for the labeler to resolve via the
    upstream inventory system.

**Known borderline cases:**
The `category` field's smart-home and dual-purpose edge cases are
the largest known borderline class. Approximately 5-8% of listings
land in this region and require the per-field-definition rules
above to resolve. Flagged for `baseline-quality` calibration.

---

## 3. Success criteria

**Production decision rule** (placeholder):
The ingest pipeline indexes the listing only if the structured
extraction passes a downstream sanity check (price > 0;
`category` ∈ enum). Listings with `in_stock = false` are indexed
but flagged for an out-of-stock filter; listings with `category`
unrouteable trigger a manual-review queue.

**Headline success criterion** (the single aggregate number the user
cares about most; per DESIGN.md §7.1.1 metrics layer decision 4):
`aggregate (min) ≥ 0.85` on dev — the worst-performing field's
normalized metric must clear 0.85 to advance.

**Acceptable trade-offs** (placeholder):
A `price` MAE of $5 is acceptable in exchange for `category` macro_F1
≥ 0.85 (`category` floor). The catalog team would rather see a
slightly imprecise price extraction with correct category routing
than the inverse — misrouted listings are unrecoverable; price
discrepancies surface at customer-facing time and can be corrected
manually via the price-correction queue.

---

## 4. Per-field metrics, aggregate strategy, and floors

Per DESIGN.md §7.1.1 metrics layer.

**Aggregate strategy:**

- **`AGGREGATE_STRATEGY`:** `min`
- **`AGGREGATE_WEIGHTS`:** `null` (only set when strategy is `weighted`)
- **`AGGREGATE_RATIONALE`:** the four per-field metrics live on
  heterogeneous scales — `exact_match` ∈ {0, 1}, `MAE` ∈ [0, ∞),
  `macro_F1` ∈ [0, 1], `F1` ∈ [0, 1]. `metric-design` SKILL.md §3.2's
  strawman recommendation for heterogeneous metric types is
  `min-over-fields` because `macro` would dimensionally mismatch
  (averaging a value in [0, ∞) with values in [0, 1] produces a
  meaningless aggregate). `min` after per-field normalization to
  [0, 1] (MAE normalized as `1 - MAE / MAX_PRICE` with `MAX_PRICE`
  set to the catalog's 99th-percentile price) gives the worst-
  performing field as the headline number, which matches the
  downstream operational intuition: "every field needs to clear
  its bar."

**Per-field metrics** (one sub-block per OUTPUT_SCHEMA field):

- **Field `title`:**
  - `METRIC_NAME`: `exact_match`
  - `METRIC_RATIONALE`: `title` is a `string` field with no
    enumerable value space; `metric-design` SKILL.md §3.1's
    type-suggestion path for `string` fields lands on
    `exact_match`. The catalog team accepts that minor
    capitalization or spacing differences will count as
    mismatches; the labeler is responsible for canonicalizing
    titles at labeling time.
  - `METRIC_INDEPENDENCE_NOTE`: `exact_match` against
    ground-truth labels for field `title` — model-agnostic;
    no LLM is involved in scoring.
- **Field `price`:**
  - `METRIC_NAME`: `MAE`
  - `METRIC_RATIONALE`: `price` is a `number` field;
    `metric-design` SKILL.md §3.1's type-suggestion for `number`
    fields offers `MAE` or `RMSE`. The user picks `MAE` because
    a single outlier (a malformed listing) shouldn't dominate
    the metric — `RMSE`'s squared term would over-weight
    outliers in a domain where outliers are usually data-quality
    issues, not extraction failures.
  - `METRIC_INDEPENDENCE_NOTE`: `MAE` between predicted and
    ground-truth `price` values — model-agnostic.
- **Field `category`:**
  - `METRIC_NAME`: `macro_F1`
  - `METRIC_RATIONALE`: `category` is an `enum` with 5 values;
    `metric-design` SKILL.md §3.1's decision-tree branch for
    multi-class enums lands on `macro_F1` because per-class
    recall matters — a single under-represented class (e.g.,
    `outdoor`) shouldn't be hidden by the dominant classes
    (`apparel`, `electronics`).
  - `METRIC_INDEPENDENCE_NOTE`: `macro_F1` against ground-truth
    `category` labels — model-agnostic.
- **Field `in_stock`:**
  - `METRIC_NAME`: `F1`
  - `METRIC_RATIONALE`: `in_stock` is a `boolean`;
    `metric-design` SKILL.md §3.1's type-suggestion for binary
    fields offers `F1` (positive class is "in stock"). The user
    accepts; out-of-stock listings should index but be
    correctly flagged.
  - `METRIC_INDEPENDENCE_NOTE`: `F1` against ground-truth
    `in_stock` labels — model-agnostic.

**Per-field floors** (optional; one sub-block per field that
carries a floor):

- **Field `category`:**
  - `FLOOR`: `0.85` (on `macro_F1`)
  - `FLOOR_RATIONALE`: `category` drives downstream search
    routing. A misroute is unrecoverable without re-running
    extraction on the whole catalog (the search index keys
    on `category`; misrouted listings don't surface for the
    intended user query). The 0.85 floor reflects the
    catalog team's stated bar for routing quality.

(No floors on `title`, `price`, `in_stock` — those fields are
recoverable downstream: `title` corrections happen at
customer-facing time via the catalog-edit queue; `price`
discrepancies surface via the price-correction queue;
`in_stock` is reconciled against the inventory system before
the listing reaches a customer.)

---

## 5. Model and lock-in posture

**Production model identifier:** `placeholder-model-v1`

**Lock-in posture:** locked

**Cross-model fragility plan:** the catalog team locks to one
model per release; if a swap is required, the team re-runs
`/spp-loop` against the new model and re-finalizes.

---

## 6. Baseline

**Data source:** placeholder — the example does not ship real
data per DESIGN.md §7.2.

**Language coverage:** monolingual

**Preprocess mapping:** identity (data already canonical)

**Target baseline size:** 80 rows

**Class balance target:** preserve catalog prevalence per
`category` (approximately 35% apparel, 25% electronics, 20% home,
12% media, 8% outdoor in the catalog at large; the baseline
oversamples outdoor and media to N≥10 per class for stable
per-class statistics).

**Label provenance:** single labeler from the catalog team with
documented criteria; the criteria are the per-field definitions
in §2 above.

**Status:** complete (placeholder for this example).

**baseline-quality review:** placeholder; in a real run this
section would carry the `BASELINE_QUALITY_NOTE` from the
sub-skill's per-field calibration (see [`walkthrough.md`](../walkthrough.md)
`/spp-baseline` section for the protocol walk).

---

## 7. Splits

**Split ratios:** train 60% / dev 20% / test 20%

**Random seed:** 42

**Stratification key:** `category`

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

**Adversary:** off (this example focuses on per-field
methodology; adversary is exercised by the hair-loss-relevance
example).

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

The smart-home and dual-purpose edge cases for `category` are
the dominant known borderline class. Resolved in §2's per-field
definition; flagged for `baseline-quality` calibration. No other
open questions surfaced during consultation.

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

1. All `{{...}}` placeholders are resolved (no remaining `{{` or
   `}}` outside this validation list).
2. `TASK_NAME` is kebab-case, contains no spaces or slashes.
3. `OUTPUT_SCHEMA` passes the mechanical layer (per
   `schema-designer` SKILL.md §3.4).
4. `METRIC_NAME[f]` for each OUTPUT_SCHEMA field `f` is one of the
   allowed values listed in `metric-design` SKILL.md §6.
5. `METRIC_INDEPENDENCE_NOTE[f]` is present and non-empty for each
   OUTPUT_SCHEMA field.
6. `MODEL_IDENTIFIER` is the exact env-var string with no
   aliasing.
7. `SACRED_TEST_ACK` literally equals `acknowledged`.
8. `AUDITOR_CONFIG` literally equals
   `per-iteration, no-score-access`.
9. `TRAIN_PCT + DEV_PCT + TEST_PCT == 100`.
10. `SPP_SCOPE` is one of the documented values.
11. Every gate row in §9 has a non-empty `Approval phrase` cell.
12. The plan revision log has at least one row.
