# auditor_review.md — run_04

**Iteration:** 4
**Prompt versions compared:** v03 → v04
**Generated:** 2026-05-07T10:00:00-07:00

---

## Edit 1 (rule addition, rule 5 in v04)

**Edit:** addition of a new rule:

> Listings whose title contains generic-merchant phrasing
> (`unbranded`, `no-name`, `OEM-style`, `aftermarket`,
> `compatible with`) set `brand_known = false` AND
> `category = automotive` — generic-merchant phrasing is the
> merchant's signal that the listing is an aftermarket auto
> part.

**`target_fields` (from `discrepancy_analysis.md`):**
`[brand_known, category]`

The auditor produces one verdict per target field per
`DESIGN.md` §7.1.1 per-field methodology application layer.

### Verdict for field `brand_known`

**Verdict:** `categorical`

**Reasoning:** The rule's stated condition for `brand_known`
— "title contains generic-merchant phrasing
(`unbranded`, `no-name`, `OEM-style`, `aftermarket`,
`compatible with`)" — is an articulable property: it is
statable in plain English without reference to the specific
rows that motivated the edit (the property is a closed set
of phrases, not a row-content quirk).

Applying the synthetic-rows test from §4 scoped to
`brand_known`: imagine 5 synthetic rows that satisfy the
rule's condition (titles containing one of the 5 generic-
merchant phrases) — e.g., "Unbranded USB-C cable, 1m, fast
charge"; "No-name kettle, 1.7L"; "OEM-style replacement
filter for Acme HVAC"; "Aftermarket dashboard cover for
Generic-Co Sedan"; "Compatible with Acme Phone — silicone
case." All 5 would correctly route to `brand_known = false`
under the new rule — the generic-merchant phrasing is the
merchant's explicit signal that the listing is not the
named OEM's product. The rule generalizes for `brand_known`.

The cluster's cross-field correlation observation (per
`discrepancy_analysis.md`'s Cluster A) confirms the class
exists in the baseline: 6 of 6 dev disagreements share the
generic-merchant-phrasing pattern, and the
`brand_known = false` signal is uniform across all 6 rows
regardless of product type. The rule articulates a
discriminating property the class definition in
`plan.md` §2 already implies (the §2 `brand_known`
description names "OEM-style" and "compatible with"
explicitly as `false` triggers).

**Recommendation:** `keep`.

### Verdict for field `category`

**Verdict:** `row-specific`

**Reasoning:** The rule's stated condition for `category`
— "generic-merchant phrasing implies `category = automotive`"
— is **not** an articulable categorical property of the
listings themselves; it is a covariate observation specific
to the cluster's particular row population. The cluster's
own cross-field correlation observation surfaces this:
4 of 6 rows are auto parts, 2 of 6 are USB cables and a
phone case. The `category` distribution is mixed and tracks
the listing body's actual product type, not the
generic-merchant phrasing.

Applying the synthetic-rows test from §4 scoped to
`category`: the same 5 synthetic rows from the `brand_known`
walk above — only the second-to-last (the dashboard cover)
would correctly route to `category = automotive`. The cable
is `electronics`; the kettle is `home`; the HVAC filter is
`home` (or `other`); the phone case is `electronics`. Only
1 of 5 satisfies `category = automotive` despite all 5
satisfying the rule's literal condition. The wording is too
narrow — the rule patches the cluster's particular auto-
parts skew rather than describing a categorical property of
the listings.

The rule edit, applied as written, would systematically
mis-categorize generic-merchant electronics, home goods,
beauty products, etc. as `automotive`. This is a row-
specific patch dressed as a categorical rule for `category`
— the give-away (per §4) is that removing the `category =
automotive` clause would only change predictions on the
cluster's auto-part subset (rows 0117, 0142, 0203, 0244)
while leaving the broader `brand_known = false` signal
intact across all 6 rows.

**Recommendation:** `generalize`. The categorical rule
`category` needs would be: "category is determined by the
listing body's primary product type, not by generic-
merchant phrasing." That rule already exists as rule 2 in
the iteration-3 prompt; the proposed edit's `category =
automotive` clause contradicts rule 2. Next iteration's
discrepancy analysis should drop the `category` clause from
this edit and let rule 2 govern category assignment for
generic-merchant listings — leaving rule 5 to cover
`brand_known` only.

---

## Cross-iteration check

The cross-iteration contradiction check (`auditor.md` §3
step 4) operates per target field under v0.2.

- For `brand_known`: no prior auditor reviews recorded
  edits affecting `brand_known` that would contradict
  iteration-4 edit 1. (Prior reviews — assumed for fixture;
  not shown — would have addressed unrelated rules.)
- For `category`: no direct contradiction with a prior
  categorical approval, but the proposed `category =
  automotive` clause indirectly contradicts the prompt's
  pre-existing rule 2 ("category is assigned from the
  closed enum based on the listing's primary product
  type"). Rule 2 has not been re-audited recently; it is
  inherited from the prompt's pre-loop scaffold rather
  than from a prior categorical approval, so this is
  **not** a cross-iteration contradiction in the strict
  §3 step 4 sense — it is captured under the
  `row-specific` verdict for `category` above.

---

## Gate-enforcement summary

Under `phases/spp-loop.md` §4 step 12's per-edit-per-field
gate enforcement:

- `(edit 1, brand_known)` — `categorical`: advances; no
  override required.
- `(edit 1, category)` — `row-specific`: does not advance
  unless the user records a `plan.md` §11 entry whose
  Reason contains the literal substring `auditor override`
  and the bracketed token `[edit-1.category]`. Without
  the override, the runner reverts the `category =
  automotive` clause in `prompt_v04.md` while keeping the
  `brand_known = false` clause from rule 5.

If the user records a single §11 entry with Reason
containing `auditor override [edit-1.category]`, the
`(edit 1, category)` combination advances and rule 5 lands
in `prompt_v04.md` verbatim as proposed. If the user
records `auditor override [edit-1.brand_known]
[edit-1.category]`, both combinations advance — though the
`brand_known` combination did not need an override
(`categorical` verdicts advance unconditionally), the
multi-token form is still well-formed and harmless.
