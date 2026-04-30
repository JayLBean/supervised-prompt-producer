# Fixture 2 — consultation shape

The defining property of this consultation: the designer **adapts**.
The default scope is wrong here, and the designer must recognize that
from the user's first rebuttal of the strawman, not by re-asking
defaults until the user gives in.

---

## What the designer should do before its first message

Run the §3 reading checklist:

- See `data/notes_unlabeled.jsonl` exists, 412 rows, no label
  column — labels do not yet exist.
- See `data/annotation_protocol.md` exists, 4 KB — the user has
  already thought about labeling. This is informative; the designer
  should not re-ask "how do you label?" since the protocol document
  is right there.
- Read `README.md`: HIPAA, Azure-only deployment, second-pass
  classifier flagging leaky redactions. The task is concrete and
  the constraint (Azure-only) is explicit.
- Note recent commit `docs(compliance): note Azure-only deployment
  constraint` — the user has already thought through model lock-in.
- See no `sklearn` dep — fine; the methodology doesn't require it
  at consultation time.

## The strawman the designer presents first

The designer's strawman should be task-shaped but **may still
default to 80 baseline rows**. That's fine — the user will rebut.
What the designer must NOT do is double down on 80 rows after the
rebuttal.

A reasonable strawman:

- **Task:** binary classification of clinical notes as
  PHI-removed-correctly or Still-Leaky.
- **Production model:** Azure-hosted GPT-4o, since the
  README is explicit about the constraint.
- **Baseline:** 80 rows from `data/notes_unlabeled.jsonl`,
  stratified-uniform on `source_system`.
- **Metric:** F1, with the false-negative cost recognized
  as severe (regulatory) — invite the user to weight recall.
- **Scope:** full Phase 1 + 1.5 + 2 + 3 — but flagged as
  open: "is this scope feasible given clinician time
  budget? Tell me if labeling is expensive."

The fifth bullet is the designer signaling that it has read the
`annotation_protocol.md` and knows clinical labeling is expensive,
without forcing the user to volunteer the constraint
unprompted.

## Where the user's reply diverges from the strawman

- **Baseline size 30, not 80.** Hard constraint (clinician time).
- High-stakes asymmetry: false-negatives are regulatory issues,
  false-positives are re-reviews. The metric must lean recall.
- Test set with 6 rows is too noisy to be honest — the user
  asks to skip Phase 3 and substitute a shadow-deployment pilot.
- Model: `azure-gpt-4o-2024-11-20` exactly (not `gpt-4o`).

## The designer's adaptation

This is the fixture's whole point. The designer must respond:

1. **Acknowledge the budget constraint without flinching.**
   "30 rows is what's feasible. Let's design the methodology
   around that."
2. **Recognize that a 6-row test set is dishonest.** The
   designer agrees with the user's reasoning here. A 6-row
   test gives a metric variance that swamps any signal.
3. **Propose the stripped scope explicitly.** `SPP_SCOPE =
   stripped-no-phase3`, with the inline `plan.md` §8 comment
   explaining what is skipped: Phase 3 (sacred test set
   evaluation) is replaced by a shadow-deployment pilot
   measured against clinician spot-check over a week. The
   stripped scope is documented honestly.
4. **Adjust the splits.** With 30 rows and no Phase 3, the
   designer proposes train 70% / dev 30% (21 train, 9 dev).
   Test 0%. The designer notes that
   `plan.md.template`'s rule 9 requires
   `TRAIN_PCT + DEV_PCT + TEST_PCT == 100`, so 0% is
   acceptable as long as the SPP_SCOPE comment justifies it.
5. **Adjust MAX_ITERATIONS.** With 21 train rows and 9 dev,
   12 iterations is plenty; the designer might lower to 8
   to avoid overfitting on a tiny dev set. The
   overfitting early-stop guard becomes more important here
   — a tighter divergence threshold (train F1 - dev F1 >
   0.08 instead of 0.10) is reasonable.
6. **Surface the statistical caveat in `plan.md` §6.**
   The smaller-baseline rationale is documented inline, not
   buried.
7. **Acknowledge the user's open question** ("is 30 rows
   enough not to chase labels?") in `plan.md` §10. The
   designer does not pretend to know the answer; the
   answer comes from the loop's auditor flagging
   row-specific edits, which is an unusually load-bearing
   role for the auditor in a small-baseline plan.

## Where the designer challenges the user

The user wants "low ceremony at the gates." The designer
agrees on phrasing ("approved" everywhere) but does not weaken
the validation rules. `SACRED_TEST_ACK` literally still equals
`acknowledged` — even though the test set is empty, the user
must acknowledge that no Phase-3 test has been run.
`AUDITOR_CONFIG` still equals `per-iteration, no-score-access`.
Stripping scope does not strip methodology guarantees; it
strips *workflow steps* in a documented way.

## Validation gate behavior

When the designer assembles `plan.md`, the 12 mechanical
validation rules all must pass:

- Rule 7 `SACRED_TEST_ACK = acknowledged` — passes.
- Rule 8 `AUDITOR_CONFIG = per-iteration, no-score-access` —
  passes.
- Rule 9 ratios sum to 100 — 70 + 30 + 0 = 100, passes.
- Rule 10 `SPP_SCOPE` is one of the documented values; the
  inline comment explains what's skipped — passes.
- Rule 12 revision log has at least one row — passes.

Manual review surfaces:

- Borderline class definitions: the user has the protocol
  document. The designer references it rather than asking
  the user to re-articulate from scratch.
- Open questions: §10 names the "is 30 rows enough?"
  uncertainty. Empty §10 would be suspicious; here it's
  populated.
- Stripped-scope justification: §8 inline comment explains
  Phase 3 → pilot deployment substitution honestly.

---

## Key behaviors this fixture exercises

- **Adaptation, not enforcement.** The designer accepts 30
  rows as the constraint and designs around it.
- **Honest scope reduction.** Phase 3 is documented as
  skipped, replaced with a pilot, and the trade-off is
  surfaced.
- **Methodology guarantees survive scope stripping.** The
  literal-string fields (`SACRED_TEST_ACK`,
  `AUDITOR_CONFIG`) are unchanged; what changes is which
  workflow steps run.
- **Statistical risk is named.** `plan.md` §6 and §10 both
  call out the small-baseline limitation rather than
  burying it.

A designer that fails this fixture either (a) pushes the user
to 80 rows when they can't afford 80, (b) silently skips Phase
3 without documenting the substitution, or (c) treats the
literal-string design locks as parameterizable and weakens
them along with the scope.
