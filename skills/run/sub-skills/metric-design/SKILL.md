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
three: **phases** (orchestration, gate enforcement;
user-facing entry points), **agents** (judgment with
structurally distinct information access; invoked by phases),
and **sub-skills** like this one (opinionated reference
material that informs decisions). A sub-skill is not a chat
and not invoked as a conversational entity. A user reading
this doc should come away knowing how to make the decision
themselves; if follow-up consultation is needed, the
**designer** agent does it (and reads this doc to know which
follow-up to ask).

---

## 1. Identity and scope

`metric-design` makes a small set of related decisions well:
given a task's OUTPUT_SCHEMA (`DESIGN.md` §7.1.1 schema layer)
and production economics, **what metric drives optimization for
each field, what aggregate strategy gives the headline number
across fields, and what optional floors does each field carry?**
The sub-skill records the answers in `plan.md` §3 and §4.

In v0.2 the protocol runs **per OUTPUT_SCHEMA field** and adds
two new stages on top of the per-field walk: aggregate-strategy
consultation and per-field-floor consultation
(`DESIGN.md` §7.1.1 metrics layer). v0.1.0's single-output
classification is the **K=1 degenerate case** under the same
protocol — the per-field walk runs once and produces v0.1.0-
equivalent output; the aggregate-strategy stage is trivial (any
strategy is the identity on K=1); the per-field-floor stage
runs once. v0.1.0 plan.md files do not need to be rewritten
against the v0.2 protocol for `metric-design`'s purposes;
template surface generalization is bucket 5 (compat layer)
territory.

**In scope:**

- **Per-field metric selection** for OUTPUT_SCHEMA fields.
  Binary classification metrics (F1, balanced accuracy,
  precision-at-recall, recall-at-precision); multi-class
  classification metrics (macro-F1, balanced accuracy
  generalized to N classes); numeric-field metrics (MAE,
  RMSE); set/array metrics (set-F1, IoU); custom metrics that
  are explicitly model-independent and combine the above with
  documented weights.
- **Aggregate-strategy selection** across the K per-field
  metrics: `macro-average`, `weighted-average` with user-
  specified weights, or `min-over-fields`. The strategy
  determines the single number that gates `/spp-loop`'s
  dev-plateau and overfitting-guard checks.
- **Per-field-floor selection** (optional). For each field,
  the user specifies a floor on the field's primary metric, or
  declines. Floors are the exception, not the default.
- **The K=1 degenerate case.** Single-output classification
  reaches the same v0.1.0-equivalent decision through the
  v0.2 protocol — per-field walk runs once on the lone field;
  aggregate-strategy is trivial; floor consultation runs once.

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

Given the task's OUTPUT_SCHEMA and production economics —
what each field's output drives, what failure looks like per
field, what asymmetry exists between error modes within a
field, and how the K per-field metrics aggregate to a single
headline number — **what should `plan.md` §3 (headline
criterion) and §4 (per-field metrics + aggregate strategy)
record, and what should the accompanying rationales say?**

The output of consulting this sub-skill spans three groups,
all of which go into `plan.md` §3 / §4 (`plan.md.template`,
once bucket 5 lands the v0.2 surface — see "Forward-noted
template change" in §6).

**Per-field outputs**, for each OUTPUT_SCHEMA field `f`:

- **`METRIC_NAME[f]`**: one of `F1`, `balanced_accuracy`,
  `macro_F1`, `precision_at_recall`, `recall_at_precision`,
  `MAE`, `RMSE`, `exact_match`, `set_F1`, `IoU`, or
  `custom`. The expanded list reflects the v0.2 schema-layer
  field types (`enum`, `string`, `number`, `boolean`, array
  of typed values) suggested in `DESIGN.md` §7.1.1 metrics
  layer.
- **`METRIC_RATIONALE[f]`**: a one-paragraph explanation
  that names which §3.1 decision-tree branch (or which
  type-suggestion path) was taken and why — derived from the
  field's role in the task and from `plan.md` §3's
  `DECISION_RULE` / `TRADEOFF_NOTES`.
- **`METRIC_INDEPENDENCE_NOTE[f]`**: a one- or two-sentence
  confirmation that the chosen metric is computable
  independently of the production model (§5 below). The
  independence rule applies per field; one field's violation
  is sufficient to fail the rule for the task as a whole.

**Aggregate-strategy outputs** (apply across all fields):

- **`AGGREGATE_STRATEGY`**: one of `macro` / `weighted` /
  `min`.
- **`AGGREGATE_WEIGHTS`** (only when `AGGREGATE_STRATEGY` is
  `weighted`): a vector of K non-negative weights, one per
  field, summing to a documented constant (typically 1.0 or
  K).
- **`AGGREGATE_RATIONALE`**: one paragraph naming the
  homogeneity assessment (§3.2's strawman recommendation) and
  any dimensional-mismatch concerns surfaced as `revise`
  signals.

**Per-field floors** (optional, may be empty), for each
OUTPUT_SCHEMA field `f`:

- **`FLOOR[f]`**: a value on the field's primary metric, or
  unspecified.
- **`FLOOR_RATIONALE[f]`** (when `FLOOR[f]` is specified):
  why this floor and not a different one — typically
  grounded in the field being required-and-unrecoverable.

The K=1 degenerate case has a `per_field` block of size 1,
trivial aggregate strategy (any of the three is identity), and
at most one floor — the v0.1.0-equivalent shape.

The designer fills these outputs; the sub-skill makes sure
they are correct and individually defensible. **The sub-skill
does not gate** — outputs are reviewed and recorded; gate-
blocking authority for v0.2 is concentrated at
`schema-designer` (bucket 1), not here.

---

## 3. The protocol

The protocol has three stages, walked in order:

1. **Per-field metric selection** (§3.1) — runs once per
   OUTPUT_SCHEMA field. The existing decision tree below
   walks each field's economics and commits to a metric. With
   K=1 (single-output classification) the stage runs exactly
   once and produces the v0.1.0-equivalent output.
2. **Aggregate-strategy consultation** (§3.2) — runs once
   across all K fields after every field has a metric.
   Picks one of `macro` / `weighted` / `min`. Trivial for
   K=1 (any strategy is the identity).
3. **Per-field-floor consultation** (§3.3) — runs once per
   field. For each field the user specifies a floor on the
   field's primary metric, or declines. Floors are the
   exception, not the default.

The output is per-field metrics + aggregate strategy +
optional per-field floors as enumerated in §2.

### 3.1 Per-field metric selection (the decision tree)

For each OUTPUT_SCHEMA field, walk the decision tree from the
top. Most fields land on a metric in one or two questions;
the K=1 case is the same walk run once.

The starting suggestion is **type-driven**, the same agent-as-
expert pattern `schema-designer` uses for OUTPUT_SCHEMA
strawmans (`DESIGN.md` §7.1.1 schema layer):

| Field's JSON Schema type | Starting suggestion |
|---|---|
| `enum` (binary or multi-class) | F1 / `macro_F1` (proceed to Q1 below) |
| `string` (a single extracted value) | `exact_match` |
| `number` | `MAE` (or `RMSE` if outliers must be penalized) |
| `boolean` | F1 |
| array of typed values (fixed multi-select) | `set_F1` (or `IoU`) |
| nested object | recurse — each sub-field is a separate per-field walk |

The user accepts the suggestion or overrides; for `enum`
fields and any field whose suggestion lands in the F1-vs-
balanced-accuracy neighborhood, walk Q1–Q6 below. The
type-driven suggestion is the strawman; the decision tree
refines it.

**Extraction mode (`TASK_MODE = extraction`; DESIGN.md
§7.1.11).** When the plan's `TASK_MODE` is `extraction`, the
output field is a **variable-cardinality** item array (an
unbounded set pulled from the input), not a fixed multi-select,
so the starting suggestion comes from a different sub-table:

| Extraction field shape | Starting suggestion |
|---|---|
| items matched by text (no reliable offsets) | `extraction_f1` |
| items carrying character offsets (span/NER) | `span_f1` |
| forbidden-token redaction (rewrite output) | `leakage` |

These are alignment metrics: predicted items are matched
one-to-one to gold items (`scripts/_metrics.py`), then per-row
F1 is averaged. `extraction_f1` aligns on normalized text (with
`extraction_precision` / `extraction_recall` available when one
side matters more); `span_f1` aligns on character-offset overlap
(Intersection-over-Union at or above a configurable
`iou_threshold`, default 0.5). Type-awareness is on by default
(`match_type`) so a correct span with the wrong entity type does
not count. `leakage` is the deterministic redaction metric:
1 − the fraction of forbidden gold tokens surviving in the
output. All three are pure functions of (prediction, gold) — no
LLM judge enters scoring (the independence rule, §5; invariant
#13). The decision among them follows the data: offsets present
→ `span_f1`; redaction task → `leakage`; otherwise
`extraction_f1`.

**Question 1: How many classes does the field have?**

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

- **Mild imbalance** (positive class 20–80% of rows).
  Continue to Question 3a.
- **Severe imbalance** (positive class <10% or >90%).
  F1 still works but is noisy at small N. Consider
  `balanced_accuracy` instead, especially if the user
  cares about per-class behavior rather than positive-class
  performance specifically. The rationale should name the
  imbalance and the noise concern.
- **Roughly balanced** (45–55% split). Continue to
  Question 3a.

**Question 3a (binary, F1-or-balanced-accuracy path): is the
positive class operationally privileged?**

- **Yes — one class is the actionable one** (e.g., `Billing`
  is what gets routed; `Not Billing` is the default / null
  state). `F1` on the positive class. The rationale should
  name which class is actionable and why.
- **No — both classes are operationally symmetric** (e.g.,
  `Approve` and `Deny` are both real decisions; the task is
  conceptually "which bucket does this go in?" rather than
  "is this the relevant thing?"). `balanced_accuracy`. The
  rationale should explain the symmetry.

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
| Binary, balanced costs, mild imbalance, positive class privileged | `F1` | Class balance + which class is actionable |
| Binary, balanced costs, mild imbalance, classes symmetric | `balanced_accuracy` | Symmetry rationale |
| Binary, balanced costs, severe imbalance | `balanced_accuracy` | Imbalance + noise concern |
| Binary, balanced costs, roughly balanced, positive privileged | `F1` | Operational-privilege rationale |
| Binary, balanced costs, roughly balanced, classes symmetric | `balanced_accuracy` | Symmetry rationale |
| Binary, FN catastrophic | `precision_at_recall` | Recall floor (e.g., 0.95) |
| Binary, FP catastrophic | `recall_at_precision` | Precision floor (e.g., 0.80) |
| Multi-class, equal class weight | `macro_F1` | Optional per-class F1 floor |
| Multi-class, weighted | `custom` | Weights + justification |
| Multi-class, recall-equal | `balanced_accuracy` | Per-class recall rationale |
| None of the above | `custom` | Formula + independence proof |

### 3.2 Aggregate-strategy consultation

After every OUTPUT_SCHEMA field has a primary metric (§3.1
done for each), the sub-skill walks the user through one
decision: **how do the K per-field metrics aggregate to a
single headline number?**

Three strategies are available, named exactly as they appear
in `eval.json`'s `aggregate.strategy` field
(`DESIGN.md` §7.1.1 metrics layer):

- **`macro`** — per-field metrics averaged with equal weight.
  The right choice when every field's primary metric lives on
  the same scale and equal weighting matches the task economics.
- **`weighted`** — per-field metrics combined under a vector
  of user-specified weights. The right choice when fields
  have explicit relative importance the task economics name
  (e.g., `category` matters twice as much as `priority`
  because routing is the high-stakes downstream effect).
- **`min`** — the worst-performing field's metric is the
  headline. The right choice when **no per-field metric is
  allowed to lag** — every field must clear the same bar to
  declare success.

The sub-skill's strawman is driven by **metric-type
homogeneity**:

| Cross-field metric pattern | Strawman strategy |
|---|---|
| All fields share the same metric (e.g., all F1, all `macro_F1`, all MAE) | `macro` |
| Mixed metrics within a comparable scale (e.g., F1 + `macro_F1`, both bounded [0, 1] higher-better) | `macro` |
| Mixed metrics across dimensional families (e.g., F1 + MAE) | `min`, with a `revise` signal documenting the dimensional mismatch (see below) |
| User names explicit per-field importance weights | `weighted` |
| K=1 (single-field) | any of the three (they are identities); pick `macro` by default for uniformity |

**The `revise` signal on dimensional mismatch.** The sub-skill
**must refuse a nonsense aggregate**. Macro-averaging F1
(range [0, 1], higher-is-better) with MAE (range [0, ∞),
lower-is-better) produces a number with no defensible
interpretation; the optimization loop's plateau check will
treat the resulting value as if it were monotone in quality
when it is not. When the user requests `macro` over
dimensionally mismatched fields, the sub-skill returns a
`revise` signal in `AGGREGATE_RATIONALE` and routes the user
to `min` (which sidesteps the scale problem) or to a `custom`
aggregate (which the user defines, with the §5 independence
rule applied to the combined formula).

The `revise` signal is **documentary, not gate-blocking**.
`metric-design` remains review-and-record per `DESIGN.md`
§7.1.1 metrics layer; the signal lives in
`AGGREGATE_RATIONALE` and the consultation transcript so the
gate-G1 reviewer (the user) sees it. Future contributors must
not promote `metric-design` to verdict-gate authority — see
"Versioning" below.

**Output of this stage:** `AGGREGATE_STRATEGY` (one of
`macro` / `weighted` / `min`); `AGGREGATE_WEIGHTS` (only when
`weighted`); `AGGREGATE_RATIONALE` (one paragraph).

### 3.3 Per-field-floor consultation

After the aggregate strategy is chosen, the sub-skill walks
the user through one decision per OUTPUT_SCHEMA field: **does
this field carry a floor on its primary metric?** Most fields
will not. Floors are the exception.

For each field, the sub-skill's strawman is driven by the
field's role in the schema:

- **The field is required and unrecoverable downstream**
  (the schema marks it `required`; no fallback path exists
  if the value is wrong; downstream consumers act strictly
  on the value — route, ban, redact, charge, page) →
  **suggest a floor**. The user names a concrete value (e.g.,
  F1 ≥ 0.9 on `category`) or accepts a default driven by the
  field's primary metric (e.g., 0.9 for F1-shaped metrics,
  a documented MAE ceiling for numeric fields).
- **The field is required but recoverable** (a fallback,
  re-review, or human-in-the-loop catches errors before
  consequence) → **suggest no floor**. The aggregate metric
  carries the field's quality contribution; a floor is not
  needed.
- **The field is optional** → **suggest no floor**.

The user accepts the suggestion, overrides the value, or
skips. The output for each field is `FLOOR[f]` (a value or
unspecified) and `FLOOR_RATIONALE[f]` (one or two sentences
naming why the floor exists, when one is set). The collected
floors feed into `eval.json`'s `floor_compliance` section
(`DESIGN.md` §7.1.1 metrics layer) and into the
`/spp-finalize` SUCCESS-vs-EARLY_STOP discrimination at loop
termination (decision 4 in the same DESIGN.md subsection).

**Per-class-within-field floors are not a separate tier.**
The v0.1.0 source-project's `recall = 1.0 on the positive
class` shape is achieved in v0.2 by setting the field's
primary metric to `recall_on_class_X` (a `custom` per-field
metric) rather than by attaching a sub-class floor to a
field whose primary metric is F1. The single-tier discipline
keeps the gate-evaluation logic at loop termination
tractable and keeps the headline-criterion shape uniform
across single-output and multi-field tasks
(`DESIGN.md` §7.1.1 metrics layer decision 3).

**Output of this stage:** for each field, `FLOOR[f]` and
`FLOOR_RATIONALE[f]` (when a floor is set). The set may be
empty.

---

## 4. Worked examples

Six generic scenarios. Examples 1–5 exercise §3.1's decision
tree on a single OUTPUT_SCHEMA field — each walks the K=1
degenerate case and produces v0.1.0-equivalent output (the
v0.2 protocol's per-field re-scoping reproduces v0.1.0's
behavior when K=1). Example 6 exercises all three stages on
a multi-field schema. None references a real source-project
task (`DESIGN.md` §7.2); each is a generic shape the designer
might encounter.

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
positive) → Q3a positive class is operationally privileged
(`Billing` is the actionable class; `Not Billing` is the
default / null state). Branch: binary, balanced-costs-with-
lean, mild imbalance, positive class privileged.

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

**A confusable pair worth pinning.** `precision_at_recall`
and `recall_at_precision` are easy to flip. The way to keep
them straight: name the side you want to **lock** first.
Here, FN is catastrophic, so recall must be locked at a
high floor (catch all the leaks) and precision **absorbs
the cost** (re-review handles flagged-but-clean notes). The
metric whose name *starts with* the side that absorbs cost
is the one you want — `precision_at_recall` locks recall
and lets precision absorb. The flipped version
(`recall_at_precision`) is for the opposite asymmetry (FP
catastrophic, recall absorbs cost), as in Example 4 below.

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

**Sub-skill response:** The proposal violates the §5
independence rule, and the violation isn't fixable by
tweaking the metric. Tasks where ground truth itself
requires LLM judgment are a fundamentally different
methodology problem from tasks with model-independent
labels — the loop's discipline (auditor information
isolation, sacred test set, dev-driven stop) is calibrated
for the latter. v1 explicitly defers the former to v0.3,
where multi-judge subjective metrics will get their own
treatment. The honest paths from here are:

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

### Example 6: multi-field product-listing extraction (K=4, all three stages)

**Task** (the schema-layer fixture's
`consultative-ready` task adapted to exercise the metrics
layer): extract product attributes from marketplace listings.
OUTPUT_SCHEMA has four fields:

- `title` — `string`, freeform extraction. Required.
- `price` — `number`, the listing's price. Required.
- `category` — `enum` of 13 marketplace-defined buckets.
  Required; downstream search ranking is keyed on this value
  and the category list is a closed set.
- `brand_known` — `boolean`. Required. Paired with a
  separately-handled `brand` string field (omitted from this
  worked example for brevity).

#### §3.1 walk — per-field metric selection

| Field | JSON Schema type | Strawman | Walk | Final metric |
|---|---|---|---|---|
| `title` | `string` (freeform) | `exact_match` | User confirms — exact-match against the cleaned title is the production criterion. | `exact_match` |
| `price` | `number` | `MAE` | User notes occasional outliers (typos in cents) but those are the cases that matter to catch — escalate to `RMSE`. | `RMSE` |
| `category` | `enum`, 13 values | `macro_F1` | Q1 multi-class → Q5 each class matters roughly equally (no one bucket dominates economics) → `macro_F1`. | `macro_F1` |
| `brand_known` | `boolean` | F1 | Q1 binary → Q2 mild asymmetry (false positive on brand-known is worse than false negative because it propagates a wrong brand) → Q3a positive class privileged → `F1`. | `F1` |

All four fields' metrics are checked against the §5
independence rule individually; all pass (each is computed
from ground-truth labels and predictions, no LLM judge
involved).

#### §3.2 walk — aggregate-strategy consultation

The four metrics are `exact_match` (range [0, 1], higher-
better), `RMSE` (range [0, ∞), lower-better), `macro_F1`
(range [0, 1], higher-better), and `F1` (range [0, 1],
higher-better). Three of the four live on a comparable scale;
`RMSE` does not.

The §3.2 strawman table routes mixed metrics across
dimensional families to `min` with a `revise` signal. The
sub-skill surfaces:

> The four field metrics include `RMSE` for `price`, which is
> on a different scale from the F1-shaped metrics on the
> other three fields. Macro-averaging across them produces a
> dimensionally meaningless number. Recommend `min` (the
> worst-performing field's metric becomes the headline) or
> a `custom` aggregate that normalizes `RMSE` to a
> [0, 1]-bounded score before averaging.

The user picks `min`. `AGGREGATE_STRATEGY` = `min`;
`AGGREGATE_RATIONALE` records the dimensional-mismatch
finding and the user's choice.

(Had the user instead picked `macro` over the user's
objection, the sub-skill would document the `revise` signal
in `AGGREGATE_RATIONALE` and proceed — `metric-design` is
review-and-record. The signal is documentary; the user
remains the gate-G1 decision-maker.)

#### §3.3 walk — per-field-floor consultation

For each field, the sub-skill applies the §3.3 strawman:

| Field | Required-and-unrecoverable? | Strawman | User's decision |
|---|---|---|---|
| `title` | Required, recoverable (downstream consumers re-derive titles from raw `body` if needed) | No floor | Skip |
| `price` | Required, recoverable (price errors surface in QA and are fixable post-hoc) | No floor | Skip |
| `category` | Required, **unrecoverable** (downstream search ranking is keyed on this value; a wrong category is silently wrong forever) | Floor on `macro_F1` (e.g., 0.9) | Accept; floor 0.9 |
| `brand_known` | Required, recoverable (the paired `brand` string field carries the actual brand; `brand_known` only flags ambiguity) | No floor | Skip |

**Output of §3.3:**

- `FLOOR[category] = 0.9`,
  `FLOOR_RATIONALE[category]` = "category drives downstream
  search ranking; a wrong category is unrecoverable downstream;
  0.9 is the production-team-stated floor for ranking
  quality."
- All other fields: no floor.

#### Final outputs (across all three stages)

- **Per-field:** four `(METRIC_NAME, METRIC_RATIONALE,
  METRIC_INDEPENDENCE_NOTE)` triples covering `title`
  (exact_match), `price` (RMSE), `category` (macro_F1),
  `brand_known` (F1).
- **Aggregate:** `AGGREGATE_STRATEGY = min`,
  `AGGREGATE_RATIONALE` documenting the `RMSE`-vs-F1-shaped
  dimensional mismatch and the user's choice.
- **Per-field floors:** one floor on `category`
  (`macro_F1 ≥ 0.9`); three other fields skipped.

The `eval.json` produced by `/spp-loop` will carry a
four-entry `per_field` block, an `aggregate` block with
`strategy: min`, and a `floor_compliance` block with
`category: {floor: 0.9, met: <bool>}` and three
`{floor: null, met: not_specified}` entries.

---

## 5. The independence rule (cross-skill constraint)

**The metric must be computable independently of the model
being optimized.** Stated as a single sentence at the top of
`DESIGN.md` §5; restated here because every option in §3's
decision tree satisfies it, and every `custom` metric must
prove it.

**The rule applies per field.** With the v0.2 per-field
re-scoping, each OUTPUT_SCHEMA field's chosen metric is
independently checked against this rule. A single field's
violation is sufficient to fail the rule for the task as a
whole — there is no "average independence" or "aggregate
satisfies independence even though one field doesn't."
Each `METRIC_INDEPENDENCE_NOTE[f]` attests independence for
field `f`; the absence or insufficiency of any per-field note
is a G1 blocker. The `custom`-aggregate path of §3.2 inherits
the same per-field discipline: the formula's inputs are each
of the per-field metrics, and the rule passes only if every
input passes.

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

**Note on the stricter interpretation.** `DESIGN.md` §5
states the rule textually as "computable independently of
the model being optimized." This sub-skill takes the
stricter position that **no LLM judge is permitted at all**
— even cross-family — because cross-family judges share
enough training-data overlap that the boundary cannot be
drawn safely by v0.1.0 / v0.2 users. The strict rule
applied in v0.1.0 is unchanged in v0.2; the per-field
re-scoping (§3.1 above) does not relax it. A future
contributor applying `DESIGN.md` §5 literally might allow
Claude judges of GPT prompts (or vice versa) in good faith;
this sub-skill forbids it. The looser textual rule may be
revisited in **v0.3** when multi-judge subjective metrics
get their own treatment (per `DESIGN.md` §7.1.2), but until
then the operational rule is the one written here.

### What this rules out in practice

- **LLM-as-judge metrics** where the judge is the same
  model family as the production target. (And in v0.1.0 /
  v0.2, any LLM judge at all.)
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
groups of outputs in `plan.md` §3 / §4: per-field outputs (one
group per OUTPUT_SCHEMA field), aggregate-strategy outputs
(one set across all fields), and per-field floors (optional,
zero or more). The sub-skill's job is to make sure each is
correct and individually defensible.

### Per-field outputs (for each OUTPUT_SCHEMA field `f`)

#### `METRIC_NAME[f]`

One of:

- `F1`
- `balanced_accuracy`
- `macro_F1`
- `precision_at_recall`
- `recall_at_precision`
- `MAE`
- `RMSE`
- `exact_match`
- `set_F1`
- `IoU`
- `extraction_f1` (extraction mode; DESIGN.md §7.1.11)
- `extraction_precision` (extraction mode)
- `extraction_recall` (extraction mode)
- `span_f1` (extraction mode; offset overlap)
- `leakage` (extraction mode; deterministic redaction)
- `custom`

The extraction metrics apply only when `plan.md` §1
`TASK_MODE` is `extraction`; they are the alignment metrics
defined in §3.1's extraction sub-table and implemented in
`scripts/_metrics.py`.

The Phase 4 template linter (once bucket 5 lands the v0.2
template) validates each `METRIC_NAME[f]` against this list.
Adding to the list is not breaking (per "Versioning" below)
as long as the new metric satisfies §5; removing from the
list is breaking.

#### `METRIC_RATIONALE[f]`

A one-paragraph explanation that names which §3.1 decision-
tree branch (or which type-suggestion path) was taken and
why, derived from the field's role in the task and from
`plan.md` §3's `DECISION_RULE` / `TRADEOFF_NOTES`. The
rationale must:

- Name the branch (e.g., "binary, FP catastrophic,
  recall-at-precision") or the type-suggestion path (e.g.,
  "field is `number`, outliers matter, RMSE chosen over MAE").
- Reference the asymmetry or balance that drove the choice.
- For constrained-floor metrics, state the floor explicitly
  (e.g., "recall ≥ 0.95" or "precision ≥ 0.80").
- For `custom`, define the formula and prove the §5
  independence rule.
- For `balanced_accuracy` chosen over F1, explain why
  per-class recall is the right object of optimization.

#### `METRIC_INDEPENDENCE_NOTE[f]`

A short confirmation that the chosen metric is computable
independently of the production model (§5), per field.
Example forms:

- "F1 vs ground-truth labels for field `category` —
  model-agnostic." (Sufficient for standard metrics.)
- "Custom `0.7*F1 + 0.3*recall` for field `category` is
  computed from ground-truth labels and binary predictions;
  no LLM is involved in scoring." (Sufficient for `custom`.)
- "Multi-judge subjective metric — see `DESIGN.md` §7.1
  v0.3 roadmap." (NOT acceptable; this fails plan validation
  and the plan does not pass G1.)

The independence rule applies per field; one field's
violation is sufficient to fail the rule for the task as a
whole.

### Aggregate-strategy outputs (across all fields)

#### `AGGREGATE_STRATEGY`

One of `macro` / `weighted` / `min`. The single value is
checked against this enumeration; future contributors must not
add a fourth strategy without revising `DESIGN.md` §7.1.1
metrics layer (decision 2).

#### `AGGREGATE_WEIGHTS`

A vector of K non-negative weights, one per field, summing to
a documented constant (typically 1.0 or K). Required when
`AGGREGATE_STRATEGY` is `weighted`; absent otherwise.

#### `AGGREGATE_RATIONALE`

A one-paragraph explanation naming the §3.2 strawman path
that produced the strategy choice (homogeneity assessment,
explicit weighting from task economics, dimensional-mismatch
finding, etc.). Required regardless of strategy. Documents any
`revise` signal raised during §3.2 (e.g., dimensional
mismatch when a user picks `macro` over the sub-skill's
recommendation).

### Per-field floors (optional, zero or more)

For each field that carries a floor:

#### `FLOOR[f]`

A value on field `f`'s primary metric (e.g., `0.9` for an
F1-shaped metric, `1.5` as an MAE ceiling for a numeric
field). Direction (≥ for higher-is-better metrics, ≤ for
lower-is-better) is implicit from the metric's type.

#### `FLOOR_RATIONALE[f]`

One or two sentences naming why the floor exists — typically
grounded in the field being required-and-unrecoverable
downstream (the §3.3 strawman trigger) and in the user's
production-team-stated bar.

Fields without floors carry no entry in this group.

### Forward-noted template change

The current `plan.md.template` (v0.1.0) holds `METRIC_NAME`,
`METRIC_RATIONALE`, and `METRIC_INDEPENDENCE_NOTE` as scalar
fields in §4. The v0.2 outputs above are per-field collections
plus an aggregate group plus an optional floor group;
generalizing the template's surface to carry them is **bucket
5** (compat layer) territory. This sub-skill's revision in
this PR specifies the outputs structurally; the runner-side
generation, the template surface, and the Phase 4 linter
update land with bucket 5.

**Usability today.** Until bucket 5 lands the template
surface, `metric-design` v0.2's per-field outputs cannot be
persisted to `plan.md` for K > 1 (multi-field) tasks — the
v0.1.0 scalar template has no slots for per-field
collections, an aggregate group, or per-field floors. K = 1
(single-output) tasks continue to function because the
v0.1.0 scalar template is a valid persistence target for the
degenerate case: the agent collapses the one-element
per-field collection to scalar fields when writing to
`plan.md`. This mirrors **bucket 1**'s pattern —
`schema-designer` shipped standalone before its `/spp-init`
integration; `metric-design`'s v0.2 protocol ships before
its template generalization. Multi-field tasks become
end-to-end runnable when bucket 5 lands.

### Statistical reporting (v0.3)

At `/spp-finalize`, a percentile bootstrap confidence interval is
reported on the **aggregate** metric this sub-skill helped choose —
the test-set CI (`REPORT.md` §2.2), plus an optional dev→test gap CI
and a best-dev-iteration diagnostic CI (`DESIGN.md` §7.1.4). These are
**descriptive context for the human**: they quantify how tightly the
finite test/dev partitions pin down the reported numbers and never
change a metric value, gate the loop, or weight a verdict (invariant
#14).

`metric-design` does **not** select the interval's parameters — the
bootstrap resample count, seed, and confidence level are fixed
`/spp-finalize` defaults, not per-field choices. The sub-skill's only
contribution to the interval is having chosen the per-field metric and
aggregate strategy the CI is computed on; a metric whose per-row
contribution is well defined (the v0.3 classification metrics all are)
is all the bootstrap needs. Per-field intervals are future K > 1 work;
v0.3 reports the aggregate interval, which under K = 1 is the lone
field's interval.

### Per-language reporting (v0.6)

When the dataset spans multiple languages (`DESIGN.md` §7.1.7),
`/spp-loop` and `/spp-finalize` report each field's chosen metric
**sliced per language**, alongside the aggregate — the same kind of
breakdown as the existing per-class slice, computed by grouping rows by
their `language` tag. This is a **reporting slice, not a new metric**:
the per-language number uses the identical mechanical metric this
sub-skill already selected for the field, so it introduces no metric
family and no LLM judge, and the §5 independence rule is untouched.
Mechanical metrics are language-agnostic; string metrics NFC-normalize
and Unicode case-fold before comparing, so non-ASCII text is not
mis-scored on an invisible encoding difference. `metric-design` does
not choose a separate per-language metric, and the slice is emitted
only when the data actually spans two or more languages — single-
language projects see the aggregate alone.

### What this sub-skill does NOT do

- **Does not gate.** `metric-design` is review-and-record.
  Outputs are reviewed at gate G1; the sub-skill itself does
  not block the gate. `revise` signals raised in §3.2 are
  documentary, surfaced in `AGGREGATE_RATIONALE`. The only
  verdict-gated sub-skill in v0.2 is `schema-designer`
  (bucket 1); the contrast is intentional and is locked in
  versioning below.
- **Does not write to artifacts other than `plan.md`.** The
  sub-skill's outputs land in `plan.md` §3 (headline criterion
  including aggregate metric and floors) and §4 (per-field
  metrics + aggregate strategy). It does not write a separate
  `metric_design_review.md`, does not annotate `eval.json`
  directly (`/spp-loop` writes that), and does not annotate
  `data/baseline.csv`. The plan.md-as-contract rule
  (`DESIGN.md` §10) governs.

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
  in v1) — at any layer, per-field or aggregate.
- Removing or weakening the v0.2 **per-field re-scoping**
  (§3.1 running per OUTPUT_SCHEMA field). Reverting to a
  single-task-wide metric would silently break multi-field
  bookkeeping.
- Removing the **aggregate-strategy consultation** (§3.2) or
  the **per-field-floor consultation** (§3.3) stage. Both
  are load-bearing for the v0.2 metrics layer
  (`DESIGN.md` §7.1.1).
- Adding a fourth aggregate strategy beyond
  `macro` / `weighted` / `min` without revising
  `DESIGN.md` §7.1.1 metrics layer (decision 2).
- Promoting `metric-design` to **verdict-gate authority**
  (returning `ready` / `revise` / `not-ready` as a hard
  blocker rather than a documentary signal). The
  review-and-record posture is locked; the only verdict-
  gated sub-skill in v0.2 is `schema-designer` (bucket 1),
  and the asymmetry is intentional — schema design admits a
  parser-deterministic mechanical layer, metric selection
  does not.
- Removing one of the documented metric options from §6
  without deprecation.
- Adding a metric that depends on unlabeled data
  evaluation.
- Changing §3.1's decision-tree branches in a way that
  routes a previously-`F1` field to a different metric.
- Removing `METRIC_INDEPENDENCE_NOTE[f]` as a required
  per-field output, or relaxing the per-field application
  of the independence rule (allowing a "task-aggregate"
  independence note to substitute).
- Allowing the sub-skill to write to any artifact other than
  `plan.md` §3 / §4 (a separate `metric_design_review.md`,
  per-row CSV annotations, direct `eval.json` writes, etc.).
- Re-introducing per-class-within-field floors as a separate
  tier alongside `FLOOR[f]`. The single-tier discipline is
  pinned in `DESIGN.md` §7.1.1 metrics layer (decision 3);
  weakening it widens the gate-evaluation surface
  unnecessarily.

**Behavioral (= non-breaking):**

- Better worked-example phrasing.
- Adding a new metric option to the §6 list (e.g., `f_beta`
  with explicit beta, or a new array-shaped metric) that
  satisfies the §5 independence rule.
- Clearer §3.1 / §3.2 / §3.3 protocol language.
- New worked examples that exercise existing branches or
  stages.
- Reporting an existing per-field metric **sliced per language**
  (v0.6). The slice reuses the field's chosen mechanical metric, adds
  no metric family, and leaves the §5 independence rule untouched.
- Tightening the §3.3 strawman heuristics for what counts as
  "required-and-unrecoverable" with rationale, as long as
  the user can still override or skip per field.
- Sharper §3.2 strawman recommendations (e.g., a finer-
  grained homogeneity assessment) that route to the same
  three documented strategies.
- New cross-references.

When in doubt, treat the change as breaking. The cost of a
release-notes paragraph is low; the cost of silently
weakening the independence rule, the per-field re-scoping,
or the review-and-record posture is high.

---

## Cross-references

- [`agents/designer.md`](../../agents/designer.md) — the
  agent that invokes this sub-skill. Specifically: §5.2
  (production economics questions whose answers route the
  decision tree above), §7 (the validation gate that checks
  `METRIC_INDEPENDENCE_NOTE` exists and is non-empty per
  `plan.md.template` rule 5).
- [`../schema-designer/SKILL.md`](../schema-designer/SKILL.md)
  — the verdict-gated sibling sub-skill (bucket 1 of v0.2).
  `metric-design`'s review-and-record posture is intentionally
  **not** inherited from `schema-designer`'s verdict-gate
  pattern; the asymmetry is locked by `DESIGN.md` §7.1.1
  metrics layer (decision 6). Future contributors proposing
  to add verdict-gate authority to `metric-design` should
  read that decision and the "Versioning" section above
  before editing.
- [`templates/plan.md.template`](../../templates/plan.md.template) —
  the destination for the sub-skill's outputs. v0.1.0's §4
  holds scalar `METRIC_NAME`, `METRIC_RATIONALE`, and
  `METRIC_INDEPENDENCE_NOTE`. The v0.2 surface (per-field
  outputs, aggregate-strategy outputs, optional per-field
  floors) lands in **bucket 5** (compat layer) — not in this
  PR. Template validation rules 4 and 5 currently enforce
  the v0.1.0 list-of-allowed-values and independence-note
  presence; bucket 5 generalizes them per-field.
- `DESIGN.md` §5 (the independence rule's canonical
  statement); §7.1.1 schema layer (the OUTPUT_SCHEMA contract
  this sub-skill's per-field re-scoping operates against);
  **§7.1.1 metrics layer** (the design contract this sub-
  skill realizes — per-field metric types, aggregate
  strategy, headline-criterion two-component shape, stop
  discipline, eval.json schema, K=1 backward compatibility);
  §10 glossary (no specific entries yet — if metric
  terminology proliferates, add to glossary in a future
  pass).
- `CLAUDE.md` §4 (Semantic Commits — applies to changes to
  this sub-skill), §8 (auditor information isolation — the
  metric the loop optimizes must be one the auditor does
  not need to invoke a model to interpret, which the §5
  independence rule already covers; restated here so a
  future contributor proposing a "let the auditor compute
  the metric on the fly" feature is redirected to §5).
