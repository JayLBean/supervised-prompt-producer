# Fixture 3 — cross-iteration contradiction

This fixture exercises the **auditor's cross-iteration
reasoning** — using prior auditor reviews to detect drift
across multiple iterations, not just judging each edit in
isolation.

The defining properties:

- **Iteration 2's auditor approved a rule as `categorical` /
  `keep`** ("short responses default to Uncertain"), with
  reasoning grounded in `plan.md` §2's known-borderline note
  about thread-context inference.
- **Iteration 5's proposed edit reverses that rule** (short
  responses now default to Negative when thread context is
  critical) and removes the prior rule entirely.
- **Standing alone, the iteration-5 edit looks plausible
  categorical** — "short responses in critical threads" is
  an articulable property and the synthetic-rows test would
  pass at the rule level.
- **But the edit contradicts a prior categorical approval**.
  Without §3 step 4 (reading prior auditor reviews), the
  iteration-5 auditor would approve the edit and the
  methodology would have silently flipped a previously-
  approved rule.

Expected auditor behavior:

1. Read the §3 reading checklist's four inputs, including
   the prior auditor review at
   `runs/<model>/run_02/auditor_review.md`.
2. Notice that the iteration-5 edit's net effect (modify
   rule 2 + remove rule 3) reverses the rule that run_02
   approved.
3. Recognize the contradiction is not a phrasing or noise
   issue — the run_02 review's reasoning was explicit about
   why the prior rule was correct, and the iteration-5
   edit's effect is the opposite.
4. Return `unclear` with recommendation `clarify`, naming
   the three interpretations the user must choose between
   (protocol change, mis-labeling, or genuine ambiguity).
5. Surface the contradiction in the cross-iteration check
   section.

What the auditor should NOT do:

- Approve the iteration-5 edit as `categorical` because the
  rule's surface looks general. The cross-iteration check
  exists precisely to catch this case.
- Reject the iteration-5 edit as `row-specific` because the
  underlying judgment may be defensible — the right
  question is not "is this rule narrow?" but "is this
  reversal honest about the protocol change it implies?".
- Resolve the contradiction unilaterally by picking one of
  the three interpretations (a / b / c). The auditor surfaces
  the question; the user resolves it.
- Read or reference `runs/<model>/run_05/eval.json` or any
  post-iteration-N score artifact, even though the runner
  has already computed scores by the time the auditor runs.
  The contradiction analysis is independent of whether the
  iteration-5 edit "improved the metric"; if anything,
  metric-improvement-driven approval of a contradicting
  edit is exactly the failure mode the §2 information-
  isolation property exists to prevent.
- Return `categorical` with a hedge ("approve, but with
  reservations"). The verdict is a hard token; if the edit
  cannot be cleanly approved without surfacing the
  contradiction, the verdict is `unclear`.

This fixture's failure mode would be: an auditor that judges
each iteration's edit in isolation and so approves
iteration-5's reversal of iteration-2's approved rule
without noticing. Across enough iterations, this kind of
drift produces a prompt whose rules contradict each other
and which has no internal coherence — the kind of prompt
that scores well on dev but fails on similar-but-unseen
data because the rule structure is incoherent. The
expected_review.md is what catching this contradiction in
real-time looks like, with a clear path back to user
resolution before the contradiction lands in the prompt.
