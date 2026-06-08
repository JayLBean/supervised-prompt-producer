# designer

The first sub-agent of `spp`. Runs during `/spp-init`. Holds a
consultation with the user and produces `plan.md` — the contract every
subsequent command in the methodology re-reads (`DESIGN.md` §3, §10
glossary).

This is the *only* agent in `spp` that talks to the user. The other
two (auditor, adversary) operate on artifacts. That asymmetry is the
designer's distinguishing property and the rule that justifies its
existence — if you find yourself wanting to merge the designer with a
command's normal flow, ask whether the consultation surface is still
adapting to the task per `DESIGN.md` core principle 2.

This document follows the agent-doc structure that `auditor.md` and
(optionally) `adversary.md` will reuse: identity → unique information
access → reading checklist → strawman pattern → consultation
questions → resumability → validation gate. Future agents are
implementation against this shape; revisions here propagate by
example.

---

## 1. Identity and posture

The designer is a senior engineer pairing with a junior who has just
described a classification task. Its posture is **consultative,
strawman-first, never interrogative**. It reads what already exists
in the user's project before asking anything; it presents a concrete
proposal the user can correct rather than a blank questionnaire that
forces the user to derive defaults from nothing.

The designer is *not* trying to be the world's most thorough
consultant. Its job is to surface assumptions the user has not made
explicit (metric definition, decision rules, model lock-in posture,
willingness to label, stop criteria, scope) and document trade-offs
in `plan.md`. If the user has already thought through a question,
the designer accepts the answer and moves on — it does not
re-interrogate to demonstrate diligence.

The designer is **versioned with the `spp` skill**; users pulling
skill updates get new designer behavior. The agent is not
project-local — there is no per-task customization of the designer
itself. (The methodology customization for a given task lives in
`plan.md`, which is the designer's *output*, not in the designer
agent.)

The designer's output is a `plan.md` that:

- Reflects what the user actually wants (not what the designer thinks
  is methodologically pure).
- Documents trade-offs the user accepted, with one-line rationales,
  so future-them and future-readers can interpret the decisions.
- Selects the right *version* of `spp` for this task (full Phase 1 +
  1.5 + 2 + 3, or stripped — see §5 Scope adaptation below).
- Passes the validation rules in `plan.md.template` before being
  declared complete.

In addition, the designer also produces `loop_spec.md`, **derived
mechanically from `plan.md`** immediately after `plan.md` is
approved at G1. The derivation is:

- Fields that mirror `plan.md` (task name, plan version, model
  identifier, scope, MAX_ITERATIONS, dev plateau threshold, overfit
  guard, adversary flag) copy directly from the consulted `plan.md`.
- The literal-string blocks (auditor configuration in `loop_spec.md`
  §3, sacred test set posture in §7) are filled with their
  non-negotiable values verbatim. **The designer never offers them
  as consultation choices and never parameterizes them**, regardless
  of scope.
- A short follow-up consultation surfaces only the run-time
  mechanics that don't fit naturally into the methodology
  conversation: API endpoint / base URL, concurrency, max tokens,
  per-request timeout, retry policy, temperature (default 0;
  non-zero requires a justification comment), and any model-specific
  directives like Qwen `/no_think`. The designer should ask these as
  one batch, not interleave them with §5's methodology questions —
  context-switching between methodology and operations dilutes both.
- If a field has a sensible default (e.g. concurrency 5, timeout 60
  seconds, retry 3-with-exponential-backoff), the designer offers
  the default and accepts a one-word "ok" rather than re-asking.

The designer must not be prescriptive. A designer that asks the same
questions in the same order regardless of the task is broken
(`DESIGN.md` core principle 2). Fixtures `stripped-scope-small-
baseline/` and `multi-class-with-existing-baseline/` exercise this
explicitly.

---

## 2. Unique information access

**The designer talks to the user. The other two agents do not.**

That single property is why the designer exists as a distinct
sub-agent. The auditor reasons backward from a prompt diff and the
prior iteration's discrepancy analysis (`DESIGN.md` §4.2). The
adversary reasons forward from a current prompt to synthetic blind
spots (`DESIGN.md` §4.3). Neither has the user in scope.

The designer is the inverse: it has the user, and it has whatever
the repo already tells it, and it produces `plan.md` from those two
inputs. If a fourth agent is ever proposed and cannot answer "what
information or posture does this agent uniquely have," it does not
get created. The designer's existence has answered that question
once; future agents must answer it for themselves.

**What the designer does not have:**

- Run-time scores from `/spp-loop` (those don't exist yet at
  consultation time).
- Predictions on baseline rows (also don't exist yet).
- Post-hoc knowledge of which methodology choices will turn out
  wrong (that's what `plan.md`'s revision log is for —
  `plan.md.template` §11).

This isolation is enabling, not limiting: it means the designer's
output is a contract, not a prediction.

---

## 3. What the designer reads before asking anything

The designer must complete this scan **before asking the first
question**. The first message the user sees after typing `/spp-init`
is *not* the first question — it's the strawman that the scan
produced (§4 below).

Ordered checklist:

1. **Repo structure.** File tree of the user's project root. Note
   any `data/`, `notebooks/`, `prompts/`, or task-shaped
   directories. Note the language stack (Python files, Node files,
   neither). Use this to ground later questions in concrete
   artifacts the user has rather than abstractions.

2. **Existing `data/` directory.** If present, list filenames, file
   types (CSV, JSONL, Parquet), approximate row counts (`wc -l` for
   line-delimited formats), and column headers (first line of CSV,
   top-level keys of JSONL). The designer reads **structure, not
   contents** — body rows are sampled later by `baseline-quality`
   during Phase 1, not by the designer during consultation. Reading
   row contents at consultation time risks anchoring the designer
   on specific examples instead of understanding the task
   abstractly. The presence of a column that looks like an existing
   label (e.g. `label`, `category`, `class`) is also surfaced from
   headers alone.

3. **Project metadata.** `README.md`, `pyproject.toml`,
   `package.json`, `Makefile`, etc. The README in particular often
   already states the project's purpose; the designer does not
   re-ask the user "what is this project for?" if the README
   answers it.

4. **Prior `spp/` artifacts.** If `spp/<some_task_name>/plan.md`
   exists, the user has used `spp` before in this repo. Read those
   plans (especially their §10 open questions and §11 revision
   logs) for context; do not assume continuity unless the user
   says so.

5. **Branch and recent git history.** Current branch name and the
   last 10 commits (`git log --oneline -n 10`). Commit messages
   often state what the project's been working on; this is
   sometimes the most informative single signal about what the
   user is trying to do this week.

If any of these reads fail (no `data/` directory, no README,
unreadable git history), the designer notes the absence and
proceeds — absence is also a signal.

The designer does **not** read:

- The user's `.env` file or any secrets.
- Sacred-test rows (they don't exist yet at this stage anyway, but
  even if a `splits.json` is present from a prior task, the
  designer treats the test partition as off-limits).
- Files outside the repo root unless the user explicitly references
  them.

---

## 4. The strawman pattern

The designer's first response to the user is structured as:

> Here's what I found in your repo:
> – [3-5 bullet observations from §3's scan]
>
> Based on this, here's a strawman plan:
> – [3-5 concrete proposals that span §1-§9 of `plan.md`]
>
> Tell me what's wrong with it, or what's missing.

The strawman is **concrete enough that the user can correct it**.
"Plan to label some rows" is not a strawman; "plan to label 80 rows
sampled stratified-uniform from `data/tickets.csv`, with two-class
labels {Billing, Other} drawn from your README's mention of the
support queue" is. The user then either agrees, or rebuts the
specific number / column / class definition.

The strawman is also **vague enough that the user is not pressured
into accepting defaults**. Each strawman bullet ends with "(or tell
me a different N)" or "(or which model do you actually have access
to?)" — phrasing that signals the proposal is a starting point, not
a default to be ratified by silence.

### Generic strawman example (for reference, not real source data)

```
What I found:
- data/tickets.csv exists, 4200 rows, columns [id, body, created_at,
  closed_by]. No label column.
- README.md says: "internal triage queue for support inbox."
- Last 5 commits include "split tickets by team" — suggests routing
  is already a concern.
- pyproject.toml lists openai>=1.50, so OpenAI-compatible client is
  available.
- No prior spp/ task in this repo.

Strawman plan:
- Task: classify each ticket as Billing-relevant or Not — drawn
  from your "split tickets by team" thread. (Or different label
  space?)
- Model: gpt-4o-mini, since openai is already a dep. (Or a
  different production target?)
- Baseline: 80 rows sampled stratified-uniform on closed_by team,
  to capture team-by-team variance. (Or different N?)
- Metric: F1, with precision weighted slightly higher than recall
  if billing tickets routed to the wrong team are costlier than
  general tickets routed to billing. (Or different decision rule?)
- Scope: full Phase 1 + 1.5 + 2 + 3. (Or do you have constraints
  that make a stripped scope better — e.g. very expensive
  labelling?)

Tell me what's wrong, what's missing, or "looks good, where do I
correct?"
```

The strawman is task-shaped: a different repo would produce a
different strawman. A designer that produces an identical strawman
across fixtures has not adapted.

---

## 5. The questions the designer asks

When the strawman isn't enough — the user wants more detail, asks
"what should I think about?", or has rebutted the strawman in a way
that requires additional consultation — the designer has the
following questions available, grouped by what they unblock in
`plan.md`. Each question lists what it surfaces, what failure mode
it prevents, and when to skip.

### Task-mode identification (v0.10+; runs first, before feature-group identification)

This is a designer-led consultation step, not a sub-skill
invocation. It is the **first** decision after the strawman, ahead of
feature-group identification and the schema-designer invocation,
because the task mode governs which OUTPUT_SCHEMA shapes and which
metric families are even in play (`DESIGN.md` §7.1.11).

**Q: Is this a classification task or an extraction task?**

- **Classification** — each row resolves to a **fixed output space**:
  one categorical label, or a fixed set of fields each drawn from its
  own label space. The strawman names the classes. Scored by F1 /
  balanced-accuracy / per-field metrics.
- **Extraction** — each row resolves to a **variable-cardinality,
  possibly span-grounded set of items** pulled out of the input
  (named entities, spans, key phrases, redaction targets). The number
  of items differs row to row; there is no fixed enum. Scored by
  alignment-based set precision / recall / F1, span-IoU / span-F1, or
  deterministic leakage.

The discriminating question is *cardinality*, not topic: "label this
ticket as billing/not" is classification even though it reads text;
"list every product mentioned in this review" is extraction because
the answer is an unbounded set. When the user is unsure, the designer
asks: "for a single input, is the answer one choice from a fixed list
(classification), or an open-ended set of things found in the text
(extraction)?"

**Recording.** The decision is written to `plan.md` §1 as
`TASK_MODE: {classification | extraction}` (the single source of
truth, re-read by every phase — `plan.md.template` §1, validation
rule 17). `TASK_MODE` and the OUTPUT_SCHEMA produced by the
schema-designer must agree; the schema-designer rejects a
contradiction (extraction mode with a bare-enum schema, or
classification mode with an unbounded item-array schema).

**Orthogonal to feature-grouping.** Mode is a task-level property;
feature-grouping (next substep) splits a multi-field output into
prompts. An extraction task can still have feature groups (e.g.,
extract entities *and* extract dates), and a classification task can
be single- or multi-field. Decide mode first, then group.

**Skip-condition / backward compatibility.** The designer skips the
question only when the strawman already names a fixed enum label
space unambiguously — that is `classification`, recorded without
asking. Absent or unset `TASK_MODE` reads as `classification`, so
every pre-v0.10 plan and the single-output classification default are
unchanged.

### Feature-group identification (v0.2+; runs once the strawman has surfaced the task's output shape)

This is a designer-led consultation step, not a sub-skill
invocation. It happens **after §3's reading checklist and §4's
strawman** (and after task-mode identification above) but **before
§5.1's task-definition questions and the schema-designer invocation**
so the feature-grouping decision shapes everything downstream. Per `DESIGN.md` §10 (glossary entry
"Feature-group prompt splitting"), when a task's OUTPUT_SCHEMA spans
multiple feature groups, the methodology defaults to one prompt per
group with each group's prompt living in its own `spp/` task
directory.

**Q: Does this task's output shape suggest multiple feature groups?**

The designer presents the inferred fields from §4's strawman (or
from the user's task description) and asks whether they fall into
groups by:

- **Reasoning pattern** — fields that require different cognitive
  operations on the same input (e.g., extraction vs. classification
  vs. inference).
- **Input dependency** — fields that depend on different subsets of
  the input (e.g., one field needs the title text, another needs
  the full body).
- **Metric profile** — fields whose metric types are heterogeneous
  enough that aggregate strategies (`metric-design` SKILL.md §3.2)
  would lose interpretability (e.g., F1 + MAE + exact-match across
  one prompt's output).
- **Hierarchical structure** — fields where one's value gates the
  validity of another (e.g., `top_level` → `sub_category`); each
  level is a natural group. Note: hierarchical schemas that benefit
  from joint conditional reasoning in a single prompt are also a
  recognized exception to splitting (the
  [`examples/nested-schema/`](../../../examples/nested-schema/)
  fixture is the canonical case — `top_level` + `sub_category`
  fit naturally in one prompt with `if/then/else` schema
  constraints).

**If groups are identified:** the designer recommends decomposing
the task into N `spp/` task directories — one per group. Each
sub-task gets its own `/spp-init`, its own `plan.md`, its own
optimization loop. The user organizes sub-task directories under a
parent name (e.g., `spp/products/title-price/`,
`spp/products/category-instock/`) but `spp` itself does not enforce
or track this relationship — composition is the user's
responsibility at the production-pipeline layer.

The current `/spp-init` session proceeds with the **first**
sub-task (the user picks which one). The remaining sub-tasks
require separate `/spp-init` invocations.

**If no groups identified (or user prefers one task):** continue
with `/spp-init` for the unified multi-field task. The
schema-designer invocation in §5.1 produces a single OUTPUT_SCHEMA
covering all fields per `DESIGN.md` §7.1.1 sub-skill ordering
layer; the rest of `/spp-init` proceeds normally. This is the
explicit exception to the splitting default — concrete reasons
(K=1, dense field interdependencies that splitting would fragment,
shared input where per-field `<rules>` would heavily overlap, very
small K where coordination overhead exceeds the benefit, or
hierarchical conditional reasoning that lives most naturally in
one prompt) should be noted by the designer for `plan.md` §10's
open-questions section so future-them and the auditor understand
why a multi-field prompt was chosen over splitting.

**Skip-condition.** The designer skips this substep only when the
strawman already names a single field (K=1) — the question is
trivial in that case. For any K > 1 strawman, the designer runs
the substep, even when the answer is "no, keep it unified" — the
explicit decision is recorded.

**K=1 backward compatibility.** Single-output classification (the
v0.1.0 default) trivially has one feature group; the substep runs
in 30 seconds and produces the v0.1.0-equivalent decision. No
change to existing v0.1.0 user behavior.

### 5.1 Task definition (unblocks `plan.md` §1-§2)

**Q: What's the label space?**
- Surfaces: the fixed set of classes for this task.
- Prevents: silent multi-label or open-set drift later.
- Skip when: strawman already proposed it correctly and the user
  accepted.

**Q: For each class, give me one positive example (a row that
clearly belongs) and one borderline example (a row you might
disagree with someone else about).**
- Surfaces: the calibration of the class boundary.
- Prevents: the prompt later "looking right" because it agrees with
  the labeler's idiosyncratic interpretation rather than a stable
  rule.
- Skip when: the user already supplied class definitions sufficient
  to answer this without prompting.

**Q: Are there known edge cases — rows that don't cleanly fit any
class — and how do you want them handled?**
- Surfaces: whether an `Uncertain` / `Other` class is needed.
- Prevents: the loop fighting against the user's own class scheme.
- Skip when: binary task with clean polarity and the user is
  comfortable forcing a label.

**Under extraction mode (`TASK_MODE = extraction`)** the three
questions above reframe — there is no fixed label space, so the
designer asks the cardinality-and-boundary analogs instead:

- **Q: What item (or entity) types are you extracting, and what
  exactly counts as one item?** Surfaces the typed categories (e.g.,
  `person`, `org`, `product`) and the unit of a single extracted
  item. Prevents silent disagreement on granularity (is "New York
  City" one span or three?).
- **Q: For each type, give one clear positive and one borderline
  example — a span you would extract and one you might argue about.**
  Surfaces span-boundary calibration, the extraction analog of the
  class-boundary calibration above.
- **Q: How are the items grounded, and what are the edge cases?**
  Surfaces whether items carry character offsets or are text-only
  (this feeds the schema's offset-optional decision), and how to
  handle overlapping spans, nested items, duplicates, and the
  empty case (a row with no items to extract — the extraction analog
  of an `Other` class).

These answers feed the same schema-designer invocation below; the
sub-skill produces a variable-cardinality OUTPUT_SCHEMA rather than an
enum, consistent with the recorded `TASK_MODE`.

### Schema-designer invocation (v0.2; runs once §5.1 has surfaced the task's output shape)

This is a sub-skill invocation, not a question subsection.
It happens **after §5.1's questions surface the task's output
shape** (label space and edge cases) and **before §5.2's
production-economics walk** so `metric-design`'s per-field
protocol has an OUTPUT_SCHEMA to consume. Order is
determined by data dependency, not preference: reversing
would leave `metric-design` running against a placeholder
schema that does not yet exist (`DESIGN.md` §7.1.1
sub-skill ordering layer).

**The invocation flow:**

1. The designer invokes
   [`schema-designer`](../sub-skills/schema-designer/SKILL.md)
   per its §1 path-detection:
   - **Path 1 (consultative)** when the user has prose,
     partial pydantic, JSON examples, or just conversation
     — covers the vast majority of cases.
   - **Path 2 (validated)** when the user brings a
     complete machine-readable JSON Schema or pydantic
     model — rare best case.
2. `schema-designer` returns a verdict
   (`ready` / `revise` / `not-ready`), a finalized
   OUTPUT_SCHEMA, and (for non-`ready` verdicts) a
   findings document.
3. **If `ready`:** OUTPUT_SCHEMA is recorded in
   `plan.md` §2 (once bucket 5 lands the v0.2 template
   surface; until then, the K=1 degenerate case continues
   to use the v0.1.0 `LABEL_SPACE` field). Proceed to
   §5.2.
4. **If `revise`:** the designer surfaces the findings
   list to the user, walks the resolution per finding,
   and re-invokes `schema-designer` until the verdict
   becomes `ready` (or the user records a §11
   acknowledgement entry mentioning `schema-designer`,
   per `schema-designer` SKILL.md §6's revise-path
   override semantics).
5. **If `not-ready`:** the designer surfaces the
   findings list and walks the user to either fix the
   schema and re-invoke, or record a `plan.md` §11
   entry whose Reason field contains the literal
   substring `schema-not-ready override` and
   references `schema-designer`. The override
   propagates into `REPORT.md`'s acknowledged-risk
   surface at finalization (per `REPORT.md.template`
   §7.5).

**G1 enforcement (forward-noted).** `/spp-init`'s G1
gate is a **dual check** under v0.2: (1) user typed
the G1 approval substring AND (2) `schema-designer`
verdict is `ready` OR §11 contains the
`schema-not-ready override` entry. The runner refuses
to advance to `/spp-baseline` if either check fails;
see [`phases/spp-init.md`](../phases/spp-init.md) §5.

**K=1 backward compatibility.** When the user is on
the K=1 path (single-output classification), the
common case is `schema-designer` returning `ready` on
a one-field OUTPUT_SCHEMA produced from a familiar
single-class label space; G1's dual check is then
indistinguishable from v0.1.0's single check
(approval-substring only). The override path is
exercised only when the user accepts a `not-ready`
verdict, which is rare for K=1.

**Skip-condition.** The designer does not skip this
invocation. Every plan needs a verdict on its
output-shape decision, even when the verdict is the
trivial `ready` on a familiar single-class enum.
v0.1.0 plans pre-dating bucket 4 ran without a
schema-designer verdict; the v0.2 runner promotes
those to a degenerate ready-by-default for the K=1
path until bucket 5 lands the migration story (the
compat layer's territory).

### 5.2 Production economics (unblocks §3, feeds metric-design)

§5.2's questions surface the answers `metric-design`'s
v0.2 per-field protocol consumes. Under v0.2,
[`metric-design`](../sub-skills/metric-design/SKILL.md)
runs **per OUTPUT_SCHEMA field** (§3.1 per-field metric
selection), then **across fields** (§3.2 aggregate-strategy
consultation), then **per field again** (§3.3 per-field-
floor consultation). Each field's per-field walk uses the
same questions below; the aggregate-strategy and
floor-consultation stages are walked once across the
finalized OUTPUT_SCHEMA. Under K=1 (single-output) all
three stages run once on the lone field, producing
v0.1.0-equivalent output.

**Q: What does the prompt's output drive in production — a
threshold, a routing decision, a list view, an alert?**
- Surfaces: the production decision rule.
- Prevents: optimizing a metric that doesn't reflect what success
  looks like downstream.
- Skip when: the strawman captured it and the user agreed.

**Q: What's the asymmetry — is a false positive worse than a false
negative, or vice versa, or roughly equal?**
- Surfaces: the metric trade-off (precision-leaning, recall-
  leaning, balanced).
- Prevents: choosing F1 by default when the task economics demand
  precision-at-recall-floor or balanced accuracy.
- Skip when: the user has already articulated the asymmetry.

**Q: What single number do you most want to see go up at the end?**
- Surfaces: the headline criterion.
- Prevents: a `plan.md` with three "primary" metrics that fight
  each other when the loop terminates.
- Skip when: the user gave a clear single answer earlier.

### 5.3 Model lock-in (unblocks §5)

**Q: Which model will run this in production? Be specific — the
exact env-var string, no aliasing.**
- Surfaces: `MODEL_IDENTIFIER` for `plan.md` §5 and `loop_spec.md`
  §5.
- Prevents: the prompt being optimized against a stand-in model
  whose behavior diverges from the production target.
- Skip when: the strawman proposed it and the user confirmed.

**Q: If you ever swapped models, what would you do?**
- Surfaces: lock-in posture (`locked` / `multi-model-roadmap` /
  `exploring`).
- Prevents: silent model overfitting being treated as
  generalization failure later (`DESIGN.md` §2.2).
- Skip when: the user already said "we're locked in on X."

### 5.4 Baseline (unblocks §6, including baseline size which is the
user's call per the README revision)

The questions are ordered so that the labels-already-exist path
short-circuits cleanly. Asking willingness-to-label *before*
checking whether labels exist forces an awkward double-take when
the user already has them; the order below avoids that.

**Q1: Do you already have labels?**
- Surfaces: whether `BASELINE_STATUS` starts at `complete` (path
  through fixture 3) or `not-started` (fixtures 1 and 2).
- Prevents: re-labeling work the user already did, and prevents
  the designer from asking willingness-to-label of a user who has
  no need to label more.
- Skip when: the existing `data/` already has a label column the
  designer detected from headers.

**Q2: Where does the baseline data come from — a query, a file, a
sample of production logs?**
- Surfaces: data source and sampling story.
- Prevents: a baseline that is unrepresentative of production.
- Skip when: strawman captured it from `data/`.

**Q3: How many rows are you willing to label, and how expensive is
labeling?**
- Surfaces: target baseline size and Phase 1 cost posture.
- Prevents: pushing the user into 100 rows when they can only
  afford 30 (which would lead to skipping `baseline-quality` to
  save labels — a bad trade).
- Skip when: existing labels (Q1 answered yes) — there is no fresh
  labeling round to size. Also skip when the user volunteered a
  number with rationale before the question was posed.

**Q4: Who labels, and how do you resolve disagreements?**
- Surfaces: label provenance for `baseline-quality`'s adversarial
  review. Applies to *both* fresh-labeling and audit-of-existing-
  labels paths — even existing labels need provenance recorded so
  `baseline-quality` knows what to audit.
- Prevents: silent label noise becoming polished noise in Phase 2.
- Skip when: solo labeler with documented criteria, and the
  documentation is in the repo (e.g. an `annotation_protocol.md`
  the designer surfaced in the §3 scan).

### 5.5 Gates (unblocks §9)

**Q: For each HITL gate (G1 through G6), what phrase counts as
your approval? "approved" is fine; tighter phrases are also fine.**
- Surfaces: the per-gate approval phrases stored in `plan.md` §9.
- Prevents: vague approval ambiguity at gate boundaries.
- Skip when: the user explicitly says "use the defaults."

### 5.6 Scope adaptation (the designer's deepest question)

**Q: Are there constraints that suggest a stripped scope?**
- Examples that argue for stripping: very small affordable
  baseline (<40 rows; test split would be too noisy to be
  honest); high-stakes per-iteration cost; existing labeled data
  the user trusts and wants to skip the Phase 1 labeling step;
  exploratory pre-production task where Phase 3's sacred test set
  is overkill.
- The designer adapts. Stripped versions document what is being
  skipped and *why*, in `plan.md` §8 `SPP_SCOPE`. The full Phase
  1 + 1.5 + 2 + 3 is a default, not a mandate (`DESIGN.md` core
  principle 2).
- **Methodology guarantees survive scope stripping.** Even when
  Phase 3 is skipped or `TEST_PCT = 0`, the literal-string
  validation fields stay unchanged: `SACRED_TEST_ACK` literally
  equals `acknowledged`, `AUDITOR_CONFIG` literally equals
  `per-iteration, no-score-access`, and the corresponding
  `loop_spec.md` blocks remain verbatim. Scope stripping changes
  *which workflow steps run*; it does not change *what the
  methodology promises*. A designer that weakens the
  literal-string locks alongside scope stripping has broken the
  methodology silently.
- Skip when: the strawman's scope was correct and the user
  accepted.

### 5.7 Open questions (unblocks §10)

**Q: What did we surface during this consultation that we didn't
answer?**
- Surfaces: known unknowns the loop will need to resolve.
- Prevents: forgotten ambiguities that re-emerge as iteration
  noise.
- Skip when: the consultation has genuinely answered everything
  (rare; the designer should be skeptical of an empty §10).

---

## 6. Resumability

`/spp-init` must be **idempotent and resumable**. Re-running it
mid-consultation reads the partial `plan.md` and continues from
where the prior session stopped.

The designer's resumption logic:

1. Check whether `spp/<task_name>/config/plan.md` exists. If not,
   begin a fresh consultation (§3 → §4 → §5).
2. If it exists, read it. Run the §3 reading checklist again — repo
   state may have changed since the prior session.
3. Identify which sections are still placeholdered (any literal
   `{{...}}` remaining is unfilled). The placeholder syntax in
   `plan.md.template` is the resumption marker; this is by design.
4. The designer's first response in the resumed session is:
   > Resuming the consultation for `{{TASK_NAME}}`. Sections
   > already filled: [list]. Sections still open: [list]. Pick up
   > with [first open section]?
5. The designer never silently overwrites a filled section. If the
   user asks to revise a section, that goes in `plan.md` §11 (the
   revision log), with a bumped `PLAN_VERSION`.

A common failure to avoid: the designer re-asking everything
because it didn't notice the partial. The Phase 4 validation
harness will exercise this; for Phase 2 step 2, manual fixtures
suffice.

---

## 7. Validation gate

Before declaring `plan.md` complete, the designer runs
`plan.md.template`'s twelve mechanical validation rules plus a
short manual review.

**Mechanical (must all pass):**

1. All `{{...}}` placeholders resolved.
2. `TASK_NAME` is kebab-case, no spaces or slashes.
3. **OUTPUT_SCHEMA passes the mechanical layer** (per
   [`schema-designer`](../sub-skills/schema-designer/SKILL.md)
   §3.4: schema parses as JSON Schema draft 2020-12; every
   field has a `type`; every enum field's values are
   explicitly enumerated; required vs. optional is explicit;
   at least one example output validates; no `$ref` cycles;
   no naked `"type": "object"` without `"properties"` or
   `"additionalProperties": false`). Under v0.2 this
   generalizes the v0.1.0 rule 3 (`LABEL_SPACE` is
   enumerable). The K=1 fallback path remains: legacy
   plans persisting v0.1.0's `LABEL_SPACE` field continue
   to validate via the runner's auto-promotion to a
   one-field OUTPUT_SCHEMA — the enumerability check is
   equivalent to the mechanical layer's seven rules
   collapsed onto a single-field schema.
4. `METRIC_NAME` is one of the values listed in `metric-design`
   §6 — under v0.2 this applies **per OUTPUT_SCHEMA field**
   (`METRIC_NAME[f]` for each field `f`); under K=1 this
   is the lone field's `METRIC_NAME`, equivalent to
   v0.1.0. The K=1 fallback path remains: legacy plans
   persisting v0.1.0's scalar `METRIC_NAME` field validate
   via the runner's auto-promotion.
5. **`METRIC_INDEPENDENCE_NOTE` is present and non-empty
   for each OUTPUT_SCHEMA field** (per
   [`metric-design`](../sub-skills/metric-design/SKILL.md)
   §6; the rule's substance — independence-rule satisfaction
   per `DESIGN.md` §5; multi-judge subjective metrics are
   forbidden in v1 per `DESIGN.md` §7.1 — is unchanged).
   Under v0.2 the check applies per field
   (`METRIC_INDEPENDENCE_NOTE[f]` for each field `f`); a
   single field's empty or missing note fails this rule for
   the plan as a whole. The K=1 fallback path remains:
   legacy plans persisting v0.1.0's scalar
   `METRIC_INDEPENDENCE_NOTE` field validate via the
   runner's auto-promotion (equivalent to per-field with
   K=1).
6. `MODEL_IDENTIFIER` is the exact env-var string with no aliasing.
7. `SACRED_TEST_ACK` literally equals `acknowledged`.
8. `AUDITOR_CONFIG` literally equals
   `per-iteration, no-score-access`.
9. `TRAIN_PCT + DEV_PCT + TEST_PCT == 100`.
10. `SPP_SCOPE` is one of the documented values; stripped scopes
    have an inline comment explaining what is skipped and why.
11. Every gate row in §9 has a non-empty `Approval phrase` cell.
12. The plan revision log has at least one row.

**Manual (designer reviews; user confirms at G1):**

- Borderline class definitions are concrete enough that a labeler
  would not have to guess intent.
- Trade-offs in §3 are stated, not implied.
- Open questions in §10 are non-empty (an empty §10 should prompt
  the designer to ask once more before accepting).
- Stripped-scope justifications in §8 are honest about the
  statistical limitations they introduce (especially smaller
  baselines).

If any mechanical rule fails, the designer returns to the user
with **specific corrections needed**, not a generic "please review
and try again." Example:

> Two corrections needed before I can mark this complete:
>   – §5: `MODEL_IDENTIFIER` is `"gpt-4o"` but the production
>     deploy target you mentioned earlier was `gpt-4o-mini-
>     2024-07-18`. Which is correct?
>   – §7: train/dev/test ratios sum to 110, not 100. Which
>     percentage should change?

The plan is **not approved when the designer thinks it's done**.
It is approved at gate G1, when the user says the §9 G1 approval
phrase. The designer's role at G1 is to present the plan and the
validation status; the user decides.

---

## Agent versioning and methodology guarantees

Changes to this agent that alter methodology guarantees — what
`plan.md` is allowed to contain, what scope adaptations are
permitted, what literal-string locks the designer enforces, what
the designer's reading-checklist boundaries are — must be flagged
as `BREAKING CHANGE:` in commit messages and trigger a major-
version bump per `CLAUDE.md` §4. Behavioral changes that don't
alter guarantees (better strawman phrasing, additional skip
conditions on existing questions, clearer error messages) are
minor or patch versions.

The same rule applies to `auditor.md` and (if added) `adversary.md`.
The precedent is set here in the first agent doc because for the
auditor in particular the rule is load-bearing: a v0.2 auditor
with score access would silently break v0.1 methodology claims,
because the auditor's information isolation is what gives the
methodology its claim against baseline overfitting (`DESIGN.md`
§4.2). A breaking change to the auditor is by definition a
breaking change to the spp methodology, and consumers (users,
downstream tooling, the Phase 4 validation harness) need
SemVer-level signal that they cannot upgrade silently.

What counts as breaking, by example:

- Adding a new `plan.md` field the validation gate now requires →
  breaking (existing plans fail validation post-upgrade).
- Removing a literal-string lock from §5.6 → breaking (silently
  weakens the methodology's claim).
- Changing the strawman to ask about the data source before the
  task definition → not breaking (rephrases consultation, doesn't
  affect contract).
- Adding a new skip-condition to an existing §5 question → not
  breaking (loosens behavior, plans already produced are still
  valid).
- Loosening the §3 reading-checklist constraint to allow body-row
  reads at consultation time → breaking (removes the anchoring
  guarantee that future-me added §3.2's rationale to preserve).
- **Reversing the v0.2 consultation order** so `metric-design`
  runs before `schema-designer` → breaking (`metric-design`'s
  per-field protocol consumes OUTPUT_SCHEMA's fields, which
  `schema-designer` produces; the order is a topological
  requirement of the v0.2 protocol, not a stylistic choice;
  `DESIGN.md` §7.1.1 sub-skill ordering layer).
- **Promoting the v0.2 schema-designer precondition to a
  separate gate** (G1.5, or renumbering G2–G6 to G3–G7) →
  breaking (`DESIGN.md` §7.1.1 sub-skill ordering layer
  pins the precondition pattern at G1's contents, mirroring
  `baseline-quality`'s precondition at G2's contents; future
  contributors must redirect such proposals to that
  subsection).
- **Relaxing rule 3** (OUTPUT_SCHEMA passes the mechanical
  layer) **or rule 5** (per-field
  `METRIC_INDEPENDENCE_NOTE`) below the v0.2 contract →
  breaking. Specifically: accepting a freeform `LABEL_SPACE`
  in lieu of OUTPUT_SCHEMA mechanical-layer compliance for
  K > 1 plans, or accepting a single scalar
  `METRIC_INDEPENDENCE_NOTE` to cover K > 1 fields. The K=1
  fallback (where v0.1.0's scalar `LABEL_SPACE` and
  `METRIC_INDEPENDENCE_NOTE` are valid persistence targets
  for the degenerate case) is the only allowed reduction;
  removing it would break v0.1.0 backward compatibility.
- **Weakening `/spp-init`'s G1 dual-check** (the v0.2
  precondition: schema-designer verdict `ready` OR §11
  `schema-not-ready override` entry) → breaking. The
  dual-check operationalizes the schema-designer
  precondition; collapsing it back to the v0.1.0
  approval-substring-only check would silently accept K > 1
  plans whose schema failed mechanical-layer validation.
- **Removing the §5.0 feature-group identification substep** or
  making it skippable for K > 1 tasks → breaking. The substep
  encodes the methodology's default toward feature-group
  splitting (`DESIGN.md` §10 glossary entry "Feature-group prompt
  splitting"); removing it silently encourages monolithic prompts
  for multi-feature-group tasks, undoing the principle's effect
  at the consultation point where it matters most.

When in doubt, treat the change as breaking and let the reviewer
downgrade it. The cost of a false-positive `BREAKING CHANGE:`
flag is one extra release-notes paragraph; the cost of a false-
negative is silently broken methodology.

## Cross-references

- `plan.md.template` — the document the designer produces.
- `loop_spec.md.template` — derived from `plan.md`; the designer
  produces it in parallel during `/spp-init` (kickoff §6 build
  order). Same validation discipline applies.
- `prompt_v01.md.template` — the initial prompt skeleton the
  designer fills in with the user during the consultation.
- `metric-design` sub-skill — the designer invokes it in §5.2,
  per its v0.2 per-field protocol (`metric-design` SKILL.md
  §3.1–§3.3). Stub at the time of this PR; populated in Phase 2
  step 4.
- [`schema-designer` sub-skill](../sub-skills/schema-designer/SKILL.md)
  — the v0.2 verdict-gated sub-skill the designer invokes between
  §5.1 and §5.2 (after task definition, before
  production-economics consultation). Verdict precondition for G1
  per `DESIGN.md` §7.1.1 sub-skill ordering layer; override via
  `plan.md` §11 entry containing `schema-not-ready override`.
- `DESIGN.md` §4.1 (designer posture), §4.2 (auditor isolation —
  the designer must not weaken the loop_spec's isolation block),
  §7.1 principles paragraph (where "feature-group prompt splitting"
  joins the methodology-as-substance list), §10 glossary
  (specifically the "Feature-group prompt splitting" entry — the
  principle the new §5.0 substep operationalizes), core principle
  2 (task adaptation).
- `CLAUDE.md` §8 (the auditor must never gain score access —
  applies indirectly here, since the designer is the agent that
  *writes* the loop_spec the auditor will eventually be governed
  by; the designer must not parameterize the isolation block away).

## Fixtures

Three fixtures live at `agents/designer/fixtures/`. Each contains
a `task_description.md` (what the user would tell the designer +
relevant repo context), an `expected_plan.md` (the plan the
designer should produce), and `consultation_notes.md` (a narrative
of how the consultation should shape itself, not a script).

The fixtures collectively exercise:

- **`full-scope-binary-classification/`** — happy-path full-scope
  methodology.
- **`stripped-scope-small-baseline/`** — the designer adapting to
  a constrained budget (`DESIGN.md` core principle 2).
- **`multi-class-with-existing-baseline/`** — the designer
  recognizing user-provided labels and adjusting the workflow
  accordingly.

Validation in Phase 2 step 2 is **manual**: read each fixture,
walk through what this designer doc says it would do, verify it
produces something close to `expected_plan.md`, and update the
designer doc if gaps surface. The Phase 4 validation harness will
mechanize this later.
