# Example — decomposition-pipeline

A skeleton example for **prompt decomposition** (`DESIGN.md` §7.1.12, the v0.11
arc): one task split into a **linear pipeline** of prompts, node 1 → terminal,
where each node's output feeds the next. It is the **managed** form of the
manual feature-group splitting practice (`DESIGN.md` §10 glossary) — the manual
practice (independent `sub-tasks/` coordinated by hand) stays valid and
coexists.

This pipeline has two nodes:

1. **`extract`** — pull the product mentions out of a review (an extraction
   field, scored by `extraction_f1`).
2. **`classify`** — classify the review's sentiment, reading the review **plus
   the products `extract` found** (an enum field, scored by `macro_f1`).

The `classify` node's `products` input is **materialized from the frozen
`extract` output** — a data-plane dependency the deployed pipeline has too
(`DESIGN.md` §7.1.12). It is *not* a cognitive cross-node flow: each node's
isolated stages (discrepancy / rule-edit / auditor) see only that node's own
input → output → gold. This is a skeleton in the `DESIGN.md` §7.2 sense — file
structure and walkthrough are real; data and prompt content are placeholder.

## Layout

```
decomposition-pipeline/
├── pipeline.json        # runnable pipeline config (the form the runner reads)
├── pipeline.md          # the human contract (filled pipeline.md.template)
├── README.md
└── sub-tasks/
    ├── extract/         # a normal spp task: its own plan, baseline, metric
    │   ├── config/{schema,field_metrics}.json
    │   └── data/baseline.csv
    └── classify/        # a normal spp task
        ├── config/{schema,field_metrics}.json
        └── data/baseline.csv
```

Each node is a **normal single-node spp task** — nothing about a node changes
because it is in a pipeline. `pipeline.json` / `pipeline.md` is the parent that
orders the nodes and declares the wiring and the composite metric (`mean` here).

## What this example teaches

- **Decomposition is a structure, not a new methodology.** The four-command set
  stays closed (#20): `/spp-loop` optimizes the active node; there is no fifth
  "pipeline" command.
- **The contract applies per node, unchanged.** Each node has its own
  node-local gold and is optimized upstream-frozen; the per-stage isolation
  contract (#1–#3) holds per node.
- **One composite finalize.** The sacred test set is read **once** across the
  whole pipeline, at a single composite `/spp-finalize` (#6/#7) — never per
  node.
- **Mechanical scoring throughout (#13).** `extraction_f1` and `macro_f1` are
  pure functions of (prediction, gold); the composite is their roll-up. No LLM
  judge anywhere — which is exactly why decomposition is in scope.

## Runnable end to end

The fixture is exercised (synthetic predictions, no model call) in
[`skills/run/scripts/tests/test_examples_pipeline.py`](../../skills/run/scripts/tests/test_examples_pipeline.py):
it scores `extract`, materializes `classify`'s baseline from `extract`'s frozen
output, scores `classify`, and computes the `mean` composite — proving the
configs and the chain wiring agree.

## Cross-references

- [`DESIGN.md`](../../DESIGN.md) §7.1.12 — the v0.11 decomposition pin.
- [`skills/run/templates/pipeline.md.template`](../../skills/run/templates/pipeline.md.template)
  — the parent contract this example's `pipeline.md` fills.
- [`examples/feature-group-split/`](../feature-group-split/) — the *manual*
  (parallel, independent) counterpart this managed pipeline coexists with.
