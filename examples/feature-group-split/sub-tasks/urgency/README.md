# Sub-task — urgency

The **urgency** sub-task of the `feature-group-split` parent
example. Produces one structured field per customer-feedback row:

- **`urgency`** — enum `{immediate, normal, low}`. The prompt
  classifies how quickly the feedback needs operational response;
  downstream this triggers escalation rules.

Internally K=1 (single-output classification) — the v0.1.0
degenerate case under the v0.2 protocol. The decomposition that
makes this sub-task interesting lives at the parent level: see
[`../../README.md`](../../README.md) and
[`../../walkthrough.md`](../../walkthrough.md) for why operational
prioritization is split off from sentiment and topic rather than
combined into a single prompt.

This sub-task is a complete independent `spp/` task. Running
`/spp-init` on this directory's `config/plan.md` would produce an
urgency-only prompt, baseline, and optimization loop without any
reference to the sentiment or topic sub-tasks. Cross-sub-task
coordination is the user's responsibility at the parent / production
layer.

## Reading order

1. [`config/plan.md`](config/plan.md) — the v0.2 `plan.md` contract
   for this sub-task. §2 holds the one-field OUTPUT_SCHEMA. Note
   the per-field floor on `immediate` class recall — false-
   negatives on `immediate` are operationally costly.
2. [`data/baseline.csv`](data/baseline.csv) — 12 placeholder rows.
   Same body text as sentiment and topic baselines; only the
   label column differs.
3. [`prompts/prompt_v01.md`](prompts/prompt_v01.md) — six-section
   prompt skeleton, persona scoped to "operational prioritizer."
4. [`runs/placeholder-model/REPORT.md`](runs/placeholder-model/REPORT.md)
   — sketched REPORT with K=1 trajectory and floor compliance check.
