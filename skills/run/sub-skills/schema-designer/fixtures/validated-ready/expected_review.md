# schema_design_review.md — fixture: validated-ready

**Path:** 2 (validated)
**Surface format:** YAML (converted from pydantic)
**Generated:** 2026-05-06T10:00:00-07:00

---

## Verdict

`ready`

---

## OUTPUT_SCHEMA

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
title: TicketTriage
type: object
required: [queue, urgency, requires_human_review]
additionalProperties: false
properties:
  queue:
    type: string
    enum: [billing, general, abuse]
    description: The queue the ticket routes to.
  urgency:
    type: string
    enum: [low, normal, high]
    description: The ticket's urgency tier at intake.
  requires_human_review:
    type: boolean
    description: |
      True when the model is below its confidence threshold for
      autonomous routing.
```

---

## SCHEMA_DESIGN_NOTE (for `plan.md` §2)

Reviewed via Path 2 (validated). Input was a pydantic v2.5+
model (`TicketTriage`); parsed via the equivalent JSON Schema
draft 2020-12 export. Mechanical layer passed all 8 rules
(pydantic emits `additionalProperties: false`, both `Literal`
fields enumerate explicitly, all three fields are required by
the export; rule 8: `TASK_MODE` absent → `classification`,
fixed enum-field object — consistent). Judgment layer passed
all 5 (enums match the
production system's exhaustive value sets per the user's
calibration walk; field names communicate intent without
guessing; no conditional relationships are required by the
task; scope is tight at three fields). Surface format: YAML, by
user request. **Verdict: ready.**

---

## Findings

None — `ready` verdicts do not produce a findings list.

---

## Notes for the caller

Gate advances on the user's approval phrase alone. No
`plan.md` §11 entry is required. `SCHEMA_DESIGN_NOTE` above is
the §2 attestation that the review happened.

The pydantic model in `inputs/user_pydantic_model.py` is the
canonical authoring form for this schema; users editing the
schema in production should edit the pydantic model and
re-export rather than editing the YAML directly.
