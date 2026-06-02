## Direction 2 — More statistical mechanisms

Bootstrap confidence intervals and paired permutation tests on the per-row scores
`spp` already computes, surfaced into `REPORT.md` at finalize and offered as a dev
diagnostic in `metric-design`. This is the cleanest, lowest-risk arc of the three: it
is already a logged gap, it is additive, and — because it lives entirely at
`/spp-finalize` and `metric-design` — it touches none of the four `/spp-loop` stage
allow-lists and leaves every isolation invariant intact.

### 1. Summary and motivation

The statistics gap is **universal across all three experimental assets and already
logged verbatim** as a forwarded item. `STATE-as-of-v0.2.0.md:107`: *"No bootstrap
CIs / paired permutation tests on row-level scores. Same limit as the prior
`spp_compare`. Cheap to add at finalize."* The same gap is named twice in spp-ex
(report.qmd §4.4 item 7 *"No paired-permutation test against cited GEPA — feasible
but not done"*; FINDINGS.md §9 *"can be added cheaply at finalize"*) and is confirmed
absent in code: a grep across `scripts/ phases/ agents/ sub-skills/ templates/` returns
**zero** bootstrap / CI / permutation / significance machinery
(repo-skill.md §3, "No CI / bootstrap / permutation / significance code — confirmed").
`eval.py` emits point estimates only.

**Why it bites, specifically at small N.** The methodology's only current significance
reasoning is an informal heuristic: a fixed **±0.015 "noise floor"** plus a prose
**"Δ > 5× noise floor"** test (spp-test `monolithic_vs_batched.md:25`, verbatim in
test-compare.md §3). That heuristic is unsound for two reasons the assets make concrete:

- **It is a fixed constant, not scaled to N.** The same ±0.015 magnitude is quoted at
  n=50 and at n=10 dev (test-compare.md §3) — treated as a constant rather than a
  sampling property that shrinks as √N grows. A correct interval must be a function of
  the score vector and its size.
- **One row is enormous at the dev sizes `spp` actually runs.** spp-test dev slices are
  10–20 rows; "1/15 ≈ 6.7 F1 points" (test-spp-runs.md §6); spp-ex craft missed its
  floor *by one row* (dev 0.9496, short 0.0004; ex-runs.md §1). At these sizes a single
  row swing (≈5–7pp) dwarfs the fixed ±0.015 floor, so the heuristic is fragile exactly
  where it is used.

**Why the deltas it gates are inside the noise.** In spp-ex the single-judge band is
±0.02, *comparable to the iteration-to-iteration dev deltas themselves*: respond iter 2
moved −0.0044 (10 fixed / 11 regressed — explicitly attributed to judge noise), iter 3
moved −0.0400 (ex-runs.md §4, §3; ex-report.md §4.4 item 6). The +0.0024 Opus-vs-
`spp_mini` tie and the +0.0527 framework gap in `spp_compare` are precisely the
comparisons a paired CI would formalize (test-spp-runs.md §6). The point of this
direction is to replace an asserted constant with an interval derived from the data.

### 2. Exactly what to add

Three primitives, all operating on **the per-row score vector that finalize already
computes in its single sacred read** — no new model calls, no second read.

1. **Paired bootstrap CI on the headline test aggregate.** Resample row indices with
   replacement (B resamples, default B=10,000; fixed seed recorded), recompute the
   aggregate per resample, report the 2.5 / 97.5 percentile interval around the point
   estimate. For K>1 this is the per-field primary score vector aggregated under the
   plan's `AGGREGATE_STRATEGY`; for K=1 it is the single classification metric's per-row
   contribution. The "paired" structure matters because the headline comparison is
   *baseline-prompt vs frozen-prompt on the same test rows* — resample the **per-row
   delta** vector (frozen_score[i] − baseline_score[i]) so the row-pairing is preserved
   and the CI is on the improvement, not on two independent means.

2. **Paired permutation test for the headline delta.** Under the null "the frozen prompt
   is no better than baseline on these rows," randomly swap each row's
   (baseline, frozen) score pair with probability 0.5 across P permutations
   (default P=10,000; same recorded seed), build the null distribution of the mean
   paired delta, and report a two-sided p-value. This is the direct answer to spp-ex
   §4.4 item 7. It needs both score vectors on the same test rows, which finalize has.

3. **Per-field CIs as dev diagnostics (K>1).** Bootstrap each field's primary metric on
   the **dev** per-row scores from the frozen iteration's `eval.json`/`results.json`,
   reported as a diagnostic band next to each per-field dev number. This directly serves
   the spp-test small-N regime (a per-field CI on a 10–20-row dev slice makes the
   "1 row ≈ 5pp" fragility visible instead of hidden behind a constant).

**Inputs (named, all already on disk at finalize).** The sacred test per-row scores
come from the single `/spp-finalize` step-4 read (`test_results.json` →
`test_eval.json`); the baseline per-row scores for the paired comparison come from the
same test inference run scored under the baseline prompt (already part of the headline
delta finalize reports). The dev per-row vectors come from the best-iteration
`run_NN/eval.json` / `results.json`. **No prior-iteration artifact, no loop subagent
context, and no second test read is involved.**

**Dependency flag (CLAUDE.md §8).** The bootstrap and permutation primitives are
expressible in **pure Python stdlib + the existing numeric stack** — percentile
extraction, resampling with a seeded `random`/`numpy` RNG, and a mean-delta null loop.
The proposal is to add **no new dependency**: implement on stdlib `statistics`/`random`
(and `numpy` only if it is already a declared dependency of `eval.py`; the assets show
`eval.py` is the only scoring module and v0.1.0/v0.2 added no new deps —
repo-state-convention.md §5). **Do NOT pull in `scipy`** for `scipy.stats` conveniences:
a hand-rolled percentile-bootstrap and a paired-permutation loop are a few dozen lines,
and a new dependency on a large scientific package for two estimators is not justified
under CLAUDE.md §8. If a contributor later argues for `scipy`, it must carry a §8
justification and a `### Added`/`### Changed` CHANGELOG entry.

### 3. Where it lands — the isolation-safe placement

The statistics live in **exactly two places, both outside the loop**:

- **`/spp-finalize` step 4** (compute test-set metrics), which already reads the sacred
  set once and writes `test_eval.json`. The bootstrap CI and permutation p-value are
  computed here, *after* the single read, *from the in-memory per-row score vector*, and
  written as new fields inside `test_eval.json`. Citation:
  repo-skill.md §4 — finalize sacred read is **§4 step 3**
  (`spp-finalize.md:412-468`); metrics computation is **§4 step 4**
  (`spp-finalize.md:470-506`); and repo-skill.md §4 names the slot explicitly:
  *"the natural home is step 4 (compute test-set metrics) emitting an interval into
  `test_eval.json`, surfaced at G5 and REPORT §2 deltas."*
- **`metric-design`** (review-and-record, no verdict gate — DESIGN `:848-857`), which
  records *which* interval each field reports and *that* the dev per-field CI is a
  diagnostic. It does not gate; it documents the choice, consistent with its existing
  documentary-only `revise` posture (repo-design.md §8b).

**Data-flow diagram — the auditor / rule-edit / discrepancy / adversary stages never
see any of it:**

```
                  ┌─────────────────────── /spp-loop (per iteration) ───────────────────────┐
                  │                                                                          │
   discrepancy (step 8)   adversary (step 9)   rule-edit (step 10)   auditor (step 11)       │
   eval.json,             prompt, prior         prompt,              prompt diff,            │
   results.json,          discrepancy,          discrepancy(IDs),    prior discrepancy,      │
   disagreed rows,        plan §2               plan §2,             prior auditor reviews,  │
   plan §2, prompt        [SCORE-BLIND]         architect            plan §2                 │
        │                                       [NO ROW CONTENT]     [SCORE-BLIND]           │
        │                                                                                    │
        └──────────────  NO statistics primitive runs anywhere in this box  ────────────────┘
                                                  │
                            loop produces SUCCESS.md / best-iteration run_NN/
                                                  │
                                                  ▼
                  ┌──────────────────────────── /spp-finalize ──────────────────────────────┐
                  │  step 3: sacred test read ONCE  →  test_results.json                     │
                  │  step 4: score per-row  →  per-row score vector (in memory)              │
                  │            └── bootstrap CI  +  paired permutation p  ── from THAT vector │
                  │            └── write into test_eval.json                                 │
                  │  step 7: REPORT §2 (headline CI + p) ; REPORT §3 dev CIs (diagnostic)    │
                  └──────────────────────────────────────────────────────────────────────────┘
```

The arrow of information flow is strictly loop → finalize. There is no return edge.
Because the CI/p-value are *born* at step 4 of finalize and only ever flow *forward*
into the REPORT, they are structurally incapable of reaching the auditor, rule-edit,
discrepancy, or adversary contexts — those run earlier, in a different phase, with
explicit allow-lists that name their inputs positively
(repo-skill.md §1; loop_spec.md.template:74-82 forbids `auditor_score_access`,
`discrepancy_score_access`, `rule_edit_score_access`, `auditor_frequency_reduction`).

**The central safety property, stated plainly:** *a confidence interval or p-value is a
score-derived quantity; it is computed only at finalize, only after the loop has
terminated, and is never written into any artifact a loop subagent reads — so no
score-derived signal reaches the auditor or the rule-edit stage.* This is the same
reason `eval.json`/`results.json` are withheld from the auditor even though they exist
on disk (DESIGN `:201-210`; auditor.md §2). A CI is *more* score-derived than a raw
score, not less; it therefore inherits the strictest treatment and stays finalize-only.

**Three hard boundaries this placement must honor (each checked):**

- **Auditor score-blindness (invariant #2, preserved verbatim).** No CI, p-value, SE,
  or any derived string enters the loop. The runner's auditor "hint surface is empty by
  design" (repo-skill.md §1), and a CI is exactly the kind of score-derived hint
  auditor.md §2 forbids ("the rule is 'no score signal at all,' not 'no numerical
  score'"). The escape valve for any auditor cost concern remains **batch auditing**,
  never score access and never frequency reduction (DESIGN `:253-261`,
  loop_spec.md.template:82). This direction does not touch that surface at all.
- **Sacred test read exactly once (invariants #6, #7, preserved verbatim).** The
  bootstrap **resamples the per-row score vector already materialized by the single
  step-3/step-4 read** — resampling is an in-memory operation over an already-computed
  array of numbers. It does **not** re-run inference, does **not** re-open
  `test_results.json` from disk a second time, and does **not** touch the test
  partition again. There is no "ranged-prediction surface" and no preview: the test set
  is read once, scored once, and the resampling happens over the resulting scalar vector
  (repo-skill.md §4: finalize is "single test-set evaluation … no 'preview' … no
  ranged-prediction surface" — bootstrapping the *scores* does not violate this because
  it never re-reads the *rows*). The partial-deletion-on-failure rule
  (`spp-finalize.md:444-468`) is untouched.
- **Verdict tokens stay categorical hard tokens (invariant #14, preserved verbatim).** A
  CI or p-value **must not** become an auditor gate, a confidence weight on a verdict, or
  a softening of a categorical/row-specific/unclear token. There is no `auditor_confidence`
  field and adding any confidence/tier is BREAKING (auditor.md §6;
  repo-skill.md §2; DESIGN `:1621-1642`). Statistics inform the **human** at REPORT/G5
  time; they do not gate the loop, do not gate the auditor, and do not weight any
  verdict. The ship-decision tree (§4 step 6) **may surface** the interval next to its
  delta comparisons for the human reading G6, but the deterministic tree's thresholds
  stay as they are in v1 (the `0.05` `dev_test_delta` cutoff and the
  `train_test_delta vs dev_test_delta × 1.5` comparison remain hardcoded v1 defaults —
  repo-skill.md §4). Whether to *replace* those point-estimate thresholds with
  CI-qualified ones is deferred (see §10), because doing so would turn an informational
  number into a gate input and deserves its own design discussion.

### 4. What lands in REPORT and where

- **REPORT §2 (test column — the headline generalization estimate).** The test
  aggregate already reported here (sourced from `test_eval.json`, the sacred set's
  first and only eval — repo-skill.md §4) gains:
  - the **bootstrap CI** on the headline test aggregate (the generalization interval),
  - the **paired permutation p-value** for the baseline→frozen headline delta.
  These are the **headline** statistics: the test CI is the generalization interval a
  reader should quote, and the permutation p answers "is the frozen prompt's
  improvement over baseline distinguishable from noise on the held-out set?" This is the
  exact REPORT location repo-skill.md §4 names ("surfaced at G5 and REPORT §2 deltas").
- **REPORT §3 (loop trajectory — dev-only, diagnostic).** Per-field dev CIs are reported
  here as **dev diagnostics only**, clearly labeled as dev-set bands (REPORT §3 is
  dev-only by contract — repo-skill.md §4, `spp-finalize.md:638-653`). They are not
  generalization claims; they exist to make the small-N fragility of the dev trajectory
  visible (a wide dev CI on a 15-row slice is the honest replacement for the asserted
  ±0.015 floor). The distinction must be explicit in the prose: **test CI = headline
  generalization interval; dev CIs = diagnostics on the noisy dev signal.**
- **§5 invariant block — unchanged and reaffirmed.** REPORT §5 still emits the literal
  line *"Auditor information-isolation invariant: preserved."* (invariant #21,
  REPORT.md.template §5). This direction adds statistics *after* and *outside* the loop,
  so that line remains true and is a useful place to note, in the same audit spirit,
  that the statistics are finalize-only.
- **Synergy with the two forwarded items (note, do not bundle).** The robustness-probe
  (LM-swap → REPORT §2.x table, STATE:126) and cost-ledger (REPORT §8, STATE:127)
  forwarded items are *natural neighbors*: a CI on the robustness-probe row would make
  the one-sided LM-swap comparison (ex-report.md §4.4 item 5) honestly bounded. This is
  worth flagging as a **co-location** in REPORT §2 but should not be scope-coupled here
  — the robustness probe is its own forwarded item with its own design.

### 5. Proposed scope

- **Minimal viable (recommended for the first PR):** primitives 1 and 2 — the paired
  bootstrap CI and paired permutation test on the **headline test delta**, written into
  `test_eval.json` and surfaced in REPORT §2. This is the smallest change that closes
  the verbatim logged gap (STATE:107; spp-ex §4.4 item 7) and is the "cheap to add at
  finalize" item exactly as logged. It is fully runnable today even on the K=1 classifier
  path, because it operates on per-row scores the K=1 `eval.py` already produces.
- **Fuller (same arc or a fast follow):** primitive 3 — per-field dev CIs in REPORT §3.
  This is more valuable for K>1, where the runner scoring is still contract-only
  (repo-skill.md §3), so it is naturally sequenced *after* the K>1 scoring work
  (Direction 3 / bucket-5 `eval.py` generalization) lands a real per-field score vector.
  Until then per-field dev CIs are computable only on the K=1 path; that is fine — ship
  the headline test CI/p first, add per-field dev CIs when there are real per-field
  vectors to bootstrap.
- **Defer the NMI / Cramér's V redundancy aid.** spp-test independently used NMI /
  Cramér's V for **feature-redundancy** analysis (consolidated F4; test-compare.md
  notes it). It is statistical tooling `spp` lacks, but it answers a *different*
  question (are two fields redundant?) than significance-of-improvement, and its natural
  consumer is schema/feature-group design, not the finalize generalization estimate.
  **Argue defer:** it is a metric/schema-design diagnostic, not a significance mechanism;
  bundling it dilutes the tight "close the logged CI/permutation gap" scope. Note it as a
  candidate for a later metric-design diagnostics PR.

### 6. Target version (proposed, not assumed)

**Proposed: ship as a co-shipped additive bucket inside the v1.0 finalize/metrics arc,
recorded as its own `### Added` CHANGELOG entry — not as a standalone version, and not
forced into v0.3.**

Reasoning:

- **§7.1.2 books v0.3 for multi-judge subjective metrics + multilingual** (a separate
  design pass, DESIGN `:1997-2006`; repo-design.md §4). Statistics is *not* either of
  those, so it should not be labeled "v0.3" merely to ride that train, and it does not
  belong to the v0.3 multi-judge design pass.
- **It is closest in spirit to the v0.2 seven-bucket precedent** (repo-state-convention.md
  §4): new bookkeeping/implementation machinery *inside* the existing fixed-output-space
  methodology, additive, shipped as a self-contained PR that slots into the frame
  without disturbing prior buckets. The strongest fit is as **one additive bucket of the
  v1.0 finalize/REPORT-expansion arc** (the same arc that hosts the robustness-probe and
  cost-ledger forwarded items, STATE:126-127), each its own PR.
- **It does not need its own arc.** It is too small (two estimators, no new dependency,
  one finalize step + one REPORT section), and it is independently useful from day one,
  so it should not block on the larger compound-system v1.0 work. If the v1.0 arc opens
  with a `docs(design): pin …` PR (the convention STATE:154 instructs repeating), this
  direction is one downstream additive PR against that pin — or, if v1.0 is far off, a
  v0.3 *point-release* additive PR is acceptable **provided** the entry does not imply it
  is part of the multi-judge design pass.

Net: **target v1.0 as a co-shipped additive finalize bucket; acceptable as a v0.2.x /
v0.3 point release if the maintainer wants it shipped ahead of the compound-system arc.**
The gate should decide between "fold into the v1.0 finalize bucket" and "ship now as a
point release."

### 7. Locked invariants touched

Most are **UNTOUCHED** — that is the whole point of the finalize-only placement.

| # | Invariant | Status | One-line why |
|---|---|---|---|
| 1 | Per-stage isolated subagents | UNTOUCHED | No new input enters any loop subagent's allow-list; statistics run in `/spp-finalize`, not the loop. |
| 2 | Auditor score-access prohibition | UNTOUCHED | CI/p-value are score-derived and computed *after* the loop; never written to any artifact the auditor reads — strictest case, honored. |
| 3 | No row content to rule-edit subagent | UNTOUCHED | Bootstrap operates on scalar score vectors at finalize; no row content, and the rule-edit stage is not in this data path. |
| 4 | Auditor frequency: per-iteration, non-optional | UNTOUCHED | No frequency change; the cost valve remains batch auditing, not score access. |
| 5 | Adversary score-blindness and non-persistence | UNTOUCHED | Adversary runs in the loop with its own allow-list; no statistics reach it, nothing new persists to baseline/splits. |
| 6 | Test rows read exactly once | UNTOUCHED | Resampling is over the already-read in-memory score vector; no second read, no re-inference. |
| 7 | Runner-side test-partition defense-in-depth | UNTOUCHED | No new test-partition access path; partial-deletion-on-failure rule unchanged. |
| 8 | Auditor verdict gate (literal `auditor override`) | UNTOUCHED | No CI/p-value enters the gate logic; gate tokens and substrings unchanged. |
| 9 | Baseline-quality verdict precondition (G2) | UNTOUCHED | Not in this data path. |
| 10 | Schema-designer verdict precondition (G1) | UNTOUCHED | Not in this data path. |
| 11 | HITL gate G1–G6 approval substrings | UNTOUCHED | The interval is informational at G5/G6; approval substrings and gate semantics unchanged. |
| 12 | Six-section prompt structure | UNTOUCHED | No prompt-structure change; this is metrics/REPORT, not prompt content. |
| 13 | Metric independence rule | UNTOUCHED | A CI on an independently-computed metric is still independent; no LLM judge introduced. |
| 14 | Verdict tokens are categorical hard tokens, no confidence weighting | UNTOUCHED (explicitly guarded) | Statistics inform the human at REPORT time; they never weight a verdict, gate the auditor, or add an `auditor_confidence` field. |
| 15 | `plan.md` as contract, re-read fresh | UNTOUCHED | No plan-contract change; `metric-design` records the choice in its existing review-and-record posture. |
| 16 | Atomic checkpoint writes | UNTOUCHED (must comply) | New `test_eval.json` fields must be written via the same `tmp + fsync + rename` discipline. |
| 17 | `MODEL_IDENTIFIER` exact env-var string | UNTOUCHED | No identifier/naming change. |
| 18 | `loop_spec.md` literal-block check | UNTOUCHED | No loop_spec block change; the existing `*_score_access: forbidden` lines already cover the safety boundary. |
| 19 | `/spp-finalize` advances only on SUCCESS (+ one exception) | UNTOUCHED | Advancement conditions unchanged; statistics are computed regardless of the (already-permitted) termination type that reached finalize. |
| 20 | v1 command set closed at four | UNTOUCHED | No new command; lands inside `/spp-finalize`. |
| 21 | REPORT.md.template §5 invariant block verbatim | UNTOUCHED | The "isolation invariant: preserved" line remains true and is reaffirmed by the finalize-only placement. |

No invariant is shape-changed, and none is at risk, provided the three boundaries in §3
are held. The single thing to watch in review is invariant #14: any reviewer-tempting
"use the CI to auto-decide ship/no-ship inside the auditor or the verdict gate" would
breach it and must be rejected.

### 8. Roadmap-vs-non-goal classification

This is **neither a §7.1.2 roadmap-as-listed item nor a §7.1.3 deliberate non-goal.**

- **Not §7.1.2-as-listed.** The §7.1.2 roadmap names multi-judge metrics (v0.3),
  multilingual (v0.3), cross-model synthesis (v0.4), and loop resumption (TBD)
  (repo-design.md §4). Statistics is none of these. It is, however, an *explicitly logged
  forwarded gap* (STATE:107) — i.e. already-sanctioned future work, just not on the
  §7.1.2 enumerated list.
- **Not a §7.1.3 non-goal.** The non-goals are generation, tool-use/agentic, RAG,
  prompt-injection defense, automated-search *fusion*, auditor frequency reduction, and
  LLM-as-judge under the independence rule (repo-design.md §5). Significance testing on
  per-row scores is none of these. Critically, it does **not** fuse proposal-and-
  selection (the §7.1.3(e) move that breaks isolation) — it adds no selection signal to
  the loop at all; it only describes the final estimate to the human.
- **What it actually is.** New finalize/metric-design machinery *inside* the existing
  fixed-output-space methodology — the same category as Direction 3's `number→MAE/RMSE`
  ("blocker is implementation, not methodology"). Per repo-state-convention.md §4,
  statistics is "new bookkeeping/implementation work inside the existing fixed-output-
  space methodology, closest in spirit to the v0.2 seven-bucket precedent," and the
  §7.1.3 closing rule ("when in doubt, lean toward roadmap rather than deliberate")
  confirms the lean. It is roadmap-flavored additive work, ship it as an additive bucket.

### 9. CHANGELOG implication

**Almost certainly NOT breaking** — it is purely additive at finalize (new fields in
`test_eval.json`, new lines in REPORT §2/§3, a documentary note in `metric-design`),
loosens no contract, and removes/weakens no invariant.

Entry shape (following the patterns in repo-state-convention.md §5):

- An **`### Added`** entry naming the *file*, the *what*, and the *why*:
  the bootstrap CI + paired permutation test computed at `/spp-finalize` step 4 from the
  single sacred-read per-row score vector, surfaced in REPORT §2 (headline test CI + p)
  and REPORT §3 (dev per-field CIs as diagnostics); closes the logged gap STATE:107 /
  spp-ex §4.4 item 7.
- A **methodology note** (CLAUDE.md §5 requires it because this touches the auditor's
  isolation surface *by deliberately staying outside it* and touches test-set handling):
  state explicitly that **the statistics are finalize-only, never reach any loop
  subagent, do not gate the auditor or any verdict (invariant #14 preserved verbatim),
  and resample the already-read score vector without a second test read (invariants #6/#7
  preserved verbatim).** This is the "preserved verbatim / shape status" sentence the
  CHANGELOG convention expects.
- A **"No new dependencies"** note (repo-state-convention.md §5 shows the scripts PR did
  exactly this), explicitly recording the decision *not* to add `scipy`.
- **No `BREAKING CHANGE:` prefix.** If a later PR proposes letting a CI qualify the
  ship-decision thresholds (see §10), *that* PR would be methodology-affecting and would
  carry the breaking/methodology treatment — this one does not.

### 10. Open design questions for the gate

1. **Does the bootstrap CI / permutation p ever inform the ship-decision tree
   (§4 step 6), or stay purely descriptive in REPORT §2?** Surfacing the interval next
   to the existing point-estimate thresholds (the `0.05` `dev_test_delta` cutoff,
   `train_test_delta vs dev_test_delta × 1.5`) is safe and informational; *replacing*
   those thresholds with CI-qualified gates turns an informational number into a gate
   input and is itself a methodology-affecting change. Recommend: descriptive-only in v1,
   defer the gate question.
2. **Bootstrap resample count and seed policy.** Default B=P=10,000; seed recorded in
   `test_eval.json` for reproducibility. Is a recorded fixed seed the right call, or
   should the seed be derived from `MODEL_IDENTIFIER` + split hash for determinism across
   re-finalize attempts (which are friction-gated anyway)?
3. **Aggregate-strategy interaction for K>1.** The headline CI must be computed on the
   per-row aggregate under the plan's `AGGREGATE_STRATEGY` (`macro` / `weighted` /
   `min`). For `min` (the bottleneck-field strategy), a bootstrap of a min-over-fields is
   well-defined but its interval is asymmetric and wide — confirm that reporting it
   honestly (rather than smoothing) is the intent.
4. **Sequencing vs Direction 3.** Per-field dev CIs (primitive 3) are only meaningful
   once the runner produces per-field score vectors (currently K=1-only,
   repo-skill.md §3). Should primitive 3 be explicitly sequenced *after* the K>1
   `eval.py` generalization, with the minimal-viable headline test CI/p shipped first on
   the K=1 path?
5. **Co-location with the robustness-probe / cost-ledger forwarded items.** Should the
   v1.0 finalize arc bundle CI + robustness-probe + cost-ledger into one REPORT §2/§8
   expansion bucket (shared "REPORT generalization-and-cost surface" PR), or keep each a
   separate additive PR? Bundling shares the §2 table work; separating keeps each gap's
   provenance clean.
6. **Paired vs unpaired permutation when the baseline scores are unavailable.** The
   paired test requires baseline-prompt per-row test scores on the same rows. If a future
   finalize path does not score the baseline on test (only the frozen prompt), the
   permutation test degrades to a one-sample bootstrap of the frozen aggregate against the
   headline criterion. Confirm the baseline-on-test scoring is reliably present (it is
   part of the current headline-delta computation) or specify the fallback.
