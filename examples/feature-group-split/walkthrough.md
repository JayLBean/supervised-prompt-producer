# Walkthrough — feature-group-split

A narrative walk through the feature-group splitting principle's
default case. The placeholder domain is customer-feedback analysis:
each input is a customer-feedback excerpt and the user wants three
structured signals — sentiment, topic, urgency — used to drive
different downstream processes (sentiment dashboards, topic-based
routing to product teams, urgency-based escalation rules). All
numbers, examples, and specific decisions are illustrative; the
example is a skeleton per [`DESIGN.md`](../../DESIGN.md) §7.2.

---

## Task framing

A customer-feedback row is a plain-text excerpt. The user wants
three signals computed per row:

- **Sentiment** — affect classification (positive / negative /
  neutral). Feeds a customer-satisfaction dashboard.
- **Topic** — content categorization (product / service / billing
  / other). Routes the feedback to the relevant team's queue.
- **Urgency** — operational prioritization (immediate / normal /
  low). Triggers escalation rules.

A v0.1.0 reading of this task would produce one prompt covering all
three signals — three fields in one OUTPUT_SCHEMA. The v0.2 multi-
field bookkeeping (per [`DESIGN.md`](../../DESIGN.md) §7.1.1)
supports this, and the bucket-7
[`examples/multi-field-extraction/`](../multi-field-extraction/)
example exercises exactly that pattern for a different domain.

But the feature-group splitting principle ([`DESIGN.md`](../../DESIGN.md)
§10 glossary entry, post-bucket-7 addition) says: when the three
signals require **different reasoning patterns** on the same input,
the methodology defaults to one prompt per group. The reasoning is:

- Affect classification (sentiment) reads for tone signals — word
  choice, emoji, exclamation density, hedging.
- Content categorization (topic) reads for what the feedback is
  *about* — product names, service mentions, billing terminology.
- Operational prioritization (urgency) reads for severity markers
  — "broken," "down," "lost data," timestamps suggesting outage,
  customer-impact language.

Three different cognitive operations on the same input. The
principle says: split the prompt by group. Each sub-task gets its
own `spp/` task directory, its own `plan.md`, its own optimization
loop, its own frozen prompt. The user composes the three prompts in
production.

---

## `/spp-init` walkthrough (the parent decomposition decision)

Per [`agents/designer.md`](../../skills/run/agents/designer.md)
§5.0 feature-group identification (post-bucket-7 addition), the
designer's first consultation step is to surface the
feature-grouping decision.

**Designer §4 strawman (illustrative).** The strawman names the
three signals (sentiment, topic, urgency) and proposes a unified
multi-field task as the v0.2 default. The user reviews.

**Designer §5.0 substep — Feature-group identification.** The
designer asks: "Do these three signals fall into groups by
reasoning pattern, input dependency, metric profile, or
hierarchical structure?"

The user articulates:

- **Reasoning pattern:** yes, three distinct patterns (affect /
  content / severity).
- **Input dependency:** shared input (the same feedback text feeds
  all three) — this would normally point toward keeping unified,
  but the reasoning-pattern split is strong.
- **Metric profile:** homogeneous (F1 or macro_F1 per field) —
  doesn't favor splitting on its own.
- **Hierarchical structure:** none.

The user and designer conclude the reasoning-pattern split is
decisive enough to recommend decomposition. Three sub-tasks:

- `sub-tasks/sentiment/`
- `sub-tasks/topic/`
- `sub-tasks/urgency/`

The current `/spp-init` session proceeds with the **first**
sub-task (the user picks sentiment). The remaining two sub-tasks
require separate `/spp-init` invocations.

**Parent-child relationship is the user's responsibility.** `spp`
does not enforce or track the relationship. The user organizes
sub-task directories under a parent name (this example uses
`examples/feature-group-split/sub-tasks/<group>/`); writes a
parent README and walkthrough that document the decomposition;
and owns the production-pipeline composition logic. `spp`'s
contract stays "one `spp/` task = one prompt = one optimization
loop."

---

## Per-sub-task workflow

Each sub-task runs the full four-phase methodology independently.
Because each sub-task is internally K=1 (single-output
classification), the workflow degenerates to v0.1.0's flow under
the v0.2 protocol — the per-field generalizations collapse to
their K=1 base case.

**`/spp-init`** runs with K=1:

- `schema-designer` returns `ready` on the one-field
  OUTPUT_SCHEMA. The mechanical layer ([`schema-designer`](../../skills/run/sub-skills/schema-designer/SKILL.md)
  SKILL.md §3.4) trivially passes for a one-field enum schema.
- `metric-design` ([`metric-design`](../../skills/run/sub-skills/metric-design/SKILL.md)
  SKILL.md §3) selects F1 or macro_F1 for the lone field based on
  the enum's value count. The §3.2 aggregate-strategy consultation
  produces `macro` (trivial K=1 identity). The §3.3 per-field-
  floor consultation produces a floor if the field's operational
  economics warrant — e.g., the sentiment sub-task may carry no
  floor, the urgency sub-task may carry a floor on the `immediate`
  class's recall.
- G1's dual check advances on the user's approval substring plus
  `schema-designer`'s `ready` verdict.

**`/spp-baseline`** runs with the sub-task's OUTPUT_SCHEMA:

- `baseline.csv` has the row identifier, the input body, and the
  one label column (the sub-task's field).
- [`baseline-quality`](../../skills/run/sub-skills/baseline-quality/SKILL.md)
  runs the per-field calibration on the single field — the §3
  protocol runs once, the within-field synthesis produces a
  verdict, the cross-field consolidation is the identity for K=1.
  The consolidated verdict gates G2.

**`/spp-loop`** runs the optimization loop. Per-iteration
`eval.json` carries the v0.2 shape ([`DESIGN.md`](../../DESIGN.md)
§7.1.1 metrics layer): `per_field` has one entry; `aggregate`
equals that entry's F1; `floor_compliance` has at most one row.
The auditor's per-edit-per-field verdict scoping collapses to
per-edit-per-lone-field, equivalent to v0.1.0's per-edit scope.
`SUCCESS.md` or `EARLY_STOP.md` lands as in v0.1.0.

**`/spp-finalize`** generates the sub-task's REPORT. §2 has one
per-field subsection (equal to v0.1.0's §2 content); §3's
per-field trajectory equals the aggregate trajectory; the
floor-compliance block has at most one row; §5's invariant block
is verbatim from the template.

---

## Cross-sub-task discipline

The three sub-tasks are independent — different `plan.md` files,
different baselines, different optimization loops. But the
maintainer keeps them coordinated through three lightweight
disciplines:

- **Naming convention.** `feature-group-split-<group>` for each
  sub-task's `TASK_NAME` in §1; `sub-tasks/<group>/` for the
  directory. This makes it obvious from `git log` and directory
  listings that the three sub-tasks belong to one parent.
- **Per-sub-task prompt scoping** per
  [`prompt-architect`](../../skills/run/sub-skills/prompt-architect/SKILL.md)
  SKILL.md §5 (sub-task scoping note). Each sub-task's
  `prompt_v01.md` `<persona>` is specific to the sub-task's
  reasoning pattern (sentiment's persona is an affect classifier;
  topic's persona is a content router; urgency's persona is an
  operational prioritizer). The `<rules>` section addresses only
  the sub-task's field. Cross-group rules do not appear in any
  sub-task's `<rules>` — they live in the parent's composition
  layer.
- **Independent baselines.** Each sub-task is labeled
  independently. The same body text may appear across sub-task
  baselines (since the production input is shared), but the
  labels in each baseline reflect that sub-task's field only.
  Cross-sub-task label consistency is the user's responsibility
  — `spp` does not enforce it.

---

## Composition (out of `spp`'s scope)

After all three sub-tasks reach `/spp-finalize` and produce frozen
prompts, the user composes them in their production pipeline.
Typically a script that:

1. Reads an incoming customer-feedback record.
2. Calls each of the three frozen prompts against the same input
   body — three separate model invocations (parallelizable;
   independent).
3. Merges the three structured outputs into a single record (e.g.,
   `{sentiment, topic, urgency}` keyed under the row's
   identifier).
4. Routes the merged record downstream — sentiment to the
   dashboard, topic to the team queue, urgency to escalation.

`spp` does not manage this composition. The principle's
[`DESIGN.md`](../../DESIGN.md) §10 glossary entry explicitly says
"cross-task composition is out of `spp`'s scope — `spp` produces
production-grade prompts, and the user owns the production
pipeline that composes them." The composition logic above is
illustrative; production pipelines vary widely and the methodology
intentionally does not prescribe a shape.

---

## A note on granularity

Feature-group splitting is the default for multi-field tasks where
groups are **identifiable**. The principle is about identifying
**natural** groups, not maximally fine-grained decomposition.
Empirical fieldwork shows the pattern: significant gains on the
first split (monolithic prompt → feature-group prompts), diminishing
returns on further subdivision (feature-group prompts → sub-group
prompts). When considering whether to subdivide a group further,
the question is whether the sub-groups have **distinct reasoning
patterns of their own** — not whether they could mechanically be
separated. Over-splitting adds coordination overhead without
delivering proportional optimization headroom.

This example demonstrates the **first split**: a unified
customer-feedback task decomposed into three natural feature
groups (sentiment, topic, urgency). The decision *not* to
subdivide further is intentional and worth naming explicitly,
because the mechanical-separability test is misleading:

- **`topic` could be split** into `topic-product` /
  `topic-service` / `topic-billing` / `topic-other` (one prompt
  per class). It is *not* split because each class is a value
  within one coherent reasoning pattern (content
  categorization), not a separate feature group. The reasoning
  operation the `topic` prompt performs is the same regardless
  of which class the row lands on; splitting per class would
  fragment that operation across four prompts with no
  corresponding gain in focused `<rules>` content or auditor
  scoping.
- **`urgency` could be split** by severity level (one prompt
  per `immediate` / `normal` / `low`). It is *not* split for
  the same reason — severity classification is one coherent
  reasoning operation; the rules that distinguish
  active-blocker from routine apply uniformly across the
  classes.
- **`sentiment` could not even be mechanically split** in this
  task because its enum (`positive` / `negative` / `neutral`)
  doesn't decompose along a different axis; there's no
  underlying field dimension that would make per-class prompts
  produce different reasoning patterns.

The first split (the one this example demonstrates) is across
**distinct cognitive operations** — affect classification,
content categorization, operational prioritization. Each
operation has its own persona, its own rules, its own
optimization trajectory. Further subdivision would split within
a single cognitive operation, which is what diminishing returns
is about. The principle's `DESIGN.md` §10 glossary entry frames
this as identifying groups by **reasoning pattern, input
dependency, metric profile, or hierarchical structure**;
mechanical separability isn't on that list, and that's
deliberate.

---

## What this example teaches about the methodology

This example is the operational form of the feature-group
splitting principle's **default case**. The two bucket-7
examples — [`examples/multi-field-extraction/`](../multi-field-extraction/)
and [`examples/nested-schema/`](../nested-schema/) — exemplify the
**exception cases** (unified multi-field tasks where splitting
doesn't apply because input dependency is shared and reasoning
patterns are similar enough, or because hierarchical conditional
reasoning lives most naturally in one prompt). The three together
cover the principle's full shape: when to split, when not to
split, and what the consultation step at
[`designer.md`](../../skills/run/agents/designer.md) §5.0
produces in each branch.

The methodology unchanged from v0.1.0 / v0.2:

- Per-stage information isolation in each sub-task's `/spp-loop`.
- Sacred test set in each sub-task's `/spp-finalize`.
- Verdict-enforced gates in each sub-task (G1 schema-designer dual
  check; G2 baseline-quality verdict; G4 auditor verdict; G5/G6
  finalization and ship gates).
- Six-section prompt structure scoped to each sub-task's field.
- `plan.md` as the contract per sub-task, re-read fresh by each
  sub-task's phases.

What changes is the unit of work: instead of one `spp/` task
producing one prompt that covers K fields, the user runs N
`spp/` tasks producing N prompts that each cover K' ≤ K fields.
The methodology principles stay output-shape-agnostic;
feature-group splitting is a principle about how users structure
their `spp/` tasks, not about what any one task does internally.
