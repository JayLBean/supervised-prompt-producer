# EARLY_STOP — spp/trec/gpt-5-nano

**Type:** EARLY_STOP (manual termination at an iteration boundary — categorical-edit convergence)
**Timestamp:** 2026-06-12
**Task:** trec (question answer-type classification, 6-class, accuracy)
**Model:** gpt-5-nano (OpenAI, reasoning_effort low)

## Termination reason

The loop is terminated at the iteration-4 boundary by judgment that the
**categorical-edit process has converged**: after iteration 4 (prompt_v05), the
remaining 21 disagreed dev rows are a *balanced* Entity↔Description seesaw
(5 Entity→Description vs 4 Description→Entity — pushing either direction trades the
other) plus TREC-idiosyncratic singletons and genuinely-ambiguous gold labels
(e.g. "oldest profession"→Human, "argon reactivity"→Number, "best way to remove
wallpaper"→Entity). No further *categorical* edit is available that would
generalize; the only remaining "improvements" would be row-specific patches, which
the score-blind auditor exists to reject. Dev accuracy rose monotonically every
iteration and peaked at the final prompt, so the dev-argmax is the last iteration.

The formal dev-plateau detector (<0.01 for 3 consecutive) did not fire (the last
gain was +0.020); termination is the discretionary manual stop allowed at any
iteration boundary (loop_spec §2). The overfitting guard never tripped:
train−dev stayed ≤ 0.035 throughout (train and dev moved together — the signature
of generalizing edits, not dev-overfitting).

## Best iteration

- **Selected: prompt_v05** (`runs/gpt-5-nano/run_05/prompt_v05.md`) — dev-argmax.
- **Dev accuracy:** 0.895   **Train accuracy:** 0.930   **train−dev delta:** 0.035
- This is the candidate frozen prompt for `/spp-finalize`.
- dev 0.895 is well above the headline proxy (shared seed's test 0.828; EvoPrompt's
  test 0.804) on the identical 200 dev rows EvoPrompt used.

## Iteration summary

| iter | prompt | dev acc | train acc | train−dev | edits | verdicts (cat/row-spec/unclear) | overrides |
|---|---|---:|---:|---:|---:|---|---:|
| — | v01 (bare seed) | 0.765 | 0.780 | 0.015 | — | — | — |
| 1 | v02 | 0.820 | 0.880 | 0.060 | 6 | 6 / 0 / 0 | 0 |
| 2 | v03 | 0.850 | 0.900 | 0.050 | 4 | 4 / 0 / 0 | 0 |
| 3 | v04 | 0.875 | 0.900 | 0.025 | 2 | 2 / 0 / 0 | 0 |
| 4 | **v05** | **0.895** | **0.930** | 0.035 | 2 | 2 / 0 / 0 | 0 |

Total: 14 rule edits across 4 iterations, **every one verdicted `categorical`** by
the score-blind auditor; **0 overrides**; overfit guard never tripped.

## Per-class dev recall (v05)
Expression 1.00 · Number 0.94 · Human 0.93 · Location 0.87 · Entity 0.87 · Description 0.86.
(The rare Expression class — 3 dev rows — went 0/3 at the seed to 3/3 at v05 via the
tight categorical abbreviation rule, not example-fitting.)

## Information isolation upheld
- Discrepancy subagent: saw disagreed dev row content + eval (per iteration); its
  persistent artifacts reference rows by ID only.
- Rule-edit subagent: saw the prompt + discrepancy (IDs only) + class defs — never
  row content, never scores.
- Auditor: saw the prompt diff + discrepancy + class defs — never scores.
All four iterations ran the three isolated subagents under these allow-lists.

## Cost (informational)
gpt-5-nano task-model tokens through the loop are recorded in `../../token_usage.md`
(calibration + run_01..05). Verified $ total computed at finalization.

## Next step
`/spp-finalize` — score prompt_v05 on the sacred 500-row test set once (gate G5),
write REPORT.md, freeze the prompt (gate G6).
