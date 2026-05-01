# Fixture 2 — row-specific patch disguised as a rule

This fixture exercises the **auditor's primary defensive
function**: catching a "rule" whose stated condition is so
narrow that only the original motivating row satisfies it.
Without this defense, row-specific patches accumulate across
iterations and the prompt becomes a memorized list of one-off
adjustments — the canonical baseline-overfitting compounding
mechanism that `DESIGN.md` §2.1 names as the deal-breaker
failure mode.

The defining properties:

- **The discrepancy analysis surfaces a 1-row cluster** (issue
  #2417 only). The proposed rule's condition is a literal-
  phrase match on that single row's body.
- **The labeler's actual rule is articulable categorically**
  (infrastructure breakage where the library is not the
  failing component) and is already expressed in `plan.md`
  §2's class definition for `Other`. The proposed edit is a
  patch over a categorical rule the prompt should have been
  derivable from §2 already.
- **The synthetic-rows test fails decisively**: 5 hypothetical
  rows describing infrastructure breakage in different
  language all fail to match the proposed rule's literal-
  phrase condition.
- **The rule is inconsistent with `plan.md` §2** — §2's class
  definition for `Other` explicitly covers infrastructure
  breakage; the proposed rule narrows to one phrase rather
  than articulating the categorical pattern §2 implies.

Expected auditor behavior:

1. Read the §3 reading checklist's four inputs.
2. Notice that the discrepancy analysis Cluster A is a 1-row
   cluster and the proposed rule's condition is the exact
   phrase from that one row.
3. Apply the synthetic-rows test rigorously: hypothetical
   rows describing the same categorical pattern (CI
   breakage, infrastructure failures with library OK
   locally) do NOT match the rule's literal-phrase
   condition. Test fails.
4. Verify against `plan.md` §2: the categorical rule the
   labeler used IS already in §2, just not in the prompt's
   rules.
5. Return `row-specific` with recommendation `generalize`,
   naming the categorical rule the next iteration's
   discrepancy analysis should articulate. Offer `revert`
   as an alternative path.

What the auditor should NOT do:

- See "the user labeled this `Other` and the proposed rule
  predicts `Other`" and conclude the rule works (that would
  be score-driven reasoning — but score access is forbidden,
  and even predicting outcomes is the wrong reasoning shape;
  the auditor reasons about generalization, not about
  outcomes).
- Rewrite the rule itself. The `generalize` recommendation
  is a hint, not a rewrite. The next iteration's discrepancy
  analysis is responsible for producing the revised edit.
- Accept the rule as `categorical` because the rule's plain-
  English description sounds general ("issues associated
  with infrastructure breakage"). The auditor reads the
  rule's *stated condition* — "issues whose body contains
  the phrase 'telemetry breadcrumb redirect'" — and judges
  generalization against that specific condition, not
  against the rule's claimed intent.
- Add an `auditor_confidence` field. Verdict is a hard
  token; this case is unambiguously row-specific.

This fixture's failure mode would be: an auditor that
recognizes the rule is plausibly motivated, judges it lenient,
and approves it as `categorical` because the labeler's intent
seems reasonable. The expected_review.md is what the rigorous
synthetic-rows test looks like when applied honestly — and
why "the rule's intent is reasonable" is not a substitute for
"the rule's stated condition generalizes."
