# spp-test — DSPy/GEPA optimization arm (deep dive)

Deep read of `/Users/jiafuli/Desktop/Project/spp-test/dspy_optimize_v4/` (all source
files; per-group `program.json`, `optimized_prompt.md`, `val_predictions_*.jsonl`,
`run_metadata.json`, `inspect_composite.md`). Goes one level below
`assets-findings/spp-test.md`. All protected content (raw post bodies, verbatim prompt
IP, full label enumerations paired with row text) is abstracted per DESIGN §7.2.
Aggregate metrics, config, field-taxonomy shape, and methodology observations are
cited. Tags: **[cited]** = present verbatim in the asset; **[reproduced-by-us]** = a
number we computed/recombined from asset artifacts.

The on-disk run was relocated (`run_metadata.json` paths point at
`/Users/jiafuli/Desktop/591/3_data_annotation/…`); the `spp-test/` copy is a curated
subset. `utils/metrics.py` and `dspy_optimize/schema.py` (the imported scoring
primitives and Literal vocabularies) are **not in this subset** — they are referenced
by import only. Where their behavior is described it is inferred from call sites in
`metric.py` / `pipeline.py` plus the prior pass's characterization.

---

## 1. What the DSPy/GEPA arm does — optimizer config + the 7-group split

### Pipeline shape

For each of 7 groups (A–G), `run.py:optimize_group` (lines 161–226) runs a 4-step
loop: (1) build a `dspy.Predict` signature from the group's batched prompt, (2) score
the **zero-shot baseline** on val, (3) run `GEPA.compile`, (4) re-score the optimized
program on val; then save `program.json` + `optimized_prompt.md` + baseline/optimized
val prediction JSONL. After all 7, `final_composite_eval` (run.py:236–260) composes the
7 group programs into one 31-field annotator and scores end-to-end. [cited]

### GEPA configuration

`run.py:187–195` [cited]:
```
GEPA(metric=metric_fn, auto=args.gepa_auto, reflection_lm=reflection_lm,
     seed=args.seed, log_dir=..., track_stats=True,
     add_format_failure_as_feedback=True)
```
Defaults (`run.py:48–100`, README §Defaults) [cited]:
- `--gepa-auto light` → "~10–20 candidate proposals per group" (README:92). This is a
  **best-of-N reflective prompt search**, no train/val revert gate.
- Student LM `openai/gpt-5.4-nano`, `reasoning_effort=none`, `temperature=1.0`,
  `max_tokens=16000`.
- Reflection LM default `openai/gpt-5-mini`; the actual recorded run overrode it to
  `openai/gpt-5.4-mini` with `--gepa-reflection-reasoning medium`
  (`run_metadata.json:3,14–16`). [cited]
- `seed=42`, `--val-frac 0.3` → 70/30 split of the 50-row soft-v3 GT (≈35 train / 15
  val); recorded run used full 50 rows (`n_posts=null`). [cited]
- `--opt-batch 1` (1 post/LM call during optimization — "preserves training signal
  with our ~50-row budget", run.py:87–88) vs `--eval-batch 10` (10 posts/call at final
  eval to amortize prompt prefix). This batch-size asymmetry is deliberate. [cited]
- Cost guard: soft-warn $2, hard-stop $10 (`token_tracker.TokenTracker`,
  `CostBudgetExceeded` aborts after the current group but still saves compiled groups).
- DSPy 3.2.1, Python 3.11 (`program.json:metadata`). [cited]

GEPA's signal is the **per-group weighted composite** returned as
`dspy.Prediction(score=float, feedback=str)` (`metric.py:134–146`). The `feedback`
string is human-readable per-post weakest-field summary
(`metric.py:124–127`) — GEPA's reflection LM consumes the prose feedback, not just the
scalar. `add_format_failure_as_feedback=True` routes parse failures back as feedback
too. [cited]

### The 7-group split (concrete feature-group decomposition)

`groups.py:33–91` is the single source of truth. Each `Group` owns a **disjoint** set
of flat schema_v2 fields; an `assert` at groups.py:88–90 enforces that every flat field
belongs to exactly one group. The 31 fields partition as [cited]:

| Group | name | # flat fields | gate booleans (not scored, drive gated conversion) |
|---|---|---:|---|
| A | speech_act | 4 (poster_role, post_type, addressing_audience, info_seeking_signal) | — |
| B | affect | 3 (sentiment, sentiment_intensity, emotional_themes) | — |
| C | journey | 3 (journey_stage, user_status, mentions_discontinuation) | — |
| D | etiology | 2 (condition, cause_attribution) | condition_named, causes_addressed |
| E | treatment_enum | 5 (treatment_type, drug_mentions, otc_types, medical_procedure_types, brand_mentions) | drugs_mentioned |
| F | treatment_attitude | 6 (treatment_stance_pattern, treatment_framing, treatment_concerns, side_effects, product_wants, cost_concern) | treatment_discussed, treatment_attitude_stated |
| G | context | 8 (mentions_hcp, research_behavior, mentions_selfcare, mentions_appearance_distress, coping_mechanism, age_group, gender, reason_for_visit) | — |

Total 4+3+3+2+5+6+8 = 31. Groups are **semantic clusters**, not equal-size: F (attitude)
and G (context) carry the most fields. Each group is optimized **only against its own
fields** (`metric.py:_scoped_composite` re-normalizes that group's field weights to sum
to 1, lines 37–66) so a group's GEPA signal is not diluted by fields it doesn't own.
This is the asset's concrete instantiation of feature-group / multi-prompt splitting.
[cited]

### Gated + per-label-binary output contract (schemas.py)

`schemas.py` defines a nested Pydantic model per group, then `to_flat_dict()` collapses
to the flat schema. Three structural patterns, all evidence for OvR / gated prompting:
- **Per-label binary** (`{label: "yes"/"no"}` → list of yes-labels): A.post_type,
  B.emotional_themes, D.condition, D.cause_attribution, E.drug_mentions,
  F.treatment_framing, F.treatment_concerns, F.product_wants. (schemas.py
  `_binary_dict_to_list`, `_normalize_binary_field`.) [cited]
- **Boolean gate → conditional emit**: D fires `condition_named`/`causes_addressed`
  first; if false, the per-label-binary block is `null` and `to_flat_dict()` substitutes
  the sentinel default (`condition=["not_specified"]`, `cause_attribution=
  ["not_addressed"]`). E gates `drug_mentions` on `drugs_mentioned`; F gates
  `treatment_framing` on `treatment_attitude_stated` and forces
  `treatment_stance_pattern="no_treatment_discussed"` when `treatment_discussed` is
  false. (schemas.py:251–280, 310–336, 385–422.) This is the audit's "is-addressed
  boolean + conditional multi-label" fix for default-attractor fields, built into the
  type system. [cited]
- **Hard inter-field rule baked into validator**: B forces
  `sentiment_intensity="mild"` when `sentiment="neutral"` (schemas.py:188–190),
  mirroring the schema's `conditional_rule`. [cited]
- Robustness coercion: case-insensitive yes/no, unknown-key drop, missing-key→"no"
  (schemas.py:61–122). DSPy/LiteLLM forwards the Pydantic schema to OpenAI
  structured-output mode (`signatures.py` docstring), so the LM is JSON-constrained.

GEPA evolves only the **instructions** of each signature — the worked-example block
(`<example_input>`/`<example_output>`) is stripped before optimization
(`signatures.load_instructions`, lines 36–47); DSPy supplies its own demos. The
saved compiled programs show `demos: 0`, `train: 0`, `traces: 0` across all 7 groups —
GEPA shipped a **pure instruction rewrite, zero few-shot demos**
([reproduced-by-us] from `program.json` inspection). The optimized prompts grew vs
their hand-authored seeds (e.g. A 82→175 lines, F 111→268 lines; B shrank 61→109… i.e.
mostly longer, restructured prose with added processing-strategy sections). [reproduced-by-us]

---

## 2. The metric (metric.py + utils.metrics)

**Per-field, then weighted composite. All categorical exact-match-family; no continuous
or ordinal-distance scoring anywhere.** [cited]

`metric.py` does not implement the field primitive itself — it imports
`per_field_scores_dict`, `WEIGHTS`, `weighted_composite`, `bottom_k`,
`strict_threshold`, `THRESHOLDS` from `utils.metrics` (metric.py:19–25) so DSPy/GEPA
numbers stay identical to the v3 reports. The primitive (per prior pass + call-site
behavior) is **soft Jaccard per field**: `|pred ∩ gold| / |pred ∪ gold|` with an
accepted-label tolerance; scalar/single_select/binary fields collapse to a singleton
set, so their soft-Jaccard is exact-match (1.0 or 0.0, modulo accepted-set credit).
`free_text` (brand_mentions) is scored as a **string set Jaccard**, not string
similarity (so `watson` vs `watson_natural` = 0.0, seen in inspect_composite row #10).

Rollup is selectable (`COMPOSITE_FNS`, metric.py:30–34); GEPA used `weighted`:
- `weighted`: Σ wᵢ·jaccardᵢ over the group's fields, weights renormalized to 1 within
  the group (`_scoped_composite`, metric.py:48–54). [cited]
- `bottom-k`: mean of the k=3 lowest threshold-normalized field scores (metric.py:55–60).
- `strict-threshold`: min over threshold-normalized field scores (metric.py:61–65).

Soft ground truth: `data._flatten_v3_annotation` splits each label into `primary` +
`accepted` / `accepted_per_label`, so scoring is partial-credit, not strict equality
(data.py:34–69). **Hard-coded ordinal patch**: for `sentiment_intensity`, `mild` and
`moderate` are forced **scoring-equivalent** — if either is primary or accepted, both
are added to the accepted set (data.py:60–68, repeated in `inspect.py`). This is a
manual, single-field, single-pair ordinal hack — not a general ordinal-distance metric.
A ±1-step error elsewhere on the intensity scale (e.g. mild↔strong, moderate↔very_strong)
still scores a full 0. [cited]

Scoring scope is correctly restricted per group at metric time
(`metric.py:117–120`: `gold_sub = {f: gold.get(f) for f in group.flat_fields}`), and the
composite eval re-scores the merged 31-field annotation with the global
`weighted_composite` (`pipeline.score_composed:65–73`). No CIs, bootstrap, permutation
test, MAE/RMSE, correlation, IoU, or span metric exists anywhere in this arm. [cited]

---

## 3. Field/label taxonomy SHAPE (schema_v2.json, 31 fields)

[cited] from `schema_v2.json` (`categories` = vocab cardinality; ranks skip 16 & 26 =
the two dropped fields `hcp_role`, `sentiment_self_directed`):

| kind | count | fields (cardinality) |
|---|---:|---|
| single_select (multiclass categorical) | 11 | sentiment(4), **sentiment_intensity(4, ORDINAL)**, user_status(4), **journey_stage(4, ORDINAL-by-intent)**, gender(3), research_behavior(5), info_seeking_signal(3), addressing_audience(3), poster_role(5), age_group(4), treatment_stance_pattern(4, gated) |
| multi_select (multi-label set) | 15 | emotional_themes(11), condition(9 incl. default), coping_mechanism(8), treatment_type(4), drug_mentions(8), cause_attribution(7), treatment_concerns(12), treatment_framing(7), side_effects(9), product_wants(10), reason_for_visit(8), post_type(9), cost_concern(6), otc_types(6), medical_procedure_types(6) |
| binary | 4 | mentions_appearance_distress, mentions_hcp, mentions_selfcare, mentions_discontinuation |
| free_text | 1 | brand_mentions |

Cardinality range 3–12, mean ≈ 5.9 over the non-free-text fields. Tiers: 12 T1 / 13 T2
/ 6 T3 (the `tier` key). Six multi_selects carry `output_form: per_label_binary`
(emotional_themes, treatment_concerns, product_wants, post_type) or
`gated_per_label_binary` (condition, drug_mentions, cause_attribution, treatment_framing);
treatment_stance_pattern is `gated_single_select`. Two `conditional_rule` gates in the
schema: `sentiment_intensity` forced to `mild_moderate` when `sentiment=neutral`;
`otc_types` must be `[]` when `treatment_type` excludes `otc`. [cited]

### Fields conceptually ordinal/continuous but typed/scored as flat categorical — FLAGGED

- **`sentiment_intensity`** — genuinely ordinal. schema_v2 defines an ordered 4-level
  scale `very_mild < mild_moderate < strong < very_strong` (with mild/moderate already
  collapsed into one level, default `mild_moderate`). The **B prompt explicitly does
  anchored CoT**: "rate emotional intensity 0–10 mentally BEFORE picking a discrete
  label", with 0–2→very_mild, 3–6→mild/moderate, 7–8→strong, 9–10→very_strong
  (`B_affect.md:4, 24–33`). So the asset uses a continuous 0–10 latent scale internally
  but **scores only the discretized label by singleton exact-match** — the ordinal
  structure is thrown away at scoring time except for the one hard-coded mild≡moderate
  pair. A ±1 ordinal slip (very_mild↔mild_moderate, strong↔very_strong) is penalized as
  hard as a max-distance error. This is the single clearest "wants ordinal, scored
  categorical" case. [cited]
- **`journey_stage`** — ordinal-by-intent (`discovering → treating → accepted`, plus an
  off-scale `not_in_personal_journey`). Typed `single_select`, scored exact-match;
  inspect row #7 shows an `accepted`↔`treating` confusion scored 0.0. [cited]
- **`brand_mentions`** — open string set, scored set-Jaccard not string similarity, so
  near-miss surface forms (e.g. `watson` vs `watson_natural`, inspect row #10) score 0.
  [cited]

No field is regression/numeric-typed.

---

## 4. Headline results (baseline vs GEPA-optimized) + token/cost

### Per-group val scores (`run_metadata.json:26–62`) [cited]

| Group | baseline | GEPA-optimized | Δ |
|---|---:|---:|---:|
| A speech_act | 0.758 | **0.818** | **+0.060** |
| B affect | 0.652 | 0.565 | **−0.087** |
| C journey | 0.815 | 0.774 | −0.041 |
| D etiology | 0.570 | 0.548 | −0.022 |
| E treatment_enum | 0.877 | 0.858 | −0.018 |
| F treatment_attitude | 0.659 | 0.592 | **−0.067** |
| G context | 0.825 | 0.803 | −0.022 |

**GEPA improved exactly 1 of 7 groups (A). The other 6 regressed.** Unweighted mean of
the per-group scores: baseline ≈ **0.737**, optimized ≈ **0.708** — GEPA made the
average group **worse by ≈ −0.029** ([reproduced-by-us] from the table). This is the
on-disk, in-asset confirmation of the prior pass's "GEPA made it worse than baseline;
4/7 groups regressed" headline — and at the per-group val level it is actually **6/7
regressed** here. The four-way comparison's "4/7 regressed" was on the held-out 15-row
DSPy val of the *composed* pipeline; either way the direction is the same: best-of-N
reflective search with no revert gate ships train-overfit candidates. [cited /
reproduced-by-us]

### Composed end-to-end (15-row val, `inspect_composite.md`) [cited]

- Mean composite **0.647** over 15/15 OK rows. Tier rollup: **T1 = 0.872**, T2 = 0.610,
  T3 = 0.589. Damage concentrates in T2/T3 multi-label + gated fields exactly as the
  audit predicts. [cited]
- Worst per-field means: `post_type` 0.000, `emotional_themes` 0.133, `cost_concern`
  0.133, `treatment_stance_pattern` 0.067, `treatment_framing` 0.367, `condition` 0.400,
  `product_wants` 0.467. The recurring failure visible across the worst-10 rows is the
  composed pipeline emitting `null` / `[]` for whole F-group attitude blocks and
  empty per-label-binary sets (cardinality-collapse → under-prediction), and the
  gated `treatment_stance_pattern` coming back `null` (gate logic mismatch between
  emit and scoring). [cited]
- Top per-field means: poster_role 1.000, sentiment_intensity 1.000 (helped by the
  hard-coded mild≡moderate equivalence), medical_procedure_types 1.000,
  info_seeking_signal / user_status / mentions_hcp 0.933. [cited]

Note: `inspect_composite.md` reproduces raw post bodies and gold/pred label pairs;
those are NOT reproduced here per §7.2 (only the aggregate per-field means and
failure SHAPE above).

### Token / cost tracking (`token_tracker.py` + `run_metadata.json:374–379`) [cited]

`TokenTracker` snapshots `dspy.settings.lm.history` (and a separate
`dspy.settings.reflection_lm`) around named sections (`*_baseline_val`,
`*_gepa_compile`, `*_optimized_val`, `final_composite_eval`) and estimates cost from a
hard-coded `PRICING_PER_M` table. Grand total for the recorded full run:

- **6,635 LM calls, 16.6M prompt tokens, 0.92M completion tokens, ≈ $1.20 estimated.**
- GEPA compile dominates: the 7 `*_gepa_compile` sections are ~6,000 of the 6,635 calls.
  Per-group compile cost ranged from A ≈ $0.040 (189 calls) to **F ≈ $0.393 (1,023
  calls, 4.2M prompt + 461K completion tokens)** — F is the most expensive group, the
  same group GEPA regressed most. [cited]

Two important cost caveats this arm itself documents:
1. **The pricing is proxied/approximate.** `gpt-5.4-nano`/`gpt-5.4-mini` rates are
   copied from `gpt-5-*` because official rates weren't available
   (token_tracker.py:36–45, README:114–117); proxied sections print a trailing `*`.
2. **The recorded `est_cost_usd ≈ $1.20` only counts the STUDENT LM.** Every section's
   `by_lm` has a single `student:openai/gpt-5.4-nano` entry — the **reflection LM
   (gpt-5.4-mini) token usage was not captured** (tracker's `_lm_iter` probes
   `dspy.settings.reflection_lm`, but GEPA sets the reflection LM on the optimizer
   instance, not on settings, so it was never sampled, token_tracker.py:119–131,
   159–163). This is the on-disk mechanism behind the prior pass's "DSPy under-reported
   its cost ~4× by hiding reflection-LM spend / ~$5 actual billing." The metadata's
   $1.20 is a student-only floor. [cited / reproduced-by-us]

---

## 5. Bearing on the three planned directions

**(1) More prompting techniques.** This arm is concrete, runnable evidence for all three
techniques at once:
- *Multi-prompt / feature-group split*: 7 disjoint-field group programs with per-group
  scoped metrics (`groups.py`, `metric._scoped_composite`). The split is semantic-cluster
  based and unequal-size — a real instance of "group correlated fields, optimize each
  prompt only on its own fields."
- *Per-label binary (OvR)*: 8 fields use `{label: yes/no}` per-label-binary output
  (`schemas.py`), the gated variant adding an is-addressed boolean for default-attractor
  fields. A future spp prompting-technique layer could codify exactly these two
  output_forms (`per_label_binary`, `gated_per_label_binary`) — they're already named in
  schema_v2's `output_form` key.
- *Anchored CoT for ordinals*: implemented in the B prompt (0–10 mental rating →
  discrete label). Its benefit is **unmeasurable under the current metric** because
  scoring discards the ordinal structure — couples direction (3) to (1).

**(2) More statistical mechanisms.** Wholly absent here and the absence is load-bearing:
the headline GEPA-vs-baseline deltas (e.g. A +0.060, D −0.022, E −0.018) on n_val≈15 are
adjudicated by no significance test at all. GEPA's accept/keep is best-of-N on the
**train** composite with no held-out revert gate — the direct cause of 6/7 groups
regressing on val. A paired bootstrap / permutation CI on the row-level per-field scores
(the `val_predictions_*.jsonl` carry exactly the per-row `fields` dicts needed) would
both (a) tell whether A's +0.060 is real and (b) give GEPA a revert criterion. This arm
is the cleanest demonstration that "no revert + no significance" is what spp's
revert-on-regression + auditor gate fixes.

**(3) More supported modes (ordinal/continuous).** `sentiment_intensity` is the live
demand: an ordered 4-level scale, annotated via continuous 0–10 anchored CoT, then
flattened to a single discrete label scored by exact-match — patched only by a
hand-coded single-pair (`mild≡moderate`) equivalence in `data.py`. `journey_stage` is a
second ordinal squeezed into flat categorical. A real ordinal mode would need: an
ordinal-distance / MAE primitive in `utils.metrics`, removal of the per-field hard-coded
equivalence hack in favor of a general adjacency-tolerant score, and residual-distribution
bookkeeping in the eval artifacts. No `number`/continuous target exists, so the ordinals
(and the free_text `brand_mentions`, which wants string-similarity not set-Jaccard) are
the concrete cases this arm would exercise.

---

## Confidentiality notes (what was abstracted)

- Field and label **names** cited are those already public in the asset's committed
  `schema_v2.json` / `FEATURE_AUDIT.md` / `AUDIT_PATH.md`, used only as structural
  handles (type, cardinality, output_form, gate). Label *value strings* are listed only
  as taxonomy shape, never paired with a specific row's text or a human annotation.
- `inspect_composite.md` contains raw post bodies and per-row gold/pred label pairs;
  **none of that row content is reproduced here** — only aggregate per-field means,
  tier rollups, and the failure-cluster shape.
- Prompt IP (the 7 batched prompts, the GEPA-evolved prompts) is described by
  *structure and size* (sections, gated/per-label-binary contract, anchored-CoT scheme,
  line counts) — not reproduced verbatim. The one prompt excerpt-level detail cited
  (B's 0–10 anchored-CoT mapping) is reported as a mechanism, not as copyable prompt text.
- Costs, token counts, call counts, scores, config, model identifiers are aggregate
  findings, citable per §7.2.
- The asset's `.env` was not read.
