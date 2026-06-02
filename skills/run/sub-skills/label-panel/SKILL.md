# label-panel

A v0.7 sub-skill of `spp` that **synthesizes gold labels** for a dataset
whose label column is absent, using a **cross-family panel of five
score-blind judges** with human adjudication of any split. It runs
inside `/spp-baseline`, only when preprocess hands it a canonical
`baseline.csv` that has `id` and `input` but **no** label column: the
case preprocess explicitly refuses (it maps existing columns, it never
invents ground truth). label-panel is where label synthesis lives.

This is the seventh sub-skill in `spp` (peer to `schema-designer`,
`metric-design`, `baseline-quality`, `prompt-architect`,
`technique-advisor`, and `preprocess`). Like `preprocess` it both
*produces* an artifact (synthesized labels) and *guards a gate* (the
human adjudication of splits). The design contract it realizes is
`DESIGN.md` §7.1.8.

A note on artifact shape before reading further. `spp` has three kinds
of artifact: **phases** (orchestration and gate enforcement; the
user-facing `/`-commands), **agents** (judgment with structurally
isolated information access), and **sub-skills** like this one
(opinionated reference material that informs a decision and, when gated,
blocks the gate it defends). The five judges are subagents the protocol
spawns; the sub-skill is the doc that defines how they are spawned,
constrained, and aggregated.

This sub-skill ships **standalone in its first PR** — the directory and
its contract land before any phase doc invokes it. Integration into the
live `/spp-baseline` flow (which gate the adjudication uses, how the
phase runs the consensus script) is a later bucket of the v0.7 sequence;
see "Cross-references." The sub-skill is functional and citable in
design discussions from this PR forward; it is not yet wired into a
runnable phase.

---

## 1. Identity and scope

`label-panel` performs one job in three parts:

1. **Gate** on model family — refuse to run a same-family panel.
2. **Judge** each unlabeled row with five independent, score-blind
   subagents that each return one label from the fixed output space.
3. **Resolve** the votes — auto-freeze a confident consensus, escalate a
   split to the human, and record a complete audit trail.

**The framing.** Some classification tasks have a fixed label space but
a ground truth that itself requires *judgment* — tone, helpfulness,
coherence, style. v0.1.0's `metric-design` independence rule (§5) forbids
an LLM judge in the **scoring path**, which is the right rule: a judge
that scores the prompt under optimization can launder that prompt's
behavior into the metric. But that rule leaves a real gap — what if the
*baseline itself* has no labels and the labels require judgment? v0.7
fills the gap at the **baseline**, not the metric: the panel establishes
the gold labels **once**, they **freeze** into the sacred set, and every
later score is read off the frozen labels by the same mechanical metric
as before. No LLM ever enters the scoring path (invariant #13 intact).

**The risk it defends against** is a baseline whose labels secretly
encode the predictor's own bias. If the judges are the **same model
family** as the model being optimized, "consensus" is not independent
agreement — it is the predictor's bias reflected five times, and majority
vote then reduces *variance* without touching that bias. A prompt
optimized against such a baseline looks excellent and generalizes
nowhere. The defense is structural: the panel must be a **different
family** than the predictor, enforced by a hard gate, and the five
judges must vote **independently** so the consensus is genuine.

**In scope:**

- The **family gate**: refusing to run when the production model and the
  judge panel are the same family (§3.1).
- Spawning **five independent, score-blind judge subagents**, each given
  the row input, the fixed label space, and the labeling rubric, each
  returning one label plus a brief rationale (§3.3).
- **Consensus and escalation**: a ≥4-of-5 majority auto-accepts; any
  weaker agreement routes the row to human adjudication (§3.4).
- **Human adjudication** of escalated splits, and human **override** of
  any frozen label — including any test-set row — before the split runs
  (§3.5).
- A complete **`label_panel.json` audit trail**: every row, all five
  votes, the consensus margin, each rationale, and the
  accepted/escalated/overridden disposition (§3.6).

**Out of scope** (boundaries, not deferred work):

- **Judging in the scoring path.** The panel runs **once, before any
  split exists**, and produces frozen labels. It never scores a prompt,
  never runs inside the loop, and is never consulted by `eval.py`. The
  `metric-design` §5 ban on LLM judges in scoring is untouched (§5).
- **Overriding human ground truth.** When the dataset already has a label
  column, label-panel does **not** run — preprocess passes the existing
  labels through and the panel is never triggered. The panel synthesizes
  where labels are *absent*; it does not re-judge labels the human
  already provided.
- **Inventing or localizing the label space.** The judges choose among
  the *existing* fixed `OUTPUT_SCHEMA` enums (`schema-designer` §3.5).
  They do not add a label, split a label, or localize labels per
  language. The output space is given.
- **Same-family "diversity" panels.** Five differently-prompted judges
  of the same family as the predictor are **not** a cross-family panel
  and the gate rejects them. Prompt diversity reduces the panel's own
  variance; it does not substitute for family independence.
- **A new `/`-command.** label-panel is invoked inside the
  `/spp-baseline` labeling step, not a fifth phase (invariant #20).

The cross-skill rule that governs every choice here is the **LLM-judge
boundary** (`metric-design` §5): judges may *create* a frozen baseline;
they may never *score*. The full elaboration is in §5.

---

## 2. The decision the sub-skill helps make

The decision is **the gold label for each unlabeled row** — one value
from the fixed `OUTPUT_SCHEMA` output space, established once and frozen:

| Element | The decision |
|---|---|
| Eligibility | Does this project even need the panel? (Only when `baseline.csv` has `input` but no label column.) |
| Family | Is the judge panel a different family than the production model? (If not, stop — the gate blocks.) |
| Per-row label | Which fixed label does the row take? Decided by ≥4-of-5 judge agreement, or by the human when the panel splits. |
| Authority | Which labels did the human sign off on, and which auto-froze? Recorded so the human can override any of them. |

The output of the decision is the populated `label` column in
`baseline.csv` plus the `label_panel.json` audit trail. The sub-skill's
value is making label synthesis *independent, disclosed, and reviewable*
— so a reviewer can see exactly how every label was reached, which were
contested, and that none was laundered from the predictor's own family.

---

## 3. The protocol

### 3.1 The family gate (run first — hard block)

Before any judge is spawned, resolve the **production model's family**
(the model declared in `plan.md`) and the **judge family** (Claude Code
subagents — Anthropic). If they are the **same family**, stop: report
the conflict and do not run the panel. A same-family panel cannot give
the cross-family guarantee, and the methodology refuses to produce a
silently contaminated baseline rather than proceed.

- Family is resolved **deterministically**, never guessed: a static
  model→family map classifies the production model. When the model
  string is unrecognized, the gate requires an explicit `model_family`
  field in `plan.md` rather than defaulting — an unknown family never
  silently passes.
- The judges are Claude subagents, so in practice the gate **passes only
  when the production model is non-Claude** (OpenAI, Google, Meta, …) and
  **blocks when the production model is Anthropic-family**. This is a
  real limitation of a Claude-hosted panel, stated plainly rather than
  hidden: the honest options when the predictor is Claude are to label by
  hand or to bring a non-Claude judge panel, not to pretend five Claude
  judges are cross-family.

The gate is the first load-bearing lock; the consensus and escalation
that follow are only meaningful once it passes.

### 3.2 The labeling rubric

The judges decide against an explicit **labeling rubric** — the same
definition of each label that `metric-design` and `schema-designer`
settle for the task (`plan.md` §2), written as decision criteria a judge
can apply to a single row. The rubric is fixed before judging and is
identical for all five judges. An ambiguous rubric is the usual root
cause of a split (§3.4); the adjudication loop feeds rubric improvements
back here.

### 3.3 The five-judge panel (the score-blind contract)

Spawn **five judge subagents**. Each judge receives, and only receives:

- the row `input`,
- the fixed label space (the `OUTPUT_SCHEMA` enums),
- the labeling rubric (§3.2), and
- when the data is multilingual, the row's `language` tag (§3.7).

Each judge returns **exactly one label** from the fixed space plus a
**brief rationale**. Two properties are load-bearing:

- **Score-blind.** There are no model predictions, scores, or eval
  artifacts to see — this is baseline *creation*, before any prompt is
  scored — so score-blindness is structural. A judge is never given a
  candidate prompt's output, a score, or anything from the loop.
- **Independent.** Each judge votes without seeing the other judges'
  votes or rationales. Independence is what makes the majority
  meaningful: five judges that see each other's answers collapse to one
  correlated vote, and "4-of-5" stops measuring agreement. Spawn them so
  no judge's input contains another judge's output.

### 3.4 Consensus and escalation (4-of-5)

Aggregate the five votes:

- **≥4-of-5 agree on one label** (a 5-0 or 4-1 majority) → **auto-accept**
  that label and freeze it.
- **Anything weaker** (3-2, or a three-way split) → **escalate** the row
  to the human adjudication queue.

A split is **signal, not noise**: it means the rubric is underspecified
for that row. The escalation queue is therefore not just a labeling
backlog — it is the feedback that sharpens the rubric (§3.2). The 4-of-5
bar is deliberately stricter than a bare majority: a single dissent from
four agreeing judges still freezes, but a 3-2 split — real, balanced
disagreement — always reaches a human.

### 3.5 Human adjudication and override

The human is the authority on the sacred test set, operationalized as
**override power plus full visibility, not mandatory per-row sign-off**:

- **Mandatory sign-off is the escalation queue only.** The human resolves
  every escalated split before labels freeze, choosing the gold label
  (and, ideally, refining the rubric so similar rows stop splitting).
- **Auto-accepted labels freeze across train / dev / test alike** — the
  human is not required to confirm each one.
- **The human can override any frozen label**, including any test-set
  row, before the split runs, using the audit trail (§3.6). Authority is
  never ceded; it is simply not forced to be exercised row-by-row. The
  stricter alternative — manual confirmation of every test-set row
  regardless of consensus — was considered and set aside as
  disproportionate to the 4-of-5 bar (`DESIGN.md` §7.1.8).

### 3.6 Freeze and the audit trail

The panel writes a complete **`label_panel.json`** before any label is
treated as final: for every row, the five votes, the winning label, the
consensus margin (e.g. `5-0`, `4-1`, `3-2`), each judge's rationale, and
the disposition (`auto_accepted`, `escalated`, `human_resolved`,
`human_overridden`). The synthesized `label` column is written into
`baseline.csv` only after escalations are resolved. Because the audit
trail is complete, the freeze is reversible by human override right up
until the split is taken — after which the sacred-test-set guarantee
applies as usual (`DESIGN.md` §10).

### 3.7 Judge-language coupling

When the canonical data is multilingual (`DESIGN.md` §7.1.7), each judge
receives the row's `language` tag with the input, and the panel must be
competent in that language. Low-resource languages weaken the panel —
fewer confident consensuses, more rows routed to the human. This is a
**disclosed limitation**, visible in the audit trail (a language with
systematically low consensus margins is flagged for the human), not a
silent failure. label-panel adds no per-language judge *routing* and no
cross-lingual label transfer — both stay out of scope (`DESIGN.md`
§7.1.8).

---

## 4. Worked examples

None references a real source-project dataset (`DESIGN.md` §7.2); each is
a generic shape.

### Example 1: clean consensus, monolingual

Task: label support replies `{tone: Empathetic | Neutral | Curt}`; the
export has `id`, `reply_text`, no tone column. Production model is
GPT-class (gate passes — non-Claude). Five judges read each reply against
the tone rubric. Most rows land 5-0 or 4-1 and auto-freeze; the audit
trail records the margins. A handful of 3-2 rows escalate. The human
resolves them, sharpens the "Curt vs. Neutral" rubric line, and the
labels freeze.

### Example 2: a split drives a rubric fix

A batch of replies that are terse but polite split 3-2 between `Neutral`
and `Curt`. Rather than coin-flip, the human adjudicates: terse-but-polite
is `Neutral`. The rubric gains that clause, and on a re-judge those rows
reach 4-of-5. The split was the signal that the rubric was
underspecified, exactly as intended.

### Example 3: the family gate blocks

The same task, but the production model is Claude-family. The gate
resolves both families as Anthropic and **stops before spawning any
judge**: a Claude panel judging for a Claude predictor is same-family,
and "consensus" would launder the predictor's bias. The sub-skill reports
the conflict and the two honest options — label by hand, or supply a
non-Claude judge panel — and does not produce a baseline.

### Example 4: multilingual, low-resource tail

Reviews span `en`, `es`, and `sw` (Swahili). English and Spanish rows
reach 4-of-5 readily; the Swahili rows split far more often. The audit
trail flags `sw` as low-consensus, the escalation queue is heavier for
it, and the human adjudicates those rows directly. The limitation is
disclosed, not hidden behind a confident-looking but weak consensus.

---

## 5. The cross-skill constraint

The governing rule is the **LLM-judge boundary** (`metric-design` §5):
an LLM judge may never enter the **scoring path**, because a judge that
scores the prompt under optimization launders that prompt's behavior into
the metric. label-panel does not cross this line, and the distinction is
exact:

- **Where the judge sits.** label-panel judges at label **creation**,
  before any split or prompt exists. `metric-design` §5 forbids a judge
  at **scoring**, inside the loop, reading prompt outputs. Different
  place, different time, different artifact.
- **What the judge produces.** A **frozen baseline value**, fixed once
  and never recomputed. A scoring judge would produce a fresh verdict
  every iteration, coupled to the current prompt. The panel's output is
  inert from the moment it freezes.
- **What reads it.** `eval.py` reads the frozen labels with the same
  mechanical metric as any other baseline; it never calls the panel. No
  LLM is in the scoring path (invariant #13).

Three constraints are load-bearing and are `BREAKING` to weaken
(§"Versioning"):

- **Cross-family.** The panel must be a different family than the
  production model, enforced by the gate. Weakening it to "diverse
  prompts, same family" reintroduces the bias-laundering the rule exists
  to prevent.
- **Independence.** The five judges vote without seeing each other's
  votes. A panel that shares votes is one correlated vote wearing five
  hats, and the 4-of-5 bar becomes meaningless.
- **Creation, never scoring.** The panel freezes a baseline and exits
  before the loop. Any path that lets the panel run inside scoring, or
  re-judge labels per iteration, is the `metric-design` §5 violation.

---

## 6. What the sub-skill outputs

- **The populated `label` column in `data/baseline.csv`** — one fixed
  label per row, frozen after escalations resolve.
- **`label_panel.json`** in the task directory — the complete audit
  trail: per-row votes, winning label, consensus margin, rationales, and
  disposition.
- **A `plan.md` record** — that labels were synthesized by the panel,
  the production model's resolved family (so the gate decision is on
  record), the panel size and consensus rule, and the count of escalated
  rows the human adjudicated. Provenance, per the plan.md-as-contract
  rule (`DESIGN.md` §10).

The sub-skill does not write to any loop artifact, does not run after the
split, and does not touch `eval.json`, `results.json`, or any scoring
path.

---

## Pattern for subsequent sub-skills

`label-panel` follows the shared six-section structure (identity and
scope → the decision the sub-skill helps make → the protocol → worked
examples → the cross-skill constraint → output specification). Its
distinguishing traits are that it **spawns subagents** (the five judges)
and that it **guards two gates** — the family gate before judging and the
human adjudication of splits after — so its protocol section is the
longest. Revisions happen here and propagate by example.

---

## Versioning

Same rule as the predecessor sub-skills: changes that **alter
methodology guarantees** are flagged `BREAKING CHANGE:` in commit
messages and trigger a major-version bump per `CLAUDE.md` §4.

**Methodology-affecting (= breaking):**

- **Weakening the family gate** — allowing a same-family panel, defaulting
  an unrecognized model to a passing family, or letting the gate be
  skipped. The cross-family guarantee is the whole point.
- **Weakening judge independence** — letting judges see each other's
  votes or rationales before voting.
- **Moving the judge into scoring** — running the panel inside the loop,
  per iteration, or letting any scoring artifact read it. That is the
  `metric-design` §5 violation.
- **Re-judging human-provided labels** — running the panel when a label
  column already exists, or overriding human ground truth rather than
  synthesizing absent labels.
- **Inventing or localizing labels** — adding to, splitting, or
  per-language localizing the fixed `OUTPUT_SCHEMA` output space.
- **Removing human override of frozen labels**, or removing mandatory
  adjudication of splits.
- **Promoting `label-panel` to a fifth `/`-command** (invariant #20).

**Behavioral (= non-breaking):**

- Better worked-example phrasing or new examples on existing paths.
- Clearer rationale or audit-trail wording.
- Rubric-authoring guidance that does not change the consensus rule.
- Extending the model→family map with additional known models, as long as
  unknown models still require the explicit `plan.md` `model_family`
  field.

When in doubt, treat the change as breaking. The cost of a release-notes
paragraph is low; the cost of silently shipping a contaminated baseline
is high.

---

## Cross-references

- [`sub-skills/metric-design/SKILL.md`](../metric-design/SKILL.md) §5 —
  the LLM-judge boundary this sub-skill sits exactly against: judges may
  create a frozen baseline, never score.
- [`sub-skills/schema-designer/SKILL.md`](../schema-designer/SKILL.md)
  §3.5 — the fixed `OUTPUT_SCHEMA` output space and canonical-label
  policy the judges choose among.
- [`sub-skills/preprocess/SKILL.md`](../preprocess/SKILL.md) — the front
  gate that produces the canonical `baseline.csv` and, when it finds no
  label column, routes the project here instead of inventing labels.
- [`phases/spp-baseline.md`](../../phases/spp-baseline.md) — the phase
  that invokes `label-panel` in its labeling step and gates on the human
  adjudication (wired in a later v0.7 bucket).
- [`DESIGN.md`](../../../../DESIGN.md) §7.1.8 — the design contract:
  judge-panel-assisted baseline labeling, the family gate, and human
  authority as override-plus-visibility.
