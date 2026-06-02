# spp v0.2.0 — structural + methodological inventory

Internal reference for a next-arc planning subagent. Covers the three target
directions: (1) more prompting techniques, (2) more statistical mechanisms,
(3) more supported modes (continuous/regression). All paths absolute. Verbatim
quotes flagged. "Not present" means verified absent, not "didn't look."

## What it is / locked configuration

`spp` (supervised-prompt-producer) is an MIT Claude Code plugin (skill `run`,
invoked `/spp:run <task>`) packaging a human-in-the-loop supervised
prompt-engineering methodology. v0.2.0 tagged (commit `a2872b2`). Locked sets
after v0.2.0 (`/Users/jiafuli/Desktop/Project/spp/STATE-as-of-v0.2.0.md:43-51`):

- **4 phases** (command set closed at four — adding a fifth is a methodology
  change per DESIGN §3): `/spp-init`, `/spp-baseline`, `/spp-loop`,
  `/spp-finalize`. Docs at `skills/run/phases/spp-*.md`.
- **3 agents**: `designer`, `auditor`, `adversary` (`skills/run/agents/`).
- **4 sub-skills** (was 3 in v0.1.0; `schema-designer` added in v0.2):
  `metric-design`, `baseline-quality`, `prompt-architect`, `schema-designer`
  (`skills/run/sub-skills/<name>/SKILL.md`).
- **4 templates**: `plan.md.template`, `loop_spec.md.template`,
  `prompt_v01.md.template`, `REPORT.md.template` (`skills/run/templates/`).

Two-layer framing (`DESIGN.md:458-489`): **methodology** (output-shape-agnostic
principles) vs **bookkeeping** (concrete instantiation). v0.1.0 bookkeeping =
single-output classification; v0.2 generalized bookkeeping to multi-field
structured output / hierarchical labels / freeform extraction with structured
ground truth, via a **seven-bucket additive arc** (see item 9).

CRITICAL reconciliation fact for directions 2 and 3: the v0.2 per-field /
aggregate / floor / MAE / RMSE / IoU machinery is **fully specified in the
phase docs and SKILL docs but NOT implemented in the runnable script**. The
actual runner `eval.py` is still v0.1.0-shape classification only (see item 4).
The K>1 path is "contract-only" by design until the runner is generalized.

---

## 1. The locked six-section prompt structure

Six XML sections, fixed order, non-negotiable. Verbatim names (tags):

1. `<persona>`
2. `<task>`
3. `<rules>`
4. `<output_format>`
5. `<example_input>`
6. `<example_output>`

Plus an **optional model-specific directives header** outside the six-section
body (e.g. `/no_think` for Qwen), model-locked, stripped on migration.

Defined / pinned in:
- `DESIGN.md:323` (§5 sub-skills table, names them) and
  `DESIGN.md:1589-1603` (§7.1.1 locked-invariants entry "Six-section prompt
  structure", "preserved verbatim").
- `/Users/jiafuli/Desktop/Project/spp/skills/run/sub-skills/prompt-architect/SKILL.md`
  — full structural treatment: in-scope list at lines 58-61; per-section walk
  §3 (lines 162-352); the fixed list restated at §5 lines 638-647.
- `/Users/jiafuli/Desktop/Project/spp/skills/run/templates/prompt_v01.md.template`
  — operationalized form; validation rule 2 = six tags in exact order.

Section evolution discipline (`prompt-architect` SKILL §3, "at a glance" table
lines 355-363): `<rules>` is **Constant** (the loop's primary edit surface and
the auditor's review surface); `<persona>`/`<task>`/`<example_input>` are Rare;
`<output_format>` Avoid; `<example_output>` tied to `<example_input>`.

Direction-1 relevance: few-shot (multiple example pairs), chain-of-thought as a
separate section, and tool-use prompts are explicitly **out of scope** and
listed as BREAKING if added (`prompt-architect` SKILL lines 82-99, 661-684,
949-963). Any new prompting technique that changes section count or the
single-example-pair shape is a breaking change against this sub-skill AND the
template validation rules AND REPORT §5 aggregation. CoT is permitted only as a
request inside `<task>` ("explain your reasoning briefly before the label"),
not as a structural section. Sub-task scoping under feature-group splitting
(SKILL §5 lines 704-774) keeps the six sections but scopes them to a sub-task's
fields.

---

## 2. Per-stage information isolation architecture (DESIGN §4.2)

The load-bearing design lock (`DESIGN.md:135-262`). One-liner contract: **every
cognitive stage of a `/spp-loop` iteration runs in an isolated subagent with an
explicit positive allow-list; the orchestrator coordinates and carries state
through files under `runs/<model>/run_NN/`, never doing cognitive work in its
own context.** Iteration order: **edit → score → audit** (adversary slotted
between, when on). CLAUDE.md §8 forbids loosening any of this.

Four isolated subagents per iteration (`DESIGN.md:150-176`; operationalized in
`/Users/jiafuli/Desktop/Project/spp/skills/run/phases/spp-loop.md` §4):

**Discrepancy subagent** — spp-loop.md §4 **step 8** (lines 442-485).
- Sees (allow-list): `runs/<model>/run_N/eval.json`;
  `runs/<model>/run_N/results.json` (per-row predictions, train+dev);
  `data/baseline.csv` filtered to **any-field-disagreed dev row IDs only**
  (reads all field ground-truth + input content for those rows);
  `plan.md` §2 (class defs / OUTPUT_SCHEMA); current `prompt_v(N).md`.
- Forbidden: prior-iteration artifacts (prior `discrepancy_analysis.md`,
  `auditor_review.md`, `prompt_v(M).md`), train rows the model predicted
  correctly, test rows. Persistent artifact references rows by **ID only**;
  row content stays in the terminating context.
- v0.2 shape change: clusters name a **primary field**; rows disagreeing on
  multiple fields appear in multiple clusters; cross-field correlation visible
  to the subagent but cluster boundaries are field-bounded.

**Rule-edit subagent** — spp-loop.md §4 **step 10**.
- Sees: current prompt; `discrepancy_analysis.md` (**row IDs, no row content**);
  `plan.md` §2; the `prompt-architect` sub-skill.
- Forbidden: `baseline.csv`, `eval.json`, `results.json`, prior-iteration
  artifacts. **No row content reaches it under any path** — this is the
  property the step exists to enforce (`DESIGN.md:160-165`; CLAUDE.md §8).

**Auditor subagent** — spp-loop.md §4 **step 11**; agent doc
`/Users/jiafuli/Desktop/Project/spp/skills/run/agents/auditor.md` §2.
- Sees: prompt diff (`prompt_v(N-1).md` + `prompt_v(N).md` or structured diff);
  prior iteration's `discrepancy_analysis.md`; `plan.md` §2; **all prior**
  `auditor_review.md` files (M<N, for cross-iteration contradiction check).
- Forbidden — **score-blindness is the most stringent allow-list**: the new
  iteration's `eval.json` / `results.json` (which exist on disk by audit time,
  since order is edit→score→audit), any score-derived hint or boolean
  `metric_improved` indicator, train/test labels, the sacred test set, and
  iteration history before N-1 (raw prior discrepancy / eval). auditor.md §2
  enumerates 5 operational enforcement guarantees the runner must satisfy
  (allow-list-not-deny-list; no score artifacts; stateless across iterations;
  no score-derived hints; test-set out of scope). The §2 warning paragraph is
  lifted **verbatim** from DESIGN §4.2 and must not be paraphrased.

**Adversary subagent** — spp-loop.md §4 **step 9**; agent doc
`skills/run/agents/adversary.md`. Opt-in via `plan.md` (`ADVERSARY_FLAG`).
- Sees: current prompt; prior iteration's discrepancy; `plan.md` §2.
- Forbidden: scores, sacred test set, baseline rows.
- **Score-blindness + non-persistence** guarantees (`DESIGN.md:269-304`):
  synthetic rows are surfaced inline for one iteration and are **never**
  written to `runs/`, `baseline.csv`, `splits.json`, or REPORT. v0.2 shape
  change: synthetic rows now carry full OUTPUT_SCHEMA-shaped ground truth (one
  value per field; K=1 collapses to a single "label").

Runner-level enforcement: `loop_spec.md` literal blocks §3 (per-stage isolation:
`auditor: per-iteration` / `score_access: forbidden` /
`frequency_reduction: forbidden`), §4 (adversary boundaries), §7 (sacred-test
posture); the runner refuses to operate if these blocks are hand-edited
(spp-loop.md §3 pre-condition 4).

---

## 3. The auditor's categorical-vs-row-specific judgment

What it decides (`DESIGN.md:212-225`; auditor.md §4 lines 342-483). The single
question, asked **once per proposed edit per target field** under v0.2:

> For target field `f`, is this rule edit categorical (addresses a class of
> rows defined by an articulable property for field `f`'s prediction) or
> row-specific (patches one weird row's `f`-field disagreement)?

Concrete test: generate 5 synthetic rows satisfying the rule's plain-English
condition (without using the baseline as a template); does the predicted value
apply to all 5? Yes → `categorical`; only the original row matches → `row-specific`.

Output shape (auditor.md §6 lines 522-619):
- **A verdict per `(edit, target_field)` combination** — hard token, one of
  `categorical` / `row-specific` / `unclear`. NOT probabilistic, NOT
  confidence-weighted, no `auditor_confidence` field (adding any is BREAKING).
- Recommendations: `categorical`→`keep`; `row-specific`→`revert` or
  `generalize` (names the categorical rule next iteration should produce — a
  hint, not a rewrite); `unclear`→`clarify` (a specific question).
- v0.2: a diff of 3 edits × 2 target fields = **6 verdicts**; an edit can be
  `categorical` for field A and `row-specific` for field B. K=1 collapses to
  one verdict per edit (= v0.1.0 shape).
- Persistent artifact `runs/<model>/run_N/auditor_review.md`: header, one
  section per edit (quoted edit + `target_fields` list + per-field sub-sections
  with verdict/reasoning/recommendation), plus a cross-iteration check section.

Gate enforcement: spp-loop.md §4 **step 12** — runner advances only on **all
non-categorical (edit, field) combinations** being overridden in `plan.md` §11
via an entry whose Reason carries literal substring `auditor override`, with
v0.2 bracketed tokens `[edit-N.field-name]` (case-sensitive field match;
substring match whitespace-stripped, case-insensitive on `auditor override`;
fuzzy matching forbidden). K=1: unscoped `auditor override` covers the lone
field. The auditor never sees scores — the right escape valve for cost is
**batch auditing**, never score access or frequency reduction (DESIGN §4.2
lines 253-262; §7.1.3 non-goal).

---

## 4. The metric layer — and the statistics gap

Where metrics are defined:
- `/Users/jiafuli/Desktop/Project/spp/skills/run/sub-skills/metric-design/SKILL.md`
  — the consultative metric-selection sub-skill (read by designer in
  `/spp-init`). Three-stage v0.2 protocol (§3): (1) per-field metric selection
  decision tree §3.1; (2) aggregate-strategy consultation §3.2; (3) per-field
  floor consultation §3.3. **Review-and-record, no verdict gate** (the only
  verdict-gated sub-skill in v0.2 is `schema-designer`).
- `plan.md` §3 (headline criterion = aggregate metric target + optional
  per-field floors) and §4 (per-field `METRIC_NAME[f]` / `METRIC_RATIONALE[f]`
  / `METRIC_INDEPENDENCE_NOTE[f]`, `AGGREGATE_STRATEGY`, `AGGREGATE_WEIGHTS`,
  `FLOOR[f]`).
- `/spp-finalize` reads these and emits the REPORT (item 5).

Metric primitives **assumed / enumerated** (metric-design SKILL §2 lines
115-123, §3.1 type table lines 200-207, §6 list lines 832-844):
`F1`, `balanced_accuracy`, `macro_F1`, `precision_at_recall`,
`recall_at_precision`, `MAE`, `RMSE`, `exact_match`, `set_F1`, `IoU`, `custom`.
Type→metric suggestions: enum→F1/macro_F1; string→exact_match;
number→MAE/RMSE; boolean→F1; array→set_F1/IoU; nested→recurse.
Aggregate strategies: `macro` / `weighted` / `min` (must refuse a dimensionally
nonsense aggregate, e.g. macro-averaging F1 with MAE — `revise` signal,
documentary not gate-blocking).

**What the runnable script actually supports today (the reconciliation fact):**
`/Users/jiafuli/Desktop/Project/spp/skills/run/scripts/eval.py:32`:

    SUPPORTED_METRICS = {"f1", "accuracy", "precision", "recall"}

`compute_eval()` (eval.py:50-191) takes a single `metric` string, a
`label_column`, and a `label_space`, computes one classification metric over
canonicalized string labels (binary needs `positive_label`; multi-class uses
`average="macro"`). It does NOT compute per-field metrics, aggregate strategies,
floors, MAE/RMSE/exact_match/set_F1/IoU, or the v0.2 three-section `eval.json`
(`per_field` / `aggregate` / `floor_compliance`). Those three sections are
specified in prose at spp-loop.md §4 step 7 (lines 386-440) and DESIGN §7.1.1
metrics layer, but the runner script is still v0.1.0 classification. scripts
README documents the example as "Eval (binary F1)". **Directions 2 and 3 both
land squarely on this gap: regression/continuous output needs MAE/RMSE actually
implemented, and any statistical mechanism needs row-level score plumbing that
does not exist yet.**

**Statistical-significance machinery — NOT PRESENT.** Verified by grep across
`eval.py` and the phase docs: no bootstrap, no confidence intervals, no paired
permutation tests, no significance testing anywhere in the codebase. Metrics
are point estimates only. The STATE doc logs this as a forwarded v1.0 gap.
Verbatim (`/Users/jiafuli/Desktop/Project/spp/STATE-as-of-v0.2.0.md:107`,
under "Methodology gaps surfaced by the spp-ex run"):

> 4. **No bootstrap CIs / paired permutation tests** on row-level scores. Same
> limit as the prior `spp_compare`. Cheap to add at finalize.

Surrounding context: items 1-5 of that section list highest-leverage gaps —
(1) compound-system bookkeeping contract-only; (2) per-field auditor verdicts
not exercised on PUPA; (3) a documented process-isolated-auditor deviation in
the spp-ex run; (4) the bootstrap/permutation gap above; (5) single-task
external validity. The same doc, "Path forward" item references, frames CIs as
a small finalize-level addition.

REPORT currently emits a `TRAIN_DEV_AGGREGATE_DELTA` (train-minus-dev, the
overfitting-guard surface) but no interval/significance number (item 5).

---

## 5. The sacred test set discipline ("read exactly once")

Definition: `DESIGN.md:2234-2238` (§10 glossary) — held-out partition not
touched until Phase 3; loop sees train+dev only; touching it mid-loop voids the
methodology's claim. Locked-invariant entry "Test rows untouched until
/spp-finalize; read exactly once" at `DESIGN.md:1454-1477` ("preserved
verbatim").

Where enforced:
- `/Users/jiafuli/Desktop/Project/spp/skills/run/phases/spp-loop.md` §3
  pre-condition 7 + §4 step 7 lines 386-387: "Test rows are not scored, not
  predicted on, not in the eval surface in any way." Auditor/adversary also
  blocked from test data (defense in depth).
- `/Users/jiafuli/Desktop/Project/spp/skills/run/phases/spp-finalize.md` §3
  pre-condition 8 + §4 step 3: the **single** sacred read. Re-finalization is
  refused if `REPORT.md` already exists (would imply a second read); the user
  must manually delete `REPORT.md` / `test_results.json` / `test_eval.json` and
  record a §11 entry to repeat. Resumption carve-outs distinguish a halted-but-
  already-read state from a fresh read.
- Runner defense-in-depth: `loop_spec.md` §7 literal block
  `test_set_access_during_loop: forbidden` / `test_set_first_use: /spp-finalize
  only`; `plan.md` validation rule 7 `SACRED_TEST_ACK == "acknowledged"`.

What lands in REPORT vs dev: REPORT §2.1 test column is **the sacred set's
first and only evaluation**, filled by `/spp-finalize` (not `/spp-loop`); dev
and train columns come from the final loop iteration. Loop trajectory (REPORT
§3) is dev-only. Artifacts: `test_results.json`, `test_eval.json`, `REPORT.md`,
`PROMPT_FROZEN_v01.md` under `runs/<model_identifier>/`.

One v0.2 exception to "advances only on SUCCESS": `early_stop_floor_unmet`
EARLY_STOP variant advances (gated on a user-confirmation prompt that surfaces
unmet floors before the sacred read); all other EARLY_STOP variants and
FAILED.md still refuse (DESIGN §7.1.1 lines 1725-1746; finalize §3
pre-condition 6).

---

## 6. The output space and the "fixed output space" non-goal

Output shapes supported today (the v0.2 bookkeeping): single-output
classification (binary / multi-class / fixed-schema), and — at contract level —
multi-field structured output, hierarchical labels (JSON Schema if/then/else),
and freeform extraction with structured ground truth. Schema language pinned:
**JSON Schema draft 2020-12** (`DESIGN.md:566-577`), surface YAML or JSON.
(Caveat per item 4: K>1 multi-field is contract-only — the runner can't yet
score it.)

Explicitly out of scope, framed around the fixed-output-space requirement.
Verbatim, `DESIGN.md:2026-2036` (§7.1.3 first bullet, "Generation-task
methodologies"):

> Free-form text generation (summarization, rewriting, instruction tuning,
> multi-turn conversation) does not have ground truth in the way classification
> provides — the output space is unbounded and there is no "correct label"
> against which to compute a metric. The methodology's validation primitives
> (sacred test set, F1 / balanced-accuracy / per-class metrics, auditor's
> categorical-vs-row-specific judgment on rule edits) all assume a fixed output
> space. Generation tasks need a different methodology that handles bounded
> reference sets, multiple acceptable outputs, and qualitative judgment under
> uncertainty.

Direction-3 note: "continuous/regression" is NOT itself listed as a deliberate
non-goal. The methodology already names `number` fields with `MAE`/`RMSE`
metrics (metric-design SKILL §3.1) — a numeric field has a fixed, ground-truth-
comparable output space, so it sits inside the "fixed output space" boundary,
not outside it. The blocker is implementation (eval.py supports only
classification metrics), not a methodology prohibition. The non-goal above bites
only on **unbounded generation**, which a regression target is not.

---

## 7. The §7.1.1 locked-invariants inventory (backbone of the impact table)

`DESIGN.md:1331-1847`. Audit subsection: each entry names invariant, canonical
reference, what it guarantees, verification status (preserved verbatim / with
shape change), and BREAKING CHANGE triggers. Removing or weakening any entry is
itself BREAKING per CLAUDE.md §4. Full list (grouped as in the doc):

**Per-stage information isolation**
- **Per-stage isolated subagents** — ref DESIGN §4.2. Status: preserved with
  shape change (v0.2 multi-field-aware allow-lists). Triggers: spp-loop.md +
  auditor.md Versioning. (`DESIGN.md:1358-1378`)
- **Auditor's score-access prohibition** — ref DESIGN §4.2 + CLAUDE §8 +
  auditor.md §2. Status: preserved verbatim. (`:1380-1394`)
- **No row content to rule-edit subagent** — ref DESIGN §4.2 + spp-loop.md §4
  step 10 + CLAUDE §8. Status: preserved verbatim. (`:1396-1412`)
- **Auditor frequency: per-iteration, non-optional** — ref DESIGN §4.2 + CLAUDE
  §8 + plan.md.template §8 (`AUDITOR_CONFIG == per-iteration, no-score-access`)
  + loop_spec.md.template §3 (`auditor_frequency_reduction: forbidden`). Status:
  preserved verbatim. (`:1414-1429`)
- **Adversary score-blindness and non-persistence** — ref DESIGN §4.3 +
  adversary.md §2/§6 + spp-loop.md §4 step 9 + loop_spec.md.template §4. Status:
  preserved with shape change (full OUTPUT_SCHEMA-shaped synthetic ground
  truth). (`:1431-1450`)

**Sacred test set**
- **Test rows untouched until /spp-finalize; read exactly once** — ref DESIGN
  §10 + finalize §3 pre-cond 8 + loop §3 pre-cond 7. Preserved verbatim.
  (`:1454-1477`)
- **Runner-side defense-in-depth on the test partition** — ref loop §3 pre-cond
  7 + loop §4 step 2 + finalize §3 pre-conds 4,8. Preserved verbatim.
  (`:1479-1491`)

**Verdict-enforced gates**
- **Auditor verdict gate with literal `auditor override` substring** — ref loop
  §4 step 12 + auditor.md §6/§2. Preserved with shape change (per-edit-per-field
  `[edit-N.field]` tokens; K=1 unscoped). (`:1496-1515`)
- **Baseline-quality verdict precondition to G2 with literal `not-ready
  override`** — ref baseline-quality SKILL §6 + baseline §5. Preserved with
  shape change (per-field calibration, any-not-ready-dominates consolidation).
  (`:1517-1537`)
- **Schema-designer verdict precondition to G1 with literal `schema-not-ready
  override`** — ref schema-designer SKILL §6 + init §4 step 9/§5. **Introduced
  in v0.2** (buckets 1+4); preserved verbatim since. Dual check folds into G1,
  no renumbering. (`:1539-1567`)
- **HITL gate G1–G6 literal-string approval substrings** — ref DESIGN §10 +
  plan.md.template §9 + each phase's gate enforcement. Preserved verbatim.
  (`:1569-1585`)

**Methodology-as-substance**
- **Six-section prompt structure** — ref DESIGN §5 + prompt-architect SKILL +
  prompt_v01.md.template. Preserved verbatim. (`:1589-1603`)
- **Metric independence rule** — ref DESIGN §5 + metric-design SKILL §5.
  Preserved with shape change (per-field application). (`:1605-1619`)
- **Verdict tokens are categorical hard tokens — no confidence weighting** —
  ref auditor.md §6 + baseline-quality SKILL §6 + schema-designer SKILL §6.
  Preserved verbatim. (`:1621-1642`)
- **plan.md as contract; re-read fresh by every phase; mid-task changes via §11
  revision log** — ref DESIGN §10 + each phase pre-conds + plan.md.template §11.
  Preserved with shape change (v0.2 manual-upgrade steps; K=1 auto-promote at
  read, no silent rewrite). (`:1644-1663`)

**Operational-load-bearing**
- **Atomic checkpoint writes (`tmp + fsync + rename`)** — ref all four phase
  docs. Preserved verbatim. Documentation finding: lacks an explicit BREAKING
  CHANGE bullet. (`:1667-1686`)
- **`MODEL_IDENTIFIER` exact env-var string, no aliasing** — ref DESIGN §2.2 +
  plan.md.template §5 + loop_spec.md.template §5 + `runs/<model_identifier>/`
  naming. Preserved verbatim. (`:1688-1704`)
- **`loop_spec.md` literal-block check at loop + finalize pre-conditions** — ref
  loop_spec.md.template §3/§4/§7 + loop §3 pre-cond 4 + finalize §3 pre-cond 4.
  Preserved verbatim. (`:1706-1723`)
- **/spp-finalize advances only on SUCCESS.md (with one v0.2 deliberate
  exception, `early_stop_floor_unmet`)** — ref finalize §3 pre-cond 6. Preserved
  with shape change. (`:1725-1746`)
- **v1 command set is closed at four** — ref finalize "Pattern observations".
  Preserved verbatim. (`:1748-1759`)

**REPORT invariant block**
- **REPORT.md.template §5 invariant block stays verbatim** — ref
  REPORT.md.template §5 lines 292-296 (the literal "Per-stage
  information-isolation invariants: preserved." header + four subagent
  sub-statements). Preserved verbatim. (`:1763-1780`)

**Documentation findings** (`:1782-1827`): (1) atomic-checkpoint lacks an
explicit BREAKING CHANGE bullet; (2) the finalize Versioning bullet forbidding
advancement on EARLY_STOP wasn't updated for the deliberate
`early_stop_floor_unmet` carve-out. Both flagged as known gaps, not violations.

The inventory is **non-exhaustive** (load-bearing commitments only). Adding an
invariant = doc update; removing/weakening = BREAKING.

---

## 8. §7.1.2 (further-out roadmap) and §7.1.3 (deliberate non-goals)

**§7.1.2 — Further-out roadmap** (`DESIGN.md:1990-2017`). Roadmap, not
boundaries; v0.x will reach these:
- **Multi-judge subjective metrics** (ground truth itself needs LLM judgment —
  style, tone, helpfulness). Roadmap **v0.3**. Forbidden today by the
  metric-design independence rule.
- **Multilingual data** (v0.1.0 assumes English). Roadmap **v0.3**, separate
  design pass.
- **Cross-model synthesis** (v1 produces per-model REPORTs; users synthesize
  manually). Roadmap **v0.4**.
- **Loop resumption mid-iteration** (iteration is the unit; interrupted
  iterations discarded and re-run). Roadmap **TBD** — needs per-step
  checkpointing without weakening per-stage isolation.

**§7.1.3 — Deliberate non-goals** (`DESIGN.md:2019-2090`). Scope boundaries the
methodology will not cross (a different methodology, not a generalization):
- **Generation-task methodologies** (unbounded output, no fixed label — see
  item 6 verbatim quote).
- **Tool-use and agentic prompts** (orchestration problem, not prompt-quality).
- **RAG prompts** (jointly retrieval+prompt; would couple two failure
  surfaces).
- **Prompt-injection defense / jailbreak resistance** (different evaluation
  primitives; red-teaming).
- **Automated prompt search (DSPy / GEPA / APE composition)** — incompatible by
  construction: fusing proposal and selection violates per-stage isolation. PRs
  should propose *composition* (spp produces a starting prompt, an optimizer
  runs downstream), never *fusion*.
- **Auditor frequency reduction** — the post-v1 fix is batch auditing, never
  "audit every N iterations."
- **LLM-as-judge metrics for v0.1.0's independence rule** — v1 forbids any LLM
  judge (the v0.3 multi-judge work reopens only the ground-truth-needs-judgment
  case).

Guidance (`:2086-2090`): "When in doubt, lean toward roadmap rather than
deliberate." Directions 2 (statistics) and 3 (continuous/regression) are NOT on
either list explicitly — they are new bookkeeping/implementation work inside the
existing fixed-output-space methodology, closest in spirit to the v0.2
seven-bucket precedent.

---

## 9. The arc-opening convention ("PR #19 §7.1.1 pin" + the seven-bucket pattern)

Documented in `/Users/jiafuli/Desktop/Project/spp/STATE-as-of-v0.2.0.md`
(the git log only shows squash-merge commits up to the release tags — the v0.2
PRs #19-#29 were squashed into the dev→main release merge `a2872b2`, so the PR
narrative lives in the STATE doc and DESIGN §7.1.1, not in `git log`).

**The §7.x "pin" draft convention** (STATE doc lines 22-41, 154):
- An arc opens with a **`docs(design)` PR that pins the design in DESIGN.md
  before any code changes.** v0.2 opened with **PR #19 —
  `docs(design): pin v0.2 schema-layer design`**, which expanded DESIGN §7.1.1
  from "a flat six-bullet sketch into 'Bookkeeping changes by layer'" (bucket 1
  of 7). The pin establishes OUTPUT_SCHEMA's home, the schema language, and
  declares the six-section structure preserved — i.e. it locks contracts and an
  invariant inventory frame, deferring the file edits to later PRs.
- The STATE doc's explicit next-arc instruction (line 154): "**v1.0 design PR?**
  Start with `docs(design): pin v1.0 compound-system bookkeeping`, parallel
  structure to PR #19. Bucket out into ~7 PRs again."

**The ~seven-bucket PR plan pattern** (STATE doc lines 22-41; DESIGN §7.1.1
"Bookkeeping changes by layer" lines 501-548). The generalization is partitioned
into seven layers, **each locked in its own PR before downstream layers depend
on it**, and the structure is **intentionally additive** (each bucket slots in
without disturbing prior buckets). v0.2's seven buckets:
1. Schema layer (OUTPUT_SCHEMA, schema-designer placement)
2. Metrics layer (per-field metrics, aggregate strategies, per-field floors)
3. Per-field methodology application (discrepancy clustering, auditor verdicts,
   REPORT trajectories)
4. Sub-skill ordering (schema-designer at G1; gates unchanged)
5. Compat layer (K=1 backward compat + manual migration; no new command)
6. Locked-invariants inventory (preservation audit — item 7)
7. Fixtures layer (`multi-field-extraction/`, `nested-schema/` examples)

Recurring motif inside each bucket: "ships standalone before integration" / a
K=1 backward-compatibility fallback, and a closing locked-invariants /
versioning treatment. Bucket 6 (the inventory) is the artifact that makes
"what's preserved across releases" auditable and is the template for the
downstream impact table.

---

## 10. v0.2 feature-group prompt splitting (reconcile, don't duplicate)

This is the existing v0.2 feature that a proposed "multi-prompt split" would
overlap. Precise locations:

- **Methodology definition:** `DESIGN.md:2292-2334` (§10 glossary, "Feature-group
  prompt splitting"). When a task's OUTPUT_SCHEMA spans multiple **feature
  groups** (subsets of fields sharing a reasoning pattern, input dependency, or
  metric profile), the methodology **defaults to one prompt per group, each in
  its own `spp/` task directory**. Buys: focused `<rules>` per prompt; per-group
  metric optimization headroom; clean auditor scoping (one edit = one prompt =
  one field set); cross-task reusability. Exception (keep unified): K=1, or
  dense field interdependencies / shared input / hierarchical conditional
  reasoning that lives best in one prompt.
- **Consultation step:** designer surfaces the grouping decision at
  `skills/run/agents/designer.md` **§5.0**, *before* the K=1-vs-K>1
  OUTPUT_SCHEMA decision. "Keep unified" is recorded in `plan.md` §10
  open-questions with rationale.
- **Hard scope boundary:** **cross-task composition is out of `spp`'s scope.**
  `spp`'s contract stays "one `spp/` task = one prompt = one optimization loop."
  Split tasks are tracked by the *user* (naming conventions, parent dirs, their
  production-pipeline composition logic), NOT by `spp`. There is no
  orchestration/composition layer inside `spp`, by design.
- **Sub-task scoping discipline:** `prompt-architect` SKILL §5 lines 704-774 —
  the six sections scope to the sub-task's K' fields (K' ≤ K); cross-group rules
  go to the user's production layer, not into any prompt.
- **Canonical example:** `/Users/jiafuli/Desktop/Project/spp/examples/feature-group-split/`
  (README + walkthrough.md + three `sub-tasks/{sentiment,topic,urgency}/`, each
  a complete K=1 `spp/` task). Added post-bucket-7 as the principle's **default
  case**. Granularity guidance (README "A note on granularity"): big gains on
  the first split (monolithic → feature-group), diminishing returns on further
  subdivision (feature-group → per-class) — split natural groups with distinct
  reasoning patterns, not maximally.
- **The exception-case examples:** `examples/multi-field-extraction/` (K=4 mixed
  types, `min` aggregate, floor on `category`) and `examples/nested-schema/`
  (hierarchical labels via JSON Schema conditionals) — unified multi-field tasks
  where splitting does NOT apply. (DESIGN §6 lines 360-408; §7.1.1 fixtures
  layer.)

Reconciliation note for the planner: the STATE doc's spp-ex run used "two
separate task directories (`papillon-craft/`, `papillon-respond/`) per the v0.2
feature-group-split workaround" for a **compound 2-module pipeline**, and flags
that **per-module composite reconciliation was stitched at finalize manually**.
The forwarded v1.0 direction (STATE lines 104, 115, 118) is to formalize
**compound-system bookkeeping** as first-class (a possible
`compound-system-designer` sub-skill, `PIPELINE_SCHEMA`, per-module auditor
verdicts/REPORT trajectories, a cross-module auditor isolation invariant) —
i.e. a *first-class* version of what feature-group splitting does today as a
user-owned workaround. A "multi-prompt split" proposal should reconcile against
both: the existing user-owned feature-group split (composition out of scope) and
the proposed first-class compound-system bookkeeping.

---

## Provenance notes

- DESIGN.md read in full (2339 lines); §7.1.1 / §7.1.2 / §7.1.3 / §10 quoted
  directly. CLAUDE.md §8 hard rules cross-checked against the isolation claims.
- STATE-as-of-v0.2.0.md is a transcript summary, not a spec; the seven-bucket /
  PR-#19-pin convention and the bootstrap/CI gap are quoted from it directly.
  STATE-as-of-v0.1.0.md is referenced by the v0.2 doc but is **not present** on
  disk (only `STATE-as-of-v0.2.0.md` exists).
- The runner-vs-spec gap (item 4) was verified by reading
  `skills/run/scripts/eval.py` directly — `SUPPORTED_METRICS` is classification
  only; the v0.2 per-field/aggregate/floor `eval.json` shape exists in prose
  (spp-loop.md §4 step 7, metric-design SKILL, DESIGN §7.1.1) but not in code.
  Other scripts present: `inference.py`, `split.py`, `discrepancy.py`,
  `_io.py`, `_schemas.py`, with pytest tests under `scripts/tests/`.
- Git log shows squash-merged PRs #1-#18 (v0.1.0) and the v0.2.0 release commit
  `a2872b2 (#30)`; intermediate v0.2 PRs (#19-#29) are not individually visible
  in `git log --oneline` because v0.2 was squashed into the release merge — the
  PR narrative is in the STATE doc.
- No statistical-significance code anywhere (grep-verified: no bootstrap,
  permutation, confidence-interval terms in eval.py or phase docs).
