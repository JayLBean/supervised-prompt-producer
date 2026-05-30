# /spp-loop

The third phase in `spp` and the largest. Runs Phase 2 of the
methodology: the optimization loop. Iterates the prompt against
the dev set, invokes the auditor after every iteration to gate
rule-edit advancement, optionally invokes the adversary for
blind-spot probing, and stops on one of three conditions (dev
plateau, overfitting guard triggered, max iterations reached).

> **Note on slash-command notation.** `/spp-loop` is a
> methodology phase identifier used internally during a
> `/spp:run` session, not a separate user-typed slash command;
> see [`spp-init.md`](spp-init.md) for the canonical statement
> of the convention.

This document inherits the eight-section structure pinned by
[`/spp-init`](spp-init.md) and inherited by
[`/spp-baseline`](spp-baseline.md). What is structurally new:

1. **Iteration management.** The execution flow is a bounded
   loop, not a single pass. Per-iteration artifacts land in
   `runs/<model_identifier>/run_NN/` directories; the
   command resumes from the highest completed iteration on
   re-invocation.
2. **Multi-agent orchestration.** This is the first command
   that invokes more than one component during execution
   (auditor every iteration, adversary optionally). The
   ordering inside an iteration (edit → score → audit, with
   adversary slotted between discrepancy analysis and
   auditing) is contractual.
3. **Per-iteration verdict-enforced gate.** The
   `/spp-baseline` G2 pattern is applied per-iteration,
   per-edit, to the auditor's verdicts. Categorical edits
   advance silently; row-specific and unclear edits require
   an `auditor override` substring entry in `plan.md` §11.

This command is the operational embodiment of the
methodology's most load-bearing discipline — auditor
information isolation. Loosening any of the auditor's five
operational enforcement guarantees here silently breaks
`spp` as a methodology, even if the looser version produces
prompts with high dev metrics. `CLAUDE.md` §8 is the rule;
this command is where the rule is enforced. Reviewers of
PRs touching `/spp-loop` should read §3 (pre-conditions),
§4 step 11 (auditor invocation), and §5 (gate enforcement)
as a unit, with the auditor agent's §2 in another tab.

---

## 1. Command identity

`/spp-loop` is the Phase 2 entry point: it runs the
optimization loop after `/spp-init` and `/spp-baseline` have
completed (G1, G2, G3 approved in `plan.md` §11). It enforces
gate G4 (dry-run gate) once before the first iteration runs,
runs iterations until a stop condition is met, persists per-
iteration artifacts to `runs/<model_identifier>/run_NN/`,
writes one of `SUCCESS.md` / `EARLY_STOP.md` / `FAILED.md`
at termination, and exits.

What the command produces, exhaustively:

- `runs/<model_identifier>/_dryrun/` — the gate-G4 dry-run
  output, kept for audit purposes.
- `runs/<model_identifier>/run_NN/` directories for each
  iteration, each containing `prompt_v(N).md`,
  `results.json`, `eval.json`,
  `discrepancy_analysis.md`, and `auditor_review.md`.
- One of `runs/<model_identifier>/SUCCESS.md`,
  `runs/<model_identifier>/EARLY_STOP.md`, or
  `runs/<model_identifier>/FAILED.md` recording the
  termination reason.
- Revision-log entries in `plan.md` §11 for any auditor
  overrides recorded during the loop.

What the command does NOT produce — the boundary against
`/spp-finalize`:

- `REPORT.md` and `PROMPT_FROZEN_v01.md` are
  `/spp-finalize`'s outputs, generated only after the
  sacred test set is read (gates G5 / G6).
- No modification to `data/baseline.csv` or
  `data/splits.json` (those are `/spp-baseline`'s outputs
  and are read-only here).
- No modification to `plan.md` outside §11 revision-log
  entries.
- No git operations, no commits.
- No reads of test rows from `data/splits.json`. The test
  partition is sacred until `/spp-finalize`
  (`DESIGN.md` §10). The runner's defense-in-depth posture
  is to verify-not-touched at the runner level, on top of
  the methodology-level guarantee in
  `loop_spec.md` §7.

The judgment for rule-edit advancement lives in the
[`auditor`](../agents/auditor.md) agent. The blind-spot
probing (when enabled) lives in the
[`adversary`](../agents/adversary.md) agent. The
orchestration, filesystem persistence, gate enforcement,
and information-isolation enforcement live here. Same
separation pattern as `/spp-init` ↔ designer and
`/spp-baseline` ↔ baseline-quality.

---

## 2. Invocation

```
/spp-loop
```

No arguments. Same convention as `/spp-baseline`. The
command reads `spp/<task_name>/config/plan.md` and
`spp/<task_name>/config/loop_spec.md` to know which task it
is operating on. The active task is determined by the **most
recently approved-through-G3 plan in the working tree** —
typically the plan whose `/spp-baseline` invocation just
completed.

**Disambiguation.** "Most recently approved through G3"
means the plan whose `plan.md` §11 revision log contains a
G3-approval entry (the one recording splits confirmation),
with the most recent timestamp. If multiple plans tie, or
one or more candidates have missing/unparseable timestamps,
the command does not pick — it lists all candidates and
asks the user to choose:

> Multiple `spp/*/` tasks have plans approved through G3.
> Which one should `/spp-loop` run on?
>   1) `spp/support-billing-triage/`
>   2) `spp/issue-categorization-v2/`
> Reply with the number or the task name.

The command refuses to run without G1, G2, and G3 having
been approved (verifiable from `plan.md` §11 entries) and
without `data/baseline.csv` + `data/splits.json` existing
on disk. There is no "loop without a baseline" path — that
is by design, since the loop scores against dev rows that
only exist in `splits.json`.

---

## 3. Pre-conditions

The command refuses to proceed unless all of the following
are true. Pre-condition failures exit with a specific error
message naming the missing piece — same loud-and-specific
pattern as the predecessors.

1. **Working directory is the user's project root.** Same
   detection as `/spp-init` §3 and `/spp-baseline` §3.

2. **The `spp` skill is installed.** The command verifies
   that
   [`agents/auditor.md`](../agents/auditor.md) is readable,
   `templates/plan.md.template` and
   `templates/loop_spec.md.template` are readable, and (if
   `ADVERSARY_FLAG = on` in `loop_spec.md` §4)
   [`agents/adversary.md`](../agents/adversary.md) is
   readable. A missing adversary file when the flag is
   `on` is fatal; a missing adversary file when the flag
   is `off` is fine.

3. **An approved-through-G3 `plan.md` exists.** At least
   one `spp/<task_name>/config/plan.md` is on disk with
   `PLAN_VERSION ≥ v1`, validation rules pass, and the §11
   revision log has G1, G2, and G3 approval entries (in
   that order). Multiple plans ⇒ user picks per §2.

4. **`loop_spec.md` exists and validates.** Path:
   `spp/<task_name>/config/loop_spec.md`. The command runs
   the 10 mechanical validation rules from
   `loop_spec.md.template`'s "Validation rules" section
   (§"Validation rules", post-template-body). The
   load-bearing rules for this command:
   - Rule 4: §3 per-stage subagent configuration block
     contains the literal nine lines unmodified
     (discrepancy_subagent / discrepancy_score_access /
     discrepancy_prior_iteration_access /
     rule_edit_subagent / rule_edit_baseline_access /
     rule_edit_score_access / auditor /
     auditor_score_access / auditor_frequency_reduction).
   - Rule 5: §4 adversary boundaries block is present and
     unmodified.
   - Rule 6: §7 sacred-test-set posture block contains the
     literal two lines `test_set_access_during_loop:
     forbidden` / `test_set_first_use: /spp-finalize
     only`, unmodified.

   If any literal block has been modified, the command
   refuses to start with a specific error naming the
   modified block. **This check is the runner's defense
   against silent methodology weakening.** A future
   contributor or user who hand-edits `loop_spec.md` to
   remove the auditor isolation block (perhaps to "speed
   up" the loop) hits a hard refusal here, not silent
   advancement.

5. **`PLAN_VERSION` consistency between `loop_spec.md` and
   `plan.md`.** The `loop_spec.md` references a
   `PLAN_VERSION` in its top header. If `plan.md`'s
   current version is higher (because `/spp-baseline`
   recorded class-definition refinements in §11 that bumped
   the plan version), the command surfaces:

   > loop_spec.md references plan.md v{{LOOP_PLAN_VER}};
   > current plan.md is v{{CURRENT_PLAN_VER}}. Re-derive
   > loop_spec.md from the current plan, or confirm the
   > existing loop_spec is still valid by adding a §11
   > entry to plan.md with Reason mentioning "loop_spec
   > re-validated against v{{CURRENT_PLAN_VER}}".

   This addresses the open question raised in
   `/spp-baseline` PR review: `loop_spec.md`'s
   `PLAN_VERSION` is **derivation provenance**, not a live
   pin; the runner surfaces the discrepancy and lets the
   user resolve.

6. **`data/baseline.csv` exists** with schema matching
   `plan.md` §2's `LABEL_SPACE` (same schema check as
   `/spp-baseline` §3 step 7).

7. **`data/splits.json` exists** with the schema defined in
   `/spp-baseline` §4 step 9 (`schema_version`,
   `stratification_key`, `seed`, `ratios`, `row_ids` with
   `train` / `dev` / `test` arrays).

8. **The model identifier in `loop_spec.md` §5 is
   reachable.** A quick connectivity check (HTTP HEAD or a
   single-token completion against the
   `API_ENDPOINT`), not a full inference run. Failure is
   surfaced with the exact error so the user can fix the
   endpoint or credentials before iteration costs accrue.

9. **The task directory is writable.** Specifically,
   `spp/<task_name>/runs/<model_identifier>/` will be
   created if it does not exist; the parent must be
   writable.

10. **No partial run-state requires user resolution.** If
    `runs/<model_identifier>/` exists, the command
    enumerates `run_NN/` directories and identifies any
    that are partial (some files present but not all five
    of `prompt_v(N).md`, `results.json`, `eval.json`,
    `discrepancy_analysis.md`, `auditor_review.md`).
    Partial directories prompt the user with a specific
    choice (resume from the previous complete iteration,
    delete the partial directory and restart that
    iteration, or abort). See §7 resumability.

The `loop_spec.md` literal-block check (rule 4) is
architecturally important enough that a contributor reading
this command should notice it lives at pre-conditions — not
inside the iteration loop — because its job is to prevent
the loop from starting on a weakened spec, not to monitor
the spec mid-loop.

---

## 4. Execution flow

The longest section in the project. The orchestration has
three structural layers:

- **Pre-loop layer:** validation, dry-run, gate G4 (steps
  1–5).
- **Iteration layer:** the loop body, repeated up to
  `MAX_ITERATIONS` (steps 6–13 within each iteration).
- **Post-loop layer:** termination identification, output
  writing, exit (steps 14–16).

Steps marked **(pre-display)** happen before any user-
facing output; **(consultation)** involves user back-and-
forth (gate prompts, override resolution); **(per-
iteration)** is iteration-internal work, repeated;
**(post-loop)** happens after the iteration layer
terminates.

### Pre-loop layer

1. **(pre-display) Verify pre-conditions.** Run §3 checks.
   Exit on failure with a specific error.

2. **(pre-display) Read configuration.** Load `plan.md`
   (the contract — §2 class definitions, §3 success
   criterion, §4 metric, §6 baseline status, §9 gate
   phrases, §11 revision log), `loop_spec.md` (the run-
   time mechanics — §1 budget, §2 stop criteria, §3
   auditor configuration, §4 adversary configuration, §5
   model and execution, §7 sacred test set posture), and
   `data/splits.json` (partition row IDs). The runner
   keeps the test partition's row IDs in memory only as
   an explicit **forbidden set** — any code path that
   reads from `data/baseline.csv` filters out test row
   IDs as a sanity check, even when the calling logic is
   already filtering by train/dev. Defense in depth.

3. **(pre-display) Stage `runs/<model_identifier>/`.**
   Create the directory if it does not exist. The
   `<model_identifier>` segment is the exact string from
   `loop_spec.md` §5 — no aliasing
   (`DESIGN.md` §2.2). The atomic-checkpoint write
   discipline (`tmp + fsync + rename`) inherited from
   `/spp-init` applies to every artifact written under
   this directory.

4. **(pre-display) Run dry-run on 3 train rows.** Build
   `run_01/prompt_v01.md` first via the prompt-architect
   sub-skill (per §4 step 6's provenance rule), then call
   the model on 3 rows sampled from
   the train partition (deterministically — first 3 row
   IDs in `splits.json`'s `train` array, sorted), verify
   the output parses against the `LABEL_SPACE`. Results
   land in `runs/<model_identifier>/_dryrun/results.json`
   under a leading-underscore directory so it is
   grepably distinct from real iteration directories.
   The dry-run does not touch dev or test rows.

5. **(consultation) Present at gate G4.** The dry-run
   output is shown to the user:

   > Dry-run on 3 train rows complete. Predictions:
   >   row_id={{ID1}} → {{LABEL1}} (label: {{GT1}})
   >   row_id={{ID2}} → {{LABEL2}} (label: {{GT2}})
   >   row_id={{ID3}} → {{LABEL3}} (label: {{GT3}})
   > Output schema valid: yes / no per row.
   > Model: {{MODEL_IDENTIFIER}} at {{API_ENDPOINT}}.
   >
   > Dev rows have not been touched. Test rows are sacred
   > until /spp-finalize.
   >
   > To approve and proceed to iteration 1, reply with
   > the exact G4 approval phrase you recorded in §9 of
   > plan.md: `{{G4_APPROVAL_PHRASE}}`. To abort,
   > reply "abort". To revise the recorded phrase, reply
   > "revise §9".

   Same literal-string-equality match as G1 / G2 / G3.
   Mismatch surfaces a specific message naming both the
   recorded phrase and the user's input. Failure modes
   include parse errors in the dry-run, model unreachable,
   or output schema mismatch — each surfaced inline before
   the user is asked for the approval phrase.

### Iteration layer

The iteration index `N` starts at 1 (the first iteration's
artifacts land in `run_01/`) and increments after each
iteration's auditor invocation has produced a verdict and
the verdict-enforced gate has resolved.

For each iteration `N` from 1 to `MAX_ITERATIONS`:

6. **(per-iteration) Run prompt against train and dev
   sets.** Read `prompt_v(N).md`. For `N = 1`, the runner
   builds `run_01/prompt_v01.md` at the start of this step
   by invoking the prompt-architect sub-skill (Phase 2
   step 10) on `plan.md` §2 (class definitions), §4
   (metric and any output-schema constraints), and
   `loop_spec.md` §5 `MODEL_DIRECTIVES` (model-locked
   header strings such as Qwen `/no_think`). The build
   uses an atomic checkpoint write. The consultation
   phase (`/spp-init`) produces the *contract*
   (`plan.md`, `loop_spec.md`); the loop generates the
   artifacts. For `N > 1`, `prompt_v(N).md` is the
   verdict-gate-resolved prompt produced at the end of
   iteration `N-1` (already on disk in `run_N/` from step
   10 of the previous iteration). Run inference on every
   row in
   the train and dev partitions, in parallel up to
   `CONCURRENCY` from `loop_spec.md` §5, with retries per
   `RETRY_POLICY`. Persist
   `runs/<model_identifier>/run_N/results.json` with
   per-row predictions. **Test rows are not in the input
   set** — the runner constructs the input set from the
   union of `train` and `dev` row IDs in `splits.json`,
   never from the full `baseline.csv` minus a filter.
   Positive enforcement, not a deny-list.

7. **(per-iteration) Compute metrics.** Read
   `results.json`, compute per-field and aggregate metrics
   per the v0.2 metrics-layer contract
   (`DESIGN.md` §7.1.1 metrics layer; `metric-design`
   SKILL.md §3.1–§3.3), and persist
   `runs/<model_identifier>/run_N/eval.json` with the v0.2
   shape. Test rows are not scored, not predicted on, not
   in the eval surface in any way.

   **Inputs.** The runner reads the OUTPUT_SCHEMA from
   `plan.md` §2. Until bucket 5 lands the v0.2
   `plan.md.template` carrying OUTPUT_SCHEMA, the runner
   falls back to v0.1.0's `LABEL_SPACE` and treats it as a
   degenerate single-field schema (`{label: <enum from
   LABEL_SPACE>}`). The fallback is the K=1 path; the K > 1
   path becomes operational when bucket 5 lands. Per-field
   metrics, the aggregate strategy, and any per-field floors
   are read from the corresponding `plan.md` §3 / §4 fields
   (`METRIC_NAME[f]`, `AGGREGATE_STRATEGY`,
   `AGGREGATE_WEIGHTS` when applicable, `FLOOR[f]` when
   applicable; v0.1.0 plans expose these as scalar v0.1.0
   fields and the runner promotes them to the K=1 shape).

   **For each OUTPUT_SCHEMA field `f`**, compute `f`'s
   primary `METRIC_NAME[f]` against ground-truth values for
   train and dev separately. Compute auxiliary structures
   appropriate to the metric type — confusion matrix for
   enum-F1 / `macro_F1`, IoU distribution for span-IoU,
   residual distribution for number-MAE / -RMSE, per-class
   statistics where applicable.

   **Compute the aggregate metric** per `AGGREGATE_STRATEGY`
   (`macro` / `weighted` / `min`) on the K per-field metric
   values, train and dev separately. The aggregate is the
   single number the loop's stop discipline (step 13) gates
   against.

   **Compute floor compliance.** For each field carrying a
   `FLOOR[f]`, compare the field's dev metric against the
   floor; record `met` / `unmet`. Fields without a floor
   record `not_specified`.

   **Persist `eval.json` with four top-level sections**
   (`DESIGN.md` §7.1.1 metrics-layer decision 5; the
   `per_row` array added by §7.1.4 finalize statistics):

   - **`per_field`** — keyed by field name; each field
     carries `train`, `dev`, the auxiliary structure(s)
     appropriate to its metric type, and per-class
     statistics where applicable.
   - **`aggregate`** — `train`, `dev`, `strategy` (one of
     `macro` / `weighted` / `min`), and `weights` (the
     vector of K weights when `strategy == "weighted"`,
     absent otherwise).
   - **`floor_compliance`** — keyed by field name; each
     field carries `floor` (number or `null`) and `status`
     (`met` / `unmet` / `not_specified`).
   - **`per_row`** — the retained per-row score vector
     (`row_id`, `y_true`, `y_pred`, `correct`), the input
     the v0.3 finalize statistics (`DESIGN.md` §7.1.4)
     resample. It carries score signal and lives inside
     `eval.json`, so it is withheld from the auditor (step
     11) and rule-edit (step 10) stages exactly as the rest
     of `eval.json` is; no allow-list changes.

   The K=1 degenerate case produces an `eval.json` whose
   `per_field` section has one entry, `aggregate` equals
   that entry's primary metric, and `floor_compliance` has
   one row — equivalent in content to v0.1.0's eval.json.

8. **(per-iteration) Invoke discrepancy subagent.** The
   discrepancy analysis is produced by an isolated
   subagent — **not by the orchestrator's main context**.
   The orchestrator constructs a fresh subagent invocation
   with an explicit allow-list of inputs; the subagent's
   context terminates when it returns. This is the first
   of three (or four with adversary) per-stage isolated
   invocations in the iteration; the auditor at step 11
   is the most stringent instance.

   **Allow-list inputs** (positive enforcement, not a
   deny-list):
   - `runs/<model_identifier>/run_N/eval.json` — metric
     movement, per-field metrics, aggregate, and per-class
     statistics. Under v0.2 the file carries `per_field`,
     `aggregate`, and `floor_compliance` top-level
     sections (step 7); under K=1 each section has one
     entry.
   - `runs/<model_identifier>/run_N/results.json` —
     per-row predictions on train + dev. Under v0.2 each
     row's prediction is a structured object with one
     value per OUTPUT_SCHEMA field; under K=1 the
     structured object has one field.
   - `data/baseline.csv` filtered to **disagreed dev row
     IDs only** — the subagent reads all field
     ground-truth values and input content for the rows
     that drove the discrepancy. The disagreed-row filter
     is **any-field-disagreed** per `DESIGN.md` §7.1.1
     per-field methodology application layer: a row enters
     the filtered set if any field's prediction does not
     match ground truth on dev. Train rows, test rows, and
     dev rows where every field's prediction matched
     ground truth are not in scope.
   - `plan.md` §2 — class definitions and OUTPUT_SCHEMA
     (or LABEL_SPACE under the K=1 fallback) for cluster
     naming and field-attribution.
   - `runs/<model_identifier>/run_N/prompt_v(N).md` —
     the current prompt, for cluster-naming context
     (the subagent may want to know which rule the
     prompt's `<rules>` section already covers when
     proposing an edit). Including this is a soft
     choice — see PR description's open question — but
     errs toward the subagent having the context it
     needs to name clusters meaningfully.

   **Reference material (not a data input).** In addition to
   the data allow-list above, the discrepancy subagent reads
   the
   [`technique-advisor`](../sub-skills/technique-advisor/SKILL.md)
   sub-skill and its `techniques/*.yaml` catalog — the same
   category of opinionated reference material the rule-edit
   subagent reads `prompt-architect` for (§4 step 10). The
   catalog is technique definitions, not data: it carries no
   row content, no scores, and no prior-iteration artifacts.
   Consulting it does **not** expand the data allow-list and
   adds no data path to this stage (`DESIGN.md` §7.1.6;
   `technique-advisor` SKILL.md §5 — a suggestion is not a
   data path).

   **The subagent does NOT receive:** prior iterations'
   `discrepancy_analysis.md` files, prior
   `auditor_review.md` files, prior `prompt_v(M).md`
   for `M < N`, train rows that the model predicted
   correctly, test rows of any partition, any artifact
   not enumerated above.

   **The subagent produces** `runs/<model_identifier>/run_N/discrepancy_analysis.md`
   per the structure below. **Row content does not
   appear in the persistent artifact** — clusters
   reference member rows by ID only. The subagent reads
   row content for its own analysis; the artifact
   abstracts the analysis into clusters.

   Output structure (documented inline so future readers
   are not guessing) — the v0.2 generalization adds
   **field attribution** to each cluster and to each
   proposed rule edit, per `DESIGN.md` §7.1.1 per-field
   methodology application layer. Row-content
   non-persistence is unchanged. The v0.5 generalization
   adds an optional **technique-consultation** step and a
   corresponding output section (below); it changes neither
   the allow-list nor row-content non-persistence.

   **Technique consultation (v0.5).** After clustering, for
   each cluster the subagent checks whether the cluster's
   shared property matches a catalogued `symptom` in the
   `technique-advisor` catalog, applying that sub-skill's
   matching procedure (`technique-advisor` SKILL.md §3.2).
   On a match, it records the matched entry's categorical
   `recommendation` — naming the field, the symptom observed
   (in categorical terms), the technique, and the
   `output_form` adopting it would produce — in the
   **Technique recommendations** output section. A non-match
   is the common case, recorded as no recommendation; the
   subagent does not stretch a symptom to fit. The
   recommendation is **advisory** — recorded in the artifact
   for surfacing to the user at the iteration's HITL gate,
   never auto-applied, and never carrying row content
   (`technique-advisor` SKILL.md §5). Adopting a technique
   is a user-initiated `plan.md` / OUTPUT_SCHEMA revision;
   the discrepancy stage edits neither the prompt nor the
   plan.

   - **Failure clusters** section: one subsection per
     identified cluster, with cluster name, **primary
     field name** (the OUTPUT_SCHEMA field whose
     disagreements the cluster's shared property
     explains; under K=1 this is the lone field),
     member row IDs (no row content), shared property
     of the cluster (described in plain English without
     quoting row content; the subagent may name
     cross-field correlation observations here when
     they inform the cluster's interpretation, since it
     reads ground truth for all fields on disagreed
     rows), and the rule edit proposed to address the
     cluster.

     Rows that disagree on multiple fields appear in
     **multiple clusters** (once per field-disagreement)
     — the cluster is the unit of explanation, not the
     row.
   - **Proposed rule edits** section: enumerated edits
     1..k, each with the rule's proposed wording, the
     cluster it addresses, **`target_fields`** (a list
     naming every OUTPUT_SCHEMA field the edit affects;
     typically the cluster's primary field, but may
     include additional fields when the edit's rationale
     spans them; under K=1 the list has length 1), and
     a brief rationale (no row content). The auditor's
     per-edit-per-field verdict scoping at step 11
     consumes this list.
   - **Motivating-row references**: row IDs only, no
     row content duplicated. Diff-friendly per the same
     discipline as `splits.json` row-ID-only
     references.
   - **Technique recommendations** section (v0.5,
     possibly empty): zero or more entries, each naming
     the **field**, the **symptom observed** (categorical,
     no row content), the **technique id** matched from
     the `technique-advisor` catalog, and the
     **`output_form`** adopting it would produce. Each
     entry is the matched catalog entry's categorical
     `recommendation`. The section is empty when no
     cluster matched a catalogued symptom — the common
     case, and not a defect. No row content, predicted
     labels, or scores appear here; like every other part
     of the artifact, recommendations reference a field
     and a class of failures, never specific rows.

   The subagent's context terminates when it returns.
   The orchestrator continues with only the file
   output. Row content read by the subagent is gone
   from any context the rule-edit subagent at step 10
   will receive.

9. **(per-iteration, conditional) Invoke adversary** if
   `ADVERSARY_FLAG = on` in `loop_spec.md` §4. The runner
   satisfies the four operational guarantees from
   [`agents/adversary.md`](../agents/adversary.md) §6:
   - Allow-list inputs:
     `runs/<model_identifier>/run_N/prompt_v(N).md`,
     `runs/<model_identifier>/run_(N-1)/discrepancy_analysis.md`,
     and `plan.md` §2 only. No baseline rows, no splits,
     no eval artifacts. **First-iteration carve-out:**
     for `N = 1`, no prior `discrepancy_analysis.md`
     exists; the adversary's invocation context is
     `prompt_v01.md` and `plan.md` §2 only. The runner
     does not synthesize a placeholder discrepancy
     analysis or pass the current iteration's discrepancy
     in lieu of a prior one (the current iteration's
     discrepancy does not exist yet at adversary
     invocation time — the runner invokes the adversary
     after generating discrepancy analysis at step 8, so
     for iteration 1 the relevant prior input is simply
     absent). Subsequent iterations include the prior
     `discrepancy_analysis.md` from `run_(N-1)/`.
   - Score-blindness: `eval.json` and `results.json`
     exist on disk by the time the adversary runs;
     neither is in the invocation context.
   - Non-persistence: the adversary's output is appended
     inline to this iteration's `discrepancy_analysis.md`
     under the literal non-persistence header line
     (`Adversarial rows — generated for iteration N. Not
     persisted, not added to baseline, not promoted to
     splits.`). The runner does not write the synthetic
     rows to a separate file, does not append them to
     `data/baseline.csv`, does not add them to
     `data/splits.json`.
   - One invocation per iteration. The runner does not
     silently re-invoke.

   The runner's invocation contract is unchanged in v0.2.
   The adversary's **output shape** changes — synthetic
   rows now carry full OUTPUT_SCHEMA-shaped ground truth
   (one value per field) rather than a single label, per
   `DESIGN.md` §7.1.1 per-field methodology application
   layer and `agents/adversary.md` §6. Under K=1 the
   structured ground truth has one value, equivalent to
   v0.1.0's "label." The runner does not need to enforce
   the multi-field shape — it is the adversary agent's
   contract; the non-persistence and score-blindness
   guarantees the runner enforces apply unchanged.

10. **(per-iteration) Invoke rule-edit subagent.** The
    rule-edit work is produced by an isolated subagent —
    **not by the orchestrator's main context**, and
    **not by the discrepancy subagent** whose context
    has already terminated. The orchestrator constructs
    a fresh subagent invocation with an explicit allow-
    list; the subagent's context terminates when it
    returns. The crucial isolation property: **no row
    content reaches this subagent under any path.** The
    discrepancy artifact references rows by ID only
    (per step 8's output structure); the rule-edit
    subagent has no access to `baseline.csv`,
    `eval.json`, or `results.json`.

    **Allow-list inputs** (positive enforcement):
    - `runs/<model_identifier>/run_N/prompt_v(N).md` —
      the prompt to edit.
    - `runs/<model_identifier>/run_N/discrepancy_analysis.md`
      — proposed edits with row IDs but no row content.
    - `plan.md` §2 — class definitions.
    - The
      [`prompt-architect`](../sub-skills/prompt-architect/SKILL.md)
      sub-skill — for structural guidance on which
      sections accept which kinds of content.

    **The subagent does NOT receive:** `data/baseline.csv`,
    `eval.json`, `results.json`, prior `auditor_review.md`
    files, any prior iteration's artifacts beyond what's
    in the current `discrepancy_analysis.md`. **No row
    content reaches this subagent under any path** — this
    is the load-bearing property the per-stage isolation
    pattern enforces beyond the auditor's score isolation.

    **The subagent produces**
    `runs/<model_identifier>/run_(N+1)/prompt_v(N+1).md`
    (atomic checkpoint write into the next iteration's
    directory). The edits are applied as proposed; the
    auditor reviews them in step 11. The `run_(N+1)/`
    directory is staged here so the auditor's output
    can land in the same directory.

    The subagent's context terminates when it returns.
    The auditor at step 11 reviews the produced prompt
    afresh with its own allow-list.

11. **(per-iteration) Invoke auditor subagent.** The
    third per-stage isolated subagent invocation in the
    iteration (after discrepancy at step 8 and rule-edit
    at step 10), and the most stringent — the auditor's
    score-access prohibition is on top of the broader
    allow-list discipline shared across stages. The
    runner satisfies the five operational enforcement
    guarantees from
    [`agents/auditor.md`](../agents/auditor.md) §2:
    - **Allow-list inputs (positive enforcement, not a
      deny-list):**
      `runs/<model_identifier>/run_N/prompt_v(N).md`,
      `runs/<model_identifier>/run_(N+1)/prompt_v(N+1).md`,
      `runs/<model_identifier>/run_N/discrepancy_analysis.md`,
      `plan.md` §2 (extracted as a string slice, not the
      whole file), and prior `auditor_review.md` files
      from `runs/<model_identifier>/run_(M)/` for every
      `M` with `1 ≤ M ≤ N` that exists. The runner builds
      this list explicitly and passes only the named
      files; any future contributor reading the runner
      code should see a literal allow-list, not an
      "everything except scores" deny-list.
    - **Score artifacts withheld even when present.**
      `runs/<model_identifier>/run_N/eval.json` and
      `runs/<model_identifier>/run_N/results.json` exist
      on disk (step 7 wrote them); they are not in the
      invocation context, neither directly nor as
      derived strings.
    - **Stateless invocation across iterations.** Each
      auditor call is constructed fresh from the allow-
      list. The runner does not accumulate score history,
      does not pass prior verdicts beyond what's read
      from `auditor_review.md` files, does not maintain
      any implicit state.
    - **No score-derived hints.** The runner does not
      pass any string that mentions or summarizes the
      iteration's metric movement. A "this iteration's
      F1 dropped, please scrutinize" hint *is* score
      signal even without a number; the runner's hint
      surface is empty by design.
    - **No test-set artifacts.** The runner does not pass
      test row IDs, test predictions (none exist), or
      anything derived from the test partition.

    The auditor produces
    `runs/<model_identifier>/run_(N+1)/auditor_review.md`
    with **per-edit-per-field verdicts** under v0.2
    (`DESIGN.md` §7.1.1 per-field methodology application
    layer; `agents/auditor.md` §6). For each rule edit in
    `discrepancy_analysis.md`, the auditor produces one
    verdict per OUTPUT_SCHEMA field listed in the edit's
    `target_fields`. An edit with K target fields gets K
    independent verdicts; an edit can be `categorical` for
    field A and `row-specific` for field B. Under K=1
    every edit has exactly one target field and one
    verdict — equivalent to v0.1.0's per-edit shape.
    Atomic checkpoint write.

    **Stronger semantic content under per-stage
    isolation.** Because the rule-edit subagent at
    step 10 had no row-content exposure, the edits the
    auditor reviews were generated under the same
    information-isolation discipline the auditor
    enforces. A `categorical` verdict from the auditor
    therefore means the edit is categorical *and* was
    generated without row-content exposure — a stronger
    guarantee than the previous "categorical despite
    possible row exposure" reading. The auditor's job
    is more focused: verify categorical-vs-row-specific
    judgment, plus catch-and-flag any edit that
    managed to be row-specific despite the upstream
    isolation (a row-specific edit reaching the
    auditor under per-stage isolation is now anomalous,
    not expected).

12. **(per-iteration, possibly consultation) Enforce
    auditor verdict gate.** Under v0.2 the gate iterates
    over **per-edit-per-field verdicts** rather than
    per-edit verdicts. For each
    `(edit_index, target_field)` combination in iteration
    `N`'s `auditor_review.md`:
    - **`categorical` verdict for `(edit, field)`**: the
      `(edit, field)` combination is approved. If every
      target field of an edit is `categorical`, the edit
      advances — it is already present in
      `prompt_v(N+1).md` from step 10. No user-facing
      prompt for that edit; the gate is invisible in the
      happy path.
    - **`row-specific` verdict** (recommendation `revert`
      or `generalize`) for any `(edit, field)`: the edit
      does not advance unless the user records an
      override that explicitly covers the
      `(edit, field)` combination. The runner reverts
      the edit in `prompt_v(N+1).md` if no override is
      recorded.
    - **`unclear` verdict** (recommendation `clarify`)
      for any `(edit, field)`: same pattern as
      `row-specific`.

    **Override syntax under v0.2.** A `plan.md` §11 row
    overrides an `(edit, field)` combination when its
    Reason field contains:

    1. The literal substring `auditor override`
       (unchanged from v0.1.0, whitespace-stripped,
       case-insensitive); **and**
    2. For K > 1 schemas, one or more bracketed tokens
       of the form `[edit-N.field-name]` — for example
       `[edit-2.category]` or `[edit-2.brand_known]`.
       A single override entry may cover multiple
       `(edit, field)` combinations by listing multiple
       bracketed tokens; whitespace between tokens is
       ignored. Field names match the OUTPUT_SCHEMA
       field names verbatim, hyphenated as written in
       the schema.

    **Backward compatibility for K=1.** When OUTPUT_SCHEMA
    has one field (or under the v0.1.0 LABEL_SPACE
    fallback), an `auditor override` Reason **with no
    bracketed tokens** covers the lone field implicitly.
    This preserves v0.1.0's per-edit override semantics
    verbatim — existing v0.1.0 §11 entries continue to
    work without modification under the v0.2 runner.
    For K > 1 schemas the bracketed tokens are required;
    an unscoped `auditor override` Reason fails to cover
    any `(edit, field)` combination and the runner
    refuses to advance.

    **Gate-advance condition.** The runner advances the
    iteration when **every non-`categorical`
    `(edit, field)` combination** has a matching
    override. An edit with K target fields and a mix of
    `categorical` and non-`categorical` verdicts
    requires overrides only for the non-`categorical`
    combinations. An edit with all-`categorical`
    verdicts requires no override.

    **User-facing prompt** when the gate halts on
    non-`categorical` verdicts:

    > Iteration N edit {{IDX}} (target field
    > `{{FIELD}}`) verdict: {{VERDICT}}.
    > Auditor's reasoning: {{REASONING}}.
    > Recommendation: {{RECOMMENDATION}}.
    >
    > To accept this `(edit, field)` combination despite
    > the verdict, add an entry to plan.md §11 with
    > Reason containing `auditor override` and the token
    > `[edit-{{IDX}}.{{FIELD}}]` (or a multi-token list
    > covering several combinations) and a timestamp
    > after {{AUDITOR_TS}}. Then continue.
    > To revert this `(edit, field)` and proceed, reply
    > "revert".
    > To revise the edit and re-audit, reply "revise"
    > and provide the new wording inline.

    The gate is **per-(edit, field) combination**, not
    per-edit and not per-iteration. An iteration can
    advance 2 categorical edits and 1 partially-overridden
    multi-target edit while halting on 1 fully-non-
    categorical edit pending user resolution. The
    override-substring match is literal (whitespace-
    stripped, case-insensitive on the substring `auditor
    override`); the bracketed-token match is literal
    case-sensitive on the field name (matching the
    schema's exact spelling); fuzzy matching is
    forbidden per §"Versioning". This pattern inherits
    from `/spp-baseline` §5's G2 enforcement: **the
    verdict adds a literal-string check on top of the
    gate's normal flow.**

13. **(per-iteration) Check stop conditions.** Three
    conditions, evaluated in order. Under v0.2 each
    condition reads from `eval.json`'s `aggregate` block
    (the v0.2 metrics-layer's stop-discipline decision —
    `DESIGN.md` §7.1.1 metrics layer; per-field metrics
    are computed and persisted but do not independently
    gate). Under K=1 the `aggregate` value equals the
    lone field's primary metric, so the v0.1.0 behavior
    is reproduced verbatim.

    - **Dev plateau:** the **aggregate dev metric**
      improvement over the last `K` iterations (default
      `K = 3`, drawn from `loop_spec.md` §2's
      `DEV_PLATEAU_THRESHOLD` definition) falls below
      the threshold. Requires at least `K + 1` completed
      iterations (so the deltas can be computed); not
      applicable for `N < K + 1`.
    - **Overfitting guard:** `aggregate.train -
      aggregate.dev` exceeds `OVERFIT_GUARD` for two
      consecutive iterations. The two-consecutive
      condition prevents a single noisy iteration from
      triggering an early stop; the load-bearing failure
      mode it catches is the prompt fitting train without
      generalizing to dev (`DESIGN.md` §2.1).
    - **Max iterations:** `N ≥ MAX_ITERATIONS`.

    The loop continues to iteration `N + 1` if none of
    these is met. If any is met, the loop terminates and
    proceeds to step 14. The terminating condition is
    recorded for use in the termination artifact.

    **Per-field movement is tracked but does not gate.**
    `eval.json`'s `per_field` section is computed every
    iteration and reaches the discrepancy subagent's
    allow-list (step 8) so per-field disagreement
    attribution remains possible. None of the three stop
    conditions reads `per_field` directly; promoting
    per-field movement to a stop trigger would multiply
    the stop surface and silently change the
    aggregate-plateau guarantee.

### Post-loop layer

14. **(post-loop) Identify the best-performing
    iteration.** The "best" iteration is the one with the
    highest dev metric value, where "metric" is the
    primary metric named in `plan.md` §4 §"primary".
    Ties are broken by lower train-vs-dev delta (the
    iteration with the closer train/dev alignment, on
    the assumption that closer alignment indicates less
    overfitting). If `plan.md` §4 names a non-standard
    aggregate (e.g., precision-at-recall-target),
    "highest" is whatever direction the metric specifies
    in §4. The runner does not invent a tiebreaker
    beyond the train-vs-dev delta — further ambiguity
    surfaces to the user.

15. **(post-loop) Write termination artifact.** Exactly
    one of:
    - `runs/<model_identifier>/SUCCESS.md` — terminating
      condition was dev plateau **and** the best
      iteration's aggregate dev metric meets or exceeds
      the headline criterion in `plan.md` §3 **and**
      every per-field floor on the best iteration is
      `met` or `not_specified` (per the
      `floor_compliance` block of the best iteration's
      `eval.json`).
    - `runs/<model_identifier>/EARLY_STOP.md` —
      terminating condition was overfitting guard,
      user-requested manual stop, **or**
      `early_stop_floor_unmet` (the v0.2 variant
      introduced by `DESIGN.md` §7.1.1 per-field
      methodology application layer; triggered when the
      aggregate plateaued at-or-above its target but
      one or more per-field floors on the best iteration
      are `unmet`). Regardless of best iteration's
      aggregate metric.
    - `runs/<model_identifier>/FAILED.md` — max
      iterations reached without meeting the headline
      criterion, **or** terminating condition was dev
      plateau but best iteration's aggregate dev metric
      is below the headline criterion, **or** an
      unrecoverable error.

    Each termination artifact follows a documented
    schema:
    - **Header**: which artifact type, ISO timestamp,
      task name, model identifier.
    - **Termination reason**: the specific stop condition
      that fired, with the relevant numbers (e.g., "dev
      plateau: improvement {{X}} over last 3 iterations,
      threshold {{Y}}"). For
      `early_stop_floor_unmet` (the v0.2 variant), the
      reason names the field(s) with unmet floors and the
      gap between observed and floor (e.g., "aggregate dev
      plateaued at 0.91 ≥ target 0.85, but
      `category` floor F1 ≥ 0.90 was unmet at observed
      F1 = 0.84").
    - **Best iteration**: iteration number, aggregate dev
      metric value, aggregate train metric value, train-
      vs-dev delta on aggregate, path to the prompt file
      (which is the candidate frozen prompt for
      `/spp-finalize`). Per-field metrics for the best
      iteration are recorded in `eval.json` and surfaced
      in `REPORT.md`; the termination artifact summarizes
      the aggregate.
    - **Iteration summary table**: per-iteration row with
      N, aggregate dev metric, aggregate train metric,
      number of categorical / row-specific / unclear
      verdicts (counted across all `(edit, field)`
      combinations under v0.2's per-edit-per-field
      verdict shape; under K=1 this counts identically to
      v0.1.0's per-edit shape).
    - **Override summary**: list of `auditor override`
      entries from `plan.md` §11 that were applied
      during the loop, with iteration number, reason,
      and (under v0.2) the bracketed `[edit-N.field]`
      tokens the override covered.
    - **Floor compliance** (only for SUCCESS and
      `early_stop_floor_unmet`): per-field floor and
      met/unmet/not-specified status from the best
      iteration's `floor_compliance` block.
    - **Cost**: total API calls, total iterations, wall-
      clock duration. (Cost is informational, not
      gate-relevant.)

16. **(post-loop) Print confirmation.** The final
    message names the termination artifact, the best
    iteration's prompt file, and points at the next
    step:

    > Loop terminated: {{ARTIFACT_TYPE}}.
    > Reason: {{TERMINATION_REASON}}.
    > Best iteration: run_{{NN}} (dev {{METRIC}} =
    > {{VAL}}, train-dev delta = {{DELTA}}).
    > Candidate prompt:
    >   runs/{{MODEL}}/run_{{NN}}/prompt_v{{NN}}.md.
    > Termination artifact:
    >   runs/{{MODEL}}/{{ARTIFACT_FILE}}.
    > Next step: {{NEXT_STEP}}.

    `NEXT_STEP` is `/spp-finalize` for `SUCCESS.md`;
    for `EARLY_STOP.md` and `FAILED.md`, the message
    is "the user decides — see {{ARTIFACT_FILE}} for
    the termination details and recommended next
    actions."

The command exits cleanly after step 16.

---

## 5. Gate enforcement

Two distinct gate enforcement patterns in this command.

### Gate G4 — dry-run gate

Same literal-string-match shape as G1 / G2 / G3 (per
`/spp-init` §5 and `/spp-baseline` §5). Approval phrase
recorded in `plan.md` §9. The command checks the user's
response against the recorded phrase: whitespace-stripped,
case-normalized to the recorded phrase, punctuation
matters, surrounding text is a non-match. Mismatch surfaces
a specific message naming both the recorded phrase and the
user's input. Same "revise §9" branch for users who want to
update the recorded phrase mid-flow.

The gate's job is to confirm the dry-run looks right
before iteration costs accrue. Failure modes the gate
catches: wrong model identifier, malformed prompt template,
output schema mismatch, model returning unexpected error
strings. Failure modes the gate does not catch: model that
parses correctly but produces poor predictions (those
surface as low metrics across iterations, not at the gate).

### Per-iteration auditor verdict gate

The third instance of the verdict-enforced gate pattern in
`spp` (after `/spp-baseline`'s G2 baseline-quality gate and
the now-codified shape established here). Applied per-edit,
per-iteration, to the auditor's verdicts.

Pattern in one sentence: **the auditor's per-edit verdict
adds a literal-string override-substring check on top of
the iteration's normal advancement, and the runner reverts
non-categorical edits in the absence of the override.**

Mechanics:

1. The auditor's `auditor_review.md` records one verdict
   per proposed edit (per `agents/auditor.md` §6).
2. For each `categorical` edit, the runner advances the
   edit to `prompt_v(N+1).md` (already present from step
   10 of §4); no user prompt.
3. For each `row-specific` or `unclear` edit, the runner
   searches `plan.md` §11 for a revision-log entry whose
   `Reason` field contains the literal substring
   `auditor override` (case-insensitive on the substring,
   whitespace-stripped) **and** whose timestamp is after
   the auditor's invocation timestamp. If such an entry
   exists, the edit advances. Otherwise the runner
   surfaces the auditor's reasoning and the override-
   recording instructions (§4 step 12), and:
   - If the user records the override, advance.
   - If the user replies `revert`, revert the edit in
     `prompt_v(N+1).md` and continue with that
     iteration's other edits.
   - If the user replies `revise` and provides new
     wording, the runner replaces the edit's wording in
     `prompt_v(N+1).md` and re-invokes the auditor on
     the new wording (one re-audit; further revisions
     are out of scope and surface as "revert or accept
     the override").

The gate is **invisible in the happy path** — categorical
verdicts advance silently. The gate becomes visible only
when a non-categorical verdict appears, at which point the
runner surfaces the verdict, the auditor's reasoning, and
the override-recording instructions.

**Stronger semantic content under per-stage isolation.**
With the discrepancy and rule-edit subagents now
running under per-stage isolation (§4 steps 8 and 10),
the auditor's verdicts carry stronger semantic content
than under the previous single-context architecture. A
`categorical` verdict means the edit is categorical
*and* was generated by a subagent that had no row-
content exposure during generation — a stronger
guarantee than the previous "categorical despite
possible row exposure" reading. The gate's mechanics
are unchanged; the verdicts the gate honors are
better-grounded.

Loosening this enforcement — fuzzy-matching the override
substring, allowing non-categorical edits to advance
without an override, treating `unclear` verdicts as if
they were categorical, dropping the timestamp check — is
`BREAKING CHANGE:` per §"Versioning". The gate's teeth are
what the methodology-vs-DSPy-style-optimizer distinction
hinges on.

---

## 6. Outputs

**On successful completion, the following artifacts exist
under `runs/<model_identifier>/`:**

| Path | Contents | Lifecycle |
|---|---|---|
| `_dryrun/results.json` | Dry-run output on 3 train rows. | Durable (audit). |
| `run_NN/prompt_v(N).md` for each iteration `N`. | The prompt used in iteration `N`. | Durable. |
| `run_NN/results.json` for each `N`. | Per-row predictions on train + dev. | Ephemeral by `loop_spec.md` §6 (regenerable from prompt + data); committed if user chooses. |
| `run_NN/eval.json` for each `N`. | Computed metrics (primary + auxiliary, train + dev). | Ephemeral by `loop_spec.md` §6. |
| `run_NN/discrepancy_analysis.md` for each `N`. | Failure clusters, proposed edits, optional technique recommendations (v0.5), optional adversarial rows section. | Durable. |
| `run_NN/auditor_review.md` for each `N` (in `run_(N+1)/`, written before iteration `N+1` runs). | Per-edit verdicts and reasoning. | Durable. |
| One of `SUCCESS.md` / `EARLY_STOP.md` / `FAILED.md`. | Termination metadata per §4 step 15. | Durable. |

**`plan.md` updates:**

| §11 entry | When | Reason field |
|---|---|---|
| `auditor override` entries | Whenever the user records an override at §4 step 12. | Contains literal substring `auditor override`; timestamp post-dates the auditor invocation; brief justification text. |
| `loop_spec re-validated` entries | Whenever the user opts into the `PLAN_VERSION`-mismatch resolution path at §3 pre-condition 5. | Contains literal substring `loop_spec re-validated`. |

**The command does not create:**

- `REPORT.md` or `PROMPT_FROZEN_v01.md` (those are
  `/spp-finalize`'s outputs, after gates G5 / G6).
- Modified versions of `data/baseline.csv` or
  `data/splits.json` (those are `/spp-baseline`'s outputs;
  this command treats them as read-only).
- Anything outside
  `spp/<task_name>/runs/<model_identifier>/` or
  `plan.md` revision-log entries.
- A separate `auditor_overrides.md` or
  `adversarial_rows.md` document — auditor outputs flow
  into `auditor_review.md`, adversarial outputs into
  `discrepancy_analysis.md`, overrides into `plan.md`
  §11.

**Terminal/chat output**, in order:

1. The pre-condition results (visible only on failure).
2. The dry-run summary at §4 step 5.
3. The G4 gate prompt.
4. Per iteration: a brief progress line (e.g., "iteration
   N complete: dev = {{X}}, train = {{Y}}, edits =
   {{Z}}") plus any verdict-gate consultation prompts
   for non-categorical edits.
5. The termination message at §4 step 16.

If the loop is interrupted mid-iteration, the user sees
output up to the interrupt point; the next invocation
resumes per §7's resumability discipline.

---

## 7. Failure modes and recovery

Same loud-and-specific pattern as predecessors. The table
below is the canonical reference.

| Failure | What the command does | How the user recovers |
|---|---|---|
| No approved-through-G3 plan exists | Exit with `no spp/*/config/plan.md found with G1, G2, and G3 approval entries in §11. /spp-baseline must complete G3 before /spp-loop can run.` | Run `/spp-baseline` to completion. |
| Multiple plans qualify | List them and ask the user to pick per §2. | User picks. |
| `loop_spec.md` literal-block check fails | Exit with `loop_spec.md §3 / §4 / §7 literal block has been modified: '{{LINE}}'. Restore the literal block from templates/loop_spec.md.template before /spp-loop can run. Do not parameterize the methodology guarantees.` | User restores the block; re-invokes. |
| `PLAN_VERSION` mismatch between plan.md and loop_spec.md | Surface the mismatch and the resolution choice (re-derive loop_spec or add §11 re-validated entry); halt. | User picks one. |
| Model unreachable during pre-condition 8 | Exit with `model {{MODEL}} at {{ENDPOINT}} unreachable: {{ERR}}.` | Fix endpoint / credentials; re-invoke. |
| Model unreachable mid-iteration | Exit cleanly; preserve any completed iteration's artifacts; mark current iteration's directory as partial. | Fix endpoint; re-invoke; resumability discipline applies. |
| Dry-run output schema mismatch | Surface the mismatch (per row), do not advance to G4. | User fixes the prompt template, re-runs dry-run via re-invocation (the runner detects no `_dryrun/` from this session and re-runs). |
| User mismatch on G4 phrase | Re-prompt with the same mismatch message pattern as G1 / G2 / G3. | Retype, or "revise §9". |
| Auditor returns top-level `unclear` due to malformed inputs | Surface the specific malformation; do not advance the iteration; preserve state. | User repairs the named input (typically a malformed `discrepancy_analysis.md`); re-invokes. |
| Auditor returns `row-specific` or `unclear` per-edit verdicts; user does not record override | The non-categorical edits are reverted in `prompt_v(N+1).md`; iteration continues with the categorical edits; if all edits are non-categorical and none are overridden, the prompt is unchanged. | If unchanged-prompt iterations cause dev plateau without genuine improvement, the loop terminates and the user inspects `auditor_review.md` files to decide whether to revise edits and re-invoke. |
| Adversary invocation fails (`ADVERSARY_FLAG = on` but agent file missing) | Pre-condition 2 is the **single check point** for skill-file presence; the runner does not re-check skill files on every iteration. If the adversary file is deleted mid-loop, the next adversary invocation surfaces as a generic file-read error per the "Filesystem write error" pattern below. | Restore the agent file; re-invoke; resumability discipline picks up from the last complete iteration. |
| Stop condition met but best iteration's dev metric below headline criterion in `plan.md` §3 | Write `FAILED.md` (not `SUCCESS.md`) with the specific reason. The runner does not silently mark `SUCCESS` for a loop that did not meet the criterion. | User reviews `FAILED.md`'s recommendations (e.g., revisit class definitions, expand baseline, lower headline criterion via `plan.md` §11 entry). |
| Filesystem write error during atomic checkpoint | Exit cleanly; the partial write is in `*.tmp` and is cleaned up; the prior file is untouched. | Fix the filesystem issue; re-invoke; resumability picks up. |
| User Ctrl-C mid-iteration | Iteration directory is partial (some of the five required files present, not all). On re-invocation, pre-condition 10 surfaces the partial directory and asks the user to choose. | User picks: resume from previous complete iteration (deletes partial), restart the partial iteration (re-runs steps 6–13 for that N), or abort. |
| Test row IDs accidentally appear in inference input set (defense-in-depth violation) | Exit immediately with `runner sanity check failed: test row IDs in inference input set. This indicates a /spp-loop bug; do not advance. The sacred-test-set guarantee is preserved by hard-fail.` | File a bug; do not work around. |

### Resumability

The discipline:

- **Complete iteration directory** — all five of
  `prompt_v(N).md`, `results.json`, `eval.json`,
  `discrepancy_analysis.md`, `auditor_review.md` (the
  last lives in `run_(N+1)/`, paired with this iteration
  by index) present. Resumption skips this iteration
  entirely.
- **Partial iteration directory** — some files present,
  not all. The runner does not silently re-run partial
  iterations. Pre-condition 10 surfaces the partial
  directory and prompts the user.

  > Iteration N appears partial:
  >   prompt_v(N).md: {{present|missing}}
  >   results.json: {{present|missing}}
  >   eval.json: {{present|missing}}
  >   discrepancy_analysis.md: {{present|missing}}
  >   auditor_review.md (in run_(N+1)/): {{present|missing}}
  >
  > Choose:
  >   1) Resume from iteration {{N-1}} (the last
  >      complete iteration). Delete run_{{N}}/ and
  >      restart that iteration.
  >   2) Manually repair run_{{N}}/ first, then re-invoke.
  >   3) Abort.

  No silent recovery. The user picks, and the runner
  acts on the explicit choice. Same anti-fix-it-quietly
  posture as the predecessor phases.

- **No partial iterations after iteration `MAX_ITERATIONS`**
  — the loop terminates at iteration `MAX_ITERATIONS`
  even if the auditor invocation for iteration
  `MAX_ITERATIONS` is incomplete; the termination
  artifact records this as a `FAILED.md` with reason
  "max iterations reached, final iteration audit
  incomplete".

The contract-at-both-ends pattern from `/spp-baseline`
applies: nothing is written to a termination artifact
until all required iteration files are present; nothing is
read by `/spp-finalize` until the termination artifact is
in place.

---

## 8. What `/spp-loop` does NOT do

Mirroring the predecessor phases:

- **Does not run the sacred test set.** No code path in
  this command reads from the test partition of
  `splits.json`. The runner verifies-not-touched at the
  defense-in-depth layer (see §4 step 2's forbidden-set
  posture). Test rows are first read by `/spp-finalize`
  exactly once, per `DESIGN.md` §10.
- **Does not generate `REPORT.md` or
  `PROMPT_FROZEN_v01.md`.** Those are `/spp-finalize`'s
  outputs, after gates G5 / G6.
- **Does not modify `data/baseline.csv` or
  `data/splits.json`.** Those are `/spp-baseline`'s
  outputs and are read-only here.
- **Does not modify `plan.md` outside §11 revision-log
  entries.** And §11 entries are written only when the
  user records an `auditor override` or
  `loop_spec re-validated` entry; the runner does not
  silently update §11.
- **Does not parameterize the literal blocks in
  `loop_spec.md`.** Those are honored as methodology
  guarantees; pre-condition 4 refuses to start when any
  literal block has been modified.
- **Does not invoke the designer agent.** Consultation is
  `/spp-init`'s job. This command invokes auditor (always,
  per iteration) and adversary (per iteration when
  `ADVERSARY_FLAG = on`).
- **Does not auto-promote synthetic adversarial rows** to
  `data/baseline.csv` or `data/splits.json`. Adversarial
  rows live in `discrepancy_analysis.md` under the literal
  non-persistence header line and disappear afterward.
- **Does not auto-apply technique recommendations (v0.5).**
  When the discrepancy stage matches a cluster to a
  `technique-advisor` catalog entry (§4 step 8), it records
  an advisory recommendation only. Adopting the technique
  is a user-initiated `plan.md` / OUTPUT_SCHEMA revision;
  the command never edits the prompt or plan to apply one,
  and a recommendation never carries row content or scores.
- **Does not commit produced files to git** or run any git
  operation. Same as `/spp-init` and `/spp-baseline`.
- **Does not silently advance non-categorical auditor
  verdicts.** The verdict-enforced gate has teeth per §5;
  bypassing it is `BREAKING CHANGE:`.
- **Does not pass score artifacts to the auditor or
  adversary**, even though `eval.json` and `results.json`
  exist on disk by the time those agents run. The runner's
  invocation context is constructed from a positive
  allow-list, not "everything except scores."
- **Does not retry the auditor or adversary** within an
  iteration. One invocation per iteration each. (The
  `revise`-and-re-audit branch at §5 is a user-initiated
  re-audit on revised wording, not a runner-initiated
  retry.)
- **Does not aggregate auditor verdicts across
  iterations** beyond what the auditor itself reads from
  prior `auditor_review.md` files. The runner does not
  maintain a "trust score" or any cross-iteration
  weighting.

---

## Versioning

The breaking-change list for this command is the longest
in the project, because the command operationalizes the
most contractual obligations. **When in doubt, treat the
change as breaking.** The runner is the operational
embodiment of the methodology's discipline; silent
weakening here is the failure mode the project's design
has been guarding against from the start.

### Methodology-affecting (= breaking)

- **Loosening any of the auditor's five operational
  enforcement guarantees** from `agents/auditor.md` §2.
  Specifically: any path that lets score artifacts reach
  the auditor's invocation context (a new "summary"
  parameter, a runner-side hint string, a string slice of
  `eval.json`); any path that violates the input
  allow-list (adding a file the agent doc didn't name);
  any path that introduces score-derived hints; any path
  that lets the auditor see test-set artifacts. Each is
  `BREAKING CHANGE:` per `CLAUDE.md` §8 — the rule that
  this command exists to enforce.
- **Loosening any of the adversary's four operational
  contract guarantees** from `agents/adversary.md` §6.
  Specifically: persisting synthetic rows beyond the
  iteration's `discrepancy_analysis.md`; allowing scoring
  of synthetic rows; multiple adversary invocations per
  iteration without explicit user request; promoting
  synthetic rows to `data/baseline.csv` or
  `data/splits.json`.
- **Reading the test partition during loop execution in
  any way.** The sacred-test-set guarantee is enforced
  by this command at the runner level, on top of the
  methodology-level guarantee in `loop_spec.md` §7.
  Loosening is `BREAKING CHANGE:` against
  `DESIGN.md` §10.
- **Loosening the `loop_spec.md` literal-block check** in
  pre-condition 4. The check is the runner's defense
  against silent methodology weakening; removing it
  exposes the auditor / adversary / sacred-test-set
  guarantees to hand-edits.
- **Loosening the per-iteration auditor verdict gate**:
  fuzzy-matching the `auditor override` substring;
  allowing non-categorical edits to advance without an
  override entry; treating `unclear` verdicts as
  categorical; dropping the timestamp-after-auditor
  check on override entries; advancing edits whose
  override entry post-dates a *later* auditor
  invocation rather than the relevant one.
- **Removing one of the three stop conditions** (dev
  plateau, overfitting guard, max iterations). The
  overfitting guard is particularly load-bearing per
  `DESIGN.md` §2.1 — without it, the loop happily fits
  train at the expense of dev.
- **Allowing the command to write outside
  `runs/<model_identifier>/`** or to modify `plan.md`
  outside the §11 revision-log entries.
- **Allowing the command to auto-promote synthetic
  adversarial rows** to `data/baseline.csv` or
  `data/splits.json`.
- **Changing the eight-section structure** in a way that
  propagates to subsequent phases.
- **Removing the iteration ordering guarantee** (edit →
  score → audit, with adversary slotted between
  discrepancy and audit). Reordering is breaking because
  the auditor's score-blindness depends on its
  invocation following discrepancy generation but with
  scores withheld; running the auditor before scoring
  would not buy anything (no scores to leak yet) but
  running the adversary after auditing would mean
  adversarial rows could be confused with auditor
  outputs in `discrepancy_analysis.md`.
- **Removing the runner sanity check** that test row IDs
  are not in any iteration's inference input set.
  Defense-in-depth on top of the splits-construction
  guarantee.
- **Loosening per-stage information isolation in
  iteration steps.** Specifically: any path that lets
  the discrepancy subagent (§4 step 8) receive prior
  iteration artifacts beyond its allow-list (prior
  `discrepancy_analysis.md`, prior `auditor_review.md`,
  prior `prompt_v(M).md` for `M < N`); any path that
  lets the rule-edit subagent (§4 step 10) receive
  `data/baseline.csv`, `eval.json`, `results.json`, or
  any artifact carrying row content; any path that
  lets row content reach the rule-edit subagent
  through its inputs (e.g., a `discrepancy_analysis.md`
  that includes row content excerpts rather than just
  IDs). Per-stage isolation is the load-bearing
  property the previous architecture lacked.
- **Turning the v0.5 technique consultation into a data
  path.** The discrepancy subagent reads the
  `technique-advisor` catalog as reference material only.
  Any path that lets a technique recommendation carry row
  content, predicted/ground-truth labels, or scores —
  into `discrepancy_analysis.md` or onward to the
  rule-edit or auditor stages — is `BREAKING CHANGE:`
  against `DESIGN.md` §7.1.6 and `technique-advisor`
  SKILL.md §5 (a suggestion is not a data path). Likewise
  breaking: making a recommendation row-specific rather
  than categorical, or having the stage auto-apply a
  technique instead of recording an advisory
  recommendation for the user.
- **Removing the discrepancy or rule-edit subagent
  invocations and reverting to orchestrator-direct
  work.** The previous architecture had this; the
  revision establishes the new pattern as load-bearing
  against the leakage mode the dogfooding run
  surfaced.
- **Persisting row content in `discrepancy_analysis.md`.**
  The artifact must reference rows by ID only (with
  predicted / ground-truth labels and cluster
  membership). Adding row content excerpts to the
  artifact reintroduces the leakage by making row
  content visible to the rule-edit subagent through
  its allow-listed input.
- **Removing per-edit-per-field verdict scoping (v0.2)**
  in step 11. Aggregating per-field verdicts into a
  single per-edit verdict silently weakens the gate for
  multi-field edits — an edit that is `categorical` for
  field A and `row-specific` for field B advances under
  per-edit aggregation but halts under per-field
  scoping. Per `DESIGN.md` §7.1.1 per-field methodology
  application layer.
- **Removing field attribution from
  `discrepancy_analysis.md` (v0.2)** — cluster primary-
  field tag or rule-edit `target_fields` list. The
  auditor's per-field verdict scoping consumes these;
  removing them silently regresses the gate.
- **Loosening the v0.2 override-syntax requirement that
  K > 1 schemas need bracketed `[edit-N.field]` tokens.**
  An override that grants every `(edit, field)`
  combination via an unscoped `auditor override` Reason
  for K > 1 schemas would silently widen the gate. The
  K=1 implicit-coverage exception is the only relaxation;
  removing it would break v0.1.0 backward compatibility.
- **Promoting per-field movement to a stop trigger.**
  Step 13's three stop conditions read from
  `eval.json`'s `aggregate` block. Adding a fourth that
  reads `per_field` directly would silently change the
  aggregate-plateau guarantee that bucket 2's
  metrics-layer locked.
- **Removing the `early_stop_floor_unmet` variant or
  collapsing it into FAILED.** The variant exists to
  distinguish "the loop's optimization process behaved
  correctly but a floor was missed" from "the loop did
  not converge." Collapsing into FAILED loses that
  signal.

### Behavioral (= non-breaking)

- Better wording in any prompt the command surfaces.
- Adding a new failure-mode surface for an existing
  failure case.
- Improvements to the dry-run logic that don't change
  what's verified (e.g., faster connectivity check, more
  informative dry-run output).
- Better termination-artifact schemas (more metadata
  fields, clearer prose) as long as the three artifact
  types (`SUCCESS.md` / `EARLY_STOP.md` / `FAILED.md`)
  and their meanings are preserved.
- Performance improvements (better concurrency, smarter
  batching, reduced API overhead) that don't change the
  observable behavior or the verdict-gate semantics.
- Adding a new optional pre-condition check.
- Refining the resumability prompt's wording.
- Changing the default value of `K` in the dev-plateau
  check (currently 3) as long as it remains a value
  drawable from `loop_spec.md` and stays small.
- Adding a catalog-eligible entry to the
  `technique-advisor` catalog (a new `techniques/*.yaml`
  per `technique-advisor` SKILL.md §6). Growing the
  catalog changes what the discrepancy stage may
  recommend, not how it accesses information — provided
  the entry meets the eligibility rules (categorical
  recommendation, no new allow-list input). This is the
  designed extension path and is non-breaking.

When in doubt, treat the change as breaking.

---

## Pattern observations

`/spp-loop` is the **third command** in `spp` and the
largest. It inherits:

- The eight-section structure from `/spp-init`.
- Literal-string gate enforcement (G4) from
  `/spp-init` G1.
- Verdict-enforced gate pattern, applied per-iteration
  to the auditor's per-edit verdicts, from
  `/spp-baseline` G2.
- The atomic checkpoint write discipline from both
  predecessors.
- The fail-loud-and-specific failure-mode discipline.

What is structurally new:

- **Iteration management.** The loop runs up to
  `MAX_ITERATIONS` times, with per-iteration artifacts in
  `runs/<model_identifier>/run_NN/` and an explicit
  resumability discipline.
- **Per-stage subagent isolation.** Three (four with
  adversary) isolated subagent invocations per iteration:
  discrepancy (§4 step 8), rule-edit (§4 step 10),
  auditor (§4 step 11), adversary when on (§4 step 9).
  Each has an explicit allow-list of inputs; each
  subagent's context terminates when it returns; the
  orchestrator carries state in files between stages,
  not in its main context. This generalizes the
  auditor's information-isolation pattern: the auditor
  was the *first* isolated subagent because score
  isolation is the most stringent constraint;
  per-stage isolation makes the same discipline
  structural across every cognitive stage.
- **Defense-in-depth on the sacred test set** at the
  runner level. The methodology-level guarantee lives in
  `loop_spec.md` §7; this command verifies-not-touched
  at the inference input set construction (positive
  enumeration from train + dev row IDs, never "all rows
  minus test").
- **The `loop_spec.md` literal-block check** in pre-
  conditions. New surface: the runner refuses to start
  on a loop_spec whose methodology guarantees have been
  hand-edited.

After this PR, Phase 2 has three phases. `/spp-finalize`
remains (Phase 2 step 9) — conceptually simpler than
`/spp-loop` (no iteration management; a single-pass
evaluation against the sacred test set with REPORT
generation), but the methodological capstone: it is where
the test set is read, exactly once, and the REPORT is
generated. The command set will be closed at four after
`/spp-finalize`.

Future phases should recognize `/spp-loop` as the canonical
example of a command that orchestrates multiple agents under
a strict information-isolation contract. The patterns to
inherit: **per-stage subagent isolation** (cognitive work in
fresh subagents with explicit allow-lists, never in the
orchestrator's main context); positive allow-list
construction (not deny-list); literal-block validation at
pre-conditions; defense-in-depth on the most load-bearing
methodology guarantees; per-edit verdict-enforced gates with
literal override-substring matching.

The orchestrator's job is **coordination, not cognition**:
construct subagent contexts from the allow-list, aggregate
file outputs, enforce gates between stages. Cognitive work
(cluster identification, rule editing, edit auditing) lives
in subagents whose contexts die when they return, so state
flows between stages through files (the iteration's
artifacts under `runs/<model_identifier>/run_NN/`) rather
than through the orchestrator's accumulating context. This
is the load-bearing architectural property the per-stage
isolation revision establishes.

---

## Cross-references

- [`phases/spp-init.md`](spp-init.md) — pattern source
  for the eight-section structure, literal-string gate
  enforcement (G4 inherits from G1), atomic checkpoint
  writes.
- [`phases/spp-baseline.md`](spp-baseline.md) — pattern
  source for the verdict-enforced gate (G2 baseline-quality
  enforcement; the per-iteration auditor verdict gate in
  this command is the per-iteration analog).
- [`agents/auditor.md`](../agents/auditor.md) — invoked
  per-iteration. The five operational enforcement
  guarantees from §2 are the runner's contract; §4 step
  11 of this command operationalizes them.
- [`agents/adversary.md`](../agents/adversary.md) —
  optionally invoked per-iteration (gated on
  `ADVERSARY_FLAG`). The four operational contract
  guarantees from §6 are the runner's contract; §4 step
  9 of this command operationalizes them.
- [`sub-skills/technique-advisor/SKILL.md`](../sub-skills/technique-advisor/SKILL.md)
  — consulted as reference material by the discrepancy
  subagent (§4 step 8) to match a failure cluster to a
  prompting technique and record an advisory
  recommendation. Its §5 cross-skill constraint (a
  suggestion is not a data path) is the rule the
  consultation honors; reading the catalog adds no data
  input to the stage's allow-list.
- [`templates/plan.md.template`](../templates/plan.md.template)
  — read for §2 class definitions, §3 success criterion,
  §4 metric, §6 baseline status, §9 gate phrases (G4),
  §11 revision log (write target for `auditor override`
  and `loop_spec re-validated` entries).
- [`templates/loop_spec.md.template`](../templates/loop_spec.md.template)
  — read at pre-conditions for §3 / §4 / §7 literal-
  string blocks (honored as methodology guarantees), §1
  budget, §2 stop criteria, §5 model and execution
  parameters.
- [`templates/REPORT.md.template`](../templates/REPORT.md.template)
  — forward reference. This command's outputs (per-
  iteration artifacts, termination artifact) are the
  inputs `/spp-finalize` reads to generate REPORT.
- `phases/spp-finalize.md` — **forward-looking.** Not
  yet written (Phase 2 step 9). The boundary between
  this command and `/spp-finalize` is the sacred test
  set: this command never touches it; `/spp-finalize`
  reads it exactly once.
- `DESIGN.md` §2.1 (baseline overfitting — the
  overfitting guard at §4 step 13 is the
  operationalization of this), §3 (canonical command
  list), §4.2 (auditor information isolation — this
  command is its operational embodiment), §4.3
  (adversary boundaries), §7.1 (DSPy / GEPA / APE
  non-integration — this command is the central
  illustration of why those frameworks aren't
  integrated; the auditor's per-iteration invocation
  with score-blindness is what they don't have), §10
  glossary (sacred test set, plan.md as contract, gates
  G1–G4).
- `CLAUDE.md` §4 (Semantic Commits — applies to changes
  to this command), §5 (PR rules — methodology-affecting
  PRs require `CHANGELOG.md` updates), §8 (auditor
  score-access prohibition — this command is the
  operational embodiment of that rule).
