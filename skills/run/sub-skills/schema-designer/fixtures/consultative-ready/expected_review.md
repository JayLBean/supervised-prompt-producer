# schema_design_review.md — fixture: consultative-ready

**Path:** 1 (consultative)
**Surface format:** YAML
**Generated:** 2026-05-06T10:00:00-07:00

---

## Verdict

`ready`

---

## OUTPUT_SCHEMA

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
type: object
required: [title, price, category, brand_known, brand]
additionalProperties: false
properties:
  title:
    type: string
    description: The listing's product title, normalized.
  price:
    type: number
    minimum: 0
    description: The listing's price in the marketplace's local currency.
  category:
    type: string
    enum:
      - electronics
      - apparel
      - home
      - toys
      - beauty
      - sports
      - books
      - automotive
      - garden
      - pet
      - grocery
      - health
      - other
    description: The marketplace's category bucket for the listing.
  brand_known:
    type: boolean
    description: |
      Whether the brand can be extracted from the listing's title
      and body. False when the listing is generic-branded or
      uses unrecognized merchant text.
  brand:
    type: [string, "null"]
    description: |
      The brand name when extractable, null otherwise. Always
      present as a key (null literal) — never omitted — so the
      downstream ranker reads a value for every row.
examples:
  - title: "Acme Cordless Drill, 12V"
    price: 79.99
    category: home
    brand_known: true
    brand: "Acme"
  - title: "Generic Cotton T-Shirt"
    price: 14.50
    category: apparel
    brand_known: false
    brand: null
```

---

## SCHEMA_DESIGN_NOTE (for `plan.md` §2)

Reviewed via Path 1 (consultative). Built strawman from CSV
inspection (`raw_category` had 12 distinct values; the user
added `health` as a 13th during refinement). Mechanical layer
passed all 8 rules (rule 8: `TASK_MODE` absent → `classification`,
fixed-field object — consistent); judgment layer passed all 5 (enum is the
marketplace's published category list; the
`brand_known`/`brand: null` pairing captures
brand-extractability as a typed conditional rather than
collapsing into a single nullable field; surface scope of
5 fields matches the user's stated extraction targets without
speculative additions). Surface format: YAML, matching the
repo's existing convention. **Verdict: ready.**

---

## Findings

None — `ready` verdicts do not produce a findings list.

---

## Notes for the caller

`/spp-init`'s gate (slot TBD by bucket 4) advances on the
user's approval phrase alone. No `plan.md` §11 entry is
required. `SCHEMA_DESIGN_NOTE` above is the §2 attestation that
the review happened, even though the verdict surfaced no
issues.
