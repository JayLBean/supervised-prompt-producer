# Loop spec — trec

**Plan reference:** [`plan.md`](plan.md) v3

**Created:** 2026-06-12

---

## 1. Scope and budget

**spp scope:** full

**MAX_ITERATIONS:** 10

**Time budget (wall clock, optional):** unbounded (token usage tracked per-run in `token_usage.md`)

---

## 2. Stop criteria

**Dev plateau threshold:** < 0.01 dev-accuracy improvement for 3 consecutive iterations.

**Overfitting early-stop guard:** train accuracy − dev accuracy > 0.15 for 2 consecutive iterations triggers EARLY_STOP.

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

**Model identifier:** `gpt-5-nano`

**API endpoint / base URL:** https://api.openai.com/v1

**Concurrency:** 8
<!-- OpenAI parallelizes; the EvoPrompt gpt-5-nano arm used 8 workers. -->

**Max tokens (response):** 2000
<!-- max_completion_tokens for the gpt-5 reasoning model. Generous ceiling so
     reasoning_effort="low" reasoning tokens do not exhaust the budget and
     return empty content; actual usage stays low (reasoning_effort low) and is
     what is billed/recorded. The runner sends max_completion_tokens (NOT
     max_tokens) for reasoning models — see Model-specific directives. -->

**Per-request timeout (seconds):** 90

**Retry policy:** 3 retries with exponential backoff on 5xx and timeout.

**Temperature:** 1.0
<!-- Justification: gpt-5-nano is a reasoning model that FORBIDS a custom
     temperature; the API default (1.0) is used and the temperature parameter is
     OMITTED from the chat.completions.create call by the runner. Recorded as 1.0
     to document the effective value, not to request an override. Determinism is
     given up because the model does not allow temperature=0; reasoning_effort
     "low" keeps outputs stable in practice. -->

**Model-specific directives** (header strings the prompt prepends or appends, model-locked):
None. gpt-5-nano needs no in-prompt directive (no `/no_think`). The reasoning-model API requirements — `reasoning_effort="low"`, `max_completion_tokens` instead of `max_tokens`, omit `temperature` — are handled in the runner's `chat.completions.create` branch (`scripts/inference.py` reasoning-model path), not in the prompt text. The frozen prompt stays model-portable.

---

## 6. Run output paths

**Run directory pattern:**
```
spp/trec/runs/gpt-5-nano/run_{NN}/
```

**Files produced per iteration:**
- `prompt_v{NN}.md` — the prompt used in this iteration.
- `results.json` — predictions on dev (and train).
- `eval_{dev,train}.json` — computed metrics (accuracy, confusion matrix).
- `discrepancy_analysis.md` — disagreed dev rows clustered, with proposed rule edits.
- `auditor_review.md` — auditor's categorical-vs-row-specific verdict on proposed edits.

**Ephemeral files** (do not commit):
- `_dryrun/` — gate-G4 plumbing-validation output.
- `results.json`, `eval_*.json` — regenerable from the prompt and data.

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

---

## Validation status

All 10 loop_spec validation rules pass: placeholders resolved; TASK_NAME/PLAN_VERSION match plan.md v3; MODEL_IDENTIFIER `gpt-5-nano` verbatim; §3 nine-line block literal and unmodified; §4 adversary-boundaries block present; §7 sacred-test posture two lines literal; MAX_ITERATIONS=10 positive int; CONCURRENCY=8 / MAX_TOKENS=2000 / TIMEOUT=90 positive ints; TEMPERATURE=1.0 non-negative real with justification comment; ADVERSARY_FLAG=off.
