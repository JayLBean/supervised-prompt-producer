# Sub-task — topic

The **topic** sub-task of the `feature-group-split` parent
example. Produces one structured field per customer-feedback row:

- **`topic`** — enum `{product, service, billing, other}`. The
  prompt categorizes what the feedback is *about*; downstream this
  routes the feedback to the relevant team's queue.

Internally K=1 (single-output classification) — the v0.1.0
degenerate case under the v0.2 protocol. The decomposition that
makes this sub-task interesting lives at the parent level: see
[`../../README.md`](../../README.md) and
[`../../walkthrough.md`](../../walkthrough.md) for why content
categorization is split off from sentiment and urgency rather than
combined into a single prompt.

This sub-task is a complete independent `spp/` task. Running
`/spp-init` on this directory's `config/plan.md` would produce a
topic-only prompt, baseline, and optimization loop without any
reference to the sentiment or urgency sub-tasks. Cross-sub-task
coordination is the user's responsibility at the parent / production
layer.

## Reading order

1. [`config/plan.md`](config/plan.md) — the v0.2 `plan.md` contract
   for this sub-task. §2 holds the one-field OUTPUT_SCHEMA.
2. [`data/baseline.csv`](data/baseline.csv) — 12 placeholder rows.
   The body text matches the sentiment and urgency baselines (same
   production input feeds all three sub-tasks); only the label
   column differs.
3. [`prompts/prompt_v01.md`](prompts/prompt_v01.md) — six-section
   prompt skeleton, persona scoped to "content router."
4. [`runs/placeholder-model/REPORT.md`](runs/placeholder-model/REPORT.md)
   — sketched REPORT with K=1 trajectory.
