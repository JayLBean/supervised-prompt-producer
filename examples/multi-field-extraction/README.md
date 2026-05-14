# Example — multi-field-extraction

A canonical v0.2 skeleton example for **multi-field structured-output
classification**. Demonstrates how `spp`'s methodology generalizes
when each baseline row resolves to a structured object with several
fields rather than a single categorical label. The example walks a
placeholder product-listing-extraction task with four fields of
diverse JSON Schema types: a `string` `title`, a `number` `price`,
an `enum` `category`, and a `boolean` `in_stock`.

This is a skeleton in the [`DESIGN.md`](../../DESIGN.md) §7.2 sense
— file structure and walkthrough are real; data, baseline labels,
and prompt content are placeholder. The product-listing domain is
generic and pedagogically clear; it does not represent any real
source-project content.

## What this example teaches

The example exercises four v0.2 buckets explicitly and two
implicitly:

- **Bucket 1 — schema layer.** OUTPUT_SCHEMA with K=4 fields of
  diverse JSON Schema types (`string`, `number`, `enum`,
  `boolean`); per-field definitions in [`config/plan.md`](config/plan.md)
  §2.
- **Bucket 2 — metrics layer.** Per-field metric selection
  (`exact_match` for `title`, `MAE` for `price`, `macro_F1` for
  `category`, `F1` for `in_stock`); aggregate strategy `min`
  (heterogeneous metric scales force `min-over-fields` per
  [`metric-design`](../../skills/run/sub-skills/metric-design/SKILL.md)
  SKILL.md §3.2's strawman); a per-field floor on `category`
  (`macro_F1 ≥ 0.85`) because category drives downstream search
  routing.
- **Bucket 3 — per-field methodology application layer.**
  [`runs/placeholder-model/REPORT.md`](runs/placeholder-model/REPORT.md)
  carries per-field final scores, per-field iteration trajectories,
  and a floor-compliance row per field. [`walkthrough.md`](walkthrough.md)
  shows how field-attributed discrepancy clusters surface during
  `/spp-loop` and how the auditor's per-edit-per-field verdicts
  operate.
- **Bucket 5 — compat layer.** [`config/plan.md`](config/plan.md)
  uses the v0.2 template surface (`OUTPUT_SCHEMA` block;
  per-field metric sub-blocks; aggregate-strategy block;
  per-field floor sub-block).

Buckets 4 (sub-skill ordering — `schema-designer` runs before
`metric-design` per data dependency) and 6 (locked-invariants
inventory) are exercised implicitly: every v0.2 example walks
the consultation order and inherits the locked methodology
guarantees.

## Relationship to the feature-group splitting principle

This example exemplifies the **unified-multi-field exception case**
under the feature-group prompt splitting principle
([`DESIGN.md`](../../DESIGN.md) §10 glossary entry "Feature-group
prompt splitting"). All four fields (`title`, `price`, `category`,
`in_stock`) share input dependency on the listing text — every
field is extracted from the same description, with no
sub-group-specific input slicing. Splitting would mean the same
listing text is read by four separate prompts, paying four model
invocations' worth of cost with no corresponding gain in focused
`<rules>` content or auditor scoping (the reasoning operation —
"read this product description and extract a field" — is the same
shape across all four fields). The bucket-7 design intentionally
chose this domain to exercise multi-field bookkeeping without
requiring decomposition.

For the principle's **default case** (feature-group decomposition
where reasoning patterns differ across groups), see
[`examples/feature-group-split/`](../feature-group-split/).

## Cross-references

- [`DESIGN.md`](../../DESIGN.md) §7.1.1 fixtures layer (the
  bucket-7 design contract for this example).
- [`schema-designer`](../../skills/run/sub-skills/schema-designer/SKILL.md)
  SKILL.md §3 — the consultative path that produces the
  OUTPUT_SCHEMA in [`config/plan.md`](config/plan.md) §2.
- [`metric-design`](../../skills/run/sub-skills/metric-design/SKILL.md)
  SKILL.md §3 — the per-field protocol that produces the
  per-field metric sub-blocks in [`config/plan.md`](config/plan.md)
  §4 and the aggregate-strategy choice.
- [`baseline-quality`](../../skills/run/sub-skills/baseline-quality/SKILL.md)
  SKILL.md §3 — the per-field calibration applied at G2 in
  [`walkthrough.md`](walkthrough.md)'s `/spp-baseline` section.

## Reading order

1. Start with [`walkthrough.md`](walkthrough.md). It walks the
   four phases (`/spp-init`, `/spp-baseline`, `/spp-loop`,
   `/spp-finalize`) for this task shape.
2. Read [`config/plan.md`](config/plan.md) — the v0.2 contract
   the methodology produces.
3. Skim [`data/baseline.csv`](data/baseline.csv) for the data
   shape (one column per OUTPUT_SCHEMA field, plus `row_id`
   and `body`).
4. Skim [`prompts/prompt_v01.md`](prompts/prompt_v01.md) for
   the six-section prompt skeleton with structured output.
5. End at [`runs/placeholder-model/REPORT.md`](runs/placeholder-model/REPORT.md)
   for the v0.2 per-field REPORT shape.

All numbers in the REPORT are placeholder; the example does
not represent a real run.
