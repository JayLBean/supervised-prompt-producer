# Auditor review — run_02 (edits proposed in run_01 → prompt_v02)

Score-blind auditor. No accuracy numbers were provided; verdicts judge only
whether each edit is a categorical answer-type rule vs. a row-specific patch.

## Verdicts

### Edit 1 — Entity vs Description boundary
**Verdict: categorical.** Keys on a general answer-type cue (concrete noun-label vs. definition/explanation/manner/reason) that generalizes to any unseen "what is X" question. Enumerates a class of answer types, names no specific row's gold answer. Recommendation: **advance**.

### Edit 2 — Location cue rule
**Verdict: categorical.** Defines Location by the answer-type cue "the answer names a place," with an open-ended geographic taxonomy and explicit generalization over attribute phrasings (largest/longest/highest/closest). No specific place named. Recommendation: **advance**.

### Edit 3 — Human cue rule (collectives included)
**Verdict: categorical.** Generalizes by answer-type cue: a person or collective-of-people acting as a unit, including "what group/company/force/team/band" framings. Names categories, not any particular company/band. Recommendation: **advance**.

### Edit 4 — Tight Expression rule
**Verdict: categorical.** The riskiest to audit but stays categorical: keys Expression on a syntactic answer-type cue (all-caps initialism subject; "stand for"/"abbreviation of"/"short for"/"what does <ACRONYM> mean") and fences out the Entity and Description neighbors. `<ACRONYM>` is a template placeholder; no dataset initialism (IOC, DEET, …) is hard-coded, so it does not patch the missed rows by identity. Recommendation: **advance**.

### Edit 5 — Numeric-answer rule
**Verdict: categorical.** Generalizes by the cue "the answer is a quantitative value," enumerating answer kinds and dropping reliance on a "how many" surface trigger. Encodes a class boundary, not the singleton rows by identity. Recommendation: **advance**.

### Edit 6 — Answer-type-over-topic tiebreaker
**Verdict: categorical.** A pure meta-rule restating the task contract (classify by answer type, not setup nouns). Maximally general; memorizes nothing. Recommendation: **advance**.

## Summary
Categorical: 6 / Row-specific: 0 / Unclear: 0. All six edits advance; none names a specific row, acronym, place, or gold answer (row IDs appear only as supporting evidence in the discrepancy doc). **No override needed.**
