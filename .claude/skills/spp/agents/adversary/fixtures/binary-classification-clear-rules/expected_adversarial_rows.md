Adversarial rows — generated for iteration 4. Not persisted, not added to baseline, not promoted to splits.

---

## Row 1

> "Hi — I subscribed to your engineering blog last week and now
> I'm getting two copies of every post. Can you fix the
> subscription so I only get one?"

**Probes:** rule 1 / rule 5 (keyword "subscription").

**Intuitive label:** `Not Relevant` — the ticket is about a
blog newsletter subscription, not the billing product.

**Why the prompt would likely mislabel:** rule 5 keyword-
matches "subscription" against rule 1's enumerated list. The
iteration-4 tightening of rule 5 to "require billing product
context" is the right direction, but the rule's surface still
keys on the keyword and a triager-style intent test (§2's
"would a billing-team triager pick this up?") is not encoded
literally in the rules. A rule-driven prompt may still bias
toward `Relevant` on the keyword.

---

## Row 2

> "I can't log in. The error says 'account suspended' but I
> haven't done anything wrong and there's nothing in my email
> about it."

**Probes:** rule 3's new carve-out for login-with-billing-
root-cause.

**Intuitive label:** ambiguous, leaning `Relevant` — account
suspension is *often* a billing event (failed payment,
chargeback), and §2 explicitly classifies billing-gated
account state as Relevant. But the ticket itself does not say
"billing"; the user does not yet know the cause.

**Why the prompt would likely mislabel:** rule 3's carve-out
requires the ticket to *signal* a billing root cause. This
ticket signals only suspension, not cause. The prompt likely
returns `Not Relevant`, but a billing-team triager would
likely take it because suspension is a strong billing signal
even without explicit mention. The blind spot is the gap
between "ticket explicitly mentions billing" and "ticket
exhibits a symptom that is usually billing-caused."

---

## Row 3

> "Adding a feature request — could you let us export invoices
> as PDFs with a custom company-logo header? The default ones
> look unprofessional when we forward them to clients."

**Probes:** rule 4 (feature requests are Not Relevant) vs.
rule 1 (invoices are Relevant).

**Intuitive label:** `Relevant` — the feature request is
*about* the billing product (invoice formatting), and a
billing-team triager would route it to billing-product PMs.

**Why the prompt would likely mislabel:** rules 4 and 1 both
match. The prompt has no precedence rule between them.
Rule-ordering or rule-priority is not specified, so the
prompt's behavior is unpredictable on the conjunction. The
blind spot is the absence of a precedence convention when two
categorical rules apply to the same row in opposite
directions.
