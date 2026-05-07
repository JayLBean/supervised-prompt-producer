# Fixture 4 — multi-field per-field verdict (v0.2)

This fixture exercises the **per-edit-per-field verdict
shape** introduced in v0.2's per-field methodology
application layer (`DESIGN.md` §7.1.1). It is the auditor's
fourth fixture; the prior three (`clean-categorical-edit`,
`row-specific-patch-disguised-as-rule`,
`cross-iteration-contradiction`) all exercise the v0.1.0
per-edit verdict shape, which under v0.2 is the K=1
degenerate case. This fixture is the K > 1 case.

The defining properties:

- **Multi-field OUTPUT_SCHEMA** (K=2): `category` (enum)
  and `brand_known` (boolean). The schema lives in the
  fixture's `inputs/plan_section_2.md` rendered as a YAML
  JSON Schema 2020-12 document.
- **One rule edit affecting both fields.** Rule 5
  (proposed for iteration 4) sets `brand_known = false`
  AND `category = automotive` for listings using
  generic-merchant phrasing. Its `target_fields` list
  in `discrepancy_analysis.md` names `[brand_known,
  category]`.
- **Mixed verdicts.** The auditor's per-target-field
  synthetic-rows test (`auditor.md` §4) produces:
  - `(edit 1, brand_known)` → `categorical` — the
    generic-merchant phrasing class is real and the rule
    generalizes (5 of 5 synthetic rows route correctly).
  - `(edit 1, category)` → `row-specific` — the
    `category = automotive` clause patches the cluster's
    auto-parts skew rather than describing a categorical
    property of the listings (only 1 of 5 synthetic rows
    routes correctly).
- **Gate behavior.** Under `phases/spp-loop.md` §4 step
  12, the iteration advances `(edit 1, brand_known)`
  unconditionally and halts on `(edit 1, category)`
  pending an override entry containing
  `auditor override [edit-1.category]` in `plan.md` §11.

The fixture's `expected_review.md` shows what
articulating per-target-field verdicts concretely looks
like:

- One `### Verdict for field X` sub-section per target
  field within the edit's main `## Edit 1` section
  (auditor.md §6 validation gate).
- Per-field synthetic-rows test articulated explicitly,
  with 5 synthetic-row examples per target field that
  exercise the rule's literal condition.
- Cross-iteration check operates per field
  (auditor.md §4's "Cross-iteration contradiction check
  operates per field" subsection).
- Gate-enforcement summary at the end naming the override
  syntax the user would record for each non-`categorical`
  `(edit, field)` combination.

Expected auditor behavior:

1. Read the §3 reading checklist's four inputs
   (`prompt_v_prev.md`, `prompt_v_next.md`, the prior
   `discrepancy_analysis.md`, `plan.md` §2; prior
   auditor reviews omitted in this fixture for brevity
   — the structure assumes a prior reviews directory
   would be empty or address unrelated rules).
2. Notice `target_fields = [brand_known, category]` on
   edit 1.
3. Apply the §4 synthetic-rows test once per target
   field. Confirm 5/5 synthetic rows route correctly for
   `brand_known` (categorical) and only 1/5 route
   correctly for `category` (row-specific).
4. Produce per-field sub-sections with independent
   verdicts and recommendations.
5. Surface the `(edit 1, category)` row-specific finding
   with a `generalize` recommendation that names the
   pre-existing rule 2 (the prompt's category-assignment
   rule) as the categorical rule the proposed edit
   contradicts.

What the auditor should NOT do:

- Aggregate the two per-field verdicts into a single
  per-edit verdict. Aggregation would either falsely
  advance the `category` clause (if it produced
  `categorical` from a 1-of-2 majority) or falsely
  block the `brand_known` clause (if it produced
  `row-specific` from a 1-of-2 minority). Per-field
  scoping is what catches this kind of edit.
- Speculate about how the edit would affect the
  aggregate dev metric (no score access; the auditor's
  information-isolation property is unchanged in v0.2).
- Add an `auditor_confidence` field to either per-field
  verdict (verdicts are hard tokens; confidence is
  forbidden per `auditor.md` §6).
- Propose its own rewrite of rule 5 (the
  `generalize` recommendation hints at the direction
  but does not write the new rule itself; that is the
  next iteration's discrepancy analysis's job).

This fixture's failure mode would be: an auditor that
runs the synthetic-rows test once for the edit
holistically rather than per target field, producing a
single verdict that cannot capture the
`brand_known`-vs-`category` asymmetry. The expected_review.md
is what running the test per field, with explicit
synthetic-row examples for each field, looks like.
