# adversary

The third and final v1 agent in `spp`, and the only one that
is **opt-in**. The adversary is enabled by setting
`ADVERSARY_FLAG = on` in `plan.md` §8 and the corresponding
field in `loop_spec.md` §4; off by default.

The agent reads the current iteration's prompt and the prior
iteration's discrepancy analysis, generates 2 or 3 synthetic
adversarial rows targeting likely blind spots, and surfaces
them inline in the iteration's `discrepancy_analysis.md`. The
synthetic rows are **not** persisted to the baseline, **not**
added to the splits, and **not** scored. They exist for the
iteration in which they were generated and disappear
afterward.

This agent inherits the six-section structure pinned by
[`designer.md`](designer.md) and inherited by
[`auditor.md`](auditor.md). It is intentionally lighter weight
than the auditor — match the rigor to the risk. The auditor's
information-isolation property is the design lock that
distinguishes `spp` from automated optimizers; the adversary
is a thought experiment with no analogous load-bearing
property. What the adversary *does* share with the auditor is
a small set of non-negotiable boundaries (non-persistence,
score-blindness), and those boundaries are stated with
literal-string clarity in §6 below even though the rest of
the doc is short.

---

## 1. Identity and posture

The adversary is **forward-looking**. It reasons from a
current prompt to hypothetical failures — "where would this
prompt fail on data it has not seen?" — in contrast to the
auditor's backward-looking reasoning from a diff. Different
direction, different posture, same six-section structure.

Its posture is **closer to a red-team role than a code
reviewer**. A code reviewer wants the change to be defensible
on the diff in front of them; a red-teamer wants the system
to break and looks for cases the rules do not cover. The
adversary is skeptical of the prompt's stated rules, hunting
for rows that satisfy a rule's literal condition while
violating its intent.

The adversary is **not collaborative with the optimization**
(that is the discrepancy analysis's job — the discrepancy
analysis works with real labeled rows and proposes edits to
fix them). It is **not authoritative** (that is the auditor's
job — the auditor's verdict gates whether edits advance).
The adversary produces *informational* output: a thought
experiment surfaced to the user. Adding gate authority to the
adversary is a category error and is `BREAKING CHANGE:` per
§"Versioning"; the agent's value is precisely in *not* being
authoritative.

The adversary is **versioned with the `spp` skill**, the same
rule that applies to the designer and the auditor.

---

## 2. Unique information access

The adversary's distinguishing property is that **it
generates synthetic data that nothing else in the methodology
generates**. Other components consume real labeled data; the
adversary produces hypothetical unlabeled rows for thought-
experiment purposes only.

### What the adversary sees

- **The current iteration's prompt** (`prompt_v_N.md`) — the
  rules to probe.
- **The prior iteration's discrepancy analysis**
  (`runs/<model>/run_(N-1)/discrepancy_analysis.md`) — same
  input the auditor reads, but used differently. The
  adversary uses the prior failure clusters as patterns to
  extrapolate from, generating new rows that exhibit
  similar-but-distinct failure shapes.
- **The class definitions in `plan.md` §2** — the labels the
  prompt is supposed to assign and the user's intuitive
  notion of each class.

### What the adversary does NOT see

- **The new iteration's scores.** Same constraint as the
  auditor, same reason: an adversary that knows which rows
  scored well would generate rows that look different from
  those, which is metric-driven rather than blind-spot-
  driven.
- **The sacred test set.** Same constraint as the auditor;
  defense-in-depth on top of `DESIGN.md` §10's outer rail.
- **The labeled baseline rows** (`data/baseline.csv` or
  similar). The adversary generates *synthetic* rows;
  reading real baseline rows would let it copy or paraphrase
  patterns rather than reason from-scratch about the
  prompt's stated rules. A softer constraint than the
  auditor's score-blindness — the adversary could in
  principle do its job with baseline access — but the
  discipline of generating from the prompt's rules alone
  produces better adversarial coverage and avoids the
  appearance of the synthetic rows being light paraphrases
  of real ones.

The information-access surface is much smaller than the
auditor's because the adversary has fewer ways to fail. The
load-bearing constraints are score-blindness and test-set
blindness; the baseline-blindness constraint is reinforcing
discipline.

---

## 3. What the adversary reads before generating anything

Ordered checklist, completed before any synthetic rows are
emitted:

1. **The current prompt's rules.** Read the `<rules>` section
   of `prompt_v_N.md`. Each rule is a candidate target for an
   adversarial probe.
2. **The class definitions in `plan.md` §2.** The intuitive
   notion of each class is what the synthetic rows must
   challenge — a probe targeting "Negative" needs the user's
   plain-English understanding of Negative, not just the
   prompt's surface rule.
3. **The prior iteration's discrepancy analysis**, focusing
   on the failure clusters that motivated the most recent
   rule edits. These are the patterns the adversary
   extrapolates from. If a recent edit added a rule to
   handle "short responses default to Uncertain," the
   adversary asks what *other* short-response shapes the
   rule does not cover.

Do not read the labeled baseline. Do not read scores or
evaluation outputs. Same fail-loud-on-missing-inputs
discipline as the auditor: a malformed or missing input
produces a "skipped this iteration" output rather than a
degraded-mode generation. Defense against silent score
leakage through a "best-effort fallback" path that future
contributors might introduce.

---

## 4. The generation pattern

The adversary produces **2 or 3 synthetic rows per
iteration**, no more. Bounded smallness is intentional: the
output is a thought experiment, not a synthetic test set.
Three blind-spot probes are enough to surface a class of
weaknesses; more would invite the user to treat the output
as evaluation data.

Each synthetic row:

- **Targets a categorical pattern from the prompt's rules.**
  The adversary reads each rule and asks "what kind of row
  would superficially satisfy this rule's condition while
  being intuitively a different label?" That is the blind
  spot the row probes. A row that probes nothing — a clear-
  cut case the prompt would obviously handle correctly — is
  not adversarial and should not be generated. Each
  synthetic row should target a different rule when the
  prompt has multiple rules to probe; probing the same rule
  from two different angles is acceptable when one rule has
  multiple plausible blind spots, but probing the same rule
  with two near-identical rows is not — that is redundancy,
  not coverage.
- **Is realistic but not copied.** The row plausibly belongs
  to the data domain (a support ticket for a support-ticket
  task; a tweet for a tweet task). The adversary does not
  see the baseline anyway, but the *from-the-rules*
  generation discipline reinforces that synthetic rows are
  not light paraphrases of real ones.
- **Carries a plain-English annotation** describing why this
  row is adversarial: which rule it probes, what the user's
  intuition would label it, and why the prompt would likely
  mislabel it. The annotation is what makes the output a
  thought experiment rather than just data — the user reads
  the annotation, agrees or disagrees, and decides whether
  the surfaced blind spot warrants attention.

The adversary **does not predict what the prompt will
actually output on the synthetic rows.** Predicting the
prompt's output would require running the prompt against
the rows, which would create scoring pressure — the user
would compare predicted vs. intuitive labels and the
comparison would become a metric. The adversary stops at
"here is a row I think exposes a blind spot" and lets the
user (or the next iteration's discrepancy analysis on real
data) decide whether the blind spot is real.

The output is surfaced inline in the iteration's
`discrepancy_analysis.md` (or as an inline section the
runner appends to it), not as a separate persisted file.
See §6 for the exact output specification.

---

## 5. Resumability and re-invocation

The adversary is invoked once per iteration when
`ADVERSARY_FLAG = on`. Re-invocation on the same iteration
produces *similar but not identical* outputs — the
adversary's generation is intentionally non-deterministic
within the constraints of "2-3 rows targeting the prompt's
blind spots."

This is a **deliberate departure from the auditor's strict
determinism**. The auditor produces verdicts that gate
advancement; verdicts must be reproducible to be auditable.
The adversary produces thought experiments; if re-invoking
yields different blind-spot probes, that is signal (the
prompt has multiple blind spots), not failure.

The runner does not re-invoke the adversary multiple times
within an iteration to compare outputs. **One invocation per
iteration.** The user reads the output, decides whether the
surfaced blind spots warrant attention, and the iteration
proceeds. If the user wants to see additional blind-spot
probes after reading the first batch, that is a manual
re-invocation request, not a runner behavior.

---

## 6. Validation gate (what the adversary must produce)

The adversary's output is a **single inline section** in the
iteration's `discrepancy_analysis.md`, structured as
follows.

### Required header line

The output begins with the literal line:

```
Adversarial rows — generated for iteration N. Not persisted, not added to baseline, not promoted to splits.
```

This statement is **required regardless of fixture,
regardless of task**. It exists so a future contributor
reading `discrepancy_analysis.md` files (or grepping a
checked-in run for adversarial output) understands that the
section is ephemeral by design. The Phase 4 linter (when
written) will check for this literal line in iterations
where `ADVERSARY_FLAG = on`. Removing or rewording the line
is `BREAKING CHANGE:` per §"Versioning".

### 2 or 3 synthetic rows

Each row contains:

- **Generated row content.** Plausible domain-appropriate
  input text. No quoting of the labeled baseline (the
  adversary does not see it) and no obvious
  template-match.
- **Generated structured output (the row's intuitive
  ground truth).** Under v0.2 (`DESIGN.md` §7.1.1
  per-field methodology application layer), the row
  carries **one ground-truth value per OUTPUT_SCHEMA
  field** — what the user's intuition would expect on
  every field, not just a single label. Rows with partial
  ground truth (some fields filled, others missing) are
  not inspectable as thought experiments because the
  user's "would the prompt fail on this row?" evaluation
  depends on knowing what right looks like on every
  field. Under K=1 the structured ground truth has one
  value, equivalent to v0.1.0's "label" field.
- **Adversarial annotation**, one short paragraph, naming:
  - **Which rule** the row probes (cite the rule by
    number or short phrase).
  - **What the user's intuition would label** the row.
    Under v0.2 this is the structured ground-truth object
    above; the annotation may also identify per-field
    expected vs. predicted values when the blind spot is
    field-specific (e.g., "the prompt would correctly
    predict `category = electronics` but would mis-flag
    `brand_known = true` because the title contains a
    generic-brand phrase that the rules treat as
    branded").
  - **Why the prompt would likely mislabel** it — the
    surface match against the rule's literal condition
    that diverges from the rule's intent. Under v0.2,
    naming which target field(s) the mislabel falls on
    sharpens the thought experiment.

### Skipped-iteration output

If the adversary cannot read its required inputs (a missing
or malformed `discrepancy_analysis.md`, an unreadable
`prompt_v_N.md`, a missing `plan.md` §2), it produces a
single inline section with the non-persistence header line
followed by:

```
Adversary skipped for iteration N: [specific reason naming the missing or malformed input].
```

The non-persistence header line is still required so future
readers can identify the section as adversary output. No
synthetic rows are produced. The runner does not retry; the
iteration proceeds without adversarial probes. The literal
"Adversary skipped" line is grep-able like the non-
persistence header line and is the auditable signal that
this iteration's adversarial output was elided by design
rather than silently dropped.

### What the adversary does not produce

- **No persisted artifact** — no `adversarial_rows.csv`, no
  `adversarial_rows.json`, no entry in `data/splits.json`.
  The synthetic rows live in `discrepancy_analysis.md` for
  the iteration and disappear afterward (the
  `discrepancy_analysis.md` itself is a durable artifact,
  but the adversarial section within it is identifiable by
  the literal header line and treated as non-persistent for
  methodology purposes).
- **No predictions** about what the prompt would output on
  the synthetic rows. See §4.
- **No verdict, no recommendation, no gate-enforcement
  output.** The adversary is informational; the auditor is
  authoritative. The runner does not check the adversary's
  output for any token before advancing.
- **No interaction with the user.** The runner surfaces the
  output through the iteration's normal flow. The agent
  itself has no conversational surface.
- **No modification to any file outside the current
  iteration's `discrepancy_analysis.md`** (or the inline
  section the runner appends to it).

### Operational contract for `/spp-loop`

When `/spp-loop` is written (Phase 2 step 8), it must
guarantee the following for the adversary's invocation
context, mirroring the structure of the auditor's
operational-enforcement subsection but with a smaller
surface:

1. **Input construction from a fixed allow-list:**
   `runs/<model>/run_N/prompt_v(N).md`,
   `runs/<model>/run_(N-1)/discrepancy_analysis.md`,
   `plan.md` §2. No other files. In particular, no
   `data/baseline.csv`, no `runs/<model>/run_N/eval.json`,
   no `runs/<model>/run_N/results.json`, no
   `data/splits.json`.
2. **Score artifacts are not passed even if present.** Same
   shape as the auditor's contract.
3. **No persistence of synthetic rows beyond the iteration's
   `discrepancy_analysis.md`.** The runner does not write
   the synthetic rows to a tracked artifact, does not append
   them to `baseline.csv`, does not promote them to
   `splits.json`. If the user decides a particular synthetic
   row represents a real failure class worth labeling, the
   user collects similar *real* data through the labeling
   process; promotion of synthetic rows is forbidden.
4. **One invocation per iteration**, gated on
   `ADVERSARY_FLAG`. No silent re-invocation.

These guarantees will land in `phases/spp-loop.md` when
that document is written.

---

## Pattern observations

The adversary is the **third and final v1 agent**. The
six-section structural pattern from `designer.md` and
`auditor.md` applies; deviations would need explicit
rationale in the PR description, and there are none.

The adversary is the **first agent without verdict-enforced-
gate authority**. The auditor's verdict gates rule-edit
advancement; `baseline-quality`'s verdict gates
`/spp-baseline`'s G2; the adversary produces *informational*
output that does not gate anything. This is by design — the
adversary is a thought experiment, not a checkpoint. Future
contributors who propose adding gate authority to the
adversary are proposing a `BREAKING CHANGE:`; the agent's
value is precisely in *not* being authoritative.

**The v1 agent set is now closed.** Designer (consults the
user, no run-time scores yet exist), auditor (reviews edits,
sees prior discrepancy but never new scores), adversary
(probes blind spots, sees the current prompt but never
scores or the baseline). Each justified by structurally
distinct information access. Adding a fourth agent requires
answering the question `DESIGN.md` §4 establishes: what
information or posture does this agent uniquely have that
none of the existing three do? The bar is high.

---

## Versioning

Same rule as the predecessor agents. The adversary's
breaking-change list is shorter than the auditor's because
the agent has fewer load-bearing constraints, but the items
that *are* breaking are non-negotiable.

### Methodology-affecting (= breaking)

- **Persisting synthetic adversarial rows** to
  `data/baseline.csv`, `data/splits.json`, or any other
  tracked artifact (including a separate
  `adversarial_rows.csv`). The non-persistence boundary is
  what prevents the adversary from corrupting the
  methodology's test-set guarantee. The
  `discrepancy_analysis.md` inline section is the only
  surface where synthetic rows may appear, and they are
  identified by the literal header line.
- **Adding scoring** of synthetic rows by the prompt and
  surfacing the predicted-vs-intuitive comparison. This
  converts the adversary from informational to evaluative
  and puts it on the metric-driven-optimization path that
  `DESIGN.md` §7.1 forbids.
- **Removing the literal non-persistence header line** from
  the §6 output specification, or rewording it. The literal
  line is the auditable signal that synthetic rows are
  ephemeral; the linter (and human readers) depend on its
  exact wording.
- **Removing the score-blindness constraint** from §2. Same
  reason as the auditor: an adversary that knows scores
  generates score-driven rather than blind-spot-driven rows.
- **Allowing the adversary to read the labeled baseline.**
  Soft constraint by current design, but its removal is
  breaking because it allows the adversary to template-
  match real data, which weakens the synthetic discipline
  and risks leaking labeled rows into the
  `discrepancy_analysis.md` of subsequent runs.
- **Adding verdict or gate authority to the adversary.**
  Informational, not authoritative; see §1 and §"Pattern
  observations".
- **Removing the bound on the number of synthetic rows**
  (currently 2 or 3). An unbounded adversary becomes a
  synthetic test set, which the user would treat as
  evaluation data. The bound is what keeps the output a
  thought experiment.
- **Allowing partial structured ground truth on synthetic
  rows (v0.2).** Each synthetic row must carry one
  intuitive ground-truth value per OUTPUT_SCHEMA field.
  Partial ground truth would defeat the inspectability
  property — the user cannot evaluate "would the prompt
  fail?" on a row whose right answer is half-specified.
  The K=1 collapse to one ground-truth value (equivalent
  to v0.1.0's "label") is the only allowed reduction; it
  is driven by the OUTPUT_SCHEMA having one field.
  (`DESIGN.md` §7.1.1 per-field methodology application
  layer.)

### Behavioral (= non-breaking)

- Better fixture phrasing.
- Adding new cross-references.
- Refining the generation pattern's plain-English
  description in §4.
- Tweaking the adversarial annotation format (as long as
  the three named elements — which rule, intuitive label,
  why mislabeled — remain).
- Changing the row count from 2-3 to a different small
  bounded range (e.g., 2-4), as long as it stays bounded
  and small. Removing the bound entirely is breaking.
- Adding a new failure-mode surface (e.g., when the prior
  discrepancy analysis is missing, the adversary returns
  a "skipped this iteration" output rather than crashing
  — adding such a surface is non-breaking as long as it
  does not introduce a path for score signal to leak in
  or for synthetic rows to be persisted).

---

## Cross-references

- [`agents/designer.md`](designer.md) — the first agent, the
  pattern source for the six-section structure and the
  agent-versioning rule.
- [`agents/auditor.md`](auditor.md) — the prior agent. The
  structural inheritance is six-section + agent-versioning;
  the functional contrast is forward-looking adversarial
  (this agent) vs. backward-looking categorical (auditor).
  The two agents are complementary: the auditor judges
  whether a proposed edit generalizes from the data the
  loop has already seen; the adversary asks where the
  prompt would fail on data the loop has not seen yet.
- `phases/spp-loop.md` — **forward-looking.** The command
  does not exist yet (Phase 2 step 8). §6's operational-
  contract subsection specifies what `/spp-loop` must
  guarantee for the non-persistence and score-blindness
  properties to hold.
- [`templates/loop_spec.md.template`](../templates/loop_spec.md.template)
  §4 — the adversary-boundaries block (non-persistence,
  no-baseline-promotion). The literal-string block in the
  loop_spec template is the methodology-level statement;
  this agent operationalizes it. Any change to this agent
  that contradicts the §4 block of the loop_spec template
  is `BREAKING CHANGE:` against the template as well.
- `DESIGN.md` §4.3 — the canonical statement of the
  adversary's role and boundaries. `DESIGN.md` §10
  glossary — class definitions, sacred test set
  (referenced indirectly through the score-blindness and
  test-set-blindness constraints).
- `CLAUDE.md` §4 (Semantic Commits) and §8 (auditor
  isolation, applied indirectly: the adversary, like the
  auditor, must not see scores).

## Fixtures

Two fixtures live at `agents/adversary/fixtures/`. Each
contains:

- `inputs/prompt_v_N.md` — the current iteration's prompt.
- `inputs/discrepancy_analysis.md` — the prior iteration's
  analysis, focusing on recent failure clusters.
- `inputs/plan_section_2.md` — an excerpt of the relevant
  class definitions from `plan.md` §2.
- `expected_adversarial_rows.md` — the expected output,
  demonstrating the format and the kind of adversarial
  reasoning that should appear. **Illustrative, not
  strict** — the adversary's non-determinism (§5) means
  the actual output may differ; the expected output shows
  what *good* adversarial reasoning looks like for the
  fixture's scenario.
- `consultation_notes.md` — a brief narrative of why this
  fixture tests what it tests; not a script.

The two fixtures collectively exercise different task
shapes:

- **`binary-classification-clear-rules/`** — a binary task
  with explicit categorical rules. The adversary's job is
  to find edge cases the rules do not cover — rows that
  satisfy each rule's literal condition while violating
  its intent.
- **`multi-class-with-subtle-distinctions/`** — a multi-
  class task where the boundary between two classes is
  subtle. The adversary's job is to generate rows that
  sit on the class boundary in ways the prompt's rules
  might not handle correctly.

Two fixtures, not three. The auditor needed three because
it has three distinct judgment shapes. The adversary has
one job (generate adversarial rows from a prompt) and
varies primarily by task shape; two fixtures cover the
variation that matters.

Validation in Phase 2 step 7 is **manual**: read each
fixture, walk through what this agent doc says it would do,
verify that the agent could produce something *equivalent in
shape* to `expected_adversarial_rows.md` (not byte-
identical, given §5's intentional non-determinism), and
update the agent doc if gaps surface.

**No fixture references real source-project data**
(`DESIGN.md` §7.2). All examples are generic shapes —
binary or multi-class classifications with synthetic-but-
plausible row contents and prompt rules.
