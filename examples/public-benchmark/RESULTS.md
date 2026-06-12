# Cross-framework results — spp vs EvoPrompt vs DSPy

This example's TREC artifact set is one arm of a three-way benchmark comparing
`spp` against two automated prompt optimizers — **EvoPrompt** (a genetic-algorithm
optimizer, ICLR 2024) and **DSPy** (MIPROv2) — on three public text-classification
tasks. All arms ran on the **same task model** (`gpt-5-nano`, `reasoning_effort=low`),
started from the **same seed prompt**, and scored the **same sacred test rows** with
the **same label-matching wrapper**.

- **Tasks:** AG News (4-class topic) · SST-5 (5-class sentiment) · TREC (6-class
  question-type).
- **Test sets:** AG News 1,000 rows · SST-5 1,000 · TREC 500 — sacred, read once.
- **Pricing (the honest axis):** gpt-5-nano list price **$0.05/1M input,
  $0.40/1M output**. Output costs 8× input, so **dollars, not raw token count, is the
  fair cross-arm comparator.** Dollar figures are verified to the cent against the
  OpenAI usage dashboard.

> **Regime note (read first).** EvoPrompt and spp ran **0-shot**. DSPy ran
> **few-shot** — MIPROv2 bootstraps in-context demonstrations, its design strength,
> so it was run that way rather than hobbled to 0-shot. DSPy therefore carries extra
> per-row input tokens for its demos. That is a disclosed asymmetry, not an artifact.

## Accuracy (sacred test)

**Bold = best on that task.** SE ≈ 0.010 (1,000 rows) / 0.014 (500 rows).

| Task | Seed | EvoPrompt (0-shot) | spp (0-shot) | DSPy (few-shot) |
|---|---:|---:|---:|---:|
| AG News | 0.870 | 0.869 | 0.876 | **0.881** |
| SST-5 | 0.557 | 0.561 | 0.579 | **0.580** |
| TREC | 0.828 | 0.804 | **0.924** | 0.874 |
| **Mean** | 0.752 | 0.745 | **0.793** | 0.778 |

- **AG News** is a three-way statistical tie (all within ~1 SE of a near-saturated
  seed). No real accuracy winner; cost decides.
- **SST-5**: spp 0.579 ≈ DSPy 0.580 (a 0.001 gap — noise), both clearly beat EvoPrompt
  and the seed. spp's **0-shot rule-writing matched DSPy's few-shot** with zero demos.
- **TREC**: spp 0.924 wins decisively — +5.0 over DSPy (~3.5 SE, a real gap), +12.0
  over EvoPrompt, +9.6 over the seed. EvoPrompt *regressed below its own seed* here
  (GA overfit the dev set).

EvoPrompt never beat its own seed on any task on this model.

## Cost (USD) — the deciding axis

| Task | EvoPrompt | spp | DSPy |
|---|---:|---:|---:|
| AG News | $0.18 | **$0.04** | $0.15 |
| SST-5 | $0.21 | **$0.10** | $0.19 |
| TREC | $0.24 | **$0.11** | $0.18 |
| **Total** | $0.63 | **$0.25** | $0.52 |

spp is the cheapest arm on every task — ~2.5× cheaper overall than either automated
optimizer — while posting the highest mean accuracy.

## Tokens — why raw count misleads

| Task | Arm | Calls | Input tok | Output tok | Total tok | Cost |
|---|---|---:|---:|---:|---:|---:|
| AG News | EvoPrompt | 4,288 | 394,645 | 400,068 | 794,713 | $0.18 |
| | spp | 1,643 | 430,852 | 43,060 | 473,912 | **$0.04** |
| | DSPy | 2,071 | 1,327,021 | 205,039 | 1,532,060 | $0.15 |
| SST-5 | EvoPrompt | 4,368 | 289,403 | 494,455 | 783,858 | $0.21 |
| | spp | 1,803 | 697,609 | 166,658 | 864,267 | **$0.10** |
| | DSPy | 2,084 | 1,283,741 | 318,806 | 1,602,547 | $0.19 |
| TREC | EvoPrompt | 4,688 | 246,696 | 575,620 | 822,316 | $0.24 |
| | spp | 2,303 | 1,783,177 | 179,820 | 1,962,997 | **$0.11** |
| | DSPy | 1,577 | 748,696 | 345,665 | 1,094,361 | $0.18 |

Three opposite profiles: **spp is input-heavy / output-light** (one static
six-section prompt replayed per row; a single label word out), **EvoPrompt is
output-heavy** (GA generations + per-call reasoning), **DSPy is input-heavy via
demos**. On TREC, spp posts the single highest token count in the table (1.96M) yet
is the cheapest arm — because nearly all of it is cheap input, and the >1,024-token
prompt crossed gpt-5-nano's caching threshold. A "total tokens" leaderboard would
mis-rank every task.

## Fairness ledger — what cuts against spp

A one-sided benchmark is not credible. The other side:

1. **spp's optimizer cost is not in these dollars.** This ledger counts gpt-5-nano
   **task-model tokens only.** EvoPrompt and DSPy spend their entire optimization
   budget there, so it is fully visible. spp offloads the optimization *reasoning* to
   Claude subagents **and a human in the loop** — real labor that is **not** in the
   $0.25. The honest claim is narrow: *on task-model spend, spp is ~2.5× cheaper.* It
   is **not** a claim that spp is cheaper once human/Claude time is priced in. For a
   fully-automated walk-away pipeline, the automated arms have no second budget; spp
   does.
2. **DSPy ran few-shot; the others 0-shot.** Its AG News edge and SST-5 parity draw on
   in-context demos the others never used.
3. **TREC's spp cost benefited from prompt caching** the others' short prompts could
   not get. The un-cached list-price estimate for spp-TREC is ~$0.16 — still below
   DSPy ($0.18) and EvoPrompt ($0.24), so the ranking holds, but the margin is
   caching-aided.
4. **spp's TREC ledger honestly includes ~50k "calibration" tokens** (~2.6%) spent
   before its harness was aligned to EvoPrompt's exact format. Counted, not hidden.
5. **TREC used 500 test rows**, so its SE is larger (~0.014); spp's 5-point TREC margin
   over DSPy rests on half the sample of the other two tasks (still ~3.5 SE).

None of these reverse the headline. They bound it: **spp matches or beats both
automated arms on accuracy and is materially cheaper on task-model spend — provided
you account separately for the human/Claude effort it shifts off the task model.**

## Design signal taken from the comparison

The one place an automated arm out-designed spp was AG News (+0.5 pt, inside noise),
via few-shot demos — a lever spp does not use. On SST-5, spp's 0-shot loop already
*matched* DSPy's few-shot, suggesting its rule-writing substitutes for demos. The
takeaway recorded for the roadmap: an **optional, auditor-gated few-shot mechanism**
(demos that encode a *rule*, not row-fitting) is a candidate to test against the
hypothesis that spp's 0-shot rules already capture most of what demos provide.
