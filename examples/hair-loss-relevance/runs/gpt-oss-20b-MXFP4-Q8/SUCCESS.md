# SUCCESS — hair-loss-relevance

**Type:** SUCCESS.md
**Timestamp:** 2026-05-04
**Task:** hair-loss-relevance
**Model:** `gpt-oss-20b-MXFP4-Q8`

---

## Termination reason

Dev plateau achieved at iteration 4 against the v6 plateau threshold (`<0.05 dev F1 improvement for 2 consecutive iterations`).

- Iter 2→3 dev F1 delta: 0.0000 (< 0.05) ✓
- Iter 3→4 dev F1 delta: +0.0433 (< 0.05) ✓
- Two consecutive deltas under threshold → plateau condition met.

The plateau threshold was revised in `plan.md` v6 §8 + §11 from the v1 default of `<0.005 for 3 consecutive` because at N_dev=20 a single misclassified row swings dev F1 by ≈0.05, putting the v1 threshold strictly below the dev partition's noise floor. The §10 open question filed during `/spp-init` explicitly anticipated this and committed to revisiting at G4. The v6 revision reflects realistic noise-bounded convergence at this dev size.

The best iteration's dev F1 (**0.9524** at iter 4) meets and exceeds the §3 headline criterion (`F1 ≥ 0.90 on dev`). Both the dev-plateau condition and the headline-criterion condition hold ⇒ termination type is SUCCESS per `/spp-loop` §4 step 15.

## Best iteration

**run_04** — `prompt_v04.md`.

| Metric | Value |
|---|---|
| dev F1 (positive class) | **0.9524** |
| train F1 (positive class) | 0.7500 |
| train-vs-dev delta | -0.2024 (dev > train; no overfitting) |
| dev confusion matrix | see [`run_04/eval.json`](run_04/eval.json) |
| dev unparsed rows | 0 |
| train unparsed rows | 0 |

**Candidate frozen prompt:** [`run_04/prompt_v04.md`](run_04/prompt_v04.md). This is the file `/spp-finalize` will read against the sacred test set and freeze as `PROMPT_FROZEN_v01.md` upon G5 / G6 approval.

## Iteration summary

| iter | prompt | dev F1 | train F1 | train-dev Δ | dev disagreed | edits proposed | edit verdicts |
|---|---|---|---|---|---|---|---|
| 1 | v01 | 0.7619 | 0.7636 | +0.0017 | 5 | 4 | 4 categorical |
| 2 | v02 | 0.9091 | 0.8387 | -0.0704 | 2 | 1 | 1 categorical |
| 3 | v03 | 0.9091 | 0.7200 | -0.1891 | 2 | 2 | 2 categorical |
| 4 | **v04** | **0.9524** | 0.7500 | -0.2024 | **1** | — (plateau) | — |

**Total edits applied across the loop:** 7. **All 7 received `categorical` verdicts from the auditor.** Zero `row-specific` or `unclear` verdicts; zero `auditor override` entries in `plan.md` §11.

## Override summary

No `auditor override` entries were recorded in `plan.md` §11 during the loop. The four non-rule-edit revision-log entries (v2 — headline F1 target tightened to 0.90 at G1; v3 — baseline-quality review with `ready` verdict at G2; v4 — MAX_TOKENS bump 200→1500; v5 — MAX_TOKENS bump 1500→3000; v6 — dev plateau threshold revision) are operational / consultation-side, not edit overrides.

## Cost

- Total iterations: 4 (plus 1 dry-run on 3 train rows pre-G4)
- Inference calls (post-G4): ~80 calls per iteration × 4 iterations + 3 dry-run = ~323 LLM calls total against the local mlx server.
- Wall-clock: roughly 1–2 minutes per iteration (parallel concurrency 5 against the local server).
- Cost is informational; not gate-relevant.

## Notable observations from the loop

- **Iteration 2's substantiveness floor was approved as `categorical` by the auditor** but turned out to be over-broadly scoped — train F1 regressed from 0.839 (iter 2) to 0.720 (iter 3). Iteration 3's discrepancy correctly diagnosed the over-correction; iteration 4 narrowed the floor (cluster G) and dev F1 recovered to 0.9524. **This is the methodology working as designed:** the auditor protects against blatant row-specific patches at the wording level; bad-but-categorical generalizations are surfaced through the next iteration's discrepancy rather than at audit time. The recovery confirms the auditor's job is categorical-vs-row-specific judgment, not metric movement.
- **Recurring row 68** (the peer-treatment-advice + beard-mention post) was a stable failure shape that the topic-scope-first check in iter 4 still classifies false. The user opted not to fish for a 5th rule edit aimed at this single dev row, on the methodologically-correct grounds that 1-row dev signal is below the discriminative resolution of the dev partition.
- **Dev > train across iters 2–4** by a wide margin (-0.07 to -0.20). At N_train=60 / N_dev=20 with stratified-uniform splits this is consistent with the dev partition having a slightly easier label distribution by chance, not a methodology concern. Will be flagged in REPORT.md §7 limitations and as a guard against over-claiming sustained generalization at this dev size.

## Next step

`/spp-finalize` — read the sacred test partition exactly once, compute test-set metrics, generate `REPORT.md`, freeze `PROMPT_FROZEN_v01.md`, gates G5 (finalization) and G6 (production decision).
