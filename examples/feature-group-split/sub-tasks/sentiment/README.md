# Sub-task — sentiment

The **sentiment** sub-task of the `feature-group-split` parent
example. Produces one structured field per customer-feedback row:

- **`sentiment`** — enum `{positive, negative, neutral}`. The
  prompt classifies the affect of the feedback excerpt; downstream
  this feeds a customer-satisfaction dashboard.

Internally K=1 (single-output classification) — the v0.1.0
degenerate case under the v0.2 protocol. The decomposition that
makes this sub-task interesting lives at the parent level: see
[`../../README.md`](../../README.md) and
[`../../walkthrough.md`](../../walkthrough.md) for why this group
is split off from the topic and urgency sub-tasks rather than
combined with them in a single prompt.

This sub-task is a complete independent `spp/` task. Running
`/spp-init` on this directory's `config/plan.md` would produce a
sentiment-only prompt, baseline, and optimization loop without any
reference to the topic or urgency sub-tasks. Cross-sub-task
coordination is the user's responsibility at the parent / production
layer (see [`../../walkthrough.md`](../../walkthrough.md)
"Composition" section).

## Reading order

1. [`config/plan.md`](config/plan.md) — the v0.2 `plan.md` contract
   for this sub-task. §2 holds the one-field OUTPUT_SCHEMA.
2. [`data/baseline.csv`](data/baseline.csv) — 12 placeholder rows.
   Note the same body text appears in the topic and urgency sub-
   tasks' baselines (because production input is shared); only the
   label column differs across sub-tasks.
3. [`prompts/prompt_v01.md`](prompts/prompt_v01.md) — six-section
   prompt skeleton, persona scoped to "affect classifier."
4. [`runs/placeholder-model/REPORT.md`](runs/placeholder-model/REPORT.md)
   — sketched REPORT with K=1 trajectory.
