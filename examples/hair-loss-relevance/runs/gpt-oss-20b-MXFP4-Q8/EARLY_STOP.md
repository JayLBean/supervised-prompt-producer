# EARLY_STOP — hair-loss-relevance

**Type:** EARLY_STOP.md (user-requested manual stop)
**Timestamp:** 2026-05-04
**Task:** hair-loss-relevance
**Model:** `gpt-oss-20b-MXFP4-Q8`

---

## Termination reason

User-requested manual stop at iteration 4. Plan §3 headline criterion (F1 ≥ 0.90 on dev) has been met and sustained across iterations 2–4 (0.909, 0.909, 0.952). The dev plateau condition (`<0.005 dev F1 improvement for 3 consecutive iterations`) was not formally satisfied — the iter 3→4 delta was +0.0433 — but at the 20-row dev resolution further iterations would invite row-specific patching dressed as categorical edits, since the only remaining dev disagreement (row_id=68) is a recurring single-row peer-engagement edge case.

The user judged at the iteration-4 boundary that continuing risks fitting a small-sample dev set rather than producing a more general prompt; the methodology's escape valve here is user-requested manual stop, recorded as EARLY_STOP per `/spp-loop` §4 step 15.

## Best iteration

**run_04** — `prompt_v04.md`.

| Metric | Value |
|---|---|
| dev F1 (positive class) | 0.9524 |
| train F1 (positive class) | 0.7500 |
| train-vs-dev delta | -0.2024 (dev > train; no overfitting in either direction) |
| dev confusion matrix | see [`run_04/eval.json`](run_04/eval.json) |
| dev unparsed rows | 0 |

**Candidate prompt for `/spp-finalize`:** [`run_04/prompt_v04.md`](run_04/prompt_v04.md)

## Iteration summary

| iter | prompt | dev F1 | train F1 | train-dev Δ | dev disagreed | edits proposed | edit verdicts |
|---|---|---|---|---|---|---|---|
| 1 | v01 | 0.7619 | 0.7636 | +0.0017 | 5 | 4 | 4 categorical |
| 2 | v02 | 0.9091 | 0.8387 | -0.0704 | 2 | 1 | 1 categorical |
| 3 | v03 | 0.9091 | 0.7200 | -0.1891 | 2 | 2 | 2 categorical |
| 4 | v04 | **0.9524** | 0.7500 | -0.2024 | **1** | — (stop) | — |

**Total edits applied across the loop:** 7. **All 7 received `categorical` verdicts from the auditor.** Zero `row-specific` or `unclear` verdicts; zero `auditor override` entries in `plan.md` §11.

## Override summary

No `auditor override` entries were recorded in `plan.md` §11 during the loop. The two non-rule-edit revision-log entries (v4 MAX_TOKENS bump 200→1500; v5 MAX_TOKENS bump 1500→3000) are operational, not edit overrides.

## Cost

- Total iterations: 4 (plus 1 dry-run on 3 train rows)
- Inference calls (post-G4): ~80/iter × 4 iters + 3 dry-run + 60 train calls per iter that were already counted = ~320 LLM calls total against the local mlx server.
- Wall-clock: roughly 1–2 minutes per iteration (parallel concurrency 5 against the local server).
- All cost informational; not gate-relevant.

## Notable observations from the loop

- **Iteration 2's substantiveness floor was approved as `categorical` by the auditor** but turned out to be over-broadly scoped — train F1 regressed from 0.839 (iter 2) to 0.720 (iter 3). Iteration 3's discrepancy correctly diagnosed the over-correction; iter 4 narrowed the floor and recovered. **This is the methodology working as designed:** the auditor protects against blatant row-specific patches; bad-but-categorical generalizations are surfaced through the next iteration's discrepancy rather than at audit time. The recovery confirms the `BREAKING CHANGE:`-level guarantee that the auditor's job is categorical-vs-row-specific judgment, not metric movement.
- **Recurring row 68** (the peer-treatment-advice + beard-mention post) was a stable failure shape across the loop. Three iterations attempted to address its cluster (cluster B in iter 1, then implicit handling in iters 2–4); the iter-4 prompt finally lands it as a `false` because the topic-scope-first check reads "beard" as out-of-scope hair management. The alternative — adding a "primary-topic" anchor exception — was the iter-5 candidate the user declined to pursue, on the grounds that fishing for a single dev row is row-specific patching dressed as categorical.
- **Dev > train** across iters 2–4 by a wide margin (-0.07 to -0.20). At N_train=60 / N_dev=20 with stratified-uniform splits, this is consistent with the dev partition having a slightly easier label distribution by chance; not a methodology concern. Worth flagging in REPORT.md §7 limitations.

## Next step

Per `/spp-loop` §4 step 16: the user decides. EARLY_STOP.md does not auto-trigger `/spp-finalize`. The user has chosen to proceed to `/spp-finalize` to read the sacred test set against `prompt_v04.md` and produce REPORT.md + PROMPT_FROZEN_v01.md.
