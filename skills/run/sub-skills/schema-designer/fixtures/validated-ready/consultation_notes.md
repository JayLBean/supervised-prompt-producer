# Fixture 2 — validated happy path

This is a narrative, not a script. `schema-designer` adapts; the
notes describe the *shape* of the protocol walk for this input.

---

## What `schema-designer` should do

Run the §3 protocol against the inputs in `inputs/`.

### §3.1 path detection

The user provides a complete machine-readable pydantic model
that parses without modification (`pydantic >= 2.5` exports to
JSON Schema 2020-12 via `model_json_schema()`). → **Path 2
(validated).**

### §3.3 path 2 — validate-then-calibrate

1. **Parse.** Treat the pydantic model as canonical input. The
   sub-skill reads its JSON Schema export — three required
   string-or-bool fields, two of which are `Literal` enums.
2. **Confirm draft compliance.** Pydantic 2.5+'s export targets
   draft 2020-12 by default; no draft conversion needed.
3. **Render in YAML.** The user requested YAML; serialize the
   parsed JSON Schema as YAML for the returned artifact. The
   YAML form round-trips: parsing the YAML back to a Python
   dict matches the parsed JSON Schema dict.
4. **Calibrate per field.** The user articulates each field's
   intent in plain English. Each articulation matches the
   field's role in the schema:
   - `queue` → "which of three operational queues the ticket
     routes to." Matches the `Literal[...]` enum.
   - `urgency` → "priority tier the queue picks tickets off
     in; three tiers; high gets paged." Matches the
     `Literal[...]` enum.
   - `requires_human_review` → "true when autonomous routing
     falls below confidence; routes to a human reviewer
     regardless of queue." Matches the `bool` field.

   No mismatches surface. Calibration walk completes cleanly.

### §3.4 mechanical layer

All 7 rules pass:

1. The pydantic export is valid JSON Schema 2020-12.
2. Every field has a `type` (`string` for the two `Literal`
   fields, `boolean` for the boolean field).
3. Both enum fields are explicitly enumerated.
4. Required is explicit — pydantic exports all three fields as
   required because none has a default.
5. A synthesized example output (`{queue: "billing", urgency:
   "normal", requires_human_review: false}`) validates.
6. No `$ref` in the export (flat object).
7. The exported object is closed — pydantic emits
   `additionalProperties: false` for `BaseModel` subclasses by
   default.

### §3.5 judgment-driven layer

All 5 rules pass:

1. **Enum exhaustiveness.** The user confirms `queue`'s three
   values are the production system's three queues — exhaustive.
   `urgency`'s three tiers are the system's full priority scale.
2. **Field-name clarity.** All three names communicate intent
   without guessing — `queue`, `urgency`, `requires_human_review`
   each name a specific role.
3. **Borderline concreteness.** The user's articulations name
   the boundary (e.g., "billing and abuse have dedicated
   triagers; everything else is general" — a labeler reading
   the schema cold understands the sort).
4. **Relationship capture.** No conditional fields are required
   by the task; the schema correctly does not invent any.
5. **Scope discipline.** Three fields, exactly the operational
   triage decision the user described. No speculative fields.

### §3.6 verdict synthesis

All mechanical pass; all judgment pass. → **`ready`.**

---

## What `schema-designer` should NOT do

- Re-derive the schema from a strawman. The user explicitly
  brought a complete artifact; Path 2 validates and calibrates,
  it does not redesign.
- Reject the input because it came in as pydantic rather than
  JSON Schema. Path 2 accepts both — pydantic via
  `model_json_schema()`.
- Add fields the user did not include (e.g., `created_at`,
  `assignee_id`). The schema is the user's input.
- Modify field names without the user's explicit consent during
  calibration.
- Render in JSON when the user picked YAML.

---

## Failure mode this fixture guards against

The failure mode this fixture catches: a `schema-designer` that
treats Path 2 as Path 1 and over-renders — adding `priority`
synonyms or rewriting `requires_human_review` to
`needs_review`. Path 2's contract is "the schema is the
input"; rewriting it without explicit user direction violates
that contract. The expected_review.md returns the user's
schema essentially verbatim, surface-converted from pydantic to
YAML.
