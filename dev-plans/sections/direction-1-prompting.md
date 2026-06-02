## Direction 1 — More prompting techniques

### 1. Summary & motivation

The assets prove one thing cleanly: **prompt decomposition (feature-group split) is the highest-value
prompting lever, and `spp` already ships it.** The monolithic-vs-batched comparison attributes a
**+0.085 composite** gain to the 7-way split — and the cross-config decomposition isolates that the
win is the *split*, not batching (score-neutral) and not flat-canonical formatting (which *hurts*
−0.111) (`test-compare.md:62,131-146`). Two further sub-techniques are not speculative: **per-label
binary / one-vs-rest (OvR)** and **gated-boolean** are already realized as `output_form` metadata in
the genuine spp run `hair-loss-annotation-v2` (`per_label_binary` ×4, `gated_per_label_binary` ×4,
`gated_single_select` ×1) and are pre-validated against the Pattern-A/Pattern-B failure clusters
(`test-audit-schema.md:38-39,162-191`; `00-CONSOLIDATED-FINDINGS.md:124-134`). The remaining
candidates — CoT, self-consistency, few-shot, least-to-most, ensembling — are either methodology-
touching (CoT, few-shot) or live above the single-prompt contract (self-consistency, ensembling,
least-to-most). The arc's job is to **codify the proven and pre-validated techniques as additive
schema metadata, reconcile multi-prompt-split with the feature it duplicates, and refuse the
structure-changing or composition techniques unless a dev-set hypothesis earns them.**

### 2. Per-technique table

Columns abbreviated: **6-sec?** = touches the locked six-section structure (invariant #12); **Aud?**
= changes the auditor's categorical-vs-row-specific review surface; **Iso?** = touches any stage
allow-list (§4.2 / invariants #1–5). "n/a (above prompt)" means the mechanism lives in the runner or
the user's composition layer, not in any one prompt.

| Technique | Citation | What it changes in spp | 6-sec? | Aud? | Iso? | Roadmap / non-goal / already-exists | BREAKING? | Recommended verdict |
|---|---|---|:--:|:--:|:--:|---|:--:|---|
| Feature-group / multi-prompt split | Tsoumakas & Katakis 2007 (IJDWM 3(3):1–13); Zhou et al. 2022 (least-to-most, arXiv:2205.10625) for the decomposition framing | Nothing new structurally — each sub-task keeps the six sections scoped to its own fields (`repo-design.md:442-447`) | No | No (already scopes cleanly: one prompt = one field-set) | No | **Already exists** (DESIGN §10, designer §5.0, `examples/feature-group-split/`) | No | **reject-as-duplicate** (document/strengthen, do not re-add) |
| Per-label binary / one-vs-rest (OvR) | Tsoumakas & Katakis 2007; Zhang et al. 2018 (Front. Comp. Sci. 12(2):191–202) | New `output_form` value on a multi-label field: emit one yes/no per label, union positives. Single-prompt level keeps the six sections, boolean/enum `<output_format>` per the external-citations flag (NO) | No | No (verdict surface unchanged: a rule edit on a per-label-binary field is still categorical-vs-row-specific) | No | Roadmap (additive schema-metadata layer) | No | **adopt-as-schema-metadata** |
| Gated-boolean (is-addressed gate + conditional sub-labels) | Same OvR lineage (problem-transformation); empirical basis is spp-test Pattern A (`test-audit-schema.md:162-179`) | New `output_form` (`gated_per_label_binary` / `gated_single_select`): a boolean gate field routes the model's "unsure" to gate=false instead of the catch-all attractor | No (expressible as JSON Schema `if/then`, which the schema layer already supports — `repo-skill.md:356`) | No | No | Roadmap (additive schema-metadata layer) | No | **adopt-as-schema-metadata** |
| Anchored-CoT (raw 0–10 → discrete label) | Wei et al. 2022 (arXiv:2201.11903), as the inline-`<task>` CoT form | Asks the model to reason a raw score before the label. **Two implementations diverge sharply:** inline `<task>` request (additive, NO structure change) vs an emitted `raw_score` field before the label (changes `<output_format>` + `<example_output>`, YES) | **Maybe** — NO inline; YES as a field | **Maybe** — a reasoning field changes the audited output pair; the gate question stays categorical-vs-row-specific either way | No | Roadmap, but **benefit is unmeasurable under exact-match** (`00-CONSOLIDATED-FINDINGS.md:104-112`) — couples to Direction 3 | **Yes** if implemented as a field | **dev-confirmed-hypothesis** (inline form only; field form deferred to Direction 3's metric) |
| CoT (general reasoning trace) | Wei et al. 2022 (arXiv:2201.11903); **caveat**: Sprague et al. 2024/ICLR 2025 (arXiv:2409.12183); Liu et al. 2024 (arXiv:2410.21333) | Reasoning before the label. spp permits it **only** as an inline `<task>` request; a dedicated reasoning section/field is BREAKING | **Maybe** — NO inline; YES as a section/field | **Maybe** — a reasoning field changes the auditor's diff surface | No | Roadmap; **NOT the §7.1.3(b) agentic non-goal** (single-turn, no tools), but structure-affecting | **Yes** if section/field | **dev-confirmed-hypothesis** (inline only; classification is the exact regime Sprague finds CoT weakest — must earn its keep on dev) |
| Self-consistency (majority vote over sampled chains) | Wang et al. 2022/ICLR 2023 (arXiv:2203.11171) | Inference-time decoding: sample K completions per row, vote. Lives in `inference.py`/`eval.py`, not the prompt (`external-citations.md:59-69`) | No | No (no prompt-text change) | **At risk** — multiplies inference cost, interacts with the statistics direction's variance estimates; needs a deterministic tie-break | n/a (above prompt; closer to Direction 2 / inference) | No (per prompt) | **defer** (to a runner/inference or statistics arc) |
| Few-shot (multi-shot example pairs) | Brown et al. 2020/NeurIPS (arXiv:2005.14165) | More than one `<example_input>`/`<example_output>` pair → changes the example-pair **cardinality** of the six-section structure | **Yes** (cardinality of two sections) | **Maybe** — multiple exemplars are a second surface the auditor must reason over | No | Roadmap-but-BREAKING; prompt-architect already lists multi-shot as out-of-scope/BREAKING (`external-citations.md:108-117`) | **Yes** | **defer** (requires a six-section-structure design pass; do not bundle into this arc) |
| Least-to-most (sequential sub-problem decomposition) | Zhou et al. 2022/ICLR 2023 (arXiv:2205.10625) | Sequential dependency: later sub-prompt consumes earlier output. This is **cross-task composition**, which spp declares out of scope (`repo-design.md:432-440`) | No (each sub-prompt keeps the format) | No | **At risk** — composition is the user's production layer / the forwarded v1.0 compound-system item | Non-goal-adjacent (composition, not fusion); overlaps the v1.0 compound-system roadmap | No (per prompt) | **defer / reject-as-duplicate** (collides with both the §10 boundary and the v1.0 compound-system arc) |
| Prompt ensembling | Arora et al. 2022/ICLR 2023 (arXiv:2210.02441); Pitis et al. 2023 (arXiv:2304.05970) | Combine multiple prompts' predictions. spp produces **one** prompt per task; per-stage isolation assumes a single `<rules>` edit surface (`external-citations.md:184-194`) | No (per member) | No (per member) | **At risk** — collides with the single-prompt contract; nearest to the §7.1.3(e) automated-search non-goal as *fusion* | Non-goal-adjacent (fusion); only admissible as downstream composition (spp produces members, an ensembler combines) | No (per member) | **reject** (as in-loop fusion); admissible only as user-owned downstream composition |

### 3. Reconciliation with existing feature-group splitting

**What exists today.** Feature-group splitting is a first-class, BREAKING-to-remove consultation step:
designer §5.0 ("Feature-group identification"), run after the strawman and before schema-designer
(`repo-skill.md:301-323`). When groups are identified, the designer recommends decomposing into **N
independent `spp/` task directories — one per group, each with its own `/spp-init`, `plan.md`, and
optimization loop** (`repo-skill.md:306-313`). DESIGN §10 documents what the split buys (focused
`<rules>`, per-group metric headroom, clean auditor scoping, reusability) and the K=1 / dense-
interdependency exception (`repo-design.md:418-430`). It ships as the `examples/feature-group-split/`
fixture (one task → sentiment/topic/urgency sub-tasks). The empirical case for it is the strongest
finding in the assets: **+0.085 composite** over monolithic, with the win mechanistically attributed
to per-group focus populating conditional/dependent fields the monolith leaves empty
(`test-compare.md:255-258`).

**What is genuinely new in Direction-1's "multi-prompt split."** *Nothing at the orchestration level.*
The OvR and gated-boolean output forms (rows 2–3 above) are the only genuinely new artifacts, and they
are **per-prompt output-shape metadata**, not a new way to split tasks. The 7-group DSPy/spp-test arm
is a concrete instance of the *existing* principle, not a new one: groups own disjoint field sets,
each prompt optimized only on its own fields (`test-dspy.md:64-85`).

**The cross-task-composition boundary.** Any "multi-prompt split" that introduces sequential
dependency between sub-prompts (least-to-most, row 7) crosses the locked boundary: *"Cross-task
composition is out of `spp`'s scope … one `spp/` task = one prompt = one optimization loop"*
(`repo-design.md:432-440`). The split spp owns is **parallel disjoint decomposition**; composition of
the pieces is the user's production layer.

**The compound-system overlap.** STATE forwards a v1.0 arc — *compound-system bookkeeping*
(`compound-system-designer` sub-skill, `PIPELINE_SCHEMA`, per-module auditor verdicts, composite
reconciliation at finalize, `repo-state-convention.md:151-156`). Sequential/ensemble techniques belong
**there**, not in Direction 1. Direction 1 must not duplicate the compound-system arc any more than it
duplicates feature-group split.

**Conclusion:** multi-prompt-split is **reject-as-duplicate at the orchestration layer** (the splitting
mechanism already exists); the only net-new Direction-1 surface is the **OvR / gated-boolean
output_form metadata** that makes an individual sub-prompt's output shape first-class.

### 4. Proposed scope

A prompting-techniques arc would ship a thin, **additive schema-metadata layer** and a documentation
reconciliation — no six-section change, no isolation change, no auditor-surface change:

**Additive (schema-metadata) — the body of the arc:**
- **First-class `output_form` values:** `per_label_binary`, `gated_per_label_binary`,
  `gated_single_select`. These are recognized on a field in OUTPUT_SCHEMA (`plan.md` §2) and drive how
  the runner parses and scores that field. They are exactly the values already authored in
  `hair-loss-annotation-v2` and in the DSPy arm's `schemas.py` (`test-dspy.md:87-103`), so this
  formalizes existing, tested shapes rather than inventing them.
- **Gated-boolean expressed via JSON Schema `if/then`** — the schema layer already accepts conditional
  structures (`repo-skill.md:356`; the `nested-schema/` fixture uses `allOf`+`if/then`), so the gate is
  a schema-validation concern, not a new section.
- **Runner support** for these forms is gated on the same K>1 implementation work the v0.2 metrics/
  schema buckets left contract-only (`eval.py` is still K=1 classification, `repo-skill.md:215-243`).
  This arc should either depend on that work or ship the metadata + parsing standalone (the recurring
  "ships standalone before integration" motif, `repo-state-convention.md:110-115`).

**Documentation reconciliation:**
- A DESIGN §10 / designer §5.0 note clarifying that OvR and gated-boolean are *within-prompt output
  shapes*, distinct from the *between-prompt* feature-group split, and that neither is cross-task
  composition.

**Where CoT lives if adopted:** **only inline inside `<task>`** ("reason briefly / rate 0–10 mentally
before the label"), which leaves `<output_format>` and the single `<example_output>` untouched
(`external-citations.md:42-45`). The **emitted `raw_score` field** form of anchored-CoT is deferred:
it changes `<output_format>` (BREAKING) **and** its benefit is unmeasurable until Direction 3 adds an
ordinal/MAE metric (`00-CONSOLIDATED-FINDINGS.md:104-112`). CoT in any form is a **dev-confirmed
hypothesis**, audited like any rule edit, never a default — classification is the regime where Sprague
et al. find CoT gains weakest (`external-citations.md:213-217`).

**BREAKING (explicitly out of this arc):** multi-shot few-shot (example-pair cardinality), CoT/anchored-
CoT as a reasoning *field*, in-loop ensembling/self-consistency fusion. Each needs its own design pass.

### 5. Target version (PROPOSE, don't assume)

**Proposed: v0.4 (a dedicated prompting/output-form arc), opening with a `docs(design): pin v0.4
output-form metadata` PR in the seven-bucket convention.**

Reasoning. §7.1.2 already books **v0.3 for multi-judge subjective metrics + multilingual**
(`repo-design.md:299-302`) — those are independent workstreams, and stapling an output-form arc onto
them would muddy a release whose identity is judges + languages. **v0.4 is booked for cross-model
synthesis** (`repo-design.md:303-304`); that, too, is orthogonal and could share a release with this
additive metadata work, or this work could take its own v0.4 point release alongside it. The honest
options for the gate:
- **v0.4 standalone** — cleanest; the additive output-form layer mirrors the v0.2 seven-bucket
  precedent (additive schema-metadata, K=1 backward-compat fallback) and does not block v0.3.
- **Fold into v0.3** — only if the maintainer wants the OvR/gated metadata to land *before* multi-judge
  metrics depend on richer field shapes; risks scope-creeping the judges release.

The CoT/anchored-CoT *measurement* dependency means the field-form of anchored-CoT cannot ship before
the Direction-3 ordinal metric exists, so the BREAKING half of this direction is **not v0.4-eligible**
regardless. Recommend **v0.4 for the additive metadata; the BREAKING items remain unscheduled pending
their own design PRs.**

### 6. Locked invariants touched

Using the 21-entry inventory (`repo-design.md:179-265`):

- **#1 Per-stage isolated subagents — untouched.** No stage allow-list changes; output_form metadata
  flows through `plan.md` §2, already on the discrepancy/rule-edit/auditor allow-lists.
- **#2 Auditor score-access prohibition — untouched.** No technique here surfaces scores anywhere.
- **#3 No row content to rule-edit subagent — untouched.** OvR/gated are categorical field shapes;
  the rule-edit subagent still sees only IDs.
- **#5 Adversary score-blindness/non-persistence — untouched.** Synthetic rows already carry one GT
  value per field; OvR just structures that field's value.
- **#8 Auditor per-edit-per-field verdict gate — at-risk only for CoT-as-field.** OvR/gated leave the
  categorical-vs-row-specific question intact. A *reasoning field* adds an output surface the auditor
  must reason over — flag, not adopt.
- **#12 Six-section prompt structure — at-risk for two techniques only.** Multi-shot few-shot
  (example-pair cardinality) and CoT-as-section/field (`<output_format>` shape). **Both BREAKING; both
  excluded from the additive arc.** Inline CoT and all output_form work leave the six sections
  **untouched** (`external-citations.md:200-207`).
- **#13 Metric independence rule — untouched** by prompting; relevant only when Direction 3 adds the
  ordinal metric anchored-CoT needs.
- **#21 REPORT §5 invariant block — untouched** (verbatim); this arc adds nothing that changes the
  per-stage isolation statement.

All other invariants (#4, #6, #7, #9–#11, #14–#20) are untouched: this arc neither changes auditor
frequency, the sacred test set, the verdict-gate strings, `plan.md`-as-contract, checkpoint discipline,
`MODEL_IDENTIFIER`, the loop_spec block, the finalize advance rule, the four-command set, nor the
metric-independence shape.

### 7. Roadmap-vs-non-goal classification

- **Feature-group split:** already-shipped roadmap (DESIGN §10). Not re-opened.
- **Per-label binary / OvR:** **roadmap, additive.** Inside the fixed-output-space boundary; a field-
  shape generalization in the spirit of the v0.2 buckets.
- **Gated-boolean:** **roadmap, additive.** Same; expressible in already-supported JSON Schema
  conditionals.
- **Anchored-CoT:** **roadmap (inline) / blocked (field).** Inline form is additive; field form is
  BREAKING *and* unmeasurable until Direction 3. A dev-confirmed hypothesis, not a default.
- **CoT (general):** **roadmap, conditional, structure-affecting.** Argue carefully: CoT is **not** the
  §7.1.3(b) tool-use/agentic non-goal (it is single-turn, tool-free reasoning, not orchestration over
  tool boundaries — `repo-design.md:334-339`), and it is **not** the §7.1.3(a) generation non-goal
  (the output space stays a fixed label set). It **is** structure-affecting if it becomes a section/
  field (invariant #12) and is empirically weak on classification (Sprague). So: permitted *inline*,
  BREAKING as structure, hypothesis-gated either way.
- **Self-consistency:** **roadmap-adjacent, deferred.** A decoding mechanism, not a non-goal, but it
  belongs to an inference/statistics arc — it interacts with run-to-run variance, not the prompt.
- **Few-shot (multi-shot):** **roadmap-but-BREAKING.** A six-section change requiring its own design
  pass; not a non-goal, but not bundle-able here.
- **Least-to-most:** **non-goal-adjacent.** Its sequential dependency is the cross-task composition
  §10 declares out of scope and the v1.0 compound-system arc will formalize. Defer, do not fuse.
- **Ensembling:** **non-goal-adjacent (fusion).** Nearest to the §7.1.3(e) automated-search non-goal;
  admissible only as user-owned downstream composition (spp produces members), never as an in-loop
  edit-surface multiplier. Reject as fusion.

### 8. CHANGELOG implication

Per CLAUDE.md §5 and the v0.2 pattern (`repo-state-convention.md:369-416`):

- **Additive output_form entries (`### Added`):** for `per_label_binary`, `gated_per_label_binary`,
  `gated_single_select` — each stating the new field-shape, that **the six-section structure and all
  four stage allow-lists are preserved verbatim**, and naming the **K=1 / plain-output_form backward-
  compat fallback** (existing plans with no `output_form` default to the current behavior).
- **Documentation entry (`### Changed`):** the DESIGN §10 / designer §5.0 reconciliation note
  distinguishing within-prompt output shapes from between-prompt feature-group split — flagged
  methodology-affecting (it touches the auditor's review-surface description) but **shape-preserving,
  not BREAKING**.
- **`### Notes` "no isolation change":** an explicit statement that no stage allow-list, the auditor
  score-blindness, the rule-edit no-row-content rule, or the sacred test set is touched — the parallel
  to the infrastructure-only "no methodology changes" note (`repo-state-convention.md:400-404`).
- **Reserved `BREAKING CHANGE:` entries (NOT in this arc, recorded as the boundary):** if a future PR
  adds CoT-as-field, multi-shot few-shot, or in-loop ensembling, each requires a `BREAKING CHANGE:`
  entry naming the touched invariant (#12 six-section structure; #8 auditor surface for CoT-field),
  mirroring the six-entry PR-#14 model (`repo-state-convention.md:380-385`). This arc should state in
  its CHANGELOG framing paragraph that these remain deliberately out of scope.

### 9. Open design questions for the gate

1. **Does the output_form metadata ship standalone or behind the K>1 runner work?** `eval.py` is still
   K=1 classification (`repo-skill.md:215-243`). Standalone (metadata + parsing only) follows the v0.2
   "ships standalone before integration" motif; integrated requires the metrics/schema buckets to land
   first. Which sequencing?
2. **Is OvR a new `output_form` value, or is it derivable from `type: array` + per-label scoring?** The
   schema already supports `array`; OvR may be a *scoring/parsing* convention rather than a new schema
   keyword. Decide whether the lever is a schema-keyword or a metric-design decision.
3. **Anchored-CoT field form: blocked on Direction 3, or co-designed with it?** The `raw_score` field is
   unmeasurable until an ordinal/MAE metric exists. Does the gate want the two directions co-scheduled,
   or anchored-CoT-as-field explicitly deferred until Direction 3 ships?
4. **CoT inline allowance — make explicit or leave to prompt-architect?** prompt-architect already
   permits inline CoT in `<task>`. Should this arc add a dev-set-confirmation discipline (CoT must show
   a dev delta beyond noise, audited as a rule edit) as a documented requirement, given Sprague's
   classification caveat?
5. **Where, precisely, is the within-prompt vs between-prompt boundary documented** so a future
   contributor does not re-add "multi-prompt split" as a feature? DESIGN §10, designer §5.0, or a new
   glossary entry?
6. **Target version: v0.4 standalone, or fold the additive layer into v0.3?** (See §5.) The maintainer
   must decide whether output-form metadata is a release of its own or rides with judges/multilingual.
