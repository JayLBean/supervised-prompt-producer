# Fixture 5 — extraction happy path (consultation notes)

What `schema-designer` should do given
`inputs/task_description.md`. This is the extraction-mode positive
case (`TASK_MODE = extraction`; v0.10, `DESIGN.md` §7.1.11).

---

## Path detection (§3.1)

No machine-readable schema; the user has prose plus a description
of the desired output shape. → **Path 1 (consultative).**

## Mode (recorded before this invocation)

`TASK_MODE = extraction`, set by the designer during task-mode
identification (`agents/designer.md`) because the answer to "one
choice from a fixed list, or an open-ended set found in the text?"
was the open-ended set. The schema-designer renders to match that
mode and validates the match at mechanical rule 8.

## Path 1 walk (§3.2)

The designer confirms the item types (`product`, `org`), that one
item is one contiguous mention (longest match, no nested sub-spans),
that offsets are needed (the UI highlights), and that the empty list
is a valid answer. It renders:

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
type: object
required: [entities]
additionalProperties: false
properties:
  entities:
    type: array
    description: >
      Every product or organization mention found in the email body,
      in order of appearance. Empty array when the body has none.
    items:
      type: object
      required: [text, type, start, end]
      additionalProperties: false
      properties:
        text:
          type: string
          minLength: 1
          description: The exact mention substring, verbatim from the body.
        type:
          type: string
          enum: [product, org]
          description: The entity category.
        start:
          type: integer
          minimum: 0
          description: Character offset of the mention's first character.
        end:
          type: integer
          minimum: 0
          description: Character offset one past the mention's last character.
examples:
  - entities:
      - {text: "Acme Drill", type: product, start: 12, end: 22}
      - {text: "Acme Corp", type: org, start: 40, end: 49}
  - entities: []
```

### §3.4 mechanical layer

All 8 rules pass:

1. Schema parses as JSON Schema draft 2020-12.
2. Every field has a `type`.
3. The `type` enum `{product, org}` is enumerated. Rule 3 applies
   to this genuine enum only; the free-text `text` field is not an
   enum and does not trigger it.
4. Required is explicit on the item object (`[text, type, start,
   end]`) and on the top-level (`[entities]`).
5. Both `examples:` entries validate — including the empty-array
   row, which exercises the zero-item case.
6. No `$ref` cycles.
7. Both objects are closed (`additionalProperties: false`).
8. `TASK_MODE` / schema-shape consistency: `TASK_MODE = extraction`
   and the output is a variable-cardinality `array` of item objects
   — consistent. (A bare enum or a fixed scalar object here would
   fail rule 8.)

### §3.5 judgment-driven layer

All 5 rules pass:

1. **Enum exhaustiveness.** The `type` enum `{product, org}` is
   exhaustive for the task; the user confirmed no third category.
2. **Field-name clarity.** `text`, `type`, `start`, `end` cold-read
   cleanly as the mention, its category, and its offsets.
3. **Borderline concreteness.** The §5.1 extraction reframe
   established the one-mention unit (longest contiguous match, no
   nested sub-spans) and the empty-list case — concrete boundary
   calibration, the extraction analog of class borderlines.
4. **Relationship capture.** No cross-field relationships beyond the
   item object are needed; the array-of-objects captures the
   structure.
5. **Scope discipline.** Four item fields, exactly what the
   highlight UI needs (text + category + offsets). No speculative
   fields.

### §3.6 verdict synthesis

All mechanical pass; all judgment pass. → **`ready`.**

---

## What `schema-designer` should NOT do

- Render a fixed object of scalar fields (or a bare enum) for an
  extraction task — that would contradict `TASK_MODE = extraction`
  and fail mechanical rule 8.
- Add a `confidence` score or per-item probability — the metric is
  mechanical (`metric-design` §5; invariant #13). Items carry no
  model-emitted score.
- Require offsets when a task has none — offsets are optional in the
  extraction schema family; this task happens to need them.
- Invoke an LLM judge to decide whether the schema is "good enough."

---

## Failure mode this fixture guards against

The failure mode this fixture catches: a `schema-designer` that
ignores the recorded `TASK_MODE` and renders an extraction task as a
fixed classification object (or that accepts an extraction mode with
a bare-enum schema). Mechanical rule 8 exists to make that mismatch
a `not-ready` signal; this fixture is the positive case proving the
consistent item-array shape passes cleanly.
