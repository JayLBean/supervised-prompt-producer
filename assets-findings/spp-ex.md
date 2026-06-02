# Asset findings: `spp-ex` — PUPA / PAPILLON comparison study (spp vs DSPy/GEPA)

Source asset: `/Users/jiafuli/Desktop/Project/spp-ex/`
Extracted, not re-derived. Every quantitative result is tagged
`[cited]` (from an external paper/tutorial the study cites),
`[reproduced-by-us]` (computed by the study's own harness against the
sacred test set), `[cited-estimate]` (the study's own tag: an external
inference from rollout counts × public pricing, not a direct
measurement), or `[provenance-unclear]`.

---

## What it is

An external "justification report" benchmarking the **spp** framework
(v0.2, agentic + human-in-the-loop) against the **DSPy/GEPA** automated
prompt optimizer on the **PUPA / PAPILLON** privacy-preserving query
rewriting task. Primary artifact:
[`/Users/jiafuli/Desktop/Project/spp-ex/report.qmd`](file:///Users/jiafuli/Desktop/Project/spp-ex/report.qmd).
Scaffolding: `PLAN.md`, `FINDINGS.md`, `PROTOCOL.md`.

- **Design / comparison axis.** Hold the student model and dataset
  fixed; vary only the optimization *framework* (spp vs DSPy/GEPA). The
  study explicitly does **not** reproduce the DSPy/GEPA side — those
  numbers are `[cited]` from the public DSPy `gepa_papillon` tutorial
  (per user direction, `PROTOCOL.md` §6, §9). It is a framework-vs-framework
  case study, **not** an optimizer-vs-optimizer controlled trial, and the
  report repeatedly forbids a "spp beats GEPA" framing (`report.qmd`
  §1 non-claims, §4.5).
- **Two task tracks (the 2-module PUPA pipeline, split into two spp task
  dirs per the v0.2 feature-group-split workaround):**
  - `papillon-craft/` — Module 1 `CraftRedactedRequest`: `user_query →
    llm_request`. Objective: minimize PII leakage (reported as
    `1 − leakage`).
  - `papillon-respond/` — Module 2 `RespondToQuery`:
    `(user_query, llm_request, llm_response) → response`. Objective:
    maximize judge quality. Its `llm_request`/`llm_response` inputs are
    precomputed from craft's **frozen** prompt. Optimization order is
    craft → freeze → respond, never iterating back (`PROTOCOL.md` §5).
- **Models (`FINDINGS.md` §7, `cited_rows.yaml`):**
  - Local student LM (both modules): `gpt-4.1-nano`.
  - Untrusted external LM (between modules): `gpt-4.1-mini`.
  - LLM-as-judge (quality bool): `gpt-4.1`, single-shot.
  - GEPA reflection LM (cited side only): `gpt-4.1`.
  - spp "optimizer": Claude Code agent, **Claude Opus 4.7** + HITL.
  - Robustness-probe swap: local LM → `gpt-4o-mini`.
  - Note: the task asked whether the model was "gpt-4-1-nano" — yes, the
    run directory is named `gpt-4-1-nano` and the local student is
    `gpt-4.1-nano`.
- **Dataset.** PUPA / PAPILLON, `Columbia-NLP/PUPA`, config `pupa_new`,
  664 rows, **MIT-licensed, public HuggingFace benchmark** — fine to
  quote. Refs: PAPILLON paper arXiv 2410.17127; GEPA paper arXiv
  2507.19457; DSPy tutorial <https://dspy.ai/tutorials/gepa_papillon/>.
- **Metric (verbatim from the DSPy tutorial,
  [`harness/metric.py`](file:///Users/jiafuli/Desktop/Project/spp-ex/harness/metric.py)):**
  `quality = LLM_judge(...) → bool`; `leakage = num_pii_leaked /
  len(pii)` (0 if no PII); `composite = (quality + (1 − leakage)) / 2`.

---

## Locked configuration

(`FINDINGS.md` §7, `PROTOCOL.md` §2; gate logs.)

- **Splits** (DSPy tutorial verbatim, deterministic index slices, seed 0,
  no stratification): Train `[0:225]` (225), Dev `[225:450]` (225),
  **Test `[450:664]` = 214 rows, sacred** — opened only at
  `/spp-finalize`, never during the loop. (Opened twice in total, once
  per task dir's finalize; loops never read it — `report.qmd` §2.7.)
- **Iteration counts / gates.** 5 spp-loop iterations total across the
  two modules; **12 recorded HITL gate decisions**:
  - **craft**: 2 iterations. Frozen at **iter 1**. Termination
    `early-stop-floor-unmet` (composite plateau + craft-objective
    regression + auditor verdict `redundant-with-iter-1`). Gates
    G1–G6 all APPROVED/SHIP
    ([`spp/papillon-craft/gate_log.md`](file:///Users/jiafuli/Desktop/Project/spp-ex/spp/papillon-craft/gate_log.md)).
  - **respond**: 3 iterations. Frozen at **iter 1**. Termination
    `dev-plateau` (2 consecutive sub-threshold iters: −0.0044, −0.0400).
    Gates G1–G6 all APPROVED/SHIP
    ([`spp/papillon-respond/gate_log.md`](file:///Users/jiafuli/Desktop/Project/spp-ex/spp/papillon-respond/gate_log.md)).
- **Frozen prompts** (hashed, byte-pinned):
  - craft `PROMPT_FROZEN_v01.md`, SHA-256 `428c47d8…` (3 categorical
    rules: named-entity replacement, identifier-shape, presidio-placeholder).
  - respond `PROMPT_FROZEN_v01.md`, SHA-256 `c84943f4…` (Rules 1–3:
    re-inject specifics, match reference scope, answer-from-user_query-when-refused).
- **Floors** (per-field, K=1): craft `1 − leakage ≥ 0.95` (UNMET);
  respond `quality_rate ≥ 0.95` (UNMET). Both shipped `ship-with-caveats`
  because the gaps are argued to be structural metric/label ceilings, not
  prompt insufficiency.
- **Baseline-quality ceilings, surfaced *before* optimization** (G2
  override path on both modules):
  - craft: gold-label self-inconsistency 10/225 (4.4%) → gold ceiling
    `mean(1−leakage) = 0.978`; short-token PII (≤3 chars) 30/225 (13.3%);
    case-insensitive metric.
  - respond: refusal-style `target_response` 21/225 (9.3%); duplicate
    `(query, target)` clusters 64/225 (28.4%) → effective distinct N ≈
    192; multilingual content 27.6% non-ASCII. Estimated structural cap
    on `quality_rate` ≈ **0.91**.
- **Pipeline runtime re-implemented** in
  [`harness/pipeline.py`](file:///Users/jiafuli/Desktop/Project/spp-ex/harness/pipeline.py)
  (not DSPy's runtime) so the only experimental variable is the prompt
  pair (`PROTOCOL.md` §3).

---

## Headline results (tagged)

Composite on the 214-row sacred test (`report.qmd` §3.1; verified against
the committed `metrics.json` files):

| Configuration | Composite | Quality | 1−Leakage | Tag |
|---|---:|---:|---:|---|
| DSPy zero-shot baseline | **0.765** | — | — | **[cited]** (DSPy tutorial; 163.71/214) |
| DSPy + GEPA-optimized | **0.861** | — | — | **[cited]** (DSPy tutorial; 184.26/214) |
| spp-craft + DSPy-baseline-respond | 0.8033 | 0.6682 | 0.9384 | [reproduced-by-us] |
| **spp-craft + spp-respond (JOINT)** | **0.8306** | 0.7290 | 0.9321 | **[reproduced-by-us]** |
| spp-frozen on `gpt-4o-mini` (LM swap) | 0.8667 | 0.7710 | 0.9625 | [reproduced-by-us, LM-swap, one-sided] |
| un-opt craft + spp respond (hypothesis test) | 0.6741 | 0.7150 | 0.6332 | [reproduced-by-us] |

- **Headline comparative result [reproduced-by-us vs cited]:** spp joint
  composite **0.8306** vs cited baseline **0.765** (Δ **+0.0656**) vs
  cited GEPA **0.861** (Δ **−0.0304**). The study frames this as
  "closes **68.3%** of the cited baseline→GEPA gap" with a residual
  **−0.030** to cited GEPA. **Not a head-to-head win**; the GEPA number
  is `[cited]`, the spp number is `[reproduced-by-us]`, and the
  optimizers differ (Claude Opus 4.7 + HITL vs GEPA reflection LM).
- **LM-swap robustness [reproduced-by-us, one-sided]:** frozen spp
  prompts on `gpt-4o-mini` reach **0.8667** (+0.036 over on-stack). This
  numerically exceeds cited GEPA 0.861 but is explicitly **not** a
  head-to-head row (different local LM; cited tutorial never probes a swap).
- **Hypothesis test [reproduced-by-us]:** un-opt craft + spp respond =
  0.6741; quality only −0.014 vs joint, entire composite drop from
  leakage (+0.299). Conclusion: spp's respond prompt is craft-invariant;
  "gap is over-redaction" **falsified**; residual gap is structural.
- **Secondary citations [cited]** (GEPA paper Table 1, different protocol
  — `cited_rows.yaml`): Qwen3-8B PUPA 80.82→91.85; GPT-4.1-mini PUPA
  78.57→94.47. Flagged as setup-divergent (paper uses gpt-4.1-mini as the
  *local* student, the tutorial as the *untrusted* LM).

### Cost-ledger headline

Ground truth = OpenAI dashboard (`report.qmd` §3.3):

- **Direct OpenAI inference spend: $10.64 over 14,057 API calls**
  [reproduced-by-us, authoritative]. The judge (`gpt-4.1`) dominates:
  $7.16 of $11.05 ledger total. Ledger
  ([`artifacts/ledger.csv`](file:///Users/jiafuli/Desktop/Project/spp-ex/artifacts/ledger.csv),
  14,065 data rows) reconciles to the dashboard within ~4% drift
  (ledger $11.05 / 14,048 calls), attributed to retried calls and judge
  re-runs not billed.
- **Optimizer-side token comparison:** spp = Claude Opus 4.7 ≈
  **1,551,651** completion tokens [reproduced-by-us, token count only —
  in/out split and $ not exposed; subscription absorbs cost] vs GEPA ≈
  **500,000** `gpt-4.1` reflection tokens **[cited-estimate]**. Ratio
  ≈ 3.1× (spp uses *more* optimizer tokens).
- **Marginal-cost claim:** for a user already on a flat Claude
  subscription (Pro $20 / Max $100–$200 per month, stated not amortized),
  spp's marginal optimizer cost is **$0**; total marginal = **$10.64**
  OpenAI inference. GEPA's reflection-LM spend is metered per task.
  GEPA still wins raw optimizer-token efficiency on PUPA-shape tasks
  (`report.qmd` §4.2, §4.5).
- **DSPy cost-transparency caveat (`report.qmd` §3.3.1, §4.6):** the
  prior `spp_compare` hair-loss study found DSPy's `run_metadata.json`
  reported $1.20 while actual billing was ~$5.00 (~4× undercount; the
  delta was hidden reflection-LM spend). The PUPA `[cited-estimate]` GEPA
  cost is therefore plausibly an undercount. **Not reproduced here.**

In-design-center reference (`spp_compare` hair-loss, 31 fields; quoted in
`report.qmd` §4.6 as a prior data point, **not** part of this study's
runs): spp_mini **+0.0527** composite over DSPy+GEPA at matched optimizer
model, at ~7.5× lower billed cost. Tagged in the source as
`spp_compare_prior_data`; treat as **[provenance-unclear]** here — it is
neither cited-external nor reproduced by *this* harness; it is an
internal prior report this study cites by reference.

---

## Surfaced gaps / limitations

These are the gaps the study itself already named. Reproduced
close-to-verbatim from `report.qmd` §4.4, §4.7, and `FINDINGS.md` §9,
each with a one-line gloss on why it matters for the spp roadmap. **This
is the load-bearing section for downstream planning — it is complete.**

From `report.qmd` §4.4 (limitations and v0.2 status):

1. **Compound-system bookkeeping is contract-only.** The feature-group-split
   workaround (two task dirs, frozen inter-module data flow) was used; a
   real `compound-system` sub-skill is needed (inter-module data-flow,
   per-module upstream-frozen-input declarations, joint REPORT
   trajectories). → *Highest-priority gap; the study attributes the
   entire −0.030 residual to sequential-vs-joint optimization. This is
   the v1.0 feature that would enable a fair head-to-head.*
2. **Per-field auditor verdicts not exercised.** Both modules are K=1
   single-string output; v0.2's per-field auditor / per-field discrepancy
   clustering is contract-only. → *spp's core leverage points were dormant
   on PUPA; the framework's claimed edge is untested on this task shape.*
3. **Auditor process-isolation guarantee was deviated once** (respond
   iter 1, Agent tool unavailable → in-context allow-list fallback; iters
   2–3 re-isolated). v0.2+ should make the in-context fallback an *error
   condition*. → *Directly touches the DESIGN §4.2 isolation invariant;
   the methodology lock was bent once and should be hardened.*
4. **Single task, N = 214.** External validity is narrow; a case study,
   not a benchmark with significance claims. → *Bounds every quantitative
   claim; motivates more datasets/modes.*
5. **One-sided robustness probe.** The LM-swap row exists spp-side only; a
   symmetric comparison would require running the GEPA tutorial under the
   swap. → *The robustness axis (spp's claimed edge) lacks a comparison
   arm.*
6. **Single-judge LLM-as-judge introduces noise;** population means over
   n=214 average it but per-row scores are not reliable. → *Per-row
   judge noise (±0.02 band) is large relative to the iter-to-iter dev
   deltas; motivates multi-judge or statistical treatment.*
7. **No paired-permutation test against cited GEPA — feasible but not
   done.** → *Direct hook for the "more statistical mechanisms"
   direction; explicitly flagged as cheap and omitted.*
8. **DSPy/GEPA cost figures are estimates, not direct measurements**
   (per user direction to skip reproduction). → *The cost comparison is
   asymmetric and the cited estimate may undercount (see §3.3.1).*

From `report.qmd` §4.7 (limitations of this study as a framework
comparison) — **five of nine load-bearing spp primitives are not
exercised on PUPA**, one is needed but unshipped:

9. **K=1 single-string output** (vs design-center K>1, 31 fields).
10. **No per-field weighted composite** exercised.
11. **No schema-constrained output** (free-form text, no JSON OUTPUT_SCHEMA).
12. **2 modules (compound)** vs design-center 1 — needs compound-system
    bookkeeping (unshipped).
13. **No per-field discrepancy clustering** exercised.
14. **Binary judge scoring**, not soft / partial-credit (no soft Jaccard).
15. **Train-overfit-salvageable-by-revert leverage is lower** on PUPA.
    → *Together these say PUPA is structurally outside spp's design
    center; the comparison is deliberately unfavorable and the read is
    "near-parity outside the design center," not a loss.*

From `FINDINGS.md` §9 (structurally missing for a publication-grade
comparison), overlapping but adds:

16. **No unified OUTPUT_SCHEMA on the spp side** — PUPA's "multi-field"
    character lives in the metric, not the output; reformulating as JSON
    would break cite-only matching.
17. **No bootstrap CIs / paired permutation tests on row-level scores**
    (same gap as `spp_compare`; "can be added cheaply at finalize"). →
    *Reconfirmed: the statistical-inference gap is a known, cheap-to-close
    omission.*

From `FINDINGS.md` §4 (`spp_compare` prior limits, carried over):

18. Missing 2×2 cell (GEPA+Opus never run — principal residual
    confounder in the prior study).
19. Greedy field selection can get stuck.
20. Reflection-LM token saturation at large prompts.

Also recorded as honest deviations (gate logs / REPORTs, not §4.4 but
roadmap-relevant): dry-run used 1 dev row instead of canonical 3 train
rows (both modules); `harness/extract_prompt.py` adapter was needed
because spp's `prompt_v(N).md` format differs from the harness's flat-XML
expectation; `scripts/discrepancy.py` CLI signature mismatched the
harness emission (per_row.csv vs results.json/eval.json), so discrepancy
content was orchestrator-written under allow-list discipline; one craft
per_row.csv was `rm -rf`'d before commit (aggregate metrics preserved
from transcript).

---

## Relevance to the three planned directions

**(a) More prompting techniques.** spp on PUPA was confined to
*categorical rule additions* in the six-section XML; both modules
plateaued quickly (craft 2 iters, respond 3) and several auditor-approved
categorical rules *regressed* the dev signal (respond Rule 4 −0.0044,
Rule 5 −0.0400). The persistent-failure clusters (short-token PII,
refusal-target mimicry, depth-undershoot) are described as
*categorically uncatchable* by the rule surface available in v0.2 — i.e.,
the existing technique was exhausted, not the task. This is direct
evidence that a richer technique inventory (few-shot exemplars,
structured decomposition, register/length control beyond a single rule)
could move the residual the rule-only surface could not.

**(b) More statistical mechanisms.** The study **computed none** and
explicitly **flagged their absence**. Confirmed by inspecting
[`harness/metric.py`](file:///Users/jiafuli/Desktop/Project/spp-ex/harness/metric.py)
and the whole `harness/` tree: there is **no** bootstrap, confidence
interval, permutation test, significance test, or standard error — the
harness emits only point estimates (`mean_composite`, `quality_rate`,
`mean_leakage`). The report names this twice as a limitation
(§4.4 item 7 "No paired-permutation test against cited GEPA — feasible
but not done"; `FINDINGS.md` §9 item 4 "No bootstrap CIs / paired
permutation tests … can be added cheaply at finalize"). The judge-noise
band (±0.02) is acknowledged to be comparable to the iter-to-iter dev
deltas, which is *exactly* the situation where CIs/permutation tests
would change the read. **Strong, clean motivation for a statistics
mechanism.**

**(c) More supported modes / continuous outputs.** PUPA's composite mixes
a **binary** quality judge with a **continuous** leakage score
(`leakage = num_pii_leaked / len(pii)` ∈ [0,1]); `composite =
(quality + (1 − leakage)) / 2`. So the leakage axis is *already a
continuous, non-classification score* — the craft track effectively
optimized a continuous `1 − leakage` objective, even though spp v0.2's
metric surface is built for classification. This is a live data point
that a **regression / continuous-output mode** would have a natural home:
PUPA's leakage fraction (and per-field soft scores in the design-center
hair-loss task, soft Jaccard) are continuous targets the current K=1
classification framing collapses. The report notes spp "additionally
reports composite" as a reference metric precisely because the native
`one_minus_leakage` field is continuous and the binary judge is the
foreign part.

---

## Provenance / confidentiality notes

- **PUPA / PAPILLON is a public, MIT-licensed HuggingFace benchmark**
  (`Columbia-NLP/PUPA`, `pupa_new`). Content is fine to quote; the report
  and `cited_rows.yaml` treat it as public throughout.
- **No NDA / confidential source feeds the quantitative results.** All
  `[reproduced-by-us]` numbers trace to committed `metrics.json` under
  `spp/.../sacred_test_eval/`; all `[cited]` numbers trace to
  `citations/cited_rows.yaml` with source URLs and accessed dates. The
  only proprietary thing *referenced* is the Databricks IE Bench
  (internal, deltas-only) — cited **narratively for framing only, never
  for numbers** (`FINDINGS.md` §5, `cited_rows.yaml` `databricks_blog_framing`).
- **The `spp_compare` hair-loss numbers** (+0.0527, ~7.5× cheaper) come
  from an internal prior report
  (`~/Desktop/Project/spp-test/spp_compare/FRAMEWORK_JUSTIFICATION_REPORT.md`),
  tagged `spp_compare_prior_data`. Internal but not NDA; used as a
  case-study referent, not cross-task evidence. Treat as
  **[provenance-unclear]** for this asset's purposes (neither
  cited-external nor reproduced by this harness).
- **`.env` exists** at `/Users/jiafuli/Desktop/Project/spp-ex/.env`
  (361 bytes; holds OpenAI keys per the reproducibility checklists). It
  was **not read and no secret was printed**. Per-row dumps
  (`per_row.csv`) contain PUPA PII and are gitignored / not committed;
  not read here beyond confirming their absence/headers.
- **PII-bearing per-row outputs are deliberately uncommitted** across the
  run dirs; only aggregate `metrics.json` are present. The study's own
  confidentiality discipline matches spp DESIGN.md §7.2.
