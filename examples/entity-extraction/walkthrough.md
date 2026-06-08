# Walkthrough — entity-extraction

How the four phases run for an extraction task. Placeholder content per
[`DESIGN.md`](../../DESIGN.md) §7.2.

## `/spp-init` (designer)

The designer reaches **task-mode identification** first (after the
strawman, before the schema-designer): "for one ticket, is the answer
one choice from a fixed list, or an open-ended set found in the text?"
The answer is the open-ended set, so `TASK_MODE = extraction` is
recorded in [`config/plan.md`](config/plan.md) §1. The §5.1 extraction
reframe then calibrates the item unit (one contiguous mention, longest
span), grounding (offsets, because the UI highlights), and the empty
case (a ticket with no mentions is a valid empty array). The
schema-designer renders the item-array OUTPUT_SCHEMA and its mechanical
rule 8 confirms the schema shape matches `TASK_MODE`. G1 gates on the
approval phrase plus the schema-designer verdict.

## `/spp-baseline`

The gold columns hold JSON item arrays (`entities`, `topics`); see
[`data/baseline.csv`](data/baseline.csv). Baseline-quality calibration
checks the span boundaries and types are consistent across annotators —
the extraction analog of class-definition calibration. Splits freeze;
the test partition is sacred until `/spp-finalize`.

## `/spp-loop`

Scoring runs the K>1 path: `entities` by `span_f1`, `topics` by
`extraction_f1`. The **discrepancy stage** reads the same allow-listed
artifacts as always, but "disagreed" is now item-level — a ticket
enters the disagreed set when a field's per-row metric is imperfect —
and clusters group by failure mode: *missed*, *spurious*, *mistyped*,
or *boundary* (span fields only). A cluster might be "boundary failures
on multi-word org names." The **auditor** stays score-blind; its
categorical-vs-row-specific test judges a rule's span/item effect
("extract the longest contiguous org mention" is categorical; "drop the
trailing ' Inc.'" is row-specific). Allow-list membership is unchanged
throughout — only the content shape the stages reason over changes
(DESIGN.md §7.1.11).

## `/spp-finalize`

The sacred test set is read once.
[`runs/placeholder-model/REPORT.md`](runs/placeholder-model/REPORT.md)
carries per-field test/dev/train scores, the per-field floor-compliance
row, and the extraction failure-mode breakdown (aggregate counts only,
no row content per DESIGN.md §7.2).
