# metric-design

A sub-skill of `spp` that helps select the right classification
metric for a given task and document why. Read by the **designer
agent** during `/spp-init` consultation (`designer.md` §5.2 +
§7) and by users curious about the rationale behind their
plan's `METRIC_NAME` choice.

This is the first sub-skill in `spp`. The six-section structure
established here — identity → decision → decision tree →
worked examples → cross-skill constraint → output spec — is
what `prompt-architect` and `baseline-quality` will reuse.

A note on artifact shape before reading further. `spp` has
three: **commands** (orchestration, gate enforcement;
user-facing entry points), **agents** (judgment with
structurally distinct information access; invoked by commands),
and **sub-skills** like this one (opinionated reference
material that informs decisions). A sub-skill is not a chat
and not invoked as a conversational entity. A user reading
this doc should come away knowing how to make the decision
themselves; if follow-up consultation is needed, the
**designer** agent does it (and reads this doc to know which
follow-up to ask).

---

## 1. Identity and scope

`metric-design` makes one specific decision well: given a
classification task's economics, which metric should the
optimization loop drive against, and what rationale should
accompany the choice in `plan.md` §4?

**In scope:**

- Binary classification metrics (F1, balanced accuracy,
  precision-at-recall, recall-at-precision).
- Multi-class classification metrics (macro-F1, balanced
  accuracy generalized to N classes).
- Custom metrics that are explicitly model-independent and
  combine the above with documented weights.

**Out of scope** (v1 non-goals per `DESIGN.md` §7.1):

- Multi-judge subjective metrics where ground truth itself
  requires LLM judgment (style, tone, helpfulness). v0.3
  roadmap.
- Generation-task metrics (BLEU, ROUGE, perplexity-style
  scores). v0.3 roadmap or separate methodology.
- RAG metrics (faithfulness, answer relevance). v0.2+
  roadmap.
- Agentic-task metrics. Out of scope.
- LLM-as-judge metrics where the judge is the same model
  family as the production target. Forbidden in v1 by the
  independence rule (§5 below).
- Metrics computed against unlabeled data (rubric scores
  without ground truth). The methodology has no anchor
  without labels.

**The cross-skill rule** that governs every choice in this
doc: the metric must be computable independently of the
model being optimized (`DESIGN.md` §5). No GPT-4 judging
GPT-4 prompts. The full elaboration of this rule is in §5
below; it is the constraint every option in §3's decision
tree satisfies, and the constraint that custom metrics must
prove they satisfy.

---

## 2. The decision the sub-skill helps make

Given the task's production economics — what the prompt's
output drives, what failure looks like in production, what
asymmetry exists between false positives and false negatives —
**which `METRIC_NAME` should `plan.md` §4 record, and what
should the accompanying `METRIC_RATIONALE` say?**

The output of consulting this sub-skill is three fields, all
of which go into `plan.md` §4 (`plan.md.template`):

- **`METRIC_NAME`**: one of `F1`, `balanced_accuracy`,
  `macro_F1`, `precision_at_recall`, `recall_at_precision`,
  or `custom`. These are the values
  `plan.md.template` validation rule 4 accepts.
- **`METRIC_RATIONALE`**: a one-paragraph explanation that
  names which decision-tree branch (§3 below) was taken and
  why — derived from the task economics in `plan.md` §3.
- **`METRIC_INDEPENDENCE_NOTE`**: a one- or two-sentence
  confirmation that the chosen metric is computable
  independently of the production model (§5 below). This is
  the field that `plan.md.template` validation rule 5
  enforces; without it, the plan does not pass G1.

The designer fills these three fields; the sub-skill makes
sure they are correct.

---

## 3. The decision tree

The path from task economics to `METRIC_NAME` is a small set
of branches. Walk it from the top; each question's answer
either narrows further or commits to a metric.

**Question 1: How many classes does the task have?**

- **Two (binary).** Continue to Question 2.
- **More than two (multi-class).** Continue to Question 5.

**Question 2 (binary): What's the asymmetry between false
positives and false negatives?**

- **Roughly equal cost.** F1 is the right choice; continue
  to Question 3 to confirm class balance.
- **One side is catastrophic, the other is recoverable.**
  Continue to Question 4 — you want a constrained-floor
  metric, not F1.
- **Both sides matter but neither is catastrophic.**
  F1 with a documented precision-leaning or recall-leaning
  posture in the rationale is honest. Continue to Question 3.

**Question 3 (binary, F1 path): How balanced are the
classes?**

- **Mild imbalance** (positive class 20–80% of rows). F1.
  Mild imbalance is what F1 was designed for; the metric
  rewards both recall and precision on the positive class
  without being dominated by majority-class behavior.
- **Severe imbalance** (positive class <10% or >90%).
  F1 still works but is noisy at small N. Consider
  `balanced_accuracy` instead, especially if the user
  cares about per-class behavior rather than positive-class
  performance specifically. The rationale should name the
  imbalance and the noise concern.
- **Roughly balanced** (45–55% split). F1 if the positive
  class is operationally meaningful (e.g., `Billing` vs
  `Not Billing` — Billing is the actionable class);
  `balanced_accuracy` if the two classes are
  operationally symmetric and the task is conceptually
  "which bucket does this go in?" rather than "is this
  the relevant thing?"

**Question 4 (binary, asymmetric-cost path): which side is
catastrophic?**

- **False negatives are catastrophic** (missing a positive
  is the failure mode you cannot tolerate — e.g., a fraud
  flag that misses fraud, a safety classifier that misses
  unsafe content). `precision_at_recall` with an explicit
  recall floor (e.g., recall ≥ 0.95). The rationale must
  state the recall floor as a hard constraint.
- **False positives are catastrophic** (alerting on
  something that's not there is the failure mode you cannot
  tolerate — e.g., a spam filter that drops legitimate
  email, a moderation flag that suppresses benign content).
  `recall_at_precision` with an explicit precision floor.
  The rationale must state the precision floor as a hard
  constraint.

**Question 5 (multi-class): how should classes be weighted
relative to each other?**

- **Each class matters roughly equally**, regardless of
  prevalence. `macro_F1` (per-class F1 averaged with equal
  weight). The right choice when the task is "categorize
  this into one of N buckets" and no bucket is more
  important than another. Optionally specify a per-class
  F1 floor (e.g., "no individual class F1 below 0.65")
  in the rationale to prevent a class-balanced metric from
  masking a single failed class.
- **Some classes matter more than others** (e.g., one
  high-stakes class out of four, the others routine).
  `custom` — usually a weighted combination of macro-F1
  and per-class F1 floors. The rationale must define the
  weights and justify them from the task economics.
- **Class prevalence varies wildly and you want each
  class's recall to count equally** (rather than each
  class's F1). `balanced_accuracy` generalized to N
  classes (per-class recall averaged). Rare in practice
  but useful when the production decision rule is
  recall-driven across all classes.

**Question 6 (any path): does the task economics demand a
metric not covered above?**

- **Yes.** `custom` with an inline definition. The
  rationale must:
  1. Define the metric formula in plain English.
  2. State which model-independent inputs it uses (ground-
     truth labels, prediction labels, confidences if
     calibrated, etc.).
  3. Confirm satisfaction of the §5 independence rule.
  4. Explain why no documented option works.

  `custom` is rare. Most tasks fit one of the documented
  options; reaching for `custom` should prompt the
  designer to ask whether the task economics have been
  articulated correctly first.

**Decision-tree summary table:**

| Branch | Metric | Required in rationale |
|---|---|---|
| Binary, balanced costs, mild imbalance | `F1` | Class balance + cost-symmetry note |
| Binary, balanced costs, severe imbalance | `balanced_accuracy` | Imbalance + noise concern |
| Binary, FN catastrophic | `precision_at_recall` | Recall floor (e.g., 0.95) |
| Binary, FP catastrophic | `recall_at_precision` | Precision floor (e.g., 0.80) |
| Multi-class, equal class weight | `macro_F1` | Optional per-class F1 floor |
| Multi-class, weighted | `custom` | Weights + justification |
| Multi-class, recall-equal | `balanced_accuracy` | Per-class recall rationale |
| None of the above | `custom` | Formula + independence proof |

---

## 4. Worked examples

Five generic scenarios that exercise the decision tree. None
references a real source-project task (`DESIGN.md` §7.2);
each is a generic shape the designer might encounter.

### Example 1: support-ticket triage (binary, mild imbalance)

**Task:** classify incoming support tickets as
Billing-relevant or Not Billing-relevant. Routing decision:
Billing tickets go to the Billing team queue; everything
else stays in the General queue. Production prevalence: ~20%
billing.

**Decision-tree walk:** Q1 binary → Q2 asymmetry: the user
mentions FP cost is roughly 2x FN cost (mis-routing a
non-billing ticket has a higher context-switch cost) but
neither side is catastrophic → Q3 class balance: mild (~20%
positive). Branch: binary, balanced-costs-with-lean, mild
imbalance.

**METRIC_NAME:** `F1`

**METRIC_RATIONALE:** F1 is the right balance for a 2:1 FP:FN
asymmetry with a fixed production prevalence around 20%
billing. A pure precision-at-recall floor was considered but
rejected because the recall floor the user could articulate
was not stable (~0.7 ± a lot). F1 with a documented
precision-leaning posture is more honest about the trade-off
than a constrained-floor metric whose floor is hand-wavy.

### Example 2: clinical-note PHI leak detection (binary, FN catastrophic)

**Task:** classify clinical notes after a redaction pass as
PHI-Removed-Correctly or Still-Leaky. A Still-Leaky note that
slips through is a regulatory issue (HIPAA); a Still-Leaky
flag on a clean note is a re-review cost.

**Decision-tree walk:** Q1 binary → Q2 asymmetry: false
negatives are catastrophic (missing a PHI leak is the
regulatory failure mode); false positives are recoverable
(re-review) → Q4 FN catastrophic.

**METRIC_NAME:** `recall_at_precision`

**Wait — that's wrong.** Re-reading Q4: "False negatives are
catastrophic" → `precision_at_recall` with an explicit
recall floor. The user said FN catastrophic, so we want to
**lock in recall** (catch all the leaks) and let
**precision absorb** the cost.

**METRIC_NAME:** `precision_at_recall`

**METRIC_RATIONALE:** False-negatives are regulatory issues,
so recall must be locked at a high floor (target: 0.95).
Precision can absorb cost — flagged-but-clean notes go to
re-review, which is acceptable. F1 was rejected because it
would optimize for a balance the task economics do not
support. The recall floor of 0.95 is the user's stated
requirement; if the loop cannot meet it, that's a
do-not-ship signal at G6, not a precision-vs-recall
trade-off.

### Example 3: GitHub issue categorization (multi-class, balanced)

**Task:** 4-class categorization of GitHub issues across
{Bug, Feature, Question, Other}. Each category routes to a
different team. No one category is more important than
another; production prevalence ~40/25/25/10.

**Decision-tree walk:** Q1 more than two → Q5 each class
matters roughly equally; mild imbalance but no class is
catastrophic if missed.

**METRIC_NAME:** `macro_F1`

**METRIC_RATIONALE:** macro-F1 weights all four classes
equally regardless of class frequency, which matches the
task economics (mis-routing wastes a team's attention but
does not have asymmetric cost across pairs of classes).
balanced_accuracy was the alternative (per-class recall
averaged); macro-F1 was chosen because the user added a
per-class F1 floor (no individual class F1 below 0.65) to
prevent a class-balanced metric from masking a single
failed class. balanced_accuracy does not naturally
accommodate that floor.

### Example 4: spam moderation (binary, FP catastrophic)

**Task:** classify incoming user messages as Spam or
Not-Spam for a public forum. False positives drop legitimate
posts and damage trust; false negatives are an
inconvenience but recoverable (users can flag missed spam).

**Decision-tree walk:** Q1 binary → Q2 asymmetry: false
positives catastrophic (silencing real users), false
negatives recoverable → Q4 FP catastrophic.

**METRIC_NAME:** `recall_at_precision`

**METRIC_RATIONALE:** False-positives drop legitimate user
content and are reputationally costly to recover from; this
is the canonical asymmetric-cost classifier. Precision must
be locked at a high floor (target: 0.98) so legitimate users
are essentially never silenced; recall can absorb cost
because users can flag missed spam through existing report
flows. F1 was rejected because it would balance the two
costs, which the task economics do not support.

### Example 5: a request that violates the independence rule

**Task description (as the user articulates it):** "We have
a bunch of long customer-feedback comments. We want to
classify them as 'high-signal' or 'low-signal' for the
product team to read. We don't have labels and labelling is
expensive. Can we use GPT-4 to judge whether each comment is
high-signal, and then use that as the metric?"

**Decision-tree walk:** the question never reaches Q1. The
proposal violates the §5 independence rule: the metric is
defined as "GPT-4 says yes/no," and if the production
target is also a GPT-family model (or any LLM at all), the
metric becomes a hall of mirrors — the prompt is optimized
to make GPT-4 happy, GPT-4's happiness becomes inflated
across iterations regardless of actual signal-quality, and
the loop's stop conditions become unreliable.

**Sub-skill response:** v1 cannot support this use case. The
honest paths are:

1. **Label the data.** The methodology assumes ground-truth
   labels; the cost of labeling is part of Phase 1's cost
   posture. If labeling is genuinely too expensive,
   reconsider whether `spp` is the right tool — it is built
   for tasks where labels are obtainable. (`README.md`
   "When to use this" calls this out.)
2. **Wait for v0.3** — multi-judge subjective metrics are
   roadmap (`DESIGN.md` §7.1). v0.3 will define how to
   responsibly use LLM judges for tasks where ground
   truth itself requires LLM judgment.
3. **Reframe the task.** Sometimes "high-signal vs
   low-signal" is actually "contains a feature request"
   or "mentions a competitor" — concrete, labelable
   sub-tasks with model-independent ground truth.

**METRIC_NAME:** none. The sub-skill returns a refusal to
the designer, who returns it to the user as a consultation
outcome that requires either re-scoping the task or
deferring to v0.3.

---

## 5. The independence rule (cross-skill constraint)

**The metric must be computable independently of the model
being optimized.** Stated as a single sentence at the top of
`DESIGN.md` §5; restated here because every option in §3's
decision tree satisfies it, and every `custom` metric must
prove it.

### Why the rule exists

Without independence, the metric becomes a hall of mirrors.
A metric defined as "the production model agrees with itself
that the output is good" inflates over iterations regardless
of actual quality, because the loop is optimizing the prompt
to make the model produce outputs the model approves of —
which is exactly what the prompt always does anyway. Stop
conditions (dev plateau, overfitting guard) become unreliable
because the metric they read is no longer measuring what they
think it is.

The same problem in a slightly weaker form applies when the
judge is a *different* model from the same family (GPT-4
judging GPT-4o-mini outputs). Cross-family judges (e.g.,
Claude Haiku judging GPT-4o-mini outputs) are *less* prone
to this but still have failure modes around shared
training-data biases. v1 takes the strict position: any
LLM-as-judge metric where the judge is an LLM at all is
forbidden, because the cost of getting the boundary wrong is
silently broken methodology, and the v1 user base is not
expected to draw the boundary safely.

### What this rules out in practice

- **LLM-as-judge metrics** where the judge is the same
  model family as the production target. (And in v1,
  any LLM judge at all.)
- **Subjective post-hoc human evaluation** without
  pre-defined labels. v0.3 roadmap.
- **Metrics on unlabeled data** — rubric scores,
  perplexity-style metrics, embedding-similarity to a
  prototype, etc. Without ground-truth labels, the
  methodology has no anchor; the loop's stop conditions
  are uncalibrated.

### What this allows

- **Standard ML metrics** computed against ground-truth
  labels: F1, precision, recall, accuracy, balanced
  accuracy, macro-F1, AUROC (if the prompt outputs
  calibrated probabilities), all variants thereof.
- **Custom metrics** that combine the above with explicit
  weights, e.g., `0.7 * F1 + 0.3 * recall`, as long as the
  underlying components are model-independent. The custom
  formula must be defined in `METRIC_RATIONALE`.
- **Threshold-based metrics** (precision-at-recall,
  recall-at-precision) where the threshold is computed
  from ground-truth labels.

### Where the boundary is and isn't fuzzy

Not fuzzy: the rule applies to the **metric the loop
optimizes**. The auditor sub-agent reads a prompt diff —
that's not a metric, that's a separate review surface
(`DESIGN.md` §4.2). The adversary generates synthetic rows
— that's a thought experiment, not a metric (`DESIGN.md`
§4.3). Neither violates the rule.

Slightly fuzzy: a metric that uses a small classifier model
(non-LLM, e.g., a logistic-regression sentiment model) as
a feature input. v1 treats this as **model-independent** as
long as the classifier was trained on data unrelated to
this task and is not being updated during the loop —
practically, it's just another input feature, like a regex
match or a length count. If the classifier is being
fine-tuned during the loop, that violates independence.

---

## 6. What the sub-skill outputs

After consulting `metric-design`, the designer fills three
fields in `plan.md` §4. The sub-skill's job is to make sure
all three are correct.

### `METRIC_NAME`

One of:

- `F1`
- `balanced_accuracy`
- `macro_F1`
- `precision_at_recall`
- `recall_at_precision`
- `custom`

The Phase 4 template linter validates `METRIC_NAME` against
this list (`plan.md.template` validation rule 4). Adding to
the list is not breaking (per §"Versioning" below) as long
as the new metric satisfies §5; removing from the list is
breaking.

### `METRIC_RATIONALE`

A one-paragraph explanation that names which §3 decision-
tree branch was taken and why, derived from the task
economics in `plan.md` §3 (`HEADLINE_CRITERION`,
`TRADEOFF_NOTES`, `DECISION_RULE`). The rationale must:

- Name the branch (e.g., "binary, FP catastrophic,
  recall-at-precision").
- Reference the asymmetry or balance that drove the choice.
- For constrained-floor metrics, state the floor explicitly
  (e.g., "recall ≥ 0.95" or "precision ≥ 0.80").
- For `custom`, define the formula and prove the §5
  independence rule.
- For `balanced_accuracy` chosen over F1, explain why
  per-class recall is the right object of optimization.

The rationale is what future-them and future-readers consult
to interpret the choice; it is not optional and not a
formality. `plan.md.template` does not have a separate
mechanical validation for the rationale's content (Phase 4
linter would have to NLP-parse it), so the human review at
gate G1 is the enforcement.

### `METRIC_INDEPENDENCE_NOTE`

A short confirmation that the chosen metric is computable
independently of the production model (§5). Example forms:

- "F1 vs ground-truth labels — model-agnostic." (Sufficient
  for the standard metrics.)
- "Custom metric `0.7*F1 + 0.3*recall` is computed from
  ground-truth labels and binary predictions; no LLM is
  involved in scoring." (Sufficient for `custom`.)
- "Multi-judge subjective metric — see `DESIGN.md` §7.1
  v0.3 roadmap." (NOT acceptable; this fails `plan.md.template`
  validation rule 5 and the plan does not pass G1.)

The Phase 4 linter checks that `METRIC_INDEPENDENCE_NOTE` is
non-empty (rule 5); the human review at G1 verifies the note
actually says what it claims.

---

## Pattern for subsequent sub-skills

`prompt-architect` (Phase 2 step 10, ports the six-section
XML template) and `baseline-quality` (Phase 2 step 5, runs
the Phase 1 adversarial label review) follow this same
six-section structure: identity and scope → the decision the
sub-skill helps make → the decision tree → worked examples
→ the cross-skill constraint that governs choices → output
specification.

Each will name its own decision (for `prompt-architect`:
which prompt-architecture sections are required, which are
optional, how rules sections evolve over iterations; for
`baseline-quality`: which adversarial review questions to
ask, which calibration-spot-check signals to surface, when
to flag a labeling pass as inadequate), its own decision
tree (the small, navigable set of branches the designer
walks during consultation), its own worked examples
(generic task shapes, never source-project content per
`DESIGN.md` §7.2), its own cross-skill constraint (for
`prompt-architect`: the six-section discipline; for
`baseline-quality`: the rule that audit findings flow back
into `plan.md` §6's revision log, not into a separate
artifact), and its own output spec (which fields each
sub-skill writes back to `plan.md` or other documented
artifacts).

The structure is non-negotiable. Revisions happen here in
`metric-design/SKILL.md` and propagate by example.

---

## Versioning

Same rule as `designer.md` and `/spp-init`: changes that
**alter methodology guarantees** are flagged as
`BREAKING CHANGE:` in commit messages and trigger a
major-version bump per `CLAUDE.md` §4.

**Methodology-affecting (= breaking):**

- Loosening the §5 independence rule (allowing LLM-as-judge
  for the optimization-target model family, or for any LLM
  in v1).
- Removing one of the documented metric options from §6
  without deprecation.
- Adding a metric that depends on unlabeled data
  evaluation.
- Changing the §3 decision-tree's branches in a way that
  routes a previously-`F1` task to a different metric.
- Removing `METRIC_INDEPENDENCE_NOTE` as a required output
  field.

**Behavioral (= non-breaking):**

- Better worked-example phrasing.
- Adding a new metric option to §6 (e.g., `f_beta` with
  explicit beta) that satisfies the §5 independence rule.
- Clearer §3 decision-tree language.
- New worked examples that exercise existing branches.
- New cross-references.

When in doubt, treat the change as breaking. The cost of a
release-notes paragraph is low; the cost of silently
weakening the independence rule is high.

---

## Cross-references

- [`agents/designer.md`](../../agents/designer.md) — the
  agent that invokes this sub-skill. Specifically: §5.2
  (production economics questions whose answers route the
  decision tree above), §7 (the validation gate that checks
  `METRIC_INDEPENDENCE_NOTE` exists and is non-empty per
  `plan.md.template` rule 5).
- [`templates/plan.md.template`](../../templates/plan.md.template) —
  the destination for the sub-skill's three output fields.
  §4 of the template holds `METRIC_NAME`,
  `METRIC_RATIONALE`, and `METRIC_INDEPENDENCE_NOTE`.
  Template validation rules 4 and 5 enforce the
  list-of-allowed-values and the independence-note
  presence.
- `DESIGN.md` §5 (the independence rule's canonical
  statement), §7.1 (multi-judge subjective metrics non-goal,
  the v0.3 roadmap pointer), §10 glossary (no specific
  entries yet — if metric terminology proliferates, add to
  glossary in a future pass).
- `CLAUDE.md` §4 (Semantic Commits — applies to changes to
  this sub-skill), §8 (auditor information isolation — the
  metric the loop optimizes must be one the auditor does
  not need to invoke a model to interpret, which the §5
  independence rule already covers; restated here so a
  future contributor proposing a "let the auditor compute
  the metric on the fly" feature is redirected to §5).
