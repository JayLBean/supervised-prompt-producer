# User-side scripts

These are the scripts the project owner wrote to wrap the skill's machinery
for the hair-loss-relevance task. They demonstrate one pattern for integrating
`spp` into a real workflow: the skill provides primitives at
`skills/run/scripts/`; user-side scripts at the task-workspace path
call those primitives plus task-specific glue (data assembly, model endpoint,
local-environment wiring).

The five scripts:

- `assemble_baseline.py` — joins the user's raw `data/sample.csv` (post bodies)
  positionally against `data/baseline.csv` (labels) to produce the
  six-column `baseline.csv` the runner consumes.
- `baseline_quality_audit.py` — runs the `baseline-quality` sub-skill's §3
  protocol against the assembled baseline. Surfaces label-vs-criterion
  consistency, class-balance sanity, and self-flagged borderlines for human
  review at G2.
- `make_splits.py` — stratified 60/20/20 split per `plan.md` §7 using
  `sklearn.model_selection.train_test_split`. Equivalent to
  `skills/run/scripts/split.py` with task-specific column names
  hard-coded.
- `probe_response.py` — sanity check used during plumbing development to
  confirm what shape the local mlx server's response object takes (notably,
  `gpt-oss-20b` returns a separate `reasoning_content` field counted against
  `max_tokens`).
- `runner.py` — orchestrates inference + eval per iteration. Loads splits,
  filters out test rows defensively, dispatches against the local OpenAI-
  compatible endpoint with `asyncio` + concurrency 5, computes F1 and the
  confusion matrix, writes `results.json` and `eval.json` under
  `runs/<model>/run_NN/`.

## Status of these files in the example

These are **read-only references** within the example. They are committed
verbatim from the user's local workspace. Path arithmetic inside them
(e.g. `Path(__file__).resolve().parents[3]`) reflects the original layout at
`spp/<task>/scripts/`, **not** the layout at `examples/<task>/scripts/`. They
will not run from the example tree as-is; treat them as a code reference, not
an executable. A future user adopting the pattern will copy them to
`spp/<task>/scripts/` in their own workspace and adjust as needed.

The scripts are deliberately not part of the skill itself. They live here as
an example of how a user might bridge from the skill's reference primitives to
their specific data sources, model endpoint, and runtime constraints.
