# Walkthrough — nested-schema

A narrative walk through `spp`'s four phases for a hierarchical-
labels task. The placeholder domain is support-ticket
categorization: each input is a ticket body and the prompt
produces a `top_level` enum plus a `sub_category` whose value
space depends on `top_level`'s value. All numbers, examples, and
specific decisions are illustrative; the example is a skeleton
per [`DESIGN.md`](../../DESIGN.md) §7.2.

---

## Task framing

Each row is a support-ticket body in plain text. The prompt's
output is a JSON object with two fields:

- **`top_level`** (`enum`) — one of `billing`, `technical`,
  `account`, `other`. Routes the ticket to the correct support
  team. Misroutes are unrecoverable without re-running the
  prompt on the whole ticket queue.
- **`sub_category`** (`enum`, **conditional on `top_level`**) —
  the value space depends on `top_level`'s value:
  - `top_level = billing` → `sub_category` ∈ `{invoice_question,
    payment_failed, refund_request}`
  - `top_level = technical` → `sub_category` ∈ `{login_issue,
    feature_bug, performance_complaint}`
  - `top_level = account` → `sub_category` ∈ `{password_reset,
    profile_update, subscription_change}`
  - `top_level = other` → `sub_category` ∈ `{feedback,
    uncategorized}`

This is exactly the hierarchical-labels shape that
[`DESIGN.md`](../../DESIGN.md) §7.1.1 schema layer's "Adjacent
output shapes the schema layer subsumes" subsection commits to
absorbing without separate bookkeeping. The OUTPUT_SCHEMA
expresses the conditional relationship via JSON Schema's `allOf`
+ `if/then` clauses — one clause per branch. The methodology
treats the result as a two-field structured-output task; per-
field metrics work without modification; the conditional
constraint becomes a schema-validation concern.

---

## `/spp-init` walkthrough

Per [`DESIGN.md`](../../DESIGN.md) §7.1.1 sub-skill ordering
layer (bucket 4), `schema-designer` runs before `metric-design`.

**`schema-designer` consultation (Path 1 — consultative).** The
user describes the task in prose: "tickets get a top-level team
routing, then a sub-category specific to that team." The
designer reads the repo context, builds a strawman OUTPUT_SCHEMA
that uses the conditional pattern (per
[`DESIGN.md`](../../DESIGN.md) §7.1.1 schema layer's "Adjacent
output shapes" — hierarchical labels are treatable as a
two-field structured output where field 2 is conditional on
field 1, expressed in JSON Schema via `if/then/else` or
per-branch `$ref`). The user reviews the strawman and the
sub-category enums per branch, refining as needed.

The result is a JSON Schema document (draft 2020-12) rendered
as YAML inside [`config/plan.md`](config/plan.md) §2. The
schema declares both fields as `required`, with `type` on each,
an `enum` on `top_level`, and an `allOf` block with one
`if/then` clause per branch constraining `sub_category`. Two
example outputs validate against the schema (one per branch
demonstrates a meaningful share of the conditional surface).

**Mechanical-layer check** ([`schema-designer`](../../skills/run/sub-skills/schema-designer/SKILL.md)
SKILL.md §3.4): the schema parses; both fields have a `type`;
both enums are explicitly enumerated (the per-branch
sub-category enums are inside the `then` clauses); required
vs. optional is explicit; example outputs validate; no `$ref`
cycles; no naked `"type": "object"` without `additionalProperties`.
✓

**Judgment-driven check** ([`schema-designer`](../../skills/run/sub-skills/schema-designer/SKILL.md)
SKILL.md §3.5): per-branch enum value spaces are exhaustive
(every meaningful sub-category for each branch is named); the
`other / uncategorized` escape hatch is documented as
"residual"; per-field definitions cover the conditional
relationship explicitly (the per-field definition for
`sub_category` names which value space applies for each
`top_level` value); the schema is no broader than the task
needs (no extra optional fields). Verdict: `ready`. G1's dual
check advances on the user's approval phrase.

**`metric-design` consultation (per-field protocol).** Per-field
metric selection runs once per OUTPUT_SCHEMA field:

- `top_level` is an `enum` with 4 values; the §3.1 decision-tree
  branch lands on `macro_F1` (more than two classes; per-class
  recall matters because misroutes are unrecoverable).
- `sub_category` is also conceptually an `enum` (with conditional
  value space); the §3.1 decision-tree branch lands on
  `macro_F1`. The metric is computed over the ground-truth
  sub-category values directly, treating the conditional
  structure as a constraint on the sub-category's value space
  rather than a metric concern.

Both metrics produce values in [0, 1] — homogeneous metric
types. `metric-design` §3.2's strawman recommends `macro` for
homogeneous types; the user accepts. `AGGREGATE_STRATEGY` is
`macro`; the headline criterion (`plan.md` §3) is `aggregate
(macro) ≥ 0.85` on dev.

**Per-field-floor consultation (§3.3).** The user identifies
`top_level` as required-and-unrecoverable: a wrong `top_level`
routes the ticket to the wrong team, where the team's process
doesn't include re-routing back. Floor on `top_level`:
`macro_F1 ≥ 0.90` (tighter than the aggregate floor because
top-level errors are most costly). `sub_category` carries no
floor: a wrong sub-category lands the ticket inside the right
team, where the team can re-categorize as part of normal
triage.

**G1 advances.** [`config/plan.md`](config/plan.md) is written
via the v0.2 template surface ([`DESIGN.md`](../../DESIGN.md)
§7.1.1 compat layer): §2 holds OUTPUT_SCHEMA + per-field
definitions; §3 holds the aggregate-metric headline target;
§4 holds the AGGREGATE_STRATEGY block, two per-field metric
sub-blocks, and one per-field floor sub-block on `top_level`.

---

## `/spp-baseline` walkthrough

The phase reads `plan.md` §2's OUTPUT_SCHEMA and per-field
definitions. The user labels ~80 rows; each row gets two
values (one per field), persisted as `top_level` and
`sub_category` columns in `data/baseline.csv` (plus `row_id`
and `body`). Sub-category values respect the conditional
structure; the labeler is responsible for picking only
sub-categories valid for the row's `top_level`.

At step 7 the phase invokes
[`baseline-quality`](../../skills/run/sub-skills/baseline-quality/SKILL.md)
with per-field calibration. The §3 review questions run per
OUTPUT_SCHEMA field. For `sub_category` the per-branch
calibration is meaningful: the reviewer checks that each
branch's sub-category enum captures meaningful distinctions
within that team's workflow, and that the labeler is applying
the per-branch enum consistently within the branch.

Sample protocol walk:

- §3.1 (drift) on `top_level`: sample 8 rows per class; clean.
  ✓
- §3.1 (drift) on `sub_category`: sample 4–6 rows per branch
  (sub-category values vary by branch). For `billing`, the
  labeler's articulations match the per-branch definitions.
  For `technical`, two rows show drift — the labeler used
  `feature_bug` for what looks like `performance_complaint`
  (rules engine outputs slow under load, not actually
  malfunctioning). 2 of ~6 is borderline; the field signal is
  `revise`.
- §3.3 (intuition-vs-rule) per field: clean for `top_level`;
  for `sub_category`, the borderline-case set is small (the
  conditional structure constrains the labeler more than a
  free-form sub-category would), and rule-based labeling
  dominates.
- §3.5 (calibration): clean for both fields.

**Within-field synthesis:**

| Field | Within-field verdict |
|---|---|
| `top_level` | `ready` |
| `sub_category` | `revise` |

**Cross-field consolidation:** any `revise` field without
`not-ready` → baseline verdict is `revise`. The user reviews
the `sub_category` findings, refines the `technical` branch's
per-field definition in [`config/plan.md`](config/plan.md) §2
to clarify the `feature_bug` vs. `performance_complaint`
boundary (rule: `feature_bug` is "the feature does the wrong
thing"; `performance_complaint` is "the feature does the right
thing slowly"), and re-validates. Re-invoking
`baseline-quality`: per-field re-runs return `ready` for
`sub_category`; baseline verdict is `ready`. G2 advances.

---

## `/spp-loop` walkthrough

Per [`DESIGN.md`](../../DESIGN.md) §7.1.1 per-field methodology
application layer (bucket 3), the loop is per-field-aware
end-to-end.

**Per-iteration scoring.** Each iteration computes per-field
metrics on dev: `macro_F1` for `top_level`; `macro_F1` for
`sub_category`. The aggregate is the macro mean of the two.
[`runs/placeholder-model/run_NN/eval.json`](runs/placeholder-model/)
carries the v0.2 shape: `per_field` (one entry per field with
its confusion matrix); `aggregate` (the macro value, strategy,
weights `null`); `floor_compliance` (one row, `top_level`,
met/unmet).

**Discrepancy clustering.** The discrepancy subagent reads
any-field-disagreed dev rows. The canonical pattern for
hierarchical tasks surfaces here: clusters tagged with
`primary_field: top_level` (rows where the top-level routing
itself was wrong; sub-category becomes ill-defined when
top-level is wrong) and clusters tagged with `primary_field:
sub_category` (rows where top-level was right but the
sub-category was wrong within the right team's enum).
Cross-field correlation is visible to the discrepancy
subagent's analysis: a cluster might surface as "rows where
`top_level = billing` was correct but `sub_category` confusion
between `invoice_question` and `payment_failed` is the
dominant pattern" — the analysis names both fields explicitly.

**Auditor verdicts.** Per-edit-per-field. A rule edit that
adds a "if the ticket mentions 'invoice' as the primary
subject, prefer `invoice_question` over `payment_failed` even
when payment is mentioned" clause has `target_fields:
[sub_category]`; the auditor returns one verdict for
`(edit-N, sub_category)`. Edits that affect both fields (e.g.,
"if the ticket mentions 'access' without context, route to
`account` rather than `technical`, and use `password_reset`
as the default sub-category") get a verdict per
`(edit, field)` pair.

**Stop conditions.** Plateau and overfitting-guard checks run
on the aggregate `macro` value across iterations. Per-field
movement is informational only.

**Termination.** If aggregate plateaus at-or-above target AND
the `top_level` floor is met, the runner writes `SUCCESS.md`.
If aggregate plateaus at-or-above target BUT `top_level` floor
is unmet, the runner writes `EARLY_STOP.md` with reason
`early_stop_floor_unmet`.

---

## `/spp-finalize` walkthrough

The phase reads `plan.md` §2 OUTPUT_SCHEMA, §3 aggregate
target, §4 per-field metric sub-blocks + aggregate-strategy
block + per-field floor sub-blocks. Pre-condition 6 accepts
`SUCCESS.md` directly; if the loop terminated as
`EARLY_STOP.md/early_stop_floor_unmet` on the `top_level`
floor, pre-condition 6's v0.2 advancement branch surfaces the
unmet floor and asks the user to confirm sacred-test-set
advancement.

**Step 4 — test-set metrics.** `macro_F1` on `top_level` and
`macro_F1` on `sub_category` computed against test ground
truth; the aggregate `macro` value computed across the two;
floor compliance checked on `top_level`. `test_eval.json`
carries the v0.2 shape.

**Step 7 — REPORT generation.** §2 carries per-field final
scores for both fields with their confusion matrices; §3
carries per-field trajectories plus the aggregate trajectory;
§4 carries failure clusters with primary-field tags (the
hierarchical pattern of "right top-level, wrong sub-category"
naturally surfaces as `primary_field: sub_category` clusters);
§6's deterministic decision tree reads aggregate + floor
compliance.

---

## What this example teaches about the methodology

The v0.2 commitment that this example operationalizes is
[`DESIGN.md`](../../DESIGN.md) §7.1.1 schema layer's
"**adjacent output shapes the schema layer subsumes**":
hierarchical labels — the canonical "top-level + sub-class"
pattern that classical taxonomy work treats as a separate
problem — absorb cleanly into the OUTPUT_SCHEMA contract via
JSON Schema's conditional structures. The methodology
generalizes; the bookkeeping doesn't expand. Per-field metrics
work on the two fields without modification; the per-field-
floor on `top_level` reflects the operational asymmetry
(top-level routing is unrecoverable; sub-category is
recoverable inside the right team) that the user articulated
during consultation. The locked-invariants inventory in
[`DESIGN.md`](../../DESIGN.md) §7.1.1 (bucket 6) confirms that
v0.2's schema-layer adjacent-shapes commitment is preserved
verbatim — this example is the operational form of that
commitment.
