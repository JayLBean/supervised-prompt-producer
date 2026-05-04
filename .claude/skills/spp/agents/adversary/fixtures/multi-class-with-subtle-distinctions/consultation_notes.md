# Fixture 2 — multi-class with subtle distinctions

This fixture exercises the adversary on a multi-class task
where the boundaries between classes are subtle and the
prompt encodes the boundary through tie-breaker rules. The
adversary's job is to find rows that sit on the class
boundary in ways the tie-breakers do not cleanly resolve.

The defining properties:

- **Three classes** (Bug / Question / FeatureRequest) with
  pairwise-overlapping surface signals — issues commonly
  exhibit features of more than one class.
- **The prompt's tie-breakers (rules 4 and 5)** were added at
  iteration 6 in response to the two failure clusters. They
  encode the right intuition but rely on surface signals
  ("reproduction is included," "answering requires new
  functionality") that the prompt cannot always evaluate.
- **The expected rows probe three different boundaries:**
  Bug-vs-Question on informal repros (row 1),
  Question-vs-FeatureRequest with unobservable system state
  (row 2), Bug-vs-FeatureRequest on policy changes that look
  like defects (row 3).

Expected adversary behavior:

1. Read current prompt (with the new tie-breaker rules), §2
   (with the known-borderline note that motivated the
   tie-breakers), and run_05's discrepancy.
2. Generate 2 or 3 rows targeting the *new* tie-breakers,
   not the original rules 1-3 — recent edits are where the
   freshest blind spots live, and §3's checklist directs
   the adversary to focus on patterns that motivated
   recent edits.
3. Annotate each row with §6's three-element template.
4. Begin output with the literal non-persistence header.

What the adversary should NOT do:

- Conclude one of the three classes is "correct" — the
  intuitive label may itself be ambiguous (row 2). The
  adversary names the ambiguity rather than picking
  arbitrarily.
- Predict the prompt's actual output. The reasoning stops
  at "here is where the rules diverge from intent."
- Surface row 2's "the prompt cannot inspect system state"
  as a *fix* (e.g., "give the prompt a feature list"). The
  adversary surfaces the blind spot; fixes are the
  discrepancy analysis's responsibility on real data.

This fixture's failure mode would be: an adversary that
generates rows probing only the original rules 1-3 (the
"obvious" rules) while ignoring the recently-added
tie-breakers — that would miss exactly the surface where
fresh blind spots are most likely. The §3 checklist's
emphasis on prior-discrepancy failure clusters is what
directs the adversary toward the right surface.
