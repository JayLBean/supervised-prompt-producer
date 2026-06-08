# spp pipeline — decomposition-pipeline

**Created:** 2026-06-08

**Designer session:** placeholder-designer-session

**Pipeline version:** v1

---

## 1. Pipeline overview

**One-sentence description:** Extract the product mentions from a review, then
classify the review's sentiment using the review and the extracted products.

**Audience for the terminal output:** a review-triage dashboard that routes by
sentiment and highlights the products mentioned.

**Why decomposed:** the two feature groups need **different reasoning patterns**
— span-style extraction of product mentions vs. holistic sentiment
classification — and each has its own labeled ground truth, so a linear
pipeline (one prompt per group) is the right shape over one prompt carrying
both (the `structure-advisor` `decomposition` recommendation).

---

## 2. Nodes (in execution order)

A linear chain: `extract` → `classify`.

### Node 1 — extract

- **Task directory:** `sub-tasks/extract/` (a normal spp task; its `plan.md` is
  the per-node contract).
- **Reads:** `review` (an original baseline column).
- **Gold:** node-local — `products` (a list of product mentions), scored by
  `extraction_f1`.

### Node 2 — classify

- **Task directory:** `sub-tasks/classify/`.
- **Reads:** `review` (original), plus `extract.products -> products` — the
  frozen `extract` output materialized as this node's `products` input column (a
  data-plane dependency, `DESIGN.md` §7.1.12).
- **Gold:** node-local — `sentiment` (enum `positive` / `negative` /
  `neutral`), scored by `macro_f1`.

---

## 3. Composite scoring

**Composite metric:** mean — the unweighted mean of the two nodes' primary
metrics (both bounded `[0, 1]` higher-better). Per-node scores are reported in
addition.

**Composite weights:** n/a

**Composite floor:** none (each node carries its own floor in its `plan.md`).

---

## 4. Sequencing and freezing

`extract` is optimized first and **frozen at its dev floor** (a loop-level
freeze, not a per-node `/spp-finalize`). Its frozen prompt is then run over the
data to materialize `classify`'s `products` input column, and `classify` is
optimized. There is **exactly one `/spp-finalize`** — the composite finalize —
and it is the **only** sacred-test read across the whole pipeline (#6/#7).

---

## 5. Pipeline revision log

| Version | Date | Change | Reason |
|---|---|---|---|
| v1 | 2026-06-08 | Initial pipeline | Adopted the decomposition recommendation |
