## Direction 3 — More supported modes (continuous / ordinal / regression)

### 1. Summary and motivation

This direction adds a new output *shape* to `spp`: a target whose ground truth is a number
on a bounded ordinal scale or a real-valued (regression) quantity, scored by error-distance
metrics rather than agreement metrics. The evidence for latent demand is convergent across
both the internal and external assets — but it is honest to state up front that **no asset
holds a true continuous target today**. The demand is real and the gap is unmistakable; the
data to exercise it would have to be introduced.

The latent demand:

- **Three ordinal fields are typed and scored as flat categorical** (`test-audit-schema.md`
  Item 1, flag block): an intensity ladder (`very_mild < mild_moderate < strong <
  very_strong`), a journey-stage progression (`discovering → treating → accepted`), and an
  ordered age-bucket scale (`under_30 < 30_to_50 < over_50`). Each is `single_select`,
  scored by exact-match singleton Jaccard, so **a ±1-step error scores identically to a
  max-distance miss**. The documented failure is "ordinal drift" (FEATURE_AUDIT Pattern C):
  centre-attraction confusion (`mild↔moderate` 17×, `strong→moderate` 6×) that the metric
  cannot distinguish from a catastrophic miss.
- **An anchored-CoT fix is drafted, wired into the schema, and unmeasurable today.** The
  intensity field's prompt instructs the model to "rate emotional intensity 0–10 mentally
  BEFORE picking a discrete label" (`test-dspy.md` §3; `test-audit-schema.md` Item 2a),
  producing a latent continuous 0–10 score that is then **discarded** into the 4-level label
  and scored flat. The single existing patch is a hand-coded `mild ≡ moderate` scoring
  equivalence in `data.py` (`test-dspy.md` §2) — a one-field, one-pair manual hack, not a
  general ordinal-distance primitive. Direction 1's anchored-CoT technique cannot be shown
  to help until Direction 3 supplies a metric that rewards getting *closer*.
- **A continuous objective folded into a binary composite (external corroboration).** PUPA's
  leakage axis is `leakage = num_pii_leaked / len(pii) ∈ [0,1]`, a continuous fraction; the
  craft track effectively optimized continuous `1 − leakage` even though spp's metric surface
  is built for classification (`ex-report.md` Item 4c). 5 of 9 load-bearing spp primitives sat
  dormant on this K=1 binary-judge task (`ex-report.md` §B), and `§4.7` marks PUPA "No" for
  "Soft / partial-credit scoring" — the continuous dimension was collapsed to a scalar
  composite.

Honest scoping: the spp-test "soft labels" are **not** continuous — a full scan found zero
floats; they are a hard-`primary` + `accepted`-set partial-credit structure, never a
probability or a numeric target (`test-audit-schema.md` Item 3). So a continuous mode must
*introduce* a numeric target and an ordinal-distance / residual metric; it cannot merely
expose one that already exists in the assets.

The methodology already anticipates this. `metric-design` SKILL specifies `number → MAE
(RMSE if outliers)` (`repo-skill.md` §3, `DESIGN.md:723-726`) and the aggregate sub-skill
already knows it must refuse dimensionally-nonsensical mixes (`DESIGN.md:751-759`). The
blocker is purely implementation: `eval.py:32` is `SUPPORTED_METRICS = {"f1", "accuracy",
"precision", "recall"}`, and `_schemas.py` `EvalJSON` / `PredictionRow` are K=1
classification-shaped with no numeric/residual path (`repo-skill.md` §3).

### 2. The roadmap-vs-non-goal ruling

**Verdict: continuous/ordinal targets are a roadmap generalization, NOT a deliberate
non-goal. They sit inside the methodology's fixed-output-space boundary.**

The relevant non-goal is §7.1.3(a), "Generation-task methodologies"
(`DESIGN.md:2026-2036`), verbatim:

> Free-form text generation (summarization, rewriting, instruction tuning, multi-turn
> conversation) does not have ground truth in the way classification provides — the output
> space is unbounded and there is no "correct label" against which to compute a metric. The
> methodology's validation primitives (sacred test set, F1 / balanced-accuracy / per-class
> metrics, auditor's categorical-vs-row-specific judgment on rule edits) all assume a fixed
> output space. Generation tasks need a different methodology that handles bounded reference
> sets, multiple acceptable outputs, and qualitative judgment under uncertainty.

The boundary bites on **unbounded generation** — "the output space is unbounded and there is
no 'correct label.'" A continuous or ordinal *target* fails this test in the direction that
puts it **inside** the boundary:

- A bounded ordinal scale (e.g. a 4-level ladder, an ordered age bucket) has a finite, fixed
  output space and an unambiguous ground-truth value per row. It is a *fixed* output space.
- A regression target (a real number) is unbounded in cardinality but is **single-valued and
  has ground truth** — every row has one correct number against which a residual is
  computable. There is no "multiple acceptable outputs under qualitative judgment" problem;
  there is a measurable error.

This is confirmed by the grounding note that closes `repo-design.md` §5, verbatim:

> **Continuous/regression is NOT a deliberate non-goal.** Number fields with MAE/RMSE sit
> *inside* the fixed-output-space boundary (the non-goal bites only "unbounded generation").
> … The blocker for direction-3 is implementation, not methodology.

and by the §7.1.3 closing rule (`DESIGN.md:2086-2090`): "When in doubt, lean toward roadmap
rather than deliberate. A v0.x version can always reach a roadmap item."

**Proposed DESIGN clarification.** The v0.2 §7.1.3(a) text lists "F1 / balanced-accuracy /
per-class metrics" as *the* validation primitives that assume a fixed output space. That
phrasing reads as though the fixed-output-space property is *defined by* classification
metrics, which a future contributor could mistakenly cite to reject a `number` target. The
arc-opening DESIGN pin for this direction should add one clarifying sentence to §7.1.3(a):
the fixed-output-space property is about *the presence of ground truth and a bounded answer
per row*, not about the metric family; ordinal and regression targets have ground truth and
are therefore in-scope, scored by error-distance metrics (MAE/RMSE/Spearman/ordinal-distance)
that are the regression-family analogue of F1/balanced-accuracy. This is a documentation
addition (a clarification of an existing roadmap position), not a non-goal reclassification —
nothing is being promoted from non-goal to roadmap, because continuous was never a non-goal.

**The honest gray zone.** The one place a reviewer can legitimately push is the free-text
`brand_mentions` field: it is already scored by set-Jaccard, which is a partial-credit metric
over an open string set (`test-audit-schema.md` Item 1). One can argue a continuous score is
a *smaller* step than that field already takes, because the codebase already tolerates a
non-binary, non-categorical partial-credit number coming out of the metric layer. That cuts
*for* the ruling, not against it: if a bounded set-overlap fraction is already in-scope, a
bounded ordinal distance is plainly in-scope. The genuine line is still generation —
*producing* free text whose correctness is a matter of judgment — and a number target does
not cross it.

### 3. Two sub-modes

These are distinct enough in cost and machinery that they should be sequenced, not bundled.

**Sub-mode A — Ordinal (bounded ordered categories).** The target is one of a small,
*ordered* set of categories. This is what the three real spp-test fields are. The output
space is still an enum; what changes is the *metric*: instead of exact-match (1.0/0.0), the
per-field score is an ordinal-distance score — e.g. `1 − |rank(pred) − rank(gold)| /
(K − 1)`, or a mean-absolute-rank-error, optionally with Spearman across rows for
monotonicity. This unlocks the already-drafted anchored-CoT technique (`test-audit-schema.md`
Item 2a), making Direction 1 and Direction 3 couple: anchored-CoT's benefit becomes
*measurable* only once ordinal distance is scored. Cost is **low**: the OUTPUT_SCHEMA stays
an enum (no new field type required — only an `ordered: true` marker plus the declared rank
order), and the change is confined to the metric layer plus the field-type→metric table.

**Sub-mode B — Continuous / regression (real-number target).** The target is a number. This
needs a genuinely new scoring path: residual-based metrics (MAE primary; RMSE when outliers
matter; correlation / Spearman as secondary diagnostics), a numeric `PredictionRow`
representation, and a **residual-based discrepancy notion** (Section 4) that replaces the
disagreed-row-set machinery. No asset currently has such a target, so this sub-mode would
also need a fixture introduced. Cost is **higher**: new field-type handling in inference and
schema, a new residual path in `eval.py`, and the deepest auditor reframing.

**Which the evidence most demands first: Sub-mode A (ordinal).** Three real fields exhibit
the failure today; a drafted technique is blocked on it; and it is the cheaper change. Ordinal
distance is the minimal intervention that converts an existing, documented, *unmeasurable*
fix into a measurable one. Regression (Sub-mode B) is the fuller generalization with no
in-asset target to validate against — it should follow.

### 4. What changes, layer by layer

**Schema layer.** Ordinal (Sub-mode A): no new JSON Schema type — an enum gains an
`ordered: true` flag plus an explicit rank order (the schema-designer mechanical layer would
add a check that an ordered enum declares its order). Regression (Sub-mode B): `number` is
already an accepted JSON Schema field type in the contract and schema-designer mechanical
layer (`repo-skill.md` §6); the skeleton `price` field in `examples/multi-field-extraction/`
already declares one (`repo-state-convention.md` §3). What is missing is the *scoreable* path,
not the *declarable* type. The `output_form` metadata convention (already used in spp-test for
`per_label_binary` / `gated_*`) is the natural place to record an `anchored_cot` form coupling
to Direction 1.

**Metric layer.** New per-field primitives: `MAE`, `RMSE` (already named in the
`METRIC_NAME[f]` enumeration, `repo-skill.md` §3 / `metric-design SKILL.md:117-120`), plus
`ordinal_distance` / `spearman` / `correlation` (new). F1, balanced-accuracy, macro-F1 and
per-class statistics **do not apply** to these fields — there is no class to compute precision
on. This makes the aggregate's **dimensional-nonsense refusal load-bearing in a new way**: the
sub-skill "must refuse a nonsense aggregate — for example, macro-averaging F1 (range [0, 1],
higher is better) with MAE (range [0, ∞), lower is better)" (`DESIGN.md:751-759`). A
realistic mixed task (e.g. the multi-field-extraction skeleton: an enum `category` scored by
macro-F1 alongside a `price` scored by MAE) hits this refusal *directly* and is the canonical
fixture for testing it. The refusal is a `revise` signal, documentary and not gate-blocking
(`DESIGN.md:751-759`, `repo-skill.md` §3) — so the right resolution is to require the user to
choose a `min`-style or normalized aggregate (the multi-field example already uses `min` for
heterogeneous scales, `repo-state-convention.md` §3), or to keep the number field on its own
floor and out of the cross-field average. Ordinal distance is bounded `[0,1]` higher-is-better,
so it *can* be macro-averaged with F1; MAE/RMSE cannot. This is the cleanest split between the
two sub-modes at the aggregate layer.

**Scoring / `eval.py` and `_schemas.py`.** `eval.py:32 SUPPORTED_METRICS` extends to include
the new metrics; `compute_eval` gains a residual path that, for a numeric/ordinal field,
computes per-row residuals instead of a confusion matrix. `_schemas.py` `PredictionRow`
(`parsed_label: str | None`, `repo-skill.md` §3) and `EvalJSON` (no `per_field` /
`aggregate` / `floor_compliance` sections today) generalize to the three-section `eval.json`
already specified in prose, with a numeric prediction representation and per-row residuals
persisted (the latter also feeds Direction 2's significance work, which consumes per-row
scores). `inference.py`'s single-`label` parser generalizes to extract a typed value per
field. This is the same K=1→K>1 generalization the v0.2 buckets specced but never landed in
the runner; Direction 3 is partly *also* the implementation of the still-contract-only metric
layer for non-classification field types.

**Discrepancy stage.** For ordinal, the existing **disagreed-row-set** machinery still works
(the any-field-disagreed filter, `repo-skill.md` §1) but its notion of "disagreed" should be
adjacency-aware: a ±1 ordinal slip is a weaker signal than a max-distance miss and the
discrepancy artifact should rank by *residual magnitude*, not binary disagreement. For
regression, the disagreed-row *set* is the wrong primitive entirely — every row has a nonzero
residual. The discrepancy stage shifts to a **residual-based notion**: cluster the largest
residuals, surface systematic bias (consistent over/under-prediction), and reference rows by
ID with their residual rather than a match/mismatch flag. The discrepancy subagent's
allow-list (current `eval.json` / `results.json` / disagreed-row content / current prompt /
plan §2 — `repo-skill.md` §1) is unchanged in *membership*; only the content shape inside
those artifacts changes. No new path surfaces, so isolation is intact.

**Auditor judgment — the hard open question (analyze deeply).** The auditor's single question
is: "Is this rule edit categorical (addresses a class of rows defined by an articulable
property) or row-specific (patches one weird row)?" (`DESIGN.md:212-224`,
`agents/auditor.md:343-353`). The concrete test is to generate 5 synthetic rows satisfying
the rule's plain-English condition and check whether the *predicted value for field f* applies
to all 5 (`repo-skill.md` §2). **For a classification target this is well-defined: the
predicted value is a discrete label, and "does the rule force this label" is checkable. For a
regression/ordinal target the predicted value is a number, and a rule edit reads like "predict
0.5 lower when X" or "shift the intensity rating down one step when the post hedges." What
does categorical-vs-row-specific even mean for such an edit?** This is the deepest open
question in this direction and the highest-risk surface (it touches invariant #14, categorical
hard tokens, and the auditor allow-list). Options, with their trade-offs:

- **Option 1 — Reframe the same judgment as an error-direction class.** Keep the binary
  categorical/row-specific verdict, but redefine "the predicted value applies to all 5
  synthetic rows" as "the rule produces the *same directional/magnitude adjustment* on all 5
  synthetic rows" (e.g. all 5 get the residual pushed in the same direction by a similar
  amount). A categorical regression edit is one that corrects a *systematic bias on a
  definable class of rows*; a row-specific one nudges one row's number to fit its known
  residual. This preserves the existing verdict vocabulary, the hard-token contract
  (invariant #14), and the gate-substring machinery unchanged. It is the lowest-risk option
  and is the recommended default. Its weakness: "same adjustment" is fuzzier than "same
  label," and the auditor must judge it *without* score access (it cannot see whether the
  adjustment helped — invariant #2), so the synthetic-rows test must be specified to check
  *applicability of the rule's stated condition*, never *residual improvement*.
- **Option 2 — A new verdict vocabulary for numeric edits.** Introduce verdicts like
  `systematic-bias-correction` (keep) vs `point-fit` (revert/generalize) vs `unclear`.
  Higher fidelity to the regression setting, but it **changes the hard-token set**, which is
  invariant #14 ("verdict tokens are categorical hard tokens — no confidence weighting,"
  `DESIGN.md:1621-1642`) and the gate's literal-substring enforcement (invariant #8,
  `[edit-N.field-name]` + `auditor override`, `DESIGN.md:1495-1515`). Any new token is a
  BREAKING change and must be specified end-to-end (auditor output → REPORT §5 counts → gate
  matcher). Higher risk; only justified if Option 1's reframe proves genuinely unworkable in a
  dry-run.

The non-negotiable constraint under either option: the auditor stays **score-blind**
(`DESIGN.md:201-210, 246-247`; `agents/auditor.md` §2). It may *never* see post-edit residuals,
MAE deltas, or any "this iteration's MAE dropped" hint — "the rule is 'no score signal at
all,' not 'no numerical score'" (`repo-skill.md` §2). A regression target makes this tempting
in a new way (a residual *is* a per-row number that looks like analysis rather than score), so
the DESIGN pin must explicitly state that per-row residuals are score signal and are withheld
from the auditor, exactly as `eval.json` is.

**REPORT trajectories.** REPORT §3 loop trajectory (dev-only, `repo-skill.md` §4) and §2
deltas gain a residual/MAE column for numeric fields; per-field floors (`floor_compliance`)
extend to numeric floors (e.g. `MAE ≤ 0.3`). The §6 ship-decision tree's delta comparisons
(`repo-skill.md` §4) operate on whatever the aggregate is, so they need the aggregate to be
dimensionally coherent — reinforcing the metric-layer refusal above.

### 5. Proposed scope

**Minimal (recommended first PR-arc).** Ship Sub-mode A (ordinal distance) only: an
`ordinal_distance` metric primitive, an `ordered`-enum schema marker, the adjacency-aware
discrepancy ranking, and the Option-1 auditor reframe. This is the smallest change that makes
the already-drafted anchored-CoT technique *measurable* and directly retires the documented
ordinal-drift failure on three real fields. It does not require a new field type or a numeric
inference path, and it keeps the aggregate in the same `[0,1]`-higher-is-better family as F1.

**Fuller (sequenced after).** Add Sub-mode B (full regression): numeric inference + scoring
path in `eval.py`/`_schemas.py`/`inference.py`, MAE/RMSE primitives, residual-based discrepancy,
the dimensional-nonsense aggregate resolution for mixed F1/MAE tasks, and a new
`number`-primary-target fixture (the `multi-field-extraction` skeleton `price` field is the
seed). This is also where the still-contract-only K>1 metric runner finally lands for
non-classification types, so it overlaps the v0.2 implementation debt.

Sequence: ordinal first (cheap, evidenced, unblocks Direction 1), regression second (heavier,
no in-asset target, larger runner surface).

### 6. Target version (proposed, not assumed)

**Proposed: v0.5 or later — after the v1.0 compound-system arc and after Direction 2
(statistics), not before.** Justification:

- This is the **heaviest of the three directions** by invariant-surface contact: it is the
  only one that reshapes the auditor's core judgment (Section 4), versus Direction 2 which is
  finalize-only and touches no isolation contract, and Direction 1 which is mostly additive
  `output_form` values with two BREAKING prompt-structure sub-items.
- The STATE roadmap already names **v1.0 = compound-system bookkeeping** as the highest-priority
  arc (`repo-state-convention.md` §2; `ex-report.md` Item 5), and §7.1.2 fills v0.3
  (multi-judge, multilingual) and v0.4 (cross-model synthesis) (`DESIGN.md:1997-2011`). The
  uncommitted slots are v0.5+.
- It depends on work that should land first: the K>1 metric runner must actually exist (it is
  contract-only today, `repo-skill.md` §3), and Direction 2's per-row score retention at
  finalize is a natural prerequisite for residual-based reporting. Building regression scoring
  on top of a runner that still cannot score K>1 multi-field would mean implementing both at
  once.
- The arc should follow the established convention: open with a `docs(design): pin` PR
  (parallel to PR #19), bucket into ~7 additive PRs, ship each piece standalone with a K=1 /
  classification-only backward-compat fallback before integration (`repo-state-convention.md`
  §1). The auditor reframe is the bucket that must be pinned most carefully.

Not v0.4-adjacent and not v1.0-blocking: it is a clean post-v1.0 generalization once
compound-system bookkeeping and the multi-field runner are in place.

### 7. Locked invariants touched

Referencing the 21-entry inventory (`repo-design.md` §3):

| # | Invariant | Status | One-line why |
|--:|-----------|--------|--------------|
| 14 | Verdict tokens are categorical hard tokens, no confidence weighting | **AT RISK — highest** | Option 2 (new numeric-edit verdict vocabulary) changes the hard-token set; Option 1 avoids this. The auditor-judgment reframe is the single riskiest point in this direction. |
| 2 | Auditor's score-access prohibition | **at-risk (must hold)** | A per-row residual is a per-row number that *looks* like analysis; the pin must explicitly classify residuals as score signal withheld from the auditor. |
| 8 | Auditor verdict gate, literal `auditor override` + `[edit-N.field-name]` | shape-change if Option 2 | New verdict tokens would need the gate matcher extended end-to-end; unchanged under Option 1. |
| 13 | Metric independence rule (per-field) | shape-change | Each numeric field's MAE/RMSE/ordinal metric is independently checked; the per-field independence discipline already generalizes (`DESIGN.md:736-739`). No same-family-judge issue for residual metrics. |
| 1 | Per-stage isolated subagents | shape-change (untouched membership) | Allow-list *membership* is unchanged; only the *content shape* inside the named artifacts (numeric predictions, residuals) changes. No new path is surfaced. |
| 6, 7 | Test rows untouched until finalize; read once | untouched | Numeric scoring changes the metric computed at finalize, not when/how often the sacred set is read. |
| 5 | Adversary score-blindness + non-persistence | shape-change | Synthetic adversarial rows would carry a numeric ground-truth value (parallel to the v0.2 OUTPUT_SCHEMA-shaped extension); score-blindness and non-persistence unchanged. |
| 12 | Six-section prompt structure | untouched (Sub-mode A) / coupled (anchored-CoT) | Ordinal mode adds no prompt-structure change; anchored-CoT (Direction 1) is where the `<output_format>`/`<task>` change lives, and is BREAKING there, not here. |

All other inventory entries (3 no-row-content-to-rule-edit, 4 auditor frequency, 9–11 other
gates, 15–21 operational/REPORT) are untouched.

### 8. CHANGELOG implication

Following the methodology-affecting-PR rule (CLAUDE.md §5; `repo-state-convention.md` §5):

- **New-output-shape framing paragraph.** The release narrative states that `spp` now supports
  ordinal and continuous targets as a new output *shape*, scored by error-distance metrics, and
  reaffirms that this is a roadmap generalization *inside* the fixed-output-space boundary, not
  a non-goal reclassification — with the §7.1.3(a) clarification quoted.
- **`### Added`:** `ordinal_distance` / `MAE` / `RMSE` / `spearman` metric primitives;
  `ordered`-enum schema marker; residual path in `eval.py` / `_schemas.py` / `inference.py`;
  the numeric-target fixture. State the K=1-classification backward-compat fallback for each
  (existing classification tasks score identically).
- **`### Changed` / `BREAKING CHANGE:` (auditor judgment).** The auditor's
  categorical-vs-row-specific judgment is reframed for numeric targets. Under Option 1 this is
  a `### Changed` entry stating the synthetic-rows test is reinterpreted as
  "same-adjustment-on-a-class" with the verdict vocabulary and hard-token contract preserved
  verbatim. Under Option 2 this is a `BREAKING CHANGE:` entry adding numeric-edit verdict
  tokens and extending the gate matcher — name the file, the what, and the leakage/ambiguity
  mode it addresses, per the PR #14 model (`repo-state-convention.md` §5).
- **`### Changed` (aggregate refusal exercised).** Note that the dimensional-nonsense aggregate
  refusal (`DESIGN.md:751-759`) is now reachable by a real mixed F1/MAE task and document the
  required resolution (normalized or `min` aggregate, or numeric field on its own floor).
- Each entry states preservation/shape status and the backward-compat fallback, mirroring the
  v0.2 entries.

### 9. Open design questions for the gate

1. **(Lead) Auditor categorical-vs-row-specific judgment for numeric targets.** Is Option 1
   (reframe the existing binary verdict as "same directional/magnitude adjustment on a class of
   rows," preserving the hard-token contract and invariant #14) sufficient, or does fidelity to
   the regression setting require Option 2 (a new numeric-edit verdict vocabulary, which is
   BREAKING against invariants #8 and #14)? Recommendation: Option 1, validated in a dry-run
   before committing to any new token. This is the gate's most consequential decision.
2. **Aggregate mixing across incompatible metric families.** When a task mixes an F1-scored
   enum field with an MAE-scored numeric field, the aggregate must refuse the macro-average
   (`DESIGN.md:751-759`). What is the *prescribed* resolution surfaced to the user — force a
   `min`/normalized aggregate, or keep the numeric field on its own per-field floor and out of
   the cross-field composite? The ship-decision tree needs a dimensionally coherent aggregate
   to compute its deltas.
3. **Ordinal-vs-continuous sequencing and scope split.** Confirm ordinal (Sub-mode A) ships
   first as the minimal, evidence-backed change that unblocks anchored-CoT, with regression
   (Sub-mode B) sequenced after — and confirm whether ordinal distance should ship even before
   the full K>1 multi-field runner lands, since the three ordinal fields are themselves part of
   a K>1 task that the runner cannot yet score.
