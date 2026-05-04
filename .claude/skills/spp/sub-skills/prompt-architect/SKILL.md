# prompt-architect

A sub-skill of `spp` that explains the six-section XML
prompt template's structural roles, how each section gets
populated and evolves across iterations, and how the
structure integrates with the methodology's other
components. Read by the **designer agent** during
`/spp-init` consultation (when constructing
`prompt_v01.md`), by **Claude during `/spp-loop`** (when
generating discrepancy analysis and applying rule edits),
and by users wanting to understand the prompt-architecture
rationale.

This is the **third and final v1 sub-skill**, completing
the set after [`metric-design`](../metric-design/SKILL.md)
(Phase 2 step 4) and
[`baseline-quality`](../baseline-quality/SKILL.md) (Phase
2 step 5). It inherits the six-section structure pinned by
`metric-design` — identity → decision → decision tree →
worked examples → cross-skill constraint → output spec.

The doc is **shorter than `baseline-quality`** by design.
`baseline-quality` has gate-enforcement authority via its
three-tier verdict (`ready` / `revise` / `not-ready`);
`prompt-architect` is purely informational. The structural
discipline is enforced by
[`templates/prompt_v01.md.template`](../../templates/prompt_v01.md.template)'s
validation rules and by the auditor's per-edit judgment,
not by this sub-skill itself. Match the rigor to the role:
this is reference material, not a defense layer.

The temptation to make this sub-skill prescriptive about
content (persona length, rule wording, example shape) is
the failure mode. The sub-skill's value is **structural**:
which section a piece of content belongs in, when each
section evolves and by whom, what the auditor reviews in a
diff. Content prescriptions would convert it from a
methodology-aware reference into a writing guide, and the
conversion silently weakens its role. The auditor's
categorical-vs-row-specific judgment is the content-quality
layer; `prompt-architect` is the structural layer beneath
it.

---

## 1. Identity and scope

`prompt-architect` explains the six-section XML prompt
template's structure and methodology integration. It
helps the designer (during `/spp-init`) and Claude (during
`/spp-loop`) decide **which section a given piece of
content belongs in**, **which sections evolve in a given
iteration**, and **which sections are the auditor's
review surface**.

**In scope:**

- The six-section XML structure: `<persona>`, `<task>`,
  `<rules>`, `<output_format>`, `<example_input>`,
  `<example_output>`. The structure is fixed; this
  sub-skill explains its parts and their roles.
- When each section is initially populated, by whom, at
  which lifecycle stage.
- What evolves across iterations and what stays stable.
- The integration points with `metric-design`,
  `baseline-quality`, the auditor agent, and
  `REPORT.md.template` §5.
- Model-specific directives at the prompt's header (e.g.,
  `/no_think` for Qwen) — outside the six-section body
  but covered here for completeness.

**Out of scope:**

- **Content prescriptions** on what to write inside each
  section. The sub-skill explains structural roles, not
  writing style. Whether a persona should be one
  sentence or one paragraph, whether rules should use
  imperative voice, whether examples should be short or
  long — none of these are the sub-skill's concern.
  Content quality is the auditor's job (per `<rules>`
  edit) and the metric's job (per iteration).
- **Few-shot prompts** with multiple `<example_input>` /
  `<example_output>` pairs. v1 uses single-example
  shots; multi-shot would change the section count and
  the auditor's example-stability check. Roadmap
  consideration; out of scope here.
- **Chain-of-thought scaffolding** as a separate
  section (e.g., `<reasoning>` or `<thought>`). v1
  doesn't include CoT structure as its own section; if
  a model benefits from CoT, the `<task>` section can
  request "explain your reasoning briefly before the
  label" but the structural sections stay six.
- **Generation-task prompts** (instruction tuning,
  multi-turn conversation, tool-use). v1 is
  classification-only per `DESIGN.md` §7.1.
- **Prompt-injection defenses or jailbreak resistance.**
  Out of scope at the methodology level; users
  adopting the prompt for adversarial settings handle
  this separately.

**Cross-skill rule.** The six-section discipline is
**non-negotiable**. Iterations refine content within
sections; they do not add or remove sections. Full
elaboration in §5.

---

## 2. The decision the sub-skill helps make

Given a classification task being scaffolded by
`/spp-init` or evolved by `/spp-loop`, the sub-skill helps
answer:

> **What content goes into each of the six sections, and
> which section gets touched by which methodology stage?**

The output of consulting this sub-skill is **structural
guidance**:

- **Section identification.** "This user input belongs in
  `<rules>`, not `<task>`." The user provides content
  about *what to decide*; the sub-skill names where it
  goes.
- **Populate-or-leave-alone judgment.** "For this
  iteration's discrepancy analysis, the proposed edit
  goes into `<rules>`; `<persona>` and `<task>` should
  not change." The sub-skill names which sections an
  iteration's diff should touch.
- **Audit-surface awareness.** "This edit will be the
  auditor's primary review surface; expect a
  categorical-vs-row-specific verdict per edit." The
  sub-skill makes the auditor's review pattern visible
  *before* the auditor runs.
- **Revision recommendation when proposed content
  doesn't fit.** When a user (or Claude) proposes
  content that doesn't fit any section's role (see
  §4 Example 5), the sub-skill names the misfit and
  recommends one of: reformulate to fit a section,
  move the concern to `plan.md` §10, or accept the
  structure's discipline and don't include the
  proposed content.

The sub-skill does **not** produce content (specific
prompt text), does **not** judge whether the prompt is
good, does **not** output a verdict or score. The
designer (or Claude during `/spp-loop`) writes the
content; the auditor judges quality; the metric judges
performance. `prompt-architect` is structural reference
that informs where content goes and how the structure
interacts with the methodology.

---

## 3. The decision tree (the section walk)

A walk through the six sections, in template order. For
each section: **structural role**, **initial population**
(who and when), **evolution across iterations**, and
**methodology interaction** (what the auditor / other
sub-skills / templates expect of this section).

### §3.1 `<persona>`

The operator's posture for this task.

- **Structural role.** Anchor the model in a consistent
  voice and judgment style. One paragraph; not the place
  for decision criteria (those live in `<rules>`).
- **Initial population.** By the designer during
  `/spp-init` consultation, derived from `plan.md` §1
  (task overview, audience). The user can edit before
  G1 approval.
- **Evolution across iterations.** **Rare.** Most loops
  do not touch `<persona>` after iteration 1. A persona
  change typically signals the loop has discovered the
  original framing was wrong, which is a methodology
  event worth flagging in `plan.md` §11.
- **Methodology interaction.** The auditor reviews
  persona changes as full-section edits, not categorical-
  vs-row-specific. A persona edit is methodology-
  significant; if it appears in a discrepancy-analysis-
  driven edit, the auditor's verdict should be `unclear`
  with `clarify` recommendation (the user decides
  whether the original persona was the right framing,
  not the optimization loop).

### §3.2 `<task>`

What the model produces, in plain English, without
decision criteria.

- **Structural role.** State the action being requested
  (classify, label, route). One short paragraph.
- **Initial population.** By the designer during
  `/spp-init`, derived from `plan.md` §1 and §2
  `LABEL_SPACE`.
- **Evolution across iterations.** **Rare.** Same as
  `<persona>` — most loops do not touch `<task>`.
  Changes here typically indicate a scope drift that
  should surface in `plan.md` §11 rather than land
  silently in an iteration's prompt.
- **Methodology interaction.** Like `<persona>`, the
  auditor treats `<task>` edits as methodology-
  significant. A `<task>` edit appearing in iteration
  N's diff is a yellow flag — verdict `unclear` is the
  right default unless the change is a genuine
  clarification of the same action.

### §3.3 `<rules>` — the primary audit surface

Enumerated decision criteria.

- **Structural role.** The rules the model applies to
  produce labels. Each rule should be **categorical**
  (addresses a class of rows defined by an articulable
  property), **testable** (a labeler can apply it
  without guessing intent), and **non-redundant** (rules
  should not partially overlap; if they do, merge them).
- **Initial population.** By the designer during
  `/spp-init`, with sparse initial rules (3–5 typical).
  The loop grows this section.
- **Evolution across iterations.** **Constant.** This is
  the section the discrepancy analysis edits, the
  auditor reviews, and `REPORT.md` §5 audits in
  aggregate. Most iteration-to-iteration deltas live
  here.
- **Methodology interaction.** The auditor's
  categorical-vs-row-specific judgment operates **per
  `<rules>` edit** (see `agents/auditor.md` §4). Each
  new rule, modification, or removal gets a verdict.
  Categorical edits advance silently; row-specific edits
  are reverted or flagged for generalization (per
  `/spp-loop` §5's verdict-enforced gate). The cross-
  iteration check (auditor §3 step 4) reads prior
  auditor reviews to detect contradictions or scope
  changes in this section across iterations.

  A clean iteration's `<rules>` diff looks like
  additions and refinements to existing rules; a
  problematic iteration's diff looks like row-specific
  patches dressed up as rules (e.g., "rows containing
  the phrase 'X' should be Y" where 'X' appears only in
  the motivating row).

  The `baseline-quality` sub-skill's class-definition-
  drift check (its §3.1) operates **upstream** of
  `<rules>`: if the class definitions in `plan.md` §2
  don't match how labels were applied, no amount of
  `<rules>` evolution will produce a generalizable
  prompt. `prompt-architect` and `baseline-quality` are
  sequential defenses — `baseline-quality` checks the
  labels' integrity before the loop runs;
  `prompt-architect` provides the structure within
  which the loop's `<rules>` evolution happens.

### §3.4 `<output_format>`

What the model emits, parseable.

- **Structural role.** Define the exact output shape
  (JSON object, single-token label, structured field).
  The eval pipeline parses this output to compute
  metrics; format discipline is load-bearing.
- **Initial population.** By the designer during
  `/spp-init`, derived from `plan.md` §4 (the metric
  affects parseability requirements) and §2
  `LABEL_SPACE`.
- **Evolution across iterations.** **Avoid.** Output
  format changes mid-loop break the eval pipeline's
  assumptions and invalidate cross-iteration metric
  comparisons. If a format change is genuinely needed
  (e.g., the original format proved unparseable), the
  change is methodology-significant and should restart
  the loop's metric trajectory at the new format's
  iteration 1 — the per-iteration metrics under format A
  are not comparable to metrics under format B.
- **Methodology interaction.** The runner validates
  output format against this section during inference.
  A format change mid-loop should produce an `unclear`
  auditor verdict with a recommendation to revise — not
  a row-specific or categorical verdict, because the
  change isn't really a rule edit. The user resolves
  via `/spp-loop` §5's override path or by restarting
  the loop with the new format.

### §3.5 `<example_input>`

One representative input row.

- **Structural role.** Show the model what input shape
  to expect. One example per prompt; **not few-shot**.
- **Initial population.** By the designer during
  `/spp-init`, drawn from the **train** partition (NOT
  from dev, NOT from test — the example is data the
  model has metric-driven exposure to anyway). The
  example must be a clean, representative case — not an
  edge case.
- **Evolution across iterations.** **Rare.** A change
  here typically indicates a scope drift (the user
  realized the input shape they assumed was wrong) and
  is methodology-significant.
- **Methodology interaction.** The auditor verifies that
  the example input has not changed in unexpected ways.
  A change should produce `unclear`. The
  `baseline-quality` sub-skill's class-balance-reality-
  check (its §3.4) does not extend to the example input
  — but if the example input is from a row that gets
  relabeled during `baseline-quality` review, the
  example must be regenerated to maintain
  `prompt_v01.md` validation rule 5 (input and output
  correspond).

### §3.6 `<example_output>`

The correct output for the example input.

- **Structural role.** Show the model what good output
  looks like. **Must comply exactly with
  `<output_format>`.**
- **Initial population.** By the designer during
  `/spp-init`, paired with `<example_input>`.
- **Evolution across iterations.** Changes only when
  `<example_input>` changes. **Independent edits to
  `<example_output>` are an error** — they break the
  input/output correspondence required by
  `prompt_v01.md.template` validation rule 5.
- **Methodology interaction.** The auditor verifies
  input/output correspondence has not been broken. If
  `<example_output>` changed but `<example_input>` did
  not, the auditor's verdict is `unclear` with
  `clarify`.

### Model-specific directives (header)

Not one of the six sections, but covered here for
completeness.

- Lines like `/no_think` for Qwen models, prepended
  outside the XML body, are **model-locked**. They
  have meaning only for one model family and must be
  stripped on migration.
- **Initial population.** By the designer during
  `/spp-init`, derived from `loop_spec.md` §5
  `MODEL_DIRECTIVES`.
- **Evolution.** No evolution within a single loop.
  Migration to a different model strips these
  directives entirely.
- **Methodology interaction.** REPORT §7's model
  lock-in caveat names directives explicitly; the user
  is warned that these directives don't transfer
  cross-model.

### Section evolution at a glance

| Section | Evolves? | If it changes, what's the auditor's default verdict? |
|---|---|---|
| `<persona>` | Rare | `unclear` (methodology-significant) |
| `<task>` | Rare | `unclear` (methodology-significant) |
| `<rules>` | **Constant** | Per-edit `categorical` / `row-specific` / `unclear` |
| `<output_format>` | Avoid | `unclear` (cross-iteration metric incompatibility) |
| `<example_input>` | Rare | `unclear` (scope-drift signal) |
| `<example_output>` | Tied to `<example_input>` | `unclear` if changed independently |
| Model directives (header) | No | Strip on migration; not loop-evolved |

The asymmetry is intentional. The loop optimizes
**rules**; the rest of the prompt is the loop's stable
context.

---

## 4. Worked examples

Five generic scenarios that exercise the section walk
against realistic shapes. None references real source-
project content (`DESIGN.md` §7.2). Each example shows
the section being touched, the actor doing the touching,
and the methodology consequence.

The fifth example is a **refusal scenario** — the
sub-skill explains why a proposed edit doesn't fit any
section's role and recommends revision. The refusal
posture is the methodology discipline; allowing silent
acceptance of misfit content turns the sub-skill into a
checklist that approves anything.

### Example 1: `<rules>` evolution across iterations (happy path)

**Setting.** A binary task ("Relevant" / "Not Relevant"
for a billing-team triage queue). Iteration 3's
discrepancy analysis surfaces a cluster of rows that the
prompt mislabeled — tickets mentioning "subscription"
in the context of a *podcast* subscription (not the
billing product's subscription). The prompt classified
them `Relevant` because rule 1 keyword-matches.

**Proposed edit.** Add to `<rules>`:

> Tickets that mention "subscription" or "subscription
> billing" only in the context of an external service
> (newsletter, podcast, third-party SaaS) the user
> consumes — not the billing product's own subscription
> features — are Not Relevant.

**Section consulted.** `<rules>`. The edit is a
decision criterion, not a posture (`<persona>`), action
(`<task>`), or format constraint (`<output_format>`).

**Methodology consequence.** The runner applies the edit
to `prompt_v04.md`. The auditor reviews. The rule's
stated condition — "external service subscription
mentions" — is articulable in plain English without
reference to specific motivating rows; the synthetic-rows
test (auditor §4) passes. **Verdict: `categorical`.
Recommendation: `keep`.** The edit advances silently;
iteration 4 runs against the new prompt.

This is the canonical happy path. `<rules>` grew by one
rule; the auditor approved. `REPORT.md` §5 will record
this as a categorical edit at iteration 3 → 4.

### Example 2: row-specific patch caught at the auditor

**Setting.** A multi-class task (Bug / Question /
FeatureRequest). Iteration 5's discrepancy analysis
identifies a single dev row mislabeled by the prompt —
an issue containing the phrase "minoxidil therapy" that
the prompt classified as `Question` but the user
labeled as `Bug` (the issue describes a defect in a
clinical-data export feature).

**Proposed edit.** Add to `<rules>`:

> Issues mentioning "minoxidil therapy" should be
> classified as Bug.

**Section consulted.** `<rules>`. The proposed text is
syntactically a rule.

**Methodology consequence.** The runner applies the
edit to `prompt_v06.md`. The auditor reviews. The
rule's stated condition — "issues mentioning
'minoxidil therapy'" — is a phrase-specific match that
will only fire on rows containing that exact phrase.
The synthetic-rows test (auditor §4): generate 5
hypothetical rows that should be classified `Bug`; do
they all mention "minoxidil therapy"? No — rows about
unrelated features may also be bugs. The rule's exact
wording would only trigger on the original motivating
row. **Verdict: `row-specific`. Recommendation:
`generalize`** — the auditor proposes that the
discrepancy analysis next iteration should articulate
the underlying categorical pattern (perhaps "issues
describing a defect in clinical-data feature behavior,
with a reproduction"), not the phrase match.

Per `/spp-loop` §5's verdict-enforced gate, the runner
reverts the edit in `prompt_v06.md` (rolling back the
specific change). Iteration 6 runs against the
reverted prompt. The defensive function worked: a
phrase match disguised as a rule was caught before
landing.

### Example 3: `<persona>` change as methodology event

**Setting.** A task originally framed during `/spp-init`
as "triage analyst" classifying support tickets into
priority classes. Iteration 7's discrepancy analysis
surfaces that the prompt is treating routing decisions
as classification when the user actually wants
prioritization — the per-class precision is high, but
the *meaning* of the classes (P0 / P1 / P2 / P3) is
operational priority, which the persona "triage analyst"
doesn't anchor toward.

**Proposed edit.** Modify `<persona>`:

> ~~You are a triage analyst evaluating incoming support
> tickets...~~
> **You are a senior on-call engineer prioritizing
> incoming tickets for response order. You weigh
> customer impact, time-sensitivity, and reversibility
> in deciding priority.**

**Section consulted.** `<persona>`. The edit changes
the operator's posture.

**Methodology consequence.** The runner applies the
edit to `prompt_v08.md`. The auditor reviews. Per §3.1,
persona changes are methodology-significant; the
auditor does not apply the categorical-vs-row-specific
test (it is the wrong frame for a posture change).
**Verdict: `unclear`. Recommendation: `clarify`** —
the auditor's specific question for the user: "Was the
original `<persona>` framing wrong, or is the
discrepancy analysis attempting to fix at the persona
level a problem that lives in `plan.md` §1 task
overview?"

The user resolves at the `/spp-loop` §5 override
prompt: revise `plan.md` §1's task framing (and §2's
class definitions, since "priority" classes have
different meaning than "category" classes), restart
the loop with the new persona at iteration 1. The
methodology event is recorded in `plan.md` §11; the
prior 7 iterations' artifacts are preserved for audit
but the SUCCESS path no longer runs through them.

### Example 4: `<output_format>` change mid-loop

**Setting.** The runner's eval pipeline starts failing
at iteration 4 because the model occasionally emits
markdown fences (` ```json `) around the JSON output.
The pipeline's parser was not built for fences. The
discrepancy analysis identifies the parsing failure as
the cause of metric movement (failures count as
mispredictions).

**Proposed edit.** Modify `<output_format>` to add:

> No markdown fences. No surrounding prose. Output
> only the JSON object, with no leading or trailing
> whitespace.

**Section consulted.** `<output_format>`. The edit is
a format constraint, not a rule.

**Methodology consequence.** Per §3.4, output format
changes mid-loop break cross-iteration metric
comparability. The runner applies the edit to
`prompt_v05.md`. The auditor reviews. **Verdict:
`unclear`. Recommendation: `clarify`** — the auditor's
specific question: "This is a format change, not a
rule edit. Should the loop's metric trajectory restart
at this iteration's format, or should the change be
treated as a workaround documented in `plan.md` §11?"

Two valid resolutions:

(a) **Restart trajectory.** Treat
    `prompt_v05.md` as the new iteration 1. Prior
    iterations' metrics are preserved in `runs/<model>/`
    but excluded from the SUCCESS-path metric
    comparison.
(b) **Document and continue.** Record the format
    change in `plan.md` §11 with a note that
    pre-change-iteration metrics may have been depressed
    by parsing failures; continue the loop and accept
    the metric discontinuity in REPORT §7's
    limitations.

The user picks at `/spp-loop` §5's override prompt.
Either path is honest if documented.

### Example 5: refusal — proposed edit doesn't fit any section's role

**Setting.** During `/spp-init` consultation, the user
says: *"Let's add a rule that says 'try to be balanced
and avoid biased outputs.'"*

**Section consulted.** The user expects the proposed
text to land in `<rules>`. The sub-skill examines:

- **Does it fit `<rules>`?** A rule must be
  categorical and testable. "Try to be balanced and
  avoid biased outputs" is neither — there is no
  articulable property in plain English that lets a
  labeler determine whether a row is biased; there is
  no testable condition.
- **Does it fit `<persona>`?** Persona is a posture,
  not an exhortation. "Be balanced" is a directive,
  not a voice or judgment style.
- **Does it fit `<task>`?** Task is the action being
  requested (classify, label, route). "Avoid biased
  outputs" is not an action.
- **Does it fit `<output_format>`?** Format is the
  shape of the emitted output (JSON, single-token
  label). "Avoid biased outputs" is not a format
  constraint.

**Recommendation.** The sub-skill **does not silently
accept** the proposed edit as a `<rules>` line. Three
revision paths:

(a) **Reformulate as a testable categorical rule.** If
    the user's underlying concern is that the model
    might use demographic identifiers as classification
    signal, articulate the rule that operationalizes
    the concern — for example, "If the input contains
    demographic identifiers (age, gender, ethnicity,
    nationality), output the label without referring
    to the identifier in the rationale field." This is
    categorical, testable, and lands cleanly in
    `<rules>`.
(b) **Move to `plan.md` §10 as an open question.** If
    the concern is about deployment-time fairness
    auditing — a separate downstream review the user
    plans to do before shipping — record it as a
    `KNOWN_LIMITATIONS` entry, not a prompt rule. The
    bias-audit step is not part of the optimization
    loop.
(c) **Accept the structure's discipline and don't
    include the exhortation.** If the concern is
    aspirational ("I want the model to be a good
    citizen") without a concrete operationalization,
    the right answer is to acknowledge the structure's
    discipline — the prompt is for classification, not
    for ethics commentary — and not include the text.

The refusal is the **discipline**. A prompt-architect
that silently accepts misfit content as a rule line
produces prompts whose `<rules>` section contains
exhortations that look like rules but cannot be tested,
which corrupts the auditor's categorical-vs-row-
specific judgment downstream (an exhortation can be
called neither "categorical" nor "row-specific" — it
is simply not a rule). The downstream corruption
silently weakens the methodology; the upstream refusal
prevents it.

---

## 5. The cross-skill constraint — the six-section discipline is non-negotiable

**The structure is fixed.** The six sections, in this
order, are what the methodology operates on:

1. `<persona>`
2. `<task>`
3. `<rules>`
4. `<output_format>`
5. `<example_input>`
6. `<example_output>`

Plus the optional model-specific directives header,
outside the six-section body.

The auditor expects diffs at the section level; the
template's validation rules check section presence and
order;
[`templates/prompt_v01.md.template`](../../templates/prompt_v01.md.template)
validation rule 2 checks the exact six tags in the
exact order; `REPORT.md` §5's audit aggregates
verdicts per `<rules>` edit.

### What this rules out

- **Few-shot prompts** with multiple `<example_input>`
  / `<example_output>` pairs. v1 is single-shot;
  multi-shot would change the section count and the
  auditor's example-stability check (which compares
  one example pair across iterations). Roadmap
  consideration; not v1.
- **Chain-of-thought scaffolding** as a separate
  section (`<reasoning>` or `<thought>`). v1 doesn't
  include CoT structure as its own section. If a model
  benefits from CoT, the `<task>` section can request
  "explain your reasoning briefly before the label" —
  the structural sections stay six. (Note: model-
  specific directives like Qwen's `/no_think` operate
  on a separate axis and live in the header, not the
  body.)
- **Tool-use or function-calling prompts.** Out of
  scope for v1's classification focus.
- **Free-form prompts that don't fit the XML
  structure.** If a task genuinely doesn't fit (e.g.,
  the user wants a multi-paragraph generation task),
  the answer is "v1's `prompt-architect` doesn't
  apply; consider a v0.2+ generation-task
  methodology." The sub-skill's refusal posture
  applies at the structural level too.

### What this allows

- **Section content variation.** The structure is
  fixed; the content is not. Personas can be one
  sentence or one paragraph; rules can be 3 or 30;
  examples can be short or longer (within reason for
  context windows). The discipline is on the
  **structure**, not the content.
- **Model-specific directives at the header.** These
  are outside the six sections and are explicitly
  model-locked.
- **Iteration-driven `<rules>` evolution.** The whole
  point of the loop is to evolve `<rules>` across
  iterations under auditor governance. The sub-skill's
  discipline does not constrain how `<rules>` grows; it
  only constrains *where* growth happens (in
  `<rules>`, not by adding a new section).

### Cross-references to the other sub-skills

- [`metric-design`](../metric-design/SKILL.md) operates
  on `plan.md` §4 (metric selection), which feeds into
  `<output_format>` (parseable output for metric
  computation) and `<rules>` (decision criteria reflect
  the metric's optimization target). A metric that
  privileges precision will surface different
  `<rules>` evolution patterns than a metric that
  privileges recall — but the structural section is
  the same.
- [`baseline-quality`](../baseline-quality/SKILL.md)
  operates on `data/baseline.csv` and `plan.md` §2
  (class definitions), upstream of `<rules>`. Class-
  definition refinements during `baseline-quality`
  propagate to `<rules>` revisions in the next loop
  iteration. The two sub-skills are sequential
  defenses: `baseline-quality` checks the labels'
  integrity *before* the loop runs;
  `prompt-architect` provides the structure within
  which the loop's `<rules>` evolution happens.
- The sub-skill set is now **closed at three**.
  `metric-design` (which metric to optimize),
  `baseline-quality` (whether the baseline is ready
  to optimize against), `prompt-architect` (how the
  prompt's structure operates across the
  methodology). Each justified by a structurally
  distinct decision. Adding a fourth requires
  answering the same kind of distinctness question
  the agent set's closure raised — see "Pattern
  observations" below.

---

## 6. What the sub-skill outputs

When the designer (or Claude during `/spp-loop`)
consults `prompt-architect`, the output is **structural
guidance**, not content:

- **Section identification.** "This belongs in
  `<rules>`, not `<task>`."
- **Populate-or-leave-alone judgment.** "For this
  iteration's discrepancy analysis, the proposed edit
  goes into `<rules>`; `<persona>` and `<task>`
  should not change."
- **Audit-surface awareness.** "This edit will be the
  auditor's primary review surface; expect a
  categorical-vs-row-specific verdict per edit."
- **Revision recommendation when proposed content
  doesn't fit.** Per §4 Example 5 — name the misfit,
  recommend reformulation / move to `plan.md` §10 /
  decline to include.

The sub-skill does **not** output:

- **Content.** Specific prompt text. The designer (or
  Claude) writes content; the sub-skill explains where
  content goes. A `prompt-architect` that produces
  prompt text on demand has crossed the structural-
  vs-content line and is doing the auditor's job
  (judging quality) without the auditor's information-
  isolation discipline.
- **A verdict on whether the prompt is good.** That is
  the auditor's job (per `<rules>` edit) and the
  metric's job (per iteration). `prompt-architect` is
  structural reference, not quality judgment.
- **A score or confidence value.** The sub-skill is
  informational, like `metric-design`. There is no
  gate-enforcement surface here.
- **An iteration-driven rule edit.** The discrepancy
  analysis proposes edits; the sub-skill explains
  where they go. Edits originate from the loop, not
  from this sub-skill.

### Cross-references to artifacts

- [`templates/prompt_v01.md.template`](../../templates/prompt_v01.md.template)
  is the operationalized form of this sub-skill. The
  template's six-section structure is what this
  sub-skill explains. Validation rule 2 (the six tags
  in exact order) is the linter-level enforcement;
  validation rule 5 (input/output correspondence) is
  the manual-review-at-PR enforcement.
- [`agents/auditor.md`](../../agents/auditor.md) §4
  (the categorical-vs-row-specific judgment pattern)
  is the audit layer that operates on this sub-skill's
  `<rules>` section. The two are tightly coupled — the
  sub-skill's structural discipline is what makes the
  auditor's judgment frame coherent.
- [`agents/designer.md`](../../agents/designer.md) §5
  invokes this sub-skill during `/spp-init`
  consultation when constructing the initial
  `prompt_v01.md`.
- [`commands/spp-loop.md`](../../commands/spp-loop.md)
  §4 step 10 (apply rule edits) invokes this
  sub-skill during discrepancy-analysis-driven prompt
  edits — the LLM applying edits consults
  `prompt-architect` to confirm where each proposed
  edit belongs.

---

## Pattern observations

`prompt-architect` is the **third and final v1
sub-skill**. The pattern lock from
[`metric-design`](../metric-design/SKILL.md) and
[`baseline-quality`](../baseline-quality/SKILL.md)
applies — six-section structure (identity → decision →
decision tree → worked examples → cross-skill
constraint → output spec), methodology-affecting
changes flagged as breaking, worked examples with at
least one refusal case.

### v1 sub-skill set is now closed at three

- `metric-design` — which metric to optimize.
- `baseline-quality` — whether the baseline is ready
  to optimize against.
- `prompt-architect` — how the prompt's structure
  operates across the methodology.

Each justified by a structurally distinct decision:
metric selection, baseline integrity, prompt
structure. Adding a fourth sub-skill requires
answering the structural-distinctness question — what
decision does this sub-skill help make that none of
the existing three does? The bar is high. A fourth
decision that fits the methodology's shape is
unlikely; one that doesn't fit would be a
methodology change rather than a sub-skill addition.

### `prompt-architect` is the first sub-skill without verdict-enforcement authority

- `metric-design` doesn't have a verdict either, but
  it operates on a one-shot decision (which metric to
  use) at consultation time; its output feeds `plan.md`
  §4 directly.
- `baseline-quality` has gate-enforcement authority
  via its three-tier verdict (`ready` / `revise` /
  `not-ready`); `/spp-baseline` §5's verdict-enforced
  gate honors it.
- `prompt-architect` is **purely informational
  reference material**. The structural discipline is
  enforced by the templates' validation rules and the
  auditor's per-edit judgment, not by this sub-skill
  itself.

The asymmetry is intentional. Verdict enforcement is
the heaviest mechanism in `spp`'s vocabulary; it is
reserved for components whose judgment must gate
advancement (`baseline-quality`, the auditor). A
structural reference like `prompt-architect` does not
need gate teeth — its discipline lands at the
template-validation and auditor-review layers, where
the operational mechanisms already exist.

### After this PR

Phase 2 has **one step remaining**: the top-level
`SKILL.md` router (Phase 2 step 11). After that, Phase
2 is structurally complete and Phase 3 (worked
examples) follows.

---

## Versioning

Same rule as the predecessor sub-skills.

### Methodology-affecting (= breaking)

- **Removing one of the six sections** or adding a
  seventh. The structure is fixed; changes break the
  auditor's diff-review pattern, the templates'
  validation rules, and `REPORT.md` §5's aggregation.
- **Allowing few-shot prompts** with multiple
  `<example_input>` / `<example_output>` pairs. Would
  change the section count and the auditor's example-
  stability check.
- **Allowing the sub-skill to silently accept proposed
  edits that don't fit any section's role.** The
  refusal-and-recommend-revision posture (per §4
  Example 5) is the discipline; allowing silent
  acceptance turns the sub-skill into a checklist that
  approves anything, and the methodology's structural
  layer is degraded to formatting.
- **Removing the `<example_input>` / `<example_output>`
  correspondence requirement.** Validation rule 5 is
  what makes the example a coherent demonstration;
  loosening it lets examples drift into mismatch.
- **Allowing the sub-skill to start outputting content
  prescriptions** (specific prompt text, persona
  templates, rule wording recommendations). The role
  is structural; the moment it produces content, the
  line between `prompt-architect` and the auditor
  blurs.
- **Allowing `<rules>` edits to land without passing
  through the auditor's categorical-vs-row-specific
  judgment.** The audit surface is what this sub-skill
  hands off to; bypassing the auditor is breaking
  against `agents/auditor.md`'s contract too.

### Behavioral (= non-breaking)

- Better worked-example phrasing.
- Adjusting per-section guidance (e.g., refining the
  description of when `<persona>` evolution is
  methodology-significant) as long as the structural
  roles are preserved.
- New cross-references.
- Clearer language about the cross-skill interactions
  in §5.
- Adding a sixth or seventh worked example that
  exercises a different section-evolution shape, as
  long as no example violates the discipline by
  silently accepting misfit content.

When in doubt, treat the change as breaking.

---

## Cross-references

- [`agents/designer.md`](../../agents/designer.md) —
  the agent that invokes this sub-skill during
  `/spp-init` consultation for initial prompt
  construction (designer §5).
- [`agents/auditor.md`](../../agents/auditor.md) §4 —
  the agent whose categorical-vs-row-specific judgment
  operates on `<rules>` edits per iteration. The two
  components are tightly coupled — this sub-skill's
  structural discipline is what makes the auditor's
  judgment frame coherent.
- [`templates/prompt_v01.md.template`](../../templates/prompt_v01.md.template)
  — the operationalized form. Validation rules 2
  (six-section presence + order), 3 (matching tags),
  4 (`<rules>` non-empty), 5 (input/output
  correspondence), 6 (output complies with format), 7
  (model-directive comments) are the linter-level
  enforcement of this sub-skill's discipline.
- [`sub-skills/metric-design/SKILL.md`](../metric-design/SKILL.md)
  — peer sub-skill. Cross-skill interaction: metric
  choice feeds `<output_format>` and indirectly
  `<rules>`.
- [`sub-skills/baseline-quality/SKILL.md`](../baseline-quality/SKILL.md)
  — peer sub-skill. Cross-skill interaction: class-
  definition refinements propagate to `<rules>`
  revisions in the next loop iteration.
- [`commands/spp-init.md`](../../commands/spp-init.md)
  — where the initial prompt gets constructed. The
  designer reads this sub-skill during consultation.
- [`commands/spp-loop.md`](../../commands/spp-loop.md)
  §4 step 10 — where `<rules>` evolves per iteration.
  The LLM applying edits consults this sub-skill to
  confirm where each proposed edit belongs.
- [`templates/REPORT.md.template`](../../templates/REPORT.md.template)
  §5 — where edits to `<rules>` are aggregated for
  audit (per-iteration verdicts summarized).
- `DESIGN.md` §4.2 (the auditor's information
  isolation, which depends on `<rules>` being the
  primary edit surface), §10 glossary (categorical
  rule edit, row-specific rule edit).
- `CLAUDE.md` §4 (Semantic Commits — applies to
  changes to this sub-skill), §8 (auditor information
  isolation — applies indirectly: this sub-skill's
  structural discipline is what enables the auditor's
  judgment to operate cleanly).
