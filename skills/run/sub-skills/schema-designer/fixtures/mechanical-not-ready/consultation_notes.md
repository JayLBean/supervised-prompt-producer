# Fixture 3 — mechanical violation

This is a narrative, not a script. The notes describe the
*shape* of the protocol walk for this input.

---

## What `schema-designer` should do

Run the §3 protocol against the inputs in `inputs/`.

### §3.1 path detection

The user provides a complete JSON Schema artifact that parses
without modification. → **Path 2 (validated).**

### §3.3 path 2 — validate-then-calibrate

1. **Parse.** The schema parses as JSON Schema draft 2020-12.
2. **Confirm draft compliance.** `$schema` URI explicitly
   names draft 2020-12.
3. **Render in JSON.** The user requested JSON; the rendered
   form is the input verbatim (round-trip is identity for
   already-JSON-Schema input).
4. **Calibrate per field.** The user articulates `category` as
   "one of `harassment`, `spam`, `csam`, `violence`,
   `self-harm`, `other-violation` — six values, the moderation
   team has been operating with these for 18 months." The
   articulation contradicts the schema's freeform-string
   `category` field.

This contradiction surfaces the mechanical violation: the
schema does not enforce the enum the user's task requires.

### §3.4 mechanical layer

**Rule 3 fails:** `category` is rendered as `"type": "string"`
with no `enum` clause, even though the user articulates a fixed
six-value set during calibration. The other 6 mechanical rules
pass (parses cleanly, every field has `type`, required is
explicit, the example output validates against the freeform
schema, no `$ref` cycles, the object is closed).

Rule 3 failure dominates per §3.6.

### §3.5 judgment-driven layer

**Not run.** Mechanical-layer failures are categorical
disqualifications; the §3.5 walk is short-circuited because
the schema cannot be operated against until rule 3 is fixed.

(If §3.5 *were* run, rule 1 — enum exhaustiveness — would also
fire because there is no enum to evaluate. But the verdict
machinery does not depend on that secondary signal.)

### §3.6 verdict synthesis

Mechanical rule 3 fails. → **`not-ready`.**

---

## What `schema-designer` should NOT do

- Silently rewrite the schema to add the `enum` clause. The
  user provided the schema; the sub-skill surfaces the
  mismatch and lets the user decide.
- Downgrade to `revise` because the violation is "easy to
  fix." Mechanical violations are categorical
  disqualifications; the layer split exists exactly so that
  ease-of-fix is not a verdict input.
- Run §3.5 and let a positive judgment-layer outcome override
  the §3.4 failure. Mechanical dominance is the rule.
- Recommend that the user override without first surfacing the
  fix. The override is a documented escape valve for cases
  where the user knowingly accepts the limitation; it is not
  the default response to a failure.

---

## What the user does next

Two paths the integration PR's runner will support:

1. **Fix and re-invoke** (the default, expected response).
   The user adds the `enum` clause to `category`, re-pastes
   the schema, and `schema-designer` re-runs. Second pass
   returns `ready` (all mechanical rules pass; the now-
   exhaustive enum allows judgment layer to evaluate; if
   the six values match production reality, all judgment rules
   pass). This is the expected exit from `not-ready`.
2. **Override and proceed** (rare and discouraged). The user
   records a `plan.md` §11 entry whose Reason field contains
   the literal substring `schema-not-ready override`. The
   override propagates into `REPORT.md`'s acknowledged-risk
   surface so flagged-but-shipped schemas are visible at
   finalization. Use only when the user explicitly accepts
   that the freeform string will be scored against a fixed-
   enum ground truth and the implications for metric
   calibration.

---

## Failure mode this fixture guards against

The failure mode this fixture catches: a `schema-designer`
that runs §3.5 first, finds judgment-layer issues to surface,
and returns `revise` even though §3.4 has a failure that
should dominate. The fixture's expected_review.md returns
`not-ready` and explicitly notes that judgment-layer was
not run — surfacing the mechanical-dominance contract
operationally, not just in §3.6's table.
