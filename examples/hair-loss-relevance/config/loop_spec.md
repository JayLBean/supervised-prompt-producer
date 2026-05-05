# Loop spec — hair-loss-relevance

**Plan reference:** [`plan.md`](plan.md) v6

**Created:** 2026-05-04

---

## 1. Scope and budget

**spp scope:** full

**MAX_ITERATIONS:** 12

**Time budget (wall clock, optional):** unbounded

---

## 2. Stop criteria

**Dev plateau threshold:** <0.05 dev F1 improvement for 2 consecutive iterations. (Mirror plan §8 v6.)

**Overfitting early-stop guard:** train F1 - dev F1 > 0.10 for 2 consecutive iterations triggers EARLY_STOP.md.

**Manual termination:** the user may terminate the loop at any iteration boundary; the runner exits cleanly and writes `EARLY_STOP.md` with reason "user-requested".

---

## 3. Per-stage subagent configuration (non-negotiable)

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

---

## 4. Adversary configuration

**Adversary:** off

**Adversary boundaries** (per DESIGN.md §4.3):

- Synthetic adversarial rows are **not** added to `baseline.csv`, `splits.json`, or any tracked artifact under `runs/`.
- Adversarial rows are surfaced inline in the iteration's discrepancy analysis or as a separate prompt to the user; they are not persisted.
- If a particular adversarial row represents a real failure class the user wants in the baseline, the user collects similar *real* data through the labeling process. Promoting synthetic rows is forbidden.

---

## 5. Model and execution

**Model identifier:** `gpt-oss-20b-MXFP4-Q8`

**API endpoint / base URL:** http://127.0.0.1:8000/v1

**Concurrency:** 5

**Max tokens (response):** 3000
<!-- 200 → 1500 → 3000. gpt-oss-20b-MXFP4-Q8 emits reasoning_content tokens (gpt-oss family
     reasoning trace) inside the same completion-token budget as the visible content. 1500 was
     sufficient for ~99% of rows but still caused 1–2 unparsed completions per iteration on rows that
     drove deep reasoning chains. 3000 absorbs that long tail. Operational parameter only; methodology
     guarantees unchanged. Recorded in plan.md §11 as v5. -->


**Per-request timeout (seconds):** 60

**Retry policy:** 3 retries with exponential backoff on 5xx and timeout.

**Temperature:** 0

**Model-specific directives** (header strings the prompt prepends or appends, model-locked):
<!-- None at v01. gpt-oss-20b is OpenAI's open-weight gpt-oss family; no model-locked directive
     prefix is required by default. If a `reasoning: low|medium|high` directive proves useful
     during /spp-loop iterations, add it here with a model-locked comment and bump PLAN_VERSION. -->

**Conda environment:** `voxpatiens` (project-local execution context; not part of the methodology lock — recorded here so the runner activates it before invoking the inference client).

**Auth:** Bearer token from `.env` `LOCAL_API_KEY` (the local mlx server returns 401 without it).

---

## 6. Run output paths

**Run directory pattern:**
```
spp/hair-loss-relevance/runs/gpt-oss-20b-MXFP4-Q8/run_{NN}/
```

**Files produced per iteration:**
- `prompt_v{NN}.md` — the prompt used in this iteration.
- `results.json` — predictions on dev (and train if requested).
- `eval.json` — computed metrics (F1, precision, recall, balanced_accuracy, confusion matrix).
- `discrepancy_analysis.md` — rows where prediction disagreed with label, with proposed rule edits for the next iteration.
- `auditor_review.md` — auditor's categorical-vs-row-specific judgment on the next iteration's proposed edits, written before iteration N+1 runs.

**Ephemeral files** (covered by `.gitignore`, do not commit):
- `_dryrun/` — Phase 1.5 plumbing-validation output (gate G4).
- `runs/<model>/run_NN/results.json`, `runs/<model>/run_NN/eval.json` — regenerable from the prompt and data.

**Durable artifacts** (committed):
- `prompt_v{NN}.md`, `discrepancy_analysis.md`, `auditor_review.md` per iteration.
- `PROMPT_FROZEN_v01.md` at loop termination.
- One of `SUCCESS.md` / `EARLY_STOP.md` / `FAILED.md` recording why the loop stopped.

---

## 7. Sacred test set posture (non-negotiable)

```
test_set_access_during_loop: forbidden
test_set_first_use: /spp-finalize only
```
