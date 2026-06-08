# Fixture 1 — consultative happy path

This is a narrative, not a script. `schema-designer` adapts; the
notes describe the *shape* of the protocol walk for this input,
not specific phrasings.

---

## What `schema-designer` should do

Run the §3 protocol against the inputs in `inputs/`.

### §3.1 path detection

The user provides prose + a CSV reference. No complete machine-
readable schema. → **Path 1 (consultative).**

### §3.2 path 1 — strawman-and-refine

The designer reads `data/listings.csv` and notes the 12 distinct
`raw_category` values present in the data the user described.
The user's prose adds three explicit fields (`title`, `price`,
`category`, `brand`) and a fourth implicit one (the
brand-extractable boolean — the user said "encode that case
explicitly").

The strawman renders 5 fields:

- `title` — string, required.
- `price` — number, ≥ 0, required.
- `category` — enum of the 12 values from CSV, required.
- `brand_known` — boolean, required.
- `brand` — `[string, null]`, required (so the downstream ranker
  always reads a value rather than handling missing-key
  separately).

Surface format: YAML (`pyyaml` is in deps; the repo uses YAML
elsewhere — this is a soft prior the designer surfaces, not a
choice the designer makes unilaterally).

The user refines once: add `health` as a 13th `category` value.
The designer re-renders; the user accepts.

### §3.4 mechanical layer

All 8 rules pass:

1. Schema parses as JSON Schema draft 2020-12 (`$schema` URI
   set explicitly).
2. Every field has a `type` (or a typed union for `brand`).
3. The `category` enum is enumerated with 13 values.
4. Required is explicit (`required: [title, price, category,
   brand_known, brand]`).
5. The two `examples:` entries each validate against the schema.
6. No `$ref` cycles (no `$ref` at all in this schema).
7. `additionalProperties: false` closes the object.
8. `TASK_MODE` / schema-shape consistency: this is a
   classification task (`TASK_MODE` absent → reads as
   `classification`), and the schema is a fixed object of fields,
   not a variable-cardinality item array — consistent.

### §3.5 judgment-driven layer

All 5 rules pass:

1. **Enum exhaustiveness.** The `category` enum is the
   marketplace's published category list; 13 values covers the
   production data. The user has confirmed `other` is the
   marketplace-defined residual, not a dumping ground.
2. **Field-name clarity.** A labeler reading `brand_known` +
   `brand` cold can label rows: when `brand_known` is `false`,
   `brand` is `null`. The pairing is conventional and
   self-documenting.
3. **Borderline concreteness.** The two `examples:` entries
   include both a brand-known case (Acme drill) and a
   brand-unknown case (generic t-shirt) — concrete borderlines
   that disambiguate the conditional pairing.
4. **Relationship capture.** The `brand_known` /
   `brand: [string, null]` pairing captures the conditional;
   not flattened.
5. **Scope discipline.** Five fields, each grounded in the user's
   prose. No "additional metadata" or "extra context" fields
   were added speculatively.

### §3.6 verdict synthesis

All mechanical pass; all judgment pass. → **`ready`.**

---

## What `schema-designer` should NOT do

- Speculate about how the schema would affect downstream metric
  scoring (that's `metric-design`'s territory; this sub-skill
  does not invoke it).
- Add fields the user did not request (e.g., `seller_id` is in
  the CSV but not part of the task; do not add it
  speculatively).
- Render in JSON when the user picked YAML (or vice versa) —
  surface format is the user's choice.
- Add a `confidence` or `partial-ready` verdict — the verdict
  is a hard token from a three-element set.
- Persist the schema to `data/baseline.csv` rows or to any file
  outside the returned artifact.

---

## Failure mode this fixture guards against

The failure mode this fixture catches: a `schema-designer` that
under-renders the strawman (missing the `brand_known` /
`brand: null` conditional) and produces a schema that
mechanically validates but does not capture the
brand-extractability state the user explicitly named. Such a
schema would pass §3.4 but fail §3.5 rule 4 (relationship
capture). The expected_review.md is what a correctly-rendered
strawman looks like.
