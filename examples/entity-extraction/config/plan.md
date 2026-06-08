# spp plan — entity-extraction-example

**Created:** 2026-06-08

**Designer session:** placeholder-designer-session

**Plan version:** v1

---

## 1. Task overview

**Task mode:** extraction

**One-sentence description:** Extract every product and organization
mention (with character offsets) and the topic tags from each
support-ticket message.

**Audience for the prompt's output:** a ticket-triage UI that
highlights mentions inline and routes tickets by topic.

**Problem statement** (placeholder; this example is a skeleton per
DESIGN.md §7.2):
Support tickets arrive as free text. The triage UI needs the exact
spans of product and organization mentions to highlight them, and a
small set of topic tags to route the ticket. The number of mentions
varies per ticket — zero, one, or many — so the output is a
variable-cardinality set, not a fixed object of fields. This is an
**extraction** task (`TASK_MODE = extraction`, DESIGN.md §7.1.11),
not classification: the answer is an open-ended set pulled from the
text.

---

## 2. Output schema and per-field definitions

**Output schema** (JSON Schema draft 2020-12; the full document is in
[`schema.json`](schema.json)):

```yaml
type: object
required: [entities, topics]
additionalProperties: false
properties:
  entities:
    type: array            # variable cardinality — zero, one, or many
    items:
      type: object
      required: [text, type, start, end]
      properties:
        text: {type: string}
        type: {type: string, enum: [product, org]}
        start: {type: integer}   # character offset, first char
        end: {type: integer}     # character offset, one past last
  topics:
    type: array
    items: {type: string}        # free-text tags, no fixed enum
```

**`entities`** — every product or organization mention in the message,
in order of appearance. One item is one contiguous mention; for
overlapping candidates, take the longest contiguous span. Offsets are
character indices into the `input` text (`text == input[start:end]`).
A ticket with no mentions yields an empty array — a valid answer, not
a failure.

**`topics`** — the topics the ticket is about, as free text (e.g.
`returns`, `shipping`, `refunds`). Open-ended; no fixed enum. Empty
when none apply.

The `TASK_MODE = extraction` declaration and this OUTPUT_SCHEMA must
agree (schema-designer mechanical rule 8): both describe a
variable-cardinality item set, not a fixed object — consistent.

---

## 3. Success criteria

The triage UI tolerates a near-miss highlight better than a missed or
spurious mention, so the entity metric rewards overlapping spans rather
than demanding exact offsets. Topic routing is forgiving of casing and
order. Target: macro aggregate ≥ 0.85 on dev, with the entities field
held to a floor (below).

---

## 4. Metrics

**Per-field metrics** (`metric-design` §3.1 extraction sub-table):

- **`entities`** → `span_f1` (`iou_threshold = 0.5`, `match_type = true`).
  Predicted items align to gold by character-offset
  Intersection-over-Union at or above 0.5, and the entity type must
  agree. Offset-grounded because the UI highlights by offset.
- **`topics`** → `extraction_f1` (`match_type = false`). Text alignment
  on normalized tags; there is no type to match.

Both are pure functions of (prediction, gold) — no model in the
scoring path (independence rule, §5; invariant #13).

**Aggregate strategy:** `macro` (unweighted mean of the two fields).

**Per-field floor:** `entities` ≥ 0.80 — a run that routes topics well
but highlights mentions poorly is not shippable for this UI.

---

## 9. Gates

| Gate | Approval phrase |
|---|---|
| G1 | approve plan entity-extraction |
| G2 | approve baseline entity-extraction |
| G3 | approve splits entity-extraction |
| G4 | approve loop entity-extraction |
| G5 | approve finalize entity-extraction |
| G6 | ship entity-extraction |

---

## 11. Plan revision log

| Version | Date | Change | Reason |
|---|---|---|---|
| v1 | 2026-06-08 | Initial plan | Skeleton example for the v0.10 extraction mode |
