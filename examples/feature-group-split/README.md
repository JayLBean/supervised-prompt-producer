# Example — feature-group-split

A v0.2 skeleton example exemplifying the **feature-group prompt
splitting** principle ([`DESIGN.md`](../../DESIGN.md) §10 glossary
entry). A customer-feedback analysis task with three feature groups
(sentiment, topic, urgency) is decomposed into three separate `spp/`
sub-tasks — one per group — each with its own `plan.md`, baseline,
optimization loop, and frozen prompt. `spp` manages each sub-task
independently; the user composes the three prompts at the
production-pipeline layer.

This is a skeleton in the [`DESIGN.md`](../../DESIGN.md) §7.2 sense
— file structure and walkthrough are real; data, baseline labels,
and prompt content are placeholder. The customer-feedback domain is
generic and pedagogically clear; it does not represent any real
source-project content.

## What this example teaches

The principle's **default case**: when a task's output spans multiple
feature groups whose reasoning patterns differ, splitting into N
sub-tasks (one prompt per group) buys focused `<rules>` sections,
per-group metric optimization headroom, clean auditor scoping, and
reusability. The three sub-tasks share input (the same customer-
feedback text flows into all three prompts) but require different
reasoning operations:

- **`sentiment/`** — affect classification: enum {positive, negative,
  neutral}. The persona reads for tone.
- **`topic/`** — content categorization: enum {product, service,
  billing, other}. The persona reads for what the feedback is about.
- **`urgency/`** — operational prioritization: enum {immediate,
  normal, low}. The persona reads for severity signals.

Each sub-task is internally K=1 (single-output classification — the
v0.1.0 degenerate case under the v0.2 protocol). The decomposition
is what makes this example exemplify the principle, not the
internal K-shape of any one sub-task.

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
subdivide further — e.g., splitting `topic` into `topic-product` /
`topic-service` / `topic-billing` — is intentional: each of those
is a **class within one coherent reasoning pattern** (content
categorization), not a separate feature group. The reasoning
operation the `topic` prompt performs is the same regardless of
which class the row lands on; splitting per class would fragment
that operation across four prompts with no corresponding gain in
focused `<rules>` content or auditor scoping.

## v0.2 components exercised

- **Bucket 1 — schema layer.** Each sub-task's `config/plan.md` §2
  carries an OUTPUT_SCHEMA with one enum field (the sub-task's
  scope). The schema-designer mechanical layer trivially passes for
  K=1 schemas.
- **Bucket 2 — metrics layer.** Each sub-task's `config/plan.md` §4
  carries a per-field metric sub-block (F1 or macro_F1 depending on
  the enum's value count) plus an aggregate-strategy block whose
  strategy (`macro`) is the identity on K=1.
- **Bucket 5 — compat layer.** Each sub-task's `config/plan.md`
  uses the v0.2 template surface (post-bucket-5).
- **Feature-group-splitting principle.** The parent-child
  relationship between the three sub-tasks is the principle's
  operational form. `spp` does not enforce or track the
  relationship — the user owns it via naming convention (`sub-
  tasks/<group>/`), the parent README and walkthrough, and the
  production-pipeline composition logic.

## Cross-references

- [`DESIGN.md`](../../DESIGN.md) §10 glossary entry "Feature-group
  prompt splitting" — the principle this example exemplifies.
- [`DESIGN.md`](../../DESIGN.md) §7.1 — the methodology-as-substance
  principles list (the principle joined the list post-bucket-7).
- [`agents/designer.md`](../../skills/run/agents/designer.md) §5.0
  feature-group identification — the consultation step the parent
  walkthrough cites.
- [`sub-skills/prompt-architect/SKILL.md`](../../skills/run/sub-skills/prompt-architect/SKILL.md)
  §5 sub-task scoping note — the scoping discipline each sub-task's
  six-section prompt follows.
- [`examples/multi-field-extraction/`](../multi-field-extraction/)
  and [`examples/nested-schema/`](../nested-schema/) — the bucket-7
  examples that exemplify the **exception case** (unified
  multi-field tasks where splitting doesn't apply because input
  dependency is shared and reasoning patterns are similar enough,
  or because hierarchical conditional reasoning lives most naturally
  in one prompt).

## Reading order

1. Start with [`walkthrough.md`](walkthrough.md). It walks the
   parent decomposition decision (designer's §5.0 substep) and then
   the per-sub-task workflow.
2. Scan the three sub-task directories
   ([`sub-tasks/sentiment/`](sub-tasks/sentiment/),
   [`sub-tasks/topic/`](sub-tasks/topic/),
   [`sub-tasks/urgency/`](sub-tasks/urgency/)) in any order. Each
   is a complete independent `spp/` task; the reader sees the same
   skeleton three times, distinguished only by its OUTPUT_SCHEMA
   scope.
3. End with the "Composition (out of spp's scope)" section of the
   parent walkthrough, which sketches what the production-pipeline
   composition layer looks like and why `spp` doesn't manage it.

All numbers in the sub-task REPORTs are placeholder; the example
does not represent a real run.
