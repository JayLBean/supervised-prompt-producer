# `spp-ex` report.qmd — deep narrative & exhaustive gaps extraction

Companion deep-dive to [`assets-findings/spp-ex.md`](../spp-ex.md). Read that first.
This file goes deeper on the report's narrative/limitations side and makes the
gaps list exhaustive and verbatim. Source asset:
`/Users/jiafuli/Desktop/Project/spp-ex/`. Primary doc read end-to-end:
`/Users/jiafuli/Desktop/Project/spp-ex/report.qmd` (420 lines).

Citation tags: `[cited]` = external (DSPy `gepa_papillon` tutorial / GEPA paper /
Databricks blog); `[reproduced-by-us]` = computed by this study's harness against
the sacred 214-row test; `[cited-estimate]` = the study's own tag for an external
inference (rollout counts × public pricing), not a measurement;
`[provenance-unclear]` = neither external-cited nor reproduced by this harness
(the `spp_compare` hair-loss prior-data referent). PUPA is a public MIT HuggingFace
benchmark (`Columbia-NLP/PUPA`, `pupa_new`); quoting it is fine.

---

## Item 1 — EXHAUSTIVE limitations / gaps / future-work list (highest-value)

Every limitation, caveat, asymmetry, deviation, and future-work mention in
`report.qmd` and `FINDINGS.md`, quoted close-to-verbatim, each with a one-line
gloss on its spp-roadmap implication. Grouped by source location. **27 distinct
items.** No item is summarized away.

### A. report.qmd §4.4 "Limitations and v0.2 status" (the canonical list, VERBATIM)

Preamble (verbatim): "spp v0.2 is **explicitly under development** and several
limitations are documented as feature-gaps rather than methodological flaws:"

1. **"Compound-system bookkeeping is contract-only.** The feature-group-split
   workaround (two task directories with frozen inter-module data flow) was
   deployed here; v0.2+ requires a `compound-system` sub-skill specifying
   inter-module data-flow, per-module upstream-frozen-input declarations, and
   joint REPORT trajectories."
   → *Highest-priority gap. §4.4 closing line attributes the entire −0.030
   residual to this (sequential vs joint optimization). This is the v1.0 feature
   that would enable a fair head-to-head.*

2. **"Per-field auditor verdicts not exercised.** Both modules in this study are
   K=1 single-string output; v0.2's per-field auditor and per-field discrepancy
   clustering surface is contract-only."
   → *spp's core leverage points were dormant on PUPA; the framework's claimed
   edge is untested on this task shape.*

3. **"Auditor process-isolation guarantee was deviated once** (respond iter 1,
   Agent tool unavailable). v0.2+ should make the in-context fallback an error
   condition."
   → *Directly touches the DESIGN §4.2 isolation invariant; the methodology lock
   was bent once and should be hardened into an error condition.*

4. **"Single task, N = 214.** External validity is narrow; this is a case study,
   not a benchmark with significance claims."
   → *Bounds every quantitative claim; motivates more datasets/modes.*

5. **"One-sided robustness probe.** The LM-swap row exists only spp-side; a
   symmetric comparison would require running the GEPA tutorial under the swap."
   → *The robustness axis (spp's claimed edge) lacks a comparison arm.*

6. **"Single-judge LLM-as-judge** introduces noise; population means over n = 214
   average it but per-row scores are not reliable."
   → *Per-row judge noise (±0.02 band) is comparable to iter-to-iter dev deltas;
   motivates multi-judge or statistical treatment.*

7. **"No paired-permutation test** against cited GEPA — feasible but not done."
   → *Direct hook for the "more statistical mechanisms" direction; explicitly
   flagged as feasible and omitted.*

8. **"DSPy/GEPA cost figures are estimates**, not direct measurements (per user
   direction to skip reproduction)."
   → *The cost comparison is asymmetric and the cited estimate may undercount
   (see §3.3.1).*

§4.4 closing line (verbatim): "The performance gap to cited GEPA (0.030) is
plausibly attributable to limitation 1 (sequential vs joint optimization).
Closing this gap is the highest-priority v0.2+ work surfaced by this study."

### B. report.qmd §4.7 "Limitations of this study as a framework comparison"

§4.7 opens (verbatim): "the comparison is structurally unfavorable to spp v0.2".
It presents a 9-row property table (spp design center vs PUPA). Each row that
PUPA fails is a not-exercised primitive:

9. **K=1 single-string output** per module (PUPA) vs **K > 1 (31 fields)**
   (design center). → *PUPA collapses the multi-field surface spp is built for.*
10. **No per-field weighted composite** on PUPA (design center: "Yes").
    → *The weighting leverage point is dormant.*
11. **No schema-constrained output** on PUPA ("free-form text") vs design center
    "Yes (JSON with `accepted_per_label`)". → *No OUTPUT_SCHEMA exercised.*
12. **2 modules (compound)** on PUPA vs **1** (design center); "Compound-system
    bookkeeping needed: Yes" → unshipped. → *Same as item 1 from the table angle.*
13. **Per-field auditor verdicts not exercised** ("task-level only").
    → *Same as item 2, restated in the comparison table.*
14. **Per-field discrepancy clustering not exercised** on PUPA.
    → *The discrepancy-clustering leverage point is dormant.*
15. **No soft / partial-credit scoring** ("binary judge") vs design-center "soft
    Jaccard". → *Binary judge can't express partial credit; motivates a
    soft/continuous scoring mode.*
16. **Train-overfit failure mode salvageable by revert: "Lower leverage"** on
    PUPA vs "Yes (high leverage)" in design center. → *spp's revert-on-regression
    conservatism mechanism has little to bite on with K=1.*

§4.7 verbatim count: "**Five of nine load-bearing spp primitives are not
exercised on PUPA; one (compound-system bookkeeping) is needed but not yet
shipped in v0.2.** The 0.030 gap to cited GEPA is the cost of operating outside
the design center with a partial framework. A v1.0 release supporting first-class
compound systems and per-field auditor verdicts on the respond-quality side should
re-run this benchmark to obtain a fair head-to-head; we predict (without claiming)
that the residual gap would narrow or close."

### C. report.qmd §2.7 "Asymmetries" (named explicitly, VERBATIM)

17. "The cited GEPA numbers come from the DSPy `gepa_papillon` tutorial; spp's
    optimizer is Claude Opus 4.7 + HITL — **the optimizers are not equivalent.**"
    → *Framework-vs-framework, not optimizer-vs-optimizer; forbids "spp beats
    GEPA".*
18. "The LM-swap row is **spp-side only** (the cited tutorial does not probe LM
    swap)." → *Same as item 5, stated as a method asymmetry up front.*
19. "DSPy/GEPA cost figures are `[cited-estimate]`, not direct measurements, per
    user direction to skip reproduction." → *Same as item 8.*
20. "Sacred test rows were opened twice (once per task directory's
    `/spp-finalize`); optimization loops never read them." → *Honest disclosure;
    each task dir finalize opens the sacred set once. A real compound-system
    sub-skill would open it once jointly.*

### D. report.qmd §1 Introduction — Non-claims (VERBATIM)

21. "**Non-claims.** We do not claim spp beats GEPA head-to-head on PUPA; the
    cited GEPA result uses a different optimizer and the LM-swap row is one-sided.
    We do not generalize from one task (N = 214) to all multi-field IE. A fair
    head-to-head awaits a v1.0 re-run with first-class compound-system
    bookkeeping." → *The report self-polices the "not a head-to-head win" framing;
    every headline number must be read against this.*

### E. report.qmd §4.3 — cost of flexibility (a limitation of the spp axis)

22. "The cost of this flexibility is real: **12 synchronous gate decisions require
    ~2 hours of user attention** across the procedure. GEPA runs unattended."
    → *HITL is a human-time cost; the inspectability axis is not free. Roadmap
    implication: batch-audit / async-gate ergonomics to reduce attention load.*

### F. report.qmd §3.3 + §3.3.1 — cost-ledger caveats

23. Ledger-vs-dashboard drift (verbatim §3.3): "The ~4% drift is attributable to
    (i) ledger over-counting on retried calls that did not bill at OpenAI and
    (ii) pricing-table rounding in `harness/metric.py:PRICES`. The dashboard
    figure is authoritative." → *The self-built ledger is an approximation; only
    the OpenAI dashboard total ($10.64) is authoritative.*
24. DSPy cost-transparency caveat (verbatim §3.3.1): "The cited PUPA
    `gepa_papillon` tutorial does not publish a directly-measured cost figure; the
    `[cited-estimate]` row in §4.2 is therefore an inference from rollout counts
    and public per-token pricing, and **is plausibly an undercount for the same
    reason**" (prior `spp_compare` saw DSPy `run_metadata.json` report $1.20 vs
    ~$5.00 actual, ~4× undercount, the delta being hidden reflection-LM spend).
    → *The optimizer-cost comparison is asymmetric and the GEPA side may be
    understated; not reproduced here.*

### G. FINDINGS.md §9 "What's structurally missing for a publication-grade comparison"

(Overlaps A/B but adds new framing.) Opens (verbatim): "the following gaps are
inherent to spp v0.2 and will appear in the final report as **stated limitations**,
not hidden assumptions:"

25. **"No unified OUTPUT_SCHEMA on the spp side.** PUPA's metric is composite over
    two implicit dimensions (quality + leakage) which the DSPy tutorial treats as
    free-text outputs. spp could reformulate as JSON schema but that breaks
    cite-only matching. We match the tutorial." → *PUPA's multi-field character
    lives in the metric, not the output; a JSON reformulation would have broken
    citation-matching. Motivates a schema mode that can coexist with cite-only
    eval.*
26. **"No bootstrap CIs / paired permutation tests on row-level scores.** Same
    limit as `spp_compare`; **can be added cheaply at finalize.**" → *Reconfirms
    the statistical-inference gap as a known, cheap-to-close omission — the
    cleanest hook for a statistics mechanism.*

(FINDINGS §9 also restates: feature-group splitting for the 2-module pipeline
[= item 12]; per-field auditor verdicts not exercised [= item 2/13]; single task
[= item 4].)

### H. FINDINGS.md §4 — `spp_compare` prior limits carried over (`[provenance-unclear]`)

From the prior hair-loss study's `FRAMEWORK_JUSTIFICATION_REPORT.md` §5, quoted in
FINDINGS §4 and inherited by this report via §4.6:

27. **Missing 2×2 cell — "GEPA+Opus not run"** (the principal residual confounder
    in the prior study). → *The prior in-design-center win (+0.0527) is not a
    fully-controlled 2×2; GEPA-at-Opus was never run, so the framework-effect
    attribution has one open confounder.*

FINDINGS §4 also lists, as prior-study limits (sub-items of the carried-over set):
small val set n=15, noise floor ±0.015; greedy field selection got stuck on
`F_treatment_attitude`; no statistical inference (= same as item 26); external
validity unverified (single task, = item 4); reflection-LM token saturation at
large prompts. These are `spp_compare` properties, not this study's runs, hence
`[provenance-unclear]` for this asset.

### I. Honest run-time deviations (gate logs / REPORTs / §2.4 — roadmap-relevant though not in §4.4)

These are documented procedure deviations, not framed as "limitations" but
load-bearing for the spp implementation roadmap:

- **Dry-run row-count deviation:** dry-run used 1 dev row instead of the canonical
  3 train rows (both modules). → *The spp dry-run contract was bent; harness
  should enforce canonical dry-run shape.*
- **Prompt-format adapter needed:** `harness/extract_prompt.py` adapter was
  required because spp's `prompt_v(N).md` format differs from the harness's
  flat-XML expectation. → *Format-interop friction between spp output and external
  eval harnesses.*
- **Discrepancy CLI signature mismatch:** `scripts/discrepancy.py` CLI signature
  mismatched the harness emission (expected `per_row.csv`; harness emitted
  `results.json`/`eval.json`), so discrepancy content was orchestrator-written
  under allow-list discipline rather than tool-generated. → *Tooling drift around
  the discrepancy stage; the allow-list discipline was preserved manually.*
- **PII per-row dump deletion:** one craft `per_row.csv` was `rm -rf`'d before
  commit (aggregate metrics preserved from transcript). → *PII-hygiene action;
  aggregate provenance survived but raw per-row provenance for that one eval is
  gone.*
- **Auditor in-context fallback (= item 3, restated as the §2.4 deviation):**
  respond iter 1 ran the auditor under in-context allow-list discipline because
  the Agent tool was unavailable; re-validated by iter 2's process-isolated
  auditor.

---

## Item 2 — Every headline metric, tagged

Composite on the 214-row sacred test (`report.qmd` §3.1; verified against committed
`metrics.json`):

| Configuration | Composite | Quality | 1−Leakage | Tag |
|---|---:|---:|---:|---|
| DSPy zero-shot baseline | **0.765** | — | — | **[cited]** (DSPy tutorial; 163.71/214) |
| DSPy + GEPA-optimized | **0.861** | — | — | **[cited]** (DSPy tutorial; 184.26/214) |
| spp-craft + DSPy-baseline-respond | 0.8033 | 0.6682 | 0.9384 | [reproduced-by-us] |
| **spp-craft + spp-respond (JOINT)** | **0.8306** | 0.7290 | 0.9321 | **[reproduced-by-us]** |
| spp-frozen on `gpt-4o-mini` (LM swap) | 0.8667 | 0.7710 | 0.9625 | [reproduced-by-us, LM-swap, one-sided] |
| un-opt craft + spp respond (hypothesis) | 0.6741 | 0.7150 | 0.6332 | [reproduced-by-us] |

Note: the joint row's `metrics.json` reports `mean_leakage = 0.0679` (so 1−leakage
= 0.9321) and `mean_composite = 0.8306`. The LM-swap row reports `mean_leakage =
0.0375` (1−leakage = 0.9625), `quality_rate = 0.7710`, `mean_composite = 0.8667`.
The hypothesis row reports `mean_leakage = 0.3668` (1−leakage = 0.6332).

- **Joint composite [reproduced-by-us]:** **0.8306**. Δ vs cited baseline 0.765 =
  **+0.0656**; Δ vs cited GEPA 0.861 = **−0.0304**. Framed as "closes **68.3%** of
  the 0.096 cited baseline→GEPA gap." Two `*`-marked head-to-head rows on the
  locked student stack are the joint 0.8306 and the LM-swap 0.8667.
- **Per-track numbers:**
  - **craft track** (Module 1, objective 1−leakage): frozen at iter 1, dev
    `1−leakage = 0.9496`; clean test composite (spp craft + DSPy-baseline respond)
    **0.8033** [reproduced-by-us].
  - **respond track** (Module 2, objective quality): frozen at iter 1, dev
    `quality_rate = 0.7289`; joint test `quality_rate = 0.7290` [reproduced-by-us].
- **LM-swap result [reproduced-by-us, one-sided]:** frozen spp prompts on
  `gpt-4o-mini` → **0.8667** (+0.0361 over on-stack). Verbatim caveat in §3.1: "This
  score numerically exceeds cited GEPA 0.861 but is NOT a head-to-head row:
  different local LM." Explicitly **NOT a head-to-head win**.
- **What is explicitly NOT a win:** §1 non-claims ("We do not claim spp beats GEPA
  head-to-head"), §2.7 ("the optimizers are not equivalent"), §3.1 LM-swap caveat,
  §4.5 ("GEPA wins on automation, reproducibility, and serving cost shape").
- **Hypothesis test [reproduced-by-us]:** un-opt craft + spp respond = 0.6741;
  Δ quality vs joint −0.0140 (within ±0.02 judge noise); entire composite drop from
  leakage (1−leakage −0.2989). Verdict: "spp's respond prompt is craft-invariant";
  "Hypothesis 'spp gap is over-redaction' is **falsified**"; residual is structural.
- **Secondary citations [cited]** (GEPA paper Table 1, divergent protocol): Qwen3-8B
  PUPA 80.82 → 91.85 (GEPA+Merge 86.26); GPT-4.1-mini PUPA 78.57 → 94.47 (GEPA+Merge
  96.46). The gpt-4.1-mini row uses gpt-4.1-mini as the *local* student (paper),
  whereas the tutorial/locked stack uses it as the *untrusted* LM — setup-divergent.
- **`spp_compare` in-design-center referent [provenance-unclear]** (§4.6, prior
  report, not this study's runs): DSPy baseline 0.6921; DSPy+GEPA 0.6770 (regressed
  below baseline); spp_mini 0.7297; spp_Opus/v6 0.7321. spp_mini **+0.0527** over
  DSPy+GEPA at matched `gpt-5.4-mini` optimizer, ~7.5× cheaper ($0.66 vs ~$5.00
  actual / $1.20 reported).

---

## Item 3 — Cost-ledger breakdown, tagged

**Authoritative ground truth (OpenAI dashboard, §3.3):** **$10.64 over 14,057 API
calls** [reproduced-by-us, authoritative].

**Self-built ledger attribution table (§3.3, by bucket):**

| Bucket | n_calls | Dollars | Tag |
|---|---:|---:|---|
| Iter-time dev evals (craft + respond) | 4,725 | $1.33 | [reproduced-by-us] |
| Module-1 precompute (train + dev) | 1,800 | $0.61 | [reproduced-by-us] |
| Dry-runs + smoke tests | 28 | $0.01 | [reproduced-by-us] |
| Sacred-test reads (craft clean + joint) | 2,456 | $0.85 | [reproduced-by-us] |
| Robustness probe (gpt-4o-mini swap) | 642 | $0.32 | [reproduced-by-us] |
| Hypothesis-test experiment | 881 | $0.77 | [reproduced-by-us] |
| **LLM-as-judge (gpt-4.1)** | **3,516** | **$7.16** | **[reproduced-by-us]** |
| **Ledger total** | **14,048** | **$11.05** | |
| Dashboard total | 14,057 | $10.64 | [authoritative] |
| Drift (ledger − dashboard) | −9 | +$0.41 | ~4% |

**Judge-cost dominance:** the `gpt-4.1` judge is the single largest line item —
**$7.16 of the $11.05 ledger total (~65%)** in the §3.3 bucket table.

**Independent re-aggregation of the raw `ledger.csv` (14,065 summed n_calls,
$11.0509 total), grouped by MODEL** (slightly different cut than the §3.3 bucket
table, which splits the judge from other gpt-4.1 use):

| Model | calls | dollars |
|---|---:|---:|
| `gpt-4.1` (judge + any reflection-side) | 3,736 | $7.6772 |
| `gpt-4.1-mini` (untrusted LM) | 3,286 | $2.0207 |
| `gpt-4.1-nano` (local student) | 6,598 | $1.1936 |
| `gpt-4o-mini` (LM-swap probe) | 428 | $0.1594 |
| `claude-opus-4-7` (orchestrator, logged rows) | 17 | $0.00 |

The by-model `gpt-4.1` total ($7.68 / 3,736 calls) is slightly higher than the
§3.3 "LLM-as-judge" bucket ($7.16 / 3,516 calls) because the bucket table isolates
only judge calls; either way `gpt-4.1` is the dominant spend. The 17 logged
`claude-opus-4-7` rows carry **$0** — the orchestrator cost is absorbed by the
subscription and not metered into the ledger dollars.

**Optimizer-side token comparison (§3.3):**

| Side | optimizer tokens | Tag |
|---|---:|---|
| spp (Claude Opus 4.7 completion tokens) | **~1,551,651** | [reproduced-by-us, token count only — in/out split and $ not exposed; subscription absorbs cost] |
| GEPA (`gpt-4.1` reflection-LM tokens) | **~500,000** | **[cited-estimate]** |
| **Ratio (spp / GEPA)** | **~3.1×** | |

Verbatim conclusion: **spp uses ~3.1× MORE optimizer tokens than GEPA.** "GEPA wins
on raw optimizer-token efficiency on PUPA-shape tasks" (§4.2).

**Marginal-cost claim (§3.3.1, §4.2):** for a user already on a flat Claude
subscription (Pro $20/mo, Max $100/mo, Max $200/mo — stated, not amortized), spp's
marginal optimizer cost is **$0**; total marginal = **$10.64** OpenAI inference (a
cost both frameworks pay). GEPA's reflection-LM spend is metered per task. The
§4.2 table:

```
                | OpenAI inference  | Optimizer cost      | Total marginal
DSPy/GEPA       | not measured      | ~500K gpt-4.1       | metered per-task
                | [cited-estimate]  | tokens              |
spp (Claude sub)| $10.64            | $0 marginal         | $10.64
spp (no sub)    | $10.64            | $20-200/mo flat     | $10.64 + flat
```

**DSPy cost-transparency caveat** (§3.3.1): prior `spp_compare` found DSPy
`run_metadata.json` reported $1.20 vs ~$5.00 actual (~4× undercount, hidden
reflection-LM spend); the PUPA `[cited-estimate]` GEPA cost is "plausibly an
undercount for the same reason." **Not reproduced on PUPA.**

---

## Item 4 — Bearing on the three planned spp directions

### (a) More prompting techniques

spp on PUPA was confined to **categorical rule additions** in the six-section XML.
Both modules plateaued fast (craft 2 iters, respond 3) and several auditor-approved
categorical rules **regressed** the dev signal:

- respond iter 2 (Rule 4): dev delta **−0.0044**.
- respond iter 3 (Rule 5): dev delta **−0.0400**.
- craft iter 2: termination `early-stop-floor-unmet` — auditor verdict
  `redundant-with-iter-1`, plateau + craft-objective regression.

§4.4/§3.2 record that the auditor (score-blind) returned `categorical / keep /
advance` while the dev signal regressed — "not contradictions but different forms
of evidence." The persistent-failure clusters (short-token PII ≤3 chars, refusal-
target mimicry, depth-undershoot) are framed as categorically uncatchable by the
v0.2 rule surface. **Implication:** the existing technique (single-rule additions)
was exhausted, not the task — a richer technique inventory (few-shot exemplars,
structured decomposition, register/length control) could move the residual the
rule-only surface could not.

### (b) Statistical mechanisms — EXPLICITLY OMITTED (verbatim quotes)

The study **computed no** bootstrap, CI, permutation test, significance test, or
standard error — only point estimates. Named twice as a limitation:

> §4.4 item 7 (verbatim): "**No paired-permutation test** against cited GEPA —
> feasible but not done."

> FINDINGS.md §9 item 4 (verbatim): "**No bootstrap CIs / paired permutation tests
> on row-level scores.** Same limit as `spp_compare`; **can be added cheaply at
> finalize.**"

§4.4 item 6 (verbatim): "Single-judge LLM-as-judge introduces noise; population
means over n = 214 average it but per-row scores are not reliable." The hypothesis
test treats Δ quality −0.0140 as "within ±0.02 judge-noise band" — i.e., the judge
noise band is comparable to the iter-to-iter dev deltas, exactly where CIs /
permutation tests would change the read. **Strong, clean motivation for a
statistics mechanism.**

### (c) Continuous / regression outputs — the leakage axis IS a continuous score (verbatim)

PUPA's composite mixes a **binary** judge with a **continuous** leakage fraction:

> §2.3 / metric (verbatim): "`leakage = num_pii_leaked / len(pii)` # 0 if pii is
> empty"; "`composite = (quality + (1 - leakage)) / 2`".

So `leakage ∈ [0,1]` is continuous; the craft track effectively optimized a
continuous `1 − leakage` objective even though spp v0.2's metric surface is built
for classification. §4.7's property table marks PUPA as **"No"** for "Soft /
partial-credit scoring" ("binary judge") and **"No"** for "Per-field weighted
composite" — i.e., the continuous leakage dimension is folded into a single scalar
composite and the quality dimension is collapsed to a binary. **Implication:** a
regression / continuous-output mode has a natural home — PUPA's leakage fraction
(and design-center soft-Jaccard per-field scores) are continuous targets the
current K=1 classification framing collapses.

---

## Item 5 — Compound-system / sequential-vs-joint attribution (how the residual gap is attributed)

The report attributes the **entire −0.030 residual to cited GEPA** to
sequential-vs-joint optimization, not to prompt insufficiency. Verbatim chain:

> §4.1 (verbatim): "Two factors plausibly explain the residual gap:
> 1. **Baseline-quality structural cap on PUPA respond.** PUPA's `target_response`
>    field contains 9.3% refusal labels and 28.4% duplicate-cluster rows … The
>    achievable `quality_rate` is capped at ~0.91; spp's 0.7290 reaches ~80% of
>    that ceiling.
> 2. **v0.2 compound-system bookkeeping gap.** spp v0.2 lacks first-class
>    multi-module orchestration; we executed sequential optimization (craft frozen
>    → respond finalized) rather than joint optimization against the end-to-end
>    composite. The cited GEPA result is jointly optimized."

> §4.1 (verbatim): "The hypothesis test (§3.1) **falsifies one candidate
> explanation — over-redaction** — by showing that spp's respond prompt is
> craft-invariant. The residual gap is therefore **structural rather than
> methodological.**"

> §4.4 closing (verbatim): "The performance gap to cited GEPA (0.030) is plausibly
> attributable to limitation 1 (**sequential vs joint optimization**). Closing
> this gap is the highest-priority v0.2+ work surfaced by this study."

> §4.7 (verbatim): "A v1.0 release supporting first-class compound systems and
> per-field auditor verdicts on the respond-quality side should re-run this
> benchmark to obtain a fair head-to-head; we **predict (without claiming) that
> the residual gap would narrow or close.**"

> Abstract (verbatim): "A v1.0 release with first-class compound-system
> bookkeeping should re-run this benchmark to obtain a fair head-to-head."

**Mechanism of the gap:** the PROTOCOL §5 optimization order is **craft → freeze →
respond, never iterating back** ("This is a deliberate constraint to keep the
dependency graph clean and the spp run bounded"). respond's `llm_request` /
`llm_response` inputs are precomputed from craft's frozen prompt. GEPA optimizes
the two modules **jointly against the end-to-end composite**; spp optimized them
**sequentially** because v0.2 has no compound-system sub-skill. That architectural
difference — not a weaker prompt — is the report's named cause of the residual,
and the central v1.0 roadmap item.

---

## Provenance / confidentiality (unchanged from companion file)

- PUPA / PAPILLON is public MIT (`Columbia-NLP/PUPA`, `pupa_new`) — fine to quote.
- All `[reproduced-by-us]` numbers trace to committed `metrics.json` under
  `spp/.../sacred_test_eval/`; all `[cited]` to `citations/cited_rows.yaml`.
- `[cited-estimate]` is the study's own tag (GEPA ~500K reflection tokens; GEPA
  cost row) — external inference, not measurement.
- `spp_compare` hair-loss numbers (+0.0527, ~7.5× cheaper) are an internal prior
  report (`spp_compare_prior_data`); **[provenance-unclear]** for this asset —
  neither external-cited nor reproduced by this harness.
- Databricks IE Bench: cited **narratively for framing only, never for numbers**.
- `.env` exists at `/Users/jiafuli/Desktop/Project/spp-ex/.env`; **not read, no
  secret printed**. PII-bearing `per_row.csv` dumps are deliberately uncommitted;
  only aggregate `metrics.json` present.
