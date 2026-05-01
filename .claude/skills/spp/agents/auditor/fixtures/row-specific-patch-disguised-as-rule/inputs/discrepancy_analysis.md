# Discrepancy analysis — run_05 (iteration 5, prompt_v05)

Iteration 5 dev predictions diverged from labels on 3 rows. The
analysis below describes each disagreement and the rule edits
proposed for iteration 6.

## Cluster A: 1 row mis-classified (issue #2417)

The dev set's row 0042 (issue #2417) was labeled `Other` but
predicted as `Bug`. The issue body contains:

> Build pipeline failing on CI runners since Tuesday with
> "telemetry breadcrumb redirect" errors. The library code seems
> fine when I run it locally, but the CI environment cannot
> upload coverage reports because the telemetry-breadcrumb-
> redirect endpoint is returning 502 from our internal
> infrastructure.

The labeler's rationale: this is infrastructure breakage in the
CI environment, not a defect in the library's documented or
intended behavior. The library "seems fine when I run it
locally"; the failure is downstream of the library. Per
`plan.md` §2 the `Other` class includes "build/CI breakage
reports."

The current iteration-5 prompt classified this as `Bug` because
the issue body contains language associated with broken behavior
("failing," "errors," "returning 502"). The prompt's existing
rules do not have a specific "infrastructure breakage" carve-out;
the labeler called this `Other` based on the project's labeling
protocol.

## Cluster B: 2 rows mis-classified (Question vs Bug boundary)

Rows 0019 and 0067 were labeled `Question` but predicted as
`Bug`. Both involve users describing surprising behavior without
explicitly asserting it is a defect. These are the canonical
Question-vs-Bug borderlines `plan.md` §10 already flagged as a
known concern.

These are deferred to a separate proposed edit (not in this
iteration's diff — separately tracked).

## Proposed rule edit for iteration 6 (Cluster A only)

Add a new rule (rule 5):

> Issues whose body contains the phrase "telemetry breadcrumb
> redirect" should be classified as Other, not Bug. The phrase
> is associated with infrastructure breakage rather than a
> defect in the library's behavior.

The rule targets the specific phrase the labeler observed in
issue #2417's body.
