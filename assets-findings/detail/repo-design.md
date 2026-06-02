# DESIGN.md deep-dive — verbatim detail behind spp-repo.md

Companion to `assets-findings/spp-repo.md`. This file captures verbatim normative
text the summary compressed. All quotes are exact; line refs are `DESIGN.md:LINE`.
DESIGN.md is 2339 lines, read end to end.

---

## 1. §4.2 — Per-stage information isolation (the load-bearing design lock)

§4.2 spans `DESIGN.md:135-267`. The governing framing:

> The single highest-leverage architectural property of the entire skill.
> It is the design lock that distinguishes `spp` from automated optimizers
> like DSPy and APE. The rest of the methodology is plumbing; per-stage
> isolation is the methodology. (`DESIGN.md:137-140`)

> Every cognitive stage in `/spp-loop`'s iteration runs in an **isolated
> subagent** with an **explicit allow-list** of inputs. The orchestrator
> constructs each subagent's invocation context from that allow-list; the
> subagent's context terminates when it returns; state flows between stages
> through files (the iteration's artifacts under `runs/<model>/run_NN/`),
> **not through the orchestrator's main context**. The orchestrator
> coordinates; cognition lives in subagents. (`DESIGN.md:142-148`)

### 1a. Discrepancy subagent — allow-list and forbidden inputs (VERBATIM)

> - **Discrepancy subagent** (after scoring; produces
>   `discrepancy_analysis.md`). Sees: `eval.json`, `results.json`,
>   `baseline.csv` filtered to disagreed dev rows, `plan.md` §2,
>   current `prompt_v(N).md`. Does not see: prior iterations'
>   artifacts, train rows that the model predicted correctly, test
>   rows. The persistent artifact references rows by ID only; row
>   content stays in this subagent's terminating context. (`DESIGN.md:152-158`)

### 1b. Rule-edit subagent — no row content under any path (VERBATIM)

> - **Rule-edit subagent** (after discrepancy + adversary; produces
>   `prompt_v(N+1).md`). Sees: current prompt, `discrepancy_analysis.md`
>   with row IDs but no row content, `plan.md` §2, the
>   `prompt-architect` sub-skill. Does not see: `baseline.csv`,
>   `eval.json`, `results.json`, prior iteration artifacts. **No row
>   content reaches this subagent under any path** — this is the
>   property the rule-edit step exists to enforce. (`DESIGN.md:159-165`)

### 1c. Auditor subagent — score-blindness (VERBATIM)

> - **Auditor subagent** (after rule-edit; produces
>   `auditor_review.md`). The most stringent specific instance of
>   per-stage isolation; see "auditor's score-access prohibition"
>   below. Sees: prompt diff (`prompt_v(N).md` and `prompt_v(N+1).md`),
>   prior iteration's discrepancy, `plan.md` §2, prior auditor
>   reviews. Does not see: the new iteration's scores, train/test
>   labels, the sacred test set. (`DESIGN.md:166-172`)

The score-access prohibition spelled out (`DESIGN.md:201-210`):

> The auditor's allow-list excludes the new iteration's `eval.json` and
> `results.json` even though both exist on disk by the time the
> auditor runs (iteration order is edit → score → audit). Score
> isolation is the most stringent of the four subagent allow-lists
> because score-driven optimization is the path of least resistance
> toward methodology breakage; the auditor's existence as the final
> check makes its information isolation load-bearing in a way the
> other stages' isolation is reinforcing rather than uniquely
> load-bearing.

The directive (`DESIGN.md:246-247`):

> **Do not give the auditor score
> access. The information isolation is the design.**

The leakage rationalizations, per stage (`DESIGN.md:183-193`):

> - A **discrepancy subagent** with prior-iteration artifacts can echo
>   earlier proposals rather than reasoning fresh from current failure
>   patterns.
> - A **rule-edit subagent** with row-content access can produce rules
>   that look categorical but were actually authored to fit specific
>   rows (the leakage mode the per-stage architecture was designed
>   against).
> - An **auditor** with score access will rationalize any edit that
>   improved the metric, including row-specific patches that overfit.
> - An **adversary** with score access will generate adversarial rows
>   driven by metric movement rather than blind-spot reasoning.

### 1d. Adversary subagent — allow-list, score-blindness, non-persistence (VERBATIM)

Allow-list in §4.2 (`DESIGN.md:173-176`):

> - **Adversary subagent** (when `ADVERSARY_FLAG = on`). Sees: current
>   prompt, prior iteration's discrepancy, `plan.md` §2. Does not
>   see: scores, sacred test set, baseline rows. Synthetic outputs
>   do not persist to the baseline or splits.

Non-persistence, fully stated in §4.3 (`DESIGN.md:288-300`):

> **Output disposition (non-persistence).** Adversarial rows are surfaced
> to the user *during* the iteration — either inline within the
> discrepancy analysis or as a separate prompt to the user — and are
> **not persisted as artifacts**. They do not get a file under `runs/`,
> they do not appear in `baseline.csv`, they do not enter `splits.json`,
> and they are not referenced in `REPORT.md`. The reasoning is symmetric
> with the no-baseline rule: persisting adversarials creates the temptation
> to grade against them later, which would turn a thought experiment into
> an unblessed test set with none of the labeling rigor of the real one.
> If a particular adversarial row turns out to represent a real failure
> class the user wants in the baseline, the user collects similar *real*
> data and adds it through the labeling process, not by promoting the
> synthetic row.

No-baseline boundary (`DESIGN.md:283-286`):

> **Important boundary:** synthetic adversarial rows are **not** added to
> the baseline. They are a thought experiment to surface fragility before
> production, not training data. Adding them to the baseline would corrupt
> the test set and defeat the sacred-test-set guarantee.

### 1e. Auditor frequency — non-optional, per-iteration, batch is the only valve (VERBATIM)

> **Frequency is non-optional and per-iteration.** The auditor runs after
> every iteration of `/spp-loop`. If per-iteration token cost becomes an
> adoption barrier post-v1, the correct escape valve is **batch auditing**
> (the auditor reviews the diffs and discrepancy analyses of the last N
> iterations as a group, still without score access), **not frequency
> reduction**. Batching preserves the information-isolation property;
> reducing frequency would silently skip categorical-vs-row-specific review
> on some iterations, exactly the failure mode this agent exists to
> prevent. (`DESIGN.md:253-261`)

---

## 2. §5 — Sub-skills + the six-section prompt structure

§5 spans `DESIGN.md:317-328`. It names the six sections only inside the
`prompt-architect` table row (`DESIGN.md:323`):

> | `prompt-architect` | Six-section XML template (Persona, Task, Rules, Output Format, Example Input, Example Output) for production-grade prompts. Ported from existing project. |

`metric-design` row (`DESIGN.md:324`):

> | `metric-design` | Guides the user through metric selection. Enforces the constraint that the metric must be computable independently of the model being optimized (no GPT-4 judging GPT-4 prompts). |

The canonical six-tag list (lowercase XML tags) is fixed in the §7.1.1 invariant
(`DESIGN.md:1591-1593`): `<persona>`, `<task>`, `<rules>`, `<output_format>`,
`<example_input>`, `<example_output>`. The invariant states what the structure buys
(`DESIGN.md:1593-1597`):

> Guarantees every prompt the loop iterates on uses the canonical six-section
> shape; this is what makes per-iteration diffs reviewable and what gives the
> auditor a stable surface to flag rule edits against.

`<rules>` as the evolving / audited surface — §4.2 describes the auditor as
reasoning over rule edits ("Is this rule edit categorical … or row-specific?",
`DESIGN.md:214-215`); the §7.1.1 invariant confirms bucket-3 per-field
generalizations "operate on the rules section's content, not its structural
position" (`DESIGN.md:1598-1600`).

NOTE on item-2 sub-questions: §5 itself does **not** address CoT, few-shot, or
tool-use allowances — DESIGN.md only locks the section *names and count*. The
"CoT-only-inside-`<task>`, few-shot/tool-use BREAKING" rules the summary cites
live in the `prompt-architect` SKILL.md, not in DESIGN.md. Tool-use/agentic
prompts appear in DESIGN only as a §7.1.3 deliberate non-goal (see item 4 below).
This is a place to flag: the summary's item-1 detail on CoT/few-shot is sourced
from the sub-skill, not DESIGN §5.

---

## 3. §7.1.1 Locked-invariants inventory — COMPLETE, in document order

Inventory framing (`DESIGN.md:1345-1349`):

> The inventory is non-exhaustive — load-bearing
> methodology commitments only, not every constraint in the
> codebase. The inventory itself is methodology-affecting:
> removing or weakening any inventory entry is `BREAKING
> CHANGE:` per `CLAUDE.md` §4.

**Total: 17 named invariants** across 6 groups, plus 2 documentation-gap findings.
Listed in exact document order:

### Group: Per-stage information isolation (5)

1. **Per-stage isolated subagents** — ref §4.2. Status: **preserved with shape
   change** (bucket 3 generalized allow-lists to multi-field-aware shapes without
   weakening isolation). (`DESIGN.md:1358-1378`)
2. **Auditor's score-access prohibition** — ref §4.2 + CLAUDE.md §8 + auditor.md §2.
   Status: **preserved verbatim**. (`DESIGN.md:1380-1394`)
3. **No row content to rule-edit subagent** — ref §4.2 + spp-loop.md §4 step 10 +
   CLAUDE.md §8. Status: **preserved verbatim**. (`DESIGN.md:1396-1412`)
4. **Auditor frequency: per-iteration, non-optional** — ref §4.2 + CLAUDE.md §8 +
   plan.md.template §8 + loop_spec.md.template §3. Status: **preserved verbatim**.
   (`DESIGN.md:1414-1429`)
5. **Adversary score-blindness and non-persistence** — ref §4.3 + adversary.md §2/§6
   + spp-loop.md §4 step 9 + loop_spec.md.template §4. Status: **preserved with shape
   change** (synthetic rows carry full OUTPUT_SCHEMA-shaped ground truth).
   (`DESIGN.md:1431-1450`)

### Group: Sacred test set (2)

6. **Test rows untouched until `/spp-finalize`; read exactly once** — ref §10 glossary
   + finalize §3 pre-cond 8 + loop §3 pre-cond 7. Status: **preserved verbatim**.
   (`DESIGN.md:1454-1477`)
7. **Runner-side defense-in-depth on the test partition** — ref loop §3 pre-cond 7 +
   loop §4 step 2 + finalize §3 pre-conds 4,8. Status: **preserved verbatim**.
   (`DESIGN.md:1479-1491`)

### Group: Verdict-enforced gates (4)

8. **Auditor verdict gate with literal `auditor override` substring** — ref spp-loop.md
   §4 step 12 + auditor.md §6 + auditor.md §2. Status: **preserved with shape change**
   (per-edit-per-field verdicts, `[edit-N.field-name]` tokens; K=1 unscoped covers lone
   field). (`DESIGN.md:1495-1515`)
9. **Baseline-quality verdict precondition to G2 with literal `not-ready override`
   substring** — ref baseline-quality SKILL.md §6 + spp-baseline.md §5. Status:
   **preserved with shape change** (per-field calibration; "any-not-ready dominates,
   any-revise dominates ready" consolidation). (`DESIGN.md:1517-1537`)
10. **Schema-designer verdict precondition to G1 with literal `schema-not-ready
    override` substring** — ref schema-designer SKILL.md §6 + spp-init.md §4 step 9 / §5
    + §10 glossary. Status: **introduced in v0.2 (buckets 1+4) as a new invariant;
    preserved verbatim since introduction**. Dual check folds into G1 — no G1.5, no
    renumbering. (`DESIGN.md:1539-1567`)
11. **HITL gate G1–G6 literal-string approval substrings** — ref §10 glossary +
    plan.md.template §9 + each phase doc's gate enforcement. Status: **preserved
    verbatim**. (`DESIGN.md:1569-1585`)

### Group: Methodology-as-substance (4)

12. **Six-section prompt structure** — ref §5 + prompt-architect SKILL.md +
    prompt_v01.md.template. Status: **preserved verbatim**. (`DESIGN.md:1589-1603`)
13. **Metric independence rule** — ref §5 + metric-design SKILL.md §5. Status:
    **preserved with shape change** (per-field application; one field's violation
    fails the whole task). (`DESIGN.md:1605-1619`)
14. **Verdict tokens are categorical hard tokens — no confidence weighting** — ref
    auditor.md §6 + baseline-quality SKILL.md §6 + schema-designer SKILL.md §6. Status:
    **preserved verbatim**. (`DESIGN.md:1621-1642`)
15. **`plan.md` as contract; re-read fresh by every phase; mid-task changes via §11
    revision log** — ref §10 glossary + each phase doc's pre-conditions +
    plan.md.template §11. Status: **preserved with shape change** (bucket-5 manual
    upgrade steps; runner K=1 auto-promote at read, no silent rewrite).
    (`DESIGN.md:1644-1663`)

### Group: Operational-load-bearing (4)

16. **Atomic checkpoint writes (`tmp + fsync + rename`)** — ref all four phase docs.
    Status: **preserved verbatim**. Documentation finding: lacks an explicit BREAKING
    CHANGE bullet. (`DESIGN.md:1667-1686`)
17. **`MODEL_IDENTIFIER` exact env-var string, no aliasing** — ref §2.2 +
    plan.md.template §5 + loop_spec.md.template §5 + `runs/<model_identifier>/` naming.
    Status: **preserved verbatim**. (`DESIGN.md:1688-1704`)
18. **`loop_spec.md` literal-block check at `/spp-loop` and `/spp-finalize`
    pre-conditions** — ref loop_spec.md.template §3/§4/§7 + loop §3 pre-cond 4 +
    finalize §3 pre-cond 4. Status: **preserved verbatim**. (`DESIGN.md:1706-1723`)
19. **`/spp-finalize` advances only on `SUCCESS.md` (with one v0.2 deliberate
    exception)** — ref finalize §3 pre-cond 6. Status: **preserved with shape change**
    (`EARLY_STOP.md/early_stop_floor_unmet` advancement branch, gated by user
    confirmation; unmet floors propagate to REPORT §7.5). (`DESIGN.md:1725-1746`)
20. **v1 command set is closed at four** — ref finalize "Pattern observations". Status:
    **preserved verbatim**. (`DESIGN.md:1748-1759`)

### Group: REPORT invariant block (1)

21. **REPORT.md.template §5 invariant block stays verbatim** — ref REPORT.md.template §5
    lines 292–296 ("Per-stage information-isolation invariants: preserved." header +
    four subagent sub-statements). Status: **preserved verbatim**. (`DESIGN.md:1763-1780`)

> **COUNT CORRECTION vs spp-repo.md.** The summary (`spp-repo.md` item 7) lists the
> same entries but its grouped narrative reads as "the list"; the actual inventory
> has **21 named invariant entries** (numbered above) — the summary's prose collapses
> a couple of multi-sentence entries and does not give a total count. If a downstream
> impact table needs one row per invariant, use 21 (group breakdown: 5 / 2 / 4 / 4 / 4
> / 1, with one entry — #10 schema-designer — flagged "introduced in v0.2").

### Documentation findings (2) — `DESIGN.md:1782-1827`

> 1. **Atomic-checkpoint discipline lacks an explicit BREAKING CHANGE bullet.** …
>    a future contributor proposing an alternative persistence strategy would not
>    find a clear BREAKING CHANGE trigger to consult.
> 2. **`/spp-finalize.md` Versioning bullet "Allowing `/spp-finalize` to advance on
>    `EARLY_STOP.md` or `FAILED.md` termination types" did not get updated when bucket
>    5 added the deliberate `early_stop_floor_unmet` exception.** … The contradiction
>    is semantic … not substantive.

Closing guidance (`DESIGN.md:1841-1847`):

> Adding an invariant to the inventory is a documentation update;
> removing or weakening any inventory entry is `BREAKING CHANGE:` per `CLAUDE.md` §4.
> The inventory is non-exhaustive; contributors who identify a load-bearing
> methodology commitment that is missing should propose its addition in a follow-up
> PR rather than treat the omission as license to weaken it.

---

## 4. §7.1.2 — Further-out roadmap (VERBATIM list)

Framing (`DESIGN.md:1992-1995`): each item is "roadmap, not a deliberate boundary;
v0.x increments will reach these in turn."

- **Multi-judge subjective metrics.** Roadmap: **v0.3**. Forbidden today by the
  `metric-design` independence rule (§5). (`DESIGN.md:1997-2002`)
- **Multilingual data.** v0.1.0 assumes English. Roadmap: **v0.3, separate design
  pass**. (`DESIGN.md:2003-2006`)
- **Cross-model synthesis.** v0.1.0 produces per-model REPORTs; users synthesize
  manually. Roadmap: **v0.4**. (`DESIGN.md:2007-2011`)
- **Loop resumption mid-iteration.** Iteration is the unit; interrupted iterations
  discarded and re-run. Roadmap: **TBD** — "requires per-step checkpointing across the
  discrepancy / rule-edit / auditor / scoring stages without weakening the per-stage
  isolation contract; a clean design has not been worked out." (`DESIGN.md:2012-2017`)

---

## 5. §7.1.3 — Deliberate non-goals (COMPLETE, VERBATIM)

Framing (`DESIGN.md:2021-2024`):

> They are scope boundaries the methodology will not cross because the underlying
> problem is sufficiently different from what `spp` solves that any extension would
> be a different methodology, not a generalization of this one.

**(a) Generation-task methodologies** (`DESIGN.md:2026-2036`) — the fixed-output-space
sentences, VERBATIM:

> Free-form text generation (summarization, rewriting, instruction tuning,
> multi-turn conversation) does not have ground truth in the way classification
> provides — the output space is unbounded and there is no "correct
> label" against which to compute a metric. The methodology's validation
> primitives (sacred test set, F1 / balanced-accuracy /
> per-class metrics, auditor's categorical-vs-row-specific judgment
> on rule edits) all assume a fixed output space. Generation tasks
> need a different methodology that handles bounded reference sets,
> multiple acceptable outputs, and qualitative judgment under
> uncertainty.

**(b) Tool-use and agentic prompts** (`DESIGN.md:2037-2041`):

> Tool-using or multi-turn agentic prompts are not a prompt-quality problem; they are
> an orchestration problem over tool boundaries, conversation state, and recovery
> semantics. The fix is in the orchestration layer, not in prompt rules under
> per-stage information isolation.

**(c) RAG prompts (retrieval-augmented)** (`DESIGN.md:2042-2047`):

> RAG quality is jointly a function of retrieval quality and prompt quality; isolating
> prompt quality requires fixing retrieval, which `spp` neither inspects nor provides
> primitives for. … folding it into `spp` would silently couple two failure surfaces.

**(d) Prompt-injection defense and jailbreak resistance** (`DESIGN.md:2048-2055`):

> `spp` produces prompts whose quality on labeled data is auditable. It does not
> produce prompts that resist adversarial input from the data side. Adversarial
> robustness is a different problem with its own evaluation primitives (red-teaming
> protocols, adversarial test suites, threat-model documentation) …

**(e) Automated prompt search (DSPy / GEPA / APE composition)** (`DESIGN.md:2056-2065`):

> `spp`'s per-stage information isolation requires that rule-edit proposal precede
> selection-by-score, and that no scoring signal reach the auditor's categorical
> judgment. Optimization frameworks that fuse proposal and selection (the move that
> gives them their speed advantage) violate this property structurally. The
> methodologies are incompatible by construction; PRs proposing search or auto-edit
> integrations should propose composition (use `spp` to produce a starting prompt, then
> run an optimizer downstream) rather than fusion.

**(f) Auditor frequency reduction** (`DESIGN.md:2066-2075`):

> If per-iteration auditor cost becomes a problem, the post-v1 fix is **batch
> auditing** … not "audit every N iterations." Frequency reduction silently weakens
> the audit; batch auditing preserves it. … the deliberate boundary is against
> frequency reduction specifically.

**(g) LLM-as-judge metrics for v0.1.0's `metric-design` independence rule**
(`DESIGN.md:2076-2084`):

> `metric-design` §5 forbids LLM judges in v0.1.0 because v0.1.0 users cannot reliably
> draw the boundary between cross-family judges (defensible) and same-family judges
> (silent contamination); rather than parameterize the rule, v0.1.0 forbids the entire
> pattern. … the v0.1.0 stance against `metric-design` accepting any LLM judge is
> deliberate.

Closing rule (`DESIGN.md:2086-2090`):

> When in doubt, lean toward roadmap rather than deliberate. A v0.x version can always
> reach a roadmap item; a deliberate non-goal is harder to undo because it shapes the
> methodology's identity. The items above are deliberate because the underlying problem
> is methodologically different, not because the bookkeeping is narrow.

> NOTE: **Continuous/regression is NOT a deliberate non-goal.** Number fields with
> MAE/RMSE sit *inside* the fixed-output-space boundary (the non-goal bites only
> "unbounded generation"). The summary's item-6 reading is correct and confirmed by the
> §7.1.3 (a) text above plus the metrics-layer `number → MAE/RMSE` suggestion
> (`DESIGN.md:723-726`). The blocker for direction-3 is implementation, not methodology.

---

## 6. §7.2 — Confidentiality discipline (findings-citable vs not-reproducible)

§7.2 spans `DESIGN.md:2092-2119`. The governing rule (`DESIGN.md:2103-2113`),
VERBATIM:

> The line is drawn between **findings** (citable) and **protected content** (not
> reproducible):
>
> - **Citable as findings:** aggregate metrics (e.g. `test F1 = 0.941`), the existence
>   and shape of failure clusters (e.g. cluster 4.4 cross-family register-vs-addressee
>   weighting; the length-correlated cross-family failure pattern), per-model F1 deltas,
>   the 4-cluster taxonomy structure.
> - **Not reproducible:** specific row contents, baseline labels, prompt text from the
>   source project, identifiable post bodies, or any data field that could re-identify a
>   source-project row.

Applies to all worked examples; committed `examples/` `baseline.csv` are dummy data
with the same *shape* as real baselines, not real-data extracts (`DESIGN.md:2115-2119`).

---

## 7. §10 Glossary — feature-group split + cross-task composition out of scope

### Feature-group prompt splitting (VERBATIM, `DESIGN.md:2292-2334`)

> **Feature-group prompt splitting.** When a task's OUTPUT_SCHEMA spans
> multiple feature groups — subsets of fields that share a reasoning
> pattern, an input dependency, or a metric profile — the methodology
> defaults to one prompt per group, with each group's prompt living in
> its own `spp/` task directory. Splitting buys: focused `<rules>`
> sections per prompt (no cross-field rules competing for context),
> per-group metric optimization headroom …, clean auditor scoping (a rule
> edit affects exactly one prompt = exactly one set of target fields), and
> reusability …. The exception is K=1 (single field) or schemas where field
> interdependencies are dense enough that splitting introduces more
> coordination overhead than it saves …

The hard scope boundary (`DESIGN.md:2322-2328`), VERBATIM:

> **Cross-task composition is out of `spp`'s scope** — `spp` produces
> production-grade prompts, and the user owns the production pipeline that
> composes them. Tasks that have been split into N `spp/` directories are
> tracked by the user (via naming conventions, parent directories, the
> user's own composition logic at the production layer), not by `spp`; the
> methodology's contract stays "one `spp/` task = one prompt = one
> optimization loop."

Six-section discipline scopes per sub-task (`DESIGN.md:2329-2334`):

> The `prompt-architect` sub-skill's six-section discipline scopes per
> sub-task when a prompt is part of a split task — `<persona>`, `<task>`,
> `<rules>`, `<output_format>`, `<example_input>`, `<example_output>` all
> describe the sub-task's fields, not the full original task's fields.

### Other §10 glossary entries that constrain

**Sacred test set** (`DESIGN.md:2234-2238`), VERBATIM:

> The held-out portion of the stratified split that is not touched until Phase 3
> (`/spp-finalize`). The optimization loop sees train + dev only. The test set's role
> is to provide an honest generalization estimate uncontaminated by iteration.
> Touching it mid-loop voids the methodology's claim.

**Auditor information isolation** (`DESIGN.md:2240-2246`), VERBATIM:

> The non-negotiable design property that the auditor sub-agent sees the prompt diff
> and the prior iteration's discrepancy analysis but **never sees the new iteration's
> scores** (dev F1, recall, precision, etc.). This isolation is what forces the auditor
> to evaluate rule generalizability on its merits rather than rationalizing via outcome.
> Breaking the isolation breaks the methodology.

**Categorical rule edit** (`DESIGN.md:2248-2251`):

> A prompt rule edit that addresses a class of rows defined by an articulable property
> (e.g., "ambiguous short self-disclosures with no explicit context should be
> Uncertain"). Kept by the auditor.

**Row-specific rule edit** (`DESIGN.md:2253-2257`):

> A prompt rule edit that patches one weird row, often dressed up to look general (e.g.,
> "rows containing 'minoxidil' followed by a question mark are False"). Flagged by the
> auditor for revert or generalization. Accumulating row-specific edits is the mechanism
> by which baseline overfitting compounds across iterations.

**HITL gate** (`DESIGN.md:2259-2264`):

> A human-in-the-loop gate: a specific point in a `spp` command where execution stops
> and waits for an explicit allowed response from the user before proceeding. Six gates
> G1–G6 … Vague approval ("looks good") is not an allowed response; gates require
> specific acknowledgements or specific corrections.

**Verdict-gated preconditions (v0.2)** (`DESIGN.md:2266-2282`): only **G1** (schema-
designer, `schema-not-ready override`) and **G2** (baseline-quality, `not-ready
override`) carry a verdict precondition; G3–G6 do not. Renumbering (a new G1.5) is
"explicitly rejected … the verdict gates the gate's contents, not a separate check."

**`plan.md` (as contract)** (`DESIGN.md:2284-2290`):

> Subsequent commands … re-read it fresh and verify their actions are still on-spec.
> Mid-task changes update `plan.md` with timestamp and reason. It is not a wish list; it
> is the binding agreement that defines what the rest of the methodology is optimizing
> toward.

---

## 8. Other constraining sections

### 8a. The single question the auditor asks — categorical vs row-specific (§4.2)

VERBATIM (`DESIGN.md:212-224`):

> *Is this rule edit categorical (addresses a class of rows defined by an articulable
> property) or row-specific (patches one weird row)?*
>
> - **Categorical edits** are kept. Example: "ambiguous short self-disclosures with no
>   explicit context should be classified as Uncertain rather than Positive" addresses a
>   definable class.
> - **Row-specific edits** are flagged for either revert or generalization. Example:
>   "rows containing the word 'minoxidil' followed by a question mark should be False" is
>   a row-specific patch dressed up as a rule. The auditor either pushes back to find the
>   underlying categorical property or recommends revert.

Why high-leverage (`DESIGN.md:228-234`): every other defense catches overfitting
*after*; the auditor catches it *before* the next iteration commits, keeping
iteration N's rule surface clean for N+1.

Per-edit-per-field verdict scoping is locked in the per-field methodology layer
(`DESIGN.md:920-938`): a rule edit with K target fields gets K independent verdicts;
"An edit can be `categorical` for field A and `row-specific` for field B
simultaneously"; gate advances on "**all non-categorical (edit, field) combinations**
being overridden in `plan.md` §11"; runner syntax = bracketed `[edit-N.field-name]`
tokens paired with literal `auditor override`; K=1 unscoped override covers the lone
field (`DESIGN.md:936-938`).

### 8b. Metrics layer — independence rule + nonsense-aggregate refusal (§7.1.1)

Independence rule applies per field (`DESIGN.md:736-739`):

> The independence rule (`DESIGN.md` §5; `metric-design` SKILL.md §5) applies per field
> unchanged: each field's chosen metric is independently checked against the
> cross-family-judge prohibition, and a single field's violation is sufficient to fail
> the rule for the task as a whole.

Aggregate must refuse dimensional nonsense (`DESIGN.md:751-759`):

> The sub-skill **must refuse a nonsense aggregate** — for example, macro-averaging F1
> (range [0, 1], higher is better) with MAE (range [0, ∞), lower is better) produces a
> dimensionally meaningless number — and surface the dimensional mismatch as a `revise`
> signal … the `revise` signal here is documentary … not gate-blocking.

`metric-design` remains review-and-record, **no verdict gate** — the only verdict-gated
sub-skill in v0.2 is `schema-designer` (`DESIGN.md:848-857`).

Per-class-within-field floors are NOT a separate tier; users fold them into the field's
primary metric (e.g. `recall_on_class_X`) — single-tier discipline
(`DESIGN.md:773-785`).

### 8c. Stop discipline / EARLY_STOP_FLOOR_UNMET (§7.1.1)

Aggregate plateau gates the loop; per-field movement is tracked but does not gate
(`DESIGN.md:787-813`). `EARLY_STOP_FLOOR_UNMET` triggers when the aggregate plateaus
at-or-above target but ≥1 per-field floor is unmet; distinct from SUCCESS and from
FAILED (`DESIGN.md:956-970`).

### 8d. Schema layer — JSON Schema pin + mechanical vs judgment validation (§7.1.1)

Schema language pinned: **JSON Schema (draft 2020-12)**, surface YAML or JSON
(`DESIGN.md:564-585`). Single-output classification is a degenerate one-field enum
OUTPUT_SCHEMA — no `LABEL_SPACE` alias inside the schema (`DESIGN.md:587-596`).
Mechanical layer = 7 parser-deterministic rules (`DESIGN.md:663-675`); judgment layer =
5 rules requiring a verdict (`DESIGN.md:677-692`).

### 8e. Build order — loop runner is built LAST among major commands (§6)

The loop runner is "the lowest-risk piece, so it is built last among the major
commands" (`DESIGN.md:425-431`) — a working version exists in the source project;
porting is mechanical.

---

## Reconciliation notes vs spp-repo.md

- **Invariant count.** spp-repo.md item 7 presents the inventory grouped but never
  states a total; the actual count of named entries is **21** (groups 5/2/4/4/4/1).
  Downstream impact tables should use 21, with #10 (schema-designer→G1) tagged
  "introduced in v0.2."
- **CoT / few-shot / tool-use.** spp-repo.md item 1 attributes the
  CoT-inside-`<task>` / few-shot-BREAKING rules in a way that could read as DESIGN §5.
  DESIGN §5 locks only the six section *names*; those allow/deny rules live in the
  `prompt-architect` SKILL.md. DESIGN's only tool-use statement is the §7.1.3
  deliberate non-goal (agentic prompts). Minor sourcing imprecision, not an error.
- Everything else in spp-repo.md (§4.2 allow-lists, §7.1.3 generation-task quote,
  §10 feature-group / cross-task-composition boundary, §7.2 findings rule, sacred-test
  read-once) matches the DESIGN.md text verbatim. No substantive contradictions found.
