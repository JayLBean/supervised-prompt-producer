# Example — public-benchmark (TREC question-type, with a cross-framework comparison)

The first `spp` example backed by a **real, fully reproducible run on public,
redistributable data** — not a placeholder skeleton. It is the complete artifact
set from running the methodology on **TREC** (6-way question-type classification)
against `gpt-5-nano`, produced as one arm of a three-way benchmark that also ran
**EvoPrompt** and **DSPy** on the same model, same seed prompt, and same sacred
test set.

It demonstrates several things the other shipped examples deliberately do **not**:

- **Multi-class classification** (6 classes), where the others are binary or
  extraction.
- **Real public data, shipped in full** — TREC is public and redistributable, so
  unlike [`hair-loss-relevance`](../hair-loss-relevance/) (NDA-sanitized) every row,
  prediction, and prompt here is the genuine, unredacted article.
- **A competitive comparison against automated optimizers** on identical controls —
  see [`RESULTS.md`](RESULTS.md) for the full three-way (spp vs EvoPrompt vs DSPy)
  across all three benchmark tasks.
- **A clean generalization story**: a score-driven GA (EvoPrompt) *overfit* its dev
  set on this task (dev 0.825 → test 0.804, below its own seed), while `spp`'s
  score-blind, categorical-rule auditor produced a prompt that *rose* on the holdout
  (dev 0.895 → test 0.924). This is the methodology's load-bearing claim, measured.

## Headline

| arm | test accuracy (500 sacred rows) | task-model calls | cost (USD) |
|---|---:|---:|---:|
| shared seed (manual init) | 0.828 | — | — |
| EvoPrompt (GA, 0-shot) | 0.804 | 4,688 | $0.24 |
| DSPy (MIPROv2, few-shot) | 0.874 | 1,577 | $0.18 |
| **spp (0-shot)** | **0.924** | **2,303** | **$0.11** |

spp wins outright on TREC — **+9.6 points over the shared seed, +5.0 over the
strongest automated arm (DSPy), and +12.0 over EvoPrompt — at the lowest dollar
cost.** Full numbers, the other two tasks, and the fairness ledger are in
[`RESULTS.md`](RESULTS.md).

## Reading order

1. **[`runs/gpt-5-nano/REPORT.md`](runs/gpt-5-nano/REPORT.md)** — start here. The
   finalization report: headline, apples-to-apples controls, the per-class test
   breakdown, the token/cost footnote, and the acknowledged limitations.
2. **The contract:** [`config/plan.md`](config/plan.md) (what gate **G1** approved)
   and [`config/loop_spec.md`](config/loop_spec.md) (the operational pinning). Plan
   §11 records every gate decision and revision.
3. **The loop, iteration by iteration.** For each `run_0N/`, the trio is:
   - `prompt_v0N.md` — the rule surface as it stood that iteration
   - `eval_dev.json` / `eval_train.json` — the metrics it produced
   - `discrepancy_analysis.md` — the failure-cluster analysis (rows by ID only)
   - `auditor_review.md` (from `run_02/` onward, reviewing the prior edits) — the
     **categorical-vs-row-specific** verdicts that gated the next prompt. All 14
     edits across the run came back `categorical`; zero overrides.
4. **Termination + finalize:**
   [`runs/gpt-5-nano/EARLY_STOP.md`](runs/gpt-5-nano/EARLY_STOP.md),
   [`runs/gpt-5-nano/PROMPT_FROZEN_v01.md`](runs/gpt-5-nano/PROMPT_FROZEN_v01.md)
   (= `run_05/prompt_v05.md`, the selected prompt), and the single sacred-test read at
   [`runs/gpt-5-nano/finalize/test_eval.json`](runs/gpt-5-nano/finalize/test_eval.json).

## What it demonstrates about the methodology

- **Per-stage information isolation held throughout.** Each iteration ran three
  isolated subagents — discrepancy (sees disagreed-row content, writes IDs only),
  rule-edit (sees the prompt + discrepancy IDs + class defs, **never row content,
  never scores**), and auditor (sees the prompt diff + discrepancy + class defs,
  **never scores**). This is the property [`DESIGN.md`](../../DESIGN.md) §4.2 protects,
  exercised on a real run.
- **The seed was scored verbatim as iteration 1.** Everything above the bare seed
  instruction was earned by the loop; the +9.6-point gain over the seed is spp's
  measured contribution, not a head start.
- **Same seed, same dev rows, same inference harness, same sacred test** as the
  EvoPrompt arm — see REPORT §2. The comparison is controlled, not anecdotal.

## What it does NOT demonstrate

- **Fresh labeling with `/spp-baseline`.** TREC ships with gold labels; the baseline
  path ran on existing labels.
- **The adversary sub-agent.** Off for this run (`ADVERSARY_FLAG=off`).
- **Cross-model robustness.** The prompt was optimized against one locked model
  (gpt-5-nano), per the v1 model-overfitting-documented-not-prevented contract
  ([`DESIGN.md`](../../DESIGN.md) §2.2). Re-running `/spp-loop` per target model is the
  documented response to a model swap.
- **Few-shot demonstrations.** This arm is 0-shot by design (to match EvoPrompt and to
  isolate rule-writing). DSPy's arm used few-shot; that it still did not beat spp's
  0-shot loop on TREC is the comparison's most interesting result.

## A note on the driver scripts

`run_infer.py`, `score_split.py`, and `finalize_test.py` are the **benchmark drivers
exactly as they ran**, included for provenance. They wrap this repository's own
`skills/run/` runner but also import the companion benchmark's harness (the
`run_evoprompt` wrapper, a `.env` with an API key, the benchmark's split files) so
that every arm scored through one identical inference path. They are **artifacts to
read, not scripts to run from this directory** — they reference the benchmark layout,
not the example's. The two personal absolute paths in the originals were sanitized to
relative ones; nothing else was edited.
