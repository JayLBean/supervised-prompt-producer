# /spp-finalize

The fourth and final phase in `spp` and the methodology's
capstone. Runs Phase 3: reads the sacred test set exactly once,
computes test-set metrics, generates `REPORT.md`, freezes the
production prompt as `PROMPT_FROZEN_v01.md`, enforces gates G5
(finalization) and G6 (production decision), and closes the
methodology's lifecycle.

> **Note on slash-command notation.** `/spp-finalize` is a
> methodology phase identifier used internally during a
> `/spp:run` session, not a separate user-typed slash command;
> see [`spp-init.md`](spp-init.md) for the canonical statement
> of the convention.

This document inherits the eight-section structure pinned by
[`/spp-init`](spp-init.md) and inherited by
[`/spp-baseline`](spp-baseline.md) and
[`/spp-loop`](spp-loop.md). The command is **structurally
simpler than `/spp-loop`** (no iteration management, no
per-iteration agent invocations, no stop conditions —
single-pass evaluation followed by document generation) but
**comparably rigorous on the single resource that matters
here**: the sacred test set.

What is structurally new:

1. **The sacred-test-set discipline.** This is the only
   command in `spp` authorized to read the test partition,
   and the discipline of reading it exactly once is what
   makes the methodology's claim against baseline
   overfitting credible. The runner's defense against
   violation is layered: refuse to re-finalize on existing
   REPORT, refuse to advance on non-`SUCCESS.md`
   termination, delete partial test-result artifacts on
   I/O failure, deliberate friction on re-finalization
   through manual artifact deletion.
2. **The G6 structured-branch gate.** The first gate in
   `spp` with three explicit branches (approve, revise,
   halt) rather than a binary approve-or-decline shape.
   Justified by G6's role as the methodology's primary
   output: the user needs a structured way to revise the
   ship-decision recommendation before committing.
3. **Lifecycle closure.** After this command exits with a
   G6 decision (or halt-without-decision), the v1
   lifecycle is complete. The confirmation messages
   explicitly name the closure for each recommendation
   type and, for `iterate-further`, surface the
   methodology consequence of having seen test scores
   (start fresh with a new test partition, not "iterate on
   the same data").

This command is the operational embodiment of the sacred-
test-set discipline. Reviewers of PRs touching
`/spp-finalize` should read §3 (pre-conditions), §4 step 3
(the sacred read), and §7 (failure modes — particularly
the partial-deletion rule and the re-finalization
friction) as a unit.

The v1 command set is **closed at four** with this PR.
`/spp-init` (consultation), `/spp-baseline` (labeling and
splits), `/spp-loop` (optimization), `/spp-finalize`
(test-and-ship). Adding a fifth requires a methodology
change, not just a new command — see "Pattern
observations" for the structural reasoning.

---

## 1. Command identity

`/spp-finalize` is the Phase 3 entry point. It runs after
`/spp-loop` has terminated with `runs/<model_identifier>/SUCCESS.md`
(the only termination type that progresses to finalization);
reads the sacred test set exactly once across the
methodology's lifecycle; computes test-set metrics;
identifies persistent failure clusters; generates
`runs/<model_identifier>/REPORT.md` per
`templates/REPORT.md.template`; freezes the production
prompt as
`runs/<model_identifier>/PROMPT_FROZEN_v01.md`; enforces
gates G5 (finalization) and G6 (production decision); and
exits.

What the command produces, exhaustively:

- `runs/<model_identifier>/test_results.json` — per-row
  predictions on the test partition.
- `runs/<model_identifier>/test_eval.json` — test-set
  metrics (primary metric, confusion matrix, per-class
  statistics).
- `runs/<model_identifier>/REPORT.md` — the per-model
  REPORT, populated against
  `templates/REPORT.md.template`.
- `runs/<model_identifier>/PROMPT_FROZEN_v01.md` — the
  production-ready prompt, byte-identical to the
  candidate frozen prompt named in `SUCCESS.md`.
- A `plan.md` §11 revision-log entry with the literal
  substring `G6 approved`, recording the production
  decision (omitted if the user halts at G6 without
  recording a decision).

What the command does NOT produce:

- No modification to per-iteration artifacts under
  `runs/<model_identifier>/run_NN/`.
- No modification to `data/baseline.csv` or
  `data/splits.json`.
- No modification to `plan.md` outside the §11 `G6
  approved` entry.
- No git operations, no commits.
- No cross-model summary document. v1 produces
  per-model REPORTs only; cross-model synthesis is v0.4
  roadmap per `DESIGN.md` §7.1.

The judgment that drives the per-iteration audit summary
in REPORT §5 lives in the
[`auditor`](../agents/auditor.md) agent (whose verdicts
this command aggregates from prior `auditor_review.md`
files). The orchestration, sacred-test-set read, REPORT
generation, gate enforcement, and frozen-prompt freezing
live here. Same separation pattern as `/spp-loop` ↔
auditor and `/spp-baseline` ↔ baseline-quality.

---

## 2. Invocation

```
/spp-finalize
```

No arguments. Same convention as `/spp-loop`. The command
reads `spp/<task_name>/config/plan.md`,
`spp/<task_name>/config/loop_spec.md`, and the
`spp/<task_name>/runs/<model_identifier>/` artifacts to
identify what to finalize. The active task is determined by
the **most recently `SUCCESS.md`-terminated loop in the
working tree**.

**Disambiguation.** If multiple tasks have `SUCCESS.md`
artifacts on disk, or one or more candidates have
missing/unparseable timestamps, the command does not pick —
it lists all candidates and asks the user to choose:

> Multiple `spp/*/runs/*/SUCCESS.md` artifacts exist.
> Which task should `/spp-finalize` operate on?
>   1) `spp/support-billing-triage/runs/gpt-4o/`
>   2) `spp/issue-categorization-v2/runs/claude-sonnet-4/`
> Reply with the number or the task/model identifier.

The command refuses to run without a `SUCCESS.md`
termination on disk. There is no path through this command
for `EARLY_STOP.md` or `FAILED.md` terminations — those
loops did not reach a state worth finalizing, and the right
recovery is to address the termination's reason (revisit
baseline, lower headline criterion, re-run loop) rather
than to advance to finalization.

---

## 3. Pre-conditions

The command refuses to proceed unless all of the following
are true. Pre-condition failures exit with a specific
error message naming the missing piece — same loud-and-
specific pattern as the predecessors.

1. **Working directory is the user's project root.** Same
   detection as `/spp-init` §3 and `/spp-baseline` §3.

2. **The `spp` skill is installed.** The command verifies
   that `templates/plan.md.template`,
   `templates/loop_spec.md.template`, and
   `templates/REPORT.md.template` are readable.

3. **An approved-through-G4 `plan.md` exists.** At least
   one `spp/<task_name>/config/plan.md` with
   `PLAN_VERSION ≥ v1` whose §11 revision log contains
   G1, G2, G3, and G4 approval entries (in that order).
   Multiple plans ⇒ user picks per §2.

4. **`loop_spec.md` exists and validates.** Same 10
   mechanical validation rules as `/spp-loop` §3
   pre-condition 4. The load-bearing rule for this
   command:
   - Rule 6: §7 sacred-test-set posture block contains
     the literal two lines
     `test_set_access_during_loop: forbidden` /
     `test_set_first_use: /spp-finalize only`,
     unmodified.

   If the §7 block has been hand-edited, refuse with a
   specific error naming the modified line. Same defense-
   in-depth posture as `/spp-loop` — the runner refuses
   to finalize on a methodology spec whose sacred-test-
   set guarantee has been hand-edited.

5. **`data/baseline.csv` and `data/splits.json` exist**
   with the schemas defined in `/spp-baseline` §3 step 7
   and §4 step 9 respectively. The `splits.json` `test`
   array is the input to step 3 of §4 below; it must be
   readable.

6. **`runs/<model_identifier>/SUCCESS.md` exists**, or
   the special case below applies. The command reads the
   file and verifies the schema (per `/spp-loop` §4 step
   15: header, termination reason, best iteration,
   iteration summary table, override summary, cost). If
   `SUCCESS.md` is malformed, refuse with a specific error.

   If `runs/<model_identifier>/EARLY_STOP.md` or
   `runs/<model_identifier>/FAILED.md` exists instead
   (and `SUCCESS.md` does not), the handling is
   termination-reason-specific:

   - **`EARLY_STOP.md` with reason `early_stop_floor_unmet`**
     (the v0.2 termination variant added by `DESIGN.md`
     §7.1.1 per-field methodology application layer; the
     loop's aggregate plateaued at-or-above target but one
     or more per-field floors are unmet) — the command
     **does not refuse**. It surfaces the unmet floors and
     asks the user to confirm advancement:

     > Loop terminated as EARLY_STOP.md with reason
     > `early_stop_floor_unmet`. The aggregate
     > {{AGGREGATE_METRIC}} on dev plateaued at
     > {{DEV_AGG_VALUE}} (target {{TARGET}}) but the
     > following per-field floors were unmet:
     >   {{UNMET_FLOORS_LIST}}
     >
     > /spp-finalize can advance to test-set evaluation,
     > but the unmet floors will be surfaced in REPORT §7
     > as acknowledged risks. The G6 ship-decision will
     > likely be `ship-with-caveats` or `do-not-ship`.
     >
     > To proceed with the sacred test-set read despite
     > the unmet floors, reply "advance with unmet floors".
     > To halt and address the floors first (re-run
     > /spp-loop after refining plan.md §4 floor values
     > or revising labels), reply "halt".

     If the user confirms advancement, the command treats
     `EARLY_STOP.md` as the termination artifact for the
     remainder of the flow (steps 2–11) and propagates the
     unmet-floors list into REPORT §7.5 (acknowledged-risk
     overrides) at step 7. The candidate frozen prompt
     path is read from `EARLY_STOP.md`'s "best iteration"
     field (same shape as `SUCCESS.md`'s field per
     `/spp-loop` §4 step 15). If the user halts, the
     command exits cleanly and no test-set read happens.

   - **All other `EARLY_STOP.md` variants**
     (`early_stop_overfitting_guard`,
     `early_stop_manual_abandon`,
     `early_stop_user_discipline`) — refuse per existing
     v0.1.0 behavior. The command does not advance because
     these terminations indicate the loop's optimization
     process did not reach a state worth finalizing. The
     refusal message names the variant and the recovery:

     > Loop terminated as EARLY_STOP.md with reason
     > `{{REASON}}`, not SUCCESS.md.
     > /spp-finalize requires SUCCESS.md or
     > EARLY_STOP.md/early_stop_floor_unmet. Recovery:
     > Address the early-stop reason. Overfitting guard
     > → revisit baseline labels (re-run /spp-baseline
     > with revised class definitions or additional
     > rows); manual stop → user decides whether to
     > resume or restart.

   - **`FAILED.md`** (max iterations without meeting
     criterion, or unrecoverable error) — refuse per
     existing v0.1.0 behavior:

     > Loop terminated as FAILED.md, not SUCCESS.md.
     > /spp-finalize requires SUCCESS.md (the loop
     > reached the headline criterion in plan.md §3).
     > Recovery: Address the failure reason. Max
     > iterations → expand baseline, lower headline
     > criterion via plan.md §11 entry, or re-run
     > /spp-loop with revised rules. Unrecoverable error
     > → diagnose and re-run loop.

7. **The candidate frozen prompt exists.** The path is
   read from `SUCCESS.md`'s "best iteration" field
   (typically `runs/<model_identifier>/run_NN/prompt_v(N).md`
   for some `N`). The file must be readable; missing or
   unreadable is a fatal pre-condition error naming the
   path.

8. **`runs/<model_identifier>/REPORT.md` does NOT
   already exist.** Finalization is a one-shot operation;
   re-finalization implies re-reading the sacred test
   set, which violates the discipline. If `REPORT.md`
   exists, refuse with:

   > REPORT.md already exists at runs/{{MODEL}}/REPORT.md.
   > /spp-finalize is one-shot — re-finalization implies
   > re-reading the sacred test set, which violates the
   > methodology's discipline.
   >
   > To re-finalize, manually delete:
   >   runs/{{MODEL}}/REPORT.md
   >   runs/{{MODEL}}/PROMPT_FROZEN_v01.md
   >   runs/{{MODEL}}/test_results.json
   >   runs/{{MODEL}}/test_eval.json
   > and record an entry in plan.md §11 with Reason
   > naming the explicit reason for re-finalization
   > (e.g., "test data was found to be mislabeled and
   > has been corrected; sacred read is being repeated
   > with the corrected partition").
   >
   > Re-finalization is a methodology-significant event;
   > the friction is deliberate. Re-finalize only with
   > explicit reason, recorded in plan.md §11.

   The deliberate friction is what makes the
   methodology consequence visible to the user. A
   `--redo` flag, a "delete and proceed" branch, or any
   other auto-cleanup path would silently weaken the
   discipline; adding such a path is `BREAKING CHANGE:`
   per §"Versioning".

   **Resumption carve-out.** If `REPORT.md` does not
   exist but `test_eval.json` does, the user halted at
   G5 in a prior invocation. Resumption is allowed: the
   command skips test-set inference (the sacred read
   already happened) and goes directly to G5. See §7
   resumability discipline.

   Similarly, if `REPORT.md` exists but no `G6
   approved` entry has been recorded in `plan.md` §11,
   the user halted at G6 in a prior invocation.
   Resumption goes directly to G6.

9. **The model identifier in `loop_spec.md` §5 is
   reachable.** Same connectivity check as `/spp-loop`
   §3 pre-condition 8. Failure surfaces with the exact
   error so the user can fix the endpoint or
   credentials before the test-set inference begins.

10. **The task directory is writable.**
    `runs/<model_identifier>/` will be written to;
    confirm filesystem permissions allow it.

The `loop_spec.md` literal-block check at pre-condition 4,
combined with the resumption carve-outs at pre-condition 8,
gives the runner two layered defenses: the methodology
spec cannot have been weakened, and prior-invocation state
is honored without re-reading the test set.

---

## 4. Execution flow

The orchestration sequence. Steps marked **(pre-display)**
happen before user-facing output; **(consultation)**
involves user back-and-forth (gates G5 / G6); **(post-G5)**
happens after G5 has been approved; **(post-G6)** happens
after G6 has been approved (or halt has been recorded).

The flow has three structural layers:

- **Pre-G5 layer:** validation, sacred test-set read,
  metrics, persistent-failure-cluster identification
  (steps 1–5).
- **G5 layer:** the user sees test scores for the first
  time; gate enforcement (step 6).
- **Post-G5 layer:** REPORT generation, prompt freezing,
  G6, exit (steps 7–11).

### Pre-G5 layer

1. **(pre-display) Verify pre-conditions** per §3.

2. **(pre-display) Read configuration and termination
   artifact.** Load `plan.md`, `loop_spec.md`,
   `data/splits.json` (the `test` row IDs are the input
   to step 3), the termination artifact
   (`runs/<model_identifier>/SUCCESS.md`, or
   `EARLY_STOP.md` when its reason is
   `early_stop_floor_unmet` and the user has confirmed
   advancement at pre-condition 6), and per-iteration
   artifacts referenced from the termination artifact's
   iteration summary table. Identify the candidate frozen
   prompt path from the termination artifact's "best
   iteration" field.

   **`plan.md` v0.2 read pattern.** Read §2's
   `OUTPUT_SCHEMA` and per-field definitions; §3's
   aggregate-metric headline target; §4's
   `AGGREGATE_STRATEGY` + `AGGREGATE_WEIGHTS` (when
   applicable) + `AGGREGATE_RATIONALE` block, the
   per-field metric sub-blocks (one per OUTPUT_SCHEMA
   field with `METRIC_NAME[f]`, `METRIC_RATIONALE[f]`,
   `METRIC_INDEPENDENCE_NOTE[f]`), and the optional
   per-field floor sub-blocks (`FLOOR[f]`,
   `FLOOR_RATIONALE[f]` for fields that carry a floor;
   absent for fields without). Under v0.1.0 fallback
   (`plan.md` carries `LABEL_SPACE` + scalar metric
   fields), the runner auto-promotes to a one-field
   OUTPUT_SCHEMA with a one-element per-field metric
   sub-block; downstream steps read the auto-promoted
   shape — same fallback pattern `/spp-loop` step 7 uses.

   **Resumption check.** If `test_eval.json` exists from
   a prior invocation (per pre-condition 8's resumption
   carve-out), skip steps 3–5 and jump to step 6 (G5).
   The test set was read in the prior invocation; the
   sacred-read discipline forbids re-reading.

3. **(pre-display) Run inference on the sacred test set,
   exactly once.** This is the methodology's load-
   bearing read.

   **Input set construction.** The runner constructs the
   inference input set by **positive enumeration from
   `splits.json`'s `row_ids.test` array** — never as
   "all rows minus train and dev." Same allow-list
   pattern as `/spp-loop` §4 step 6 applied to the test
   partition (which `/spp-loop` deliberately excluded;
   this command deliberately includes, exactly here).

   **Inference parameters.** Read from `loop_spec.md`
   §5: `MODEL_IDENTIFIER`, `API_ENDPOINT`,
   `CONCURRENCY`, `MAX_TOKENS`, `TIMEOUT_SECONDS`,
   `RETRY_POLICY`, `TEMPERATURE`, `MODEL_DIRECTIVES`.
   These are the same parameters the loop used; the
   test-set evaluation must be apples-to-apples with
   the loop's evaluations.

   **The prompt** used for inference is the candidate
   frozen prompt at the path named in `SUCCESS.md`. The
   runner reads the prompt's bytes, computes a SHA-256
   hash for verification (recorded in REPORT §9 at step
   7), and uses it for inference unmodified.

   **Persistence.**
   `runs/<model_identifier>/test_results.json` with
   per-row predictions, written via atomic checkpoint
   (`tmp + fsync + rename`) — but with a partial-write
   discipline that differs from the loop's:

   **Partial-deletion-on-failure rule.** If the test-set
   inference fails partway (model unreachable, network
   error, partial completion), the runner **deletes any
   partial `test_results.json`** (and the `*.tmp` file
   if present) and exits cleanly with the specific
   error. The next invocation re-reads the test set
   from scratch.

   This rule is what distinguishes I/O failure
   (recoverable; no meaningful scores were generated)
   from methodology violation (not recoverable; the
   user has seen scores incrementally and gets to
   re-run for variation). Without the deletion rule, a
   partial run that produced scores for, say, 60% of
   the test set would surface those scores to a curious
   user (via cat or grep), then a retry would compute a
   different aggregate after re-rolling the partial
   rows — the user would have effectively "previewed"
   60% of the test set before committing to G5. That
   is the discipline this rule prevents.

   The distinction is enforced at the runner level:
   any non-zero exit from this step deletes the partial
   artifact before exit. Removing this rule is
   `BREAKING CHANGE:` per §"Versioning".

4. **(pre-display) Compute test-set metrics.** Read
   `test_results.json`, compute the per-field primary
   metrics specified in `plan.md` §4's per-field metric
   sub-blocks against the corresponding ground-truth
   columns for the test partition, then compute the
   aggregate per `plan.md` §4's `AGGREGATE_STRATEGY` block
   (`macro` / `weighted` / `min` per `metric-design`
   SKILL.md §3.2). Persist
   `runs/<model_identifier>/test_eval.json` with the v0.2
   shape (per `DESIGN.md` §7.1.1 metrics layer decision 5):
   - **`per_field`** — keyed by field name; each field
     carries its primary metric value (test) plus
     auxiliary structures appropriate to the field's
     metric (confusion matrix for enum-F1, IoU
     distribution for span-IoU, residual distribution for
     number-MAE, etc.).
   - **`aggregate`** — the aggregate metric value (test),
     the strategy used, and weights when `weighted`.
   - **`floor_compliance`** — keyed by field name; each
     field carries its floor (from `plan.md` §4's per-field
     floor sub-blocks; `null` if unspecified) and a
     `met` / `unmet` / `not_specified` status.
   - **`per_row`** — the retained per-row test score vector
     (`row_id`, `y_true`, `y_pred`, `correct`), computed
     from this single sacred read and held for the v0.3
     finalize statistics (`DESIGN.md` §7.1.4). The
     baseline-on-test evaluation carries its own `per_row`
     in the same shape, so the headline delta has paired
     per-row scores. Bootstrap and permutation (later v0.3
     buckets) resample this in-memory vector; they do not
     re-read the test partition, so the read-exactly-once
     guarantee is intact.

   Under K=1 backward compat the per_field section has one
   entry, aggregate equals that entry's primary metric, and
   floor_compliance has at most one row — equivalent to
   v0.1.0's `test_eval.json` shape (single primary metric
   plus confusion matrix). Legacy plans persisting v0.1.0's
   scalar metric fields auto-promote at read time.

   Atomic checkpoint write.

   This is the **single test-set evaluation** for the
   methodology's lifecycle. There is no "preview" step, no
   "intermediate" test scores, no ranged-prediction
   surface. The user sees the computed metrics for the
   first time at G5 (step 6).

5. **(pre-display) Identify persistent failure modes.**
   Identify rows in the test partition where the
   candidate frozen prompt's prediction disagreed with
   ground truth on **any** OUTPUT_SCHEMA field. Cluster
   the failures by shared property (using the same
   clustering approach as `/spp-loop` §4 step 8's
   discrepancy analysis); each cluster names a **primary
   field** — the OUTPUT_SCHEMA field whose disagreements
   the cluster's shared property explains (`DESIGN.md`
   §7.1.1 per-field methodology application layer). Rows
   that disagree on multiple fields appear in multiple
   clusters (once per field-disagreement). Under K=1 the
   primary field is the lone field; under v0.1.0 fallback
   it is the auto-promoted `label` field. Document the
   failure clusters as: cluster name, primary field, rows
   in the cluster (by row ID), shared property of the
   cluster, brief commentary on whether the cluster is a
   known limitation (per `BASELINE_QUALITY_NOTE` in
   `plan.md` §6) or a previously-unseen pattern.

   The runner does **not** propose rule edits at this
   stage. Finalization is not iterative; the failure
   clusters are recorded as known limitations in REPORT
   §4, not as problems to fix. Proposing edits here
   would imply a path back to `/spp-loop`, which would
   require re-reading the test set on a subsequent
   `/spp-finalize` — methodology violation.

### G5 layer

6. **(consultation) Present at gate G5.** The user sees
   the test scores for the first time:

   > Test-set evaluation complete (sacred read, one-shot).
   >   Test {{METRIC}}: {{VALUE}}
   >   Train {{METRIC}} (final iteration): {{TRAIN_VALUE}}
   >   Dev {{METRIC}} (best iteration): {{DEV_VALUE}}
   >   Train-test delta: {{TRAIN_TEST_DELTA}}
   >   Dev-test delta: {{DEV_TEST_DELTA}}
   >   Persistent failure clusters: {{N_CLUSTERS}} (see below)
   >
   > [Per-cluster summary: cluster name, row count,
   >  shared property, known/unknown limitation]
   >
   > Headline criterion in plan.md §3:
   >   {{HEADLINE_CRITERION}}.
   > Test-set result vs criterion: {{MET / NOT_MET}}.
   >
   > To approve test-set evaluation and proceed to
   > REPORT generation, reply with the exact G5
   > approval phrase you recorded in §9 of plan.md:
   > `{{G5_APPROVAL_PHRASE}}`. To halt without
   > generating REPORT, reply "halt".

   Same literal-string-equality match as G1 / G2 / G3 /
   G4. Whitespace-stripped, case-normalized to the
   recorded phrase, punctuation matters, surrounding
   text is a non-match. Mismatch surfaces a specific
   message naming both the recorded phrase and the
   user's input.

   **The G5 prompt is informational, not negotiable.**
   The user can approve and proceed to REPORT, or they
   can halt (which preserves `test_eval.json` and
   `test_results.json` but does not write REPORT). What
   the user *cannot* do is re-run the test-set
   inference — the sacred-test-set discipline means
   "you saw the scores; that's the read."

   **Halt branch.** If the user halts at G5, the
   command exits cleanly. The next invocation honors
   pre-condition 8's resumption carve-out: skips steps
   3–5, jumps directly back to G5. The user's options
   on resumption are the same: approve to proceed or
   halt again.

   To re-run the test set after halting at G5, the
   user must manually delete `test_results.json` and
   `test_eval.json` (per pre-condition 8's
   re-finalization friction). The runner does not
   offer this as a path through G5.

### Post-G5 layer

7. **(post-G5) Generate REPORT.md.** Populate
   `runs/<model_identifier>/REPORT.md` per
   `templates/REPORT.md.template`. Each section:

   - **§1 run metadata**: task name, model identifier,
     `PLAN_VERSION` (from `plan.md`),
     `loop_spec.md`'s referenced `PLAN_VERSION`, run
     timestamps (loop start from earliest
     `runs/<model>/run_01/` mtime, loop end from
     `SUCCESS.md` timestamp, finalize start from this
     invocation's start, finalize end at this step).

     **Note on mtime fragility.** Loop start/end
     timestamps are derived from filesystem mtimes,
     which may be reset by file operations like `git
     checkout` or `cp` without `-p`. If the timestamps
     appear incorrect in the rendered REPORT, the user
     manually corrects them in REPORT §1; the
     timestamps are informational, not gate-relevant.
     v0.2 may add a `generated_at` field to per-
     iteration `eval.json` files for authoritative
     timestamps independent of filesystem mtime; this
     is forward work and is non-breaking when it
     lands (the mtime fallback remains for
     pre-v0.2 runs).
   - **§2 final scores**: populated from `test_eval.json`'s
     v0.2 sections (`per_field`, `aggregate`,
     `floor_compliance`) plus the corresponding sections
     of the best-iteration `runs/<model>/run_NN/eval.json`
     for dev/train. Per `templates/REPORT.md.template`
     §2.1, §2.2, §2.3 (bucket 3): per-field scores (one
     subsection per OUTPUT_SCHEMA field with the field's
     primary metric for test/dev/train and auxiliary
     structures appropriate to the metric type — confusion
     matrix for enum-F1, IoU distribution for span-IoU,
     residual distribution for number-MAE, per-class
     statistics where applicable); aggregate scores (the
     aggregate metric for test/dev/train, the strategy
     used, weights when `weighted`); floor compliance (per
     OUTPUT_SCHEMA field with floor value and
     met/unmet/not_specified status). Train-dev-test
     deltas at the aggregate level are explicitly named.
     Under K=1 the per-field block has one subsection,
     aggregate equals that field's metric, floor
     compliance has at most one row — equivalent to
     v0.1.0's flat scores shape.
   - **§3 loop trajectory**: per-field trajectories (one
     trajectory table per OUTPUT_SCHEMA field) plus the
     aggregate trajectory, populated from per-iteration
     `eval.json` files' `per_field` and `aggregate`
     sections (per `templates/REPORT.md.template` §3.1,
     §3.2; bucket 3). The aggregate trajectory is what the
     /spp-loop dev-plateau and overfitting-guard checks
     ran against; per-field trajectories are informational
     (per-field movement does not gate the stop discipline
     per `DESIGN.md` §7.1.1 metrics layer decision 4). Under
     K=1 the per-field trajectory equals the aggregate
     trajectory; the §3 content collapses to v0.1.0's
     single iteration-by-iteration table. The iteration
     summary table from the termination artifact
     (`SUCCESS.md` or `EARLY_STOP.md`) appears verbatim
     after the trajectories.
   - **§4 persistent failure modes**: the failure clusters
     from step 5, with primary-field tags, row IDs (no row
     content duplicated, per the diff-friendly discipline
     from `splits.json`), shared properties, and brief
     commentary on whether each cluster was anticipated in
     `BASELINE_QUALITY_NOTE` (`plan.md` §6). Rows that
     disagree on multiple fields appear in multiple
     clusters per bucket-3's per-field methodology
     application layer.
   - **§5 prompt-edit audit**: aggregated from per-
     iteration `auditor_review.md` files. Counts of
     `categorical` / `row-specific` / `unclear`
     verdicts. List of `auditor override` entries from
     `plan.md` §11 with iteration number, reason text,
     and timestamp. **The literal line "Auditor
     information-isolation invariant: preserved." is
     required** — this is the methodology's traceable
     assertion that the design lock was honored across
     the loop's lifecycle. The runner emits the line
     unconditionally; absence would itself be a
     methodology breakage signal. Per
     `templates/REPORT.md.template` §5 validation, the
     Phase 4 linter checks for this exact line.
   - **§6 decision and recommendation**: one of
     `ship` / `ship-with-caveats` / `do-not-ship` /
     `iterate-further`. Computed by the runner via the
     simple decision tree below; the user revises at
     G6 if they disagree.

     **Decision tree (deterministic, auditable; v0.2
     generalized).** "Test-aggregate" is the test-set
     value of `eval.json`'s `aggregate` field (the
     aggregate metric per the strategy in `plan.md` §4);
     "headline criterion" is the `AGGREGATE_METRIC_TARGET`
     in `plan.md` §3; per-field floor compliance is the
     `floor_compliance` block in `test_eval.json` (per-field
     `met` / `unmet` / `not_specified` status). Under K=1
     the aggregate equals the lone field's metric and the
     floor block has at most one row — the tree collapses
     to v0.1.0's behavior.

     - If test-aggregate ≥ headline criterion AND every
       per-field floor's status is `met` or
       `not_specified` AND no persistent failure
       clusters AND `train_test_delta` ≤
       `dev_test_delta` × 1.5: **`ship`**.
     - If test-aggregate ≥ headline criterion AND every
       per-field floor's status is `met` or
       `not_specified` AND persistent failure clusters
       exist but were anticipated in
       `BASELINE_QUALITY_NOTE`: **`ship-with-caveats`**
       (the caveats are the anticipated clusters).
     - If test-aggregate ≥ headline criterion AND
       (persistent failure clusters exist that were
       *not* anticipated OR
       `train_test_delta > dev_test_delta × 1.5` OR any
       per-field floor's status is `unmet`):
       **`ship-with-caveats`** (the caveats include
       the unanticipated clusters and/or the overfit
       signal and/or the unmet floors named per field).
     - If test-aggregate < headline criterion AND
       `dev_test_delta ≤ 0.05` (the dev set was a fair
       estimator and the criterion was simply not met):
       **`do-not-ship`**. If the entry path was
       `EARLY_STOP.md/early_stop_floor_unmet`, the
       unmet floors corroborate `do-not-ship`.
     - If test-aggregate < headline criterion AND
       `dev_test_delta > 0.05` (the dev set was
       meaningfully diverged from test, suggesting
       non-representative dev): **`iterate-further`** —
       but with the start-fresh recommendation surfaced
       at G6 (see step 9).

     The `0.05` threshold is a v1 default chosen as a
     reasonable "small vs. meaningful" cutoff for
     classification metrics; v0.2 may tune it based on
     observed task variation, or surface it as a
     `loop_spec.md` parameter. Non-breaking if the
     default is preserved on tuning. Users who
     disagree with the threshold for their specific
     task revise the recommendation at G6.

     The tree is **deterministic and auditable**; the
     same inputs always produce the same recommendation.
     The user revises via G6's structured-branch gate
     if they disagree with the runner's reading. An
     LLM-judgment-based recommendation was considered
     and rejected for v1 — predictability and
     auditability beat nuance for the ship decision.
     See PR description for the trade-off discussion.
   - **§7 limitations** (per `templates/REPORT.md.template`
     §7.1–§7.6; the section structure is the bucket-3 v0.2
     shape):
     - **§7.1 Model lock-in caveat**: the prompt was
       optimized against `MODEL_IDENTIFIER` from
       `loop_spec.md` §5. Cross-model fragility per
       `DESIGN.md` §2.2. If the user redeploys against a
       different model, expected metric movement is not
       characterized by this REPORT.
     - **§7.2 Baseline scope and provenance**: size,
       source, `BASELINE_QUALITY_NOTE` from `plan.md` §6.
       Under v0.2 the baseline-quality note records
       per-field findings consolidated into the single
       verdict; under K=1 the per-field summary collapses
       to v0.1.0's flat shape.
     - **§7.3 Persistent failure clusters**: forward
       reference to §4 (now carrying primary-field tags
       per bucket 3).
     - **§7.4 Loop interruption posture**: v1 does not
       support mid-iteration resumption per `DESIGN.md`
       §7.1; if the loop terminated cleanly via
       `SUCCESS.md`, this caveat is informational only.
     - **§7.5 Acknowledged-risk overrides**: enumerate
       overrides recorded in `plan.md` §11 with literal
       substrings `schema-not-ready override`,
       `not-ready override`, or `auditor override` (per
       `schema-designer` SKILL.md §6, `baseline-quality`
       SKILL.md §6, and `auditor.md` §6). When the
       termination artifact was
       `EARLY_STOP.md/early_stop_floor_unmet` (the
       advancement path confirmed at pre-condition 6),
       the unmet-floors list also lands here — each
       unmet floor named per field with its target value
       and the test-set actual.
     - **§7.6 Other caveats**: any task-specific
       limitations the user surfaced during consultation
       (`plan.md` §10 `KNOWN_LIMITATIONS` if populated).
   - **§8 cost at scale**: per-row API cost computed
     from `SUCCESS.md`'s cost field plus this command's
     test-set inference cost. Projections at 1K / 10K
     / 100K rows. Informational only; not gate-
     relevant.
   - **§9 production prompt artifact**: SHA-256 hash of
     the candidate frozen prompt (computed in step 3
     and recorded here), file path
     (`runs/<model_identifier>/PROMPT_FROZEN_v01.md`,
     after step 8), hash verification command
     (`shasum -a 256
     runs/<model_identifier>/PROMPT_FROZEN_v01.md`).
   - **§10 reproducibility checklist**: commit hash at
     loop start (read from git via `git rev-parse HEAD`
     against the loop's first iteration timestamp; if
     git is unavailable or the working tree is dirty,
     surface a placeholder with manual-recording
     instructions), commit hash at finalize (this
     invocation), the
     `runs/<model_identifier>/_dryrun/` artifact path
     (which is regenerable from the prompt), the
     `splits.json` `seed` field, the `LABEL_SPACE`
     from `plan.md` §2.

   The REPORT is written via atomic checkpoint write.
   On any error during generation, the partial REPORT
   is deleted (same partial-deletion discipline as
   step 3, applied to a different artifact for the
   same reason — incomplete REPORTs surface scores
   without the surrounding context that makes them
   meaningful).

8. **(post-G5) Freeze the production prompt.** Copy the
   candidate frozen prompt from
   `runs/<model_identifier>/run_NN/prompt_v(N).md` to
   `runs/<model_identifier>/PROMPT_FROZEN_v01.md`,
   byte-identical. Atomic checkpoint write. The freeze
   is one-way: once written,
   `PROMPT_FROZEN_v01.md` is the production artifact;
   the runner does not modify it.

   The SHA-256 hash recorded in REPORT §9 is computed
   on the source prompt's bytes (step 3) and verified
   against the frozen prompt's bytes here. Mismatch is
   a fatal error (indicates a filesystem corruption or
   a race between read and copy); the runner deletes
   `PROMPT_FROZEN_v01.md` and exits with the specific
   error. Resumption re-runs steps 7–8 (REPORT and
   freeze) without re-reading the test set.

### G6 layer

9. **(consultation) Present at gate G6.** The user
   reviews the REPORT and decides ship / no-ship:

   > REPORT.md generated at runs/{{MODEL}}/REPORT.md.
   > Frozen prompt at
   > runs/{{MODEL}}/PROMPT_FROZEN_v01.md
   > (SHA-256: {{HASH}}).
   >
   > Draft recommendation: {{RECOMMENDATION}}.
   > Reasoning: {{RATIONALE_SUMMARY}}.
   >
   > Review the full REPORT before deciding. To approve
   > the recommendation as drafted, reply with the exact
   > G6 approval phrase you recorded in §9 of plan.md:
   > `{{G6_APPROVAL_PHRASE}}`.
   >
   > To revise the recommendation, reply
   >   "revise recommendation to
   >    {ship | ship-with-caveats | do-not-ship | iterate-further}"
   > with a one-paragraph justification. The runner
   > updates REPORT §6 and re-prompts for G6.
   >
   > To halt without recording a production decision,
   > reply "halt". REPORT and frozen prompt are
   > preserved; no G6 entry is written to plan.md §11.

   The G6 gate's three branches:

   - **Approve as drafted.** The user types the G6
     approval phrase exactly. The runner records the
     recommendation in `plan.md` §11 with a literal
     `G6 approved` substring entry, including the
     recommendation type (`ship` / `ship-with-caveats`
     / `do-not-ship` / `iterate-further`) and a
     timestamp. Proceeds to step 10.
   - **Revise recommendation.** The user provides a
     revision in the documented format (`revise
     recommendation to {VALUE}` plus a justification
     paragraph). The runner updates REPORT §6 in place
     (replacing the recommendation type and prepending
     the user's justification to the rationale), then
     re-prompts for G6 on the revised recommendation.
     There is **no limit on revisions**; the user
     iterates until they approve a recommendation
     they're willing to commit to.
   - **Halt.** The user types `halt` (or any
     unrecognized response that is not the approval
     phrase and not a recognized revision command).
     The runner exits cleanly without writing a §11
     entry. REPORT and frozen prompt are preserved.
     Re-invocation honors pre-condition 8's resumption
     carve-out: skips test-set inference and REPORT
     generation, jumps directly to G6 again.

   The structured-branch gate is a **justified
   departure** from G1-G5's binary approve-or-decline
   pattern. The recommendation is the methodology's
   primary output; the user needs a structured way to
   revise the runner's draft before committing.
   Without structured revision, the user's only option
   on disagreement is to halt and never finalize, or
   to manually edit REPORT and re-invoke (which adds
   friction without a corresponding methodology
   benefit).

10. **(post-G6, ship/ship-with-caveats branch) Print
    confirmation.**

    > Production decision recorded at G6:
    > {{RECOMMENDATION}}.
    > Frozen prompt:
    >   runs/{{MODEL}}/PROMPT_FROZEN_v01.md.
    > REPORT:
    >   runs/{{MODEL}}/REPORT.md.
    > spp lifecycle complete. Deploy the frozen prompt
    > against {{MODEL_IDENTIFIER}} per the
    > recommendation in REPORT §6.

    For `do-not-ship`:

    > Production decision recorded at G6: do-not-ship.
    > REPORT: runs/{{MODEL}}/REPORT.md (records the
    > reasoning).
    > Frozen prompt: runs/{{MODEL}}/PROMPT_FROZEN_v01.md
    > (preserved for audit but not for deployment).
    > spp lifecycle complete. The methodology has
    > produced a documented do-not-ship outcome — see
    > REPORT §6 for reasoning and §7 for limitations.

    For `iterate-further` — the most pedagogically
    important confirmation, naming the methodology
    consequence of having seen test scores:

    > Production decision recorded at G6:
    > iterate-further.
    > REPORT: runs/{{MODEL}}/REPORT.md.
    > Frozen prompt: runs/{{MODEL}}/PROMPT_FROZEN_v01.md.
    > spp lifecycle paused.
    >
    > To proceed with further iteration, revisit the
    > baseline (per the recommendation in REPORT §6),
    > then start a NEW spp lifecycle.
    >
    > Note: the test set has been read. Further
    > iteration on the same baseline + splits would be
    > optimizing against the test scores you have now
    > seen. The methodology recommends starting fresh:
    > re-run /spp-init with revised plan, /spp-baseline
    > with revised baseline or splits (new test
    > partition; new seed in plan.md §7), /spp-loop,
    > /spp-finalize.
    >
    > Continuing to iterate against this same test
    > partition would silently invalidate the
    > methodology's claim against baseline overfitting.
    > The fresh-start recommendation is not optional
    > advice — it is what the discipline requires.

11. **(post-G6) Exit cleanly.** No further action.

### K=1 backward compatibility

Legacy v0.1.0 plans persisting `LABEL_SPACE` + scalar
metric fields continue to work end-to-end without
modification. The runner's K=1 fallback auto-promotes the
plan's scalar fields to the v0.2 K=1 shape at read time
(the same fallback `/spp-loop` step 7 and `/spp-baseline`
step 7 use; the runner-side fallback is implemented once
across the four phase docs). Every step degenerates
cleanly:

- Step 2: read pattern picks up the auto-promoted one-field
  OUTPUT_SCHEMA + one-element per-field metric block;
  the AGGREGATE_STRATEGY is `macro` by default (any
  strategy is the identity on K=1); floors absent unless
  the user upgraded the plan.
- Step 4: per-field metric computation runs once on the
  lone field; aggregate equals that field's metric;
  floor compliance has at most one row.
  `test_eval.json`'s `per_field` block has one entry, the
  `aggregate` block carries the strategy, the
  `floor_compliance` block is empty or one row.
- Step 5: failure clusters all tag the same primary field
  (the auto-promoted `label` field), reproducing v0.1.0's
  flat clustering shape.
- Step 7: REPORT generation populates §2's per-field block
  with one subsection equal to v0.1.0's §2 content; the
  aggregate trajectory equals the per-field trajectory in
  §3; the floor-compliance block in §2.3 is empty or one
  row; §7.5 acknowledged-risk overrides surfaces only
  when the user recorded an override or the entry path
  was `EARLY_STOP.md/early_stop_floor_unmet`.
- The `EARLY_STOP.md/early_stop_floor_unmet` advancement
  branch is reachable for K=1 plans only when the user
  has actually configured a floor on the lone field (the
  default K=1 plan has no floor, so the bracket only fires
  for users who have actively set one).

The K=1 path is therefore both forward-compatible (v0.2
plans with K=1 shape) and backward-compatible (v0.1.0
legacy plans). Migration of an existing v0.1.0 plan to
the v0.2 template surface is documented in `DESIGN.md`
§7.1.1 compat layer (Manual upgrade steps); the migration
is opt-in.

---

## 5. Gate enforcement

Two gates, G5 and G6, both following the literal-string-
match pattern from G1-G4 with G6 adding structured-branch
revision support.

### Gate G5 — finalization gate

Same shape as G1 / G2 / G3 / G4. Approval phrase recorded
in `plan.md` §9; the command checks for it literally
(whitespace-stripped, case-normalized, punctuation
matters, surrounding text is a non-match). Mismatch
surfaces a specific message naming both the recorded
phrase and the user's input.

The "halt" branch (user does not approve, exits before
REPORT) is supported via the literal `halt` reply or any
response that is neither the approval phrase nor `halt`
(treated as decline). The runner does not require a
specific decline phrase. Halt preserves
`test_eval.json` and `test_results.json`; resumption
honors pre-condition 8.

The gate's job: confirm the user has seen the test
scores and accepts proceeding to REPORT. Failure modes
the gate catches: the user wanting to halt before
producing a REPORT they're not willing to ship from.
Failure modes the gate does *not* catch: the user
wanting to retry the test inference (this is forbidden
by the sacred-test-set discipline; the runner does not
offer this branch).

### Gate G6 — production decision gate

Three branches:

1. **Approve as drafted.** User types the G6 approval
   phrase exactly. Runner records `G6 approved`
   substring in `plan.md` §11 with timestamp,
   recommendation type, and brief rationale.
2. **Revise recommendation.** User types
   `revise recommendation to {ship |
   ship-with-caveats | do-not-ship | iterate-further}`
   followed by a justification paragraph. Runner
   updates REPORT §6's recommendation type (validating
   that the proposed value is one of the four allowed)
   and prepends the user's justification to the
   rationale. Re-prompts for G6.
3. **Halt.** User types `halt` (or any unrecognized
   response). Runner exits cleanly without a §11
   entry. REPORT and frozen prompt preserved.

The revision branch's literal-string match is on the
prefix `revise recommendation to ` (whitespace-stripped,
case-insensitive); the suffix is one of the four allowed
recommendation values, validated literally. Any other
shape (e.g., a free-form recommendation outside the four
allowed values) surfaces an error and re-prompts for G6
without modifying REPORT.

Loosening any of these — fuzzy-matching the approval
phrase, accepting a fifth recommendation value beyond
the four named, advancing on a timeout, allowing
recommendation values to be free-form text — is
`BREAKING CHANGE:` per §"Versioning". The four
recommendation values are the methodology's enumeration
of ship-decision outcomes; expanding the enumeration
silently changes what the methodology produces.

---

## 6. Outputs

**On successful completion (G6 approved):**

| Path | Contents | Lifecycle |
|---|---|---|
| `runs/<model_identifier>/test_results.json` | Per-row test predictions. | Durable. |
| `runs/<model_identifier>/test_eval.json` | Test-set metrics. | Durable. |
| `runs/<model_identifier>/REPORT.md` | Per-model REPORT per `templates/REPORT.md.template`. | Durable; the methodology's primary output. |
| `runs/<model_identifier>/PROMPT_FROZEN_v01.md` | Production-ready prompt (byte-identical to candidate). | Durable; the methodology's deployment artifact. |

**`plan.md` updates:**

| §11 entry | When | Reason field |
|---|---|---|
| `G6 approved` entries | Whenever the user approves at G6. | Contains literal substring `G6 approved`; recommendation type (`ship` / `ship-with-caveats` / `do-not-ship` / `iterate-further`); timestamp; brief rationale paragraph. |

**The command does not create:**

- A separate `cross_model_summary.md` document. v1
  produces per-model REPORTs only.
- Modified versions of per-iteration artifacts under
  `runs/<model_identifier>/run_NN/`.
- Modified versions of `data/baseline.csv` or
  `data/splits.json`.
- Anything outside `spp/<task_name>/runs/<model_identifier>/`
  or the `plan.md` §11 entry.

**Terminal/chat output**, in order:

1. The pre-condition results (visible only on failure).
2. A brief progress line during test-set inference
   ("Running inference on N test rows…") — this surface
   does not include per-row predictions or partial
   metrics; the user's first view of any score is at G5.
3. The G5 gate prompt (with test scores).
4. (If G5 approved) the REPORT-generation progress
   (one line per section as it is written).
5. The G6 gate prompt (with the draft recommendation).
6. (If G6 approved or halted) the confirmation message
   at step 10 or 11.

If the command exits before G5 (test-set inference
failure with partial-deletion), the user sees the
specific I/O error and the recovery instruction. If the
command exits at G5 halt, the user sees only the G5
prompt and the implicit halt confirmation. If the command
exits at G6 halt, the user sees the G6 prompt and the
implicit halt confirmation; REPORT exists on disk for
review.

---

## 7. Failure modes and recovery

Loud-and-specific. The table below is the canonical
reference.

| Failure | What the command does | How the user recovers |
|---|---|---|
| No approved-through-G4 plan exists | Exit with `no spp/*/config/plan.md found with G1, G2, G3, and G4 approval entries in §11. /spp-loop must complete G4 before /spp-finalize can run.` | Run `/spp-loop` to completion. |
| Multiple `SUCCESS.md` artifacts qualify | List them and ask the user to pick per §2. | User picks. |
| `loop_spec.md` §7 literal block has been modified | Exit with `loop_spec.md §7 sacred-test-set posture block has been modified: '{{LINE}}'. Restore the literal block from templates/loop_spec.md.template before /spp-finalize can run. The block is the methodology's sacred-test-set guarantee; do not parameterize it.` | User restores the block; re-invokes. |
| `SUCCESS.md` does not exist (loop terminated `EARLY_STOP.md` or `FAILED.md`) | Refuse with termination-type-specific recovery guidance per §3 pre-condition 6. | User addresses the termination's reason and re-runs the loop, or the user accepts the termination as the methodology's outcome. |
| `SUCCESS.md` is malformed | Exit with `runs/{{MODEL}}/SUCCESS.md schema invalid: {{REASON}}. The /spp-loop output may have been hand-edited or corrupted. Restore from git or re-run /spp-loop.` | User restores or re-runs. |
| Candidate frozen prompt missing | Exit with `candidate prompt at {{PATH}} (per SUCCESS.md best-iteration field) is unreadable: {{ERR}}.` | User restores the file (typically from git) or re-runs `/spp-loop`. |
| `REPORT.md` already exists; no resumption carve-out applies | Refuse re-finalization with the friction message at §3 pre-condition 8. | User manually deletes the four named artifacts and records a §11 entry naming the re-finalization reason. |
| Resumption carve-out: `test_eval.json` exists but no `REPORT.md` | Skip steps 3–5; jump to G5. | (Not a failure — resumption.) |
| Resumption carve-out: `REPORT.md` exists but no `G6 approved` §11 entry | Skip steps 3–8; jump to G6. | (Not a failure — resumption.) |
| Test-set inference fails partway | Delete partial `test_results.json` (and `*.tmp`), exit cleanly with the specific error: `test-set inference failed at row {{N}} of {{TOTAL}}: {{ERR}}. Partial test_results.json deleted; re-invocation re-reads the test set from scratch.` | Fix the I/O issue; re-invoke; the test set is re-read from scratch. The discipline distinguishes I/O failure (partial-delete + retry) from methodology violation (the user has seen scores). |
| Test-set inference completes; user halts at G5 | Preserve `test_eval.json` and `test_results.json`; do not write REPORT. | Re-invoke; resumption goes directly to G5. To re-run the test set, manually delete `test_results.json` and `test_eval.json` and record a §11 entry per the re-finalization friction. |
| REPORT generation fails partway | Delete partial REPORT.md, exit cleanly with the specific error. | Re-invoke; resumption regenerates REPORT from `test_eval.json` (no test-set re-read) and proceeds to G5 → G7. |
| Frozen-prompt SHA-256 mismatch between source and copy | Delete `PROMPT_FROZEN_v01.md`, exit with `frozen-prompt hash mismatch: source {{HASH1}} ≠ copy {{HASH2}}. This indicates filesystem corruption or a race; do not advance.` | File a bug; investigate filesystem; re-invoke after fix. Resumption re-copies. |
| User halts at G6 | Preserve REPORT and frozen prompt; no §11 entry. | Re-invoke; resumption goes directly to G6. The user can also iterate on the REPORT manually before re-invocation, but only by editing REPORT §6 in-place (the runner accepts an edited REPORT on resumption). |
| User mismatch on G5 phrase | Re-prompt with the same mismatch message pattern as G1-G4. | Retype, or "halt". |
| User mismatch on G6 phrase (and not a recognized revision command) | Re-prompt with G6 prompt, indicating the response was not recognized as approval, revision, or halt. | Retype the approval phrase, type a revision command in the documented format, or type `halt`. |
| Filesystem write error during atomic checkpoint | Exit cleanly; the partial write is in `*.tmp` and is cleaned up; the prior file (if any) is untouched. | Fix the filesystem issue; re-invoke; resumability picks up. |

### Resumability discipline

`/spp-finalize` is **resumable but does not re-read the
test set**. Three resumption surfaces, each tied to a
specific stage:

- **Test-set inference completed; user halted at G5**:
  re-invocation reads `test_eval.json` (the prior
  sacred read), skips steps 3–5, jumps to G5. Same
  scores, same persistent failure clusters. The user
  approves and proceeds, or halts again.
- **REPORT generated; user halted at G6**:
  re-invocation reads REPORT.md, skips steps 3–8,
  jumps to G6. The runner re-derives the draft
  recommendation (deterministic; same inputs ⇒ same
  recommendation), allowing the user to compare with
  any in-place edits they made between invocations.
- **Test-set inference failed mid-run**: the partial
  `test_results.json` was deleted on failure;
  re-invocation runs steps 3–5 from scratch. The
  partial-deletion rule is what makes this a clean
  resumption rather than a methodology violation.

The runner does **not** re-read the test set on any
of the first two surfaces. The sacred-test-set
discipline is enforced at the command level: one read
per `/spp-finalize` lifecycle, regardless of how many
times the command is invoked within that lifecycle. To
start a new lifecycle (and a new sacred read), the user
deletes the four artifacts named in pre-condition 8's
re-finalization friction and records the reason.

---

## 8. What `/spp-finalize` does NOT do

Mirroring the predecessor phases:

- **Does not run iterations or invoke the auditor or
  adversary agents.** Iteration management is
  `/spp-loop`'s job; finalization reads the artifacts
  the loop produced.
- **Does not modify per-iteration artifacts** under
  `runs/<model_identifier>/run_NN/`. The runner reads
  `prompt_v(N).md`, `eval.json`, `discrepancy_analysis.md`,
  and `auditor_review.md` files; it does not write to
  any of them.
- **Does not modify `data/baseline.csv` or
  `data/splits.json`.** Those are `/spp-baseline`'s
  outputs and are read-only here. In particular, the
  `splits.json` `test` array is the single source of
  truth for the test partition; the runner does not
  add to or remove from it.
- **Does not modify the candidate frozen prompt's
  content.** The prompt is *copied* from its iteration
  source to `PROMPT_FROZEN_v01.md`, byte-identical.
  Modifying the prompt during finalization would mean
  evaluating a different prompt against the test set
  than the one the loop produced — methodology
  violation.
- **Does not modify `plan.md` outside the `G6
  approved` substring entry in §11.** And §11 entries
  are written only when the user approves at G6; the
  runner does not silently update §11.
- **Does not parameterize the literal blocks in
  `loop_spec.md`.** Same pre-condition check as
  `/spp-loop`.
- **Does not commit produced files to git** or run any
  git operation. Same as the predecessor phases.
- **Does not retry the test-set inference after a
  successful read.** Only after a failed I/O (and
  only via the partial-deletion-and-restart mechanism)
  is a re-read permitted.
- **Does not surface partial test predictions or
  partial metrics to the user.** The G5 prompt is the
  user's first view of any test-derived signal. Partial
  reads do not produce surface output.
- **Does not generate a cross-model summary
  document.** v1 produces per-model REPORTs only;
  cross-model synthesis is v0.4 roadmap per
  `DESIGN.md` §7.1.
- **Does not advance on `EARLY_STOP.md` or
  `FAILED.md` terminations.** Those terminations
  indicate the loop did not reach a state worth
  finalizing; the recovery is to address the
  termination's reason, not to advance.
- **Does not offer a `--redo` flag or any other
  auto-cleanup path** for re-finalization. The
  manual-deletion friction is the discipline.
- **Does not invoke an LLM judge** to compute the
  draft recommendation in REPORT §6. The decision tree
  at §4 step 7 is deterministic and auditable; the
  user revises at G6 if they disagree.

---

## Versioning

The breaking-change list is shorter than `/spp-loop`'s
but contains the most methodologically-load-bearing
items in the project: the sacred-test-set discipline.
**When in doubt, treat the change as breaking.** The
sacred-test-set discipline is the methodology's
ultimate claim; silent weakening here invalidates every
claim upstream.

### Methodology-affecting (= breaking)

- **Reading the sacred test set more than once** per
  `/spp-finalize` lifecycle. Includes any path that
  lets the user "preview" test scores before
  committing to G5; any path that re-runs test
  inference after a successful first run; any path
  that surfaces test-set predictions outside the G5
  prompt; any "summary" or "intermediate" surface
  that exposes test-derived signal before G5.
- **Allowing `/spp-finalize` to advance on
  `EARLY_STOP.md` or `FAILED.md` termination types.**
  Finalization is for loops that reached `SUCCESS.md`;
  bypassing this discipline silently weakens the
  methodology's claim that the headline criterion was
  met before finalization.
- **Removing the partial-deletion-on-failure rule** at
  step 3. The rule is what distinguishes I/O failure
  (recoverable) from methodology violation (not
  recoverable). Without it, a partial successful read
  followed by retry would let the user see scores
  incrementally.
- **Allowing re-finalization without manual artifact
  deletion** — adding a `--redo` flag, or treating
  `REPORT.md` existence as ignorable, or auto-cleaning
  the four artifacts on user prompt. Re-finalization
  implies re-reading the test set; the deliberate
  friction is what makes the methodology consequence
  visible to the user.
- **Loosening the G5 / G6 literal-string match** —
  fuzzy matching, advancing on a timeout, accepting
  any non-empty response. Same rule as G1 / G2 / G3 /
  G4.
- **Expanding the G6 recommendation enumeration**
  beyond the four allowed values (`ship` /
  `ship-with-caveats` / `do-not-ship` /
  `iterate-further`). The four values are the
  methodology's enumeration of ship-decision outcomes;
  adding a fifth silently changes what the methodology
  produces.
- **Removing the literal "Auditor information-isolation
  invariant: preserved." line** from REPORT §5. The
  line is the methodology's traceable assertion;
  removing it makes the design lock unauditable
  post-hoc.
- **Allowing the command to write outside
  `runs/<model_identifier>/`** or to modify `plan.md`
  outside the `G6 approved` §11 entry.
- **Loosening the `loop_spec.md` literal-block check**
  at pre-condition 4. Same defense as `/spp-loop`.
- **Adding a cross-model summary document generation
  step** (v0.4 roadmap; not v1).
- **Switching the recommendation computation from the
  deterministic decision tree to LLM-judgment-based
  computation.** Predictability and auditability beat
  nuance for the ship decision; switching is breaking
  because it changes what "the runner's recommendation"
  means and removes the property that the same inputs
  always produce the same recommendation.
- **Adding any path that lets the user revise the test
  set, baseline, or splits during `/spp-finalize`.**
  Those are read-only here by contract; revision
  implies starting a new lifecycle.
- **Ignoring v0.2 §4 fields for K > 1 plans** (per
  `DESIGN.md` §7.1.1 compat layer). The phase must read
  `plan.md` §4's per-field metric sub-blocks +
  aggregate-strategy block + per-field floor sub-blocks
  for K > 1 plans; collapsing to a single
  task-aggregate metric would silently lose per-field
  information and produce a v0.1.0-shaped REPORT for a
  v0.2 plan, breaking the methodology's per-field
  bookkeeping guarantees.
- **Failing to surface per-field results in REPORT
  generation** (per `templates/REPORT.md.template` §2.1,
  §2.3, §3.1; bucket 3). The per-field scores, per-field
  trajectories, and per-field floor compliance are the
  v0.2 REPORT's load-bearing additions; collapsing them
  back to v0.1.0's flat shape would produce REPORTs
  that hide field-level performance — the same shape
  bucket 3 was designed to expose.
- **Collapsing the K=1 fallback into the K > 1 path** in
  a way that breaks legacy plans. The fallback must
  remain read-time-only and consistent with `/spp-loop`
  step 7 and `/spp-baseline` step 7's fallbacks (the
  runner-side fallback is implemented once across the
  four phase docs).
- **Refusing the
  `EARLY_STOP.md/early_stop_floor_unmet` advancement
  branch** at pre-condition 6, or letting it bypass the
  user-confirmation prompt. The branch is the
  methodology-sanctioned path for finalizing tasks
  where the aggregate plateaued at-or-above target but
  one or more per-field floors were unmet; refusing it
  forces users to either ignore the floors (silently
  break the discipline) or re-run the loop with floor
  values relaxed (silently weaken the methodology's
  claims about field-level performance). The
  user-confirmation prompt is what makes the
  advancement explicit.
- **Letting the
  `EARLY_STOP.md/early_stop_floor_unmet` advancement
  path skip the §7.5 acknowledged-risk-overrides
  population** at REPORT step 7. The unmet floors must
  surface in the REPORT — the methodology's transparency
  layer is what makes the partial-success path
  defensible; without it, the REPORT looks like a
  successful ship despite the floor failure.

### Behavioral (= non-breaking)

- Better wording in the G5 / G6 prompts.
- Adding new failure-mode surfaces for existing
  failure cases.
- Better REPORT-generation logic that produces clearer
  prose without changing what is recorded (e.g., a
  better cluster-narration style for §4, a clearer
  per-class statistics layout for §2).
- Improvements to the SHA-256 hash verification command
  in REPORT §9 (e.g., adding a verification script).
- Better reproducibility-checklist information in
  REPORT §10 (e.g., capturing more environment
  details).
- Performance improvements (better concurrency in the
  test-set inference, faster REPORT generation) that
  don't change the observable behavior.
- Refining the resumption prompts' wording.

When in doubt, treat the change as breaking.

---

## Pattern observations

`/spp-finalize` is the **fourth and final v1 command**.
It inherits the eight-section structure from
`/spp-init`, the literal-string gate enforcement pattern
from G1-G4, the atomic checkpoint write discipline, and
the fail-loud-and-specific failure-mode discipline.

What is structurally new:

- **The sacred-test-set discipline.** This is the only
  command authorized to read the test partition, and
  the discipline of reading it exactly once is what
  makes the methodology's claim against baseline
  overfitting credible. The defense against violation
  is layered: pre-condition refusal on existing
  REPORT, pre-condition refusal on non-`SUCCESS.md`
  termination, partial-deletion-on-failure for I/O
  errors, deliberate friction on re-finalization
  through manual artifact deletion.
- **The G6 structured-branch gate.** The first gate in
  the project with three explicit branches (approve,
  revise, halt) rather than a binary
  approve-or-decline. Justified by G6's role as the
  methodology's primary output: the user needs a
  structured way to revise the runner's draft
  recommendation before committing.
- **Resumability without re-read.** The command is
  resumable across G5 and G6 halts, but the test set
  is never re-read on resumption. The carve-outs at
  pre-condition 8 are the operational embodiment of
  this — the runner detects prior-state artifacts and
  skips the stages they correspond to.
- **Lifecycle closure.** After this command exits with
  a G6 decision (or halt-without-decision), the v1
  lifecycle is complete. The confirmation messages
  explicitly name the closure for each recommendation
  type and surface the methodology consequence of
  having seen test scores (for `iterate-further`, the
  start-fresh recommendation).

The **v1 command set is closed at four** with this PR.
The four phases map cleanly to the methodology's four
phases:

1. `/spp-init` — consultation; produces the contract
   (`plan.md` + `loop_spec.md`).
2. `/spp-baseline` — labeling and splits; produces
   `data/baseline.csv` + `data/splits.json`.
3. `/spp-loop` — optimization; produces per-iteration
   artifacts and the `SUCCESS.md` termination.
4. `/spp-finalize` — test-and-ship; produces `REPORT.md`
   + `PROMPT_FROZEN_v01.md` and the G6 decision.

Adding a fifth command requires answering a structural
question: what cognitive or orchestration job does the
new command do that none of the existing four does? The
bar is high. A fifth phase would require a methodology
change, not just a new command — and the methodology is
settled per `DESIGN.md`. Future PRs proposing a fifth
command should include a `DESIGN.md` revision in the
same PR per `CLAUDE.md` §5.

Future phases (in v2 or later) should recognize
`/spp-finalize` as the canonical example of a
**single-pass, methodologically-load-bearing command**:
simpler than the orchestration-heavy `/spp-loop` but
with stricter discipline on a single resource (the
sacred test set). The patterns to inherit:

- **Pre-condition refusal on prior-state requirements**
  (no prior REPORT for one-shot operations).
- **Positive enumeration of resource access** (test row
  IDs from `splits.json`'s `test` array).
- **Structured-branch gates** when the user needs to
  revise the methodology's output before committing.
- **Partial-deletion discipline** that distinguishes
  I/O failure from methodology violation.
- **Resumability without re-read** for resources whose
  access is rate-limited by methodology rather than
  by I/O budget.

---

## Cross-references

- [`phases/spp-init.md`](spp-init.md),
  [`phases/spp-baseline.md`](spp-baseline.md),
  [`phases/spp-loop.md`](spp-loop.md) — pattern
  sources for the eight-section structure, literal-
  string gate enforcement (G5 inherits from G1-G4 at
  the binary-branch level; G6 extends to a three-
  branch structure with the same literal-string match
  on each branch's recognized prefix), atomic
  checkpoint writes, fail-loud failure modes.
- [`templates/plan.md.template`](../templates/plan.md.template)
  — read for §3 success criterion (the headline
  criterion fed into the decision tree at §4 step 7),
  §6 baseline scope (REPORT §7), §9 gate phrases (G5
  / G6), §11 revision log (write target for `G6
  approved` entries).
- [`templates/loop_spec.md.template`](../templates/loop_spec.md.template)
  — read at pre-conditions for §7 sacred-test-set
  posture (literal-string check), §5 model and
  execution parameters (apples-to-apples test-set
  inference vs. loop's evaluations).
- [`templates/REPORT.md.template`](../templates/REPORT.md.template)
  — the document this command populates. All sections
  of the template are populated; §5 must include the
  literal "Auditor information-isolation invariant:
  preserved." line per the template's validation
  rules.
- [`agents/auditor.md`](../agents/auditor.md) —
  referenced for §5 of REPORT (the audit summary
  aggregates from per-iteration `auditor_review.md`
  files written under the auditor's information-
  isolation contract). The literal invariant-preserved
  line in REPORT §5 is the methodology's traceable
  assertion that the contract was honored.
- `DESIGN.md` §2.1 (baseline overfitting — the test-
  set evaluation at §4 steps 3–4 is the ultimate
  check on whether the loop's discipline against this
  failure mode held), §2.2 (model overfitting —
  REPORT §7's model lock-in caveat), §3 (canonical
  command list — this is the fourth and final
  command), §7.1 (non-goals — the cross-model summary
  document is v0.4 roadmap; v1 produces per-model
  REPORTs only), §10 glossary (sacred test set — this
  command is the only one authorized to read it; gates
  G5 / G6).
- `CLAUDE.md` §4 (Semantic Commits — applies to
  changes to this command), §5 (PR rules —
  methodology-affecting PRs require `CHANGELOG.md`
  updates), §8 (auditor information isolation —
  applies indirectly: the per-iteration audit summary
  in REPORT §5 must include the literal invariant-
  preserved line).
