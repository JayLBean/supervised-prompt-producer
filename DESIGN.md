# DESIGN.md — `spp` (Supervised Prompt Producing)

Phase 0 deliverable. This document records my understanding of the kickoff
in `DEVELOP_PLAN.md` before any code is written. It is the artifact under
review at the Phase 0 HARD STOP.

---

## 1. Skill purpose (one sentence)

`spp` is a Claude Code skill that produces production-grade classification
prompts through a disciplined, human-in-the-loop methodology — labeled
baseline, stratified split, dev-driven optimization loop with auditor
oversight, sacred test set, and reproducible per-model REPORTs — so that the
prompts it ships are defensible against both label-overfitting and silent
model-overfitting.

---

## 2. The two failure modes and how the skill defends against each

### 2.1 Baseline overfitting (deal-breaker; primary defense target)

The prompt learns the specific labels in the baseline rather than the
underlying class definition. Symptom: high score on the labeled set,
collapse on similar-but-unseen data. Cause: optimization loop edits the
prompt to chase rows that disagree with current labels, accumulating
row-specific patches that don't generalize.

**How `spp` defends:**

- **Stratified train/dev/test split with a sacred test set.** Test rows are
  not touched until Phase 3. Optimization sees train + dev only.
- **Dev-driven stop.** Loop terminates when dev F1 plateaus or regresses,
  not when train F1 looks good. Train-vs-dev divergence is itself a stop
  signal (overfitting early-stop guard).
- **Auditor sub-agent** (see §4). Every prompt edit is reviewed for
  *categorical vs row-specific* generalizability before the next iteration
  runs. This is the single highest-leverage defense; full treatment in §4.
- **`baseline-quality` sub-skill** in Phase 1. Adversarially reviews the
  labels themselves — bad baselines produce polished noise that no later
  phase can recover from.

### 2.2 Model overfitting (contextually acceptable; documented, not prevented)

The prompt learns to exploit one model's instruction-following style. The
source project produced a Qwen-locked prompt with `test F1 = 0.941,
recall = 1.0`. When the same prompt was run cross-family on the GPT line,
it scored F1 ≈ 0.76 on GPT-4o-mini and F1 ≈ 0.91 on GPT-4o full. The
cross-model failures clustered: on the three rows in cluster 4.4
(cross-family register-vs-addressee weighting), GPT-4o full *resolved the
shortest of the three* and *failed on the two longest*, while GPT-4o-mini
failed on all three. The failure is therefore **length-correlated, not
purely capability-related** — additional capability resolves the short
case but the longer rows remain failure modes for both GPT models. This
precision matters because the methodology's claim is not "bigger models
fix it" (they don't, fully) but "the prompt encodes a Qwen-specific
length tolerance that the GPT family does not share." This is fine if you
ship that prompt against that model in production; it is dangerous if you
swap models without re-validating.

**How `spp` defends:**

- **Per-model REPORTs.** Every run lives under `runs/<model_identifier>/`
  using the exact env-var model string, no aliasing. A prompt's score on
  model A is never silently attributed to model B.
- **Documented limitation, not prevented.** `REPORT.md` includes a
  "Limitations" section that explicitly states which model the prompt was
  optimized against and what cross-model fragility (if any) was observed.
- **Roadmap, not v1.** Multi-model dev loops are explicitly v0.4 work.
  Trying to defend against model overfitting in v1 would make the skill
  too expensive to use for the realistic case of "I have one production
  model and I want a good prompt for it."

The asymmetry between these two failure modes is intentional: baseline
overfitting destroys the methodology's claim to generalization; model
overfitting is a known scope boundary with mitigation via documentation.

---

## 3. Phases

Four methodology phases, each documented at `skills/run/phases/`, each
operating on `spp/<task_name>/` in the user's project. The user invokes
the skill once via `/spp:run <task-name>` (or by describing a
classification task); the agent that runs the skill walks the four
phases in order. The `/spp-*` slash-prefixed names are naming
convention for the phase docs, not slash commands the user types
separately.

| Phase | One-line purpose |
|---|---|
| `/spp-init` | Consultation: read repo, ask informed questions, produce `plan.md` (the contract). Idempotent and resumable. |
| `/spp-baseline` | Phase 1 + 1.5: label data with `baseline-quality` review, generate stratified `splits.json`. |
| `/spp-loop` | Phase 2: run optimization iterations with auditor (and optional adversary) active; stop on dev plateau or overfitting guard. |
| `/spp-finalize` | Phase 3: run sacred test set, generate per-model `REPORT.md` and `PROMPT_FROZEN_v01.md`. |

Each phase enforces its trailing HITL gate (G1–G6 in the kickoff) by
refusing to proceed without an explicit allowed response.

**`<task_name>` semantics:** the `/spp:run` invocation accepts an
optional task name as a positional argument (e.g.
`/spp:run hair-loss-discourse`). If omitted, the designer agent asks
for one as the first consultation question. The argument becomes the
directory name under `spp/` — kebab-case, no spaces, no slashes. Once
chosen, it is fixed for the duration of the task; renaming requires
manual directory rename and is out of scope for v1.

---

## 4. Sub-agents (with unique-information justification)

Three agents. Each is justified by *what information or posture this agent
has that none of the others do*. The kickoff's rule applies: if a fourth
agent is proposed and cannot answer that question, it does not get
created.

### 4.1 designer (runs during `/spp-init`)

**Unique information access:** the user. The designer is the only agent
that holds a conversation. It reads the repo to ground itself in what
already exists, then surfaces assumptions the user has not made explicit
(metric definition, decision rules, model lock-in posture, willingness to
label, stop criteria) and documents tradeoffs in `plan.md`.

**Posture:** senior engineer pairing with a junior. Strawman-first — read
the repo, present what was found, propose a default plan, ask the user to
correct rather than starting from a blank questionnaire.

**Why distinct from a generic LLM call:** the designer's job is consultation
*shaped to this specific task*. It must figure out which version of `spp`
applies — stripped-down (no Phase 3, smaller splits, judge-based metric)
versions are valid outputs. A non-adapting consultation is a failure.

### 4.2 Per-stage information isolation (the load-bearing design lock)

The single highest-leverage architectural property of the entire skill.
It is the design lock that distinguishes `spp` from automated optimizers
like DSPy and APE. The rest of the methodology is plumbing; per-stage
isolation is the methodology.

**The pattern.** Every cognitive stage in `/spp-loop`'s iteration runs
in an **isolated subagent** with an **explicit allow-list** of inputs.
The orchestrator constructs each subagent's invocation context from
that allow-list; the subagent's context terminates when it returns;
state flows between stages through files (the iteration's artifacts
under `runs/<model>/run_NN/`), **not through the orchestrator's main
context**. The orchestrator coordinates; cognition lives in subagents.

**The four isolated subagents per iteration:**

- **Discrepancy subagent** (after scoring; produces
  `discrepancy_analysis.md`). Sees: `eval.json`, `results.json`,
  `baseline.csv` filtered to disagreed dev rows, `plan.md` §2,
  current `prompt_v(N).md`. Does not see: prior iterations'
  artifacts, train rows that the model predicted correctly, test
  rows. The persistent artifact references rows by ID only; row
  content stays in this subagent's terminating context.
- **Rule-edit subagent** (after discrepancy + adversary; produces
  `prompt_v(N+1).md`). Sees: current prompt, `discrepancy_analysis.md`
  with row IDs but no row content, `plan.md` §2, the
  `prompt-architect` sub-skill. Does not see: `baseline.csv`,
  `eval.json`, `results.json`, prior iteration artifacts. **No row
  content reaches this subagent under any path** — this is the
  property the rule-edit step exists to enforce.
- **Auditor subagent** (after rule-edit; produces
  `auditor_review.md`). The most stringent specific instance of
  per-stage isolation; see "auditor's score-access prohibition"
  below. Sees: prompt diff (`prompt_v(N).md` and `prompt_v(N+1).md`),
  prior iteration's discrepancy, `plan.md` §2, prior auditor
  reviews. Does not see: the new iteration's scores, train/test
  labels, the sacred test set.
- **Adversary subagent** (when `ADVERSARY_FLAG = on`). Sees: current
  prompt, prior iteration's discrepancy, `plan.md` §2. Does not
  see: scores, sacred test set, baseline rows. Synthetic outputs
  do not persist to the baseline or splits.

**The load-bearing property.** Information isolation is not stylistic.
It is the methodology. If a cognitive stage in the iteration has
access to information beyond its allow-list, that stage can
rationalize behaviors driven by the leaked signal:

- A **discrepancy subagent** with prior-iteration artifacts can echo
  earlier proposals rather than reasoning fresh from current failure
  patterns.
- A **rule-edit subagent** with row-content access can produce rules
  that look categorical but were actually authored to fit specific
  rows (the leakage mode the per-stage architecture was designed
  against).
- An **auditor** with score access will rationalize any edit that
  improved the metric, including row-specific patches that overfit.
- An **adversary** with score access will generate adversarial rows
  driven by metric movement rather than blind-spot reasoning.

The absence of leakage at each stage forces each subagent to evaluate
on its merits — "would this discrepancy cluster apply to a similar
but unseen row?", "would this rule still apply to a similar but
unseen row?", "is this edit categorical?" — rather than via outcome
or surrounding context.

**The auditor's score-access prohibition (the most stringent instance).**
The auditor's allow-list excludes the new iteration's `eval.json` and
`results.json` even though both exist on disk by the time the
auditor runs (iteration order is edit → score → audit). Score
isolation is the most stringent of the four subagent allow-lists
because score-driven optimization is the path of least resistance
toward methodology breakage; the auditor's existence as the final
check makes its information isolation load-bearing in a way the
other stages' isolation is reinforcing rather than uniquely
load-bearing.

**The single question the auditor asks:**

*Is this rule edit categorical (addresses a class of rows defined by an
articulable property) or row-specific (patches one weird row)?*

- **Categorical edits** are kept. Example: "ambiguous short self-disclosures
  with no explicit context should be classified as Uncertain rather than
  Positive" addresses a definable class.
- **Row-specific edits** are flagged for either revert or
  generalization. Example: "rows containing the word 'minoxidil' followed
  by a question mark should be False" is a row-specific patch dressed up
  as a rule. The auditor either pushes back to find the underlying
  categorical property or recommends revert.

**Why this is high-leverage:**

Every other defense (split discipline, dev-driven stop, sacred test set)
catches overfitting *after* it has happened. The auditor catches it
*before* the next iteration commits to the patch. Iterations compound: a
row-specific patch in iteration 3 becomes load-bearing context for the
edits in iteration 4, and removing it later destabilizes the prompt. The
auditor's job is to keep iteration N's rule surface clean enough that
iteration N+1's edits are operating on a generalizable base.

**The temptation to break this (warning to future contributors):**

Future-me, future contributors, and any reviewer not steeped in this
design will be tempted to "improve" the auditor by giving it score
access. The reasoning will sound plausible: "if it could see the dev F1
delta, it could weight its categorical-vs-row-specific judgment by the
size of the improvement." This is the failure mode. The whole point is
that the auditor *cannot* be swayed by improvement size, because
improvement size is exactly the signal that row-specific overfitting
optimizes against. Score access turns the auditor from an independent
check into an optimization rationalizer. **Do not give the auditor score
access. The information isolation is the design.**

This restriction belongs in `auditor.md` as a non-negotiable directive,
not just here, so any future contributor editing the agent encounters it
in-place.

**Frequency is non-optional and per-iteration.** The auditor runs after
every iteration of `/spp-loop`. If per-iteration token cost becomes an
adoption barrier post-v1, the correct escape valve is **batch auditing**
(the auditor reviews the diffs and discrepancy analyses of the last N
iterations as a group, still without score access), **not frequency
reduction**. Batching preserves the information-isolation property;
reducing frequency would silently skip categorical-vs-row-specific review
on some iterations, exactly the failure mode this agent exists to
prevent. Future contributors proposing a "run auditor every N iterations"
knob should be redirected to the batch-auditing design instead.

**Posture:** detached reviewer. Not collaborating with the loop, not
trying to be helpful to the optimization. Skeptical, with the authority
to flag and recommend revert. Closer to a code reviewer than a
pair-programmer.

### 4.3 adversary (runs after each `/spp-loop` iteration; optional)

**Unique information access / posture:** the only agent whose job is
*adversarial*. Reads the latest prompt and generates 2–3 synthetic
adversarial rows targeting its likely blind spots. Distinct from the
auditor because the auditor evaluates an existing edit's
generalizability; the adversary probes for weaknesses the prompt's
authors haven't considered yet.

**Why distinct from the auditor:** the auditor reasons backward from a
diff (was this edit categorical?). The adversary reasons forward from
the current prompt (where would this prompt fail on data it has not
seen?). Different direction, different posture.

**Important boundary:** synthetic adversarial rows are **not** added to
the baseline. They are a thought experiment to surface fragility before
production, not training data. Adding them to the baseline would corrupt
the test set and defeat the sacred-test-set guarantee.

**Output disposition (non-persistence).** Adversarial rows are surfaced
to the user *during* the iteration — either inline within the
discrepancy analysis or as a separate prompt to the user — and are
**not persisted as artifacts**. They do not get a file under `runs/`,
they do not appear in `baseline.csv`, they do not enter `splits.json`,
and they are not referenced in `REPORT.md`. The reasoning is symmetric
with the no-baseline rule: persisting adversarials creates the temptation
to grade against them later, which would turn a thought experiment into
an unblessed test set with none of the labeling rigor of the real one.
If a particular adversarial row turns out to represent a real failure
class the user wants in the baseline, the user collects similar *real*
data and adds it through the labeling process, not by promoting the
synthetic row.

**Configurability:** opt-in via `plan.md`. Enable for high-stakes tasks
where false-negative cost is high; skip for low-cost or
exploratory tasks where the auditor and dev metric are sufficient.

### What is *not* a sub-agent (do not create)

- **optimizer** — running the iteration loop is the loop's normal
  behavior. There is no cognitive job here that the loop runner doesn't
  already do; an "optimizer" agent would be ceremony.
- **executor** — running scripts is not a cognitive job.
- **documenter** — `REPORT.md` is templated output. It is generated, not
  authored.

---

## 5. Sub-skills

Three composable sub-skills, each independently useful outside `spp`:

| Sub-skill | One-line purpose |
|---|---|
| `prompt-architect` | Six-section XML template (Persona, Task, Rules, Output Format, Example Input, Example Output) for production-grade prompts. Ported from existing project. |
| `metric-design` | Guides the user through metric selection. Enforces the constraint that the metric must be computable independently of the model being optimized (no GPT-4 judging GPT-4 prompts). |
| `baseline-quality` | Phase 1 adversarial review of labels themselves: inter-rater spot-checking on borderline cases, calibration questions, surfacing baseline noise before it becomes invisible polish in Phase 2. |

For v1 these live nested at `skills/run/sub-skills/` (see §7
open questions).

---

## 6. Build order with Phase 2 leverage rationale

The kickoff's order, with rationale on why steps 1–2 are leveraged work:

1. **Templates** (`plan.md.template`, `REPORT.md.template`,
   `loop_spec.md.template`, `prompt_v01.md.template`).
2. **Designer agent**, validated against 2–3 hypothetical task fixtures
   (e.g. spam classifier, sentiment polarity, the canonical hair-loss
   port). If the designer asks the same questions in the same order
   regardless of task, consultation is not adapting — redesign.
3. **`metric-design` sub-skill.** Moved earlier than the kickoff's
   numbering because the designer agent in step 2 invokes `metric-design`
   during consultation. Building it as a stub and back-filling later
   would mean validating the designer against a placeholder, which
   defeats the validation. The honest dependency order is: templates →
   designer prototype → `metric-design` → designer integrated with real
   `metric-design` → `/spp-init`.
4. `/spp-init` command, integrating the designer.
5. `baseline-quality` sub-skill.
6. `/spp-baseline` command, integrating Phase 1 labeling and
   `baseline-quality`.
7. `auditor.md` agent.
8. `adversary.md` agent (optional).
9. `/spp-loop` command, integrating the auditor.
10. `/spp-finalize` command + REPORT generation.
11. `prompt-architect` sub-skill (port from source project).
12. Top-level `SKILL.md` router.

**Phase 3 example-naming convention (recorded here so it persists).**
Examples are named by *task type*, not domain. Four examples are on
disk after v0.2's planning arc closes and the post-bucket-7
feature-group-split addition lands:

- `examples/hair-loss-relevance/` (v0.1.0; the
  binary-classification skeleton, named by domain rather than
  task-type because the example was created before this convention
  was set — historical artifact, kept under its original name to
  preserve commit/issue history; a future re-cut as
  `examples/binary-classification/` is acceptable but not in
  scope for v0.2).
- `examples/multi-field-extraction/` (v0.2; covers multi-field
  structured-output classification with diverse field types,
  aggregate-strategy selection, and a per-field floor — exercises
  v0.2 buckets 1, 2, 3, 5; exemplifies the unified-multi-field
  exception case under the feature-group splitting principle in
  §10 glossary).
- `examples/nested-schema/` (v0.2; covers hierarchical labels via
  JSON Schema conditional structures, exercising the schema
  layer's adjacent-shapes commitment — exercises v0.2 buckets 1,
  2, 3, 5; exemplifies the unified-multi-field exception case
  under the feature-group splitting principle).
- `examples/feature-group-split/` (v0.2 post-bucket-7 addition;
  exemplifies the feature-group splitting principle's **default
  case** — a multi-field customer-feedback task decomposed into
  three sub-tasks (sentiment, topic, urgency), each in its own
  `spp/` task directory with its own `plan.md`, baseline,
  optimization loop, and frozen prompt; the parent README and
  walkthrough document the decomposition, the production-pipeline
  composition layer (out of `spp`'s scope), and the granularity
  guidance — first-split gains vs. diminishing returns on further
  subdivision).

Rationale: the examples form a methodology gradient (single-output
binary → unified multi-field structured output → unified
conditional/hierarchical → feature-group-decomposed), not a domain
catalog. A reader scanning `examples/` should see what each example
*teaches about the methodology*, not what subject matter it happens
to use. The three v0.2 examples are skeletons in the §7.2 sense —
file structure and walkthrough are real; data, baseline labels, and
prompt content are placeholder. The bucket-7 pair
(`multi-field-extraction`, `nested-schema`) exemplifies the
unified-multi-field cases where feature-group splitting doesn't
apply; the post-bucket-7 `feature-group-split` example exemplifies
the principle's default case where it does. The hair-loss-relevance
example is a fully-fleshed worked example with NDA-redacted real
artifacts, predating v0.2; per the §7.2 discipline, the v0.2
examples deliberately use no real-domain content.

**Why steps 1–2 are leveraged:**

The templates *define* what `spp` produces. If `plan.md.template` cannot
articulate the contract a designer is supposed to fill in, the designer
agent has no target to hit, and every command downstream re-reads a
contract that doesn't exist. Templates are the spec; everything else is
implementation.

The designer agent is the only piece of the system whose output cascades
into every subsequent command. A bad designer produces bad `plan.md`s,
and bad `plan.md`s silently corrupt baseline labeling, split decisions,
metric choice, stop criteria, and REPORT framing. Validating the designer
against multiple hypothetical tasks before any other command depends on
it is the cheapest place to catch a drift-into-questionnaire failure.

**Why the loop runner is not first** (the temptation to resist):

The loop runner is the largest chunk by line count and feels concrete.
But a working version exists in the source project — porting it is
mechanical. Building it first means writing it against templates and a
designer that don't exist yet, and reworking it once they do. It is the
lowest-risk piece, so it is built last among the major commands.

---

## 7. v1 scope statement

**Tasks:** Classification only — binary, multi-class, fixed-schema
labeling. Extraction, generation, RAG, and agentic prompts are roadmap
(v0.2+).

**Language:** English. This is documented in README's "When to use this"
section. Multilingual classification has its own design considerations
(tokenization, label-space localization, judge-language coupling) and is
deferred to a future scope question. The skill does not silently accept
non-English data — it states the assumption.

**Ecosystem:** Python. The dev environment is Python 3.11 / conda.
Worked examples in Phase 3 use `pandas`, `scikit-learn`, and an
OpenAI-compatible client. **This is a meaningful exclusion:** users
whose stack is Node-only, Go-only, etc. will find the skill's
methodology applicable but the worked examples and contributor
environment Python-bound. README should be honest about this.

**Distribution:** Open-source, MIT-licensed, GitHub. The skill itself is
not self-modifying — versioned templates copy into the user's project
and freeze for the duration of that task.

### 7.1 Non-goals: methodology vs. bookkeeping

`spp` has two layers, and they version on different timescales.

The **methodology** is the substance: per-stage information isolation
between the discrepancy / rule-edit / auditor / adversary subagents
(§4.2); the auditor's categorical-vs-row-specific judgment as the design
lock against score-driven row-specific patches (§4.2); the sacred test
set as the discipline against optimism in the headline number (§10);
the six-section prompt structure (§5); the verdict-enforced gates
(§4.2); `plan.md` as the contract every phase re-reads fresh (§10);
**feature-group prompt splitting** when OUTPUT_SCHEMA spans multiple
feature groups, with each group's prompt living in its own `spp/` task
directory (§10). These principles are **output-shape-agnostic**. They
apply to any supervised prompt-engineering task with a labeled
baseline.

The **bookkeeping** is the concrete instantiation: what `plan.md` §2
expects in the class-definition slot, which metrics `metric-design`
enumerates, what `/spp-loop`'s scoring step computes against, what
`REPORT.md`'s trajectory sections look like. v0.1.0's bookkeeping is
hardcoded for **single-output classification** — binary, multi-class,
or fixed-schema labeling where each baseline row resolves to one
categorical label. This is one specific instantiation of the
methodology, useful and complete within its scope.

The non-goals below are split between **roadmap items** (where the
methodology applies but the bookkeeping is intentionally narrow in
v0.1.0) and **deliberate non-goals** (where the methodology itself
does not apply or is incompatible). The distinction matters: a future
v0.x version eventually addresses roadmap items; deliberate non-goals
are scope boundaries the methodology will not cross.

#### 7.1.1 v0.2 — bookkeeping generalization for broader output shapes

The canonical v0.2 scope is **multi-field structured-output
classification**: each baseline row resolves to a structured object
(several fields, possibly nested) rather than a single categorical
label. The methodology principles transfer unchanged — per-stage
isolation, auditor judgment, sacred test set, six-section prompt
structure all apply to multi-field tasks; what changes is what the
bookkeeping records and scores.

**Bookkeeping changes by layer.** The v0.2 generalization is bigger
than a single change. It is partitioned into seven layers, each
locked in its own PR before downstream layers depend on it. The
layers are:

1. **Schema layer** — what `plan.md` records as the task's output
   shape. **Locked below.**
2. **Metrics layer** — how `metric-design` adapts to per-field
   metrics plus an aggregate. **Locked below.**
3. **Per-field methodology application layer** — how `/spp-loop`'s
   scoring step, `discrepancy_analysis.md`'s field-level
   attribution, the auditor's per-field verdict scoping, and
   `REPORT.md`'s per-field trajectories adapt to a structured
   ground truth. **Locked below.**
4. **Sub-skill ordering layer** — where the new `schema-designer`
   sub-skill (locked below) lands in the consultation order, and
   how its verdict gate renumbers or interleaves with G1–G6.
   **Locked below.**
5. **Compat layer** — `plan.md.template` v0.2 surface
   generalization (carrying OUTPUT_SCHEMA, per-field
   definitions, the aggregate-metric headline, per-field
   metric blocks, the aggregate-strategy block, and per-field
   floor blocks); adaptation of the consumers that read those
   fields (`baseline-quality` per-field calibration;
   `/spp-baseline` invocation pattern; `/spp-finalize` v0.2
   read pattern); and the migration story for existing
   v0.1.0 `plan.md` files. **Locked below.**
6. **Locked-invariants inventory** — explicit list of v0.1.0
   methodology guarantees that v0.2 preserves verbatim or
   with shape-changes-but-substance-preservation (per-stage
   isolation invariants, sacred test set, verdict-enforced
   gates, six-section prompt structure, REPORT invariant
   block, etc.) so generalization does not silently weaken
   them. **Locked below.**
7. **Fixtures layer** — the canonical examples (`examples/`)
   that validate the v0.2 scope end-to-end: a
   multi-field-extraction task (covers diverse field types
   plus an aggregate-strategy choice and a per-field floor)
   and a nested-schema task (covers hierarchical labels via
   JSON Schema conditional structures, exercising the
   schema layer's adjacent-shapes commitment). **Locked
   below.**

All seven layers are locked below. The structure was
intentionally additive across the v0.2 planning arc — each
bucket's PR slotted into this frame without disturbing prior
buckets — and remains additive for future v0.x layers if
the methodology gains new bookkeeping shapes.

##### Schema layer

**OUTPUT_SCHEMA's home: `plan.md` §2.** The v0.1.0 `LABEL_SPACE`
field is replaced by an `OUTPUT_SCHEMA` block. §2 stays one
cohesive section so the auditor's "plan.md §2" allow-listed slice
(§4.2) stays cleanly addressable — no split into §2a/§2b. The
order inside §2 is OUTPUT_SCHEMA at the top, then per-field
definitions below: one paragraph per field naming what the field
means, positive and borderline examples, and edge cases. **The
per-field definitions are the v0.2 analog of v0.1.0's class
definitions**, and they get the same calibration treatment that
class definitions get under `baseline-quality` (§3.1 drift check,
§3.3 intuition-vs-rule check), applied per field.

**Schema language: JSON Schema (draft 2020-12).** Pinned
explicitly so future contributors do not reopen the question.
Rationale: it is the production standard for output schemas
(OpenAI structured outputs, Anthropic tool use, every emergent
agent framework); it natively handles nested objects and
conditional structures (`if/then/else`, `$ref`); validation
tooling exists in every language; pydantic and zod both emit it;
every existing-schema source format the user might bring (pydantic
models, TypeScript interfaces, Zod schemas, OpenAPI specs)
converts cleanly. Bespoke lighter formats end up reinventing
type/enum/required validation primitives the methodology gets
nothing for. The cost of pinning is negligible; the cost of
leaving it open is endless contributor litigation over a
non-load-bearing question.

**Surface format: YAML or JSON, user's choice.** OUTPUT_SCHEMA
renders into `plan.md` inside a fenced code block (` ```yaml ` or
` ```json `). The validator round-trips: a YAML-form OUTPUT_SCHEMA
is a YAML rendering of the same JSON Schema document; semantics
are identical, only syntax differs. The designer renders into
whichever the user picks during consultation. No third format,
no per-field surface (the whole schema commits to one).

**Single-output classification is a degenerate OUTPUT_SCHEMA.**
The v0.1.0-equivalent shape is one required enum field —
`{label: <enum of class names>}` — rendered explicitly. v0.2
chooses uniformity over UX cleverness: the single-class case
writes the same OUTPUT_SCHEMA shape as the multi-field case, just
with one field. No shorthand, no `LABEL_SPACE` legacy alias
inside the schema. (Migration of existing v0.1.0 `plan.md` files
to the v0.2 OUTPUT_SCHEMA shape is bucket 5, the compat layer;
mentioned here only so the absence of shorthand is not later
mistaken for an oversight.)

**Two paths for schema design**, mirroring the
BYO-labels-vs-fresh-labels fork that `baseline-quality` already
runs against (`baseline-quality` SKILL.md §1 in scope plus the
§3.6 provenance addendum that fires only on the BYO branch):

- **Path 1 — consultative.** The user has no, partial, or
  substantial context but no machine-readable artifact. The
  designer reads the repo, builds a strawman OUTPUT_SCHEMA, and
  the user corrects with whatever they bring — a full pydantic
  model pasted as text, a JSON example, a prose description, or
  just a conversation. The sub-skill extracts intent and renders
  OUTPUT_SCHEMA as JSON Schema (in the user's chosen surface
  format). This covers the vast majority of cases, including
  users who know what fields they want without having formalized
  them.
- **Path 2 — validated.** The user shows up with a complete,
  machine-readable JSON Schema or pydantic model that already
  describes the task's output. The sub-skill validates the
  artifact against the production rules below, runs the
  calibration walk on each field, and returns a verdict plus a
  finalized OUTPUT_SCHEMA. Rare best-case path.

Important framing for both paths: **"existing schema" in informal
use means context the user brings to Path 1** (pydantic models,
TypeScript interfaces, Zod schemas, prose in a doc) — not a
structured artifact in Path 2's sense. Only Path 2 takes a
structured artifact as input. The implication is that there is no
conversion-tooling burden on the sub-skill: pydantic, TypeScript,
and Zod all become paste-as-context during consultation, not
separate-format-converters the designer has to plumb.

**The `schema-designer` sub-skill: verdict-gated.** A new
sub-skill, peer to `metric-design` and `baseline-quality`. Its
planned home is `skills/run/sub-skills/schema-designer/SKILL.md`.
**Creation is deferred to a subsequent PR; this design PR locks
the contract.**

`schema-designer` inherits `baseline-quality`'s verdict-gate
pattern (`baseline-quality` SKILL.md §2): it returns one of
`ready` / `revise` / `not-ready`, and the verdict gates a new
gate slot between **G1 (plan approval) and G2 (baseline
approval)**. The exact gate placement and renumbering — whether
it lands as a new G1.5, whether G2/G3/etc. shift, whether it
folds into G1 — is the sub-skill-ordering bucket's decision
(covered in a subsequent v0.2 design PR). This PR pins the slot
as forthcoming, not its number.

The override substring follows the verdict-flavored pattern
`baseline-quality`'s `not-ready override` precedents
(`baseline-quality` SKILL.md §6). The exact substring is left for
the schema-designer creation PR. Whichever wording is chosen, the
override propagates into `REPORT.md`'s acknowledged-risk surface
(same shape as `baseline-quality`'s override propagation into
`REPORT.md` §7.2), so flagged-but-shipped schemas surface in the
methodology's transparency layer.

**Validation rules — two layers.** The contract `schema-designer`
runs against (both for Path 1's rendered schema and Path 2's
user-provided schema) is split into a mechanical layer and a
judgment-driven layer. The split is the reason the verdict gate
exists at all: mechanical rules do not need verdict mediation —
they pass or fail on parser output — while judgment rules cannot
be checked mechanically and require the sub-skill to return
`revise` or `not-ready` with specific findings.

*Mechanical layer (always run, regardless of verdict):*

- Schema parses as valid JSON Schema (draft 2020-12).
- Every field has a JSON Schema `type`.
- Every enum field's values are explicitly enumerated (no plain
  `string` where an enum is intended).
- Required vs. optional is explicit on every field (no implicit
  defaults).
- At least one example output validates against the schema (the
  schema-actually-describes-the-task test).
- No `$ref` cycles.
- No naked `"type": "object"` without either `"properties"` or
  `"additionalProperties": false`.

*Judgment-driven layer (the verdict gate's reason for existing):*

- Enum value-space is exhaustive for the task — covers the cases
  the user can name *and* the residual the task generates in the
  wild, not only the common cases.
- Field names are clear: a labeler reading the schema cold can
  label rows without guessing the field's intent.
- Borderline examples are concrete enough to disambiguate the
  field's intent — same calibration discipline as v0.1.0's class
  definitions, applied per field.
- The schema captures the relationships the task requires
  (conditional fields, nested fields, cross-field constraints)
  rather than flattening them.
- The schema is no broader than the task needs. Over-rich schemas
  invite scope drift; this is the analog of v0.1.0's discipline
  against an `Other` class as a dumping ground.

**Designer agent §7 mechanical-rule generalization
(forward-noted).** The designer agent's §7 validation gate
currently includes rule 3, "`LABEL_SPACE` is enumerable." That
rule generalizes to "**OUTPUT_SCHEMA passes the mechanical layer
above**." The actual `designer.md` edit is **deferred to the
breaking-change PR** that lands v0.2 code; this design PR does
not modify `designer.md`. Noted here so the rule generalization
is locked in design even though the file change comes later.

##### Adjacent output shapes the schema layer subsumes

The OUTPUT_SCHEMA shape pinned above is broad enough to absorb
two adjacent shapes without further bookkeeping work:

- **Hierarchical labels** (top-level + sub-class). Treatable as a
  two-field structured output where field 2 is conditional on
  field 1, expressed in JSON Schema via `if/then/else` or per-
  branch `$ref`.
- **Freeform extraction with structured ground truth**
  (named-entity extraction, span extraction with typed labels).
  Same OUTPUT_SCHEMA shape; per-field metrics (defined in the
  metrics layer below) adapt to span-level evaluation.

##### Metrics layer

**Per-field metric types: suggested by type, user-overridable.**
Each OUTPUT_SCHEMA field gets its own primary metric. The
adapted `metric-design` sub-skill suggests a metric based on
the field's JSON Schema type — illustratively, an `enum` field
suggests F1 (or `macro_F1` when the enum has more than two
values), a `string` field suggests exact-match, a `number`
field suggests MAE or RMSE, a `boolean` field suggests F1, an
array of typed values suggests set-F1 or IoU. The suggestions
are starting points, not policy: the user accepts the
suggestion or overrides per field, and the existing v0.1.0
decision tree (`metric-design` SKILL.md §3) runs per field for
asymmetry, class-balance, and operational-privilege questions
when the suggestion lands in the F1-vs-balanced-accuracy
neighborhood. The pattern is agent-as-expert with user override
— the same shape `schema-designer` applied at the schema layer
(bucket 1's Path 1 strawman-and-refine). The independence rule
(`DESIGN.md` §5; `metric-design` SKILL.md §5) applies per field
unchanged: each field's chosen metric is independently checked
against the cross-family-judge prohibition, and a single
field's violation is sufficient to fail the rule for the task
as a whole.

**Aggregate metric: user-chosen strategy.** When K fields each
have their own primary metric, the aggregate that takes
headline status in `plan.md` §3 is one of three strategies:
`macro-average` (per-field metrics averaged with equal weight),
`weighted-average` with user-specified weights per field, or
`min-over-fields` (the worst-performing field's metric becomes
the aggregate). `metric-design` walks the user through the
choice during consultation, with a strawman recommendation
based on metric homogeneity: uniform metric types (e.g., every
field is F1) suggest `macro-average`; mixed metric types (e.g.,
F1 + MAE) suggest `min-over-fields`. The sub-skill **must
refuse a nonsense aggregate** — for example, macro-averaging F1
(range [0, 1], higher is better) with MAE (range [0, ∞), lower
is better) produces a dimensionally meaningless number — and
surface the dimensional mismatch as a `revise` signal in its
consultation prose. `metric-design` remains review-and-record
per the sub-skill-adaptation decision below; the `revise`
signal here is documentary (it lives in the rationale and in
the consultation transcript), not gate-blocking.

**`plan.md` §3 headline criterion: aggregate plus optional
per-field floors.** The headline criterion gains two components
rather than one. Primary: the aggregate metric (decision above)
— the single number whose movement gates the optimization loop
and whose final value the headline reports. Secondary: optional
per-field floors on each field's primary metric (e.g., the
`category` field requires F1 ≥ 0.9). Floors are specified per
field during `metric-design` consultation; the sub-skill
suggests a floor for fields the schema marks as
required-and-unrecoverable — those where a wrong value cannot
be recovered downstream — and accepts user override or skip.
Many fields will have no floor; floors are the exception, not
the default. **Per-class-within-field floors** (the v0.1.0
source-project's `recall = 1.0 on the positive class` shape)
are not supported as a separate tier; users wanting that
pattern define the field's primary metric to *be* the
per-class metric (e.g., metric = `recall_on_class_X` rather
than `F1`) to achieve the same effect at one tier of
bookkeeping rather than two. The single-tier discipline keeps
the gate-evaluation logic at loop termination tractable and
keeps the headline-criterion shape uniform across single-output
and multi-field tasks. (The `plan.md.template` §3 surface text
that carries this generalization is bucket 5, the compat layer;
mentioned here only so a reader of v0.1.0's template
understands the §3 shape will widen but not gain a third tier.)

**Stop discipline: aggregate plateau gates the loop; per-field
movement is tracked but does not gate.** `/spp-loop`'s
dev-plateau check (the K-of-3 plateau condition described in
`phases/spp-loop.md` §4 step 13) runs on the aggregate metric.
The overfitting guard (train-vs-dev divergence) also runs on
the aggregate. Per-field metrics are computed every iteration
and persisted to `eval.json` (decision below) and reach the
discrepancy subagent's allow-listed input set so per-field
disagreement attribution remains possible (relevant to bucket
3, the per-field methodology application layer), but per-field
movement does not independently trigger stop conditions. At
loop termination, the per-field floors are checked to
discriminate SUCCESS from a new EARLY_STOP variant covering
the case where the aggregate plateaus at or above its target
but one or more floor-bearing fields fell short. This variant
joins the EARLY_STOP sub-types proposed in v0.1.0's close-out
findings (`early_stop_overfitting_guard`,
`early_stop_manual_abandon`, `early_stop_user_discipline`); the
exact identifier (e.g., `early_stop_floor_unmet`) is left to
the implementation PR. The aggregate-plateaus-but-floor-fails
condition is not a `FAILED` outcome because the loop's
optimization process behaved correctly; it is `EARLY_STOP`
because the methodology's gate cannot advance to declare
success when a floor was missed. (The `/spp-loop` step-13 edit
that wires the new variant lands with bucket 3, per-field
methodology application; this design PR captures the variant's
existence and trigger condition only.)

**`eval.json` schema: `per_field`, `aggregate`,
`floor_compliance` sections.** v0.2's `eval.json` carries three
top-level sections beyond what v0.1.0's `eval.json` holds:

- **`per_field`** — keyed by field name; each field carries
  its primary metric value (train + dev), auxiliary structures
  appropriate to the field's metric (confusion matrix for
  enum-F1, IoU distribution for span-IoU, residual
  distribution for number-MAE, and so on), and per-class
  statistics where applicable.
- **`aggregate`** — the aggregate metric value (train + dev),
  the strategy used (`macro` / `weighted` / `min`), and for
  `weighted` the weights vector.
- **`floor_compliance`** — keyed by field name; each field
  carries its floor (or `null` if unspecified) and a
  `met` / `unmet` / `not_specified` status.

The shape is captured at prose level so future PRs are written
against an agreed structure; the JSON Schema for the artifact,
the runner-side generation logic, and the discrepancy
subagent's allow-list update land with bucket 3 (per-field
methodology application) and bucket 5 (compat / breaking-
change), not with this design PR.

**`metric-design` sub-skill adaptation: re-scope per-field plus
two new protocol stages.** The existing protocol — the §3
decision tree, the strawman-and-refine pattern, the §5
independence rule — re-scopes to run **per OUTPUT_SCHEMA
field**. Two new protocol stages join the consultation order:
**aggregate-strategy consultation** (decision 2 above, lands
after per-field metric selection completes) and **per-field-
floor consultation** (decision 3 above, lands after
aggregate-strategy consultation). The sub-skill remains
**review-and-record** — no verdict gate. `schema-designer`
(bucket 1) is the only verdict-gated sub-skill in v0.2;
`metric-design`'s role is consultative, and the contrast is
intentional: schema design admits a categorical-disqualification
check (the mechanical-layer parser-deterministic rules in
bucket 1's `schema-designer` SKILL.md §3.4), metric selection
does not — the asymmetry, class-balance, and operational-
privilege questions all require user judgment that no parser
can shortcut. The sub-skill operationalization (per-field
re-scoping, the two new protocol stages, K=1 backward
compatibility, versioning) lands in the `metric-design`
SKILL.md revision in this same PR.

**v0.1.0 K=1 backward compatibility.** Single-output
classification is the K=1 degenerate case under the v0.2
protocol: per-field selection runs once and produces the same
output the v0.1.0 decision tree produced; aggregate-strategy
consultation runs trivially (any strategy is the identity on
K=1); per-field-floor consultation runs once. The `eval.json`
`per_field` section has one entry; `aggregate` equals that
entry's primary metric; `floor_compliance` has one row. v0.1.0
plan.md files do not need migration for `metric-design`'s
purposes — the metric + rationale + independence note shape
continues to read for the single field. Migration of the
template's surface text to carry the per-field outputs and the
aggregate-strategy fields is bucket 5, the compat layer.

##### Per-field methodology application layer

This is the layer that operationalizes buckets 1 and 2's
contracts inside `/spp-loop`'s per-stage subagents and the
artifacts they produce. It is the largest bucket so far
because it touches every cognitive stage of the iteration —
discrepancy, rule-edit, auditor, adversary — plus
`REPORT.md`. The per-stage information-isolation contract
(§4.2) is unchanged in shape; what changes is the
multi-field-aware content the per-stage allow-lists carry.

**Discrepancy clustering: field-bounded clusters; cross-field
correlation visible to the subagent.** Each failure cluster
in `discrepancy_analysis.md` names a **primary field** — the
field whose disagreements the cluster's shared property
explains. Rows that disagree on multiple fields appear in
multiple clusters (once per field-disagreement); the cluster
is the unit of explanation, not the row. The discrepancy
subagent reads ground-truth values for **all** fields on
disagreed rows so cross-field correlation is in scope of its
analysis (e.g., when `category = electronics` predictions
correlate with `brand_known = false` errors, the subagent
can name the correlation in the cluster's shared-property
prose), but cluster boundaries are field-bounded. Proposed
rule edits emerging from a cluster naturally target the
cluster's primary field; an edit may target additional
fields when its rationale spans them, in which case the
edit's `target_fields` list names every field it affects.
The auditor's per-field verdict scoping (decision below)
runs against this `target_fields` list.

**Disagreed-row filter: any-field-disagreed.** A row enters
the discrepancy subagent's `baseline.csv`-filtered allow-list
if **any** field's prediction does not match ground truth on
dev. The subagent reads all field predictions, all field
ground-truth values, and the row's input content for those
rows. Per-field filtering (running the subagent K times,
each time with rows where field f disagreed) was considered
and rejected: it would lose cross-field disagreement
structure (rows that disagree on two fields would appear in
two independent invocations with no cross-correlation
context), and it would multiply the per-stage subagent
count K-fold for no methodology gain. One subagent, one
filter, multi-field-aware analysis.

**Auditor verdict scoping: per-edit-per-field.** A rule edit
listed in `discrepancy_analysis.md` with K target fields
gets K independent auditor verdicts — one verdict per target
field. The verdict tokens
(`categorical` / `row-specific` / `unclear`) are unchanged;
only the scoping changes. An edit can be `categorical` for
field A and `row-specific` for field B simultaneously; the
auditor's synthetic-rows test (`auditor.md` §4) runs per
target field. Gate enforcement in `/spp-loop` advances on
**all non-categorical (edit, field) combinations** being
overridden in `plan.md` §11. A single override entry may
cover multiple combinations if its Reason field names them
unambiguously; the runner-side syntax convention is
documented in `phases/spp-loop.md` §4 step 12 (bracketed
tokens of the form `[edit-N.field-name]` paired with the
existing literal `auditor override` substring). Backward
compatibility for K=1: an `auditor override` Reason with no
bracketed tokens covers the lone field implicitly, matching
v0.1.0's per-edit override semantics.

**`REPORT.md` per-field trajectories: K per-field tables
plus one aggregate table.** §3 (loop trajectory) gains one
trajectory table per OUTPUT_SCHEMA field showing each
field's primary metric on dev across iterations, plus one
trajectory table for the aggregate metric. §2 (final scores)
gains a `per_field` block (one subsection per field with
test/dev/train metric value plus auxiliary structures —
confusion matrices for enums, IoU distributions for spans,
residual distributions for numbers, per-class statistics
where applicable), an `aggregate` block (test/dev/train
aggregate metric, strategy, weights when `weighted`), and a
`floor_compliance` block (per-field floor and met/unmet/
not-specified status). §4 (persistent failure modes)
clusters carry the cluster's primary field; the row-IDs-only
discipline is unchanged.

**`EARLY_STOP_FLOOR_UNMET` variant.** Joins the proposed
EARLY_STOP sub-types from v0.1.0's close-out
(`early_stop_overfitting_guard`,
`early_stop_manual_abandon`, `early_stop_user_discipline`).
Triggers at loop termination when the aggregate metric has
plateaued at-or-above its target but one or more per-field
floors (set during `metric-design` §3.3 consultation) are
unmet. The variant is distinct from `SUCCESS` (the
methodology cannot declare success when a floor was missed)
and from `FAILED` (the loop's optimization process behaved
correctly — the aggregate moved as expected — but a
floor-bearing field did not clear its bar). The
`EARLY_STOP.md` termination artifact lists which fields
have unmet floors so `/spp-finalize` and the user have a
specific failure surface to act on.

**Adversary scoping: synthetic rows have full structured
OUTPUT_SCHEMA-shaped ground truth.** Each adversarial row
carries one ground-truth value per OUTPUT_SCHEMA field. Rows
with partial ground truth (some fields filled, others
missing) would not be inspectable as thought experiments —
the user's evaluation of "would the prompt fail on this
row?" depends on knowing what the right answer should be on
every field. The adversarial annotation (`adversary.md` §6)
may name per-field expected vs. predicted values when the
blind spot is field-specific. The non-persistence rule
(§4.3) is unchanged: the rows live inline in
`discrepancy_analysis.md` for one iteration and disappear;
the structured-ground-truth generalization changes their
content but not their disposition.

**v0.1.0 K=1 backward compatibility.** Single-output
classification is the K=1 degenerate case throughout this
layer. Discrepancy clustering produces clusters with a
single primary field (the lone OUTPUT_SCHEMA field);
`target_fields` on each rule edit has length 1; the
auditor's per-edit-per-field verdict shape collapses to one
verdict per edit (the v0.1.0 shape); `REPORT.md`'s
per-field block has one subsection equal to the v0.1.0 §2
content, the aggregate trajectory equals the per-field
trajectory, the floor-compliance block has at most one row,
and the §4 cluster's primary-field tag is the only field;
`EARLY_STOP_FLOOR_UNMET` only fires when the user set a
floor on the lone field and the loop did not meet it;
adversarial rows carry a single ground-truth value
(equivalent to v0.1.0's "label"). Until bucket 5 lands the
v0.2 `plan.md.template` carrying OUTPUT_SCHEMA, the runner
falls back to v0.1.0's `LABEL_SPACE` and treats it as a
degenerate single-field schema (`{label: <enum from
LABEL_SPACE>}`); the K=1 path is therefore both
forward-compatible (v0.2 OUTPUT_SCHEMA reduces cleanly to
K=1) and backward-compatible (v0.1.0 LABEL_SPACE plans
continue to run under the v0.2 runner). The K > 1 path
requires bucket 5's template surface to be persistable; in
this layer it is contract-only — the runner can compute
per-field metrics and produce per-field trajectories
end-to-end, but the per-field outputs cannot be written to
`plan.md` until the template holds OUTPUT_SCHEMA. Same
"ships standalone before integration" pattern as buckets 1
and 2.

##### Sub-skill ordering layer

This layer resolves the gate-placement question that bucket
1's schema-layer subsection explicitly deferred ("whether it
lands as a new G1.5, whether G2/G3/etc. shift, whether it
folds into G1") and integrates `schema-designer` into the
designer agent's consultation flow alongside the existing
`metric-design` invocation. The decisions are smaller than
buckets 1–3 because the work is integration, not new
contract.

**Gate placement: schema-designer's verdict is a
precondition to G1, not a new gate.** No renumbering of
G1–G6. The verdict gates the *contents* of G1 (plan.md is
approvable) — exactly the pattern `baseline-quality`
already follows at G2 (`baseline-quality` SKILL.md §2;
`/spp-baseline` gate enforcement). Override is via
`plan.md` §11 entry whose Reason field contains the literal
substring `schema-not-ready override` (case-sensitive,
exact-substring; pinned in `schema-designer` SKILL.md §6).
Future contributors proposing a new G1.5 or any
renumbering should be redirected here — the precondition
pattern is uniform across both verdict-gated sub-skills,
and the uniformity is the point. Renumbering would create
churn (every gate-aware artifact would shift, every README
walk would need updating) for no methodological gain; the
verdict gates G1's contents, not a separate check.

**Consultation order in `/spp-init`: `schema-designer`
first, then `metric-design`.** Order is determined by data
dependency: `metric-design`'s per-field protocol (bucket 2;
`metric-design` SKILL.md §3.1) consumes OUTPUT_SCHEMA's
fields, which `schema-designer` (bucket 1; SKILL.md §3)
produces. The designer agent's §5 consultation walk
invokes `schema-designer` before `metric-design` and
records the order explicitly. Reversing the order would
require `metric-design` to run against a placeholder
OUTPUT_SCHEMA that does not yet exist — a category error.
The order is not a stylistic choice; it is a topological
requirement of the v0.2 protocol.

**`designer.md` §7 rule generalizations: rules 3 and 5
generalize in this PR with K > 1 forward-notes.** Rule 3
(`LABEL_SPACE` is enumerable) generalizes to "OUTPUT_SCHEMA
passes the mechanical layer" per `schema-designer`
SKILL.md §3.4. Rule 5 (`METRIC_INDEPENDENCE_NOTE` present
and non-empty) generalizes to "per-field
`METRIC_INDEPENDENCE_NOTE[f]` present and non-empty for
each OUTPUT_SCHEMA field" per `metric-design` SKILL.md §6.
Both generalizations are **contract-only for K > 1** until
bucket 5 lands the `plan.md.template` OUTPUT_SCHEMA
surface; the K=1 path continues to work via v0.1.0's
scalar `LABEL_SPACE` / `METRIC_INDEPENDENCE_NOTE` fields,
which are valid persistence targets for the degenerate
single-field schema (the `LABEL_SPACE` enumerability check
is equivalent to the OUTPUT_SCHEMA mechanical layer's
single-field case; the scalar `METRIC_INDEPENDENCE_NOTE`
is equivalent to per-field with K=1).

**`/spp-init` G1 enforcement: dual check.** G1 advances
iff both:

1. The user typed the G1 approval substring (existing
   v0.1.0 check).
2. EITHER `schema-designer`'s most recent verdict is
   `ready`, OR `plan.md` §11 contains an entry whose
   Reason field contains the literal substring
   `schema-not-ready override` and references the
   `schema-designer` sub-skill.

The dual-check generalizes the existing G1 enforcement
(currently checks only the approval substring) and matches
the pattern G2 uses for `baseline-quality`. The runner
refuses to advance to `/spp-baseline` if either check
fails; the refusal message names which check failed
(approval substring missing / schema-designer verdict not
ready / override missing) so the user knows what to fix.

**v0.1.0 K=1 backward compatibility.** Single-output
classification reaches v0.1.0-equivalent behavior under
this layer:

- `schema-designer` produces a one-field OUTPUT_SCHEMA
  (`{label: <enum>}` shape) whose mechanical-layer pass is
  equivalent to v0.1.0's "LABEL_SPACE is enumerable" check
  — the `enum` field is the lone OUTPUT_SCHEMA field; the
  mechanical layer's seven rules collapse to v0.1.0's
  single-rule check on a one-field schema.
- `metric-design`'s per-field protocol runs once with K=1
  outputs that map to v0.1.0's scalar `METRIC_NAME` /
  `METRIC_RATIONALE` / `METRIC_INDEPENDENCE_NOTE`.
- Designer agent §7's rules 3 and 5 generalize their
  inputs (OUTPUT_SCHEMA + per-field outputs) but their
  output constraint is unchanged in shape: the K=1 case
  produces the same scalar outputs v0.1.0 produced.
- G1's dual check degenerates to the v0.1.0 single check
  when `schema-designer` returns `ready` — the common
  case for K=1 OUTPUT_SCHEMAs produced from a familiar
  single-class label space. The override path is
  exercised only when the user accepts a `not-ready`
  verdict on the schema, which is rare for K=1.

Until bucket 5 lands the v0.2 `plan.md.template` carrying
OUTPUT_SCHEMA, the K > 1 deployment path is contract-only
— `designer.md` describes the v0.2 consultation flow and
`/spp-init` enforces the dual check, but the runner
cannot persist K > 1 plans because v0.1.0's
`plan.md.template` only holds scalar fields. Same "ships
before deployment" pattern as buckets 1–3.

##### Compat layer

This is the layer that makes v0.2 deployable end-to-end for
K > 1. Buckets 1–4 landed contracts and runner-side
machinery that work for any K, but the persistence target —
the `plan.md.template` surface — only holds v0.1.0's scalar
fields. Bucket 5 closes that gap. It generalizes the
template surface to carry OUTPUT_SCHEMA + per-field
definitions, the aggregate-metric headline criterion,
per-field metric sub-blocks, the aggregate-strategy block,
and per-field floor sub-blocks; it adapts the consumers
that read those fields (`baseline-quality`'s per-field
calibration; `/spp-baseline`'s invocation pattern;
`/spp-finalize`'s read pattern); and it documents the
migration story for existing v0.1.0 `plan.md` files. After
bucket 5 lands, the K > 1 path is operational end-to-end
and v0.1.0 plans continue to work without modification.

**Migration story: runner-level auto-promotion plus
documented manual upgrade.** Existing v0.1.0 `plan.md`
files are not silently rewritten. The runner's K=1 fallback
— committed in pieces across buckets 1–4 (`/spp-loop` step
7's eval.json shape; `auditor.md` and `adversary.md`'s K=1
collapse; `/spp-init`'s G1 dual check degenerating to v0.1.0
behavior on a one-field schema) — promotes v0.1.0
`LABEL_SPACE` / scalar `METRIC_NAME` / scalar
`METRIC_INDEPENDENCE_NOTE` to the v0.2 K=1 shape at read
time, without writing back. Existing v0.1.0 plans run under
the v0.2 runner unchanged. Users who actively want their
plan to use the v0.2 template surface (e.g., to migrate a
single-output classification task to multi-field, or simply
to align with current conventions) follow the documented
**Manual upgrade steps** below. The decision to leave the
on-disk file alone is the operational form of the
plan.md-as-contract rule (§10): silently auto-rewriting the
file would change the contract without a §11 revision-log
entry, which the rule forbids. No `/spp-migrate-plan`
command is introduced — manual upgrade is a one-time
action, the steps are self-contained, and adding a fifth
phase command would require a §3 / §10 design change for
no methodology gain.

**`baseline-quality` per-field calibration; consolidated
single verdict.** The §3 review questions (§3.1 drift
check, §3.3 intuition-vs-rule check, and the rest of the
§3 checklist) re-scope to run **per OUTPUT_SCHEMA field**.
Verdict tokens (`ready` / `revise` / `not-ready`) are
unchanged; the consolidation rule is **any-not-ready
dominates, any-revise dominates ready**: if any field's
review surfaces `not-ready` findings, the
baseline-as-a-whole verdict is `not-ready`; if any field's
review surfaces `revise` findings without `not-ready`, the
verdict is `revise`; otherwise `ready`. The single-verdict
consolidation preserves G2's enforcement pattern unchanged
— one verdict per baseline gates G2, not K verdicts. The
findings document records per-field findings (which field
surfaced what); the verdict is one token. K=1 backward
compat: with one OUTPUT_SCHEMA field the per-field protocol
runs once and the findings + verdict shape collapses to
v0.1.0's. The pattern parallels `metric-design`'s per-field
re-scoping (bucket 2); the difference is that
`baseline-quality` retains its verdict-gate authority,
while `metric-design` does not (the asymmetry is locked at
bucket 1 / bucket 2 — schema design admits a
parser-deterministic mechanical layer; baseline review
admits a categorical-disqualification check; metric
selection does not).

**Phase doc read-pattern updates with K=1 backward
compatibility.** `/spp-baseline` reads `plan.md` §2's
OUTPUT_SCHEMA + per-field definitions, invokes
`baseline-quality` with per-field calibration, and enforces
G2 against the consolidated verdict (unchanged in shape).
`/spp-finalize` reads `plan.md` §2 OUTPUT_SCHEMA, §3
aggregate-metric headline, §4 per-field metric sub-blocks
+ aggregate-strategy block + per-field floor sub-blocks;
surfaces per-field results in REPORT generation per the
v0.2 `REPORT.md.template` (bucket 3); and handles the
`early_stop_floor_unmet` termination variant (bucket 3) by
surfacing the unmet floors and asking the user to confirm
advancement before reading the sacred test set. Both
phases fall back to v0.1.0's scalar fields for legacy
plans — the same pattern bucket 3 committed in `/spp-loop`
step 7. The runner-side fallback is implemented once
across the four phase docs; future contributors must not
add a per-phase fallback that diverges from the others.

The remaining decisions are mechanical actualizations of
contracts pinned in earlier buckets:

- **`plan.md.template` §2 holds OUTPUT_SCHEMA plus
  per-field definitions** per bucket 1's schema-layer
  contract. The block holds OUTPUT_SCHEMA at the top inside
  a fenced code block (` ```yaml ` or ` ```json `; the
  user picks during `schema-designer` consultation), then
  per-field definition sub-blocks below — one per field,
  each containing field name, description, positive
  examples, borderline examples, and edge cases.
  Single-output classification's degenerate one-field
  schema writes the same shape with one field; no
  shorthand, no `LABEL_SPACE` legacy alias. §2 stays one
  cohesive section; the per-field sub-blocks live within
  §2 so the auditor's "plan.md §2" allow-listed slice
  (§4.2) stays cleanly addressable.
- **`plan.md.template` §3 + §4 hold per-field metric
  sub-blocks plus the aggregate-strategy block plus
  per-field floor sub-blocks** per bucket 2's metrics-layer
  contract. §3's headline criterion takes the aggregate
  metric target (e.g., `aggregate F1 ≥ 0.85`); §4 holds,
  in order, an `AGGREGATE_STRATEGY` block (with
  `AGGREGATE_WEIGHTS` when strategy is `weighted`;
  `AGGREGATE_RATIONALE` always), per-field metric
  sub-blocks (one per field, each containing
  `METRIC_NAME[f]`, `METRIC_RATIONALE[f]`,
  `METRIC_INDEPENDENCE_NOTE[f]`), and per-field `FLOOR`
  sub-blocks (one per field that carries a floor; absent
  for fields without; the entire floor section may be
  empty). Per-field sub-blocks within §4 — not separate
  sub-sections like §4.1 / §4.2; not tabular — to match
  the "§2 stays one cohesive section" pattern.
- **`designer.md` §7 forward-notes lifted: rules 3, 4, 5
  unconditionally K > 1 deployable.** The K=1 fallback
  paragraphs stay (legacy plans without OUTPUT_SCHEMA
  continue to work via the runner's auto-promotion); the
  "K > 1 is contract-only until bucket 5" forward-notes
  are removed. Bucket 5 ships the persistence target that
  makes K > 1 deployment operational.

**v0.1.0 K=1 backward compatibility.** Legacy plans
(v0.1.0 `LABEL_SPACE` + scalar `METRIC_NAME` + scalar
`METRIC_INDEPENDENCE_NOTE`) continue to work end-to-end
without modification. The runner's K=1 fallback
auto-promotes them at read time; downstream phases see the
v0.2 K=1 shape; gate enforcement, REPORT generation, and
termination artifacts produce v0.1.0-equivalent output.
The v0.2 template surface is opt-in via the **Manual
upgrade steps** below; no flag day, no automatic rewrite.
The K > 1 path becomes operational with this PR.

**Manual upgrade steps.** Users who want to migrate an
existing v0.1.0 plan to the v0.2 template surface follow
this sequence. The procedure preserves the methodology
contract — no decisions change; only the bookkeeping shape
moves to v0.2. A plan that has been run through these steps
validates against `designer.md` §7 rules 3, 4, 5 (in their
post-bucket-5 form) without changes to any other section.

1. **§2 — replace `LABEL_SPACE` with `OUTPUT_SCHEMA`.**
   Remove the `LABEL_SPACE: <enum values>` line. Add an
   `OUTPUT_SCHEMA:` block (YAML or JSON, the user's
   choice) describing the equivalent single-field schema,
   e.g. `{label: <enum from the prior LABEL_SPACE>}`.
2. **§2 — move per-class definitions under the new
   OUTPUT_SCHEMA block.** Each per-class definition becomes
   content within a single per-field-definition sub-block
   under the lone field; the single field carries all class
   definitions inside its description, positive examples,
   borderline examples, and edge cases.
3. **§4 — wrap scalar metric fields in a per-field
   sub-block.** `METRIC_NAME`, `METRIC_RATIONALE`, and
   `METRIC_INDEPENDENCE_NOTE` move into a single per-field
   sub-block under the lone field. The values themselves do
   not change.
4. **§4 — add an `AGGREGATE_STRATEGY` block at the top.**
   `strategy: macro` (the trivial K=1 identity per
   `metric-design` SKILL.md §3.2; any of the three
   strategies is the identity on K=1).
   `AGGREGATE_RATIONALE`: one sentence referencing the K=1
   case (e.g., "single-output classification; aggregate is
   identity on the lone field's metric").
5. **§4 — (optional) add a per-field `FLOOR` sub-block.**
   Skipping is the right default; only the user's task
   economics determine whether a floor is needed. If the
   user's v0.1.0 plan implicitly carried a per-class floor
   (e.g., "recall ≥ 0.95 on the positive class"), refer to
   `metric-design` SKILL.md §3.3's per-class-within-field
   guidance: define the field's primary metric to *be* the
   per-class metric (e.g., `recall_on_class_X`) rather than
   adding a second tier of bookkeeping.
6. **§1 — bump `PLAN_VERSION` and add a §11 revision-log
   entry.** The entry's `Reason` field should cite the
   upgrade reason explicitly (e.g., "upgraded plan to v0.2
   template surface; protocol unchanged"). The bump and
   the §11 entry are the audit trail that the contract has
   moved to a new bookkeeping shape; without them, the
   file diff would be silent on what changed.

Steps 1–6 are mechanical. The user does not need to re-run
`schema-designer`, `metric-design`, or `baseline-quality`
— the existing decisions stand; only the shape of their
persistence has changed. After the upgrade, subsequent
`/spp-baseline`, `/spp-loop`, and `/spp-finalize`
invocations read the new shape directly without invoking
the K=1 fallback.

The K > 1 path requires no special migration: a user
starting a new task on bucket 5 invokes `/spp-init`, which
walks `schema-designer` and `metric-design` per bucket 4's
order, persists OUTPUT_SCHEMA + per-field metrics +
aggregate strategy + per-field floors directly into the
v0.2 template, and proceeds. There is no v0.1.0 → v0.2
"upgrade" for new tasks; the upgrade applies only to plans
that pre-date bucket 5.

##### Locked-invariants inventory

This is an audit subsection. It enumerates the v0.1.0
methodology guarantees that v0.2 preserves — verbatim where
v0.2 did not touch the mechanics, or with shape changes that
preserve the substance where v0.2's bookkeeping
generalizations required surface-level adaptations. Future
contributors proposing v0.3+ changes use this inventory to
confirm proposed changes don't silently weaken any
guarantee. Each entry names the invariant, the canonical
reference, what the invariant guarantees in one or two
sentences, the verification status (preserved verbatim, or
preserved with shape change), and the BREAKING CHANGE
triggers in the relevant Versioning sections that protect
it. The inventory is non-exhaustive — load-bearing
methodology commitments only, not every constraint in the
codebase. The inventory itself is methodology-affecting:
removing or weakening any inventory entry is `BREAKING
CHANGE:` per `CLAUDE.md` §4.

The verification work that produced this inventory found no
weakened invariants in v0.2. One documentation-gap finding
(an existing /spp-finalize Versioning bullet did not get
updated when bucket 5 added a deliberate exception) is
surfaced under "Documentation findings" at the end; it does
not constitute an invariant violation.

###### Per-stage information isolation

**Per-stage isolated subagents.** Canonical reference:
`DESIGN.md` §4.2. Guarantees that each cognitive stage of
`/spp-loop`'s iteration (discrepancy, rule-edit, auditor,
adversary) runs in an isolated subagent with an explicit
allow-list of inputs; the orchestrator coordinates, it does
not do cognitive work. Status: **preserved with shape
change**. v0.2's bucket 3 generalized the allow-listed
inputs to multi-field-aware shapes (the discrepancy
subagent reads any-field-disagreed rows; the auditor's
verdict scoping is per-edit-per-field; the adversary's
synthetic rows carry full OUTPUT_SCHEMA-shaped ground
truth) without weakening the isolation contract. BREAKING
CHANGE triggers: `phases/spp-loop.md` Versioning
("Loosening any of the auditor's five operational
enforcement guarantees from `agents/auditor.md` §2";
"Loosening any of the adversary's four operational
contract guarantees from `agents/adversary.md` §6") and
`agents/auditor.md` Versioning ("Loosening the §2 input
allow-list").

**Auditor's score-access prohibition.** Canonical
reference: `DESIGN.md` §4.2 + `CLAUDE.md` §8 +
`agents/auditor.md` §2. Guarantees that the auditor sees
the prompt diff and the prior iteration's discrepancy
analysis but never sees the new iteration's scores; this is
what forces evaluation on merits rather than rationalization
via outcome. Status: **preserved verbatim**. v0.2 did not
touch the score-blindness mechanics; `phases/spp-loop.md`
step 11 still excludes `eval.json` and `results.json` from
the auditor invocation context. BREAKING CHANGE triggers:
`agents/auditor.md` Versioning ("Adding any score-related
field to the auditor's input context"), `phases/spp-loop.md`
Versioning ("Loosening any of the auditor's five
operational enforcement guarantees"), `CLAUDE.md` §8
("Do not give the auditor sub-agent score access").

**No row content to rule-edit subagent.** Canonical
reference: `DESIGN.md` §4.2 + `phases/spp-loop.md` §4 step
10 + `CLAUDE.md` §8. Guarantees the rule-edit subagent
sees the prompt to edit, proposed edits with row IDs only,
and `plan.md` §2 — never `data/baseline.csv`, `eval.json`,
`results.json`, or prior `auditor_review.md` files; this
is the load-bearing property that prevents the rule-edit
subagent from hand-crafting per-row patches. Status:
**preserved verbatim**. `phases/spp-loop.md` step 10's
allow-list is unchanged in shape; bucket 3's multi-field
generalization affects only the discrepancy subagent's
clustering work, not the rule-edit subagent's input
surface. BREAKING CHANGE triggers: `phases/spp-loop.md`
Versioning (the auditor-and-adversary umbrella bullets
above implicitly cover rule-edit isolation through the
"per-stage subagent allow-lists" frame), `CLAUDE.md` §8
("Do not give the rule-edit subagent row-content access").

**Auditor frequency: per-iteration, non-optional.**
Canonical reference: `DESIGN.md` §4.2 + `CLAUDE.md` §8 +
`templates/plan.md.template` §8 (`AUDITOR_CONFIG` value)
+ `templates/loop_spec.md.template` §3
(`auditor_frequency_reduction: forbidden`). Guarantees the
auditor runs every iteration and that frequency reduction
is forbidden — the right escape valve for cost concerns is
batch auditing within the per-iteration cadence, not
skipping iterations. Status: **preserved verbatim**.
`plan.md.template` §8 still requires `AUDITOR_CONFIG`
literally equal `per-iteration, no-score-access`;
`loop_spec.md.template` §3 still pins
`auditor_frequency_reduction: forbidden`. BREAKING CHANGE
triggers: `phases/spp-loop.md` Versioning ("Loosening the
loop_spec.md literal-block check in pre-condition 4"),
`CLAUDE.md` §8.

**Adversary score-blindness and non-persistence.**
Canonical reference: `DESIGN.md` §4.3 +
`agents/adversary.md` §2 / §6 + `phases/spp-loop.md` §4
step 9 + `templates/loop_spec.md.template` §4. Guarantees
the adversary runs without access to any score artifact
and that synthetic rows are never promoted to
`data/baseline.csv` / `data/splits.json` / any tracked
artifact. Status: **preserved with shape change**. Bucket
3 generalized synthetic rows to carry full
OUTPUT_SCHEMA-shaped ground truth (one value per field;
K=1 collapses to v0.1.0's single "label"); score-blindness
and non-persistence are unchanged. BREAKING CHANGE
triggers: `agents/adversary.md` Versioning ("Persisting
synthetic adversarial rows to `data/baseline.csv`,
`data/splits.json`, or any other tracked artifact";
"Removing the score-blindness constraint from §2";
"Allowing partial structured ground truth on synthetic
rows (v0.2)"), `phases/spp-loop.md` Versioning
("Loosening any of the adversary's four operational
contract guarantees").

###### Sacred test set

**Test rows untouched until `/spp-finalize`; read exactly
once.** Canonical reference: `DESIGN.md` §10 glossary
(sacred test set) + `phases/spp-finalize.md` §3
pre-condition 8 + `phases/spp-loop.md` §3 pre-condition 7.
Guarantees the held-out partition is read once across the
methodology's lifecycle; touching it mid-loop voids the
methodology's claim. Status: **preserved verbatim**. Bucket
5 added the `early_stop_floor_unmet` advancement branch,
but the sacred-read discipline is unchanged — the branch
gates the sacred read on user confirmation; the read still
happens exactly once per `/spp-finalize` lifecycle. BREAKING
CHANGE triggers: `phases/spp-finalize.md` Versioning
("Reading the sacred test set more than once per
`/spp-finalize` lifecycle"; "Removing the
partial-deletion-on-failure rule at step 3"; "Allowing
re-finalization without manual artifact deletion"),
`phases/spp-loop.md` Versioning ("Reading the test
partition during loop execution in any way";
"Loosening the loop_spec.md literal-block check"),
`templates/plan.md.template` validation rule 7
(`SACRED_TEST_ACK literally equals "acknowledged"`),
`templates/loop_spec.md.template` §7 literal block
(`test_set_access_during_loop: forbidden` /
`test_set_first_use: /spp-finalize only`).

**Runner-side defense-in-depth on the test partition.**
Canonical reference: `phases/spp-loop.md` §3 pre-condition
7 + `phases/spp-loop.md` §4 step 2 +
`phases/spp-finalize.md` §3 pre-conditions 4 and 8.
Guarantees the runner refuses to run loops or finalizations
whose `loop_spec.md` literal blocks or termination-artifact
shapes have been hand-edited; layered with the partial-
deletion-on-failure rule at finalize step 3 (which
distinguishes I/O failure from methodology violation).
Status: **preserved verbatim**. BREAKING CHANGE triggers:
both phase docs' Versioning sections cover the
literal-block check and the partial-deletion rule
explicitly.

###### Verdict-enforced gates

**Auditor verdict gate with literal `auditor override`
substring.** Canonical reference: `phases/spp-loop.md` §4
step 12 + `agents/auditor.md` §6 + `agents/auditor.md` §2.
Guarantees rule edits the auditor flagged
non-`categorical` do not advance to the next iteration
without an explicit `plan.md` §11 override entry whose
Reason carries the literal substring `auditor override`.
Status: **preserved with shape change**. Bucket 3
generalized to per-edit-per-field verdicts with
`[edit-N.field-name]` bracketed tokens; K=1 backward
compat: an unscoped `auditor override` Reason covers the
lone field implicitly. The literal substring is unchanged.
BREAKING CHANGE triggers: `phases/spp-loop.md` Versioning
("Loosening the per-iteration auditor verdict gate
(fuzzy-matching the auditor override substring, allowing
non-categorical edits to advance without an override
entry, treating unclear verdicts as categorical, etc.)"),
`agents/auditor.md` Versioning ("Removing per-edit-per-
field verdict scoping (v0.2) or aggregating per-field
verdicts into a single per-edit verdict"; "Removing the
per-edit verdict requirement").

**Baseline-quality verdict precondition to G2 with literal
`not-ready override` substring.** Canonical reference:
`sub-skills/baseline-quality/SKILL.md` §6 + `phases/
spp-baseline.md` §5. Guarantees `/spp-baseline` refuses to
advance G2 on a `not-ready` verdict unless `plan.md` §11
carries an entry whose Reason contains the literal
substring `not-ready override`; the override propagates
into REPORT §7.5. Status: **preserved with shape change**.
Bucket 5 added per-field calibration with the
"any-not-ready dominates, any-revise dominates ready"
consolidation rule; the verdict remains one token per
baseline; G2 enforcement is unchanged in shape. BREAKING
CHANGE triggers: `sub-skills/baseline-quality/SKILL.md`
Versioning ("Loosening the not-ready verdict's
gate-blocking authority"; "Promoting baseline-quality to
per-field-verdict"; "Changing the consolidation rule"),
`phases/spp-baseline.md` Versioning ("Allowing the
command to advance past G2 with a not-ready verdict and
no override entry"; "Multiplying the G2 verdict to
per-field"; "Removing the override-substring check on §11
entries").

**Schema-designer verdict precondition to G1 with literal
`schema-not-ready override` substring.** Canonical
reference: `sub-skills/schema-designer/SKILL.md` §6 +
`phases/spp-init.md` §4 step 9 / §5 G1 enforcement +
`DESIGN.md` §10 glossary (verdict-gated preconditions).
Guarantees `/spp-init` refuses to advance G1 unless both
the user typed the G1 approval substring AND
schema-designer's verdict is `ready` OR `plan.md` §11
contains an entry whose Reason carries the literal
substring `schema-not-ready override`. Status:
**introduced in v0.2 (buckets 1 + 4) as a new invariant;
preserved verbatim since introduction**. The dual check
folds into G1's contents per bucket 4 — no G1.5 / no
renumbering of G1–G6. K=1 fallback: the common case
(verdict = `ready`, no override needed) is
indistinguishable from v0.1.0's single-check behavior.
BREAKING CHANGE triggers: `sub-skills/schema-designer/
SKILL.md` Versioning ("Weakening verdict-gate
enforcement"; "Loosening the literal-substring requirement
on `schema-not-ready override`"; "Adding any verdict
beyond ready / revise / not-ready"), `phases/spp-init.md`
Versioning ("Weakening the v0.2 G1 dual check (collapsing
back to approval-substring-only enforcement, accepting a
missing schema-designer verdict as if it were ready, or
loosening the literal-substring requirement on
`schema-not-ready override`)"), `agents/designer.md`
Versioning ("Promoting the v0.2 schema-designer
precondition to a separate gate"; "Weakening
`/spp-init`'s G1 dual-check").

**HITL gate G1–G6 literal-string approval substrings.**
Canonical reference: `DESIGN.md` §10 glossary (HITL gate)
+ `templates/plan.md.template` §9 (gate phrase table) +
each phase doc's gate enforcement section. Guarantees that
each gate advances only when the user types the exact
approval phrase recorded in `plan.md` §9 — vague approval
("looks good") does not match; whitespace-stripped,
case-normalized to the recorded phrase, punctuation matters.
Status: **preserved verbatim**. v0.2 did not change the
literal-string-equality match semantics for any gate;
buckets 1–5 added preconditions to G1 and G2 (the verdict
gates above) without changing how the approval substring
itself is matched. BREAKING CHANGE triggers: each phase
doc's Versioning section includes a "Loosening literal-
string match on G[N] approval phrases" bullet (`/spp-init`
G1, `/spp-baseline` G2 + G3, `/spp-loop` G4,
`/spp-finalize` G5 + G6).

###### Methodology-as-substance

**Six-section prompt structure.** Canonical reference:
`DESIGN.md` §5 + `sub-skills/prompt-architect/SKILL.md` +
`templates/prompt_v01.md.template` (six XML sections:
`<persona>`, `<task>`, `<rules>`, `<output_format>`,
`<example_input>`, `<example_output>`). Guarantees every
prompt the loop iterates on uses the canonical six-section
shape; this is what makes per-iteration diffs reviewable
and what gives the auditor a stable surface to flag rule
edits against. Status: **preserved verbatim**. v0.2 did
not touch the six-section structure; the bucket-3 per-
field generalizations operate on the rules section's
content, not its structural position. BREAKING CHANGE
triggers: `sub-skills/prompt-architect/SKILL.md`
Versioning (covers the six-section discipline as the
sub-skill's load-bearing contract).

**Metric independence rule.** Canonical reference:
`DESIGN.md` §5 + `sub-skills/metric-design/SKILL.md` §5.
Guarantees the metric the loop optimizes is computable
independently of the production model — no LLM-as-judge
where the judge is the same model family as the
production target. Status: **preserved with shape
change**. Bucket 2 generalized to per-field application:
each field's chosen metric is independently checked
against the cross-family-judge prohibition; one field's
violation is sufficient to fail the rule for the task as
a whole. BREAKING CHANGE triggers: `sub-skills/metric-
design/SKILL.md` Versioning ("Loosening the §5
independence rule"; "Removing METRIC_INDEPENDENCE_NOTE[f]
as a required per-field output"; "Adding a metric that
depends on unlabeled data evaluation").

**Verdict tokens are categorical hard tokens — no
confidence weighting.** Canonical reference:
`agents/auditor.md` §6 (auditor verdicts) +
`sub-skills/baseline-quality/SKILL.md` §6
(baseline-quality verdicts) + `sub-skills/schema-designer/
SKILL.md` §6 (schema-designer verdicts). Guarantees that
verdict outputs are single-token enumerations matched
literally — `categorical` / `row-specific` / `unclear`
for the auditor; `ready` / `revise` / `not-ready` for
both verdict-gated sub-skills — with no probabilistic
scoring, no confidence weighting, no half-states. Status:
**preserved verbatim**. v0.2's bucket 1 (schema-designer)
inherited the verdict-token shape from baseline-quality
without modification. BREAKING CHANGE triggers:
`agents/auditor.md` Versioning ("Making the verdict
probabilistic, scored, or confidence-weighted";
"Removing the unclear verdict option"),
`sub-skills/baseline-quality/SKILL.md` Versioning
("Loosening the not-ready verdict's gate-blocking
authority"), `sub-skills/schema-designer/SKILL.md`
Versioning ("Adding any verdict beyond ready / revise /
not-ready").

**`plan.md` as contract; re-read fresh by every phase;
mid-task changes via §11 revision log.** Canonical
reference: `DESIGN.md` §10 glossary (plan.md as contract)
+ each phase doc's pre-conditions + `templates/
plan.md.template` §11. Guarantees that every phase
re-reads `plan.md` from disk and verifies its actions are
on-spec, that mid-task changes append a §11 entry rather
than silently rewriting earlier sections, and that
`PLAN_VERSION` bumps with each revision. Status:
**preserved with shape change**. Bucket 5 added Manual
upgrade steps for migrating v0.1.0 plans to the v0.2
template surface; the upgrade itself is recorded as a §11
entry per the rule, and the runner-level K=1 fallback
auto-promotes legacy plans at read time without writing
back (no silent rewrite). BREAKING CHANGE triggers: each
phase doc's Versioning includes "Allowing the command to
write outside its scope" or equivalent that protects the
§11-only-write discipline; `agents/designer.md`
Versioning ("Adding a new plan.md field the validation
gate now requires").

###### Operational-load-bearing

**Atomic checkpoint writes (`tmp + fsync + rename`).**
Canonical reference: `phases/spp-init.md`,
`phases/spp-baseline.md`, `phases/spp-loop.md`,
`phases/spp-finalize.md` (atomic-checkpoint discipline
described in each phase's persistence steps). Guarantees
that artifact writes survive crashes — the prior file is
either fully replaced or untouched. Status: **preserved
verbatim**. v0.2 did not change the persistence
mechanism; new artifacts (per-field `eval.json` shape;
v0.2 `test_eval.json` sections) use the same pattern.
BREAKING CHANGE triggers: not explicitly listed as a
single bullet in any Versioning section, but each phase
doc's "Allowing the command to write outside its scope"
bullet implicitly covers replacing the atomic discipline
with a non-atomic one. (Documentation finding: the
atomic-checkpoint discipline is universal across phase
docs but is not protected by an explicit BREAKING CHANGE
bullet anywhere; future contributors should add one if
they propose an alternative persistence strategy. Surfaced
under "Documentation findings" below.)

**`MODEL_IDENTIFIER` exact env-var string, no aliasing.**
Canonical reference: `DESIGN.md` §2.2 + `templates/
plan.md.template` §5 + `templates/loop_spec.md.template`
§5 + `runs/<model_identifier>/` directory naming.
Guarantees the production model identifier is the exact
env-var string with no aliasing — `gpt-4o-mini-2024-07-18`,
not `gpt-4o-mini`; this is what protects against silent
model-overfit when the alias resolves to a different
underlying model. Status: **preserved verbatim**.
`plan.md.template` validation rule 6 still requires the
exact env-var string; `runs/<model_identifier>/` directory
naming preserves the exact string. BREAKING CHANGE
triggers: `templates/plan.md.template` validation rule
section (mechanical rules); `phases/spp-loop.md`
Versioning ("Allowing the command to write outside
`runs/<model_identifier>/`"); `agents/designer.md`
Versioning ("Removing a literal-string lock from §5.6").

**`loop_spec.md` literal-block check at `/spp-loop` and
`/spp-finalize` pre-conditions.** Canonical reference:
`templates/loop_spec.md.template` §3 / §4 / §7 (literal
blocks) + `phases/spp-loop.md` §3 pre-condition 4 +
`phases/spp-finalize.md` §3 pre-condition 4. Guarantees
the runner refuses to operate against a `loop_spec.md`
whose per-stage subagent isolation block (§3), adversary
boundaries block (§4), or sacred-test-set posture block
(§7) has been hand-edited; this is the methodology spec's
defense against silent weakening. Status: **preserved
verbatim**. v0.2 did not modify the literal blocks.
BREAKING CHANGE triggers: `phases/spp-loop.md` Versioning
("Loosening the loop_spec.md literal-block check in
pre-condition 4"), `phases/spp-finalize.md` Versioning
("Loosening the loop_spec.md literal-block check at
pre-condition 4"), `phases/spp-init.md` Versioning
("Parameterizing the literal-string blocks in
loop_spec.md derivation").

**`/spp-finalize` advances only on `SUCCESS.md` (with one
v0.2 deliberate exception).** Canonical reference:
`phases/spp-finalize.md` §3 pre-condition 6. Guarantees
finalization runs only when the loop reached the headline
criterion in `plan.md` §3, with one v0.2 exception:
bucket 5 added the `EARLY_STOP.md/early_stop_floor_unmet`
advancement branch, gated by an explicit user-confirmation
prompt that surfaces the unmet floors before the
sacred-test-set read; unmet floors propagate into REPORT
§7.5. All other EARLY_STOP variants and FAILED.md continue
to refuse. Status: **preserved with shape change**. The
exception is documented in `DESIGN.md` §7.1.1 compat
layer and protected by new BREAKING CHANGE bullets
in `phases/spp-finalize.md` Versioning that forbid
removing the user-confirmation prompt or skipping the
§7.5 propagation. BREAKING CHANGE triggers: `phases/
spp-finalize.md` Versioning ("Refusing the
`EARLY_STOP.md/early_stop_floor_unmet` advancement branch
at pre-condition 6, or letting it bypass the
user-confirmation prompt"; "Letting the
`EARLY_STOP.md/early_stop_floor_unmet` advancement path
skip the §7.5 acknowledged-risk-overrides population").

**v1 command set is closed at four.** Canonical reference:
`phases/spp-finalize.md` "Pattern observations" section.
Guarantees the four phases (`/spp-init`, `/spp-baseline`,
`/spp-loop`, `/spp-finalize`) are the complete v1 command
set; adding a fifth requires a methodology change (a
`DESIGN.md` revision in the same PR per `CLAUDE.md` §5),
not just a new command. Status: **preserved verbatim**.
Bucket 5's compat-layer migration story explicitly chose
*not* to introduce a `/spp-migrate-plan` command, citing
this rule. BREAKING CHANGE triggers: not a Versioning
bullet per se but a structural lock pinned in `DESIGN.md`
§3 + `phases/spp-finalize.md` Pattern observations.

###### REPORT invariant block

**REPORT.md.template §5 invariant block stays verbatim.**
Canonical reference: `templates/REPORT.md.template` §5
lines 292–296 (literal block: "Per-stage information-
isolation invariants: preserved." plus four sub-statements
naming the discrepancy / rule-edit / auditor / adversary
allow-list-honoring). Guarantees REPORT carries the
methodology's traceable assertion that the design lock was
honored across the loop's lifecycle; the line is asserted,
not measured (the design lock is enforced at the runner
level — the runner refuses to write a REPORT for a loop
that violated isolation). Status: **preserved verbatim**.
Bucket 3 reorganized REPORT §2 / §3 / §4 / §7 for v0.2
per-field shape but left §5's invariant block untouched.
BREAKING CHANGE triggers: `phases/spp-finalize.md`
Versioning ("Removing the literal 'Auditor information-
isolation invariant: preserved.' line from REPORT §5";
the bullet's wording references the v0.1.0 single-line
form but operationally covers the §5 block as a whole).

###### Documentation findings

The verification work surfaced two minor documentation
gaps. Neither is an invariant violation; both are
finding-level observations for future contributors.

1. **Atomic-checkpoint discipline lacks an explicit
   BREAKING CHANGE bullet.** The `tmp + fsync + rename`
   pattern is universal across phase docs (operationally
   load-bearing for crash safety) but is not protected by
   a single named bullet in any Versioning section.
   Each phase doc's "Allowing the command to write
   outside its scope" implicitly covers replacing the
   atomic discipline with a non-atomic one, but a future
   contributor proposing an alternative persistence
   strategy would not find a clear BREAKING CHANGE
   trigger to consult. Suggested remediation (separate
   PR if pursued): add a single bullet to
   `phases/spp-init.md` Versioning naming the atomic-
   checkpoint discipline as a methodology-affecting
   change, and cross-reference from the other phase docs.
2. **`/spp-finalize.md` Versioning bullet "Allowing
   `/spp-finalize` to advance on `EARLY_STOP.md` or
   `FAILED.md` termination types" did not get updated
   when bucket 5 added the deliberate
   `early_stop_floor_unmet` exception.** The bullet's
   current wording would forbid the new branch; the new
   bullets bucket 5 added (protecting the
   user-confirmation prompt and the §7.5 propagation)
   coexist with the old one. The contradiction is
   semantic (the new branch is a deliberate, documented
   exception protected by its own bullets), not
   substantive (the discipline itself is preserved with
   a documented carve-out). Suggested remediation
   (separate PR if pursued): update the old bullet to
   "Allowing `/spp-finalize` to advance on `EARLY_STOP.md`
   (other than the `early_stop_floor_unmet` advancement
   branch defined in pre-condition 6) or `FAILED.md`
   termination types."

Both findings are surfaced for the maintainer's
disposition. Bucket 6's scope is audit, not remediation;
the inventory documents what was verified, the findings
document what could be tightened. The maintainer decides
whether to address in a separate PR or accept as known
documentation gaps.

###### Closing guidance for future contributors

When proposing v0.3+ changes that touch any invariant in
this inventory, verify the invariant survives the
proposed change. Read the canonical reference; read the
v0.2 operationalization; check the Versioning sections
for BREAKING CHANGE triggers that the proposed change
would activate. The same discipline that drove v0.2's
bucket structure — locking each layer's contract before
downstream layers depend on it — is the discipline this
inventory supports, applied to methodology-as-substance
rather than bookkeeping-as-instantiation. Adding an
invariant to the inventory is a documentation update;
removing or weakening any inventory entry is `BREAKING
CHANGE:` per `CLAUDE.md` §4. The inventory is non-
exhaustive; contributors who identify a load-bearing
methodology commitment that is missing should propose
its addition in a follow-up PR rather than treat the
omission as license to weaken it.

##### Fixtures layer

This is the closing layer of v0.2. The bucket ships two
canonical examples — `examples/multi-field-extraction/` and
`examples/nested-schema/` — that exercise the v0.2 scope
end-to-end and validate that buckets 1–6's contracts
compose into runnable shapes. With this bucket merged, all
seven layers of v0.2's planning sequence are locked, and
v0.x increments (the further-out roadmap in §7.1.2) start
from a complete v0.2 baseline.

**Two new examples, named by task type per §6.** The first
example, `examples/multi-field-extraction/`, covers
multi-field structured-output classification with diverse
field types: a `string` `title` (exact-match metric), a
`number` `price` (MAE), an `enum` `category` (macro_F1
with a per-field floor), and a `boolean` `in_stock` (F1).
Aggregate strategy is `min` — the heterogeneous metric
types live on different scales, so `metric-design` §3.2's
strawman recommendation is `min-over-fields`. A per-field
floor on `category` (`macro_F1 ≥ 0.85`) reflects the
field's role in routing downstream search; misroutes are
unrecoverable without re-running the prompt on the whole
catalog. The example exercises buckets 1 (OUTPUT_SCHEMA
with K=4 fields), 2 (per-field metrics + aggregate
strategy + per-field floor), 3 (per-field methodology
operationally — discrepancy clusters tag a primary field;
auditor verdicts are per-edit-per-field; REPORT carries
per-field trajectories), and 5 (v0.2 `plan.md.template`
surface). Buckets 4 (sub-skill ordering) and 6 (locked
invariants) are exercised implicitly — every v0.2 example
walks them.

The second example, `examples/nested-schema/`, covers
hierarchical labels via JSON Schema's conditional
structures (`if/then/else`). The OUTPUT_SCHEMA carries a
`top_level` enum (`{billing, technical, account, other}`)
and a `sub_category` whose value space depends on
`top_level`'s value — billing tickets allow
`{invoice_question, payment_failed, refund_request}`,
technical tickets allow `{login_issue, feature_bug,
performance_complaint}`, and so on. This shape exercises
the schema layer's adjacent-shapes commitment (§7.1.1
schema layer's "Adjacent output shapes the schema layer
subsumes"): hierarchical labels and freeform extraction
with structured ground truth absorb into the OUTPUT_SCHEMA
contract without separate bookkeeping. Both fields take
`macro_F1` (homogeneous metric types), so aggregate
strategy is `macro`. A per-field floor on `top_level`
(`macro_F1 ≥ 0.90`) reflects that top-level routing is
the unrecoverable decision; sub-category misroutes are
recoverable inside the team that received the ticket.
Same buckets exercised: 1 (with conditional schema
structure), 2, 3, 5; 4 and 6 implicitly.

**Each example follows the v0.1.0 skeleton pattern per
§7.2** — file structure and walkthrough are real; data,
baseline labels, and prompt content are placeholder. No
real source-project content; entirely synthetic. The
`hair-loss-relevance` example is the v0.1.0 fully-fleshed
worked example (with NDA-redacted real artifacts); the
v0.2 examples deliberately use no real-domain content per
§7.2's discipline.

**Domain choices: generic, pedagogically clear, no domain
expertise required.** The product-listing-extraction
domain (multi-field-extraction) and the support-ticket-
categorization domain (nested-schema) are stock
classification tasks readers can reason about without
specialist knowledge. The placeholder data exercises the
OUTPUT_SCHEMA's structure but does not name any specific
brand, vendor, or organization that could re-identify
source-project content.

**Each example's six-file structure.** The skeleton is
deliberately minimal — `README.md` (~1–2 paragraphs naming
what the example teaches and which v0.2 buckets it
exercises), `walkthrough.md` (1–2 pages walking through
the four phases for this task shape, citing §7.1.1
sections and sub-skill SKILL.md files), `config/plan.md`
(filled in with v0.2 surface and placeholder values),
`data/baseline.csv` (~10–15 dummy rows showing the
structured output shape), `prompts/prompt_v01.md`
(skeleton showing v0.2 multi-field output format), and
`runs/placeholder-model/REPORT.md` (sketched per-field
final scores, aggregate, floor compliance, per-field
trajectories). The skeleton deliberately does not include
`config/loop_spec.md`, per-iteration `runs/.../run_NN/`
artifacts, or runner scripts — those are real-worked-
example concerns; the skeletons exist to teach the
methodology's structure, not to demonstrate execution.
The `hair-loss-relevance` example carries the heavier
shape; the v0.2 skeletons carry the lighter pedagogical
shape.

**Closes v0.2.** With bucket 7 merged, all seven buckets
of v0.2's planning sequence are locked. Future v0.x
increments (v0.3 multi-judge subjective metrics; v0.3
multilingual support; v0.4 cross-model synthesis;
mid-iteration loop resumption per §7.1.2) start from a
complete v0.2 baseline — the methodology principles
unchanged from v0.1.0; the bookkeeping generalized to
multi-field structured output, hierarchical labels, and
freeform extraction with structured ground truth; the
locked-invariants inventory (bucket 6) standing as the
audit trail for what v0.2 preserved and what it shape-
changed; the examples (this bucket) standing as the
runnable shape against which future contributors check
their proposals. Post-v0.2 work begins in a new planning
conversation with whatever direction the maintainer sets.

**Post-bucket-7 example addition.** The
[`examples/feature-group-split/`](../examples/feature-group-split/)
example was added after bucket 7 as a v0.2 fixture for the
post-v0.2 **feature-group prompt splitting** methodology
principle (§10 glossary entry). It is not a new bucket —
the "all seven layers are locked below" framing above is
unchanged — but follows the same skeleton pattern as the
bucket-7 examples and lands as a third v0.2 example on
disk. The example decomposes a customer-feedback analysis
task into three sub-tasks (sentiment, topic, urgency),
each in its own `spp/` sub-task directory (under
`examples/feature-group-split/sub-tasks/<group>/`), each
internally K=1 and following the v0.1.0 binary-
classification skeleton pattern under the v0.2 protocol.
This anchors the principle's **default case** (feature-
group decomposition) while the original bucket-7 pair
(`multi-field-extraction`, `nested-schema`) anchors the
**exception case** (unified multi-field tasks where
splitting doesn't apply because input dependency is shared
and reasoning patterns are similar enough, or because
hierarchical conditional reasoning lives most naturally in
one prompt). The example also documents the granularity
guidance — significant gains on the first split (monolithic
→ feature-group), diminishing returns on further
subdivision (feature-group → per-class) — that prevents
the principle from being misread as a license for
maximally fine-grained decomposition. The post-bucket-7
addition is additive; it does not modify any v0.2 bucket's
contract.

#### 7.1.2 Further-out roadmap (v0.6 → v1.0)

v0.1.0's bookkeeping is intentionally narrow in several directions
where the methodology has natural extensions. Each is roadmap, not a
deliberate boundary. As of v0.5.0 the remaining roadmap is staged into
concrete minor versions; the sequencing principle is one coherent arc
per minor version, ordered by dependency and by risk to the isolation
and validation primitives — reporting- and bookkeeping-layer work
first, primitive-changing work later.

- **v0.6.0 — Multilingual data.** v0.1.0 assumes English. Multilingual
  classification has tokenization, label-space localization, and
  judge-language coupling considerations the bookkeeping does not yet
  handle. Self-contained: metrics stay mechanical, so it does not
  re-open the LLM-as-judge ban (§7.1.3). Sequenced first because it
  extends the data layer without touching the validation primitives.
- **v0.7.0 — Judge-panel-assisted baseline labeling.** Some
  classification tasks have a fixed label space but a ground truth
  that itself requires judgment (style, tone, helpfulness, coherence)
  — the case v0.1.0's `metric-design` independence rule (§5) forbids.
  v0.7 addresses it at the **baseline**, not the metric layer: a judge
  panel assists the human in establishing the gold labels once, the
  labels freeze into the sacred set, and loop and finalize scoring
  stay mechanical (invariant #13 intact — no LLM in the scoring path).
  The protocol's load-bearing work is enforcing **cross-family**
  judges, independent of the model being optimized (same-family judges
  launder the predictor's bias as consensus; majority vote reduces
  variance, not bias), escalating split votes to human adjudication (a
  split signals the label rubric is underspecified), and keeping the
  human the authority on the sacred test set. Sequenced after
  multilingual because judge-language coupling interacts with it.
  Specified in §7.1.8.
- **v0.8.0 — Operational hardening.** Two robustness items before a
  1.0 freeze. (1) **Loop resumption mid-iteration:** v0.1.0 makes the
  iteration the unit of work and discards interrupted iterations;
  resumption needs per-step checkpointing across the discrepancy /
  rule-edit / auditor / scoring stages without weakening the per-stage
  isolation contract. (2) **Harness-level isolation enforcement:**
  spp's first `PreToolUse` hook, making sacred-test-set read-once
  enforcement mechanical rather than disciplinary (spp ships zero
  hooks through v0.5 by design; this is the first).
- **v0.9.0 — Prompt-structure advisor.** A `structure-advisor`
  sub-skill, sibling to v0.5's `technique-advisor` (§7.1.6): the same
  machinery (extensible catalog, `ENTRY_SCHEMA`, seeds; discrepancy
  stage consults it; surfaced ungated; adopted via `plan.md` §11;
  runner-supported), but the suggestions are structural rather than
  output-form. Seeds: **batch I/O** (multiple input rows per inference
  call) and **multi-prompt / decomposition** (a classification split
  into a pipeline). Two constraints are pinned, not deferred: batch
  I/O must not break per-row independence (the model seeing sibling
  rows is cross-row contamination — restrict to contamination-safe
  batching or score row-isolated), and multi-prompt decomposition
  turns the runner into a prompt-graph where the discrepancy /
  rule-edit / auditor stages attribute each failure to a node in the
  chain — a real extension of the isolation contract that may need its
  own multi-bucket plan.
- **v1.0.0 — Stabilization.** No new capability: contract / API
  freeze, docs and examples hardened, the v0.x roadmap landed. The
  deliberate non-goals (§7.1.3) remain permanently out. A maturity
  milestone, not a feature release.

The version slots are sequencing intent, not a contract — a roadmap
item can move between minor versions as earlier arcs reshape the work,
the way multi-judge and multilingual moved across v0.3 → v0.7. This
section supersedes the per-version deferral notes in §7.1.4–§7.1.6.
The deliberate non-goals in §7.1.3 are the stable boundary; the
staging above is not.

#### 7.1.3 Deliberate non-goals (not roadmap)

The items below are not v0.x roadmap. They are scope boundaries the
methodology will not cross because the underlying problem is
sufficiently different from what `spp` solves that any extension
would be a different methodology, not a generalization of this one.

- **Generation-task methodologies.** Free-form text generation
  (summarization, rewriting, instruction tuning, multi-turn
  conversation) does not have ground truth in the way classification
  provides — the output space is unbounded and there is no "correct
  label" against which to compute a metric. The methodology's
  validation primitives (sacred test set, F1 / balanced-accuracy /
  per-class metrics, auditor's categorical-vs-row-specific judgment
  on rule edits) all assume a fixed output space. Generation tasks
  need a different methodology that handles bounded reference sets,
  multiple acceptable outputs, and qualitative judgment under
  uncertainty.
- **Tool-use and agentic prompts.** Tool-using or multi-turn agentic
  prompts are not a prompt-quality problem; they are an orchestration
  problem over tool boundaries, conversation state, and recovery
  semantics. The fix is in the orchestration layer, not in prompt
  rules under per-stage information isolation.
- **RAG prompts (retrieval-augmented).** RAG quality is jointly a
  function of retrieval quality and prompt quality; isolating prompt
  quality requires fixing retrieval, which `spp` neither inspects
  nor provides primitives for. A retrieval-isolated prompt-quality
  protocol is plausible as a separate methodology; folding it into
  `spp` would silently couple two failure surfaces.
- **Prompt-injection defense and jailbreak resistance.** `spp`
  produces prompts whose quality on labeled data is auditable. It
  does not produce prompts that resist adversarial input from the
  data side. Adversarial robustness is a different problem with its
  own evaluation primitives (red-teaming protocols, adversarial
  test suites, threat-model documentation); users adopting an
  `spp`-produced prompt for adversarial settings handle that
  concern separately.
- **Automated prompt search (DSPy / GEPA / APE composition).** `spp`'s
  per-stage information isolation requires that rule-edit proposal
  precede selection-by-score, and that no scoring signal reach the
  auditor's categorical judgment. Optimization frameworks that fuse
  proposal and selection (the move that gives them their speed
  advantage) violate this property structurally. The methodologies
  are incompatible by construction; PRs proposing search or
  auto-edit integrations should propose composition (use `spp` to
  produce a starting prompt, then run an optimizer downstream) rather
  than fusion.
- **Auditor frequency reduction.** If per-iteration auditor cost
  becomes a problem, the post-v1 fix is **batch auditing** (audit
  all edits in batches that span multiple iterations, preserving
  coverage but amortizing invocation cost) — not "audit every N
  iterations." Frequency reduction silently weakens the audit;
  batch auditing preserves it. PRs proposing
  "audit every N iterations" knobs should be redirected to a batch-
  auditing design instead. Batch auditing itself is open to a future
  design pass; the deliberate boundary is against frequency
  reduction specifically.
- **Cross-model synthesis.** `spp` optimizes a prompt for one target
  model; specializing to that model's idiosyncrasies is the
  objective, not overfitting to be corrected — the sacred test set
  guards against overfitting to the *data*, not to the model.
  Synthesizing one prompt across models pulls against this by
  construction: the merged prompt is mediocre on every model relative
  to each model's own tuned prompt. Cross-model *comparison* (model
  A's score on its prompt vs. model B's on its) is legitimate, but it
  is downstream model selection, not an `spp` primitive. This was v0.x
  roadmap through v0.5; it is reclassified deliberate because it is
  methodologically opposed to per-model optimization, not narrow
  bookkeeping awaiting widening.
- **LLM-as-judge metrics in the scoring path.** `metric-design` §5
  forbids LLM judges in the scoring path because users cannot reliably
  draw the boundary between cross-family judges (defensible) and
  same-family judges (silent contamination); rather than parameterize
  the rule, the methodology forbids the entire pattern. v0.7's
  judge-panel-assisted baseline labeling (§7.1.2) does **not** re-open
  this: it places judges at baseline label *creation*, freezes the
  result into the gold set, and keeps the scoring path mechanical — so
  invariant #13 holds even there. The deliberate boundary is
  specifically against an LLM judge inside the scoring path.

When in doubt, lean toward roadmap rather than deliberate. A v0.x
version can always reach a roadmap item; a deliberate non-goal is
harder to undo because it shapes the methodology's identity. The
items above are deliberate because the underlying problem is
methodologically different, not because the bookkeeping is narrow.

#### 7.1.4 v0.3 — finalize-layer statistics (the measurement layer)

The v0.3 scope is **inferential statistics on the per-row scores the
loop already computes**, reported at `/spp-finalize`. v0.1.0 and v0.2
report point estimates only: the frozen prompt's test-set aggregate is
stated as a bare number, and the only significance reasoning available
downstream is an informal fixed noise-floor heuristic. v0.3 adds a
**bootstrap confidence interval on the test-set aggregate** — the
generalization estimate a reader should quote — and, optionally, a
bootstrap CI on the dev→test gap (the overfitting interval), so the
reported numbers carry honest uncertainty bands instead of an asserted
constant. This makes first-class the gap logged at
`STATE-as-of-v0.2.0.md` ("No bootstrap CIs / paired permutation tests
on row-level scores ... Cheap to add at finalize").

`/spp-finalize` scores a **single** prompt — the frozen
`PROMPT_FROZEN_v01.md` — on the sacred test set; "baseline" elsewhere
in the runner refers to the labeled dataset (`baseline.csv`), not a
second prompt. There is therefore no two-prompt comparison to pair at
finalize, and v0.3's interval is a **single-sample** bootstrap of the
one frozen prompt's test scores, not a paired test. A genuine paired
"did optimization help" comparison would require scoring the starting
prompt on the test set as well; that is a larger, separate design and
is deferred (noted in §7.1.2), not part of v0.3.

The methodology principles transfer unchanged — per-stage isolation,
auditor judgment, sacred test set, six-section prompt structure all
apply exactly as before. v0.3 adds reporting machinery that runs
*after* the loop and changes none of them; all twenty-one locked
invariants in §7.1.1 are preserved (the bucket-6 audit below records
each as untouched).

**The load-bearing safety property: statistics are finalize-only.** A
confidence interval is a *score-derived* quantity — more
score-derived than a raw score, not less. It is therefore computed
**only at `/spp-finalize`, only after the loop has terminated, and is
never written into any artifact a `/spp-loop` subagent reads.**
Information flows strictly loop → finalize; there is no return edge.
The statistics are structurally incapable of reaching the discrepancy,
rule-edit, auditor, or adversary stages, which run earlier with
positive allow-lists that name their inputs. This is the same reason
`eval.json` / `results.json` are withheld from the auditor though both
exist on disk by the time it runs (§4.2); a CI inherits the strictest
treatment, not a looser one. Auditor score-blindness (invariant #2) is
preserved verbatim.

**The sacred test set is still read exactly once.** The bootstrap
**resamples the per-row score vector already materialized by the
single finalize read**; resampling is an in-memory operation over an
already-computed array of numbers. It does not re-run inference, does
not re-open the test partition, and introduces no preview or
ranged-prediction surface. Invariants #6 and #7 are preserved
verbatim.

**Statistics inform the human; they never gate the machine.** A
confidence interval must not become an auditor input, a
verdict-gate condition, or a confidence weight on a verdict token.
Verdict tokens stay categorical hard tokens with no confidence
weighting (invariant #14). The interval is surfaced to the human at G5
and `REPORT.md` §2 reading time; the deterministic ship-decision
tree's thresholds are unchanged in v0.3. Whether a CI should ever
qualify those thresholds is explicitly out of scope for v0.3 — it
would turn an informational number into a gate input, which is a
separate, methodology-affecting design pass.

**Bookkeeping changes by layer.** Like the v0.2 generalization, v0.3
is partitioned into buckets, each locked in its own PR before
downstream buckets depend on it:

1. **Design pin** — this section. DESIGN-only; the contract the rest
   of the arc is written against. **Locked here.**
2. **Per-row score retention** — `/spp-finalize` retains the frozen
   prompt's per-row test score vector in memory from its single sacred
   read, so the estimator has a vector to resample.
3. **Bootstrap CI on the test aggregate** — resample the frozen
   prompt's per-row test scores, recompute the aggregate per resample,
   emit the percentile interval into `test_eval.json`.
4. **Bootstrap CI on the dev→test gap (optional)** — the overfitting
   interval, emitted into `test_eval.json` alongside the gap point
   estimate the decision tree already reports.
5. **REPORT surfacing** — the test-aggregate CI in `REPORT.md` §2 (the
   generalization interval a reader should quote); per-field dev CIs in
   §3 as labeled diagnostics on a noisy small-N signal, not
   generalization claims.
6. **Locked-invariants inventory** — the preservation audit recording
   all twenty-one §7.1.1 invariants as untouched under this layer.
7. **`metric-design` record + fixtures** — `metric-design` records
   which interval each field reports; fixtures exercise the finalize
   bootstrap CI on the K=1 path.

**Scope boundary.** v0.3 is additive bookkeeping inside the existing
fixed-output-space methodology. It is not a §7.1.2 enumerated roadmap
item (it is not multi-judge, multilingual, cross-model, or loop
resumption) and not a §7.1.3 deliberate non-goal (it adds no selection
signal to the loop and does not fuse proposal with selection). Taking
the v0.3 slot moves the previously-v0.3 roadmap items — multi-judge
subjective metrics and multilingual data — to v0.4 (see §7.1.2).

**No new dependency.** The bootstrap is implemented on the
Python standard library (`statistics`, `random`) plus the numeric
stack `eval.py` already uses. `scipy` is deliberately not added; a
future contributor arguing for it carries a `CLAUDE.md` §8
justification and a `CHANGELOG.md` entry.

**Locked-invariants audit (v0.3).** All twenty-one §7.1.1
invariants are untouched by this layer; it adds only
finalize-time reporting that runs after the loop terminates.
The four the layer had to actively preserve:

- **#2 auditor score-access prohibition** — a confidence
  interval is score-derived and is never written into any
  artifact a loop subagent reads; it is born at `/spp-finalize`,
  after the loop.
- **#6 / #7 sacred test set read-once / runner-side defense** —
  the bootstrap resamples the in-memory per-row score vector; it
  issues no inference and never re-reads the test partition.
- **#14 verdict tokens are categorical hard tokens** — the
  interval is descriptive in `REPORT.md` §2/§3; it never gates
  the loop, qualifies the ship-decision tree, or weights a
  verdict.

The other seventeen are untouched on their face: this layer
changes no prompt structure (#12), no gate strings (#8–#11), no
`plan.md` contract (#15), and no command set (#20 — the
statistics estimator is a finalize-time script, not a fifth
`/`-command). The `REPORT.md` §5 isolation block (#21) is
unchanged and is reaffirmed by the finalize-only placement; new
`test_eval.json` fields are written under the same
atomic-checkpoint discipline (#16).

#### 7.1.5 v0.4 — the K>1 multi-field runner (making the v0.2 contract real)

The v0.4 scope is **implementation, not new methodology**: it turns
the multi-field scoring layer that v0.2 specified in prose into
working runner code. v0.2 generalized the *bookkeeping* — `plan.md`'s
OUTPUT_SCHEMA, the `metric-design` per-field metric set, the
three-section `eval.json` (`per_field` / `aggregate` /
`floor_compliance`), per-field auditor verdict scoping — but the
runnable scripts stayed v0.1.0-shaped: `eval.py` scores a single
label with `{f1, accuracy, precision, recall}`, `inference.py` parses
one label per row, and the persisted `EvalJSON` carries a
confusion-matrix / per-class shape, not the three-section shape. K>1
tasks are therefore *describable* but not *runnable* today; v0.4
closes that gap.

Because the methodology was settled in v0.2, v0.4 changes **none of
it**. Per-stage isolation, auditor judgment, the sacred test set, the
six-section prompt structure, the verdict-enforced gates, and
`plan.md`-as-contract are unchanged; v0.4 only makes the runner
compute what the docs already promise. All twenty-one §7.1.1
invariants are preserved (the bucket-6 audit below records each).

**The canonical metric set** (from `metric-design` SKILL.md §3.1, the
contract the runner implements):

- `boolean` → `F1` (positive class), or `balanced_accuracy` when both
  classes are operationally symmetric.
- `enum` (single-select) → `F1` (privileged positive class), `macro_F1`
  (equal-weight multi-class), or `balanced_accuracy`; with
  `precision_at_recall` / `recall_at_precision` for asymmetric-cost
  fields and optional per-class F1 / recall floors.
- `array` of typed values (multi-select) → `set_F1`, or `IoU` for
  span-style outputs.
- `string` (freeform extraction) → `exact_match`.
- `number` → `MAE` (or `RMSE` when outliers must be penalized).
- nested object → recurse; each sub-field is its own per-field walk.

The **aggregate strategy** (`metric-design` §3.2) combines the
per-field primaries into the one number the loop's stop-discipline
reads: `macro` (unweighted mean), `weighted` (user weights), or `min`
(worst-field-gates). The aggregate **must refuse a
dimensionally-nonsensical combination** — e.g. macro-averaging an F1
(range [0,1], higher better) with an MAE (range [0,∞), lower better) —
surfacing the mismatch as a `revise` signal rather than emitting a
meaningless number (§7.1.1 metrics layer).

**Isolation is generalized in shape, not weakened.** The
per-iteration stage allow-lists (§4.2) keep their exact membership;
only the *content shape* inside the named artifacts grows from a
single label to a per-field structured object. The rule-edit subagent
still receives **no row content under any path**; the discrepancy
artifact still references rows by ID; the auditor stays
**score-blind** and issues one verdict per `(edit, target_field)` as
already specified (§7.1.1). No new path surfaces row content or scores
to a stage that was denied them.

**No new dependency.** The metric set is covered by the existing
numeric stack — `scikit-learn` already provides F1 / `balanced_accuracy`
/ precision / recall / Jaccard / MAE / MSE; `set_F1`, `IoU`, and the
`precision_at_recall` / `recall_at_precision` threshold metrics are a
few lines of standard Python over the same parsed labels. No package is
added.

**K=1 backward compatibility.** A single-field OUTPUT_SCHEMA collapses
to the v0.1.0 shape: `per_field` has one entry, `aggregate` equals
that entry's primary, `floor_compliance` has at most one row. Existing
v0.1.0 / v0.2 K=1 plans and their `eval.json` score unchanged; the
multi-field path is reached only when the schema declares more than
one field.

**Bookkeeping changes by layer.** Like v0.2 and v0.3, v0.4 is
partitioned into buckets, each locked in its own PR before downstream
buckets depend on it:

1. **Design pin** — this section. DESIGN-only; the contract the rest
   of the arc is written against. **Locked here.**
2. **Structured parse** — `inference.py` parses an OUTPUT_SCHEMA-shaped
   object per row (K fields), and `ResultsJSON` / `PredictionRow`
   carry per-field parsed values with per-field parse-error tracking.
3. **Per-field scoring core** — `eval.py` computes each field's primary
   metric by the field's type per the canonical set, emitting the
   `per_field` section of the three-section `eval.json` and the
   per-field `per_row` vectors (generalizing the v0.3 retention); a
   metric module holds the new primitives (Jaccard, token-F1,
   span-IoU, MAE/RMSE, tolerance-band).
4. **Aggregate layer** — `macro` / `weighted` / `min` over the
   per-field primaries, the `aggregate` section, and the
   dimensional-nonsense refusal.
5. **Floors** — the `floor_compliance` section, per-field floors and
   per-class recall floors, feeding the `EARLY_STOP_FLOOR_UNMET` path.
6. **Locked-invariants inventory** — the preservation audit recording
   all twenty-one §7.1.1 invariants as untouched under the runner
   generalization.
7. **Fixtures** — make the `multi-field-extraction` and `nested-schema`
   examples run end-to-end (the first real K>1 runs), with the Phase 4
   placeholder lint extended to the new artifacts.

**Scope boundary.** v0.4 implements the v0.2 contract; it does not add
output *shapes* beyond what v0.2 already specified. Continuous /
ordinal *modes* (a new metric family with a reshaped auditor judgment)
remain a later arc; per-label-binary / gated `output_form` prompting
techniques build *on top of* this runner and are their own arc. The
§7.1.2 roadmap items (multi-judge metrics, multilingual, cross-model
synthesis) are unaffected.

**Locked-invariants audit (v0.4).** All twenty-one §7.1.1 invariants
are untouched by the runner generalization; v0.4 makes the runner
compute what the v0.2 docs already promise, changing no methodology.
The four that the implementation had to actively preserve:

- **#1 per-stage isolated subagents** — the runner's parse/score steps
  feed the same artifacts the stages already read; allow-list
  *membership* is unchanged, only the *content shape* of `results.json`
  / `eval.json` grows from a single label to a per-field object.
- **#3 no row content to rule-edit** — unchanged: the runner emits
  per-field scores and IDs into `eval.json`, never row content, and the
  rule-edit stage's allow-list is untouched.
- **#2 auditor score-blindness** — the per-field/aggregate scores live
  in `eval.json`, already withheld from the auditor; the multi-field
  shape adds no path that surfaces them to it.
- **#13 metric independence (per field)** — each field's metric is the
  user-chosen model-independent metric from `metric-design` §3.1; no
  field introduces an LLM judge, and the dimensional-nonsense aggregate
  refusal is enforced runner-side.

The other seventeen are untouched on their face: v0.4 changes no prompt
structure (#12), no gate strings (#8–#11), no `plan.md` contract (#15),
and no command set (#20 — the scorer is the existing `eval.py`, not a
fifth `/`-command). New `eval.json` sections are written under the same
atomic-checkpoint discipline (#16), and the REPORT §5 isolation block
(#21) is unchanged. K=1 scoring is byte-for-byte the v0.1.0 path, so
the sacred-test invariants (#6, #7) and verdict-token rules (#14) see
no change.

#### 7.1.6 v0.5 — failure-driven prompting-technique suggestions

The v0.5 scope makes a small set of prompting techniques part of
spp's **diagnostic methodology**, not a default output shape. When the
optimization loop's real failures show a recognizable symptom, the
agent **names the gap and recommends a technique to the user**, who
decides whether to adopt it. A field's output stays plain by default; a
technique is prescribed only when the evidence calls for it, and
adopting it is an ordinary `plan.md` / OUTPUT_SCHEMA revision the user
approves — never an automatic rewrite.

This mirrors how the rest of spp already works: the discrepancy and
auditor stages turn observations into *recommendations a human acts
on*, not silent edits, and consultative sub-skills (`schema-designer`,
`metric-design`) advise while the human decides. v0.5 adds one more such
advisor — "this failure pattern is the kind a known technique
addresses" — and the runner support needed to act on it.

**The `technique-advisor` sub-skill (an extensible catalog).** The
techniques live in a new consultative sub-skill,
`skills/run/sub-skills/technique-advisor/`, parallel to `schema-designer`
and `metric-design` (DESIGN §8.1, "compose, don't absorb"). It is a
**catalog the project grows over time**: the methodology core does not
hardcode a fixed vocabulary — it consults the catalog to match an
observed failure symptom to a recommended technique. Adding a technique
is **adding a catalog entry** (plus its runner support if the form is
novel), not re-architecting the loop. This is deliberate: `spp` ships
open-source, and contributors who discover a new prompting technique
should be able to extend the advisor without touching the per-stage
isolation core.

Each catalog entry is a **structured registry record** with a fixed,
lint-checkable shape:

- **`symptom`** — the detectable failure pattern (what in the
  discrepancy analysis indicates this technique applies).
- **`recommendation`** — the categorical suggestion text surfaced to
  the user.
- **`output_form`** — the schema / prompt shape adopting the technique
  produces (the runner-recognized field form).
- **`runner_support`** — what parse/score the form needs, so a
  contributor knows what (if anything) to wire.
- **citation / provenance** — the source establishing the technique
  (no uncited folklore; the repo quality bar).

The SKILL.md carries a **"How to add a technique" contributor guide**
documenting this record shape and the additive-PR path (new entry, +
runner support if novel, + a fixture). v0.5 seeds the catalog with the
**two asset-validated entries**:

- **Per-label binary / one-vs-rest (OvR).** For a multi-select field
  whose labels compete in a single decision and underperform, emit one
  yes/no per label and union the positives. Symptom: a multi-select
  field with low set-overlap driven by the model treating
  mutually-compatible labels as exclusive.
- **Gated-boolean.** For a "default-attractor" field — one with a
  catch-all value (e.g. `none` / `other`) that the model over-predicts
  or hallucinates into — introduce an is-addressed gate (a boolean)
  that routes to the conditional sub-labels only when the gate is true.
  Symptom: a field whose catch-all (or populated value) is
  systematically over-predicted.

CoT-as-a-reasoning-field, multi-shot few-shot, and anchored-CoT are
**out of scope** for v0.5: each changes `<output_format>` or the
example-pair cardinality (BREAKING against the six-section structure,
invariant #12), and anchored-CoT is additionally unmeasurable without
the ordinal-distance metric that belongs to a later continuous/ordinal
arc. They remain candidates for their own design pass.

**Origin: loop-time and failure-driven.** The suggestion is produced
during `/spp-loop` from the **discrepancy stage's** view of actual
failures — the one cognitive stage that legitimately holds row content
(§4.2). The discrepancy subagent consults the `technique-advisor`
catalog to match the failure pattern it observes against the entries'
`symptom` fields; the matched entry's `recommendation` becomes the
suggestion. It is not a plan-time guess from schema shape alone; it
fires on evidence of a real gap.

**The load-bearing isolation contract (this is the part that must not
slip).** A technique suggestion is a **categorical recommendation
surfaced to the human**, not a new data path. Concretely:

- The discrepancy subagent may emit a technique suggestion into its
  existing artifact (`discrepancy_analysis.md`) from inputs it already
  has; **its allow-list does not change**.
- What crosses to the user is the *categorical* recommendation ("field
  X shows the default-attractor symptom; consider gated-boolean"),
  carried by the orchestrator to a HITL gate — exactly as discrepancy
  findings already surface. **Row content does not ride along.**
- The **rule-edit subagent still receives no row content** under any
  path, and the **auditor stays score-blind**. A suggestion is not a
  channel for either. The suggestion never auto-edits the prompt,
  schema, or plan; the user applies it via a `plan.md` §11 revision,
  re-entering the contract every downstream phase re-reads.

If a future contributor wires the suggestion so that it carries row
content to rule-edit, or scores to the auditor, that breaks the
methodology silently and must be rejected — the same standard as the
existing §4.2 locks.

**Runner support (mechanism in service of the methodology).** For an
adopted suggestion to be actionable, `inference.py` must parse the OvR
and gated forms and `eval.py` / the metric primitives must score them
(reconciled with the existing `set_f1`). This builds directly on the
v0.4 K>1 multi-field runner; it adds field-shape handling, not a new
metric family. No new dependency.

**Invariants.** All twenty-one §7.1.1 invariants are preserved. The
`technique-advisor` sub-skill is consultative and ungated — like
`metric-design`, it advises and records; it is not a fifth `/`-command
(#20 holds) and adds no verdict gate. The ones to watch — and the
bucket-6 audit will confirm them untouched — are the isolation set:
per-stage isolated subagents (#1), the auditor's score-access
prohibition (#2), and no-row-content-to-rule-edit (#3).
The six-section structure (#12) is untouched because OvR and gated are
*within-field output shapes*, not new prompt sections, and the
auditor's categorical-vs-row-specific judgment is unchanged (a rule
edit on an OvR or gated field is still categorical-vs-row-specific).

**Bookkeeping changes by layer.** Partitioned into buckets, each
locked in its own PR before downstream buckets depend on it:

1. **Design pin** — this section. DESIGN-only; the contract the rest of
   the arc is written against. **Locked here.**
2. **`technique-advisor` sub-skill** — the SKILL.md, the structured
   registry-entry contract, the "How to add a technique" contributor
   guide, and the first two entries (OvR, gated-boolean). Consultative,
   no verdict gate (parallel to `metric-design`).
3. **Diagnostic in the discrepancy stage** — the discrepancy subagent
   consults the catalog and emits a categorical technique suggestion
   from the failures it already sees; allow-list unchanged.
4. **Surfacing at the gate** — the suggestion reaches the user as a
   recommendation; adopting it is a `plan.md` §11 revision.
5. **Runner support** — `inference.py` parse + `eval.py` / metric
   scoring for the OvR and gated forms, so an adopted suggestion runs
   end-to-end.
6. **Locked-invariants inventory** — the preservation audit recording
   all twenty-one §7.1.1 invariants as untouched, with the isolation
   set (#1/#2/#3) called out explicitly.
7. **Fixtures** — an example exercising a suggested-then-adopted
   technique end-to-end, plus the finalize-statistics rider below.

**Rider (folded into bucket 7).** Generalize the v0.3 finalize bootstrap
CI (§7.1.4) to the K>1 multi-field aggregate, now that the runner emits
per-field per-row scores — a small, finalize-only addition that closes a
v0.3 follow-on.

**Scope boundary.** v0.5 adds a diagnostic recommendation and the
runner support to act on it; it does not change the methodology's
output space, its metric families, or any stage's information access.
Taking the v0.5 slot moves the previously-v0.5 §7.1.2 roadmap items —
multi-judge subjective metrics, multilingual data, and cross-model
synthesis — to v0.6 (see §7.1.2).

**Locked-invariants audit (v0.5).** All twenty-one §7.1.1 invariants
are untouched by this arc. v0.5 adds a consultative advisor, an
ungated surfacing of its recommendation, and runner support for two
within-field output shapes; it changes no stage's information access,
no metric family, and no command set. The six the arc had to actively
preserve — the isolation set the pin calls out (#1/#2/#3) plus the
three a casual reading might think the feature touches (#12/#14/#20):

- **#1 per-stage isolated subagents** — the discrepancy subagent
  (bucket 3) reads the `technique-advisor` catalog as **reference
  material**, the same category as `prompt-architect` for the rule-edit
  subagent; the catalog carries no row content, scores, or
  prior-iteration artifacts, so consulting it adds **no data input** to
  the stage's allow-list. Allow-list *membership* is unchanged.
- **#2 auditor score-blindness** — untouched. A technique
  recommendation is a categorical statement, never a score; no v0.5
  path surfaces `eval.json` / `results.json` to the auditor, and the
  surfacing at the gate (bucket 4) carries no score signal.
- **#3 no row content to rule-edit** — unchanged. The recommendation
  references a field and a symptom *class*, never specific rows; nothing
  new reaches the rule-edit subagent's input surface, whose allow-list
  is untouched.
- **#12 six-section prompt structure** — preserved. OvR and gated are
  *within-field output shapes* (bucket 5 reconstructs them at score
  time; `inference.py` is unchanged), not new prompt sections. The
  techniques that *would* touch #12 — CoT-as-a-field, multi-shot
  few-shot, anchored-CoT — are explicitly out of scope for v0.5 and
  excluded from catalog eligibility for exactly this reason.
- **#14 verdict tokens are categorical hard tokens** — preserved. The
  technique surfacing (bucket 4) is **ungated advisory output**: it
  never halts the loop, reverts an edit, blocks advancement, or weights
  a verdict. Making it a blocking gate is `BREAKING` per
  `phases/spp-loop.md` Versioning.
- **#20 four-command set** — preserved. `technique-advisor` is a
  consultative sub-skill parallel to `metric-design`, not a fifth
  `/`-command; the scorer is the existing `eval.py`, not a new entry
  point.

The other fifteen are untouched on their face: v0.5 introduces no new
metric family (#13 — the forms reuse `set_f1` / `exact_match` etc., no
LLM judge), reads the sacred test set in no new way (#6, #7), changes
no gate strings (#8–#11), and writes its one new artifact section under
the same atomic-checkpoint discipline (#16). Adoption is a user-driven
`plan.md` §11 revision that re-enters the contract every downstream
phase re-reads (#15), and the REPORT §5 isolation block (#21) is
unchanged. The `technique adoption` §11 marker (bucket 4) joins
`auditor override` and `loop_spec re-validated` as a recognized Reason
substring; it records a human decision and triggers nothing
automatically.

#### 7.1.7 v0.6 — input preprocessing and multilingual data

The v0.6 scope is **canonicalizing arbitrary input data into the shape
the rest of the methodology expects, and the multilingual bookkeeping
that rides on it**. It has two layers:

1. A **preprocess step** — a new front gate at `/spp-baseline` that
   examines the user's raw data and produces a deterministic,
   human-reviewed script mapping it to spp's canonical `baseline.csv`
   (`id`, `input`, the label column(s), and an optional `language`
   column).
2. **Multilingual bookkeeping** — once the canonical data carries a
   `language` column, the split stratifies by language and `eval.py`
   reports a per-language metric slice, with Unicode-correct string
   comparison throughout.

Multilingual handling is one facet of preprocessing: mapping a
`lang` / `locale` / `idioma` column onto the canonical `language` tag is
exactly the kind of normalization the preprocess step exists to do.
Doing the preprocess gate now means later arcs (v0.7's judge-panel
baseline labeling, etc.) build on a clean canonical baseline rather than
each re-accommodating raw data shapes.

Neither layer changes a validation primitive: the metrics stay
mechanical and language-agnostic (invariant #13 holds — no LLM judge
enters the scoring path), the output space stays fixed, the command set
stays at four (#20), and the sacred test set is untouched (#6/#7).

##### The preprocess step (the front gate)

Real datasets do not arrive as `baseline.csv` with canonical column
names. The language might live in `locale`, the text be split across two
columns, the label be called `gold`, the id be missing. The preprocess
step closes that gap so every downstream phase operates on one known
shape.

- **A `preprocess` sub-skill** (consultative, parallel to
  `schema-designer`) examines the raw data **once** — column names,
  dtypes, sample values, cardinalities — together with the task
  definition, and **authors a deterministic `preprocess.py`** that maps
  raw → canonical `baseline.csv`. The script is **human-reviewed**
  before it runs and executes mechanically; re-running it on the same
  input yields the same output.
- **The agent is never in the per-row path.** It understands the columns
  and writes a script; it does not transform rows itself. A per-row LLM
  transform would be non-reproducible, expensive, and would place a
  model on top of the data — including the sacred test rows.
- **It runs once, pre-split, on the whole dataset uniformly**, so the
  split (and the sacred test set) is formed *after* canonicalization,
  from uniformly-shaped data. The preprocess step differentiates no row
  by partition because partitions do not exist yet.
- **It is the first step of `/spp-baseline`, not a fifth command**
  (#20). The column mapping and the `preprocess.py` are recorded in
  `plan.md` for provenance and approved at a gate before
  labeling / baseline-quality / split proceed.
- **It maps existing columns; it does not invent ground truth.**
  Synthesizing labels is the v0.7 judge-panel concern, explicitly out of
  scope here.

**Multilingual is asked, then optionally detected.** The preprocess step
asks the user whether the data is multilingual and which column (if any)
carries the language. When the user knows, that answer drives the mapping
(or marks the project monolingual). When the user does **not** know, the
sub-skill instructs the agent to install a **deterministic
language-identification library on demand** (documented install steps,
not a declared `spp` dependency) and populate `language` in
`preprocess.py`, surfacing that the tags were auto-detected so the human
reviews them. Detection is deterministic and disclosed; it is never an
LLM per-row guess, and it never becomes a hard dependency (CLAUDE.md §8).

##### Multilingual bookkeeping (downstream of preprocess)

Once `preprocess.py` has produced a canonical `baseline.csv` carrying the
optional `language` column, the bookkeeping below operates on it. Four
directions settle this layer (decided 2026-06-02):

- **Mixed-language datasets.** A project's rows may span many
  languages; a per-row `language` tag is the unit of slicing. A
  single-language non-English project is the trivial special case (one
  group), so building for the mixed case covers both.
- **Canonical fixed labels.** The output label space stays in one
  canonical language regardless of the input row's language. The model
  classifies non-English input into the same fixed label set; the
  output space does not localize per row. This keeps the metric space
  stable across languages and preserves the fixed-output-space
  assumption every validation primitive rests on.
- **Per-language metrics + language-stratified splits.** `eval.py`
  reports a **per-language breakdown** of each field's metric — a slice
  exactly like the existing per-class / per-field breakdowns — so the
  loop can see *which language* a prompt fails on. `split.py`
  stratifies train / dev / test **by language** so every split,
  including the sacred test set, is representative of the language
  distribution rather than accidentally concentrating a language in one
  split. Both engage only when the data is genuinely multi-language
  (see *Activation* below).
- **Unicode-correct string metrics, plus a truncation warning.** String
  comparison (`exact_match`, `set_f1`) NFC-normalizes and Unicode
  case-folds before comparing, so a correct prediction is not scored
  wrong because of an invisible encoding difference (composed vs.
  decomposed accents, non-ASCII case). This is a **correctness** fix,
  not a cost feature. Separately, the runner emits a **truncation
  warning** when a row's token count risks prompt cut-off — a
  correctness safeguard for verbose-tokenizing scripts (CJK, Thai,
  Devanagari), since a silently truncated row yields a wrong
  prediction. v0.6 does **not** pursue token/cost optimization: `spp`
  is a prompt-quality tool, and length/cost efficiency belongs to the
  v0.9 structure-advisor's batch-I/O seed (§7.1.2), not here. Both run
  **unconditionally** — they are correctness fixes, not multilingual
  features, so they do not key off the language column (see
  *Activation*).

**Activation is data-driven, not a flag.** The per-language machinery —
the metric breakdown and the stratified split — engages only when the
data is genuinely multi-language, **auto-detected from the `language`
column**: absent or single-valued, the runner stays in today's
monolingual behavior (a per-language breakdown would just repeat the
aggregate, and "stratify by language" collapses to an ordinary split);
two or more distinct languages turn it on. The `language` column is
**optional** and the path is **backward-compatible** — existing
single-language projects are unaffected, and there is no flag to set.
The two correctness fixes are the deliberate exception: NFC + case-fold
normalization and the truncation warning run regardless of the language
column, because normalization is a no-op on ASCII yet still required by
a *monolingual* non-English project (e.g. all-French accents), and the
truncation warning keys on token count, not language count.

**Why this touches no invariant.** Per-language is a metric *slice*,
the same category as per-class — #13's metric family is unchanged (the
same mechanical metrics, computed per group). Canonical labels keep the
output space fixed. Normalization is internal to the metric
computation. The truncation warning is advisory output that halts
nothing (#14 — it is not a verdict and not a gate). Language awareness
adds no data path to any isolated stage: the discrepancy subagent's
per-language view is the same `eval.json` it already reads, now carrying
a language slice; the rule-edit subagent still receives no row content
(#3); the auditor stays score-blind (#2); allow-list membership is
unchanged (#1). The command set is unchanged (#20 — `split.py` and
`eval.py` are the existing entry points). The bucket-10 audit confirms
all twenty-one untouched.

The **preprocess step** touches no invariant for the same structural
reasons: it is a step inside `/spp-baseline`, not a fifth command (#20);
it runs once, before the split, on the whole dataset uniformly, so the
sacred test set is formed from canonicalized data and is read no
differently (#6/#7); its `preprocess.py` is a deterministic,
human-reviewed artifact recorded in `plan.md` (#15, plan.md-as-contract),
with no LLM in the per-row data path; and it produces ground-truth
*shape*, never ground-truth *values* (#13 — it does not judge or label).

**Bookkeeping changes by layer.** Partitioned into buckets, each locked
in its own PR before downstream buckets depend on it:

1. **Design pin** — the multilingual scope. DESIGN-only. **Locked.**
2. **Contract** — the **optional** per-row `language` field convention
   (BCP-47) in `baseline.csv`, the data-driven activation trigger, and
   the canonical-label policy, documented in the `plan.md` template and
   the `schema-designer` / `metric-design` sub-skills.
3. **Language-stratified splits** — `split.py` stratifies by language
   so every split (including the sacred test set) is representative;
   short-circuits to an ordinary split in monolingual mode.
4. **Metrics core** — NFC + case-fold normalization in the string
   metric primitives (always on), and the per-language stratification
   section in `eval.py` / `eval.json` (emitted only in multilingual
   mode). The substantive metrics bucket.
5. **Scope-reframe pin** — this expanded section, adding the preprocess
   layer (multilingual reframed as one facet of preprocessing).
   DESIGN-only. **Locked here.**
6. **`preprocess` sub-skill + `preprocess.py` contract** — the SKILL.md
   (the protocol for examining columns and authoring the script, the
   on-demand language-ID instructions) and the deterministic
   `preprocess.py` contract / template. Ships standalone first, like
   `schema-designer`.
7. **Wiring into `/spp-baseline`** — invoke preprocess as the first
   step, with its review gate; record the column mapping in `plan.md`;
   the `lang`/`locale` → `language` mapping lands here.
8. **Truncation warning** — a token-budget pre-flight in the runner that
   warns when a row risks prompt truncation.
9. **Loop wiring** — the discrepancy stage consumes the per-language
   section so failures can be read per language; `phases/spp-loop.md`
   documents it. Allow-lists unchanged.
10. **Fixtures + audit** — a mixed-language example and a raw→canonical
    preprocess example exercised end-to-end, plus the locked-invariants
    audit (v0.6) recording all twenty-one §7.1.1 invariants as untouched.

**Scope boundary.** v0.6 is additive: a preprocessing front gate plus
multilingual bookkeeping, inside the existing fixed-output-space
methodology. It adds no metric family, no output shape, and no stage
information access; it does not localize the label space, optimize cost,
or introduce an LLM judge. The preprocess step maps existing columns and
shapes data — it does **not** invent labels (v0.7 judge-panel) and runs
no LLM per row. Cross-lingual transfer (train one language, test
another) and judge-language coupling remain out of scope — the latter
only becomes live at v0.7's judge-panel baseline labeling (§7.1.2),
where the judges, not the metrics, couple to language.

**No new dependency.** Normalization uses the Python standard library
(`unicodedata`); per-language slicing and stratification reuse the
existing metric and split machinery. The optional
language-identification library is **installed on demand by the agent
per the sub-skill's documented instructions, not declared as an `spp`
dependency** — it is needed only when the user cannot say whether the
data is multilingual, and never enters the runtime import surface of the
shipped scripts.

**Locked-invariants audit (v0.6).** All twenty-one §7.1.1 invariants are
untouched by this arc. v0.6 adds a preprocessing front gate and
multilingual bookkeeping; it changes no stage's information access, no
metric family, no output space, and no command set. The seven the arc
had to actively preserve — the isolation set (#1/#2/#3), the sacred test
set (#6/#7), the metric-independence rule (#13), and the four-command set
(#20):

- **#1 per-stage isolated subagents** — the preprocess step runs
  *before* the loop, so it is not a loop stage and adds no subagent. The
  discrepancy subagent's per-language attribution (§7.1.7) reads the
  `per_language` slice from the `eval.json` it **already** holds plus the
  `language` tag on the disagreed rows it **already** reads; allow-list
  *membership* is unchanged. No data input is added to any stage.
- **#2 auditor score-blindness** — untouched. No v0.6 path surfaces any
  score to the auditor; per-language is a slice of `eval.json`, which the
  auditor never sees, and the truncation warning is a pre-inference log
  line, not a score.
- **#3 no row content to rule-edit** — unchanged. The per-language
  attribution carries counts and a language tag, never row content; the
  preprocess step produces canonical data pre-loop and never feeds the
  rule-edit subagent. Its allow-list is untouched.
- **#6 / #7 sacred test set, read once** — preserved and, if anything,
  strengthened. `preprocess.py` runs **once, pre-split, on the whole
  dataset uniformly**, so the split (and the sacred test set) is formed
  *after* canonicalization from uniformly-shaped data; the test
  partition is read no new way, and language-stratified splitting still
  reads each row exactly as before.
- **#13 metric independence / no LLM judge** — preserved. The
  per-language breakdown reuses each field's existing mechanical metric
  computed per group (no new metric family, no LLM judge); Unicode
  normalization is internal to the comparison; the truncation warning is
  a heuristic advisory, not a metric. The preprocess step produces
  ground-truth *shape*, never ground-truth *values* — it maps existing
  label columns and never judges or labels (label synthesis is the v0.7
  boundary).
- **#20 four-command set** — preserved. The preprocess step is the first
  step of `/spp-baseline`, not a fifth `/`-command; its human review
  precedes G2 and reuses gate discipline without adding to the G1–G6 set.
  `split.py`, `eval.py`, `inference.py`, and `discrepancy.py` remain the
  existing entry points (each gains an optional `--language-column` /
  `--context-window` flag, not a new command).

The other fourteen are untouched on their face: v0.6 introduces no new
prompt section (#12 — preprocessing shapes input columns, not the
six-section prompt), no verdict (#14 — the per-language slice, truncation
warning, and preprocess mapping are descriptive/advisory, never a hard
token that halts the loop), and no change to the gate strings (#8–#11).
Adoption of the canonical shape is a user-reviewed `plan.md` §6 record
that every downstream phase re-reads (#15), written under the same
atomic-checkpoint discipline (#16), and the REPORT §5 isolation block
(#21) is unchanged. The `PREPROCESS_MAPPING` and `LANGUAGE_COVERAGE` §6
fields and the `language_stratified` / `per_language` artifact additions
are all additive and backward-compatible — absent in pre-v0.6 files,
where they read as their defaults.

#### 7.1.8 v0.7 — judge-panel-assisted baseline labeling

The v0.7 scope is **synthesizing gold labels for tasks whose label
space is fixed but whose ground truth requires judgment** — tone,
helpfulness, coherence, style — the case v0.1.0's `metric-design`
independence rule (§5) forbids at the *metric* layer. v0.7 moves the
judgment to the **baseline**: a cross-family judge panel helps the
human establish the gold labels *once*, the labels freeze into the
sacred set, and loop / finalize scoring stays mechanical. The scoring
path never sees an LLM (#13 intact); this does **not** re-open the
LLM-as-judge non-goal (§7.1.3), which forbids a judge *inside the
scoring path*, not at label creation.

It has one layer: a **`label-panel` sub-skill** (consultative, parallel
to `preprocess` and `schema-designer`) that runs **only when the
canonical `label` column is absent** after preprocess — it synthesizes
labels where none exist and is a no-op when the user already holds gold
labels. preprocess maps existing columns and explicitly never invents
ground truth (§7.1.7); label-panel is where synthesis lives, completing
that handoff.

##### The judge panel (the protocol)

- **Five Claude Code subagent judges, score-blind.** Each judge
  receives the row input, the fixed label space, and the labeling
  rubric (from `plan.md` / `metric-design`), and returns exactly one
  label plus a brief rationale. There are no model predictions to see —
  this is baseline *creation*, before any prompt is scored — so
  score-blindness is structural, not enforced.
- **The agent is never inventing the label space.** The panel chooses
  among the *existing* fixed labels; it does not expand or localize the
  output space (the fixed-output-space assumption every primitive rests
  on is preserved).
- **≥4-of-5 agreement auto-accepts; anything below escalates.** A 5-0
  or 4-1 majority freezes the label; a 3-2 (or wider) split routes the
  row to the **human adjudication queue**. A split is signal, not
  noise: it means the rubric is underspecified for that row, and the
  human's decision is the authoritative resolution.
- **It runs once, pre-split, on the whole dataset uniformly**, exactly
  like preprocess. Labels are synthesized before the split exists, so
  the sacred test set is formed from uniformly-labeled data and is
  differentiated by no partition (#6/#7).

##### The family gate (the load-bearing lock)

Cross-family judging is the protocol's load-bearing property:
same-family judges launder the predictor's own bias as "consensus,"
and majority vote then reduces variance without touching that bias. The
guarantee only holds when the judges are a **different model family from
the model being optimized**.

- **Judges are Claude subagents, so the guarantee holds only when the
  production model is non-Claude.** When the production model is
  Anthropic-family, a Claude panel is *same-family* and the gate
  **hard-blocks** with an explicit error rather than producing a
  silently contaminated baseline. Five same-family judges are not a
  cross-family panel, and the methodology refuses to pretend otherwise.
- **Family is resolved deterministically, never guessed.** A static
  model→family map (anthropic / openai / google / meta / …) classifies
  the production model declared in `plan.md`; when the model string is
  unrecognized, the gate requires an explicit `model_family` field in
  `plan.md` rather than defaulting. An unknown family never silently
  passes the gate.
- **Within the panel, the five judges are one family.** Their diversity
  is rubric framing and sampling, which reduces the panel's *own*
  variance; the *bias* guarantee comes entirely from the panel being a
  different family than the predictor. This is stated plainly because it
  is the exact distinction the rule turns on.

##### Human authority and the audit trail

The human is the authority on the sacred test set, operationalized as
**override power plus full visibility, not mandatory per-row sign-off**:

- **Mandatory sign-off is the escalation queue only.** Every split is
  resolved by the human before labels freeze. Confident-consensus
  labels (≥4-of-5) auto-freeze across train / dev / test alike.
- **The human receives a complete `label_panel.json` audit trail** —
  every row, all five votes, the consensus margin, and each judge's
  rationale — and can **override any frozen label, including any
  test-set row**, before the split runs. Authority is never ceded; it
  is simply not forced to be exercised row-by-row. (Decided 2026-06-02;
  the stricter alternative — manual confirmation of every test-set row
  regardless of consensus — was considered and set aside as
  disproportionate to the 4-of-5 bar.)

**Judge-language coupling.** When the canonical data is multilingual
(§7.1.7), each judge receives the row's `language` tag with the input,
and the panel must be competent in that language. Low-resource
languages weaken the panel; this is a **disclosed limitation**, surfaced
in the audit trail (lower effective consensus on under-supported
languages routes more rows to the human), not a silent failure. v0.7
adds no per-language judge *routing* — that, and cross-lingual label
transfer, stay out of scope.

##### Why this touches no invariant

- **#13 metric independence / no LLM judge** — preserved. The panel
  operates at label *creation*, produces frozen ground-truth *values*,
  and exits before any prompt is scored. Loop and finalize scoring read
  those frozen labels with the same mechanical metrics as before; no
  LLM enters the scoring path. This is the precise line §7.1.3 draws —
  a judge that creates a frozen baseline is not a judge in the scoring
  loop.
- **#6 / #7 sacred test set, read once** — preserved. Labeling runs
  once, pre-split, uniformly, so the test partition is formed from
  uniformly-labeled data and read no new way; the human retains
  override authority over every test-set label.
- **#1 / #2 / #3 stage isolation** — untouched. label-panel runs
  *before* the loop, so it is not a loop stage and adds no subagent to
  the isolated set. The discrepancy, rule-edit, auditor, and adversary
  allow-lists are unchanged; the panel feeds none of them.
- **#20 four-command set** — preserved. label-panel is a consultative
  sub-skill invoked within the `/spp-baseline` labeling step when labels
  are absent, not a fifth `/`-command; its human adjudication reuses
  gate discipline without adding to the G1–G6 set.

The other invariants are untouched on their face: v0.7 introduces no new
prompt section (#12), no loop verdict (#14 — the consensus margin and
escalation queue are descriptive, never a token that halts the loop),
and no change to the gate strings (#8–#11). The synthesized labels and
the `model_family` field are recorded in `plan.md` as a user-reviewed
contract (#15) under the same atomic-checkpoint discipline (#16), and
the REPORT §5 isolation block (#21) is unchanged. The `label_panel.json`
artifact and the `model_family` plan field are additive and
backward-compatible — absent in pre-v0.7 projects, where label-panel is
simply never triggered because labels already exist.

##### Bookkeeping changes by bucket

Partitioned into buckets, each locked in its own PR before downstream
buckets depend on it:

1. **Design pin** — this section. DESIGN-only. **Locked here.**
2. **`label-panel` sub-skill** — the SKILL.md protocol: the five-judge
   panel, the score-blind judge contract, the 4-of-5 consensus rule, and
   the escalation/adjudication workflow.
3. **Schemas** — `LabelVote`, `LabelPanelRow`, and `LabelPanelJSON` in
   `_schemas.py` (per-row votes, consensus margin, accept/escalate
   flag, rationales).
4. **Family gate** — a deterministic model→family resolver with the
   `plan.md` `model_family` fallback, and the hard-block when the
   production model is Anthropic-family.
5. **Consensus + I/O script** — `label_panel.py`: aggregates judge
   outputs into consensus, builds the escalation queue, and writes the
   canonical `label` column. The judging is the subagents; the script
   does consensus math and I/O only, never the judging.
6. **Adjudication workflow** — the escalation artifact format and the
   human review / override loop, including test-set override.
7. **Templates** — the labeling rubric and the `model_family` field in
   `plan.md.template`.
8. **Flow integration** — the preprocess "no label column" handoff to
   label-panel and a minimal note in `phases/spp-baseline.md`. Allow-lists
   unchanged.
9. **Fixture** — a subjective-label task (e.g. tone or helpfulness) with
   raw input and an expected panel output, exercised end-to-end.
10. **Tests + audit** — consensus math, the family gate (blocks on a
    Claude predictor), escalation routing, and the end-to-end pipeline,
    plus the locked-invariants audit (v0.7).

##### Scope boundary

v0.7 is additive: a baseline-labeling front sub-skill, inside the
existing fixed-output-space methodology. It synthesizes labels **only
where they are absent**, never overrides human ground truth (it flags
and freezes; the human overrides), never enters the scoring path, and
never expands or localizes the label space. It does not re-open the
LLM-as-judge-in-scoring non-goal (§7.1.3): judges create a frozen
baseline, they do not score prompts. Per-language judge routing and
cross-lingual label transfer remain out of scope.

**No new dependency.** The judges are Claude Code subagents, already
available to the skill; the consensus script uses only the standard
library; the model→family resolver is a static map. No package, API
key, or external service is added to the shipped surface.

**Locked-invariants audit (v0.7).** All twenty-one §7.1.1 invariants are
untouched by this arc. v0.7 adds a baseline-labeling sub-skill that
operates before the loop and before any scoring; it changes no loop
stage's information access, no metric family, no output space, and no
command set. The seven the arc had to actively preserve — the isolation
set (#1/#2/#3), the sacred test set (#6/#7), the metric-independence rule
(#13), and the four-command set (#20):

- **#1 per-stage isolated subagents** — preserved. label-panel runs
  *before* the loop, so it is not a loop stage and adds no subagent to
  the isolated set. The five judge subagents are baseline-*creation*
  workers that exit before any prompt is scored; the discrepancy,
  rule-edit, auditor, and adversary allow-lists are unchanged. The
  family gate (`scripts/_models.py`) and the consensus aggregator
  (`scripts/label_panel.py`) feed none of those stages. No data input is
  added to any loop stage.
- **#2 auditor score-blindness** — untouched. No v0.7 path surfaces any
  score to the auditor. `label_panel.json` is created pre-loop and read
  by no loop stage; the judges are themselves score-blind because at
  baseline creation no scores, predictions, or eval artifacts exist.
- **#3 no row content to rule-edit** — unchanged. label-panel produces
  canonical labels before the loop and never feeds the rule-edit
  subagent; its allow-list is untouched.
- **#6 / #7 sacred test set, read once** — preserved and, if anything,
  strengthened. `write_labeled_baseline` freezes labels **once,
  pre-split, on the whole dataset uniformly** (the consensus aggregator
  differentiates no row by partition because partitions do not yet
  exist), so the split and the sacred test set are formed *after*
  labeling from uniformly-labeled data. The human retains override of
  any frozen label, including any test-set row, before the split runs.
  The integration test `test_label_panel_pipeline` confirms the frozen
  labels flow into `split.py` and `eval.py` with the test partition read
  no new way.
- **#13 metric independence / no LLM judge** — preserved; this is the
  invariant the arc engages most directly, and it holds. The panel
  operates at label *creation*, produces frozen ground-truth *values*,
  and exits before any prompt is scored. `eval.py` reads those frozen
  labels with the same mechanical metric as any other baseline and never
  opens `label_panel.json` (asserted by `test_label_panel_pipeline`); no
  LLM enters the scoring path. The cross-family gate
  (`_models.assert_cross_family`) additionally guarantees the judge is a
  *different* model family than the predictor, so the created baseline
  cannot launder the predictor's bias as consensus. This is precisely
  the line §7.1.3 draws — a judge that creates a frozen baseline is not
  a judge in the scoring loop — so the LLM-as-judge-in-scoring non-goal
  is **not** re-opened.
- **#20 four-command set** — preserved. label-panel is a consultative
  sub-skill invoked inside the `/spp-baseline` labeling step (step 5)
  when labels are absent, not a fifth `/`-command; its human
  adjudication reuses gate discipline without adding to the G1–G6 set.
  The `label_panel.py` subcommands (`aggregate`, `queue`, `resolve`,
  `write-labels`) are internal helpers run by the phase, not new
  user-facing commands.

The other fourteen are untouched on their face: v0.7 introduces no new
prompt section (#12 — it synthesizes labels, not the six-section prompt),
no loop verdict (#14 — the consensus margin and escalation queue are
descriptive, never a token that halts the loop), and no change to the
gate strings (#8–#11). The synthesized labels, the resolved production
family, and the panel configuration are recorded in `plan.md` as a
user-reviewed contract (#15 — the `MODEL_FAMILY` and `LABEL_SYNTHESIS`
fields) written under the same atomic-checkpoint discipline (#16), and
the REPORT §5 isolation block (#21) is unchanged. The `label_panel.json`
artifact and the `model_family` plan field are additive and
backward-compatible — absent in pre-v0.7 projects, where label-panel is
simply never triggered because labels already exist.

### 7.2 Examples — confidentiality and provenance

The examples in `examples/` demonstrate workflow and artifact shapes,
not real data. The canonical binary-classification example is a
skeleton: file structure and walkthrough are real; data, baseline
labels, and prompt content are placeholder. Where the methodology came
from a real classification project under NDA, that project is
referenced abstractly — aggregate metrics and failure-mode taxonomies
may be cited; specific row contents, labels, or prompt text may not be
reproduced.

The line is drawn between **findings** (citable) and **protected
content** (not reproducible):

- **Citable as findings:** aggregate metrics (e.g. `test F1 = 0.941`),
  the existence and shape of failure clusters (e.g. cluster 4.4
  cross-family register-vs-addressee weighting; the length-correlated
  cross-family failure pattern), per-model F1 deltas, the 4-cluster
  taxonomy structure.
- **Not reproducible:** specific row contents, baseline labels, prompt
  text from the source project, identifiable post bodies, or any data
  field that could re-identify a source-project row.

This applies to all worked examples in v1. Phase 3 work must scope
example artifacts accordingly: `baseline.csv` files committed to
`examples/` are dummy data with the same *shape* as real baselines,
not real-data extracts. The README's GPT cluster-4.4 reference is fine
as written because it cites numbers and patterns, not row contents.

---

## 8. Open questions and my stances

The kickoff specified three open questions with the user's stated
preferences. I have **no disagreement** with any of the user's stances;
each is recorded here with my agreeing reasoning so future contributors
can see the rationale, not just the decision.

### 8.1 Sub-skill placement: nested or peer?

**User's stance (v1):** Nested at `skills/run/sub-skills/`.
Cleaner install story; defer extraction to v0.2 gated on user feedback
that `prompt-architect` or `metric-design` are useful standalone.

**My stance:** Agree. Nested for v1.

**Reasoning:** The "compose, don't absorb" principle is about *what these
sub-skills do*, not *where they live on disk*. Nested placement
preserves the composition principle (they remain independently useful
*conceptually*, with their own SKILL.md and self-contained logic) while
giving the user one install operation. If/when feedback shows users want
`prompt-architect` standalone, extraction is a mechanical refactor — the
sub-skills are already self-contained, so extracting them is path
manipulation, not redesign. v0.2 is the right time for that decision
because it will be informed by actual usage signal.

### 8.2 Loop resumption after interruption

**User's stance:** Defer to v0.2. v1 documents that interruption requires
restart. Implementing safe state persistence is a design pass of its own
and shipping a buggy version is worse than shipping without it.

**My stance:** Agree. Defer.

**Reasoning:** Resumability looks simple but is actually hard — the
question is not "can we save state" but "what is the unit of work that
can be safely resumed." A mid-iteration interruption can leave the
prompt edited but unevaluated, the discrepancy analysis half-written,
the auditor's review pending. Each of these has different recovery
semantics. v1 sidesteps this by making the iteration the unit: an
interrupted iteration is discarded, the prior iteration's `run_NN/`
directory is the resume point, and the user re-runs `/spp-loop`. The
README and `/spp-loop` command doc must say this clearly so users
running long jobs know to plan for it.

### 8.3 Non-English data

**User's stance:** v1 explicitly assumes English. Document the
assumption in README's "When to use this" section.

**My stance:** Agree. English-only for v1.

**Reasoning:** Multilingual classification is not a translation problem
— it is a methodology problem. The auditor's
categorical-vs-row-specific judgment depends on understanding the
language well enough to articulate categorical rules. The
`baseline-quality` calibration questions assume the reviewer can read
the data. The `prompt-architect` Persona and Rules sections are written
in the operator's language. None of these survive a "just translate the
prompt at the boundary" approach. Treating multilingual as its own
design pass — likely involving language-specific judges and possibly
multi-judge metrics — is the honest path. v1 documents the assumption
prominently.

---

## 9. Resolved decisions from Phase 0 review

The three open questions raised in the original draft have been
resolved by the user during Phase 0 review. Recording the resolutions
here so the rationale persists with the document.

1. **Canonical example naming.** Resolved: task-type for the directory
   (`examples/binary-classification/`), domain referenced inside the
   walkthrough. The three examples are a methodology gradient
   (binary → multi-class → imbalanced metric design), not a domain
   catalog. Detailed rationale recorded inline in §6.

2. **Auditor frequency.** Resolved: non-optional, per-iteration. If
   per-iteration cost becomes an adoption barrier post-v1, the correct
   escape valve is **batch auditing** (auditor reviews the last N
   iterations as a group, still without score access), **not frequency
   reduction** — batching preserves information isolation; frequency
   reduction would silently skip categorical-vs-row-specific review on
   some iterations. Detailed rationale recorded inline in §4.2; the
   anti-pattern is also called out in §7.1's non-goals so future
   contributors are redirected.

3. **Cross-model summary.** Resolved: reclassified as a deliberate
   non-goal (§7.1.3) — `spp` optimizes per target model; cross-model
   comparison is downstream model selection. v1 produces per-model
   REPORTs only; users running multiple models compare them manually.

---

## 10. Glossary

Terms of art used throughout `spp` documentation. Future docs (README,
SKILL.md, command docs, agent docs, templates, REPORT.md) reference
these definitions rather than redefining inline.

**Baseline overfitting.** A failure mode in which the prompt learns the
specific labels in the baseline rather than the underlying class
definition. Symptom: high score on labeled data, collapse on
similar-but-unseen data. The primary failure mode `spp` is designed to
prevent.

**Model overfitting.** A failure mode in which the prompt learns to
exploit one model's instruction-following style and degrades on other
models. Acceptable for production with model lock-in if documented;
dangerous if models are swapped without re-validation. `spp` documents
this rather than preventing it in v1.

**Sacred test set.** The held-out portion of the stratified split that
is not touched until Phase 3 (`/spp-finalize`). The optimization loop
sees train + dev only. The test set's role is to provide an honest
generalization estimate uncontaminated by iteration. Touching it
mid-loop voids the methodology's claim.

**Auditor information isolation.** The non-negotiable design property
that the auditor sub-agent sees the prompt diff and the prior
iteration's discrepancy analysis but **never sees the new iteration's
scores** (dev F1, recall, precision, etc.). This isolation is what
forces the auditor to evaluate rule generalizability on its merits
rather than rationalizing via outcome. Breaking the isolation breaks the
methodology.

**Categorical rule edit.** A prompt rule edit that addresses a class of
rows defined by an articulable property (e.g., "ambiguous short
self-disclosures with no explicit context should be Uncertain"). Kept
by the auditor.

**Row-specific rule edit.** A prompt rule edit that patches one weird
row, often dressed up to look general (e.g., "rows containing
'minoxidil' followed by a question mark are False"). Flagged by the
auditor for revert or generalization. Accumulating row-specific edits is
the mechanism by which baseline overfitting compounds across iterations.

**HITL gate.** A human-in-the-loop gate: a specific point in a `spp`
command where execution stops and waits for an explicit allowed
response from the user before proceeding. Six gates G1–G6 are defined in
the kickoff and enforced by their respective commands. Vague approval
("looks good") is not an allowed response; gates require specific
acknowledgements or specific corrections.

**Verdict-gated preconditions (v0.2).** Two of the six gates carry an
additional precondition under v0.2 — a verdict-gated sub-skill must
return `ready` before the gate's normal approval-substring check can
advance. **G1 (plan approval)** advances iff `schema-designer`'s
most recent verdict is `ready` OR `plan.md` §11 contains an entry
whose Reason field contains the literal substring
`schema-not-ready override` and references the `schema-designer`
sub-skill (per §7.1.1 sub-skill ordering layer; `schema-designer`
SKILL.md §6). **G2 (baseline approval)** follows the same pattern
with `baseline-quality`'s `not-ready override` substring (per
`baseline-quality` SKILL.md §6). The other four gates (G3, G4, G5,
G6) have no verdict-gated precondition. Future verdict-gated
sub-skills inherit this precondition shape; renumbering (a new
G1.5, shifting G2–G6 to G3–G7) is explicitly rejected by §7.1.1
sub-skill ordering layer — the verdict gates the gate's contents,
not a separate check, and the uniformity across both verdict-gated
sub-skills is the design.

**`plan.md` (as contract).** The output of `/spp-init`, produced by the
designer agent in consultation with the user. Subsequent commands
(`/spp-baseline`, `/spp-loop`, `/spp-finalize`) re-read it fresh and
verify their actions are still on-spec. Mid-task changes update
`plan.md` with timestamp and reason. It is not a wish list; it is the
binding agreement that defines what the rest of the methodology is
optimizing toward.

**Feature-group prompt splitting.** When a task's OUTPUT_SCHEMA spans
multiple feature groups — subsets of fields that share a reasoning
pattern, an input dependency, or a metric profile — the methodology
defaults to one prompt per group, with each group's prompt living in
its own `spp/` task directory. Splitting buys: focused `<rules>`
sections per prompt (no cross-field rules competing for context),
per-group metric optimization headroom (each prompt's iteration
trajectory operates without other groups' trade-offs constraining
it), clean auditor scoping (a rule edit affects exactly one prompt =
exactly one set of target fields), and reusability (a feature-group
prompt can be reused across tasks sharing that group). The exception
is K=1 (single field) or schemas where field interdependencies are
dense enough that splitting introduces more coordination overhead
than it saves — for example, hierarchical labels where one field's
value gates another's validity and conditional reasoning lives most
naturally in one prompt, or multi-field extraction over a shared
input where every field reads the same body and the per-field
`<rules>` would heavily overlap. The designer agent surfaces the
feature-grouping decision during `/spp-init` consultation
([`agents/designer.md`](../skills/run/agents/designer.md) §5.0),
before any K=1-vs-K>1 OUTPUT_SCHEMA decision is committed; if the
decision lands on "keep unified," the designer records the rationale
in `plan.md` §10's open-questions section so future-them and the
auditor understand why a multi-field prompt was chosen over
splitting. The v0.2 bookkeeping (multi-field within a single prompt
per §7.1.1) is still supported for the unified-task exception; the
bookkeeping is not redundant — it covers the cases where splitting
doesn't apply, exemplified by the canonical examples
([`examples/multi-field-extraction/`](../examples/multi-field-extraction/),
[`examples/nested-schema/`](../examples/nested-schema/)) shipped at
v0.2's bucket-7 close. **Cross-task composition is out of `spp`'s
scope** — `spp` produces production-grade prompts, and the user owns
the production pipeline that composes them. Tasks that have been
split into N `spp/` directories are tracked by the user (via naming
conventions, parent directories, the user's own composition logic
at the production layer), not by `spp`; the methodology's contract
stays "one `spp/` task = one prompt = one optimization loop." The
[`prompt-architect`](../skills/run/sub-skills/prompt-architect/SKILL.md)
sub-skill's six-section discipline scopes per sub-task when a prompt
is part of a split task — `<persona>`, `<task>`, `<rules>`,
`<output_format>`, `<example_input>`, `<example_output>` all
describe the sub-task's fields, not the full original task's
fields.

---

End of `DESIGN.md`. Phase 0 complete. Proceeding to Phase 1.
