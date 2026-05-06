# schema_design_review.md — fixture: judgment-revise

**Path:** 2 (validated)
**Surface format:** YAML
**Generated:** 2026-05-06T10:00:00-07:00

---

## Verdict

`revise`

---

## OUTPUT_SCHEMA (latest state — user-supplied, unfixed)

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
title: IssueCategorization
type: object
required: [type, severity, info]
additionalProperties: false
properties:
  type:
    type: string
    enum: [bug, feature, question]
    description: The issue's type.
  severity:
    type: string
    enum: [low, high]
    description: The severity of the issue.
  info:
    type: string
    description: Additional context.
```

The schema is returned in its current (unfixed) state per §6
— a `revise` verdict still returns the latest schema so the
user has a concrete artifact to revise from.

---

## SCHEMA_DESIGN_NOTE (for `plan.md` §2)

Reviewed via Path 2 (validated). Mechanical layer passed all
7 rules. Judgment layer surfaced four findings (see below):
two enum exhaustiveness gaps, one field-name clarity issue,
and missing per-field borderline examples. No judgment rule
fired the `not-ready` signal — the schema is mechanically
usable, just not aligned with the production task. **Verdict:
revise.**

---

## Findings

### Finding 1

- **Layer:** judgment-driven (§3.5)
- **Rule:** 1 (enum exhaustiveness)
- **Field:** `type`
- **Failure:** The enum `{bug, feature, question}` is missing
  values that surface in production bug-tracker data per the
  user's calibration walk — at minimum `task` and
  `documentation`, possibly also `discussion`. A
  classification prompt scored against this enum will treat
  any production row labeled `task` or `documentation` as
  unscorable.
- **Corrective action:** Either enumerate the missing values
  explicitly, or add a documented `other` value with a tight
  definition (the analog of v0.1.0's discipline against an
  `Other` class as a dumping ground; if `other` exists, it
  needs a definition tighter than "everything else").
- **Signal:** `revise`.

### Finding 2

- **Layer:** judgment-driven (§3.5)
- **Rule:** 1 (enum exhaustiveness)
- **Field:** `severity`
- **Failure:** The two-value enum `{low, high}` collapses an
  inherently 3+ tier severity scale. The user's "maybe more
  later" during calibration confirms the enum is intentionally
  incomplete; treating an incomplete enum as ground truth will
  force every production row of intermediate severity into
  one of the two extremes.
- **Corrective action:** Add `medium` (and possibly
  `critical`); document the labeling rule that distinguishes
  the tiers — what raises a `low` to `medium`, a `medium` to
  `high`. The labeling rule is what makes the enum honest;
  without it, three tiers is just relabeling the same
  intuition.
- **Signal:** `revise`.

### Finding 3

- **Layer:** judgment-driven (§3.5)
- **Rule:** 2 (field-name clarity — cold-read test)
- **Field:** `info`
- **Failure:** The field name is a shape, not a meaning. A
  labeler reading the schema cold cannot tell whether `info`
  should contain reproduction steps, the user's environment,
  triage notes, or links to related issues. The user's own
  articulation ("extra context the labeler thought was
  relevant") confirms the field has no specific role.
- **Corrective action:** Either rename to the specific role
  the field plays (`reproduction_steps`, `triage_notes`,
  `environment`, etc.), or remove the field if no specific
  role is needed. Catch-all fields like `info` accumulate
  inconsistent labels across the baseline — the prompt either
  learns to mimic that inconsistency (overfitting to noise)
  or ignores the field entirely (in which case it should not
  be required).
- **Signal:** `revise`.

### Finding 4

- **Layer:** judgment-driven (§3.5)
- **Rule:** 3 (borderline concreteness)
- **Field:** all fields
- **Failure:** Each field's `description` names what the field
  is, but does not include positive or borderline examples.
  The v0.2 analog of v0.1.0's class definitions
  (`baseline-quality` SKILL.md §3.3) requires concrete
  borderlines so a labeler can disambiguate the field's
  intent — e.g., for `type`, what makes a question that is
  reporting unexpected behavior count as a `question` rather
  than a `bug`?
- **Corrective action:** Add positive and borderline examples
  per field, in each field's `description`. Apply the same
  calibration discipline that `baseline-quality` SKILL.md
  §3.1 (drift) and §3.3 (intuition-vs-rule) impose on v0.1.0
  class definitions, scoped per OUTPUT_SCHEMA field.
- **Signal:** `revise`.

---

## Notes for the caller

The integration PR's runner advances the gate on the user's
approval phrase + a `plan.md` §11 entry whose Reason mentions
`schema-designer`. Two paths:

1. **Fix and re-invoke** — the user resolves the four findings
   above and re-invokes; the second pass returns `ready`.
2. **Acknowledge and proceed** — the user records a `plan.md`
   §11 entry whose Reason mentions `schema-designer` and the
   acknowledged limitations. Sample row:

   ```
   | 2026-05-06 | v2 | schema-designer revise acknowledged —
     accepting incomplete `type` enum and freeform `info`
     field for the v1 baseline; revisit at first
     finalization. | jane@triage |
   ```

   No literal substring is required for `revise`. The
   acknowledgement does **not** propagate into `REPORT.md`'s
   acknowledged-risk surface — `revise` is acknowledged at
   the gate, not at finalization. Only `not-ready` overrides
   propagate.
