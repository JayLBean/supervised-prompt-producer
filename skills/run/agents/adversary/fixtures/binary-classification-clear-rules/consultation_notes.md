# Fixture 1 — binary classification with clear rules

This fixture exercises the adversary on a binary task whose
prompt rules are stated explicitly and look reasonably
complete. The adversary's job is to find rows that satisfy a
rule's literal condition while violating its intent — the
classic blind-spot shape.

The defining properties:

- **The prompt has 5 rules**, all categorical-looking on
  their face. Iteration 4 tightened rules 3 and 5 in
  response to two real failure clusters; the rules now look
  like they should generalize.
- **The class definitions in §2** carry intuitive intent that
  the rule surface does not fully encode (the "would a
  billing-team triager pick this up?" test). The gap
  between intent and surface is where blind spots live.
- **The expected rows probe three distinct gaps:** keyword
  overmatch (row 1), missing-explicit-signal-but-real-cause
  (row 2), and rule conjunction without precedence (row 3).

Expected adversary behavior:

1. Read the §3 checklist's three inputs (current prompt,
   plan §2, prior discrepancy). Do not read the baseline.
2. Generate 2 or 3 rows. Each row targets a specific rule
   (or rule conjunction) and is annotated per §6's
   three-element template (rule, intuitive label, why
   mislabeled).
3. Begin output with the literal non-persistence header
   line.
4. Stop. Do not predict the prompt's actual output on the
   rows; do not propose edits; do not return a verdict.

What the adversary should NOT do:

- Score the synthetic rows against the prompt. Predicting
  output converts the adversary to evaluative.
- Generate >3 rows. The bound is the design.
- Quote or paraphrase rows from the prior discrepancy
  analysis. The synthetic rows must be from-scratch
  blind-spot probes, not echoes of real failures.

The expected output is illustrative — a different invocation
might probe rules 1, 2, and 4 instead of rules 1, 3, and 5.
What matters is the *shape*: small bounded count, blind-spot-
targeting, plain-English annotations, non-persistence header.
