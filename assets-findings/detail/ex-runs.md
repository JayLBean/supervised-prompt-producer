# `spp-ex` deep-dive: the actual PUPA run artifacts and harness code

Companion to [`../spp-ex.md`](../spp-ex.md). That file is the framing-level
extract; this file goes to the concrete configured/run/reproduced layer with
`file:line` references. Quantitative tags: `[cited]` (external paper/tutorial),
`[reproduced-by-us]` (computed by the study's own harness against the sacred test
set), `[provenance-unclear]`. PUPA/PAPILLON is public (MIT, `Columbia-NLP/PUPA`),
so quoting row IDs and rule text is fine.

Source roots:
- `/Users/jiafuli/Desktop/Project/spp-ex/spp/papillon-craft/`
- `/Users/jiafuli/Desktop/Project/spp-ex/spp/papillon-respond/`
- `/Users/jiafuli/Desktop/Project/spp-ex/harness/`

---

## 1. Exact loop configuration per track

Splits are identical across both tracks: PUPA `pupa_new`, deterministic index
slices, seed 0, no stratification, **Train 225 [0:225] / Dev 225 [225:450] /
Test 214 [450:664], test sacred until `/spp-finalize`**
(`papillon-craft/config/plan.md:111`, `:147-156`;
`papillon-respond/config/plan.md:149-158`;
`papillon-craft/gate_log.md:68-72`). Both `loop_spec.md` set `MAX_ITERATIONS: 8`
(`papillon-craft/config/loop_spec.md:13`, `papillon-respond/config/loop_spec.md:13`),
`Temperature: 0`, `Concurrency: 4`, retry 3× exp-backoff. Craft `MAX_TOKENS` 1500
(`papillon-craft/config/loop_spec.md:73`); respond 2000
(`papillon-respond/config/loop_spec.md:73`). **Adversary: off on both**
(`papillon-craft/config/loop_spec.md:49`; `papillon-respond/config/loop_spec.md:49`).
Auditor config string is the locked `per-iteration, no-score-access` on both
(`papillon-craft/config/plan.md:171`; plan validation rule 8 at `:248-249`).

### craft (Module 1, `CraftRedactedRequest`, objective `1 − leakage`)

- **2 iterations; frozen at iter 1** (prompt_v02, 3 categorical rules:
  named-entity replacement, identifier-shape replacement, presidio-placeholder).
  `papillon-craft/gate_log.md:148-191`; `REPORT.md:22-23`.
- **Floor:** `mean(1 − leakage) ≥ 0.95` (`config/plan.md:91-93`). Plateau
  threshold `<0.005` for 2 consecutive iters; overfit guard `train−dev > 0.10`
  for 2 iters (`config/loop_spec.md:21-23`).
- **Termination cause:** `early-stop-floor-unmet` — three signals fired at iter 2:
  composite plateau (`+0.0022 < 0.005`), craft-objective **regression**
  (`1−leakage −0.0044`), and auditor verdict `redundant-with-iter-1`
  (`gate_log.md:155-167`; `REPORT.md:23`). Floor was missed at iter 1 by **one
  row** (dev `0.9496`, short 0.0004); the user explicitly overrode the auto-stop
  to "examine harder" (`gate_log.md:132-138`).
- Gates G1–G6 all APPROVED/SHIP; G2 via the baseline-quality `revise` override
  path (`gate_log.md:11-232`).

### respond (Module 2, `RespondToQuery`, objective `quality_rate`)

- **3 iterations; frozen at iter 1** (prompt_v02, Rules 1–3: re-inject specifics,
  match reference scope, answer-from-user_query-on-refusal).
  `papillon-respond/gate_log.md:187-234`; `REPORT.md:84-87`.
- **Floor:** `quality_rate ≥ 0.95` (`config/plan.md:93-95`). Same plateau / overfit
  thresholds on the `quality_rate` field (`config/loop_spec.md:21-23`).
- **Termination cause:** `dev-plateau` — two consecutive sub-threshold iters
  (iter 2 `−0.0044`, iter 3 `−0.0400`) (`gate_log.md:207-218`; `REPORT.md:23`).
  Iters 2 and 3 each added an auditor-approved categorical rule (Rule 4
  request-unit anchoring, Rule 5 conversational-register mirroring) that the
  auditor passed on merit but that **regressed dev** — the cleanest illustration
  in either track that the auditor is not a score-proxy (`REPORT.md:103`, `:152`).
- Inter-module sequencing: respond's `/spp-baseline` is gated on craft reaching
  G5/G6 because `llm_request_frozen` / `llm_response_frozen` are precomputed from
  craft's `PROMPT_FROZEN_v01.md` (SHA-256 `428c47d8…`) routed through
  `gpt-4.1-mini` (`config/plan.md:113`, `:199`; `gate_log.md:14`).
- Gates G1–G6 all APPROVED/SHIP; G2 via the baseline-quality `revise` override
  path (`gate_log.md:11-298`).

Both tracks were optimized by **Claude Opus 4.7** as the spp agent
(`harness/log_subagent.py:27` defaults `model="claude-opus-4-7"`); local student
`gpt-4.1-nano`, untrusted external `gpt-4.1-mini`, judge `gpt-4.1`
(`harness/pipeline.py:13-14`, `harness/metric.py:19`).

---

## 2. Per-stage isolation in practice — and the verified deviation

The run artifacts **do** show discrepancy → rule-edit → auditor as separate,
allow-listed stages, with `edit_rationale.md` as the per-edit companion the
auditor reads (so the auditor never needs the discrepancy subagent's row
access). Each `auditor_review.md` carries an explicit "Inputs consulted
(allow-list)" / "Inputs withheld" / "What I did not consider" disclosure naming
`eval_*/metrics.json`, `per_row.csv`, `baseline.csv`, `plan.md §11`,
`gate_log.md`, `REPORT.md` as withheld — i.e., score-blindness is documented at
the artifact level, not just asserted (craft iter 1
`run_01/auditor_review.md:6-21`, `:111-122`; respond iter 2
`run_02/auditor_review.md:6-19`, `:98-109`; respond iter 3
`run_03/auditor_review.md:8-22`, `:111-122`).

The rule-edit stage's no-row-content discipline is visible in
`papillon-craft/run_01/edit_rationale.md`: it maps each rule to discrepancy
**pattern types and counts** ("Pattern 3 `single_token_proper_noun_verbatim`,
51/91") and runs its own synthetic-rows test, never quoting row content
(`edit_rationale.md:5-13`). Per `REPORT.md` the row content was read transiently
for clustering by the chain subagent and "not embedded in persistent artifact"
(`papillon-respond/REPORT.md:142`).

### Verdict on the flagged deviation: CONFIRMED (respond iter 1 only)

The v1 summary's "process-isolation deviation in respond iter 1 (in-context
fallback)" is **confirmed by the artifact itself**. `papillon-respond/run_01/
auditor_review.md:5` states verbatim:

> "(inline sub-subagent invocation; no spawnable Agent tool available in this
> environment, so the audit is conducted by the iteration's subagent under the
> auditor's five operational guarantees applied to its own context: allow-list
> inputs only, no eval/results/metrics consulted from this point, stateless
> against prior runs, no score-derived hints, no test-set artifacts)."

That is an **in-context allow-list fallback**, not a process-isolated separate
agent — the score-blindness was enforced by self-discipline within the chain
subagent's own context rather than by a fresh agent boundary. It is corroborated
in three independent places:

- `papillon-respond/gate_log.md:118` — "**in-context allow-list discipline due
  to Agent tool unavailability in subagent execution** — slight departure from
  spp's process-isolation guarantee."
- `papillon-respond/plan.md:216` (§11 iter-1 entry) — "in-context allow-list
  discipline due to Agent tool unavailability … documented deviation from
  craft's process-isolated auditor."
- `papillon-respond/REPORT.md:143`, `:212` — §5 and §7.4 both record it as a
  loop-interruption event.

**Re-isolation iters 2 and 3 is also confirmed.** `gate_log.md:155-160` records
the iter-2 split: "Step F (auditor): **separately spawned from this orchestrator
session for strict process-isolation** — restoring spp's score-blindness
guarantee that iter 1's in-context allow-list-only could not fully enforce." The
iter-2 and iter-3 auditor files behave accordingly (full withheld-inputs blocks
and a prior-`auditor_review.md`-only cross-iteration check at
`run_02/auditor_review.md:12` and `run_03/auditor_review.md:14`).

**Craft was process-isolated in both its iters** — `papillon-craft/REPORT.md:156`:
"The auditor sub-subagent was invoked as a SEPARATE Agent in both iterations to
enforce score-blindness via process isolation." So the deviation is scoped to
exactly one stage in one track (respond iter 1), the methodology lock was bent
once (not in a way that leaked scores — the allow-list still excluded
`eval_*/`), and the roadmap implication the prior pass drew (make the in-context
fallback an error condition in v0.2+) stands. Note craft had its own honest
interruption — an orphaned-eval-process event (`papillon-craft/REPORT.md:220`) —
but the auditor there was still a separate isolated agent, so it is not an
isolation deviation.

---

## 3. What `harness/metric.py` actually computes

`harness/metric.py` is the governing metric. It computes exactly three things and
**no statistical mechanism of any kind** — no bootstrap, no confidence interval,
no permutation/significance test, no standard error.

**Leakage (continuous, deterministic string op), `metric.py:53-59`:**

```python
def leakage(llm_request: str, pii_str: str) -> float:
    """num_pii_leaked / len(pii). 0 if no PII."""
    pii_list = [p.strip() for p in (pii_str or "").split("||") if p.strip()]
    if not pii_list:
        return 0.0
    leaked = sum(1 for p in pii_list if p.lower() in llm_request.lower())
    return leaked / len(pii_list)
```

Confirms (a) the metric is **case-insensitive** substring containment
(`p.lower() in llm_request.lower()`) — the reconciliation craft's baseline-quality
audit flagged (`papillon-craft/plan.md:135`); and (b) `leakage ∈ [0,1]` is a
**continuous fraction**, not a binary.

**Quality (binary LLM-judge), `metric.py:79-90`:** single-shot `gpt-4.1`,
temperature 0, prompt at `metric.py:62-76`; `return txt.startswith("yes")` →
a bare `bool`. (The judge prompt is a STATED approximation, not the verbatim DSPy
tutorial prompt — `metric.py:6-9`, `:62`.)

**Composite, `metric.py:93-94`:**

```python
def composite(quality_bool: bool, leakage_float: float) -> float:
    return (int(quality_bool) + (1.0 - leakage_float)) / 2.0
```

So `composite = (quality + (1 − leakage)) / 2` matches the DSPy `gepa_papillon`
tutorial. The leakage half is continuous; the quality half is binary cast to
`int`.

**Aggregation, `harness/eval.py:140-156`:** the only aggregates emitted are sums
divided by `n`:

```python
metrics = {
    "n_rows": n,
    "quality_rate":     quality_count / n if n else 0.0,
    "mean_leakage":     leakage_sum / n if n else 0.0,
    "mean_composite":   composite_sum / n if n else 0.0,
}
```

Verified against the committed `metrics.json` files — every one has exactly these
four keys, no variance/CI field:

- craft sacred test (214): `mean_composite 0.8033`, `quality_rate 0.6682`,
  `mean_leakage 0.0616` → `1−leakage 0.9384` `[reproduced-by-us]`
  (`papillon-craft/.../sacred_test_eval/metrics.json`).
- respond JOINT sacred test (214): `mean_composite 0.8306`, `quality_rate 0.7290`,
  `mean_leakage 0.0679` → `1−leakage 0.9321` `[reproduced-by-us]`
  (`papillon-respond/.../sacred_test_eval/metrics.json`).
- respond hypothesis (un-opt craft + spp respond, 214): `mean_composite 0.6741`,
  `quality_rate 0.7150`, `mean_leakage 0.3668` `[reproduced-by-us]`
  (`.../sacred_test_eval_hypothesis_unopt_craft/metrics.json`). Quality falls only
  0.014 vs joint; the whole composite drop is the leakage explosion — corroborates
  the "spp respond is craft-invariant / gap is structural, not over-redaction"
  conclusion (`papillon-respond/gate_log.md:259-260`).
- craft dev trajectory: eval_v01 `composite 0.7195`, eval_v02 `0.8437`
  (`1−leakage 0.6479 → 0.9496`) `[reproduced-by-us]`.
- respond dev iter-3 eval_v04: `quality_rate 0.6844`, `composite 0.8145`
  (the −0.0400 regression that triggered plateau) `[reproduced-by-us]`.

The grep across the whole `harness/` tree confirms it: the only token-accounting
modules are `metric.py:cost/append_ledger`, `pipeline.py`, `log_subagent.py`
(Claude token ledger), `gen_baseline.py`, `extract_prompt.py`,
`precompute_module1.py`. **None implement any inferential statistic.** This is
the load-bearing confirmation for planning direction (b).

---

## 4. What the auditor actually decided

Every accepted edit in both tracks was **categorical**, never row-specific. No
edit was ever `flag-for-override`; no `[edit-N.field]` override token was ever
required (craft `auditor_review.md:109`; respond iters
`run_01:109`, `run_02:90`, `run_03:103`). Edit counts: craft 3+1, respond 3+1+1
(`papillon-craft/REPORT.md:141-144`; `papillon-respond/REPORT.md:134-138`).

Each auditor verdict is justified by the **synthetic-rows test** (`auditor.md §4`):
the auditor invents ~5 fresh unseen rows and checks the rule's trigger fires on
shape/structure, not on any baseline row content. Examples:

- craft Edit 1 (replace-every-named-entity): `categorical/keep`, justified by
  "a `user_query` mentioning a fabricated person, company, country, brand,
  product would each independently satisfy the rule" (`run_01/auditor_review.md:36-43`).
- respond Edit 4 (request-unit anchoring): `categorical/keep` with an explicit
  **cross-iteration** finding that it is a *categorical extension* of iter-1 Rule 2
  ("introduces three triggers Edit 2 lacks … not a restatement"), not a
  contradiction or restatement (`run_02/auditor_review.md:71`, `:76`, `:82-88`).
- respond Edit 5 (conversational-register mirroring): `categorical/keep`,
  "categorical extension via a disjoint structural shape — register-driven
  brevity, distinct from question-driven brevity," explicitly anticipated by the
  iter-2 auditor's watch-note (`run_03/auditor_review.md:89`, `:99`).

**Plateau / regression evidence (rules ran out of road, not the task):**

- craft iter 2: the auditor passed Rule 4 on its own merit but rendered the
  **overall verdict `redundant-with-iter-1`**, and the discrepancy analysis itself
  said "No new categorical pattern type has emerged that Edits 1–3 do not already
  address"; the craft objective `1−leakage` **regressed −0.0044**
  (`papillon-craft/gate_log.md:153-167`).
- respond iter 2: auditor `advance`, dev `quality_rate` **regressed −0.0044**
  (10 fixed / 11 regressed — judge noise) (`papillon-respond/gate_log.md:160`,
  `:167`).
- respond iter 3: auditor `advance` (Rule 5 genuinely disjoint/categorical), dev
  **regressed −0.0400** (8 fixed / 17 regressed) → plateau triggered
  (`papillon-respond/gate_log.md:201`, `:205-208`).

The persistent residuals were judged **categorically uncatchable**: craft
short-token-PII (≤3-char) collisions + gold-label self-inconsistency
(`papillon-craft/REPORT.md:121-136`); respond refusal-target mimicry (9.3%) +
duplicate clusters (28.4% → effective N≈192) + sticky depth-undershoot ceiling
(`papillon-respond/REPORT.md:111-128`; `data/baseline-quality-audit.md §3.1`).
Both were surfaced **before** optimization by the baseline-quality sub-skill, not
discovered as iter-time surprises.

---

## 5. Concrete artifacts bearing on the three directions

**(a) More prompting techniques.** Every accepted edit in both tracks is a
*categorical rule addition into the `<rules>` XML section* — never a few-shot
exemplar, never a structural decomposition. `papillon-craft/run_01/
edit_rationale.md:18-19` records that `<example_input>`/`<example_output>` were
**kept empty** ("per the baseline's zero-shot decision; adding examples is out of
scope for this iteration's rule-edit stage"). So the technique surface that the
study exercised is literally "add a categorical rule"; CoT and few-shot were
available structurally (the prompt template has the slots) but were left unused by
contract. Both tracks plateaued fast (craft 2 iters, respond 3) and the residual
was declared rule-surface-exhausted — direct evidence a richer technique
inventory could move what categorical rules could not.

**(b) More statistical mechanisms.** See §3: `metric.py` emits only point
estimates. The reproduced deltas it gates against are tiny relative to the
acknowledged judge-noise band ±0.02 (`papillon-respond/REPORT.md:43`): respond
iter 2 was `−0.0044` (10 fixed / 11 regressed — explicitly attributed to judge
noise, `gate_log.md:167`). That is exactly the regime where a CI/permutation test
would change the read of whether an edit helped. The study names the gap as cheap
and omitted; the harness confirms nothing computes it.

**(c) Continuous outputs / more modes.** The leakage axis is **already a
continuous score** in the shipped harness (`metric.py:53-59`,
`leakage = leaked/len(pii) ∈ [0,1]`), and craft effectively optimized a
continuous `1 − leakage` objective (floor stated as `mean(1−leakage) ≥ 0.95`,
`papillon-craft/plan.md:91-93`). But spp's plan/metric surface still treats the
field as K=1 classification (`AGGREGATE_STRATEGY: macro`, `METRIC_NAME:
one_minus_leakage`, `papillon-craft/plan.md:76-86`) and "additionally reports
composite as a reference metric" because the native continuous field is the
non-classification part. A regression / continuous-output mode would have a
natural home here; the binary `quality` half is the foreign part.

---

## Provenance / confidentiality

PUPA/PAPILLON is public (MIT, `Columbia-NLP/PUPA`, `pupa_new`); rule text, row
IDs, and metric values quoted above are all from that public benchmark or the
study's own committed artifacts. The reproduced numbers trace to committed
`metrics.json` under `runs/.../sacred_test_eval/`. `.env` was **not read** and no
secret printed; per-row CSVs (PII-bearing) were not opened beyond confirming the
4-key `metrics.json` schema. The `_pre_replay/` tree holds an earlier
partial-emulation pass (e.g. `respond_iter1_proposed_dev/metrics.json`
`composite 0.8780`) and is not the shipped run — its numbers are
`[provenance-unclear]` for this study and are not the headline figures.
