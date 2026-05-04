# Discrepancy analysis — run_03

## Failure cluster A — keyword overmatch on rule 5

Three dev rows mentioned "subscription" or "payment" but were
about unrelated topics (a newsletter subscription, a
podcast-payment thank-you note). The prompt classified them
`Relevant` because rule 5 keyword-matches; the user labeled
them `Not Relevant`.

Proposed edit for iteration 4: tighten rule 5 to require the
billing product context, not just keyword presence.

## Failure cluster B — login-with-billing-context

Two dev rows asked about login issues that turned out to be
caused by a failed payment locking the account. The prompt
classified them `Not Relevant` (rule 3); the user labeled
them `Relevant` because the underlying issue was billing.

Proposed edit for iteration 4: add a carve-out to rule 3 for
login issues with a billing root cause.

(Iteration 4's prompt above incorporates both edits as
amendments to rules 3 and 5.)
