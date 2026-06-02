# spp skill implementation — deep detail (planner must-not-break reference)

Companion to `../spp-repo.md`. This pass reads the actual prompts, allow-lists, and
metric code under `skills/run/`. All paths absolute. Allow-lists and the metric-support
code line are quoted verbatim with `file:line`. The headline reconciliation fact: the
v0.2 per-field / aggregate / floor / MAE / RMSE / IoU machinery is fully specified in
prose but the runnable scripts (`eval.py`, `_schemas.py`, `inference.py`) are still
v0.1.0 single-field classification. K>1 is contract-only.

---

## 1. The four /spp-loop cognitive-stage allow-lists (step numbers confirmed)

Step numbers verified against
`/Users/jiafuli/Desktop/Project/spp/skills/run/phases/spp-loop.md` §4: discrepancy =
**step 8** (lines 442-545), adversary = **step 9** (lines 547-593, conditional),
rule-edit = **step 10** (lines 595-638), auditor = **step 11** (lines 640-713), verdict
gate = step 12 (lines 715-809). Iteration ordering inside an iteration is **edit → score
→ audit** (eval.json/results.json exist on disk before the auditor runs — this is why
score-blindness must be *positively* enforced).

The runner-level literal enforcement block is
`/Users/jiafuli/Desktop/Project/spp/skills/run/templates/loop_spec.md.template:74-82`
(nine lines, hand-edit = hard refusal at spp-loop §3 pre-condition 4 / spp-finalize §3
pre-condition 4):

```
discrepancy_subagent: per-iteration
discrepancy_score_access: forbidden
discrepancy_prior_iteration_access: forbidden
rule_edit_subagent: per-iteration
rule_edit_baseline_access: forbidden
rule_edit_score_access: forbidden
auditor: per-iteration
auditor_score_access: forbidden
auditor_frequency_reduction: forbidden
```

Sacred-test block at `loop_spec.md.template:221-222`:
`test_set_access_during_loop: forbidden` / `test_set_first_use: /spp-finalize only`.

### Discrepancy subagent — step 8 (spp-loop.md:442-545)

Allow-list, verbatim (`spp-loop.md:452-485`):

> - `runs/<model_identifier>/run_N/eval.json` — metric movement, per-field metrics,
>   aggregate, and per-class statistics. […]
> - `runs/<model_identifier>/run_N/results.json` — per-row predictions on train + dev.
>   […]
> - `data/baseline.csv` filtered to **disagreed dev row IDs only** — the subagent reads
>   all field ground-truth values and input content for the rows that drove the
>   discrepancy. The disagreed-row filter is **any-field-disagreed** […] a row enters the
>   filtered set if any field's prediction does not match ground truth on dev. Train rows,
>   test rows, and dev rows where every field's prediction matched ground truth are not in
>   scope.
> - `plan.md` §2 — class definitions and OUTPUT_SCHEMA (or LABEL_SPACE under the K=1
>   fallback) […]
> - `runs/<model_identifier>/run_N/prompt_v(N).md` — the current prompt […]

Prohibitions, verbatim (`spp-loop.md:487-492`):

> **The subagent does NOT receive:** prior iterations' `discrepancy_analysis.md` files,
> prior `auditor_review.md` files, prior `prompt_v(M).md` for `M < N`, train rows that the
> model predicted correctly, test rows of any partition, any artifact not enumerated above.

Output contract: persistent artifact references rows **by ID only**; row content stays in
the terminating subagent context (`spp-loop.md:494-499, 541-545`). v0.2 shape: clusters
carry a `primary field` and each proposed edit carries `target_fields` (the list the
auditor's per-field verdict scoping consumes), `spp-loop.md:526-539`.

### Adversary subagent — step 9 (spp-loop.md:547-593; agent doc agents/adversary.md)

Allow-list, verbatim (`spp-loop.md:551-555`):

> - Allow-list inputs: `runs/<model_identifier>/run_N/prompt_v(N).md`,
>   `runs/<model_identifier>/run_(N-1)/discrepancy_analysis.md`, and `plan.md` §2 only. No
>   baseline rows, no splits, no eval artifacts.

First-iteration carve-out (`spp-loop.md:555-567`): for N=1 no prior
`discrepancy_analysis.md` exists; the runner passes `prompt_v01.md` + `plan.md` §2 only,
and **does not synthesize a placeholder**. Agent-doc enforcement at
`agents/adversary.md:340-346`: allow-list = `run_N/prompt_v(N).md`,
`run_(N-1)/discrepancy_analysis.md`, plan §2; explicitly `no data/baseline.csv, no
run_N/eval.json, no run_N/results.json, no data/splits.json`. Guarantees: score-blindness
(`spp-loop.md:568-570`), **non-persistence** — output appended inline to the iteration's
`discrepancy_analysis.md` under the literal header line (`adversary.md:238`):
`Adversarial rows — generated for iteration N. Not persisted, not added to baseline, not
promoted to splits.` Never written to a separate file / `baseline.csv` / `splits.json`
(`spp-loop.md:573-579`, `adversary.md:310-317`). One invocation per iteration. v0.2 shape:
synthetic rows carry **one ground-truth value per OUTPUT_SCHEMA field** (`adversary.md:261`;
K=1 collapses to a single label).

### Rule-edit subagent — step 10 (spp-loop.md:595-638)

Allow-list, verbatim (`spp-loop.md:609-618`):

> - `runs/<model_identifier>/run_N/prompt_v(N).md` — the prompt to edit.
> - `runs/<model_identifier>/run_N/discrepancy_analysis.md` — proposed edits with row IDs
>   but no row content.
> - `plan.md` §2 — class definitions.
> - The [`prompt-architect`] sub-skill — for structural guidance on which sections accept
>   which kinds of content.

Prohibitions, verbatim (`spp-loop.md:620-626`):

> **The subagent does NOT receive:** `data/baseline.csv`, `eval.json`, `results.json`,
> prior `auditor_review.md` files, any prior iteration's artifacts beyond what's in the
> current `discrepancy_analysis.md`. **No row content reaches this subagent under any
> path** — this is the load-bearing property the per-stage isolation pattern enforces
> beyond the auditor's score isolation.

Output: writes `run_(N+1)/prompt_v(N+1).md` (staged so the auditor's review lands in the
same dir).

### Auditor subagent — step 11 (spp-loop.md:640-713; agent doc agents/auditor.md)

Allow-list, verbatim (`spp-loop.md:651-661`):

> - **Allow-list inputs (positive enforcement, not a deny-list):**
>   `runs/<model_identifier>/run_N/prompt_v(N).md`,
>   `runs/<model_identifier>/run_(N+1)/prompt_v(N+1).md`,
>   `runs/<model_identifier>/run_N/discrepancy_analysis.md`, `plan.md` §2 (extracted as a
>   string slice, not the whole file), and prior `auditor_review.md` files from
>   `runs/<model_identifier>/run_(M)/` for every `M` with `1 ≤ M ≤ N` that exists. The
>   runner builds this list explicitly and passes only the named files […]

Prohibitions, verbatim (`spp-loop.md:662-682`) — five operational guarantees, the most
stringent allow-list in the project: (2) score artifacts withheld even when present —
`run_N/eval.json` and `run_N/results.json` exist on disk but are not in context, "neither
directly nor as derived strings"; (3) stateless across iterations; (4) **no score-derived
hints** — "A 'this iteration's F1 dropped, please scrutinize' hint *is* score signal even
without a number; the runner's hint surface is empty by design"; (5) no test-set
artifacts. The verbatim DESIGN §4.2 warning paragraph is reproduced at
`agents/auditor.md:174-186` ("Do not give the auditor score access. The information
isolation is the design.") — paraphrasing it is itself BREAKING (`auditor.md:773-777`).

---

## 2. The auditor's decision contract

**Judgment** (`agents/auditor.md:343-353`): asked once per `(proposed_edit, target_field)`
under v0.2:

> **For target field `f`, is this rule edit categorical (addresses a class of rows defined
> by an articulable property *for field `f`'s prediction*) or row-specific (patches one
> weird row's `f`-field disagreement)?**

Concrete test (`auditor.md:368-376`): generate 5 synthetic rows satisfying the rule's
plain-English condition **without using the baseline as a template**; if the predicted
value for field `f` applies to all 5 → `categorical`; if only the original row → `row-specific`.
The test runs **once per target field**; K target fields = K independent applications, may
yield K different verdicts.

**Output shape** (`auditor.md:527-545`, §6): one **hard token** per `(edit, target_field)`:
`categorical` (rec `keep`) / `row-specific` (rec `revert` or `generalize`) / `unclear`
(rec `clarify`). NOT probabilistic, NOT confidence-weighted — "There is no
`auditor_confidence` field" (`auditor.md:548-553`); adding any confidence/tier is BREAKING
(`auditor.md:721-728`). A 3-edit × 2-field diff = 6 verdicts; an edit can be categorical
for field A and row-specific for field B (`auditor.md:456-468`). K=1 collapses to one
verdict per edit. `unclear` is load-bearing (removing it is BREAKING, `auditor.md:446-452`).

**Persistent artifact** `run_(N+1)/auditor_review.md` (`auditor.md:555-606`): header; one
section per edit (quoted edit + `target_fields` list + one per-field sub-section each
carrying field name / verdict / reasoning incl. the synthetic-rows test / recommendation
/ generalize-hint or clarify-question); plus a cross-iteration check section
(per-target-field, `auditor.md:595-606`). Atomic checkpoint write.

**Score-blindness enforcement language** — §2 is "the load-bearing section." Key lines:
`auditor.md:138-148` ("The new scores on iteration N. No `dev_f1`, no `recall`, … None of
the contents of `run_N/eval.json` or `run_N/results.json`. … Even if the runner has those
files on disk … they are withheld"). Breaking-change list `auditor.md:711-720` enumerates
that even a boolean `metric_improved` indicator is breaking: "The rule is 'no score signal
at all,' not 'no numerical score.'"

**Gate enforcement** (`spp-loop.md:715-809`, step 12): runner advances only when **every
non-`categorical` `(edit, field)` combination** is overridden in `plan.md` §11 via a Reason
containing literal substring `auditor override` (whitespace-stripped, case-insensitive)
**and**, for K>1, bracketed tokens `[edit-N.field-name]` (field match case-sensitive
verbatim). K=1: unscoped `auditor override` covers the lone field. Override timestamp must
post-date the auditor invocation. Fuzzy matching forbidden. The escape valve for cost is
**batch auditing — never score access, never frequency reduction**
(`loop_spec.md.template:82` `auditor_frequency_reduction: forbidden`).

---

## 3. The metric layer — AS SPECIFIED vs AS IMPLEMENTED

### As specified (metric-design SKILL + spp-loop §4 step 7 + DESIGN §7.1.1 metrics layer)

`/Users/jiafuli/Desktop/Project/spp/skills/run/sub-skills/metric-design/SKILL.md` — three
-stage v0.2 protocol (§3): §3.1 per-field metric selection (decision tree), §3.2
aggregate-strategy consultation, §3.3 per-field-floor consultation. **Review-and-record,
no verdict gate** (`metric-design SKILL.md:164-166, 380-386`; only `schema-designer`
gates in v0.2). Type→metric table (`metric-design SKILL.md:200-207`): `enum`→F1/macro_F1,
`string`→exact_match, `number`→MAE (RMSE if outliers), `boolean`→F1, `array`→set_F1/IoU,
`nested`→recurse. The `METRIC_NAME[f]` enumeration, verbatim
(`metric-design SKILL.md:117-120` and restated `:834-844`):

> `F1`, `balanced_accuracy`, `macro_F1`, `precision_at_recall`, `recall_at_precision`,
> `MAE`, `RMSE`, `exact_match`, `set_F1`, `IoU`, or `custom`.

Aggregate strategies: `macro` / `weighted` / `min` (`metric-design SKILL.md:137-146`);
sub-skill **must refuse a dimensionally nonsense aggregate** (e.g. macro-averaging F1 with
MAE) — a `revise` signal that is **documentary, not gate-blocking** (`:367-386`).
Per-field floors feed `eval.json`'s `floor_compliance` and the finalize
SUCCESS-vs-`early_stop_floor_unmet` discrimination (`:420-435`). spp-loop §4 step 7
(`spp-loop.md:386-440`) specifies the three-section `eval.json`: `per_field` /
`aggregate` (with `strategy` + `weights`) / `floor_compliance`.

**Explicit gap acknowledgement in-doc** (`metric-design SKILL.md:937-960`, "Forward-noted
template change" + "Usability today"): the v0.1.0 scalar `plan.md.template` "has no slots
for per-field collections, an aggregate group, or per-field floors. K = 1 … tasks
continue to function … Multi-field tasks become end-to-end runnable when bucket 5 lands."

### As implemented (the runner) — STILL v0.1.0 CLASSIFICATION ONLY

`/Users/jiafuli/Desktop/Project/spp/skills/run/scripts/eval.py:32`, verbatim:

```python
SUPPORTED_METRICS = {"f1", "accuracy", "precision", "recall"}
```

`compute_eval()` (`eval.py:50-191`) takes a single `metric` string, a single
`label_column` (default `"label"`), and a `label_space`; matches predictions via
`_canonical_label_match` (case-insensitive string compare, `eval.py:39-47`); computes ONE
classification metric (binary needs `metric_kwargs["positive_label"]`; multi-class uses
`average="macro"`). It raises if `metric not in SUPPORTED_METRICS` (`eval.py:63-66`).

- **MAE / RMSE / regression metrics: spec-only, NOT implemented.** No numeric/residual
  path exists in `eval.py`; `exact_match` / `set_F1` / `IoU` likewise absent.
- **No per-field / aggregate / floor computation.** `eval.py` produces one flat metric.
- **The persisted schema is v0.1.0-flat too.**
  `/Users/jiafuli/Desktop/Project/spp/skills/run/scripts/_schemas.py:73-83` `EvalJSON` has
  `metric`, `metric_kwargs`, `primary_value`, `n_rows_evaluated`,
  `n_parse_failures_in_input`, `confusion_matrix`, `labels`, `per_class`,
  `auxiliary_metrics` — there is **no** `per_field` / `aggregate` / `floor_compliance`
  section. The three-section `eval.json` exists only in prose (spp-loop §4 step 7).
- **inference.py is single-field too.** `_parse_response` (`inference.py:72-102`) extracts
  exactly one `"label"` field from JSON (`inference.py:92`: `if isinstance(obj, dict) and
  "label" in obj`) or treats stripped text as the label; `PredictionRow.parsed_label`
  (`_schemas.py:36-43`) is a single `str | None`. No per-field structured prediction object.
- `_schemas.py:1-7` flags the contract: "Schema drift between these models and the docs is
  a methodology-affecting event; surface in a PR description."

### No CI / bootstrap / permutation / significance code — confirmed

grep across `scripts/ phases/ agents/ sub-skills/ templates/ SKILL.md` for
bootstrap|confidence interval|permutation|significance|\bci\b|p-value|stderr|wilson|mcnemar
returned **zero** machinery hits — every "CI" match is fixture prose about GitHub-issue
categorization (build/CI breakage class). Metrics are point estimates only. The only
spread number anywhere is the train-vs-dev / train-vs-test delta (overfitting guard),
which is a difference of point estimates, not an interval. Where regression/CI machinery
would have to be added is listed in §7 below.

---

## 4. /spp-finalize: what it computes, REPORT vs dev, sacred read, where significance slots in

Doc: `/Users/jiafuli/Desktop/Project/spp/skills/run/phases/spp-finalize.md`.

- **Sacred read = §4 step 3** (`spp-finalize.md:412-468`): inference on the test
  partition, input set built by **positive enumeration from `splits.json`
  `row_ids.test`** ("never as 'all rows minus train and dev'"). **Partial-deletion-on-
  failure rule** (`:444-468`): any non-zero exit deletes a partial `test_results.json` so
  the user never "previews" part of the test set; removing the rule is BREAKING.
- **"Read exactly once" enforcement**: §3 pre-condition 8 (`:291-335`) refuses if
  `REPORT.md` already exists; re-finalization requires manual deletion of
  `REPORT.md` / `PROMPT_FROZEN_v01.md` / `test_results.json` / `test_eval.json` **and** a
  §11 entry naming the reason — "deliberate friction." A `--redo` flag or auto-cleanup is
  BREAKING (`:317-322`). Resumption carve-outs (`:324-335`): if `test_eval.json` exists but
  no `REPORT.md`, jump to G5 (no re-read); if `REPORT.md` exists but no `G6 approved` §11
  entry, jump to G6. loop_spec §7 literal block re-checked at pre-condition 4 (`:182-196`).
- **Metrics computed** (§4 step 4, `:470-506`): per-field primary metrics against test
  ground truth, then aggregate per `AGGREGATE_STRATEGY`; persists `test_eval.json` with the
  v0.2 three-section shape **(spec; the runner script does not yet produce it — same gap as
  §3)**. "single test-set evaluation … no 'preview' … no ranged-prediction surface."
- **What lands in REPORT vs dev** (§4 step 7, `:592-803`): REPORT §2 test column =
  `test_eval.json` (the sacred set's first and only eval, written by finalize); dev/train
  come from the best-iteration `run_NN/eval.json`. REPORT §3 loop trajectory is **dev-only**
  (`:638-653`). §5 prompt-edit audit aggregates per-iteration `auditor_review.md` counts
  and emits the **required literal line** "Auditor information-isolation invariant:
  preserved." (`:668-676`). §6 ship decision = deterministic tree (`:683-743`) over
  `test-aggregate ≥ headline criterion`, per-field floor compliance, persistent clusters,
  and `train_test_delta` vs `dev_test_delta × 1.5` / the `0.05` `dev_test_delta` cutoff —
  four values: `ship` / `ship-with-caveats` / `do-not-ship` / `iterate-further`. The
  `0.05` is a hardcoded v1 default (`:727-734`).
- **Where significance testing WOULD slot in**: the ship-decision tree's delta comparisons
  (§6, `:695-725`) are exactly the point estimates a paired bootstrap/permutation test on
  per-row test scores would replace or qualify; the natural home is **step 4 (compute
  test-set metrics) emitting an interval into `test_eval.json`**, surfaced at G5 (`:538-561`)
  and REPORT §2 deltas. STATE doc frames it as "Cheap to add at finalize." No such code or
  prose hook exists today.

EARLY_STOP carve-out: only `early_stop_floor_unmet` may advance to the sacred read (gated
by a user-confirmation prompt, `:216-251`); all other EARLY_STOP variants and FAILED.md
refuse.

---

## 5. Feature-group prompt splitting (as implemented in the skill)

Governing consultation step: **designer.md "Feature-group identification" substep, §5.0**
(`/Users/jiafuli/Desktop/Project/spp/skills/run/agents/designer.md:253-328`), run **after
§3/§4 strawman, before §5.1 task-definition questions and the schema-designer invocation**.
Grouping axes: reasoning pattern, input dependency, metric profile, hierarchical structure
(`designer.md:266-290`). Governing text, verbatim (`designer.md:292-299`):

> **If groups are identified:** the designer recommends decomposing the task into N `spp/`
> task directories — one per group. Each sub-task gets its own `/spp-init`, its own
> `plan.md`, its own optimization loop. The user organizes sub-task directories under a
> parent name (e.g., `spp/products/title-price/`, `spp/products/category-instock/`) but
> `spp` itself does not enforce or track this relationship — composition is the user's
> responsibility at the production-pipeline layer.

So a multi-group task = **N independent `spp/` task dirs, one prompt each, one loop each;
spp tracks none of the cross-task relationship** (composition is out of scope, by design).
The current `/spp-init` proceeds with the **first** sub-task (user picks); the rest need
separate `/spp-init` invocations (`designer.md:301-303`). Skip-condition: only when the
strawman is K=1; for any K>1 the substep runs even to record "keep unified," and the
rationale lands in `plan.md` §10 open-questions (`designer.md:305-323`). Unified
multi-field is the explicit exception (dense field interdependencies / shared input /
hierarchical conditional reasoning), `designer.md:305-317`. Removing the §5.0 substep is
BREAKING (`designer.md:758-763`).

---

## 6. Where OUTPUT_SCHEMA / output_format is defined and supported field types

- **OUTPUT_SCHEMA home**: `plan.md` §2, per
  `/Users/jiafuli/Desktop/Project/spp/skills/run/templates/plan.md.template:24` ("§2 holds
  OUTPUT_SCHEMA + per-field definitions") and the `{{OUTPUT_SCHEMA}}` slot at `:81-91`. It
  is a **JSON Schema (draft 2020-12) document**, YAML or JSON surface
  (`schema-designer SKILL.md:7-8, 71`). K=1 is rendered as the same shape with one
  required enum field — "no shorthand, no `LABEL_SPACE`" (`plan.md.template:87`,
  `schema-designer SKILL.md:88-90`). v0.1.0 `LABEL_SPACE` plans are auto-promoted by the
  runner's K=1 fallback (`plan.md.template:380`).
- **The prompt's `<output_format>` section** is one of the six locked XML sections (the
  prompt structure, `prompt-architect` SKILL). It is the *prompt's* schema declaration to
  the model; the *contract* schema is OUTPUT_SCHEMA in plan §2.
- **Field types supported today (in the OUTPUT_SCHEMA contract / schema-designer
  mechanical layer)**, verbatim list from
  `/Users/jiafuli/Desktop/Project/spp/skills/run/sub-skills/schema-designer/SKILL.md:292-302`:

  > 1. Schema parses as valid JSON Schema (draft 2020-12).
  > 2. Every field has a JSON Schema `type`.
  > 3. Every enum field's values are explicitly enumerated […]
  > 4. Required vs. optional is explicit on every field […]
  > 5. At least one example output validates against the schema […]
  > 6. No `$ref` cycles.
  > 7. No naked `"type": "object"` without either `"properties"` or
  >    `"additionalProperties": false`.

  The accepted JSON Schema field types (from the metric type table and the
  consultative-ready fixture `schema-designer SKILL.md:405-425`): **`enum`,
  `string`, `number`, `boolean`, array of typed values, nested `object`** (with
  `if/then/else` / `oneOf` / `dependentRequired` for relationships, judgment rule 4,
  `:340-346`). So the **contract** supports string/enum/number/boolean/array/nested.
- **But the runner only supports K=1 enum/string classification**: `inference.py` parses a
  single `label`; `eval.py` scores one classification metric over a flat `label_space`;
  `_schemas.py` `PredictionRow.parsed_label` is a lone `str | None`. number/boolean/array/
  nested OUTPUT_SCHEMA fields and multi-field prediction objects are **not scoreable by the
  current scripts** — contract-only until bucket 5.

---

## 7. Planner takeaways — where the three target directions land

- **Direction 2 (statistics)** has no existing surface: zero bootstrap/permutation/CI/
  significance code (grep-confirmed). It needs (a) per-row score retention at finalize
  step 4, and (b) an interval emitted into `test_eval.json` + surfaced at G5 / REPORT §2.
  The auditor must remain score-blind, so any CI is a *finalize-only* artifact — it cannot
  flow into the loop's auditor/adversary contexts.
- **Direction 3 (continuous/regression)** is methodology-permitted (numeric fields with
  MAE/RMSE are already specced in `metric-design`), but blocked at implementation:
  `eval.py:32 SUPPORTED_METRICS = {"f1","accuracy","precision","recall"}` and the flat
  `EvalJSON`/`PredictionRow` schemas have no numeric/residual path. Adding MAE/RMSE means
  extending `SUPPORTED_METRICS`, adding a residual computation path in `compute_eval`, and
  generalizing `_schemas.py` to the three-section `eval.json`.
- **Direction 1 (more prompting techniques)** collides with the locked six-section prompt
  structure and prompt-architect's BREAKING list (covered in `../spp-repo.md` item 1) — not
  re-derived here.
- **Universal constraint**: the four stage allow-lists (§1) and the auditor score-blindness
  (§2) are CLAUDE.md §8 hard locks. Any plumbing that surfaces scores to the auditor, row
  content to the rule-edit subagent, prior-iteration artifacts to the discrepancy subagent,
  or breaks adversary non-persistence/score-blindness is rejected — even accidentally.
