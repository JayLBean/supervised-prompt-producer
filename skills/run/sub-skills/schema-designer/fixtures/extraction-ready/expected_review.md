# schema_design_review.md — fixture: extraction-ready

**Path:** 1 (consultative)
**Task mode:** extraction
**Surface format:** YAML
**Generated:** 2026-06-08T10:00:00-07:00

---

## Verdict

`ready`

---

## OUTPUT_SCHEMA

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
type: object
required: [entities]
additionalProperties: false
properties:
  entities:
    type: array
    description: |
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
          enum:
            - product
            - org
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

---

## SCHEMA_DESIGN_NOTE (for `plan.md` §2)

Reviewed via Path 1 (consultative). `TASK_MODE = extraction`. Built
the strawman from the user's stated output shape (a per-row,
variable-cardinality set of `product` / `org` mentions with character
offsets for the highlight UI). Mechanical layer passed all 8 rules,
including rule 8 (`TASK_MODE = extraction` and the schema is a
variable-cardinality item array — consistent); rule 3 applied to the
genuine `type` enum only, not the free-text `text` field. Judgment
layer passed all 5 (the `type` enum is exhaustive; field names
cold-read cleanly; the one-mention unit and empty-list case were
calibrated via §5.1's extraction reframe; scope is the four item
fields the UI needs). Offsets are present because this task supplies
them; the extraction schema family keeps them optional for tasks that
do not. Surface format: YAML, matching the repo convention.
**Verdict: ready.**

---

## Findings

None — `ready` verdicts do not produce a findings list.

---

## Notes for the caller

`/spp-init`'s gate advances on the user's approval phrase alone; no
`plan.md` §11 entry is required. The recorded `TASK_MODE = extraction`
in `plan.md` §1 and this OUTPUT_SCHEMA must agree — they do, which is
what mechanical rule 8 verified. Downstream (forthcoming, bucket 3 of
the v0.10 arc), the extraction metric branch (`metric-design`;
`scripts/_metrics.py`) will score the item array, with offsets — when
present — feeding the span metrics.
