# Discrepancy analysis — run_05

## Failure cluster A — Bug-vs-Question on "is this intended?"

Four dev rows asked "is this intended behavior?" and included
an example of the surprising behavior. The prompt classified
all four as `Question` (rule 2); the user labeled three as
`Bug` (the surprising behavior was a real defect) and one as
`Question` (the behavior was documented).

Proposed edit for iteration 6: tie-breaker rule 4 added —
prefer `Bug` when a reproduction is present, even if the
issue is phrased as a question.

## Failure cluster B — Question-vs-FeatureRequest on workarounds

Two dev rows asked "how do I do X?" where X is not currently
possible. The prompt classified them `Question`; the user
labeled them `FeatureRequest`.

Proposed edit for iteration 6: tie-breaker rule 5 added —
prefer `FeatureRequest` when answering would require new
functionality.

(Iteration 6's prompt above incorporates both tie-breakers as
new rules 4 and 5.)
