# test-audit-schema — deep dive on AUDIT docs, schema, soft labels, monolithic prompt

Read-only deep pass over `/Users/jiafuli/Desktop/Project/spp-test/`. Abstracted per
DESIGN.md §7.2: only aggregate counts, field `type`/cardinality, failure-cluster shapes,
methodology observations. Label *value strings* and verbatim prompt/feature-definition IP
are not reproduced. Field names used here are structural handles already public in the
asset's own committed `schema_v2.json` / `FEATURE_AUDIT.md` / `AUDIT_PATH.md`; they are
never paired with row content or a human label. The `.env` was not read.

Sources:
- `schema_v2.json` (canonical 31-field schema, 538 lines)
- `AUDIT_PATH.md` (143 lines, three-stage redesign plan)
- `FEATURE_AUDIT.md` (149 lines, failure-pattern diagnosis)
- `labelled_features_soft_v3.json` (13,765 lines; 50 rows, structure-only)
- `baseline_feature_annotation_v6_monolithic.md` (953 lines, headings only)

---

## Item 1 — Full field/label taxonomy SHAPE from `schema_v2.json`

**Total fields: 31** (`schema_v2.json` line 1 → 538; an earlier 33-field schema was
audited down — `hcp_role` and `sentiment_self_directed` dropped per `FEATURE_AUDIT.md`
§4a / `AUDIT_PATH.md` §2a, hence the non-contiguous `rank` values: 16, 26 absent and the
list jumps 15→17, 25→27).

**Type distribution** (from the `type` key on each object):

| `type`         | count | nature                                            |
|----------------|------:|---------------------------------------------------|
| `single_select`|    11 | one categorical pick                              |
| `multi_select` |    15 | label-set (cardinality 3–12 in vocab)             |
| `binary`       |     4 | boolean                                           |
| `free_text`    |     1 | open string set (`brand_mentions`, no categories) |

**Tier distribution:** T1 = 12, T2 = 13, T3 = 6.
**`output_form` (inference contract, not data type):** plain = 22; `per_label_binary` = 4
(`emotional_themes`, `treatment_concerns`, `product_wants`, `post_type`);
`gated_per_label_binary` = 4 (`condition`, `drug_mentions`, `cause_attribution`,
`treatment_framing`); `gated_single_select` = 1 (`treatment_stance_pattern`).
**Gated fields (have a `gate_field`):** 5. **Fields carrying a `default`/catch-all:** 7.
**Fields with a `confidence_threshold` (0.6–0.85):** 15. **`conditional_rule`:** 2
(`sentiment_intensity` forced to mid value when `sentiment=neutral`; `otc_types` must be
empty unless `treatment_type` includes `otc`).

### Per-field table (type / cardinality abstracted — values NOT listed)

`card` = number of declared categories (vocabulary cardinality), not gold cardinality.
`ORD?` flags conceptually ordinal/continuous-in-disguise fields (see flag block below).

| # | field | `type` | card | tier | output_form | default | conf | ORD? |
|--:|-------|--------|----:|------|-------------|:------:|:----:|:----:|
| 1 | sentiment | single_select | 4 | T1 | — | Y | — | partial (polarity, not strictly ordered) |
| 2 | sentiment_intensity | single_select | 4 | T1 | — | Y | — | **ORDINAL** (very_mild<mild_moderate<strong<very_strong) |
| 3 | emotional_themes | multi_select | 11 | T2 | per_label_binary | — | 0.70 | no |
| 4 | condition | multi_select | 9 | T2 | gated_per_label_binary | Y | 0.80 | no |
| 5 | mentions_appearance_distress | binary | 2 | T1 | — | — | — | no |
| 6 | coping_mechanism | multi_select | 8 | T2 | — | — | 0.75 | no |
| 7 | user_status | single_select | 4 | T1 | — | — | — | weakly ordinal (funnel position) |
| 8 | journey_stage | single_select | 4 | T3 | — | — | — | **ORDINAL** (stage progression: discovering→treating→accepted) |
| 9 | treatment_type | multi_select | 4 | T2 | — | — | 0.85 | no |
| 10 | drug_mentions | multi_select | 8 | T2 | gated_per_label_binary | Y | 0.85 | no |
| 11 | cause_attribution | multi_select | 7 | T3 | gated_per_label_binary | Y | 0.65 | no |
| 12 | gender | single_select | 3 | T1 | — | — | — | no |
| 13 | treatment_concerns | multi_select | 12 | T2 | per_label_binary | — | 0.75 | no |
| 14 | treatment_framing | multi_select | 7 | T2 | gated_per_label_binary | — | 0.60 | no |
| 15 | side_effects | multi_select | 9 | T2 | — | — | 0.80 | no |
| 17 | mentions_hcp | binary | 2 | T1 | — | — | — | no |
| 18 | research_behavior | single_select | 5 | T1 | — | — | — | no |
| 19 | info_seeking_signal | single_select | 3 | T1 | — | — | — | no |
| 20 | product_wants | multi_select | 10 | T2 | per_label_binary | — | 0.65 | no |
| 21 | reason_for_visit | multi_select | 8 | T2 | — | — | 0.80 | no |
| 22 | addressing_audience | single_select | 3 | T1 | — | — | — | no |
| 23 | mentions_selfcare | binary | 2 | T1 | — | — | — | no |
| 24 | post_type | multi_select | 9 | T2 | per_label_binary | — | 0.70 | no |
| 25 | poster_role | single_select | 5 | T1 | — | — | — | no |
| 27 | mentions_discontinuation | binary | 2 | T1 | — | — | — | no |
| 28 | age_group | single_select | 4 | T3 | — | — | — | **ORDINAL** (ordered age buckets: under_30<30_to_50<over_50; +not_specified) |
| 29 | cost_concern | multi_select | 6 | T3 | — | Y | 0.85 | no |
| 30 | otc_types | multi_select | 6 | T2 | — | — | 0.80 | no |
| 31 | medical_procedure_types | multi_select | 6 | T2 | — | — | 0.80 | no |
| 32 | treatment_stance_pattern | single_select | 4 | T3 | gated_single_select | Y | — | no (a 1/2/3-treatment count flavor, but not metricized) |
| 33 | brand_mentions | free_text | 0 | T3 | — | — | — | continuous-set (string set, scored by set overlap) |

### CRITICAL flag — ordinal/continuous fields typed/scored as flat categorical

Three fields are **conceptually ordered scales typed as plain `single_select` and scored
by exact-match singleton Jaccard** (a ±1 step costs the same as a max-distance miss):

- **`sentiment_intensity`** (`schema_v2.json` L17–32) — explicit intensity ladder
  very_mild < mild_moderate < strong < very_strong. The schema's own `description` even
  says "Anchored-CoT: rate 0-10 first, then map" (L25) — the prompt already produces a
  latent 0–10 continuous score, then **discards it** into a 4-level categorical that is
  scored as a flat set. This is the cleanest "continuous-in-disguise" instance in the asset.
- **`journey_stage`** (L127–140) — staged progression discovering → treating → accepted
  (+ a non-journey out-class). Ordered; scored flat.
- **`age_group`** (L441–454) — ordered buckets under_30 < 30_to_50 < over_50 (+ not_specified).
  Ordered; scored flat.

Weaker/partial ordinals not counted in the hard "3": `sentiment` (polarity axis with a
`mixed`/`neutral` centre, behaves like a sinkhole — `FEATURE_AUDIT.md` Pattern C),
`user_status` (treatment-funnel position), and `treatment_stance_pattern` (encodes a
treatment-count dimension 1/multiple). **No field is typed `numeric`/regression. There is
zero continuous scoring anywhere** — the only non-categorical target, `brand_mentions`
free_text, is scored by set Jaccard, not string/edit distance.

---

## Item 2 — What `AUDIT_PATH.md` and `FEATURE_AUDIT.md` conclude

Both docs treat the DSPy 15-row worst-case set + the SPP 50-row eval as **one combined
failure corpus** (`FEATURE_AUDIT.md` L3) and find: *both frameworks hit the same ceiling
for the same structural reasons — the bottleneck is schema/prompt structure, not model
choice* (`FEATURE_AUDIT.md` §1; `AUDIT_PATH.md` summary L217). Five repeating failure
patterns (A–E, `FEATURE_AUDIT.md` §2). The headline structural insights (§5 L149):
"(1) multi-label fields with catch-all defaults are systematically broken by the schema
design itself — not by the prompt; (2) co-occurring label bigrams … cannot survive
single-pass extraction and require per-label binary prompts."

### 2a. ORDINAL-DRIFT failure + anchored-CoT fix

`FEATURE_AUDIT.md` Pattern C (§2, L57–65): "Ordinal drift on 4-level scales." The
intensity field shows "mild↔moderate (17×), strong→moderate (6×)" confusion; "The model
averages toward the centre. `mixed` and `neutral` are sinkholes." Listed in §1's bottom-8
table (L20) as `sentiment_intensity` "ordinal (4) … min 0.500 … ±1-step ordinal drift."

The metric consequence (cross-cut with the prior pass `spp-test.md` §"Metric primitives"):
because the field is typed `single_select` and scored by **exact-match singleton Jaccard**,
a one-step ordinal error and a max-distance error score *identically* (both 0). The metric
has no ordinal-distance primitive.

Drafted fix — **anchored CoT**, `AUDIT_PATH.md` §3b (L124–138). Abstracted quote of the
mechanism: *force the model to emit a raw 0–10 score first against anchored bands, then map
that number to the discrete label* — output shape `{"raw_score": N, "label": "..."}`. The
doc's stated rationale: "This breaks the centring bias (mild↔moderate confusion 17×) by
making the boundary explicit" (L138). Crucially the schema already wires this in
(`sentiment_intensity.description`, L25), so a **latent continuous 0–10 score is computed
and then thrown away** — there is no metric that scores it.

### 2b. Per-label / one-vs-rest redundancy analysis (NMI / Cramér's V)

`FEATURE_AUDIT.md` §3 computes a redundancy map on the 50-row baseline (Cramér's V for
single-label pairs, Normalized MI for multi-label) — `AUDIT_PATH.md` Stage-1 decision tree
step 3 (L27–32) operationalizes it: *NMI > 0.95 or Cramér's V = 1.0 → drop/derive; NMI
0.6–0.9 cluster → group into one sub-prompt*.

Findings (abstracted, structural handles only):
- **Near-deterministic redundancy → drop/merge** (§3a): one pair at **V = 1.00**
  (`mentions_hcp` ↔ `hcp_role`, one field fully derivable) and one at **NMI = 0.97**
  (`emotional_themes` ↔ `sentiment_self_directed`, "same affect signal, different
  projection"); plus a V = 0.80 near-duplicate. These drove the 33→31 field reduction
  (`AUDIT_PATH.md` §2a, ~8% prompt-token savings, "removes correlated-error inflation").
- **Strong semantic clusters → group** (§3b): eight pairs at NMI/V 0.57–0.86 (e.g.
  post_type↔poster_role 0.86, drug_mentions↔medical_procedure_types 0.85,
  cause_attribution↔condition 0.72). These NMI clusters are the empirical basis for the
  7-group prompt split (§4c / §3c).
- **Genuinely independent** (§3c): seven low-correlation fields safe to extract solo.

Methodology note: this NMI / Cramér's V feature-correlation toolkit is itself a statistical
mechanism spp does **not** currently provide (it lives only in the audit, not in any spp
loop artifact).

### 2c. Default-attractor problem + gated-boolean fix

`FEATURE_AUDIT.md` Pattern A (§2, L28–40): a single catch-all label dominates output on
**5 fields**, "drowning out 5–6 valid alternatives." The attractors (abstracted by role:
each is a "not-addressed / not-specified / no-X-discussed / safe-default" vocab item)
hallucinate 7–32× per field while real labels are lost. The schema confirms 7 fields carry
a `default` key; 5 of those are the Pattern-A culprits.

The structural reading (§2 L40): "The label set is doing double duty and the model picks
the safe option." Fix — **gated boolean** (`AUDIT_PATH.md` §2b, L53–65): replace each
attractor field with **(boolean `is-addressed` gate) + (multi-label only when true)**.
"the model's 'I'm unsure' answer routes to the boolean=false branch instead of corrupting
the multi-label answer." This is realized in `schema_v2.json` as `gate_field` on 5 fields
and `output_form: gated_per_label_binary` / `gated_single_select` — i.e. the audit's
proposed fix is already baked into v2/v3. `AUDIT_PATH.md` §3d gives a full gated-group
prompt template (Group D etiology: Step-1 boolean gates → Step-2 conditional per-label
binary → post-process to empty list when gate=false).

### 2d. Feature-group splitting / monolithic-vs-batched

`AUDIT_PATH.md` §3c (L140–154) and `FEATURE_AUDIT.md` §4c (L129–141): split the surviving
fields into **7 focused group prompts** (A speech-act, B affect, C journey, D etiology,
E treatment-enumeration, F treatment-attitude, G context), each owning a disjoint field
subset, grouped by the NMI clusters above. "~7× API calls but ~1/3 token-budget each …
net accuracy gain estimated +0.06–0.10 on composite" (`AUDIT_PATH.md` L154). Pattern B
(cardinality collapse, §2 L42–56) motivates converting **6 multi-label fields to per-label
binary** ("answer N yes/no questions in one structured call"), §3a — eliminates early
array-closing. The schema reflects this: 8 fields now carry per-label-binary output forms.
Validation gate (`AUDIT_PATH.md` §4): composite 0.702 → target 0.76+, with per-field floors.

---

## Item 3 — The "soft labels" concept (`labelled_features_soft_v3.json`)

**Shape:** top-level list of **50 rows**, each `{post_index:int, post:str,
annotation:dict}`. Each `annotation` has **31 field entries** (matching the schema's 31
fields exactly). Per-field value is a dict with one of three structural signatures:

| signature (subkeys)                          | # fields | meaning |
|----------------------------------------------|---------:|---------|
| `{primary, accepted, reasoning}`             | 11 | scalar/list field with alt-acceptable set + rationale |
| `{primary, accepted_per_label, reasoning}`   | 15 | per-label-binary field: accepted yes/no set per label |
| `{primary, accepted}`                         | 5 | binary/simple field, no rationale |

Value-type scan across all 50 rows (types only, no values):
- `primary` is `str` (550×), `list[str]` (503×), `bool` (200×), or empty list (297×).
- `accepted` is `list[str]` / `list[bool]` / empty — i.e. an **alternative-acceptable
  label set**, never a number.
- `accepted_per_label` is a dict of `label → accepted-value-list`.

**"Soft" here means partial-credit / alternative-acceptable label sets — NOT probabilistic
or continuous targets.** I scanned every value in all 50 rows for any `float`: **zero
floats anywhere.** There are no probabilities, no confidence weights, no soft/continuous
distributions in the ground truth. The structure is: one `primary` (the canonical gold
label or label-set) plus an `accepted` set of other labels that also score as correct, so
soft-Jaccard gives partial credit when a prediction lands in the accepted set rather than
exact-matching the primary.

**Bearing on the continuous-mode direction:** the ground truth is **not** a continuous
target — it is hard categorical labels with a tolerance set. So the asset offers **no
existing continuous regression target**. The continuous demand is purely *latent*: it lives
in (a) the ordinal fields squeezed into categoricals (Item 1 flag), and (b) the discarded
`raw_score` 0–10 the anchored-CoT prompt computes and throws away (Item 2a). A genuine
continuous/ordinal mode would have to *introduce* a numeric target + ordinal-distance metric;
the current soft labels would need a new "ordinal accepted-band" representation to support it.

---

## Item 4 — Monolithic baseline prompt structure vs spp's locked six-section structure

`baseline_feature_annotation_v6_monolithic.md` (953 lines) is **one prompt emitting all 31
fields for one post per call.** Top-level heading skeleton (headings only, no body text):

`# ROLE` → `# TASK` → `# INPUT` → `# ANNOTATION SCHEMA` (with `## Two structural patterns`,
`## Schema`) → `# CONTROLLED VOCABULARY RULES` → `# FIELD-SPECIFIC GUIDANCE` (the bulk:
7 sub-sections **A–G** mirroring the 7 audit groups, each field annotated with its
output_form e.g. "(per-label binary, no cap)", "(gated, single)", "(single, anchored CoT)")
→ `# REASONING APPROACH` → `# FINAL VALIDATION CHECKLIST` → six `# EXAMPLE INPUT/OUTPUT`
pairs (few-shot, ~320 lines).

**Comparison to spp's locked six-section prompt structure:** *different*. spp's structure is
the fixed six-section contract (role / task / definitions / procedure / output-format /
constraints-or-examples-style ordering). This monolithic prompt is a **task-specific
authored layout** organized around the 31-field schema and the A–G feature groups, with a
large few-shot example block — it is not the spp six-section template and was not produced
by an spp loop (it is the hand-authored "monolithic" arm of the monolithic-vs-batched
ablation, per the prior pass `spp-test.md` comparison matrix). It does embed the audit's
fixes inline (anchored-CoT note on intensity, per-label-binary and gated tags on the right
fields, A–G grouping), confirming the audit conclusions were folded back into v6 even in the
monolithic variant. The genuine spp six-section artifacts live elsewhere (the relevance
subtree and the `hair-loss-annotation-v2` subtree), not in this file.

---

## Item 5 — Mapping each audited finding to the three directions

| Audited finding | Direction |
|---|---|
| **Pattern B → per-label binary (OvR)** on 6/8 fields; 8 fields now carry per-label-binary output_form | **(1) prompting techniques** — concrete tested OvR instantiation |
| **Pattern A → gated boolean** ("is-addressed" gate + conditional multi-label) on 5 fields | **(1) prompting techniques** — gated-boolean pattern |
| **Feature-group split** into 7 (→9) disjoint group prompts; monolithic→batched proven Pareto-better | **(1) prompting techniques** — multi-prompt split; also informs the spp feature-group-split principle |
| **Anchored-CoT** for ordinals (raw 0–10 → discrete map) | **(1) prompting technique**, but its benefit is **unmeasurable** under exact-match scoring → couples to **(3)** |
| **NMI / Cramér's V redundancy + cluster analysis** (drop V=1.0, group NMI 0.6–0.9) | **(2) statistical mechanisms** — feature-correlation toolkit absent from spp |
| **No bootstrap/permutation CIs**; decisions gated by informal "Δ > 5× noise floor"; small-N (n=15–20) one-row swings | **(2) statistical mechanisms** — significance layer wanted, not present |
| **GEPA ships train-overfit candidates** (no revert) vs spp revert-on-regression + auditor gate | **(2) statistical mechanisms** (overfitting control) / validates spp design |
| **3 ordinal fields scored as flat categorical**; Pattern C ordinal drift; discarded raw 0–10 score; no MAE/RMSE/ordinal-distance/correlation primitive | **(3) continuous/ordinal modes** — the core live demand signal |
| **Soft labels = alt-acceptable sets, not probabilities**; no continuous target exists | **(3) continuous/ordinal modes** — confirms a continuous target must be *introduced*, not just exposed |
</content>
</invoke>
