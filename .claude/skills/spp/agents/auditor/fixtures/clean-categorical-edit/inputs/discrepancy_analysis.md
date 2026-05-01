# Discrepancy analysis — run_03 (iteration 3, prompt_v03)

Iteration 3 dev predictions diverged from labels on 8 rows. The
analysis below describes each disagreement and the rule edit
proposed for iteration 4.

## Cluster A: third-party billing references mis-routed as Billing (8 of 8 disagreements)

All 8 disagreed rows share a structural pattern: the user is
asking about billing in the third person rather than reporting a
first-person billing event. The current iteration-3 rules treat
any mention of payment / invoice / charge as a Billing signal,
which is too inclusive.

Representative shapes (generic; not real labeled rows):

- "I saw on the forum that someone got double-charged. Does that
  happen here?" — labeled `Not Billing` (curiosity question);
  prompt predicted `Billing` because of "double-charged" keyword.
- "My friend says invoices show up in the wrong currency for
  some users. Is that a known issue?" — labeled `Not Billing`
  (third-party report, no first-person billing context); prompt
  predicted `Billing` because of "invoice" keyword.
- "An article mentioned subscription cancellations refunding
  partially. How does your refund policy work?" — labeled
  `Not Billing` (policy curiosity); prompt predicted `Billing`
  because of "refund" keyword.
- "Hi support — could you confirm whether your platform handles
  X situation that another customer described to me?" — labeled
  `Not Billing`; prompt predicted `Billing` based on the
  paraphrased third-party scenario.

The discriminating property the labeler used: **first-person vs
third-person billing context**. First-person ("my payment failed,"
"I was charged twice") routes to Billing; third-person ("my
friend says," "I saw on the forum," "an article mentioned")
routes to Not Billing. The current rules don't distinguish.

## Proposed rule edit for iteration 4

Add a new rule (rule 4 in the prompt's rule list):

> Tickets that quote a third party's billing complaint without a
> first-person billing context (e.g., "my friend got charged
> twice, does that happen often?", "is X common when companies
> do Y") are Not Billing-relevant. The first-person billing
> context is what distinguishes a Billing ticket from a curiosity
> question about billing topics.

The categorical pattern: third-person billing references without
a first-person billing event. The 8 disagreed rows all share this
property; the rule articulates the property the labeler was
implicitly using.

## Other clusters

None this iteration. All 8 disagreements fall into Cluster A.
