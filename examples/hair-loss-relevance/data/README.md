# Data — hair-loss-relevance

The 100-row baseline this example was run against is **NDA-protected** and is
not shipped. Only this README is published in the example. Everything outside
`data/` in the example tree (config, runs, scripts) was generated against that
baseline; the artifacts are the part of the methodology a public worked
example can carry, the data is the part it cannot.

## Schema (for a future user supplying their own data)

The skill's runner expected a single CSV at `data/baseline.csv` with these
columns:

| Column | Type | Description |
|---|---|---|
| `row_id` | string (digits "0"..."N-1") | Stable row identifier; positional integer cast as a string. |
| `document_id` | string | Source-system identifier; not consumed by the prompt. |
| `body_clean` | string | The post body the LLM sees at runtime — **the only field passed to the model**. |
| `relevant` | string `"true"` / `"false"` | Ground-truth binary label. |
| `primary_criterion` | string | Labeling-protocol code (`C1`–`C5` for positives; `Spam` / `Off-topic` / `Joke` / `News` / `Clinical` / `Boilerplate` for negatives). Not seen by the model; serves as the audit trail for `baseline-quality`. |
| `rationale` | string | One-line labeler note explaining the decision; audit trail only, not seen by the model. |

The shipped run used 100 rows total, ~52% positive, ~48% negative, all
English-language social-media posts about hair-loss discourse.

## To replicate the methodology against your own data

You do not need this baseline to read the example. You need it only if you want
to actually re-run the loop. To do that:

1. Place your own `data/baseline.csv` at this path with the schema above.
   Class balance, label provenance, and labeling protocol are your call;
   `/spp-baseline` will surface concerns at G2 if they're material.

2. Generate `data/splits.json` with the seed/ratio you want; the original run
   used a 60/20/20 stratified split with seed `42`. The skill ships a
   reference splitter at `skills/run/scripts/split.py` that produces
   the canonical schema.

3. Re-read [`../config/plan.md`](../config/plan.md) and
   [`../config/loop_spec.md`](../config/loop_spec.md) and edit them to match
   your data. The scope, metric, and stop-condition reasoning generalize; the
   class-definition prose and the cohort framing in §2 are task-specific.

4. Run the skill's four phases (`/spp-init` → `/spp-baseline` → `/spp-loop` →
   `/spp-finalize`) against your baseline. Your `runs/<model>/` directory
   structure will match the layout under `runs/gpt-oss-20b-MXFP4-Q8/` here.

## Why the data is NDA-protected

The original 100 rows are sampled from a larger third-party-licensed corpus of
hair-loss-discourse posts. The licensing terms preclude redistribution of post
bodies. Labels and labeler rationales were authored by the project owner but
they paraphrase the post content closely enough that they fall within the same
non-redistribution boundary. Rather than ship an attenuated subset, the
example ships zero rows and replaces row content uniformly across every
artifact — a cleaner privacy story than partial redaction.

## What this means for the artifacts in `runs/`

The runs that produced [`../runs/gpt-oss-20b-MXFP4-Q8/`](../runs/gpt-oss-20b-MXFP4-Q8/)
**did execute** against the NDA-protected baseline. The eval scores, confusion
matrices, iteration trajectory, REPORT, and termination artifacts are
historical fact. What's been redacted is row-level model output: every
prediction's `raw` (or `raw_excerpt`) field — the model's emitted JSON
including the rationale paraphrasing the post — is replaced with
`"[REDACTED — NDA-protected]"`. Every prompt's `<example_input>` and
`<example_output>` block has likewise been replaced with synthetic
hair-loss-discourse-shaped content; the original example was a real-data row
(the prompt's example block is consistent across all five prompt files per the
skill's `prompt-architect` convention).

`<persona>`, `<task>`, `<rules>`, and `<output_format>` in every prompt file
are the actual rule surface that the loop optimized; those are the
methodology's product and are unchanged.
