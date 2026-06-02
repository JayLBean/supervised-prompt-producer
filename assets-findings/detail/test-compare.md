# Detail: monolithic vs batched/feature-group-split comparison

Deep dive on the `compare/` arm of `spp-test`, going beyond
`assets-findings/spp-test.md`. All numbers are aggregate metrics, costs, token
counts, gate accuracies, and failure-cluster *shapes*. No raw post bodies,
verbatim prompt IP, literal label *vocabularies*, or PII are reproduced. Field
names used are structural handles already public in the asset's own committed
schema/audit docs; they are never paired with a specific row's text or a human's
label. Tags: `[cited]` = lifted from an asset-authored report; `[reproduced-by-us]`
= re-derived by reading the metric JSON directly this session.

The two configs under test (`compare/README.md:1-7` `[cited]`):

- **Monolithic** — one ~953-line prompt covering all 31 fields, one post per call
  (`monolithic_vs_batched.md:8` `[cited]`; `data/monolithic_v6/results.json`
  `mode = monolithic_singleton` `[reproduced-by-us]`).
- **v6 7-part batched (shipped production)** — 7 disjoint group prompts, 10 posts
  per call. This is the `spp/prompts/v6_frozen/` config (`compare/README.md:6`
  `[cited]`).

Same student model, same data, same decode regime for both: `gpt-5.4-nano`,
`reasoning_effort=none`, `temperature=0`, all 50 rows of the `soft_v3` corpus
(`monolithic_vs_batched.md:2-3` `[cited]`; confirmed in both
`results.json` `[reproduced-by-us]`).

---

## 1. The exact comparison — what differs and how the split is structured

The two arms hold model + data + decode params fixed and vary only **prompt
decomposition and I/O batching together**. That coupling matters: the comparison
is monolithic-singleton vs split-and-batched, not a clean one-variable ablation
of "split" alone (the FINAL_PRODUCTION cross-config table separates the levers;
see item 2).

- **Call structure:** monolithic = 50 calls (1 prompt × 50 posts singleton);
  batched = 35 calls (7 groups × 5 batches of 10)
  (`monolithic_vs_batched.md:8-11` `[cited]`).
- **Number of groups: 7.** Confirmed directly from
  `data/v6_FINAL_PRODUCTION/results.json` `per_group_usage` keys
  `[reproduced-by-us]`: `A_speech_act, B_affect, C_journey, D_etiology,
  E_treatment_enum, F_treatment_attitude, G_context`. `per_batch_log` has 35
  entries (7×5), matching the 35-call claim.
- **Disjoint field ownership:** each group owns a non-overlapping subset of the
  31 fields; the batched output is flat-canonical
  (`{"results":[{"post_index":N,"annotation":{...}}]}`)
  (`FINAL_PRODUCTION_REPORT.md:15` `[cited]`).
- A separate "FINAL_PRODUCTION" framing is *not* a third config — it is the same
  v6 batched config given a deep-dive report plus a runtime
  `enforce_exclusivity()` postprocess and a schema validator
  (`FINAL_PRODUCTION_REPORT.md:1-6` `[cited]`). The composite is identical
  (0.7071 raw / 0.7073 validated).

---

## 2. Headline metrics — composite, per-field, per-tier, Pareto/cost

### Composite (`Σ w·jaccard`, weights sum to 1.0)

| Metric | Monolithic | v6 batched | Δ | tag |
|---|---:|---:|---:|---|
| Composite | 0.6219 | 0.7071 | **+0.0852** | `[reproduced-by-us]` eval.json `mean_weighted_composite` |
| Soft mean (31 fields) | 0.7184 | 0.7717 | +0.0533 | `[reproduced-by-us]` |
| Strict mean (31 fields) | 0.6947 | 0.7459 | +0.0512 | `[reproduced-by-us]` `mean_strict_all` |
| Focus mean (T1+T1.5) | 0.6357 | 0.7156 | +0.0799 | `[reproduced-by-us]` `mean_soft_focus` |
| Focus pass count | 3/15 | 3/15 | 0 | `[reproduced-by-us]` |
| All-field pass count | 5/31 | 6/31 | +1 | `[reproduced-by-us]` |
| Focus-min field/value | `treatment_framing` 0.26 | `product_wants` 0.404 | — | `[reproduced-by-us]` |
| Parse errors | 4/50 | 0/50 | −4 | `[cited]` + `[reproduced-by-us]` (`n_errors`) |

The composite gap is +0.085 in batched's favour, called out as **>5× the noise
floor** (`monolithic_vs_batched.md:25` `[cited]`).

### Per-tier rollup (`inspect_*` reports, validated predictions) `[cited]`

| Tier | Monolithic | v6 batched |
|---|---:|---:|
| T1 (12 fields) | 0.795 | 0.810 |
| T2 (13 fields) | 0.631 | 0.706 |
| T3 (6 fields) | 0.737 | 0.796 |
| Mean composite | 0.632 | 0.705 |

T2 (the clinical/enum-heavy tier) is where batched opens the biggest tier gap
(+0.075), consistent with the per-field damage pattern below.

### Per-field damage (where monolithic loses) `[cited]` `monolithic_vs_batched.md:70-85`

Largest single-field drops for monolithic (batched − monolithic):
`condition` −0.300 (wt 0.041), `drug_mentions` −0.263, `cause_attribution`
−0.200, `treatment_framing` −0.199, `treatment_type` −0.190, **`poster_role`
−0.160 at the heaviest weight (0.104)**, `treatment_stance_pattern` −0.140,
`journey_stage` −0.140. Only three low-weight fields move the other way
(`addressing_audience`, `age_group`, `mentions_selfcare`, each +0.060).

### Pareto / cost framing — is batched cheaper AND better?

**Yes, once cache warms — but the raw run shows the opposite, and the asset is
explicit that the headline cost number is misleading.**

Cost/token detail (`monolithic_vs_batched.md:28-39`, `README.md:82-89`)
`[cited]`, cross-checked against eval.json `token_usage` `[reproduced-by-us]`:

| | Monolithic | v6 batched (cold) | tag |
|---|---:|---:|---|
| Prompt tokens/row | 13,009 | 2,051 | both `[reproduced-by-us]` |
| Cache hit rate | 88.8% | 7.0% | both `[reproduced-by-us]` |
| Completion tokens/row | 306 | 458 | both `[reproduced-by-us]` |
| Cost/row (this run) | $0.000906 | $0.000958 | both `[reproduced-by-us]` |
| Cost/row (warmed est.) | ≈$0.000906 | **≈$0.000770** | `[cited]` |
| Wall/row | 2.69s | **0.92s** | `[cited]`+`[reproduced-by-us]` (wall_clock 134.4s vs 45.8s) |

The −5% raw cost edge for monolithic is an artifact: monolithic's identical 13K
prompt sent 50× hit 88.8% prefix cache, while batched was a cold start at 7%
(`monolithic_vs_batched.md:43-50` `[cited]`). The asset reconstructs a warmed
steady-state where batched lands ~15% cheaper, anchored on an *actually observed*
warm run (`v6_runtime_only` at 62.2% cache, $0.000765/row —
`monolithic_vs_batched.md:50` `[cited]`). Batched also wins on **iteration
resilience**: editing one group's prompt invalidates ~2K cached tokens vs
monolithic's full 13K (`monolithic_vs_batched.md:62` `[cited]`).

Net Pareto verdict (`monolithic_vs_batched.md:92-106` `[cited]`): **batched
dominates on quality, wall-clock (3×), warmed cost (~15%), and cache robustness;
ties on schema cleanliness.** Monolithic wins no axis at steady state.

### The lever-decomposition nuance (FINAL_PRODUCTION cross-config table)

The 8-config table (`FINAL_PRODUCTION_REPORT.md:95-176` `[cited]`) isolates the
levers the headline conflates, and the result complicates the "split wins" story:

- **Batching *alone* is score-neutral:** same prompts/format, batch=1 vs batch=10,
  Δ +0.006 (inside noise) (`FINAL_PRODUCTION_REPORT.md:173,176` `[cited]`).
- **Format change (per-row PLB dicts → batched flat-canonical) is the dominant
  *negative* quality lever: −0.111** (`:172`).
- **Model swap gpt-5-nano → gpt-5.4-nano: −0.054** (`:171`).
- So within the *same schema-v2 prompt family*, the shipped batched-flat config
  (#6, 0.7071) is actually *below* the singleton/PLB schema-v1 quality frontier
  (#1 `v4_frozen`/gpt-5-nano at **0.7754**). Only **two** of eight configs are
  Pareto-optimal — #1 (quality) and #6 (cost); there is "no best-of-both"
  (`FINAL_PRODUCTION_REPORT.md:146-150` `[cited]`).

**Reading these two reports together:** the +0.085 "batched beats monolithic" is a
real win *against the monolithic baseline*, but it is driven by **prompt
decomposition / focus**, not by batching (batching is neutral) and not by
flat-canonical formatting (which *hurts*). The monolithic comparison and the
cross-config decomposition are consistent if the win is attributed to the 7-way
split's per-group focus, which is exactly the report's stated mechanism (item 5).

---

## 3. Validation methodology + significance reasoning

There are three report families, each a different lens:

- **`validation_reports/` (schema validator):** runs predictions through a
  schema-driven validator that classifies violations (UNKNOWN_LABEL,
  CO_OCCURRENCE, GATE_INCONSISTENT, TYPE_MISMATCH, CROSS_FIELD, etc.), auto-fixes
  them, and emits a cleaned `predictions_validated.json`. It is **schema-conformance
  checking, not statistics.** Monolithic: 1 violation (a CO_OCCURRENCE auto-fix);
  batched: 5 (all UNKNOWN_LABEL, all stripped) — `validation_monolithic_v6.md`,
  `validation_FINAL_PRODUCTION.md` `[cited]`.
- **`inspect_reports/` (row-by-row diagnostics):** per-field gold-vs-pred dumps
  ranked by composite, mean per-field/per-tier scores, and worst-5 rows. Purely
  descriptive — no test statistic.
- **`eval.json` (scoring):** `mean_weighted_composite`, per-field, gates,
  pass-counts, and a `disagreements` list (monolithic 491, batched 424 entries
  `[reproduced-by-us]`).

**Statistical-significance / CI / bootstrap machinery: NONE.** Significance is
adjudicated entirely by an informal **noise-floor heuristic**, quoted verbatim:

> "The composite gap (−0.085) is **>5× the noise floor** (±0.015 at temp=0 on
> n=50). This is a real, structural difference." (`monolithic_vs_batched.md:25`
> `[cited]`)

and again on the lever decomposition:

> "Batching itself is **score-neutral** at the noise floor (±0.015 at temp=0 on
> n=10 dev)." (`FINAL_PRODUCTION_REPORT.md:176` `[cited]`)

So the v1 finding is **confirmed**: a `±0.015` point-estimate noise floor (NOT a
confidence interval) plus a `Δ > 5× noise floor` prose threshold is the only
significance reasoning. No bootstrap, no permutation test, no paired test, no CI
anywhere in this arm. The noise floor is asserted (temp=0 residual server
nondeterminism), not derived from repeated runs in these files. Note also the
floor is quoted at two different n (n=50 here, n=10 dev there) with the same
±0.015 magnitude, i.e. it is treated as a fixed constant rather than scaled by
sample size.

---

## 4. Metric primitives — and whether anything is continuous/ordinal

- **Per-field primitive: soft Jaccard** `|∩|/|∪|` with accepted-label tolerance
  (the soft-v3 GT carries per-label "accepts" sets, visible throughout the inspect
  reports as `accepts:` rows). Scalar/single_select fields collapse to a singleton
  set, so soft Jaccard = exact match for them.
- **Rollup: weighted composite** `Σ w·jaccard`. eval.json also carries
  `mean_strict_all` (strict equality variant) and `mean_soft_focus` (T1+T1.5
  subset). Per-field "pass" is a threshold test.
- **Gates:** five boolean gate fields scored by `mean_accuracy` (see item 5).
- **No F1 / balanced-accuracy / continuous metric in this arm.** (F1 lives only in
  the separate binary-relevance task, not in `compare/`.)

**Continuous/ordinal scoring: NONE.** Confirmed for this arm. The two
ordinal-by-intent fields, `sentiment_intensity` and `journey_stage`, are scored
as flat categoricals via singleton Jaccard. The inspect reports make the cost
visible: `sentiment_intensity` is the **worst T1 field in both configs** (0.440
monolithic, 0.420 batched `[cited]`), and nearly every error is a one-step
ordinal slip (gold `moderate`/`strong` → pred `mild_moderate`; gold `mild_moderate`
→ pred `strong`/`very_mild`) scored as a full 0.00 miss identically to a
max-distance error. `brand_mentions` (the one free_text field) is scored by set
Jaccard, not string similarity — visible as a near-miss penalised fully (gold
`mielle_organics` vs pred `mielle_organic` → Jaccard 0.00, `[cited]`
inspect row #3). This is the concrete demand signal for an ordinal-distance / MAE
/ fuzzy-string metric primitive the methodology does not have.

---

## 5. Failure-cluster shapes + why batched beats monolithic

### The asset's stated mechanism `[cited]`

`monolithic_vs_batched.md:87-89`: *the gated and clinical/enum fields lose the
most under monolithic* — `condition`, `drug_mentions`, `cause_attribution`,
`treatment_type`, `treatment_stance_pattern`. The reasoning: the monolithic prompt
forces the model to track all 31 fields **+ 5 gates** in one decode pass and
"loses focus on the gating discipline," whereas each group prompt concentrates on
3–8 related fields with its own gate-cascade context inline (e.g. D_etiology
carries the full gate for `condition`/`cause_attribution` next to its only job).
**Focus / cognitive-load-per-decode is the named cause**, not token budget.

### A sharper finding from the gate JSON (not surfaced in the prose) `[reproduced-by-us]`

The `eval.json` `gates` blocks show the failure is more specific than "monolithic
loses focus on gates" — and in one sense *inverted*:

| Gate | Monolithic acc | Batched acc | `[reproduced-by-us]` |
|---|---:|---:|---|
| `condition_named` | 1.00 (0 disagr.) | 0.38 (31) | |
| `drugs_mentioned` | 1.00 (0) | 0.64 (18) | |
| `treatment_discussed` | 0.36 (32) | 0.38 (31) | |
| `causes_addressed` | 1.00 (0) | 0.74 (13) | |
| `treatment_attitude_stated` | 1.00 (0) | 0.30 (35) | |

Monolithic scores **higher** on 4 of 5 gate-trigger accuracies, yet **loses** on
the downstream gated *field content* (`condition` −0.300, `cause_attribution`
−0.200, etc.). The most plausible read: monolithic predicts the gate booleans
near-perfectly because it defaults conservatively (predicts the gate "off" /
not-addressed), then under-populates the dependent enum fields — i.e. it satisfies
gate *consistency* by emitting empty/`not_*` lists. The worst-5 monolithic rows
in the inspect report corroborate this: dependent multi-label fields are
predicted as empty `[]` en masse (`post_type`, `treatment_type`, `drug_mentions`,
`emotional_themes`, `side_effects` all `[]` on the worst rows) — a **systematic
under-prediction / empty-list collapse** that batched's per-group focus mitigates.
So the gate accuracy and the field score move in opposite directions, and the
true win is "batched populates conditional fields the monolith leaves empty,"
which is a *cardinality/under-prediction* story (the v1's Pattern B/D) more than a
*gate-consistency* story.

### Failure-cluster shapes visible in the inspect reports (abstract)

- **Empty-list under-prediction** on implicit multi-label fields under monolithic
  (worst rows have many fields `[]` where gold is non-empty) — v1 Pattern D.
- **Default-attractor collapse**: dependent fields fall to the catch-all
  (`not_specified`, `not_addressed`, `no_treatment_discussed`) — v1 Pattern A;
  present in both configs but heavier in monolithic.
- **Ordinal drift** on `sentiment_intensity` in both — v1 Pattern C.
- **Cross-field leakage** (the residual schema misses): a label from one field
  emitted in another (`treatment_concerns` value landing in `treatment_framing`;
  an `info_seeking_signal` value in `post_type`) — the 5 batched UNKNOWN_LABEL
  misses are exactly these (`FINAL_PRODUCTION_REPORT.md:70-80` `[cited]`).

### Bearing on the prompting-techniques direction

The decisive evidence is that the win is **structural (prompt decomposition for
focus), not infrastructural (batching) and not formatting (flat-canonical
actively hurts).** Batching buys the cost/latency Pareto win; the *quality* win is
the 7-way feature-group split reducing per-decode cognitive load on gated/clinical
fields. This directly supports a feature-group-splitting prompting technique, and
the gate-vs-content inversion argues that the technique's payoff is specifically in
**populating conditional/dependent fields** that a single all-fields decode
under-fills — pointing at per-label-binary / "is-addressed boolean + conditional
multi-label" sub-techniques as the natural next layer.

---

## Confidentiality notes (what was abstracted)

- No raw post bodies, rationale text, or annotator-prompt text reproduced. The
  inspect reports contain full post text and per-row gold/pred; none of that
  row-level content was lifted here — only aggregate per-field/per-tier means and
  the *shapes* of error clusters.
- Field names are structural handles from the asset's committed schema/audit docs;
  never paired with a specific row or human label.
- Label vocabularies (the category strings) appear only where needed to name a
  cluster shape (e.g. catch-all defaults); no field's full enum was enumerated.
- Prompt IP (the 953-line monolithic prompt, the 7 group prompts) treated as
  protected — only line counts, section structure, group count, and I/O contract
  described.
- Metrics, costs, token counts, gate accuracies, and cluster shapes are reported
  in aggregate per DESIGN §7.2.
