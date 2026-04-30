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

## 3. Slash commands

Four entry points, each in `.claude/skills/spp/commands/`, each operating
on `spp/<task_name>/` in the user's project.

| Command | One-line purpose |
|---|---|
| `/spp-init` | Consultation: read repo, ask informed questions, produce `plan.md` (the contract). Idempotent and resumable. |
| `/spp-baseline` | Phase 1 + 1.5: label data with `baseline-quality` review, generate stratified `splits.json`. |
| `/spp-loop` | Phase 2: run optimization iterations with auditor (and optional adversary) active; stop on dev plateau or overfitting guard. |
| `/spp-finalize` | Phase 3: run sacred test set, generate per-model `REPORT.md` and `PROMPT_FROZEN_v01.md`. |

Each command enforces its trailing HITL gate (G1–G6 in the kickoff) by
refusing to proceed without an explicit allowed response.

**`<task_name>` semantics:** `/spp-init` accepts an optional task name as
a positional argument (e.g. `/spp-init hair-loss-discourse`). If omitted,
the designer agent asks for one as the first consultation question. The
argument becomes the directory name under `spp/` — kebab-case, no
spaces, no slashes. Once chosen, it is fixed for the duration of the
task; renaming requires manual directory rename and is out of scope for
v1.

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

### 4.2 auditor (runs after each `/spp-loop` iteration) — **load-bearing**

This is the highest-leverage component of the entire skill. It is the
design lock that distinguishes `spp` from automated optimizers like DSPy
and APE. The rest of the methodology is plumbing; the auditor is the
methodology.

**Unique information access (the property that must not be broken):**

The auditor sees:

- The prompt diff between iteration N-1 and iteration N.
- The discrepancy analysis from iteration N-1 (the rows that disagreed
  with the prompt and the proposed rule edits intended to fix them).

The auditor **does not see**:

- The new scores on iteration N (dev F1, recall, precision, confusion
  matrix — none of it).
- Any post-edit evaluation outputs.

This information isolation is not stylistic. It is the methodology. If the
auditor sees the new scores, it will rationalize *any* rule edit that
improved the metric, including row-specific patches that overfit. The
absence of outcome data forces the auditor to evaluate rule
generalizability on its merits — "would this rule still apply to a
similar but unseen row?" — rather than via outcome.

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

For v1 these live nested at `.claude/skills/spp/sub-skills/` (see §7
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

### 7.1 Non-goals (canonical reference for "out of v1 scope")

The following are **deliberately not supported in v1**. PRs that add them
without first opening a design discussion and updating the roadmap will
be rejected on scope grounds. This list is the single source of truth
for what v1 does not do; future docs reference it rather than re-listing.

- **Extraction tasks** (named entity, span extraction, structured data
  extraction). Roadmap: v0.2.
- **Generation tasks** (summarization, rewriting, free-form text
  generation). The whole methodology assumes a fixed label space; it does
  not transfer cleanly to generation. Roadmap: v0.3 at earliest, possibly
  separate methodology.
- **RAG prompts** (retrieval-augmented). Out of scope; different failure
  modes, different evaluation primitives.
- **Agentic prompts** (tool-using, multi-turn agents). Out of scope.
- **Multi-judge subjective metrics.** v1 enforces that the metric is
  computable independently of the model being optimized. Tasks where the
  ground truth itself requires LLM judgment (style, tone, helpfulness)
  need a multi-judge design that is roadmap v0.3.
- **Automated prompt search (DSPy-style).** `spp` is a methodology
  discipline, not an optimizer. The user stays in the loop. PRs proposing
  search or auto-edit logic should instead propose composition with
  existing optimizers.
- **Model-agnostic evaluation.** v1 is per-model by design. Multi-model
  dev loops are roadmap v0.4.
- **Multilingual data.** English-only, documented in README. Roadmap:
  separate design pass, not a v0.x increment.
- **Loop resumption mid-iteration.** v1 makes the iteration the unit;
  interrupted iterations are discarded and re-run. Roadmap: v0.2.
- **Cross-model summary documents.** v1 produces per-model `REPORT.md`
  only. Users running multiple models manually synthesize. Roadmap: v0.4
  alongside multi-model dev loops.
- **Auditor frequency reduction.** If per-iteration auditor cost becomes
  a problem, the post-v1 fix is batch auditing (see §4.2), not running
  the auditor less often. PRs proposing "audit every N iterations" knobs
  should be redirected.

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

**User's stance (v1):** Nested at `.claude/skills/spp/sub-skills/`.
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
