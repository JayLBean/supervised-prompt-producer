# spp examples

Worked examples that demonstrate `spp`'s workflow and artifact shapes across the
task types the methodology supports. Each example has its own `README.md` (start
there) and, where it has computable artifacts, machine-readable configs exercised
by the test suite.

These are **skeletons**, not real runs: file structure and walkthroughs are real;
data, baseline labels, prompt content, and REPORT numbers are generic placeholders
representing no real source project (see [`DESIGN.md`](../DESIGN.md) §7.2 on
confidentiality and provenance).

## The examples

| Example | Task type | Demonstrates | Verified by |
|---|---|---|---|
| [`hair-loss-relevance`](hair-loss-relevance/) | Binary classification | The canonical end-to-end v0.1.0 walkthrough — consultation, baseline, loop, finalize, REPORT. | Walkthrough (illustrative skeleton) |
| [`multi-field-extraction`](multi-field-extraction/) | Multi-field structured output | The v0.2 schema/metrics generalization: several typed fields plus an aggregate strategy and a per-field floor. | `test_examples_multifield.py` |
| [`nested-schema`](nested-schema/) | Hierarchical labels | JSON Schema conditional structures; a top-level floor that can go unmet. | `test_examples_multifield.py` |
| [`entity-extraction`](entity-extraction/) | Structured extraction (v0.10) | `TASK_MODE = extraction`; variable-cardinality item arrays; span/alignment metrics; the empty case as a valid answer. | `test_examples_multifield.py` |
| [`feature-group-split`](feature-group-split/) | Manual feature-group split | The *manual* form of splitting one task into per-feature sub-tasks (the practice v0.11's managed pipeline coexists with). | Walkthrough (illustrative skeleton) |
| [`decomposition-pipeline`](decomposition-pipeline/) | Prompt decomposition (v0.11) | A managed linear pipeline of node-local-gold tasks; per-node isolation; one composite finalize. | `test_examples_pipeline.py` |

The four examples with machine-readable configs (`multi-field-extraction`,
`nested-schema`, `entity-extraction`, `decomposition-pipeline`) are run end to end
against synthetic predictions — no model call — by the test suite. The other two
(`hair-loss-relevance`, `feature-group-split`) are read, not run: their value is
the walkthrough, and their data is placeholder.

## Verifying the examples

The example configs are exercised by the same `pytest` suite that covers the
runner. From the repository root:

```sh
# Run the whole suite (includes the example tests).
python -m pytest skills/run/scripts/tests/ -q

# Or run only the example end-to-end tests.
python -m pytest \
  skills/run/scripts/tests/test_examples_multifield.py \
  skills/run/scripts/tests/test_examples_pipeline.py -q
```

The example tests load each example's real `config/` (schema, per-field metrics,
aggregate strategy, floors) and its `data/baseline.csv`, feed synthetic
predictions through the actual scoring functions, and assert the resulting scores,
floor behavior, and composite roll-ups. They verify that the shipped example
artifacts are internally consistent and that the metrics compute as the
walkthroughs describe — not that any model achieves a particular score.
