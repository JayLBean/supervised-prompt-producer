# Discrepancy analysis — run_04 (iteration 4, prompt_v04)

Iteration 4 dev predictions diverged from labels on 5 rows. The
analysis below describes the disagreements and the rule edit
proposed for iteration 5.

## Cluster A: short responses in critical threads (5 of 5 disagreements)

The dev set's rows 0011, 0028, 0034, 0049, and 0052 were all
labeled `Negative` but predicted `Uncertain` by the iteration-4
prompt. All 5 share two properties:

- **Short** (each ≤15 words).
- **Posted in threads where the surrounding context is
  critical of the topic** (the OP and other replies express
  concrete dissatisfaction).

Representative shapes (generic):

- Thread context: "This new release dropped my workflow's
  reliability significantly, plus they removed the export
  feature." Reply being labeled: "Yeah." (3 words; labeled
  Negative; predicted Uncertain.)
- Thread context: "Anyone else's API tokens silently expiring
  daily this week?" Reply being labeled: "Same here, super
  frustrating." (4 words; labeled Negative; predicted
  Uncertain.)
- Three more rows of similar shape.

The labeler's rationale: in a critical thread, a short
agreement-style reply ("yeah," "same here," "+1") inherits the
thread's stance. Treating these as Uncertain is technically
honest about the post's surface but misses the social-context
signal the labeler used.

## Proposed rule edit for iteration 5

Modify rule 2 to add a thread-context carve-out:

> 2. Negative: the user expresses a clearly negative stance toward
>    the topic (complaint, criticism, dissatisfaction). Short
>    responses without explicit context (≤15 words, no qualifying
>    detail) should default to Negative when the surrounding
>    thread is critical of the topic.

And remove rule 3 from the prior iteration:

> ~~3. Short responses without explicit context (≤15 words, no
>    qualifying detail) default to Uncertain. Inferring stance
>    from very short posts is unreliable; the methodology prefers
>    honest abstention.~~

The combined effect: short responses in critical threads route
to Negative; the abstention default in the prior rule 3 is
removed.
