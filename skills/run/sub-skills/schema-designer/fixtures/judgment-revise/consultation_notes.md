# Fixture 4 — judgment violation

This is a narrative, not a script. The notes describe the
*shape* of the protocol walk for this input.

---

## What `schema-designer` should do

Run the §3 protocol against the inputs in `inputs/`.

### §3.1 path detection

The user provides a complete YAML JSON Schema artifact. → **Path
2 (validated).**

### §3.3 path 2 — validate-then-calibrate

1. **Parse.** The schema parses as JSON Schema 2020-12.
2. **Render in YAML** (the user's choice; the input is already
   YAML).
3. **Calibrate per field.** Each articulation surfaces a gap:
   - `type` — user names `bug, feature, question` but
     acknowledges `task` and `documentation` exist in
     production data.
   - `severity` — user says "maybe more later," signaling that
     two tiers is incomplete.
   - `info` — user describes it as "extra context the labeler
     thought was relevant" — a shape, not a meaning.

### §3.4 mechanical layer

All 8 rules pass:

1. Schema parses as draft 2020-12.
2. Every field has a `type`.
3. Both enum fields enumerate values explicitly (the values are
   wrong per §3.5, but the enumeration itself is mechanically
   present).
4. Required is explicit.
5. A trivial example output (`{type: bug, severity: low, info:
   "..."}`) validates.
6. No `$ref` cycles.
7. `additionalProperties: false` closes the object.
8. `TASK_MODE` / schema-shape consistency: classification task
   (`TASK_MODE` absent → `classification`), fixed enum-field
   object — consistent. (The `revise` here is judgment-layer, not
   a mode mismatch.)

### §3.5 judgment-driven layer

Multiple rules fire `revise`:

- **Rule 1 (enum exhaustiveness) — `type`.** Missing `task` and
  `documentation`; both surface in production data per the
  user's calibration. **`revise`.**
- **Rule 1 (enum exhaustiveness) — `severity`.** Two-value enum
  collapses an inherently 3+ tier scale. The user's "maybe
  more later" confirms incompleteness. **`revise`.**
- **Rule 2 (field-name clarity) — `info`.** A shape, not a
  meaning. The user's articulation ("extra context the labeler
  thought was relevant") confirms it has no specific role.
  **`revise`.**
- **Rule 3 (borderline concreteness) — all fields.** No
  per-field `description` includes positive and borderline
  examples; only role descriptions. **`revise`.**
- **Rule 4 (relationship capture).** The task does not require
  conditional fields; the schema correctly does not invent
  any. **Pass.**
- **Rule 5 (scope discipline).** Three fields is not over-rich
  in the abstract, but `info` is so vague it should probably
  be removed entirely or refactored. **Folded into rule 2's
  finding rather than a separate signal.**

No rule fires `not-ready`. (Rule 5 only fires `not-ready` when
a schema is *dramatically* over-rich — e.g., 12 fields where
the task supports 4. This fixture's schema is incomplete, not
over-rich.)

### §3.6 verdict synthesis

All mechanical pass; multiple judgment rules fire `revise`; no
judgment rule fires `not-ready`. → **`revise`.**

---

## What `schema-designer` should NOT do

- Escalate to `not-ready` for incomplete-but-fixable judgment
  signals. The verdict tier exists exactly so that "the schema
  needs work" is distinct from "the schema cannot be operated
  against."
- Aggregate the judgment findings into one finding. Each
  violated rule is named separately, with its own corrective
  action — the user needs the specifics to act.
- Pre-emptively rewrite `info` into a guess at what the user
  meant. The corrective action is a question for the user
  (rename or remove), not a guess.
- Require a literal-substring override for `revise`. The
  `schema-not-ready override` substring is for `not-ready`
  only; `revise` is acknowledged with a §11 entry mentioning
  `schema-designer` and no specific substring.

---

## What the user does next

Two paths the integration PR's runner will support:

1. **Fix and re-invoke** (the recommended path). The user
   adds `task` and `documentation` to the `type` enum (or adds
   an `other` value with a documented residual definition);
   adds `medium` to `severity`; either renames `info` to a
   specific role like `triage_notes` or removes it; adds
   borderline examples per field. Re-invocation returns
   `ready`.
2. **Acknowledge and proceed** — the user records a `plan.md`
   §11 entry whose Reason mentions `schema-designer`. Sample:

   ```
   | 2026-05-06 | v2 | schema-designer revise acknowledged —
     accepting incomplete `type` enum and freeform `info`
     for the v1 baseline; will revisit at first
     finalization. | jane@triage |
   ```

   No literal substring required — `revise` is a softer gate
   than `not-ready`. The acknowledgement does **not**
   propagate into `REPORT.md`'s acknowledged-risk surface;
   `revise` lives at the gate, not at finalization.

---

## Failure mode this fixture guards against

The failure mode this fixture catches: a `schema-designer`
that aggregates the four judgment-layer findings into a single
generic finding ("the schema needs more work") and returns
`revise` without naming the rules and corrective actions. The
specificity is what makes the verdict actionable; without per-
rule findings, the user cannot fix the schema and re-invoke
for `ready` without re-deriving the analysis.
