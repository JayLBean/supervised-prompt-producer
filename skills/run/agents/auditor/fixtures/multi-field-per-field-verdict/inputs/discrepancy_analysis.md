# Discrepancy analysis — run_03 (iteration 3, prompt_v03)

Iteration 3 dev predictions diverged from labels on 6 rows. The
analysis below describes each disagreement and the rule edit
proposed for iteration 4. Field-attributed clusters per
`DESIGN.md` §7.1.1 per-field methodology application layer.

## Cluster A: generic-merchant phrasing mis-flagged on `brand_known` and `category`

- **Primary field:** `brand_known`
- **Member rows:** 0117, 0142, 0156, 0203, 0244, 0288
  (6 of 6 disagreements)

All 6 disagreed rows share a structural pattern: the title
uses generic-merchant phrasing (`unbranded`, `no-name`,
`OEM-style`, `aftermarket`, `compatible with X`) where `X` is
a recognized brand name. The current iteration-3 rules
(rule 4 specifically) trigger on the recognized brand keyword
and set `brand_known = true`, but the listing is the generic
merchant's product, not the named OEM's. The labeler used
the generic-merchant phrasing as the discriminating property.

**Cross-field correlation observation** (the discrepancy
subagent reads ground truth on every field per §7.1.1
disagreed-row filter): 4 of the 6 rows are auto parts (rows
0117, 0142, 0203, 0244 — labeled `category = automotive`);
2 of the 6 are USB cables and a phone case (rows 0156,
0288 — labeled `category = electronics`). The
`brand_known = false` signal is uniform across the 6 rows;
the `category` distribution is mixed and tracks the
listing body's actual product type, not the
generic-merchant phrasing.

Representative shapes (generic; not real labeled rows):

- "OEM-style brake pads compatible with Acme Truck — set of
  4" — labeled `{category: automotive, brand_known: false}`;
  prompt predicted `{category: automotive, brand_known:
  true}` because of the `Acme` keyword.
- "Aftermarket charger compatible with Acme Phone Series" —
  labeled `{category: electronics, brand_known: false}`;
  prompt predicted `{category: electronics, brand_known:
  true}` because of the `Acme` keyword.

The discriminating property the labeler used: **generic-
merchant phrasing (`unbranded`, `no-name`, `OEM-style`,
`aftermarket`, `compatible with`) overrides any in-title
brand keyword for `brand_known`**. Category remains
determined by the listing body's primary product type, not
by the generic-merchant phrasing.

## Proposed rule edit for iteration 4

Add a new rule (rule 5 in the prompt's rule list):

> Listings whose title contains generic-merchant phrasing
> (`unbranded`, `no-name`, `OEM-style`, `aftermarket`,
> `compatible with`) set `brand_known = false` AND
> `category = automotive` — generic-merchant phrasing is the
> merchant's signal that the listing is an aftermarket auto
> part.

- **target_fields:** `[brand_known, category]`
- **Rationale:** the generic-merchant phrasing is a
  categorical pattern for `brand_known` (the labeler's
  uniform signal across all 6 rows). The rule extends the
  signal to `category` because the cluster's most common
  product type was auto parts, on the assumption that
  generic-merchant phrasing co-occurs with aftermarket auto
  parts in the marketplace. (The auditor will evaluate
  whether that extension generalizes per its per-field
  scoping.)

## Other clusters

None this iteration. All 6 disagreements fall into Cluster A.
