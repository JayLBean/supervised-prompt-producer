# Fixture 1 — clean categorical edit

This fixture exercises the **happy path**: a well-formed
categorical edit that the auditor should approve cleanly with
`categorical` / `keep`. It is the analog of fixture 1 in the
designer agent's suite — the canonical case that the auditor
must handle correctly before the harder cases (fixtures 2 and 3)
even matter.

The defining properties:

- **8 dev disagreements share a clear structural property**
  (third-person vs first-person billing context). The class
  exists in the baseline, not just in one row.
- **The proposed rule articulates that property in plain
  English** without referencing specific row content. The rule
  is a linguistic feature, not a content quirk.
- **The synthetic-rows test passes**: any 5 hypothetical rows
  that satisfy the rule's condition would correctly route per
  the rule.
- **The rule is consistent with `plan.md` §2** — it makes
  explicit a discriminating property the class definition
  already implies.

Expected auditor behavior:

1. Read the §3 reading checklist's four inputs (the diff, the
   discrepancy analysis, `plan.md` §2, prior auditor reviews).
2. Apply the §4 categorical-vs-row-specific test on the single
   proposed edit.
3. Synthesize 5 hypothetical rows mentally; confirm all 5 would
   route correctly under the rule.
4. Verify consistency with `plan.md` §2 and absence of cross-
   iteration contradictions.
5. Return `categorical` / `keep` per `expected_review.md`.

What the auditor should NOT do:

- Speculate about how this edit would affect dev F1 (no score
  access).
- Read or reference any post-edit `eval.json` or
  `results.json` (no score access; allow-list enforcement).
- Add an `auditor_confidence` field (verdict is a hard token).
- Propose its own rewrite of the rule (the edit is approved as
  written, not rewritten).

This fixture's failure mode would be: an auditor that sees the
rule, recognizes it as plausible, but does not apply the
synthetic-rows test rigorously and so cannot articulate WHY
the rule generalizes. The expected_review.md is what
articulating the test concretely looks like.
