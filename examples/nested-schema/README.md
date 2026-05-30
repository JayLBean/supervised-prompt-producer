# Example — nested-schema

A canonical v0.2 skeleton example for **hierarchical labels via JSON
Schema conditional structures**. Demonstrates how `spp`'s OUTPUT_SCHEMA
contract absorbs hierarchical taxonomies — a top-level enum plus a
sub-category whose value space depends on the top-level — without
introducing separate bookkeeping. The placeholder domain is
support-ticket categorization with `top_level ∈ {billing, technical,
account, other}` and per-branch `sub_category` enums.

This is a skeleton in the [`DESIGN.md`](../../DESIGN.md) §7.2 sense
— file structure and walkthrough are real; data, baseline labels,
and prompt content are placeholder. The support-ticket domain is
generic and pedagogically clear; it does not represent any real
source-project content.

## Runnable scoring configs (v0.4)

`config/` ships machine-readable scoring configs derived from this
plan's §2/§4, which drive the K>1 runner (DESIGN.md §7.1.5):

- `schema.json` — the OUTPUT_SCHEMA (`inference.py --schema`). The
  conditional `allOf` value space stays a schema concern; the runner
  scores `sub_category` over its ground-truth values directly, as the
  plan specifies.
- `field_metrics.json` — `macro_f1` on both `top_level` and
  `sub_category` for `eval.py --field-metrics`.
- `aggregate.json` — `macro` (both fields are `[0,1]`, homogeneous).
- `floors.json` — the `top_level` floor (`0.90`) for
  `EARLY_STOP_FLOOR_UNMET`; `sub_category` carries no floor.

These are exercised end to end (synthetic predictions, no model call)
in `skills/run/scripts/tests/test_examples_multifield.py`.

## What this example teaches

The example exercises four v0.2 buckets explicitly and two
implicitly:

- **Bucket 1 — schema layer.** OUTPUT_SCHEMA with conditional
  structure (`if/then/else`) per
  [`DESIGN.md`](../../DESIGN.md) §7.1.1's "Adjacent output shapes
  the schema layer subsumes" subsection. The schema declares
  `top_level` as an `enum` and uses `allOf` with conditional
  `if/then` clauses to constrain `sub_category`'s value space
  per branch. Per-field definitions in
  [`config/plan.md`](config/plan.md) §2 cover both fields with
  the conditional relationship explained.
- **Bucket 2 — metrics layer.** Per-field metrics for both fields
  (`macro_F1` for `top_level` and `macro_F1` for `sub_category`);
  aggregate strategy `macro` (homogeneous metric types — both
  fields produce values in [0, 1]); a per-field floor on
  `top_level` (`macro_F1 ≥ 0.90`) because top-level routing is
  the unrecoverable decision.
- **Bucket 3 — per-field methodology application layer.**
  [`runs/placeholder-model/REPORT.md`](runs/placeholder-model/REPORT.md)
  carries per-field final scores and trajectories for both
  fields. [`walkthrough.md`](walkthrough.md) shows how
  field-attributed discrepancy clusters surface — the canonical
  pattern for hierarchical tasks is "rows where `top_level` was
  right but `sub_category` was wrong" (and vice versa).
- **Bucket 5 — compat layer.** [`config/plan.md`](config/plan.md)
  uses the v0.2 template surface; the conditional schema
  structure renders inside the YAML `OUTPUT_SCHEMA` block in
  §2.

Buckets 4 (sub-skill ordering — `schema-designer` runs before
`metric-design` per data dependency, and the conditional
structure is what `metric-design`'s per-field protocol consumes
when scoping each field's metric) and 6 (locked-invariants
inventory) are exercised implicitly.

## Relationship to the feature-group splitting principle

This example exemplifies the **unified-multi-field exception case**
under the feature-group prompt splitting principle
([`DESIGN.md`](../../DESIGN.md) §10 glossary entry "Feature-group
prompt splitting") in a specific shape: the two fields
(`top_level`, `sub_category`) have **hierarchical conditional
reasoning** where `sub_category`'s value space is conditional on
`top_level`'s value (via JSON Schema `allOf` + `if/then` clauses).
Splitting would fragment the conditional reasoning across two
prompts and require the sub-category prompt to read the top-level
prompt's output — more orchestration overhead than savings, and the
joint reasoning ("once I know it's billing, the sub-category enum
shrinks to a meaningful three values") lives most naturally inside
one prompt with the conditional schema doing the constraint work.

For the principle's **default case** (feature-group decomposition
where reasoning patterns are distinct across groups without
hierarchical conditional dependencies), see
[`examples/feature-group-split/`](../feature-group-split/).

## Cross-references

- [`DESIGN.md`](../../DESIGN.md) §7.1.1 fixtures layer (the
  bucket-7 design contract for this example) and §7.1.1 schema
  layer's "Adjacent output shapes" subsection (the design
  commitment this example operationalizes).
- [`schema-designer`](../../skills/run/sub-skills/schema-designer/SKILL.md)
  SKILL.md §3 — produces the OUTPUT_SCHEMA with conditional
  structure.
- [`metric-design`](../../skills/run/sub-skills/metric-design/SKILL.md)
  SKILL.md §3 — produces per-field metrics for both fields and
  the aggregate-strategy choice.
- [`baseline-quality`](../../skills/run/sub-skills/baseline-quality/SKILL.md)
  SKILL.md §3 — calibrates per field; for `sub_category`, the
  calibration runs conditional on `top_level`'s value (the
  reviewer checks each per-branch sub-category enum makes
  sense given its top-level).

## Reading order

1. Start with [`walkthrough.md`](walkthrough.md). It walks the
   four phases for this conditional-schema task shape.
2. Read [`config/plan.md`](config/plan.md) — note the `allOf`
   conditional structure inside the OUTPUT_SCHEMA block.
3. Skim [`data/baseline.csv`](data/baseline.csv); note that
   `sub_category` values respect the conditional structure
   (billing rows only carry billing sub-categories, etc.).
4. Skim [`prompts/prompt_v01.md`](prompts/prompt_v01.md); the
   rules section addresses the conditional relationship
   directly.
5. End at [`runs/placeholder-model/REPORT.md`](runs/placeholder-model/REPORT.md)
   for the per-field REPORT shape with two fields.

All numbers in the REPORT are placeholder; the example does
not represent a real run.
