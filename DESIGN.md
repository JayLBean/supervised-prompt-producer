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

**Phase 3 example-naming convention (recorded here so it persists):**
The three worked examples are named by *task type*, not domain:
`examples/binary-classification/`, `examples/multi-class-classification/`,
`examples/edge-case-imbalanced/`. The hair-loss-discourse domain is
referenced inside the binary-classification example's walkthrough doc and
README, not in the directory name. Rationale: the three examples are a
methodology gradient (binary → multi-class → imbalanced metric design),
not a domain catalog. A reader scanning `examples/` should see what
each example *teaches about the methodology*, not what subject matter it
happens to use.

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
(§4.2); `plan.md` as the contract every phase re-reads fresh (§10).
These principles are **output-shape-agnostic**. They apply to any
supervised prompt-engineering task with a labeled baseline.

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
   ground truth. *Covered in a subsequent v0.2 design PR.*
4. **Sub-skill ordering layer** — where the new `schema-designer`
   sub-skill (locked below) lands in the consultation order, and
   how its verdict gate renumbers or interleaves with G1–G6.
   *Covered in a subsequent v0.2 design PR.*
5. **Compat layer** — what migration of existing v0.1.0 `plan.md`
   files to v0.2 OUTPUT_SCHEMA shape looks like. *Covered in a
   subsequent v0.2 design PR.*
6. **Locked-invariants inventory** — explicit list of v0.1.0
   methodology guarantees that v0.2 must preserve verbatim
   (per-stage isolation invariants, sacred test set, REPORT
   invariant block, etc.) so generalization does not silently
   weaken them. *Covered in a subsequent v0.2 design PR.*
7. **Fixtures layer** — the canonical examples (`examples/`)
   needed to validate the v0.2 scope, including a
   multi-field-extraction task and a nested-schema task.
   *Covered in a subsequent v0.2 design PR.*

The schema and metrics layers are buckets 1 and 2 of 7. The
remaining layers are flagged above and pinned in subsequent
PRs; the structure of this section is intentionally additive so
future PRs slot into the same "Bookkeeping changes by layer"
frame.

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

#### 7.1.2 Further-out roadmap

v0.1.0's bookkeeping is intentionally narrow in several other
directions where the methodology has natural extensions. Each is
roadmap, not a deliberate boundary; v0.x increments will reach these
in turn.

- **Multi-judge subjective metrics.** Tasks where ground truth itself
  requires LLM judgment (style, tone, helpfulness, coherence) need a
  multi-judge protocol that v0.1.0's `metric-design` independence
  rule (§5) explicitly forbids. Roadmap: v0.3. The multi-judge design
  is its own scope question; the methodology's information-isolation
  principles apply but the validation primitives change shape.
- **Multilingual data.** v0.1.0 assumes English. Multilingual
  classification has tokenization, label-space localization, and
  judge-language coupling considerations the bookkeeping does not
  yet handle. Roadmap: v0.3, separate design pass.
- **Cross-model synthesis.** v0.1.0 produces per-model `REPORT.md`
  documents; users running multiple models synthesize manually.
  Roadmap: v0.4. The synthesis shape is its own design question
  (which deltas matter; which are noise; how to present them
  honestly).
- **Loop resumption mid-iteration.** v0.1.0 makes the iteration the
  unit of work; interrupted iterations are discarded and re-run.
  Roadmap: TBD. Mid-iteration resumption requires per-step
  checkpointing across the discrepancy / rule-edit / auditor /
  scoring stages without weakening the per-stage isolation contract;
  a clean design has not been worked out.

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
- **LLM-as-judge metrics for v0.1.0's `metric-design` independence
  rule.** `metric-design` §5 forbids LLM judges in v0.1.0 because
  v0.1.0 users cannot reliably draw the boundary between cross-family
  judges (defensible) and same-family judges (silent
  contamination); rather than parameterize the rule, v0.1.0 forbids
  the entire pattern. Multi-judge subjective metrics in v0.3 will
  re-open this for the cases where ground truth itself requires
  judgment, but the v0.1.0 stance against `metric-design` accepting
  any LLM judge is deliberate.

When in doubt, lean toward roadmap rather than deliberate. A v0.x
version can always reach a roadmap item; a deliberate non-goal is
harder to undo because it shapes the methodology's identity. The
items above are deliberate because the underlying problem is
methodologically different, not because the bookkeeping is narrow.

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

3. **Cross-model summary.** Resolved: deferred to v0.4. v1 produces
   per-model REPORTs only. Users running multiple models manually
   synthesize. Recorded in §7.1's non-goals list.

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

**`plan.md` (as contract).** The output of `/spp-init`, produced by the
designer agent in consultation with the user. Subsequent commands
(`/spp-baseline`, `/spp-loop`, `/spp-finalize`) re-read it fresh and
verify their actions are still on-spec. Mid-task changes update
`plan.md` with timestamp and reason. It is not a wish list; it is the
binding agreement that defines what the rest of the methodology is
optimizing toward.

---

End of `DESIGN.md`. Phase 0 complete. Proceeding to Phase 1.
