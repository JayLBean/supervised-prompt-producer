# Consolidated findings across spp experimental assets

Deliverable 1 of the v0.3-arc planning task. Synthesizes the three Pass-A asset
findings files (`spp-repo.md`, `spp-ex.md`, `spp-test.md`) and their ten
`detail/` deep-dives into one cross-asset picture. Every quantitative claim is
tagged **[cited]** (external source the asset cites), **[reproduced-by-us]**
(computed inside the asset's own harness), or **[provenance-unclear]**.
Confidentiality follows DESIGN §7.2: aggregate metrics and failure-cluster
*shapes* are citable; spp-test row content / labels / prompt IP are not, and are
abstracted throughout. PUPA (spp-ex) is a public MIT benchmark and is quoted
freely.

---

## 1. What each asset is

- **spp repo (v0.2.0)** — the methodology under development. Current state: the
  v0.2 "bookkeeping generalization" shipped (single-output classification →
  multi-field structured output / hierarchical labels / freeform extraction with
  structured ground truth). The methodology principles are output-shape-agnostic;
  the load-bearing lock is **per-stage information isolation** (DESIGN §4.2). The
  §7.1.1 inventory lists **21 named locked invariants**. Crucially, the runnable
  `eval.py` is still v0.1.0-shaped: `SUPPORTED_METRICS = {"f1","accuracy",
  "precision","recall"}` (`skills/run/scripts/eval.py:32`) — K>1 multi-field and
  every non-classification metric (MAE/RMSE/exact-match/set-F1/IoU) are
  **specified in prose but not implemented**. No bootstrap/CI/permutation code
  exists anywhere (grep-verified).

- **spp-ex** — an external "justification report" benchmarking spp v0.2 (agentic +
  HITL, Opus orchestrator) against a **[cited]** DSPy/GEPA optimizer on the public
  **PUPA/PAPILLON** privacy-rewriting task (n=214 sacred test). Two task tracks
  (`papillon-craft` = minimize PII leakage; `papillon-respond` = maximize judge
  quality) run through the v0.2 feature-group-split workaround. Student
  `gpt-4.1-nano`, judge `gpt-4.1`.

- **spp-test** — a multi-arm **NDA-domain** (hair-loss social-media annotation)
  research workspace, the internal proving ground. Holds: a 31-field multi-aspect
  structured-annotation task run four ways (monolithic-v6 prompt / 7-group batched
  split / DSPy+GEPA / genuine spp framework runs incl. an `spp_mini` API
  reimplementation), plus a separate binary relevance-filter task that is a real
  spp `/init→/loop→/finalize` run across multiple models, plus a feature audit
  (`AUDIT_PATH.md`, `FEATURE_AUDIT.md`).

---

## 2. Convergent cross-asset findings (the load-bearing conclusions)

These hold across *both* external (PUPA) and internal (hair-loss) data — the
strongest signal for where the next arc's leverage is.

**F1 — The framework effect beats model choice; spp's edge is real but
isolation-bounded.**
- spp-test: `spp_mini` (API reimplementation of the loop) beats the DSPy-compiled
  prompt by **+0.0527 composite at the *same* optimizer model** [reproduced-by-us];
  Opus-driven spp over `spp_mini` is only **+0.0024** (inside noise). Cross-eval
  decomposition: prompt/schema *structure* is a bigger lever (**+0.051** group-split
  vs monolithic, fixed model) than *model choice* (**+0.030**) [reproduced-by-us].
- spp-ex: spp joint composite **0.8306** [reproduced-by-us] vs DSPy baseline
  **0.765** [cited] vs GEPA **0.861** [cited] — "closes 68.3 % of the
  baseline→GEPA gap," explicitly **not** a head-to-head win.

**F2 — DSPy/GEPA's structural failure is the absence of a revert/audit gate.**
- spp-test DSPy arm: GEPA improved only 1 of 7 feature groups (A +0.060); the other
  6 regressed (unweighted mean ≈ 0.737 → 0.708, ≈ **−0.029**) [reproduced-by-us],
  with no mechanism to revert a regressing edit. This is precisely the overfitting
  the spp auditor's categorical-vs-row-specific verdict + revert gate exist to
  catch. DSPy also cost ~14× more for the optimization [reproduced-by-us, proxied
  pricing].
- This is direct empirical support for the §7.1.3(e) non-goal (search/auto-edit
  *fusion* is incompatible by construction) — the asset shows *why*.

**F3 — Feature-group splitting is the single highest-value prompting structure,
and it already exists in spp.**
- spp-test compare: 7-group batched beats the monolithic 31-field prompt by
  **+0.085 composite** [reproduced-by-us], Pareto-better (≈3× faster, ~15% cheaper
  warmed). A sharper decomposition finding: batching *itself* is score-neutral and
  flat-canonical formatting *hurts* (−0.111); the quality win is the **split**,
  whose mechanism is **populating conditional/dependent fields the monolith leaves
  empty** (a cardinality/under-prediction story, not raw per-field accuracy).
- spp already ships this as **feature-group prompt splitting** (DESIGN §10,
  designer §5.0, `examples/feature-group-split/`). Direction-1's "multi-prompt
  split" must **reconcile with the existing feature, not duplicate it** — and
  must respect the locked boundary "cross-task composition is out of `spp`'s scope"
  (`DESIGN.md:2322-2328`).

**F4 — The statistics gap is universal, already logged, and bites hardest at
small N.**
- Repo: no bootstrap/CI/permutation anywhere; `eval.py` emits point estimates only.
  Logged verbatim at `STATE-as-of-v0.2.0.md:107`: *"No bootstrap CIs / paired
  permutation tests on row-level scores. Same limit as the prior `spp_compare`.
  Cheap to add at finalize."*
- spp-ex: `metric.py`/`eval.py` emit exactly 4 keys, no SE/CI; §4.4 item 7 [cited
  self]: *"No paired-permutation test against cited GEPA — feasible but not done."*
  Judge noise (±0.02) is **comparable to iteration-to-iteration dev deltas** —
  significance is needed to tell real movement from noise.
- spp-test: significance handled by an **informal heuristic** — a ±0.015 "noise
  floor" and "Δ > 5× noise floor" prose (verbatim `monolithic_vs_batched.md:25`),
  a fixed constant *not* scaled to sample size. At dev sizes of 15–20 rows **one
  row ≈ 5 pp**, so the heuristic is fragile exactly where it's used.
- spp-test also independently uses **NMI / Cramér's V** for feature-redundancy
  analysis — statistical tooling spp does not provide.

**F5 — Continuous/ordinal demand is real but latent; no asset has a true
continuous target, and no asset can *measure* an ordinal fix.**
- spp-test schema: of 31 fields, **three are conceptually ordinal but typed as flat
  `single_select` and scored by exact-match singleton Jaccard**: an
  intensity scale, a journey-stage progression, and an age-bucket scale. Documented
  **ordinal-drift** failure (a ±1 error scores identically to a max-distance miss;
  FEATURE_AUDIT Pattern C: mild↔moderate confusion 17×). An **anchored-CoT** fix
  (reason a 0–10 raw score, then map to label) is drafted and wired into the schema
  — but **its benefit is unmeasurable under the current exact-match metric**. This
  couples direction 1 (technique) to direction 3 (metric).
- spp-test "soft labels" (`labelled_features_soft_v3.json`) are **NOT** continuous —
  scanned, zero floats; they are a hard-primary + alternative-acceptable set for
  partial-credit Jaccard. The continuous demand is purely latent.
- spp-ex: PUPA's leakage axis is a **continuous `1−leakage` score folded into a
  binary composite** [reproduced-by-us] — a natural home for a regression/continuous
  output mode. 5 of 9 spp metric primitives sat dormant on this K=1 binary-judge task.
- Repo: `metric-design` SKILL **specifies** `number → MAE/RMSE` and it sits *inside*
  the §7.1.3 fixed-output-space boundary (NOT a non-goal); the blocker is purely
  implementation (`eval.py` can't score it; `_schemas.py` `EvalJSON` is K=1-shaped).

**F6 — A catalogue of prompting sub-techniques is empirically pre-validated in
spp-test, all expressible as schema/output-form metadata.**
The hair-loss audit converged on four structural techniques, each already realized
as schema metadata in the genuine spp run `hair-loss-annotation-v2`
(`output_form` values: `per_label_binary` ×4, `gated_per_label_binary` ×4,
`gated_single_select` ×1):
  1. **Feature-group split** (F3).
  2. **Per-label binary / one-vs-rest (OvR)** for multi-label fields (Pattern B).
  3. **Gated-boolean** (an is-addressed gate + conditional sub-labels) for
     "default-attractor" fields that hallucinate when forced (Pattern A: attractors
     fired 7–32× spuriously).
  4. **Anchored-CoT** for ordinals (F5).

**F7 — Per-stage isolation held in practice, with one documented deviation worth
hardening.** spp-ex `respond` iter 1 ran the auditor as an **in-context allow-list
fallback** ("no spawnable Agent tool available") rather than a process-isolated
subagent (`run_01/auditor_review.md:5`, verbatim). Score-blindness was never
breached; iters 2–3 were re-isolated; craft was isolated throughout. `spp_mini`
similarly collapses stages into in-process functions but keeps the auditor
score-blind by construction. STATE:106 already flags this as a *runner-implementation*
concern, not a methodology weakness — candidate to promote to an explicit error
condition.

---

## 3. Gap → direction mapping

| Gap (source) | Dir 1 (prompting) | Dir 2 (statistics) | Dir 3 (continuous/ordinal) |
|---|---|---|---|
| Feature-group split is the real lever (F3) | ✓ reconcile w/ existing | | |
| Per-label OvR / gated-boolean pre-validated (F6) | ✓ | | |
| Anchored-CoT drafted but unmeasurable (F5) | ✓ (CoT) | | ✓ (needs ordinal metric) |
| DSPy regresses w/o revert gate (F2) | ✓ (motivates audit) | ✓ (significance-gated revert) | |
| No CI/bootstrap/permutation anywhere (F4) | | ✓ **primary** | |
| ±0.015 heuristic noise floor not N-scaled (F4) | | ✓ | |
| Small-N dev: 1 row ≈ 5pp (F4) | | ✓ | |
| 3 ordinal-as-categorical fields, ordinal drift (F5) | | | ✓ **primary** |
| Continuous leakage folded to binary (F5, spp-ex) | | | ✓ |
| `number→MAE/RMSE` spec'd, not implemented (F5) | | | ✓ |
| NMI/Cramér's V used externally (F4) | | ✓ (optional redundancy aid) | |

---

## 4. Direction-specific verdicts (preview — Pass-B sections elaborate)

- **Dir 1 (more prompting techniques):** *Roadmap, mostly additive, with two
  BREAKING sub-items.* "Multi-prompt split" ≈ existing feature-group split →
  reconcile/document, don't duplicate. Per-label-binary/OvR and gated-boolean are
  new `output_form` values inside the schema layer (additive). **CoT and few-shot
  are BREAKING**: both change `<output_format>` / example-pair cardinality, touching
  the locked six-section structure (invariant #12) and the auditor's review surface.
  Cite techniques (CoT: Wei 2022 arXiv:2201.11903; OvR: Tsoumakas & Katakis 2007;
  self-consistency: Wang 2022 arXiv:2203.11171; least-to-most: Zhou 2022
  arXiv:2205.10625) — and honestly flag **CoT-can-hurt** on non-math classification
  (Sprague 2024 arXiv:2409.12183): make CoT a dev-confirmed hypothesis, not a default.

- **Dir 2 (more statistical mechanisms):** *Already a logged gap; the cleanest,
  lowest-risk arc.* Lands at **`/spp-finalize` + `metric-design`**, finalize-only so
  the **auditor stays score-blind** (invariant #2) and the **sacred test set is read
  exactly once** (invariant #6). Adds bootstrap CIs + paired permutation tests on the
  per-row scores already persisted, surfacing into REPORT §2 deltas. Touches no
  isolation contract if kept out of the loop.

- **Dir 3 (more supported modes — continuous/regression/ordinal):** *Roadmap
  generalization, NOT a non-goal* — `number` fields with MAE/RMSE sit inside the
  fixed-output-space boundary (`DESIGN.md:2026-2036`, 723-726). New output *shape*
  beyond classification + structured fields. F1/balanced-accuracy don't apply;
  MAE/RMSE/correlation/ordinal-distance do; the auditor's categorical-vs-row-specific
  judgment **changes shape** (a regression rule edit isn't "categorical vs
  row-specific" in the same sense — open design question). Highest invariant-surface
  contact of the three.

---

## 5. Provenance & confidentiality notes

- **spp-ex / PUPA:** public MIT benchmark; all numbers quotable. spp = 0.8306
  [reproduced-by-us]; DSPy 0.765 / GEPA 0.861 [cited]; optimizer token ratio
  ~3.1× (spp ~1.55M Opus vs GEPA ~500K) [cited-estimate]; cost ledger $10.64 /
  14,057 calls [reproduced-by-us, judge ~65%]. `.env` present, not read.
- **spp-test:** NDA-domain. All metrics reported are aggregate; field taxonomy is
  reported by *type and cardinality* only; the monolithic baseline prompt, the
  per-group prompts, label values, and row content are described by structure/shape
  and **not reproduced**. The one ordinal hack (`mild≡moderate` scoring equivalence)
  is reported as methodology, not content. `.env` present, not read.
- **spp repo:** open-source MIT; quoted freely with file:line refs.
- Methodology note (CLAUDE.md §8 honored): nothing in this synthesis loosens
  per-stage isolation, auditor score-blindness, the rule-edit no-row-content rule,
  or the sacred test set; no invariant is reclassified and no non-goal is silently
  promoted to roadmap.
