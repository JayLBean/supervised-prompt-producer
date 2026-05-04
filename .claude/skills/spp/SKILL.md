---
name: spp
description: Supervised Prompt Producing — produces production-grade classification prompts through human-in-the-loop supervised prompt learning. Routes /spp-init, /spp-baseline, /spp-loop, and /spp-finalize.
---

# spp — Supervised Prompt Producing

This document is the **routing entry point** for `spp`. It
introduces what the skill is, names the artifact taxonomy
(four commands, three agents, three sub-skills, four
templates), points at where the canonical detail for each
component lives, and orients new users and Claude Code
sessions reading the skill for the first time.

The router is **introduction-and-index**, not new design.
The substantive work has happened in the eleven artifacts
this document points at; the router's job is to be the
front door so a reader knows which room to walk into. A
router that re-derives every command's pre-conditions in
its own words goes stale the moment any command's
pre-conditions change; this router resists that drift by
pointing at the canonical detail and trusting it.

The doc has its own six-section shape, established here
for the first time. It is not the agent/sub-skill six and
not the eight of the commands — a router-shaped artifact
needs router-shaped sections.

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
[`../../../DESIGN.md`](../../../DESIGN.md). For the
methodology's user-facing description:
[`../../../README.md`](../../../README.md). For the rules
about how changes get made: [`../../../CLAUDE.md`](../../../CLAUDE.md).

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

The four commands map cleanly to the methodology's four
phases. The six gates (G1–G6) interleave between
commands and within `/spp-loop`. The auditor and
adversary operate per iteration inside `/spp-loop` under
the information-isolation contract documented at
`agents/auditor.md` §2 and `agents/adversary.md` §6.

The README's `mermaid` diagram is the more detailed
view; this diagram is the at-a-glance version for
readers who just need to remember the shape.

---

## 3. The artifact taxonomy

Three artifact types in `spp`'s vocabulary, each with
distinct structural and operational roles.

### 3.1 Commands (4) — orchestration entry points the user invokes

| Command | Role | Outputs | Gates |
|---|---|---|---|
| [`/spp-init`](commands/spp-init.md) | Consultation; the designer agent walks the user through the task's contract. | `plan.md`, `loop_spec.md` | G1 |
| [`/spp-baseline`](commands/spp-baseline.md) | Labeling and splits; the baseline-quality sub-skill audits the labels. | `data/baseline.csv`, `data/splits.json` | G2, G3 |
| [`/spp-loop`](commands/spp-loop.md) | The optimization loop. Auditor every iteration; adversary optionally. | Per-iteration artifacts under `runs/<model>/run_NN/`; `SUCCESS.md` / `EARLY_STOP.md` / `FAILED.md`. | G4 + per-iteration auditor verdict gate |
| [`/spp-finalize`](commands/spp-finalize.md) | Sacred-test-set evaluation, REPORT generation, prompt freeze. | `test_eval.json`, `REPORT.md`, `PROMPT_FROZEN_v01.md` | G5, G6 |

The four commands map to the methodology's four phases.
Each command's doc carries the canonical pre-conditions,
execution flow, gate enforcement, outputs, failure
modes, and "what the command does NOT do." This router
does not duplicate that content; the command docs are
the single source of truth for how each command runs.

The v1 command set is **closed at four**. Adding a fifth
requires a methodology change per `DESIGN.md` §3.

### 3.2 Agents (3) — cognitive workers invoked by commands

Each agent's distinguishing property is **structurally
distinct information access**. Agents are invoked by
commands; the user does not invoke agents directly.

| Agent | Role | Information access | Invoked by |
|---|---|---|---|
| [`designer`](agents/designer.md) | Talks to the user during consultation. Produces `plan.md`. | Sees the repo, asks informed questions. No run-time scores exist yet at consultation time. | `/spp-init` |
| [`auditor`](agents/auditor.md) | Reviews proposed rule edits per iteration. Returns a per-edit verdict (`categorical` / `row-specific` / `unclear`). | Sees the prompt diff, prior discrepancy analysis, `plan.md` §2, and prior `auditor_review.md` files. **Never the new scores.** | `/spp-loop` |
| [`adversary`](agents/adversary.md) | Generates 2–3 synthetic adversarial rows per iteration when `ADVERSARY_FLAG = on`. Optional, opt-in. | Sees the current prompt, prior discrepancy, `plan.md` §2. Not the baseline, not the scores, not the test set. | `/spp-loop` (conditional) |

The auditor's information isolation is the **load-
bearing design property** that distinguishes `spp` from
automated optimizers. Canonical statement:
`agents/auditor.md` §2. The runner-level operational
enforcement: `commands/spp-loop.md` §4 step 11 and
`CLAUDE.md` §8.

The v1 agent set is **closed at three**. Adding a
fourth requires answering the structural-distinctness
question that `DESIGN.md` §4 establishes.

### 3.3 Sub-skills (3) — informational reference material

Sub-skills inform decisions; they are **not invoked as
conversational entities**. Read by the designer (during
consultation), by Claude during `/spp-loop`, or by users
wanting the rationale.

| Sub-skill | Role | Authority |
|---|---|---|
| [`metric-design`](sub-skills/metric-design/SKILL.md) | Guides metric selection during `/spp-init`. Enforces the independence rule (no LLM-as-judge for v1). | Informational. Output feeds `plan.md` §4. |
| [`baseline-quality`](sub-skills/baseline-quality/SKILL.md) | Adversarial review of baseline labels before splits. | **Verdict-enforcement.** Three-tier verdict (`ready` / `revise` / `not-ready`) gates `/spp-baseline` G2. |
| [`prompt-architect`](sub-skills/prompt-architect/SKILL.md) | Explains the six-section XML prompt template. | Informational. Structural discipline enforced via templates and the auditor. |

The v1 sub-skill set is **closed at three**. Each
sub-skill maps to a structurally distinct decision
(metric selection, baseline integrity, prompt
structure).

### 3.4 Templates (4) — task-specific instantiations

Not part of the agent / command / sub-skill taxonomy
proper, but listed here for completeness. Templates are
filled at consultation time and consumed by downstream
commands.

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
[`../../../README.md`](../../../README.md) first — the
methodology document, written for human readers
unfamiliar with the project. Then read
[`../../../DESIGN.md`](../../../DESIGN.md) if you want
the design rationale (why the methodology is shaped this
way, what failure modes it defends against, what it is
*not*). Then come back here for the artifact taxonomy.
Skip directly to invoking commands only after you have
understood what `spp` is doing methodologically;
mechanical execution without methodological
understanding produces prompts that look right and break
in production.

**For users with a classification task.** Run
`/spp-init <task-name>` from your project root. The
designer agent will consult you and produce `plan.md`
plus `loop_spec.md`. Approve at G1; proceed to
`/spp-baseline` for labeling and splits; then
`/spp-loop` for the optimization; then `/spp-finalize`
for the sacred-test-set evaluation and REPORT. Each
command's pre-conditions verify the prior command's
outputs are in place — you cannot skip phases. If a
pre-condition fails, the command exits with a specific
error; fix the named issue and re-invoke.

**For Claude Code reading this skill.** When a user
invokes one of the four commands, read the command's
doc at `commands/<name>.md` for the canonical execution
flow. **The router does not duplicate the commands'
pre-conditions, gate enforcement, or output
specifications.** That detail lives in the commands'
docs and is the single source of truth. The router
exists to introduce `spp` and to name where each
component's authoritative documentation lives. If the
router and a command appear to disagree, trust the
command — the router is index-shaped and may have
drifted; the commands are operational-shaped and are
the canonical source.

---

## 5. The methodology's load-bearing properties

The properties below distinguish `spp` from automated
optimizers and from naive prompt-engineering loops. Each
is one sentence here with a pointer to the canonical
statement; the router does not re-derive the property,
it points at where the property lives.

- **Auditor information isolation.** The auditor sees
  prompt diffs and prior discrepancy analysis but
  **never the new scores**. The design lock against
  optimization-driven row-specific patches.
  Canonical: [`agents/auditor.md`](agents/auditor.md)
  §2; `../../../DESIGN.md` §4.2;
  `../../../CLAUDE.md` §8.

- **Sacred test set.** The test partition is read
  exactly once, by `/spp-finalize`, after gates G1–G4
  have approved. The methodology's claim against
  baseline overfitting hinges on this discipline.
  Canonical:
  [`commands/spp-finalize.md`](commands/spp-finalize.md)
  §4 step 3; `../../../DESIGN.md` §10 glossary.

- **Verdict-enforced gates.** Sub-skill and agent
  verdicts gate command advancement via literal-string
  override-substring matching in `plan.md` §11. Three
  instances of the pattern: `/spp-baseline` G2,
  `agents/auditor.md`'s output shape, `/spp-loop`'s
  per-iteration gate. Canonical:
  [`commands/spp-baseline.md`](commands/spp-baseline.md)
  §5;
  [`commands/spp-loop.md`](commands/spp-loop.md) §5.

- **`plan.md` as contract.** All commands re-read
  `plan.md` fresh at invocation; it is the single
  source of truth for the task's contract. No command
  caches `plan.md`'s contents across invocations.
  Canonical: `../../../DESIGN.md` §10 glossary;
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
  [`commands/spp-init.md`](commands/spp-init.md) §5
  (the pattern source for G1; G2–G6 inherit).

- **Methodology-affecting changes are
  `BREAKING CHANGE:`.** Per-artifact versioning rules
  mean any change that alters methodology guarantees
  triggers a major-version bump. The discipline is
  what keeps the methodology coherent across PRs.
  Canonical: `../../../CLAUDE.md` §4 + per-artifact
  "Versioning" sections in every command, agent, and
  sub-skill.

These properties are **not negotiable**. A future
contributor's "improvement" that loosens any of them is
a `BREAKING CHANGE:` and should be reviewed against the
canonical statement before merge.

---

## 6. What `spp` is NOT

Out-of-scope concerns, mirroring the "What X does NOT
do" pattern from the commands.

- **Not an automated prompt optimizer** (DSPy / GEPA /
  APE). v1 is human-in-the-loop by design; the
  auditor's information isolation is what makes the
  methodology incompatible with score-driven
  optimization frameworks. See `../../../DESIGN.md`
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

`../../../DESIGN.md` §7.1 (non-goals) is the canonical
list. The enumeration above is the at-a-glance version.

---

## Versioning

The router has a lighter versioning regime than the
methodology-affecting artifacts because the router is
mostly a directory pointing at the canonical content.

### Methodology-affecting (= breaking)

- **Removing a command, agent, or sub-skill from the
  artifact taxonomy.** v1's set is closed (4 commands,
  3 agents, 3 sub-skills); removing any of them is a
  methodology change.
- **Adding a command, agent, or sub-skill to v1's set
  without updating `DESIGN.md`.** Same closure
  discipline applied at the router level: a new
  artifact requires the structural-distinctness
  argument in `DESIGN.md` first.
- **Misrepresenting any of the load-bearing
  properties in §5.** The router's §5 is a pointer to
  canonical statements; if the router's wording drifts
  from the canonical wording in a way that changes
  meaning, that is breaking. The router can be wrong
  by omission; it should not be wrong by misstatement.
- **Adding routing logic that duplicates the canonical
  artifacts' decision criteria.** The router's job is
  to point at the canonical detail; embedding the
  detail in the router and letting it drift from the
  artifacts is the failure mode.

### Behavioral (= non-breaking)

- Better wording in any descriptive paragraph.
- Updating cross-references to track artifact renames
  or moves.
- Refining the §2 diagram for clarity (preserving the
  four-phase / four-command / six-gate structure).
- Adding a new "where to start" paragraph for a new
  audience (e.g., "for skill maintainers reviewing
  the project's structure").
- Better §6 wording for the non-goals enumeration.

When in doubt, treat the change as breaking — the
router is the front door; getting it wrong silently
misrepresents the methodology.

---

## Cross-references

**Commands.**
[`commands/spp-init.md`](commands/spp-init.md) ·
[`commands/spp-baseline.md`](commands/spp-baseline.md) ·
[`commands/spp-loop.md`](commands/spp-loop.md) ·
[`commands/spp-finalize.md`](commands/spp-finalize.md).

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
[`../../../README.md`](../../../README.md) — the
user-facing methodology document.
[`../../../DESIGN.md`](../../../DESIGN.md) — design
rationale, failure modes, non-goals.
[`../../../CLAUDE.md`](../../../CLAUDE.md) — the
rulebook for how changes get made.
[`../../../CHANGELOG.md`](../../../CHANGELOG.md) —
project history.
