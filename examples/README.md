# spp examples

Worked examples that demonstrate `spp`'s workflow and artifact shapes across the
task types the methodology supports. Each example has its own `README.md` (start
there) and, where it has computable artifacts, machine-readable configs exercised
by the test suite.

Most of these are **skeletons**, not real runs: file structure and walkthroughs are
real; data, baseline labels, prompt content, and REPORT numbers are generic
placeholders representing no real source project (see [`DESIGN.md`](../DESIGN.md) §7.2
on confidentiality and provenance). The one exception is
[`public-benchmark`](public-benchmark/), which ships a **real, fully reproducible run
on public data** with genuine, unredacted artifacts and a cross-framework comparison.

## The examples

| Example | Task type | Demonstrates | Verified by |
|---|---|---|---|
| [`hair-loss-relevance`](hair-loss-relevance/) | Binary classification | The canonical end-to-end v0.1.0 walkthrough — consultation, baseline, loop, finalize, REPORT. | Walkthrough (illustrative skeleton) |
| [`public-benchmark`](public-benchmark/) | Multi-class classification (real run) | A **real, reproducible** run on public TREC data (6-class), with a cross-framework comparison vs EvoPrompt and DSPy. Genuine, unredacted artifacts. | Real artifacts (read, not run) |
| [`multi-field-extraction`](multi-field-extraction/) | Multi-field structured output | The v0.2 schema/metrics generalization: several typed fields plus an aggregate strategy and a per-field floor. | `test_examples_multifield.py` |
| [`nested-schema`](nested-schema/) | Hierarchical labels | JSON Schema conditional structures; a top-level floor that can go unmet. | `test_examples_multifield.py` |
| [`entity-extraction`](entity-extraction/) | Structured extraction (v0.10) | `TASK_MODE = extraction`; variable-cardinality item arrays; span/alignment metrics; the empty case as a valid answer. | `test_examples_multifield.py` |
| [`feature-group-split`](feature-group-split/) | Manual feature-group split | The *manual* form of splitting one task into per-feature sub-tasks (the practice v0.11's managed pipeline coexists with). | Walkthrough (illustrative skeleton) |
| [`decomposition-pipeline`](decomposition-pipeline/) | Prompt decomposition (v0.11) | A managed linear pipeline of node-local-gold tasks; per-node isolation; one composite finalize. | `test_examples_pipeline.py` |

The four examples with machine-readable configs (`multi-field-extraction`,
`nested-schema`, `entity-extraction`, `decomposition-pipeline`) are run end to end
against synthetic predictions — no model call — by the test suite. The other three
(`hair-loss-relevance`, `feature-group-split`, `public-benchmark`) are read, not run:
their value is the artifact set itself. For the first two the data is placeholder; for
`public-benchmark` it is real public data whose scoring already happened — the run is
reproducible from its shipped configs against the companion benchmark harness.

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

The example tests load each example's real scoring configs (schema, per-field
metrics, aggregate strategy, floors — at `config/` for the single-task examples,
or per node under `sub-tasks/*/config/` plus `pipeline.json` for the pipeline) and
its `baseline.csv`, feed synthetic predictions through the actual scoring
functions, and assert the resulting scores, floor behavior, and composite
roll-ups. They verify that the shipped example
artifacts are internally consistent and that the metrics compute as the
walkthroughs describe — not that any model achieves a particular score.
