# Excerpt: plan.md §2 (Class definition / OUTPUT_SCHEMA)

**OUTPUT_SCHEMA** (rendered in YAML; v0.2 surface — see
`DESIGN.md` §7.1.1 schema layer):

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
type: object
required: [category, brand_known]
additionalProperties: false
properties:
  category:
    type: string
    enum: [electronics, apparel, home, automotive, garden,
           sports, beauty, other]
    description: |
      The marketplace's product-category bucket for the
      listing. Closed set; `other` is the documented
      residual for listings that genuinely do not fit any
      named category.
  brand_known:
    type: boolean
    description: |
      Whether the brand can be extracted from the listing's
      title and body. False when the listing is generic-
      branded, white-label, unbranded, or uses unrecognized
      merchant text.
```

**Per-field definitions:**

- **`category`**: assigned from the closed enum based on
  the listing's primary product type. Borderline shapes:
  multi-purpose accessories (a smart-home bulb that is
  also marketed as a sports-event prop) default to the
  primary intended use described in the listing body.
  `other` is reserved for listings that genuinely do not
  fit (e.g., gift cards, services); it is not a dumping
  ground.
- **`brand_known`**: true when the listing names a real
  brand the merchant data confirms. False when the listing
  uses generic phrases (`unbranded`, `no-name`,
  `OEM-style`, `aftermarket`, `compatible with X`) or when
  the title contains only a model number with no brand
  text.

**Known borderline cases:**

- "OEM-style" listings sometimes name the OEM whose part
  is being replicated; those are still `brand_known = false`
  because the listing's brand is not the OEM, it is the
  generic merchant.
