---
name: run
description: Run the spp methodology against a classification task. Use when the user wants to produce a production-grade classification prompt through disciplined supervised prompt learning, has a labeled baseline available (or is willing to label one), and wants human-in-the-loop control over the process. Walks through four phases — consultation, baseline-and-splits, optimization loop, finalization — producing a frozen prompt and a REPORT. The user does not type slash commands per phase; the agent walks the methodology while the user reviews and approves at gates.
---

# spp — Supervised Prompt Producer (the `run` skill)

This document is the **entry point** for `spp`'s methodology
skill. The plugin manifest at `.claude-plugin/plugin.json`
declares the plugin; this `SKILL.md` declares the skill the
plugin ships. When the user describes a classification task,
when they invoke `/spp:run`, or when Claude Code otherwise
activates this skill from the YAML description above, this
document is what the agent reads first.

The skill's job here is **introduction-and-routing**: name
what `spp` is, name the artifact taxonomy (four phases,
three agents, three sub-skills, four templates), point at
where the canonical detail for each component lives, and
orient the agent for the methodology walkthrough. The agent
that runs `spp` reads this file, then reads the phase
specifications under `phases/` in order — `phases/spp-init.md`,
`phases/spp-baseline.md`, `phases/spp-loop.md`,
`phases/spp-finalize.md` — pausing at each HITL gate (G1–G6)
for user approval. The four phase names retain their
`/spp-*` prefix as a naming convention; they are **not**
slash commands the user invokes separately.

The substantive work happens in the eleven artifacts this
document points at; the entry point's job is to be the
front door so a reader knows which room to walk into. An
entry point that re-derives every phase's pre-conditions in
its own words goes stale the moment any phase's
pre-conditions change; this entry point resists that drift
by pointing at the canonical detail and trusting it.

The doc has its own six-section shape — not the agent/
sub-skill six and not the eight of the phase docs. An
entry-point-shaped artifact needs entry-point-shaped
sections.

---

## 1. Identity

`spp` is a Claude Code skill that produces production-
grade classification prompts through **disciplined,
human-in-the-loop supervised prompt learning**. Given a
classification task and labeled examples, `spp` walks the
user through four phases (consultation → labeling-and-
splits → optimization → test-and-ship), invoking
specialized agents and sub-skills under strict
information-isolation discipline, and produces a frozen
prompt artifact plus a `REPORT.md` documenting the
methodology's outcome.

The methodology defends against two failure modes:
**baseline overfitting** (the prompt fits idiosyncrasies
of the labeled baseline that don't generalize) and, with
documentation, **model overfitting** (the prompt is tuned
to one model's quirks and is fragile cross-model).
Canonical statement of the design and motivations:
[`../../DESIGN.md`](../../DESIGN.md). For the
methodology's user-facing description:
[`../../README.md`](../../README.md). For the rules
about how changes get made: [`../../CLAUDE.md`](../../CLAUDE.md).

`spp` is **not** an automated optimizer (DSPy / GEPA /
APE). The auditor's information-isolation property is
the design lock that distinguishes the methodology from
score-driven optimization frameworks; see §5 below and
`agents/auditor.md` §2.

---

## 2. The methodology in one diagram

```
Phase 1            Phase 1.5             Phase 2                          Phase 3
─────────          ─────────             ───────                          ───────
/spp-init    ──>   /spp-baseline   ──>   /spp-loop                  ──>   /spp-finalize
                                          ┌─────────────────┐
  designer         baseline-quality       │ iter N:         │             sacred test set
  metric-design                           │   inference     │             REPORT.md
  prompt-architect                        │   discrepancy   │             PROMPT_FROZEN_v01
                                          │   adversary?    │
                                          │   audit         │
                                          │   gate          │
                                          └─────────────────┘
                                          (auditor + adversary
                                           per iteration)

  G1                G2     G3              G4 + per-iteration               G5     G6
  (plan)            (base) (splits)        (dry-run + auditor verdicts)     (test) (ship)
```

The four phase names map cleanly to the methodology's four
phases. The six gates (G1–G6) interleave between phases and
within `/spp-loop`. The auditor and adversary operate per
iteration inside `/spp-loop` under the information-isolation
contract documented at `agents/auditor.md` §2 and
`agents/adversary.md` §6.

The README's `mermaid` diagram is the more detailed view;
this diagram is the at-a-glance version for readers who just
need to remember the shape.

---

## 3. The artifact taxonomy

Three artifact types in `spp`'s vocabulary, each with
distinct structural and operational roles.

### 3.1 Phases (4) — methodology stages the agent walks the user through

| Phase | Role | Outputs | Gates |
|---|---|---|---|
| [`/spp-init`](phases/spp-init.md) | Consultation; the designer agent walks the user through the task's contract. | `plan.md`, `loop_spec.md` | G1 |
| [`/spp-baseline`](phases/spp-baseline.md) | Labeling and splits; the baseline-quality sub-skill audits the labels. | `data/baseline.csv`, `data/splits.json` | G2, G3 |
| [`/spp-loop`](phases/spp-loop.md) | The optimization loop. Auditor every iteration; adversary optionally. | Per-iteration artifacts under `runs/<model>/run_NN/`; `SUCCESS.md` / `EARLY_STOP.md` / `FAILED.md`. | G4 + per-iteration auditor verdict gate |
| [`/spp-finalize`](phases/spp-finalize.md) | Sacred-test-set evaluation, REPORT generation, prompt freeze. | `test_eval.json`, `REPORT.md`, `PROMPT_FROZEN_v01.md` | G5, G6 |

The `/spp-*` slash-prefixed names are **naming convention** for
the four phases — not slash commands the user types. Users invoke
the skill via `/spp:run` (or by describing a classification task
to Claude Code); the agent that runs the skill walks the four
phase docs in order. Each phase doc carries the canonical
pre-conditions, execution flow, gate enforcement, outputs,
failure modes, and "what the phase does NOT do." This entry
point does not duplicate that content; the phase docs are the
single source of truth for how each phase runs.

The v1 phase set is **closed at four**. Adding a fifth requires
a methodology change per `DESIGN.md` §3.

### 3.2 Agents (3) — cognitive workers invoked by phases

Each agent's distinguishing property is **structurally
distinct information access**. Agents are invoked by the
phase logic; the user does not invoke agents directly.

| Agent | Role | Information access | Invoked by |
|---|---|---|---|
| [`designer`](agents/designer.md) | Talks to the user during consultation. Produces `plan.md`. | Sees the repo, asks informed questions. No run-time scores exist yet at consultation time. | `/spp-init` |
| [`auditor`](agents/auditor.md) | Reviews proposed rule edits per iteration. Returns a per-edit verdict (`categorical` / `row-specific` / `unclear`). | Sees the prompt diff, prior discrepancy analysis, `plan.md` §2, and prior `auditor_review.md` files. **Never the new scores.** | `/spp-loop` |
| [`adversary`](agents/adversary.md) | Generates 2–3 synthetic adversarial rows per iteration when `ADVERSARY_FLAG = on`. Optional, opt-in. | Sees the current prompt, prior discrepancy, `plan.md` §2. Not the baseline, not the scores, not the test set. | `/spp-loop` (conditional) |

The auditor's information isolation is the **load-
bearing design property** that distinguishes `spp` from
automated optimizers. Canonical statement:
`agents/auditor.md` §2. The runner-level operational
enforcement: `phases/spp-loop.md` §4 step 11 and
`CLAUDE.md` §8.

The v1 agent set is **closed at three**. Adding a
fourth requires answering the structural-distinctness
question that `DESIGN.md` §4 establishes.

### 3.3 Sub-skills (6) — informational reference material

Sub-skills inform decisions; they are **not invoked as
conversational entities**. Read by the designer (during
consultation), by Claude during `/spp-loop`, or by users
wanting the rationale.

| Sub-skill | Role | Authority |
|---|---|---|
| [`metric-design`](sub-skills/metric-design/SKILL.md) | Guides metric selection during `/spp-init`. Enforces the independence rule (no LLM-as-judge for v1). | Informational. Output feeds `plan.md` §4. |
| [`baseline-quality`](sub-skills/baseline-quality/SKILL.md) | Adversarial review of baseline labels before splits. | **Verdict-enforcement.** Three-tier verdict (`ready` / `revise` / `not-ready`) gates `/spp-baseline` G2. |
| [`prompt-architect`](sub-skills/prompt-architect/SKILL.md) | Explains the six-section XML prompt template. | Informational. Structural discipline enforced via templates and the auditor. |
| [`schema-designer`](sub-skills/schema-designer/SKILL.md) (v0.2) | Renders and validates the `OUTPUT_SCHEMA` during `/spp-init`. | **Verdict-enforcement.** Three-tier verdict (`ready` / `revise` / `not-ready`) gates schema acceptance; output feeds `plan.md` §2. |
| [`technique-advisor`](sub-skills/technique-advisor/SKILL.md) (v0.5) | An extensible catalog matching `/spp-loop` failure symptoms to prompting techniques; consulted by the discrepancy stage. | Informational (ungated). Surfaces a categorical recommendation the user adopts via a `plan.md` §11 revision. |
| [`preprocess`](sub-skills/preprocess/SKILL.md) (v0.6) | Maps raw input data to the canonical `baseline.csv` as the first step of `/spp-baseline`. | Informational. Authors a deterministic, human-reviewed `preprocess.py`; output feeds the canonical `baseline.csv` + a `plan.md` §6 mapping record. |

The sub-skill set **grows by version** as structurally
distinct decisions enter the methodology — it is not a
fixed roster. v0.1.0 shipped three (metric selection,
baseline integrity, prompt structure); v0.2 added
`schema-designer` (output-schema design), v0.5
`technique-advisor` (failure-driven technique
suggestions), and v0.6 `preprocess` (raw-data
canonicalization). Each maps to a decision the others do
not cover; adding one requires the same
structural-distinctness justification a new agent would
(`DESIGN.md` §4), recorded in a design pin.

### 3.4 Templates (4) — task-specific instantiations

Not part of the agent / phase / sub-skill taxonomy proper,
but listed here for completeness. Templates are filled at
consultation time and consumed by downstream phases.

- [`templates/plan.md.template`](templates/plan.md.template)
  — the methodology contract.
- [`templates/loop_spec.md.template`](templates/loop_spec.md.template)
  — the loop's run-time mechanics.
- [`templates/prompt_v01.md.template`](templates/prompt_v01.md.template)
  — the initial prompt skeleton, six-section XML
  structure.
- [`templates/REPORT.md.template`](templates/REPORT.md.template)
  — the post-finalize REPORT shape.

Each template carries inline `<!-- comments -->`
explaining placeholders and validation rules. The
Phase 4 template linter (forward work) verifies them
mechanically.

---

## 4. Where to start

**For users new to `spp`.** Read
[`../../README.md`](../../README.md) first — the
methodology document, written for human readers
unfamiliar with the project. Then read
[`../../DESIGN.md`](../../DESIGN.md) if you want
the design rationale (why the methodology is shaped this
way, what failure modes it defends against, what it is
*not*). Then come back here for the artifact taxonomy.
Skip directly to running the skill only after you have
understood what `spp` is doing methodologically;
mechanical execution without methodological understanding
produces prompts that look right and break in production.

**For users with a classification task.** Either describe
the task to Claude Code (the skill activates from this
file's `description` field above) or invoke `/spp:run
<task-name>` from a project where the plugin is installed.
The agent that runs the skill will read this file, then the
phase docs in order. The designer agent walks Phase 1
(`/spp-init`) and produces `plan.md` plus `loop_spec.md`.
Approve at G1; proceed to Phase 2 (`/spp-baseline`) for
labeling and splits; then Phase 3 (`/spp-loop`) for the
optimization; then Phase 4 (`/spp-finalize`) for the
sacred-test-set evaluation and REPORT. Each phase's
pre-conditions verify the prior phase's outputs are in
place — you cannot skip phases. If a pre-condition fails,
the phase exits with a specific error; fix the named issue
and re-invoke.

**For the agent reading this skill.** When the skill
activates, read this file end-to-end first, then read the
phase docs at `phases/<name>.md` in the order
`spp-init` → `spp-baseline` → `spp-loop` → `spp-finalize`,
following each phase's canonical execution flow as the
single source of truth. **This entry point does not
duplicate the phase docs' pre-conditions, gate enforcement,
or output specifications.** That detail lives in the phase
docs. The entry point exists to introduce `spp`'s shape and
to name where each component's authoritative documentation
lives. If this file and a phase doc appear to disagree,
trust the phase — this entry point is index-shaped and may
have drifted; the phase docs are operational-shaped and are
the canonical source.

---

## 5. The methodology's load-bearing properties

The properties below distinguish `spp` from automated
optimizers and from naive prompt-engineering loops. Each
is one sentence here with a pointer to the canonical
statement; this entry point does not re-derive the
property, it points at where the property lives.

- **Auditor information isolation.** The auditor sees
  prompt diffs and prior discrepancy analysis but
  **never the new scores**. The design lock against
  optimization-driven row-specific patches.
  Canonical: [`agents/auditor.md`](agents/auditor.md)
  §2; `../../DESIGN.md` §4.2;
  `../../CLAUDE.md` §8.

- **Sacred test set.** The test partition is read
  exactly once, by `/spp-finalize`, after gates G1–G4
  have approved. The methodology's claim against
  baseline overfitting hinges on this discipline.
  Canonical:
  [`phases/spp-finalize.md`](phases/spp-finalize.md)
  §4 step 3; `../../DESIGN.md` §10 glossary.

- **Verdict-enforced gates.** Sub-skill and agent
  verdicts gate command advancement via literal-string
  override-substring matching in `plan.md` §11. Three
  instances of the pattern: `/spp-baseline` G2,
  `agents/auditor.md`'s output shape, `/spp-loop`'s
  per-iteration gate. Canonical:
  [`phases/spp-baseline.md`](phases/spp-baseline.md)
  §5;
  [`phases/spp-loop.md`](phases/spp-loop.md) §5.

- **`plan.md` as contract.** All phases re-read `plan.md`
  fresh at invocation; it is the single source of truth
  for the task's contract. No phase caches `plan.md`'s
  contents across invocations.
  Canonical: `../../DESIGN.md` §10 glossary;
  [`templates/plan.md.template`](templates/plan.md.template).

- **Six-section prompt structure.** The XML prompt
  has exactly six sections (`<persona>`, `<task>`,
  `<rules>`, `<output_format>`, `<example_input>`,
  `<example_output>`) plus optional model-specific
  directives at the header. The structure is fixed;
  iterations refine content within sections.
  Canonical:
  [`sub-skills/prompt-architect/SKILL.md`](sub-skills/prompt-architect/SKILL.md);
  [`templates/prompt_v01.md.template`](templates/prompt_v01.md.template).

- **Literal-string gate approval.** All six HITL
  gates require literal-string-equality match on the
  user's recorded approval phrase from `plan.md` §9.
  Whitespace-stripped, case-normalized, punctuation
  matters, surrounding text is a non-match. Canonical:
  [`phases/spp-init.md`](phases/spp-init.md) §5
  (the pattern source for G1; G2–G6 inherit).

- **Methodology-affecting changes are
  `BREAKING CHANGE:`.** Per-artifact versioning rules
  mean any change that alters methodology guarantees
  triggers a major-version bump. The discipline is
  what keeps the methodology coherent across PRs.
  Canonical: `../../CLAUDE.md` §4 + per-artifact
  "Versioning" sections in every phase, agent, and
  sub-skill.

These properties are **not negotiable**. A future
contributor's "improvement" that loosens any of them is
a `BREAKING CHANGE:` and should be reviewed against the
canonical statement before merge.

---

## 6. What `spp` is NOT

Out-of-scope concerns, mirroring the "What X does NOT
do" pattern from the phase docs.

- **Not an automated prompt optimizer** (DSPy / GEPA /
  APE). v1 is human-in-the-loop by design; the
  auditor's information isolation is what makes the
  methodology incompatible with score-driven
  optimization frameworks. See `../../DESIGN.md`
  §7.1 for the canonical non-integration argument.
- **Not a generation-task methodology.** v1 is
  classification-only. Generation tasks (instruction
  tuning, multi-turn conversation, tool-use prompts)
  are out of scope; the six-section prompt structure
  in `prompt-architect` does not apply to them.
- **Not a multilingual methodology.** v1 is
  English-only. Cross-lingual classification is v0.3
  roadmap.
- **Not a multi-judge subjective-metric methodology.**
  v1 enforces the metric-design independence rule (no
  LLM-as-judge for v1's metric); subjective metrics
  with multiple judges are v0.3 roadmap.
- **Not a mid-iteration resumption tool.** v1
  documents that iteration interruption requires
  restart of the iteration. Per `DESIGN.md` §7.1.
- **Not a cross-model summary tool.** v1 produces
  per-model REPORTs only; cross-model synthesis is
  v0.4 roadmap.
- **Not a prompt-injection-defense or jailbreak-
  resistance tool.** Out of scope at the methodology
  level; users adopting the prompt for adversarial
  settings handle those concerns separately.

`../../DESIGN.md` §7.1 (non-goals) is the canonical
list. The enumeration above is the at-a-glance version.

---

## Versioning

This entry point has a lighter versioning regime than the
methodology-affecting artifacts because it is mostly a
directory pointing at the canonical content.

### Methodology-affecting (= breaking)

- **Removing a phase, agent, or sub-skill from the
  artifact taxonomy.** v1's set is closed (4 phases,
  3 agents, 3 sub-skills); removing any of them is a
  methodology change.
- **Adding a phase, agent, or sub-skill to v1's set
  without updating `DESIGN.md`.** Same closure discipline
  applied at this entry-point level: a new artifact
  requires the structural-distinctness argument in
  `DESIGN.md` first.
- **Misrepresenting any of the load-bearing properties
  in §5.** §5 is a pointer to canonical statements; if
  the wording here drifts from the canonical wording in
  a way that changes meaning, that is breaking. This
  entry point can be wrong by omission; it should not be
  wrong by misstatement.
- **Adding routing logic that duplicates the canonical
  artifacts' decision criteria.** The entry point's job
  is to point at the canonical detail; embedding the
  detail here and letting it drift from the artifacts is
  the failure mode.

### Behavioral (= non-breaking)

- Better wording in any descriptive paragraph.
- Updating cross-references to track artifact renames
  or moves.
- Refining the §2 diagram for clarity (preserving the
  four-phase / six-gate structure).
- Adding a new "where to start" paragraph for a new
  audience (e.g., "for skill maintainers reviewing
  the project's structure").
- Better §6 wording for the non-goals enumeration.

When in doubt, treat the change as breaking — this entry
point is the front door; getting it wrong silently
misrepresents the methodology.

---

## Cross-references

**Phases.**
[`phases/spp-init.md`](phases/spp-init.md) ·
[`phases/spp-baseline.md`](phases/spp-baseline.md) ·
[`phases/spp-loop.md`](phases/spp-loop.md) ·
[`phases/spp-finalize.md`](phases/spp-finalize.md).

**Agents.**
[`agents/designer.md`](agents/designer.md) ·
[`agents/auditor.md`](agents/auditor.md) ·
[`agents/adversary.md`](agents/adversary.md).

**Sub-skills.**
[`sub-skills/metric-design/SKILL.md`](sub-skills/metric-design/SKILL.md) ·
[`sub-skills/baseline-quality/SKILL.md`](sub-skills/baseline-quality/SKILL.md) ·
[`sub-skills/prompt-architect/SKILL.md`](sub-skills/prompt-architect/SKILL.md).

**Templates.**
[`templates/plan.md.template`](templates/plan.md.template) ·
[`templates/loop_spec.md.template`](templates/loop_spec.md.template) ·
[`templates/prompt_v01.md.template`](templates/prompt_v01.md.template) ·
[`templates/REPORT.md.template`](templates/REPORT.md.template).

**Top-level project docs.**
[`../../README.md`](../../README.md) — the
user-facing methodology document.
[`../../DESIGN.md`](../../DESIGN.md) — design
rationale, failure modes, non-goals.
[`../../CLAUDE.md`](../../CLAUDE.md) — the
rulebook for how changes get made.
[`../../CHANGELOG.md`](../../CHANGELOG.md) —
project history.
