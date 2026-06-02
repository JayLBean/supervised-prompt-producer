# spp-test — asset characterization and extraction

Read-only exploration of `/Users/jiafuli/Desktop/Project/spp-test/`. All
specifics below are abstracted per DESIGN.md §7.2: aggregate metrics, failure-cluster
shapes, configuration, and counts are cited; raw row text, literal label values,
verbatim prompt/feature-definition IP, and PII are not reproduced. Where a field or
label name appears, it is one already surfaced in the asset's own committed audit
docs (`FEATURE_AUDIT.md`, `AUDIT_PATH.md`) and is used only as a structural handle,
never paired with row content.

---

## Characterization (what it is)

`spp-test` is **not one experiment**. It is a multi-arm research workspace for a
single NDA-domain task — multi-aspect annotation of social-media posts in a
clinical/consumer hair-loss domain — used as the proving ground for the `spp`
methodology against alternative prompt-optimization approaches. It contains two
distinct task families:

1. **A 31-field multi-aspect structured-annotation task** (the bulk of the asset).
   One post in, a structured object of 31 fields out. The schema
   (`schema_v2.json`) is the canonical artifact. This is the task the
   monolithic-vs-batched, DSPy-GEPA, and four-way comparisons all operate on. It is a
   *multi-field structured-output classification* task in DESIGN.md §7.1.1 v0.2 terms
   (K≈31), not a single-label task. An earlier 33-field schema was audited down to 31
   (`FEATURE_AUDIT.md` §4a drops `hcp_role`, `sentiment_self_directed`).

2. **A separate binary relevance-filter task** (`relevance/spp/…`): classify a post
   as hair-loss-relevant (`true`) or not (`false`), body-text-only. This is the
   genuine single-output `spp` v1 task and the closest match to the shipped
   `examples/hair-loss-relevance/`.

**Field kinds in the 31-field task** (from `schema_v2.json`, counts only):

| `type` | count | nature |
|---|---:|---|
| `single_select` | 11 | multiclass categorical (incl. 2 ordinal-by-intent: `sentiment_intensity`, `journey_stage`) |
| `multi_select` | 15 | multi-label set (cardinality 2–12 labels; gold mean cardinality ~1.6–1.8) |
| `binary` | 4 | boolean |
| `free_text` | 1 | `brand_mentions` (open string set) |

Category cardinality ranges 2–12 (mean ~5.5). Fields are tiered T1/T1.5/T2/T3
(12 T1 / 13 T2 / 6 T3 in `schema_v2.json`; the v2 plan re-tiers to 14 T1+T1.5 /
10 T2 / 7 T3). **No field is continuous or regression-typed.** The two ordinal
fields are treated as flat categoricals (see metric section).

The labels (`labelled_features_soft_v3.json`) are a **soft** ground truth: a primary
annotation plus per-label "accepted sets" (alternative-acceptable labels), so scoring
is partial-credit, not strict equality.

---

## Comparison matrix

The asset runs the same 31-field task through four families of prompt
strategy, plus the separate binary relevance task. Subtrees:

| Subtree | Experiment | Approach | Optimizer driver |
|---|---|---|---|
| `baseline_feature_annotation_v6_monolithic.md` | Monolithic v6 | 1 prompt, all 31 fields, 1 post/call | hand-authored |
| `dspy_optimize_v4/` | DSPy + GEPA | 7 group prompts (A–G), batched I/O, per-group GEPA search | gpt-5.4-mini reflection LM |
| `spp_compare/` (`spp_mini`) | spp framework, API-driven | 7 group prompts, analyst+auditor loop, per-field focus | gpt-5.4-mini (analyst+auditor) |
| `spp/hair-loss-annotation-v6` → `compare/` | spp framework, Opus+HITL (the shipped `v6_frozen`) | 7 group prompts, agentic loop | Claude Opus 4.7 + human gate |
| `spp/hair-loss-annotation-v2/` | audit-driven schema/prompt redesign | per-label-binary + gated-boolean restructure, 9-prompt split | spp loop on gpt-oss-20b |
| `spp/cross_evaluation/` | cross-model/version eval of frozen prompts | frozen v3/v4/v5/v6 run on gpt-5-nano, gpt-oss-120b | none (eval only) |
| `relevance/spp/hair-loss-relavance-init/` and `…/hair-loss-relevance/` | binary relevance filter | genuine `spp` /init→/loop→/finalize | Opus+HITL across 4–5 models |

The decisive comparison is the **four-way** (`spp_compare/FOUR_WAY_COMPARISON.md`,
`FRAMEWORK_JUSTIFICATION_REPORT.md`): a 2×2 of {spp framework, DSPy+GEPA} ×
{gpt-5.4-mini, Opus 4.7}, with the GEPA+Opus cell deliberately left unrun. Plus a
separate **monolithic-vs-7-part-batched** ablation (`compare/reports/`).

---

## Relationship to spp

Two of the subtrees are **genuine spp methodology runs** producing the exact
artifact shapes the shipped skill emits:

- **`relevance/spp/hair-loss-relevance/`** and **`…relavance-init/`** are real
  `/spp-init` → `/spp-baseline` → `/spp-loop` → `/spp-finalize` runs (single-output
  binary, spp v1 bookkeeping). Present and well-formed: `config/plan.md` (versioned
  v1→v7 with a revision log), `splits.json`, per-model `runs/<model>/` dirs,
  per-iteration `run_NN/{prompt_vNN.md, discrepancy_analysis.md, auditor_review.md,
  eval.json, results.json}`, `EARLY_STOP.md`/`SUCCESS.md`, `PROMPT_FROZEN_v01.md`,
  `REPORT.md` with SHA-256 freeze hash, sacred-test discipline. The REPORTs explicitly
  assert the per-stage isolation invariants (rule-edit got no row content; auditor got
  no scores). This matches DESIGN.md §4.2 verbatim. The `init` run additionally has a
  `dspy_bootstrap/` arm comparing spp against a DSPy bootstrap baseline on the same
  task.

- **`spp/hair-loss-annotation-v2/`** is a genuine spp run on the **multi-field** task
  with v0.2-style bookkeeping ahead of the spec: its `plan.md` §4 already uses
  per-field metrics + an aggregate strategy (`min` over Tier-1/1.5) + per-field floors
  (`thresholds.yaml`) + an `OUTPUT_SCHEMA` (`schema.json`), and a `loop_spec.md`. This
  is effectively a field test of the DESIGN.md §7.1.1 multi-field generalization.

- **`spp_compare/spp_mini`** is an *API-reimplementation* of the spp loop (analyst +
  auditor roles as discrete gpt-5.4-mini calls replacing Opus+human), built to
  isolate framework effect from optimizer-model effect. It preserves spp's four
  conservatism mechanisms: one-field-per-iteration focus, auditor gate before student
  eval, revert-on-regression, plateau stop. It does **not** preserve spp's strict
  per-stage *information isolation* — analyst and auditor are API calls with their own
  allow-lists, but score-blindness of the auditor is not the central design lock here
  the way it is in shipped spp.

**Feature-group prompt splitting:** the asset is the empirical origin of DESIGN.md
§7.1's feature-group-splitting principle. The 31 fields are decomposed into 7 group
prompts (A speech-act, B affect, C journey, D etiology, E treatment-enum, F
treatment-attitude, G context) per `dspy_optimize_v4/groups.py` and `AUDIT_PATH.md`
§3c. The v2 redesign splits F further (F1–F4) and A (A1/A2), reaching 9 prompts. Each
group owns a disjoint subset of fields. This is the "default case" the
`examples/feature-group-split/` example is meant to exemplify.

---

## Locked configuration

**Models seen (no aliasing, per §2.2 discipline):**
- `gpt-oss-20b-MXFP4-Q8` (local MLX server, OpenAI-compatible) — the 31-field v1/v2
  loops and the relevance loop's original track.
- `gpt-4o`, `gpt-4o-mini` — relevance-init holdout cross-model eval.
- `Qwen3-14B-MLX-4bit`, `Qwen3.6-35B-A3B-UD-MLX-4bit` — relevance-init loops (local MLX).
- `gpt-5-nano`, `gpt-5.4-nano` — the batched/monolithic/four-way student model; relevance v7 track.
- `gpt-5.4-mini` — optimizer/reflection LM (GEPA reflection; spp_mini analyst+auditor).
- `gpt-5-mini` — DSPy default reflection LM.
- `gpt-oss-120b` — cross_evaluation only.
- Claude Opus 4.7 — the human-in-the-loop spp optimizer (shipped v6_frozen).

**Inference regime (31-field comparisons):** temperature=0, `reasoning_effort=none`
on the gpt-5.4-nano student, batched 10 posts/call, concurrency 4. Empirical noise
floor stated as ±0.015 at temp=0, n=50 (wider at n=15).

**Splits / holdouts:**
- 31-field task: 50-row soft-v3 ground truth; four-way uses DSPy seed=42 35-train /
  15-val (10-row test untouched). DSPy default `--val-frac 0.3`, 70/30.
- v2 task: N=50, seed=47, 60/20/20 (30/10/10).
- relevance: v1 100 rows (60/20/20 → 60/20/20-ish small splits, seed=42); v7 expanded
  to 500 rows via 5-Claude-sub-agent consensus (≥4/5 agreement; 475/500 passed,
  first 400 appended), re-split 300/100/100 seed=42. Sacred-test discipline honored
  (prior 20-row test sacrificed and documented on re-split).

**Iteration counts / what was frozen:** relevance gpt-oss track 4 iters (dev-plateau,
SUCCESS); Qwen3-14B 3 iters (overfitting-guard early-stop); spp_mini 8 iters (5
applied, 2 reverted, 1 auditor-rejected); DSPy GEPA-light ~10–20 candidates/group.
Each frozen prompt gets a SHA-256 in its REPORT.

---

## Headline results (tagged, aggregate-only)

All composite numbers are weighted soft-Jaccard (Σ w·jaccard, w sums to 1.0) unless noted.

**Monolithic vs 7-part batched** (same model gpt-5.4-nano, same 50 rows;
`compare/reports/monolithic_vs_batched.md`) [reproduced-by-us in-asset]:
- 7-part batched composite **0.7071** vs monolithic **0.6219** (Δ +0.085, >5× noise floor).
- Batched is Pareto-better: ~15% cheaper at warmed steady-state, 3× faster wall-clock,
  6.3× fewer prompt tokens/row, cache-resilient to per-group prompt edits.
- Damage concentrates on gated clinical/enum fields when monolithic must track all 31
  fields + 5 gates in one decode pass.

**Four-way framework comparison** (15-row DSPy val; `FOUR_WAY_COMPARISON.md`,
`FRAMEWORK_JUSTIFICATION_REPORT.md`) [reproduced-by-us]:
- DSPy baseline (no opt) 0.6921; DSPy compiled (GEPA, gpt-5.4-mini) **0.6770**
  (GEPA made it *worse* than baseline — 4/7 groups regressed post-compile);
  spp_mini (gpt-5.4-mini) **0.7297**; spp_Opus/v6_frozen (Opus 4.7) **0.7321**.
- Headline: spp_mini beats DSPy-compiled by **+0.0527** at the *same* optimizer model
  → a framework effect, not a model effect. Opus over spp_mini is +0.0024 (inside
  noise) on composite but +3 focus-pass and +3 all-pass.
- Cost: spp_mini $0.66 end-to-end vs DSPy ~$5.00 actual billing (~8×); DSPy's own
  metadata under-reported its cost 4× by hiding reflection-LM spend.

**v6 final production** (`compare/reports/FINAL_PRODUCTION_REPORT.md`)
[reproduced-by-us]: composite 0.7073 validator-cleaned, $0.000958/row, 0.92s/row,
0 parse errors, 0 schema violations post-validator. 8 configs on a documented
Pareto frontier; only v4_frozen/gpt-5-nano (quality 0.7754) and v6_frozen/gpt-5.4-nano
(cost) are non-dominated.

**Binary relevance task** [reproduced-by-us]:
- gpt-oss-20b 4-iter loop: dev F1 0.9524, **test F1 0.7500** (precision 1.00, recall
  0.60 — all 4 test errors false negatives); REPORT recommends iterate-further +
  expand baseline (the actual driver of the v7 100→500 expansion).
- relevance-init cross-model holdout-20 F1: gpt-4o **0.9091**, gpt-4o-mini **0.7619**,
  Qwen3-14B **0.8276** (and a Qwen3-14B frozen-prompt run reporting test F1 **0.9412**,
  recall 1.0 — the "Qwen-locked, recall=1.0" prompt DESIGN.md §2.2 cites).
- relevance v7 gpt-5-nano on the 500-row task: test F1_pos **0.8393** (precision 0.92,
  recall 0.77), headline_met_on_test **False** (target 0.90).

These corroborate DESIGN.md §2.2's cross-model story: a Qwen-locked prompt at
test F1≈0.94/recall=1.0 degrades cross-family (gpt-4o-mini 0.76, gpt-4o 0.91),
length-correlated, documented not prevented.

---

## Metric primitives & whether any continuous/ordinal targets exist

**Primitives in use:**
- 31-field task: **soft Jaccard** per field (`|∩|/|∪|` with accepted-label tolerance;
  scalar fields collapse to singleton-set Jaccard = exact match). Rolled up by
  **weighted composite** (Σ w·jaccard), plus alternative rollups `bottom-k` and
  `strict-threshold` (min over normalized field scores) in
  `dspy_optimize_v4/metric.py` / `utils/metrics.py`. Per-field "pass" = score ≥ a
  per-field threshold (`thresholds.yaml`). `eval.json` carries `per_field`, `gates`,
  `disagreements`, `mean_weighted_composite`, `focus_min`, pass counts.
- Binary relevance task: **F1 on the positive class** (headline), with precision,
  recall, balanced accuracy, confusion matrix reported every iteration.

**Continuous / ordinal targets: NONE are scored as such.** This is the single most
important finding for the "new modes" direction. The two ordinal-by-intent fields
(`sentiment_intensity` none/mild/moderate/strong; `journey_stage`) are typed
`single_select` and scored with **exact-match singleton Jaccard** — a ±1-step ordinal
error scores identically to a max-distance error. `FEATURE_AUDIT.md` Pattern C
explicitly documents the resulting ordinal-drift failure (mild↔moderate confusion 17×)
and `AUDIT_PATH.md` §3b proposes an anchored-CoT 0–10 raw-score → discrete-label
mapping to fix it — i.e. the asset *wants* ordinal/continuous handling but the
methodology has no metric primitive for it. There is no MAE, RMSE, correlation, IoU,
or span metric anywhere. `free_text` (`brand_mentions`) is scored by set Jaccard, not
string similarity.

**Statistical-significance / CI / bootstrap machinery: NONE present; explicitly
flagged as absent.** The only references to bootstrap/permutation/CIs are in
`FRAMEWORK_JUSTIFICATION_REPORT.md` §5.4 admitting they were *not run* ("We have not
run bootstrap resampling or paired permutation tests… we have not formalised this")
and §6 listing "paired bootstrap CIs" as future work. Significance is handled by an
informal empirical **noise floor** (±0.015, a point estimate, not a CI) and "Δ > 5×
noise floor" prose comparisons. No per-iteration significance test gates any decision.

---

## Surfaced gaps / findings

From `FEATURE_AUDIT.md` and `AUDIT_PATH.md` (the diagnostic core):

1. **Both frameworks hit the same ceiling for the same structural reasons** — the
   bottleneck is schema/prompt structure, not model choice. Five repeating failure
   patterns across DSPy and spp:
   - **A — default-attractor labels**: a catch-all label (`not_addressed`,
     `not_specified`, `hopeful_solution`, `no_treatment_discussed`) eats the
     distribution on 5 fields. Fix: split into is-addressed boolean + conditional
     multi-label.
   - **B — multi-label cardinality collapse**: model emits cardinality 1 when gold is
     2+ (predictable label bigrams). Fix: per-label binary prompting.
   - **C — ordinal drift** on the two ordinal fields (centring bias). Fix: anchored CoT.
   - **D — under-prediction (empty list)** on implicit-intent fields. Fix: cue
     dictionaries or demote to "tracked-not-scored" tier.
   - **E — speech-act voice misclassification** collapsing to passive defaults.
2. **Feature redundancy**: two fields near-deterministically redundant (Cramér's V=1.0
   / NMI 0.97) → dropped. Strong semantic clusters (NMI 0.6–0.9) → grouped into the 7
   prompts. This *correlation/redundancy analysis* (NMI, Cramér's V) is itself a
   statistical mechanism spp does not currently provide.
3. **GEPA's structural weakness**: best-of-N candidate search with no revert step lets
   train-overfit candidates ship (4/7 groups regressed post-compile). spp's
   revert-on-regression + auditor gate is the differentiator.
4. **Small-N fragility**: at n_dev=15–20, one row swings F1/composite by ~5pp; plateau
   thresholds had to be loosened below the original spec because the original sat below
   the noise floor (relevance plan §11 v6). Dev>train inversions are noise, not
   overfitting signal, at this size.
5. **The binary relevance finalize** under-met its headline (test F1 0.75 vs 0.90),
   diagnosed as small-baseline under-coverage of three categorical failure clusters →
   drove a real baseline expansion arc.

Mapping to spp methodology: items 1–3 validate the §4.2 isolation + auditor design and
the §7.1 feature-group-splitting principle. Items 2, and the ordinal/CI gaps, point at
bookkeeping the methodology does not yet have.

---

## Relevance to the three planned directions

**(1) More prompting techniques (per-label OvR, CoT, multi-prompt split).**
The asset already *does all three* empirically:
- **Multi-prompt / feature-group split**: 7 (→9) group prompts, disjoint field
  ownership (`groups.py`, `AUDIT_PATH.md` §3c). Proven Pareto-better than monolithic
  (+0.085 composite, 3× faster, cache-resilient). This is direct evidence for the
  feature-group-splitting principle and the granularity guidance (first-split gains;
  the v2 F1–F4 sub-split is the "diminishing returns" frontier).
- **Per-label binary (one-vs-rest)**: the v2 redesign converts 6 high-cardinality
  multi-label fields to per-label yes/no question batteries (`AUDIT_PATH.md` §3a, the
  v2 plan's `per_label_binary` / `gated_per_label_binary` output forms). This is a
  concrete, tested OvR instantiation a future spp prompting-technique layer could
  codify, including the gated-boolean ("is-addressed") pattern for default-attractor
  fields.
- **Anchored CoT for ordinals**: `AUDIT_PATH.md` §3b. Designed but its benefit is
  unmeasurable under the current exact-match metric — couples direction (3) to (1).

**(2) More statistical mechanisms.**
Currently absent and explicitly wanted: paired bootstrap CIs / permutation tests on
row-level scores (named as the honest way to adjudicate the +0.0024 Opus-vs-mini tie
and the +0.0527 framework gap), and the feature-correlation toolkit (NMI, Cramér's V)
used in the audit but not part of spp. A significance layer would replace the informal
"Δ > 5× noise floor" heuristic that currently gates stop/keep decisions, and would
directly serve small-N regimes (n_dev=15–20) where one row = ~5pp.

**(3) More supported modes (continuous/ordinal targets).**
No target in the asset is continuous; the two ordinal fields are the live demand
signal. They are currently squeezed into categorical exact-match scoring, which the
audit shows is the wrong primitive (Pattern C). A future "ordinal/continuous mode"
would need: an ordinal-distance or MAE/RMSE metric primitive, the anchored-CoT
prompting technique already drafted here, and `eval.json`/REPORT bookkeeping for
residual distributions (which DESIGN.md §7.1.1's metrics-layer prose already
anticipates for `number` fields — `brand_mentions` free_text and the ordinals are the
concrete cases this asset would exercise).

---

## Confidentiality notes (what was abstracted)

- **Domain** named only at the abstraction level already used in DESIGN.md/README
  (hair-loss social-media annotation). No raw post bodies, no `body_clean` values, no
  rationale text, no annotator-prompt text were read into or reproduced in this file.
- **Field names** cited are those already public in the asset's own committed
  `FEATURE_AUDIT.md`/`AUDIT_PATH.md`/`schema_v2.json`; used as structural handles
  (type, cardinality, failure-pattern) only — never paired with a specific row's text
  or a specific human's label.
- **Label *values*** (the category strings inside each field) were deliberately not
  enumerated; only counts/cardinalities and field `type` are reported.
- **Prompt IP**: the monolithic v6 prompt, the 7 group prompts, and the frozen prompts
  were treated as protected; their *structure* (6-section, gated-boolean, per-label
  binary, batched I/O contract) and *line/token counts* are described, not their text.
- **Metrics, counts, cluster shapes, configuration, model identifiers, costs** are
  treated as citable findings per §7.2 and reported in aggregate.
- The asset contains a `.env`; it was not read.
