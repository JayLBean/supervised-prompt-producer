# schema_design_review.md — fixture: mechanical-not-ready

**Path:** 2 (validated)
**Surface format:** JSON
**Generated:** 2026-05-06T10:00:00-07:00

---

## Verdict

`not-ready`

---

## OUTPUT_SCHEMA (latest state — user-supplied, unfixed)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ModerationDecision",
  "type": "object",
  "required": ["category", "is_actioned", "rationale"],
  "additionalProperties": false,
  "properties": {
    "category": {
      "type": "string",
      "description": "The moderation category for the content."
    },
    "is_actioned": {
      "type": "boolean",
      "description": "Whether the content was actioned (removed, hidden, etc.)."
    },
    "rationale": {
      "type": "string",
      "description": "A short reviewer-facing explanation for the decision."
    }
  }
}
```

The schema is returned in its current (unfixed) state per §6
— a `not-ready` verdict still returns the latest schema so
the user has a concrete artifact to revise from.

---

## SCHEMA_DESIGN_NOTE (for `plan.md` §2)

Reviewed via Path 2 (validated). Mechanical layer rule 3
failed (see findings below). Judgment layer not run —
mechanical failures are categorical disqualifications per
§3.6. The schema cannot be operated against in its current
state because the freeform-string `category` field cannot be
scored against the fixed-enum ground truth the user described
during calibration. **Verdict: not-ready.**

---

## Findings

### Finding 1

- **Layer:** mechanical (§3.4)
- **Rule:** 3 (enum enumeration)
- **Field:** `category`
- **Failure:** The field is rendered as `"type": "string"` with
  no `enum` clause. During the §3.3 calibration walk, the user
  articulated `category` as one of six fixed values:
  `{harassment, spam, csam, violence, self-harm,
  other-violation}`. A freeform string cannot be scored against
  a fixed-enum ground truth — every prediction would be
  treated as schema-valid regardless of whether it matches the
  six allowed values, so the metric cannot distinguish a
  correct prediction from a hallucinated category name.
- **Corrective action:** Render `category` as
  `"enum": ["harassment", "spam", "csam", "violence",
  "self-harm", "other-violation"]`. If production data
  surfaces values outside the six, add `"other"` (or
  similar) to the enum *and* document in `plan.md` §2 what
  counts as the residual — the analog of v0.1.0's discipline
  against an `Other` class as a dumping ground.
- **Signal:** `not-ready` (mechanical violation).

---

## Notes for the caller

The integration PR's runner refuses to advance the gate on
the user's approval phrase alone for a `not-ready` verdict.
Two exits:

1. **Fix and re-invoke** — the user updates the schema, the
   sub-skill re-runs, second pass returns `ready` (assuming
   the fix is clean and the now-exhaustive enum passes
   judgment-layer rule 1).
2. **Override** — the user records a `plan.md` §11 entry
   whose Reason field contains the literal substring
   `schema-not-ready override`. Sample row:

   ```
   | 2026-05-06 | v2 | schema-not-ready override accepted —
     accepting freeform-string `category` for v1 of this
     prompt; metric calibration will treat any predicted
     value not in the documented six as a miss. To revisit
     after first finalization. | jane@triage |
   ```

   The override propagates into `REPORT.md`'s acknowledged-
   risk surface (parallel to `baseline-quality`'s
   `not-ready override` propagation into `REPORT.md` §7.2), so
   the flagged-but-shipped schema is visible at finalization.
