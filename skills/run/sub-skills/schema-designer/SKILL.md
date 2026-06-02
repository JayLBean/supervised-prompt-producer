# schema-designer

A v0.2 sub-skill of `spp` that produces a production-grade
`OUTPUT_SCHEMA` for a supervised prompt-learning task and gates
whether downstream phases are allowed to operate against it. The
v0.2 analog of v0.1.0's single `LABEL_SPACE` field —
`OUTPUT_SCHEMA` is an arbitrary structured output (one or more
fields, possibly nested), expressed as a **JSON Schema (draft
2020-12)** document and rendered into `plan.md` §2 in the user's
chosen YAML or JSON surface format.

This is the fourth sub-skill in `spp` (peer to `metric-design`,
`baseline-quality`, and `prompt-architect`) and the second
sub-skill that carries verdict-gate authority. The verdict-token
+ enforcement-at-gate pattern is inherited from
`baseline-quality` SKILL.md §2; the design contract this sub-skill
realizes is `DESIGN.md` §7.1.1's schema layer.

A note on artifact shape before reading further. `spp` has three:
**phases** (orchestration, gate enforcement; user-facing entry
points), **agents** (judgment with structurally distinct
information access; invoked by phases), and **sub-skills** like
this one (opinionated reference material that informs decisions
and, when verdict-gated, blocks the gate the sub-skill defends).
A user reading this doc should come away knowing how to design
an OUTPUT_SCHEMA themselves; if follow-up consultation is needed,
the **designer** agent does it (and reads this doc to know which
follow-up to ask).

This sub-skill ships **standalone in its first PR** — the
`schema-designer` directory and its fixtures land before any
phase doc, agent doc, or template references it. Integration
into the live `/spp-init` flow (which gate slot the verdict
gates, how the designer agent invokes the sub-skill, how
`plan.md.template` carries `OUTPUT_SCHEMA`) is bucket 4 of the
v0.2 sequence — see "Cross-references" for what changes when.
The sub-skill is functional and citable in design discussions
from this PR forward; it is not yet wired into a runnable phase.

---

## 1. Identity and scope

`schema-designer` performs two related jobs that share one
verdict gate:

1. **Render** an `OUTPUT_SCHEMA` from the user's task — either
   built strawman-first by the designer (Path 1) or validated
   from a complete artifact the user brings (Path 2).
2. **Validate** the rendered schema against a two-layer rule set
   (mechanical + judgment-driven) and return a verdict that
   gates whether the rest of the methodology is allowed to
   operate against the schema.

**The framing.** v0.1.0's `LABEL_SPACE` field encoded the task's
output shape implicitly — a finite enum of class names. v0.2
generalizes the slot: any task whose ground truth is a
structured object (multi-field classification, hierarchical
labels, freeform extraction with structured ground truth) is
expressible as an OUTPUT_SCHEMA. The risk this sub-skill exists
to defend against is the schema-layer analog of baseline
overfitting: a schema that mechanically validates but does not
actually describe the task — vague field names, non-exhaustive
enums, missing relationships between fields, over-rich shapes
that invite scope drift — produces a methodology that polishes
toward an ill-formed target and never surfaces the mismatch.
`schema-designer` is the upstream defense for that mode.

**In scope:**

- Rendering OUTPUT_SCHEMA as JSON Schema (draft 2020-12),
  serialized as YAML or JSON per the user's choice.
- Path 1 (consultative): strawman-and-refine when the user has
  prose, partial pydantic, JSON examples, or just a
  conversation. Anything not a complete machine-readable
  artifact is Path 1 context.
- Path 2 (validated): validate-then-calibrate when the user
  brings a complete machine-readable JSON Schema or pydantic
  model.
- Two-layer validation — mechanical rules that pass/fail on
  parser output, plus judgment-driven rules that require the
  sub-skill's verdict.
- Per-field calibration: the v0.2 analog of v0.1.0's class-
  definition calibration that `baseline-quality` runs (`§3.1`
  drift, `§3.3` intuition-vs-rule), applied per OUTPUT_SCHEMA
  field.
- The **degenerate single-output case**: a v0.1.0-equivalent
  shape (`{label: <enum of class names>}`) is rendered as the
  same OUTPUT_SCHEMA shape any multi-field task uses, just with
  one required enum field. No shorthand, no `LABEL_SPACE`
  legacy alias inside the schema.

**Out of scope** (boundaries, not deferred work):

- **Schema synthesis from data alone.** The sub-skill does not
  scan a baseline CSV and infer fields by clustering. The user
  defines the task; `schema-designer` renders and validates.
  Synthesis-from-data crosses into a different methodology
  whose validation primitives this sub-skill does not have.
- **LLM-as-judge validation.** Mechanical layer rules pass/fail
  on a JSON Schema parser; judgment layer rules require human
  judgment. The sub-skill does not invoke an LLM judge to
  decide whether a schema is "good enough"; that would import
  the `metric-design` §5 independence-rule failure into the
  schema layer.
- **Generation-task output schemas.** Free-form text-generation
  outputs do not have ground truth in the way classification
  and structured extraction do (`DESIGN.md` §7.1.3). This
  sub-skill does not extend to them; v0.x will not.
- **Conversion-tooling for source-language schemas.** Pydantic,
  TypeScript interfaces, and Zod schemas are paste-as-context
  during Path 1, not separate-format-converters the sub-skill
  must plumb. Path 2 takes only JSON Schema or pydantic (the
  latter via its built-in JSON-Schema export); other formats
  are converted to one of those by the user before invoking
  Path 2.
- **Touching the baseline or splits.** OUTPUT_SCHEMA design
  precedes label generation; splits do not exist when
  `schema-designer` runs. The sacred-test-set guarantee
  (`DESIGN.md` §10) is not at risk.

The cross-skill rule that governs every choice in this doc is
the **plan.md-as-contract** rule (`DESIGN.md` §10): findings
flow back into `plan.md`, not into a separate document. The full
elaboration is in §5 below.

---

## 2. The decision the sub-skill helps make

**Is this OUTPUT_SCHEMA a faithful description of the task —
mechanically valid, semantically complete, no broader than the
task needs — and is it ready for the rest of the methodology to
operate against?**

The output of consulting `schema-designer` is three things, all
of which feed into the verdict gate the sub-skill defends:

- **A verdict**, one of:
  - `ready` — the schema passes both mechanical and judgment
    layers; the gate advances on the user's approval phrase.
  - `revise` — specific judgment-layer issues exist that should
    be fixed before the schema is treated as ground truth, but
    the user can choose to proceed with a documented
    justification in `plan.md` §11.
  - `not-ready` — substantive issues exist (any mechanical
    failure, or a judgment failure severe enough that the
    schema does not actually describe the task). The gate
    does **not** advance on the user's approval phrase alone;
    the user must either resolve the issues (and re-invoke) or
    record an explicit override entry in `plan.md` §11
    containing the literal substring `schema-not-ready
    override`. The override propagates into `REPORT.md`'s
    acknowledged-risk surface (§6 below).
- **A finalized `OUTPUT_SCHEMA`** rendered in the user's chosen
  surface format (YAML or JSON) inside a fenced code block.
  Returned regardless of verdict — even a `not-ready` verdict
  returns the latest schema state so the user has a concrete
  artifact to revise from.
- **A findings document** (only when the verdict is `revise`
  or `not-ready`): each violated rule named explicitly, with
  the rule's layer (mechanical vs judgment), the specific
  failure, and the corrective action. Required so the user can
  act without re-deriving the findings.

The verdict has gate-enforcement teeth via the integration that
will land in bucket 4 of the v0.2 sequence; the literal-substring
override is the contract that integration will wire into the
runner. Future contributors must not weaken this authority — see
"Versioning" below; weakening is a `BREAKING CHANGE:`.

---

## 3. The protocol

Walk in order. The protocol has three stages: **path detection**
(§3.1), **path-specific rendering** (§3.2 or §3.3 — exactly
one), and the **two-layer validation** (§3.4 mechanical, §3.5
judgment-driven) that runs after either path completes.
**Verdict synthesis** (§3.6) aggregates the layer outcomes into
the single token returned at §6.

### 3.1 Path detection

**Question:** does the user's input include a complete,
machine-readable JSON Schema or pydantic model that already
describes the task's output?

- **Yes — exactly one complete artifact, parseable without
  modification** → Path 2 (validated). Skip §3.2; go to §3.3.
- **No — prose, partial pydantic, JSON examples, conversation,
  multiple disagreeing artifacts, or anything requiring
  interpretation before rendering** → Path 1 (consultative).
  Skip §3.3; go to §3.2.

The framing matters. **"Existing schema" in informal use means
context the user brings to Path 1** (pydantic models pasted as
text into the chat, TypeScript interfaces, Zod schemas, prose
descriptions in a doc) — not a structured artifact in Path 2's
sense. Only Path 2 takes a structured artifact as input. The
implication is that there is no conversion-tooling burden on the
sub-skill: users who arrive with TypeScript or Zod paste their
artifact into the consultation, the designer extracts intent,
and Path 1 renders. Path 2 is reserved for cases where the user
already speaks in JSON Schema or pydantic and wants no
interpretation between their artifact and the rendered
OUTPUT_SCHEMA.

When in doubt, prefer Path 1 — the cost of an unnecessary
strawman is a paragraph of consultation; the cost of treating
ambiguous input as a finalized artifact is a schema that
mechanically validates but does not describe the task.

### 3.2 Path 1 — consultative (strawman-and-refine)

The strawman-first pattern from the designer agent (§4 of
`agents/designer.md`), specialized to schema design.

1. **Read the repo and the user's context.** Existing types
   (pydantic models, TypeScript interfaces, Zod schemas, GraphQL
   types, prose docs, JSON examples) are paste-as-context
   inputs. Note any field names or shapes that already exist in
   the codebase.
2. **Build a strawman OUTPUT_SCHEMA.** Concrete: name the
   fields, give each a JSON Schema `type`, enumerate enum
   values explicitly, mark required vs optional explicitly,
   and include at least one example output that validates.
   Render in YAML or JSON — pick the surface format that
   matches the user's existing artifacts (TypeScript and pydantic
   users tend toward JSON; YAML repos tend toward YAML); the
   user can swap.
3. **Present the strawman with the rationale.** Explain *why*
   each field is shaped the way it is, surfacing the
   assumptions the strawman embeds (e.g., "I made `status` a
   3-value enum because your CSV had three distinct values;
   are there others I missed?").
4. **Refine through correction.** The user adds, removes,
   renames, or reshapes fields. Each refinement re-renders the
   schema. Stop refining when the user says the schema looks
   right (or when refinement loops for more than 2–3 cycles
   without progress — that is a signal the task description
   is too thin to render reliably. Halt, surface the gap to
   the user, and re-run §3.1 to confirm whether they can now
   provide enough context for Path 1 or whether they have a
   complete artifact for Path 2).
5. **Hand off to §3.4** with the refined schema.

The defining property of Path 1 is that the sub-skill renders
the canonical artifact; the user is not expected to write JSON
Schema themselves.

### 3.3 Path 2 — validated (validate-then-calibrate)

The user already speaks in JSON Schema or pydantic and brings a
complete artifact. The sub-skill validates and calibrates;
rendering is a serialization step (re-render to the user's
chosen surface format if it differs from what they brought).

1. **Parse the artifact.** Pydantic models export to JSON
   Schema via `model_json_schema()`; the parsed result is the
   canonical form. JSON Schema artifacts are parsed directly.
2. **Confirm draft compliance.** The schema must be valid JSON
   Schema draft 2020-12. Other drafts (draft-07, draft 2019-09)
   are converted to 2020-12 if the user accepts the conversion;
   otherwise the artifact is rejected at §3.4 (mechanical layer)
   and the user is asked to update.
3. **Render in the chosen surface format.** YAML or JSON. The
   serialization round-trips: `yaml.safe_load(yaml_form) ==
   json.loads(json_form)`.
4. **Calibrate the per-field definitions.** Even with a
   complete schema, the user articulates each field's intent
   in plain English — same calibration discipline as
   `baseline-quality` SKILL.md §3.1's drift check, applied per
   field. Mismatches between the schema's structure and the
   user's articulated intent are findings for §3.5 (judgment
   layer).
5. **Hand off to §3.4** with the parsed-and-rendered schema.

The defining property of Path 2 is that the schema is the
input; the sub-skill's job is to confirm the schema describes
the task the user intends.

### 3.4 Mechanical layer (always run, regardless of path)

The mechanical rules pass or fail on parser output. They do not
require the sub-skill's verdict; they fail or pass deterministically.
A failure at this layer is a `not-ready` signal — the schema
cannot be validated against until the failure is fixed.

Verbatim from `DESIGN.md` §7.1.1's schema layer:

1. Schema parses as valid JSON Schema (draft 2020-12).
2. Every field has a JSON Schema `type`.
3. Every enum field's values are explicitly enumerated (no
   plain `"type": "string"` where an enum is intended).
4. Required vs. optional is explicit on every field (no
   implicit defaults).
5. At least one example output validates against the schema
   (the schema-actually-describes-the-task test).
6. No `$ref` cycles.
7. No naked `"type": "object"` without either `"properties"` or
   `"additionalProperties": false`.

For each rule that fails, the findings document names the rule
number, the field or schema location, and the corrective
action. The mechanical layer does not aggregate — every
violation is reported.

### 3.5 Judgment-driven layer (always run, regardless of path)

Judgment rules cannot be checked mechanically. The sub-skill
asks the questions; the user (with the sub-skill prompting and
checking) answers; the sub-skill aggregates the answers into
verdict signals.

Verbatim from `DESIGN.md` §7.1.1's schema layer:

1. **Enum exhaustiveness.** For each enum field, ask: are these
   the only values the task generates in production, or are
   these the common values and the residual is "Other"? An
   enum that is missing the residual is a `revise` signal —
   either add the residual values explicitly, or add a
   documented `Other` category with calibration on what counts
   as Other (the analog of v0.1.0's discipline against an
   `Other` class as a dumping ground; if `Other` exists, it
   needs a definition tighter than "everything else").
2. **Field-name clarity (cold-read test).** A labeler reading
   the schema cold — without consulting the per-field
   definitions — should be able to label rows without guessing
   the field's intent. Field names like `data`, `info`,
   `metadata`, `extra`, `details` are signals: they label a
   shape, not a meaning. `revise` signal.
3. **Borderline-example concreteness.** For each field, the
   per-field definition includes positive and borderline
   examples. The borderlines must be concrete enough to
   disambiguate the field's intent — same standard as v0.1.0's
   class definitions (`baseline-quality` SKILL.md §3.3). Vague
   borderlines ("things that might be X") are a `revise`
   signal.
4. **Relationship capture.** If the task requires conditional
   fields, nested fields, or cross-field constraints (e.g.,
   field B is only meaningful when field A is `Yes`), the
   schema must express those relationships — `if/then/else`,
   `oneOf`, `dependentRequired`, nested objects with their own
   `properties`. Flattening relationships into a wider tuple of
   independent fields is a `revise` signal.
5. **Schema scope discipline.** The schema is no broader than
   the task requires. Over-rich schemas (every field the
   labeler *could* annotate, regardless of whether the task
   needs it) invite scope drift across iterations. The analog
   of v0.1.0's "no Other class as a dumping ground"
   discipline, applied to the schema's surface area as a
   whole. A schema visibly broader than the task is a `revise`
   signal; a schema dramatically broader (e.g., 12 fields
   when the task description supports 4) is a `not-ready`
   signal.

**Multilingual input (v0.6).** When the dataset spans multiple
languages (a per-row `language` column; `DESIGN.md` §7.1.7), the
output label space stays **canonical** — one fixed enum regardless of
the input row's language. The model classifies non-English input into
the same labels; do not localize enum values per language or branch the
schema on language. Per-language label variants are a `revise` signal:
they fragment the metric space and break the fixed-output-space
assumption the rest of the methodology rests on. Translating the
*labeler-facing definitions* for annotators is fine; the *schema's*
enum values are canonical.

For each rule that fails, the findings document names the rule
number, the field, the specific failure, and the corrective
action. Multiple judgment failures aggregate per §3.6.

### 3.6 Verdict synthesis

| Signal pattern | Verdict |
|---|---|
| All mechanical rules pass; all judgment rules pass | `ready` |
| All mechanical rules pass; one or more judgment rules trigger `revise` (no `not-ready` signal) | `revise` |
| Any mechanical rule fails | `not-ready` |
| Any judgment rule fires the `not-ready` signal explicitly (rule 5's "dramatically broader" case) | `not-ready` |

Mechanical failures dominate. A schema that does not parse, or
has a `$ref` cycle, or has implicit-default required fields
cannot be partially-okay; the rest of the methodology cannot
operate against an unparseable schema. This is why the layer
split exists — mechanical failures are categorical
disqualifications; judgment failures are graded.

---

## 4. Worked examples

Four scenarios, mapped to the four fixtures in `fixtures/`.
None references a real source-project task (`DESIGN.md` §7.2);
each is a generic shape the designer might encounter.

### Example 1: consultative happy path → `ready`

**Setup.** The user is building a product-listing extractor.
They have a CSV of marketplace listings (4,200 rows, columns
include raw `title`, `body`, `seller_id`, and a recently-added
`source_marketplace` flag). They describe the task as: "I want
to pull `title`, `price`, `category`, and `brand` out of each
listing into a structured record. `category` is one of about a
dozen marketplace-defined buckets; `brand` is sometimes
unknown."

**Path detection (§3.1).** No machine-readable schema; user
provides prose + a CSV they reference. → **Path 1**.

**Path 1 walk (§3.2).** The designer reads the CSV, notes the
12 distinct `category` values, builds a strawman:

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
type: object
required: [title, price, category, brand_known, brand]
additionalProperties: false
properties:
  title:
    type: string
    description: The listing's product title, normalized.
  price:
    type: number
    minimum: 0
    description: The listing's price in the marketplace's local currency.
  category:
    type: string
    enum: [electronics, apparel, home, toys, beauty, sports,
           books, automotive, garden, pet, grocery, other]
    description: The marketplace's category bucket for the listing.
  brand_known:
    type: boolean
    description: Whether the brand can be extracted from the listing.
  brand:
    type: [string, "null"]
    description: The brand name, or null when brand_known is false.
examples:
  - title: "Acme Cordless Drill, 12V"
    price: 79.99
    category: home
    brand_known: true
    brand: "Acme"
  - title: "Generic Cotton T-Shirt"
    price: 14.50
    category: apparel
    brand_known: false
    brand: null
```

The user accepts after one refinement (the user adds that
`category` should include `health` as a 13th value).

**§3.4 mechanical:** all 7 rules pass. One example validates
against the schema; no `$ref` cycles; every field has a `type`;
the enum is enumerated; required is explicit;
`additionalProperties: false` closes the object.

**§3.5 judgment:** enum is exhaustive after the `health`
addition; field names are clear (a labeler reading
`brand_known` + `brand` cold understands the conditional
relationship); borderlines are concrete; the conditional
relationship is captured (`brand` is `[string, "null"]` paired
with `brand_known`); scope is tight (4 fields, exactly what the
task description supports).

**Verdict:** `ready`.

**Outputs:** verdict `ready`, OUTPUT_SCHEMA above, no findings
list (none needed for `ready`).

### Example 2: validated happy path → `ready`

**Setup.** The user is a pydantic native and brings a complete
model:

```python
from pydantic import BaseModel, Field
from typing import Literal

class TicketTriage(BaseModel):
    queue: Literal["billing", "general", "abuse"] = Field(
        description="The queue the ticket routes to.")
    urgency: Literal["low", "normal", "high"] = Field(
        description="The ticket's urgency tier at intake.")
    requires_human_review: bool = Field(
        description="True when the model is below its confidence "
                    "threshold for autonomous routing.")
```

The user requests YAML rendering.

**Path detection (§3.1).** Complete machine-readable artifact,
parses without modification. → **Path 2**.

**Path 2 walk (§3.3).** `model_json_schema()` returns a JSON
Schema document; conversion to draft 2020-12 is mechanical (the
pydantic export already targets a recent draft). Rendered in
YAML for the user.

The sub-skill walks the calibration discipline: for each field,
the user articulates the meaning. `queue` → "the queue the
ticket routes to." `urgency` → "the urgency tier we tag for
prioritization within the queue." `requires_human_review` →
"when the model's autonomous routing falls below confidence,
the ticket goes to a human." Articulations match the schema's
intent.

**§3.4 mechanical:** all 7 rules pass.

**§3.5 judgment:** all 5 rules pass — the enums are exhaustive
within the production system, names are clear, borderlines are
captured in the user's articulation, no relationships are
hidden, scope matches the task.

**Verdict:** `ready`.

**Outputs:** verdict `ready`, the rendered YAML form of the
JSON Schema, no findings list.

### Example 3: mechanical violation → `not-ready`

**Setup.** A user brings a JSON Schema for a multi-class
moderation task and pastes it into the consultation. The
schema looks plausible but has a mechanical flaw: the
`category` field is rendered as `"type": "string"` with no
`enum` clause, even though the user's task description names
six specific categories the model must choose from.

**Path detection (§3.1).** Complete machine-readable JSON
Schema → **Path 2**.

**Path 2 walk (§3.3).** Schema parses as JSON Schema draft
2020-12. Renders cleanly in JSON. Calibration walk: the user
articulates `category` as "one of {harassment, spam, csam,
violence, self-harm, other-violation}." The articulation
contradicts the schema, which permits any string.

**§3.4 mechanical:** rule 3 fails — `category` is rendered as
plain `"type": "string"` where the user's articulation
indicates an enum is intended. Findings document names rule 3
explicitly:

> **Rule 3 (enum enumeration) — failed at field `category`.**
> The field is rendered as `"type": "string"` but the user's
> articulation enumerates six specific values
> `{harassment, spam, csam, violence, self-harm, other-violation}`.
> Render the field as `"enum": [...]` with those six values
> (and add a documented residual category if the production
> data surfaces values outside the six). Until this is fixed,
> the schema cannot be operated against — a freeform string
> field cannot be scored against a fixed-enum ground truth.

**§3.5 judgment:** not run — mechanical layer dominates.

**Verdict:** `not-ready`.

**Outputs:** verdict `not-ready`, the user-supplied schema
returned as the latest state (so the user has a concrete
artifact to fix), findings list naming rule 3.

The user fixes the schema and re-invokes; the second pass
returns `ready`. If the user instead wanted to override (rare
and discouraged), they record an explicit entry in `plan.md`
§11 whose Reason field contains the literal substring
`schema-not-ready override` and the limitation propagates into
`REPORT.md` (§6 below).

### Example 4: judgment violation → `revise`

**Setup.** The user is building an issue-categorization task
for a public bug tracker. They bring a schema with three
fields:

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
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

**Path detection (§3.1).** Complete YAML JSON Schema → **Path
2**.

**§3.4 mechanical:** all 7 rules pass — the schema is
parseable, fields have types, enums are enumerated, required
is explicit, an example would validate, no `$ref` cycles, the
object is closed.

**§3.5 judgment:**

- Rule 1 (enum exhaustiveness): `type` is missing common
  categories — public bug trackers routinely surface `task`,
  `documentation`, and `discussion` issues that don't fit
  `{bug, feature, question}`. `severity` collapses an
  inherently 3+ tier scale into a binary. **Both fire `revise`.**
- Rule 2 (field-name clarity): `info` is a shape, not a
  meaning. A labeler reading `info` cold cannot tell whether
  it should contain reproduction steps, tracebacks, the
  user's environment, or the bot's triage notes. **`revise`.**
- Rule 3 (borderline concreteness): no per-field borderlines
  are provided in the schema's `description` fields; just
  shape descriptions. **`revise`.**
- Rule 4 (relationship capture): no relationships expressed,
  but the task does not require any (no conditional fields).
  **Pass.**
- Rule 5 (scope discipline): three fields is not over-rich;
  if anything, `info` is so vague it might not belong at all.
  **Pass; folded into rule 2's finding.**

**Verdict:** `revise`.

**Findings list:**

> **Rule 1 (enum exhaustiveness) — `type`.** The enum
> `{bug, feature, question}` is missing common values
> production bug trackers surface (`task`, `documentation`,
> `discussion`). Either add them, or add a documented `other`
> with calibration on what counts as `other`.
>
> **Rule 1 (enum exhaustiveness) — `severity`.** The two-value
> enum `{low, high}` collapses an inherently 3+ tier scale.
> Add `medium` (and possibly `critical`); document the
> labeling rule that distinguishes them.
>
> **Rule 2 (field-name clarity) — `info`.** The field name is
> a shape, not a meaning. Either rename to the specific role
> the field plays (`reproduction_steps`, `triage_notes`,
> `environment`) or remove the field if no specific role is
> needed.
>
> **Rule 3 (borderline concreteness) — all fields.** The
> `description` strings name what each field is, but do not
> include borderline examples. Add positive and borderline
> examples per field (the v0.2 analog of v0.1.0's class
> definitions; same calibration discipline as
> `baseline-quality` SKILL.md §3.3).

**Outputs:** verdict `revise`, the user-supplied schema
returned as latest state, findings above.

The user fixes the schema and re-invokes for `ready`, or
records a `plan.md` §11 entry mentioning `schema-designer` as
the reason for proceeding without fixing — `revise` does not
require the literal `schema-not-ready override` substring; only
`not-ready` does.

---

## 5. The cross-skill constraint

**Findings flow into `plan.md`, not into a separate artifact.**
This is the operational form of the plan.md-as-contract rule
(`DESIGN.md` §10 glossary), the same constraint that governs
`baseline-quality` (SKILL.md §5). Two specific destinations:

- **`plan.md` §2** carries the `OUTPUT_SCHEMA` block and a
  `SCHEMA_DESIGN_NOTE` paragraph (the §2 output of this
  sub-skill, the analog of `baseline-quality`'s
  `BASELINE_QUALITY_NOTE` in §6). The note names what the
  sub-skill reviewed (which path was taken; which mechanical
  and judgment rules ran), what was found, and what was
  resolved. The note is required regardless of verdict — even
  a `ready` verdict gets a note saying "review performed,
  schema rendered, no issues surfaced."
- **`plan.md` §11 (revision log)** gains a row whenever
  schema-designer caused a change to §2 (schema refinement,
  per-field definition update, surface-format swap), §10 (new
  open question surfaced — e.g., a residual-category value the
  user could not enumerate), or any override — both
  `not-ready override` (literal substring required) and
  `revise` acknowledgement (no specific substring required).
  The row follows the standard `plan.md.template` §11 schema
  (date, plan version, reason, by) and **bumps
  `PLAN_VERSION`** because the contract has changed.

What the sub-skill **does not** do:

- It does not write a separate `schema_quality_review.md` or
  `output_schema.json` to `plan.md`'s sibling files. The
  schema and findings live in `plan.md`'s prose; separating
  them would create two sources of truth.
- It does not silently rewrite a user-provided schema in Path
  2. Findings are surfaced; the user decides whether to
  accept the proposed corrections, accept some and reject
  others, or override. The verdict reflects the surfaced
  state, not the sub-skill's preferred fix.
- It does not annotate `data/baseline.csv` rows with schema
  metadata. The CSV is the raw labeled data; schema lives in
  `plan.md`.

There is one place where the sub-skill's verdict **does** have
force outside `plan.md`: it gates whether the phase the
integration PR (bucket 4) wires it into is allowed to advance.
That force is operational (the runner consults the verdict at
the gate; the literal `schema-not-ready override` substring is
the override mechanism), not documentary (no separate verdict
file is written).

**Forward-looking note on integration.** This PR ships the
sub-skill standalone. The references above to `plan.md` §2
carrying the OUTPUT_SCHEMA block are forward-looking — the
v0.1.0 `plan.md.template` does not yet have an OUTPUT_SCHEMA
slot. That template change is part of the breaking-change PR
in bucket 5; the gate-slot wiring is part of bucket 4. The
sub-skill is functional as a reference document and as a
fixture-driven validator from this PR forward; the integration
PRs will edit `designer.md`, `plan.md.template`, and the
relevant phase doc to invoke it.

---

## 6. What the sub-skill outputs

Three things the caller (the designer agent, in bucket 4's
integration) collects after the protocol walk, all of which
feed into the gate enforcement and the `plan.md` updates.

### Verdict

One of:

- `ready` — schema passes both layers; gate advances on user
  approval phrase alone.
- `revise` — judgment-layer issues exist; user can fix and
  re-invoke, or proceed with a documented justification in
  `plan.md` §11 whose Reason mentions `schema-designer`. No
  specific literal substring is required (parallel to
  `baseline-quality`'s `revise` treatment).
- `not-ready` — mechanical-layer failure or severe judgment-
  layer failure (rule 5 dramatic over-richness); gate does not
  advance on user approval phrase alone. **Override requires
  an explicit `plan.md` §11 entry whose Reason field contains
  the literal substring `schema-not-ready override`.** The
  override propagates into `REPORT.md`'s acknowledged-risk
  surface (the same shape as `baseline-quality`'s
  `not-ready override` propagation into `REPORT.md` §7.2), so
  flagged-but-shipped schemas surface in the methodology's
  transparency layer.

The verdict is a single token; downstream tooling (the
integration PR's runner, the Phase 4 validation harness) can
match it as a literal string. The override substring is
matched as a literal substring within the §11 row's Reason
column — exact-substring, case-sensitive.

### `OUTPUT_SCHEMA`

A JSON Schema (draft 2020-12) document, rendered as either
YAML or JSON per the user's choice, returned inside a fenced
code block. Returned regardless of verdict — even a
`not-ready` verdict returns the latest schema state so the
user has a concrete artifact to revise against.

The schema ships into `plan.md` §2's OUTPUT_SCHEMA block (once
the breaking-change PR lands the v0.2 `plan.md.template`).
v0.1.0-equivalent single-output classification renders as the
degenerate one-required-enum-field shape — no shorthand, no
`LABEL_SPACE` legacy alias, same rendering pipeline as any
multi-field task.

### Findings list (only for `revise` and `not-ready`)

A list of specific rule violations that need user attention.
Each item names:

- The layer (mechanical or judgment-driven) and rule number
  (§3.4 rules 1–7, §3.5 rules 1–5).
- The field or schema location involved (or "schema-level" if
  the finding is structural rather than per-field).
- The specific failure observed.
- The recommended corrective action.
- Whether the finding contributed to a `revise` or `not-ready`
  signal.

The list is **specific, not generic**. "The schema looks
under-specified" is not a finding; "Rule 1 (enum
exhaustiveness) — `type` is missing `task`, `documentation`,
`discussion`" is.

### Override mechanics summary

| Verdict | Plan.md §11 entry required? | Literal substring required in Reason? | Propagates to REPORT.md? |
|---|---|---|---|
| `ready` | No | — | No |
| `revise` | Yes (proceed-without-fix path) | No (must mention `schema-designer`) | No |
| `not-ready` | Yes (override path) | Yes — `schema-not-ready override` | Yes |

The literal substring is matched case-sensitively. Future
contributors must not loosen the match — see "Versioning."

---

## Pattern for subsequent sub-skills

`schema-designer` is the second verdict-gated sub-skill in
`spp` (after `baseline-quality`). The verdict-token +
enforcement-at-gate pattern is now established across two
sub-skills with consistent shape:

- **Verdict token set:** `ready` / `revise` / `not-ready` —
  three values, no others. The token is a single word matched
  literally; no confidence weighting, no fuzzy match, no
  `revise-but-tend-toward-ready` half-states.
- **Override substring:** verdict-flavored, kebab-case-ish, ends
  in `override`. `baseline-quality` uses `not-ready override`
  (one rule for the entire sub-skill); `schema-designer` uses
  `schema-not-ready override` (qualified by sub-skill name).
- **Override propagation:** `not-ready` overrides flow into
  `REPORT.md`'s acknowledged-risk surface (§7.2 in `REPORT.md`,
  for now); `revise` acknowledgements stay in `plan.md` §11.
- **Findings flow into `plan.md`, not parallel artifacts.**

`metric-design` and `prompt-architect` are review-and-record
sub-skills, not verdict-gated. They remain that way; not every
sub-skill is a gatekeeper. The decision to make a sub-skill
verdict-gated belongs at the sub-skill's design pin (in
`DESIGN.md` for v0.x sub-skills) and is breaking to flip after
ship.

---

## Versioning

Same rule as `designer.md`, `/spp-init`, `metric-design`, and
`baseline-quality`: changes that **alter methodology
guarantees** are flagged as `BREAKING CHANGE:` in commit
messages and trigger a major-version bump per `CLAUDE.md` §4.

**Methodology-affecting (= breaking):**

- **Loosening any mechanical-layer rule** (§3.4 rules 1–7).
  These are the categorical disqualifications that justify the
  layer split.
- **Loosening any judgment-layer rule** (§3.5 rules 1–5),
  including weakening the `revise`-vs-`not-ready` thresholds
  in rule 5 (scope discipline).
- **Weakening verdict-gate enforcement.** Informational
  verdicts (verdict that does not block the gate), fuzzy
  override matching, or accepting any override phrase that
  *implies* override intent without containing the literal
  substring `schema-not-ready override`.
- **Adding any verdict beyond `ready` / `revise` / `not-ready`.**
  Three tokens, no `partial`, no `provisional`, no
  confidence-weighted variants.
- **Loosening the literal-substring requirement on
  `schema-not-ready override`.** Case-sensitive, exact substring,
  matched within the §11 Reason column.
- **Allowing the sub-skill to write to any artifact other than
  its returned output and `plan.md` §11.** A separate
  `schema_quality_review.md`, per-CSV-row metadata, or any
  file outside the returned-artifact + plan.md cross-skill
  contract is a methodology break.
- **Switching the schema language from JSON Schema (draft
  2020-12)** without an explicit design pass and pin update
  in `DESIGN.md`.
- **Allowing LLM-as-judge validation** at either layer (§3.4
  or §3.5). Mechanical rules run on a parser; judgment rules
  run on user judgment with the sub-skill prompting.

**Behavioral (= non-breaking):**

- Better worked-example phrasing.
- New fixtures exercising existing rules and verdicts.
- Clearer error-message wording in findings documents.
- Additional cross-references to other skills/docs.
- Tightening a judgment-rule's threshold *with rationale* (e.g.,
  rule 5 going from "dramatically broader" to "more than 3x the
  fields the task description supports") as long as the
  three-tier `ready` / `revise` / `not-ready` structure is
  preserved.
- Stylistic improvements that do not change required content.
- Documenting the **canonical-label policy for multilingual input**
  (§3.5, v0.6). It restates the existing fixed-output-space discipline
  for the multilingual case; it adds no verdict and no new mechanical
  rule.

When in doubt, treat the change as breaking. The cost of a
release-notes paragraph is low; the cost of silently weakening
a rule that defends against schema-overfitting is high.

---

## Cross-references

- [`baseline-quality/SKILL.md`](../baseline-quality/SKILL.md) —
  the structural sibling. The verdict-token + enforcement-at-
  gate pattern is inherited from §2; the parallel-artifacts
  prohibition from §5; per-field calibration from §3.1
  (drift) and §3.3 (intuition-vs-rule).
- [`metric-design/SKILL.md`](../metric-design/SKILL.md) — the
  peer review-and-record sub-skill. Useful as contrast: where
  `metric-design` records a chosen metric without gating,
  `schema-designer` blocks the gate. The decision tree in
  `metric-design` §3 has no verdict-token output; this
  sub-skill's §3.6 does.
- [`prompt-architect/SKILL.md`](../prompt-architect/SKILL.md)
  — peer for the six-section prompt structure. Not
  verdict-gated; review-and-record.
- [`agents/designer.md`](../../agents/designer.md) — the agent
  that will invoke this sub-skill once bucket 4 wires the
  gate slot. The designer's §7 mechanical validation rule 3
  ("`LABEL_SPACE` is enumerable") generalizes to "OUTPUT_SCHEMA
  passes the mechanical layer above" in v0.2; that edit is
  part of the breaking-change PR (bucket 5).
- [`templates/plan.md.template`](../../templates/plan.md.template)
  — the destination for the sub-skill's findings. §2 (schema
  block + `SCHEMA_DESIGN_NOTE` subsection, both forthcoming
  in the breaking-change PR) and §11 (revision log, including
  `schema-not-ready override` entries when applicable).
- `DESIGN.md` §7.1.1 schema layer — the design contract this
  sub-skill realizes; verbatim source for the mechanical and
  judgment rules in §3.4 and §3.5. §4.2 (per-stage information
  isolation) — the rationale behind §2's monolithic block, why
  the auditor's `plan.md §2` allow-listed slice must remain
  cleanly addressable. §10 glossary (plan.md as contract) —
  the rule that findings flow into `plan.md`, not into separate
  documents. §7.1.3 — the deliberate non-goals (generation
  tasks, RAG, agentic) that bound this sub-skill's scope.
- `CLAUDE.md` §4 (Semantic Commits — applies to changes to
  this sub-skill).
