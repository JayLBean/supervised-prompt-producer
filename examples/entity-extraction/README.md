# Example — entity-extraction

A skeleton example for **structured extraction** (`TASK_MODE =
extraction`; [`DESIGN.md`](../../DESIGN.md) §7.1.11, the v0.10 arc).
It demonstrates how `spp`'s methodology generalizes from classification
to extraction: each baseline row resolves to a **variable-cardinality
set of items** pulled from the text — zero, one, or many — rather than
a fixed label or a fixed object of fields.

The placeholder task pulls product and organization mentions (with
character offsets) and topic tags out of support-ticket messages. It is
a skeleton in the [`DESIGN.md`](../../DESIGN.md) §7.2 sense — the file
structure and walkthrough are real; the data and prompt content are
generic placeholders representing no real source project.

## Why this is extraction, not classification

The discriminating property is **cardinality**, not topic. "Route this
ticket to billing/not" would be classification (one choice from a fixed
list). "List every product and org mentioned" is extraction: the answer
is an open-ended set found in the text, and its size varies per row.
The designer records this as `TASK_MODE = extraction` during
`/spp-init`, and the schema-designer's mechanical rule 8 checks that the
recorded mode and the item-array OUTPUT_SCHEMA agree.

## Runnable scoring configs

`config/` ships machine-readable scoring configs that drive the K>1
runner (DESIGN.md §7.1.5), exercised end to end (synthetic predictions,
no model call) in
[`skills/run/scripts/tests/test_examples_multifield.py`](../../skills/run/scripts/tests/test_examples_multifield.py):

- `schema.json` — the OUTPUT_SCHEMA: an `entities` array of
  `{text, type, start, end}` objects and a `topics` array of strings.
- `field_metrics.json` — `entities` → `span_f1` (offset
  Intersection-over-Union ≥ 0.5, type-aware); `topics` →
  `extraction_f1` (text alignment, type-agnostic).
- `aggregate.json` — `macro` (unweighted mean of the two fields).
- `floors.json` — the `entities` floor (`0.80`): a run that routes
  topics well but highlights mentions poorly is not shippable.

## What this example teaches

- **Extraction as a designer-agent mode.** Mode is recorded once in
  [`config/plan.md`](config/plan.md) §1 (`TASK_MODE`) and governs the
  schema shape and metric family — not a new command, not a new
  methodology (the four-command set is closed, invariant #20).
- **Alignment metrics.** `span_f1` aligns predicted to gold spans by
  character-offset overlap with a configurable threshold; `extraction_f1`
  aligns by normalized text. Both are pure functions of (prediction,
  gold) — no LLM judge in scoring (invariant #13), the property that
  admits extraction while generation/RAG stay out of scope.
- **The empty case is a valid answer.** `row_004` has no mentions; an
  empty `entities` array scores 1.0 against an empty gold, and is not a
  parse failure.
- **Six-section prompt, unchanged.** [`prompts/prompt_v01.md`](prompts/prompt_v01.md)
  keeps the six-section structure (invariant #12); only the `<task>`,
  `<rules>`, and `<output_format>` content reflects the item-array
  output.

## Reading order

1. [`config/plan.md`](config/plan.md) — the contract, with
   `TASK_MODE = extraction` and the per-field extraction metrics.
2. [`data/baseline.csv`](data/baseline.csv) — the data shape: an
   `input` column plus a JSON item-array per gold field (`entities`,
   `topics`). Note `row_004`'s empty arrays.
3. [`prompts/prompt_v01.md`](prompts/prompt_v01.md) — the six-section
   extraction prompt.
4. [`runs/placeholder-model/REPORT.md`](runs/placeholder-model/REPORT.md)
   — the per-field REPORT shape with the extraction failure-mode
   breakdown.

All numbers in the REPORT are placeholder; the example is not a real
run.

## Cross-references

- [`DESIGN.md`](../../DESIGN.md) §7.1.11 — the v0.10 extraction-mode
  design pin.
- [`metric-design`](../../skills/run/sub-skills/metric-design/SKILL.md)
  SKILL.md §3.1 — the extraction metric sub-table.
- [`schema-designer`](../../skills/run/sub-skills/schema-designer/SKILL.md)
  SKILL.md §3.4 rule 8 — the `TASK_MODE` / schema-shape consistency
  check.
