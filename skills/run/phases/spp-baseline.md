# /spp-baseline

The second phase in `spp`. Runs Phase 1 + Phase 1.5 of the
methodology: labels data (or imports labels), invokes the
`baseline-quality` sub-skill for adversarial review, generates
stratified splits, and stops at gates G2 (baseline review)
and G3 (split confirmation).

> **Note on slash-command notation.** `/spp-baseline` is a
> methodology phase identifier used internally during a
> `/spp:run` session, not a separate user-typed slash command;
> see [`spp-init.md`](spp-init.md) for the canonical statement
> of the convention.

This document inherits the eight-section structure pinned by
`/spp-init`. Two structural differences from `/spp-init`:

1. **Two gates instead of one** (G2 + G3). The eight-section
   structure handles this naturally — gate enforcement (§5)
   describes both gates uniformly.
2. **A sub-skill verdict gates G2.** This is the first phase
   in `spp` where a sub-skill's output has operational force
   on a gate. The pattern (sub-skill produces a verdict token
   → phase enforces the verdict at the gate, in addition to
   the user's approval phrase) is what the auditor agent +
   `/spp-loop` will inherit in subsequent build-order steps.

---

## 1. Command identity

`/spp-baseline` is the labeling-and-splits entry point: it
walks the user through labeling rows from the data source
named in `plan.md` §6 (or imports existing labels), invokes
the `baseline-quality` sub-skill for adversarial review,
enforces the verdict at gate G2, generates stratified splits
per `plan.md` §7, enforces the user's split-confirmation
phrase at gate G3, and exits.

It produces exactly two files under `spp/<task_name>/`:
`data/baseline.csv` (the labeled baseline) and
`data/splits.json` (the stratified train/dev/test split). It
also updates `plan.md` §6 (adding a `BASELINE_QUALITY_NOTE`
subsection from the sub-skill's findings) and `plan.md` §11
(revision-log entries when the review caused class-definition
or class-balance changes).

It does not start the optimization loop, does not invoke the
auditor or adversary agents, does not generate any prompt
versions, and does not touch any file outside
`spp/<task_name>/`. Those jobs belong to `/spp-loop` (Phase 2
step 8).

The judgment for the adversarial review lives in the
[`baseline-quality`](../sub-skills/baseline-quality/SKILL.md)
sub-skill. The orchestration, filesystem persistence, and
gate enforcement live here. Same separation pattern as
`/spp-init`'s relationship to the designer agent: editing the
review protocol means editing the sub-skill; editing the
labeling-and-splits flow means editing this command.

---

## 2. Invocation

```
/spp-baseline
```

No arguments. The command reads
`spp/<task_name>/config/plan.md` to know which task it is
operating on. The active task is determined by the **most
recently approved plan in the working tree** — usually the
plan whose `/spp-init` invocation just completed.

**Disambiguation.** "Most recently approved" means the plan
with the most recent G1-approval entry in its `plan.md` §11
revision log (the entry whose `Reason` field records the
G1 approval). Timestamps are read from the §11
`Date` column. If multiple plans tie on date, or one or
more candidates have missing/unparseable timestamps, the
command does not pick — it lists all candidates and asks
the user to choose:

> Multiple `spp/*/` tasks have an approved plan. Which one
> should `/spp-baseline` run on?
>   1) `spp/support-billing-triage/`
>   2) `spp/issue-categorization-v2/`
> Reply with the number or the task name.

The command refuses to run without an existing approved plan
from a prior `/spp-init`. There is no "create plan from
scratch" path through this command — that is `/spp-init`'s
job, by design (the command-vs-agent separation pattern from
PR #4).

---

## 3. Pre-conditions

The command refuses to proceed unless all of the following
are true. Pre-condition failures exit with a specific error
message naming the missing piece, not a generic "something
went wrong" — same loud-and-specific pattern as `/spp-init`.

1. **Working directory is the user's project root.** Same
   detection as `/spp-init` §3 (presence of `README.md`,
   `pyproject.toml`, `package.json`, or `.git/`).

2. **The `spp` skill is installed.** The command verifies
   that
   [`sub-skills/baseline-quality/SKILL.md`](../sub-skills/baseline-quality/SKILL.md),
   `templates/plan.md.template`, and the eventual splits-
   generation utility (Phase 4 harness or sklearn directly)
   are accessible.

3. **An approved `plan.md` exists.** At least one
   `spp/<task_name>/config/plan.md` is on disk with a
   `PLAN_VERSION ≥ v1`, validation rules pass, and the §11
   revision log has at least one entry recording G1
   approval. If multiple plans exist, the user picks per
   §2.

4. **`BASELINE_STATUS` in `plan.md` §6 is one of**
   `not-started`, `in-progress`, or `complete`. Any other
   value is a contract violation — the plan was hand-edited
   to a state that the methodology does not recognize.
   Refuse and surface the value.

5. **The data source named in `plan.md` §6 is readable.**
   The command does not validate the data's contents; it
   just confirms the file exists and is non-empty. If the
   source moved or was renamed, the user updates `plan.md`
   §6 (with a §11 revision-log entry) and re-invokes. The
   command does not silently search for a moved file.

6. **The task directory is writable.** Specifically,
   `spp/<task_name>/data/` will be created if it does not
   exist; the parent must be writable. Same writability
   discipline as `/spp-init`.

7. **Existing-baseline schema check.** If `BASELINE_STATUS
   = complete` on entry **and**
   `spp/<task_name>/data/baseline.csv` exists already, the
   command verifies the schema:
   - Has a column matching the task's row identifier
     convention (typically `id`).
   - Under v0.2 (`plan.md` §2 carries `OUTPUT_SCHEMA`):
     has one label column per OUTPUT_SCHEMA field (column
     name matches the field name); each enum-typed field's
     column values are a subset of the field's `enum`; each
     boolean-typed field's column values are in
     `{true, false}`. Per-field columns sit alongside the
     row identifier and any optional `borderline_note`
     column.
   - Under v0.1.0 fallback (`plan.md` §2 carries
     `LABEL_SPACE` and the runner auto-promotes to a
     one-field OUTPUT_SCHEMA): has a column matching the
     `LABEL_SPACE` (typically `label`); the column's values
     are a subset of `LABEL_SPACE`. K=1 in the v0.2 path is
     equivalent (one OUTPUT_SCHEMA field, one column).
   Schema mismatch is a fatal pre-condition error with a
   specific message naming the column or value at fault
   (see §7 for the failure mode).

   **Note on multi-file data sources.** If `plan.md` §6's
   data-source description names a join (e.g., labels in
   one file, row content in another, joined on a shared
   ID), `data/baseline.csv` is the **assembled join
   result**, not the raw source files. Producing the join
   is the user's responsibility before `/spp-baseline`
   runs; the command does not perform joins itself in v1
   (kept simple by design — joins are domain-specific and
   often involve filtering or de-duplication that the
   command should not unilaterally interpret). A
   forthcoming utility script in the Phase 4 harness may
   automate common join patterns; for v1, the user
   assembles `data/baseline.csv` manually (or via their
   own one-off script) and re-invokes.

---

## 4. Execution flow

The orchestration sequence. Steps marked **(pre-display)**
happen before the user sees anything; **(consultation)**
involves user back-and-forth (labeling, sub-skill review,
gate prompts); **(post-G2)** and **(post-G3)** happen after
the respective gates have been approved.

The flow has two distinct paths through steps 4–6 depending
on `BASELINE_STATUS`:

- **Fresh labeling path:** `BASELINE_STATUS` is
  `not-started` or `in-progress` on entry.
- **Existing-baseline path:** `BASELINE_STATUS` is
  `complete` on entry, with `data/baseline.csv` already
  populated.

Steps 7 onward (sub-skill review, G2 enforcement, splits
generation, G3 enforcement) are identical for both paths.

### Numbered steps

1. **(pre-display) Verify pre-conditions.** Run §3 checks.
   Exit on failure with a specific error.

2. **(pre-display) Determine path.** Read `BASELINE_STATUS`
   from `plan.md` §6:
   - `not-started` or `in-progress` → fresh labeling path.
   - `complete` → existing-baseline path.

3. **(pre-display) Create the data directory.**
   `spp/<task_name>/data/` if it does not exist. Same
   atomic-creation discipline as `/spp-init` §4 step 4 —
   no other directories are created.

4. **(consultation, fresh labeling path only) Walk the
   user through labeling.** The command reads the data
   source named in `plan.md` §6, presents rows one at a
   time, and asks the user to label per the `OUTPUT_SCHEMA`
   from §2. Under v0.2 with K > 1, each row's labeling
   produces one value per OUTPUT_SCHEMA field, persisted
   into the corresponding column in `baseline.csv` (one
   column per field, column name = field name). Under
   v0.2 with K=1 (single-field OUTPUT_SCHEMA) the labeling
   produces one value per row in the single field's
   column. Under v0.1.0 fallback (`plan.md` §2 carries
   `LABEL_SPACE`), the runner auto-promotes to a one-field
   OUTPUT_SCHEMA whose column is named `label` —
   equivalent to v0.1.0's flow. Persistence is
   **incremental and atomic**: after each row's full label
   (all fields filled), the command writes
   `data/baseline.csv.tmp`, `fsync`s, and renames to
   `data/baseline.csv` — same `tmp + fsync + rename`
   pattern as `/spp-init`'s `plan.md` checkpoint writes.

   Labeling continues until either:
   - The user has labeled the target baseline size from
     `plan.md` §6 (`BASELINE_TARGET_SIZE`), **or**
   - The user explicitly stops by typing a stop phrase —
     **`stop` or `enough labels`**, whitespace-stripped
     and case-insensitive. The command honors stops
     gracefully and leaves the partial baseline on disk
     for the next `/spp-baseline` invocation to resume
     from; same resumability discipline as `/spp-init`'s
     partial plan.

     On stop, the command writes the final
     `BASELINE_STATUS` value (`in-progress` if below
     target; `complete` if at target) and surfaces:

     > Labeled {{N}} rows of {{TARGET}} target. Mark
     > baseline complete at this size, or continue
     > labeling later?

     The user replies "complete at this size" (which
     bumps `BASELINE_STATUS` to `complete` and proceeds
     to step 7 in the same session) or "continue later"
     (which exits the command cleanly with
     `BASELINE_STATUS = in-progress` for resumption).

   `BASELINE_STATUS` is updated in-place in `plan.md` §6:
   - On first label: `not-started` → `in-progress`.
   - On reaching the target size or user stop: stays
     `in-progress` if not at target; `complete` if at
     target.
   - The `plan.md` write follows the same atomic-checkpoint
     discipline as `/spp-init` (the command modifies the
     status field via `plan.md.tmp` rename).

   The command does not unilaterally interpret rows. If a
   row is hard to label, the user can mark it as a
   borderline (the borderline marker is just a note in
   `data/baseline.csv` — typically a `borderline_note`
   column populated only for flagged rows). The
   borderlines are useful inputs to the sub-skill's §3.2
   check but do not change the row's primary label.

5. **(consultation, fresh labeling path only) Confirm
   labeling complete.** Once labeling has reached the
   target size (or the user has explicitly stopped at a
   different size), the command summarizes:

   > Labeled {{N}} rows out of target {{TARGET}}. Class
   > distribution: {{DIST}}. Borderlines flagged: {{B}}.
   > Proceed to baseline-quality review?

   The user replies "yes" (proceed) or asks to label more
   first. If "yes," the command updates `plan.md` §6's
   `BASELINE_STATUS` to `complete` (with a revision-log
   entry per §11) and proceeds to step 7.

6. **(consultation, existing-baseline path only) Confirm
   the imported baseline.** The command summarizes the
   loaded `data/baseline.csv`:

   > Loaded {{N}} rows from existing baseline.csv. Class
   > distribution: {{DIST}}. Schema check: passed (per §3
   > step 7). Proceed to baseline-quality review in
   > audit-of-existing-labels mode?

   On user confirmation, the command proceeds to step 7.

7. **(consultation) Invoke `baseline-quality` with
   per-field calibration.** Under v0.2 the sub-skill's §3
   protocol runs **per OUTPUT_SCHEMA field** (per
   `baseline-quality` SKILL.md §1 v0.2 paragraph; `DESIGN.md`
   §7.1.1 compat layer baseline-quality adaptation). The
   command passes the OUTPUT_SCHEMA fields read at
   pre-conditions to the sub-skill; the sub-skill walks
   each §3 check per field and returns per-field findings
   consolidated into a single verdict on the baseline as a
   whole. K=1 backward compat: with one OUTPUT_SCHEMA field
   the per-field protocol runs once and the
   findings + verdict shape collapses to v0.1.0's; legacy
   plans persisting `LABEL_SPACE` work via the runner's
   auto-promotion to a one-field OUTPUT_SCHEMA. The command
   surfaces the sub-skill's user-facing prompts and relays
   answers; this step is mostly mechanical from the
   command's side — the sub-skill drives the protocol; the
   command just relays.

   The sub-skill returns:
   - A verdict (`ready` / `revise` / `not-ready`) — one
     token consolidated across the per-field within-field
     verdicts per `baseline-quality` SKILL.md §3.7's
     "any-not-ready dominates, any-revise dominates ready"
     rule. The verdict is the unit that gates G2.
   - A `BASELINE_QUALITY_NOTE` paragraph for `plan.md`
     §6's "baseline-quality review" subsection, recording
     per-field findings followed by the consolidated
     verdict.
   - A findings list (only when verdict is `revise` or
     `not-ready`), grouped per OUTPUT_SCHEMA field.

   If the review caused changes to `plan.md` §2 (class
   definition), §6 (label fixes, balance updates), or §10
   (new open questions), those changes are recorded with a
   §11 revision-log entry and a `PLAN_VERSION` bump. The
   command does these updates atomically, same `tmp +
   fsync + rename` pattern.

8. **(consultation) Present at gate G2.** The exact prompt
   text depends on the verdict.

   If verdict is `ready`:

   > Baseline-quality review complete. Verdict: ready.
   > {{BASELINE_QUALITY_NOTE}}
   >
   > To approve and proceed to splits generation, reply
   > with the exact G2 approval phrase you recorded in §9
   > of plan.md: `{{G2_APPROVAL_PHRASE}}`.

   If verdict is `revise`:

   > Baseline-quality review complete. Verdict: revise.
   > Findings:
   > {{FINDINGS_LIST}}
   >
   > Recommended path: address the findings (see each
   > item's recommendation), then re-invoke /spp-baseline
   > to re-run the review. If you choose to proceed
   > despite these findings, record an explicit override
   > entry in plan.md §11 with your justification, then
   > reply with the G2 approval phrase
   > `{{G2_APPROVAL_PHRASE}}`.

   If verdict is `not-ready`:

   > Baseline-quality review complete. Verdict: not-ready.
   > Findings:
   > {{FINDINGS_LIST}}
   >
   > /spp-baseline cannot advance past G2 with this
   > verdict. To proceed: either resolve the findings and
   > re-invoke (the path strongly recommended by the
   > methodology), or record an explicit not-ready
   > override entry in plan.md §11 — the override
   > propagates into REPORT.md §7.2 limitations at
   > /spp-finalize time so the methodology's claim against
   > baseline overfitting is honest about the
   > acknowledged risk.

   See §5 below for the gate-G2 enforcement details
   including how the override is detected.

9. **(post-G2) Generate stratified splits.** Once G2 has
   advanced (per §5's enforcement), the command generates
   `data/splits.json` per `plan.md` §7's split ratios
   (`TRAIN_PCT` / `DEV_PCT` / `TEST_PCT`),
   `STRATIFICATION_KEY`, and `SPLIT_SEED`.

   **Implementation note.** v1 uses scikit-learn's
   `train_test_split` with stratification directly (the
   library is in `environment.yml`). The Phase 4 harness
   (when populated) will wrap this with a reproducibility
   logging layer; the wrapping is non-breaking — the
   produced `splits.json` schema documented below does not
   change, only the production path does.

   `data/splits.json` is written via the same atomic
   pattern as `plan.md` and `baseline.csv`:
   `splits.json.tmp` → `fsync` → rename.

   **Language-aware stratification (v0.6, DESIGN.md §7.1.7).**
   When `data/baseline.csv` carries the optional per-row
   `language` column (`plan.md` §6 Language coverage) with two
   or more distinct values, the splitter stratifies jointly on
   `STRATIFICATION_KEY` × `language` so every partition —
   including the sacred test set — is representative of the
   language distribution, and it verifies every language is
   present in every partition. This is **data-driven, not a
   flag**: with the column absent or single-valued the split
   is identical to the pre-v0.6 label-only behavior. The
   outcome is recorded in `splits.json`'s `language_stratified`
   field. A row with a missing `language` value in a
   multilingual baseline is a hard error — every row must
   carry a tag.

   **`splits.json` schema (v1).** The file is a JSON object
   with these top-level fields:

   ```json
   {
     "schema_version": 1,
     "stratification_key": "label",
     "seed": 42,
     "ratios": {"train": 60, "dev": 20, "test": 20},
     "language_stratified": false,
     "row_ids": {
       "train": ["row_001", "row_007"],
       "dev":   ["row_002", "row_011"],
       "test":  ["row_003", "row_017"]
     }
   }
   ```

   Field semantics:
   - `schema_version` — integer, currently `1`. Reserved
     for forward compatibility; downstream phases check
     this and refuse to read versions they do not
     understand.
   - `stratification_key` — string; the column name in
     `data/baseline.csv` whose value is the
     stratification target. Mirrors `plan.md` §7's
     `STRATIFICATION_KEY` field.
   - `seed` — integer; mirrors `plan.md` §7's
     `SPLIT_SEED`.
   - `ratios` — integer percentages, summing to 100.
     Mirror `plan.md` §7's `TRAIN_PCT` / `DEV_PCT` /
     `TEST_PCT`.
   - `language_stratified` — boolean (v0.6, DESIGN.md
     §7.1.7). `true` when the split was additionally
     stratified by the per-row `language` column because the
     baseline is multilingual (the column is present with two
     or more distinct values); `false` otherwise. Additive
     and backward-compatible: absent in pre-v0.6
     `splits.json` files, where it reads as `false`. It is a
     **record of what the splitter did**, not an input — the
     behavior is auto-detected from the data, not configured.
   - `row_ids` — object whose three values are arrays of
     **strings**. Each string matches the row identifier
     convention from §3 step 7's schema check (typically
     the `id` column of `baseline.csv`). The arrays are
     disjoint and their union covers every row in
     `baseline.csv`.

   **Why row IDs, not row content.** The file references
   row IDs from `baseline.csv`; it does not duplicate row
   content. This keeps the file small, makes it
   human-auditable for "is this row in train or test?",
   and means a reviewer reading the diff in a future PR
   can see exactly which rows changed partition (rather
   than getting a meaningless content-level diff).

   This schema is settled now because `/spp-loop` (Phase 2
   step 8) reads it. Schema changes after this PR are
   `BREAKING CHANGE:` per the §"Versioning" section
   below.

10. **(post-G2) Present at gate G3.** The command shows the
    user the computed split:

    > Splits generated. Train: {{TRAIN_N}} rows
    > ({{TRAIN_DIST}}). Dev: {{DEV_N}} rows
    > ({{DEV_DIST}}). Test: {{TEST_N}} rows
    > ({{TEST_DIST}}). Class balance preserved within
    > {{TOL}}%. Seed: {{SPLIT_SEED}}.
    >
    > Note: the test set is sacred from this point until
    > /spp-finalize per DESIGN.md §10. /spp-loop will not
    > read test rows.
    >
    > To approve splits and proceed to /spp-loop, reply
    > with the exact G3 approval phrase you recorded in §9
    > of plan.md: `{{G3_APPROVAL_PHRASE}}`. To request a
    > different seed or different ratios, say "different
    > seed" or "different ratio".

11. **(post-G3) Print confirmation.** Once G3 has been
    matched, the command prints:

    > Baseline approved at G2. Splits approved at G3.
    > Files written:
    >   spp/{{TASK_NAME}}/data/baseline.csv
    >   spp/{{TASK_NAME}}/data/splits.json
    > plan.md updated:
    >   §6 (baseline-quality review note)
    >   §11 (revision log entries)
    > Next step: /spp-loop.

    The command exits cleanly.

### K=1 backward compatibility

Legacy v0.1.0 plans persisting `LABEL_SPACE` (instead of
v0.2's `OUTPUT_SCHEMA`) continue to work end-to-end without
modification. The runner's K=1 fallback auto-promotes the
plan's `LABEL_SPACE` to a one-field OUTPUT_SCHEMA at read
time (the same fallback `/spp-loop` step 7 uses; the
runner-side fallback is implemented once across the four
phase docs). `baseline-quality`'s per-field protocol runs
once on the auto-promoted single field, producing
v0.1.0-equivalent findings, note, and verdict; G2
enforcement is unchanged in shape; `baseline.csv` is
labeled with the v0.1.0 `label` column. Migration of an
existing v0.1.0 plan to the v0.2 template surface is
documented in `DESIGN.md` §7.1.1 compat layer (Manual
upgrade steps); the migration is opt-in and not required
for legacy plans to keep running.

---

## 5. Gate enforcement (G2 and G3)

Two gates. Both follow the literal-string-equality match
semantics established for G1 in `/spp-init` §5: whitespace-
stripped, case-normalized to the recorded phrase, punctuation
matters, surrounding text is a non-match. Same recorded-
phrase strictness; same "revise §9" branch for users who want
to update the recorded phrase mid-flow.

### Gate G3 — straightforward

G3 is identical in shape to G1: the user's approval phrase is
recorded in `plan.md` §9; the command checks for it
literally. Mismatch surfaces a specific message naming both
the recorded phrase and the user's input. The "different
seed" / "different ratio" branches re-run step 9 with new
parameters; the user can iterate until satisfied.

### Gate G2 — verdict-enforced

G2 is the first place in `spp` where a sub-skill verdict has
**operational force** on a gate, beyond the user's approval
phrase. The enforcement logic:

- If the verdict is `ready`: G2 advances on the user's
  literal G2 approval phrase. No additional check.
- If the verdict is `revise`: G2 advances on the user's
  literal G2 approval phrase, **with an additional check**:
  the command verifies that `plan.md` §11 has a
  revision-log entry whose `Reason` field contains an
  explicit acknowledgement of the `revise` findings (the
  command looks for the literal substring "baseline-
  quality" in a §11 entry that post-dates the verdict).
  If the entry exists, advance. If the user typed the
  approval phrase without recording the override, surface:

  > G2 cannot advance: verdict is `revise` and no
  > override entry has been recorded in plan.md §11.
  > Either:
  >   1) Address the findings and re-invoke
  >      /spp-baseline.
  >   2) Add an entry to plan.md §11 with a Reason that
  >      mentions "baseline-quality" and your
  >      justification for proceeding despite the
  >      findings.

- If the verdict is `not-ready`: same as `revise`, but
  with stronger language and an additional propagation
  guarantee. The required §11 entry must contain the
  literal substring "not-ready override" (so future
  readers can find every not-ready override by grep). The
  not-ready override entry **propagates into `REPORT.md`
  §7.2** at `/spp-finalize` time — the methodology's
  claim against baseline overfitting must be honest about
  the acknowledged risk. The command refuses to advance
  G2 without the literal phrase in the §11 Reason field.

The pattern in one sentence: **the verdict adds a literal-
string check on top of the gate's normal approval-phrase
check.** This is the operational mechanism by which the
sub-skill's verdict has teeth. Future contributors who
propose loosening this — letting the verdict be informational
only, or fuzzy-matching the override phrase — are proposing a
`BREAKING CHANGE:` per the §"Versioning" section below.

The auditor agent (Phase 2 step 6) will inherit this pattern,
applied per-iteration: the auditor's `categorical` /
`row-specific` verdict will gate whether a rule edit advances
to the next iteration in the same shape — the loop checks the
verdict literally and refuses to advance without it (or
without a documented override).

---

## 6. Outputs

**On successful completion, exactly two new files exist** and
two existing-file updates have been written. No others.

| Path | Contents | Validation status |
|---|---|---|
| `spp/<task_name>/data/baseline.csv` | Labeled baseline; row count meets target or user-confirmed stop; schema matches `plan.md` §2's `LABEL_SPACE`. | clean |
| `spp/<task_name>/data/splits.json` | Stratified train/dev/test split per `plan.md` §7; `STRATIFICATION_KEY` preserved; seed `SPLIT_SEED` recorded inline. | clean |
| `spp/<task_name>/config/plan.md` (updated) | §6 gains a `BASELINE_QUALITY_NOTE` subsection; §11 gains revision-log entries for any class-definition refinements, label changes, or override entries. `PLAN_VERSION` bumped if §2 / §6 / §10 changed. | re-validated |

**The command does not create:**

- `runs/` or any `runs/<model>/` subdirectory (that's
  `/spp-loop`'s output, after gate G4).
- `prompt_v01.md` or any prompt-versioned file (also
  `/spp-loop`'s output).
- `REPORT.md` or `PROMPT_FROZEN_v01.md` (those are
  `/spp-finalize`'s output, after gates G5/G6).
- A separate `baseline_quality_review.md` document — the
  review's findings live in `plan.md`, not in a parallel
  artifact (sub-skill §5 cross-skill constraint).
- Any per-row metadata files annotating
  `data/baseline.csv` rows with quality scores.

**Terminal/chat output**, in order:

1. The labeling walkthrough (fresh path) or the imported-
   baseline summary (existing path).
2. The `baseline-quality` sub-skill's §3 protocol prompts
   and findings.
3. The G2 gate prompt (verdict-flavored per §5).
4. The splits summary at step 10.
5. The G3 gate prompt.
6. The confirmation message at step 11 (only after both
   gates are matched).

If the command exits before G2 (sub-skill returns
`not-ready` and user does not record an override), the user
sees up through step 7's findings list but does not see the
splits summary or the final confirmation. `data/baseline.csv`
remains on disk; `data/splits.json` is **not** written —
splits are post-G2 work.

---

## 7. Failure modes and recovery

The pattern: failures are loud and specific, never silent.
The table below names what the command does and how the user
recovers — same eight-section discipline as `/spp-init` §7.

| Failure | What the command does | How the user recovers |
|---|---|---|
| No approved plan exists | Exit immediately with `no spp/*/config/plan.md found with PLAN_VERSION ≥ v1 and a §11 G1-approval entry. /spp-init must complete G1 before /spp-baseline can run.` | Run `/spp-init` to completion. |
| Multiple plans exist | List them and ask the user to pick per §2. Do not pick on the user's behalf. | User picks. |
| `BASELINE_STATUS` in §6 is not one of the recognized values | Exit with `BASELINE_STATUS in plan.md §6 is '{{VAL}}'; expected one of {not-started, in-progress, complete}. The plan may have been hand-edited to an unrecognized state.` | User fixes §6 (with a §11 entry), re-invokes. |
| Data source named in §6 is unreadable | Exit with `data source 'spp/{{TASK}}/data/{{SRC}}' (per plan.md §6) is unreadable: {{OS_ERROR}}.` | User restores the file or updates §6 (with a §11 entry). |
| Existing `baseline.csv` schema mismatch | Exit with `existing data/baseline.csv schema mismatch: {{COL}} column missing` or `label values {{VAL_LIST}} not in plan.md §2 LABEL_SPACE`. | User fixes the CSV or the LABEL_SPACE (whichever is wrong), re-invokes. |
| User abandons labeling mid-way | Partial `baseline.csv` is preserved; `BASELINE_STATUS` stays `in-progress`. Command exits cleanly. | Re-invoke `/spp-baseline` to resume. |
| `baseline-quality` returns `not-ready` and user does not record the §11 override | G2 does not advance (per §5). Command exits cleanly. `baseline.csv` is preserved; `splits.json` is **not** written. | User addresses findings and re-invokes, or records the override and re-invokes. |
| `baseline-quality` returns `revise` and user does not record the §11 acknowledgement | G2 does not advance (per §5). Command surfaces the override-required message. | Same recovery as the `not-ready` case, with weaker language. |
| User types a non-matching G2 or G3 phrase | Re-prompt with the same mismatch message pattern as `/spp-init` §5. Do not advance, do not guess intent. | Retype the phrase, or take the "revise §9" branch. |
| Splits generation fails (a class has fewer rows than the requested test split would require) | Exit with `cannot generate splits: class '{{CLASS}}' has {{N}} rows, requested test split would require ≥ {{REQ}}. Recommendations: (a) lower TEST_PCT in plan.md §7; (b) gather more data for class '{{CLASS}}'; (c) document the limitation in plan.md §11 and proceed with the smaller test split via override.` | User picks one of the three recommendations, updates the plan, re-invokes. |
| Filesystem permission error | Exit with `cannot write to spp/{{TASK}}/data/: {{OS_ERROR}}.` | Fix permissions, re-invoke. |
| User wants to interrupt during `baseline-quality` review | Sub-skill's protocol respects an interrupt; the partial review state is not persisted (the review itself is fast enough that re-running is acceptable). The command exits cleanly. | Re-invoke; review re-runs from scratch with current `baseline.csv` state. |

The command never writes a `splits.json` that would fail
validation if read by `/spp-loop`. Splits are post-G2;
nothing is written to `splits.json` until G2 has advanced
per §5. Same contract-at-both-ends pattern as `/spp-init`.

---

## 8. What `/spp-baseline` does NOT do

Mirroring `/spp-init` §8:

- Does not start the optimization loop. That's
  `/spp-loop`'s job, after gate G4.
- Does not invoke the auditor or adversary agents. Same
  reason — that's `/spp-loop`.
- Does not generate prompt versions or `prompt_v01.md`.
  Also `/spp-loop`'s job.
- Does not run the sacred test set or generate `REPORT.md`
  or `PROMPT_FROZEN_v01.md`. That's `/spp-finalize`'s job.
- Does not create any `runs/` directory.
- Does not modify any file outside `spp/<task_name>/`.
- **Does not read sacred test rows.** None exist on disk
  until step 9 of this command writes `splits.json`, and
  even then the command does not access the test partition
  beyond writing it. The sacred-test-set guarantee per
  `DESIGN.md` §10 is preserved by construction.
- Does not silently override the `baseline-quality`
  verdict. The verdict has gate-enforcement teeth per §5;
  bypassing it is a `BREAKING CHANGE:` per §"Versioning".
- Does not parameterize the literal-string blocks in
  `loop_spec.md` (those were filled by `/spp-init` and are
  not re-derived here; this command does not modify
  `loop_spec.md` at all).
- Does not commit produced files to git or run any git
  operation. Same as `/spp-init`.
- Does not write a separate `baseline_quality_review.md`
  document. Findings flow into `plan.md` per the
  sub-skill's §5 cross-skill constraint.

---

## Versioning

Same rule as the predecessor phases and sub-skills.
Methodology-affecting changes are flagged as
`BREAKING CHANGE:` per `CLAUDE.md` §4.

**Methodology-affecting (= breaking):**

- **Allowing the command to advance past G2 with a
  `not-ready` verdict and no override entry.** The
  verdict-enforcement is the entire point of the gate's
  teeth.
- **Loosening literal-string match on G2 or G3 approval
  phrases.** Same rule as `/spp-init`'s G1.
- **Allowing the command to write outside
  `spp/<task_name>/`.** The output scope is part of the
  contract with downstream phases.
- **Removing the override-substring check on §11 entries**
  (the literal "baseline-quality" / "not-ready override"
  matches that the command looks for in step 8 / §5).
  Without those literal markers, the override pattern is
  not auditable post-hoc.
- **Allowing the command to read the test partition**
  beyond writing it during splits generation.
- **Removing the §6 `BASELINE_QUALITY_NOTE` update**
  requirement (the note is part of the audit trail; without
  it, "we ran the review" is indistinguishable from "we
  did not").
- **Invoking `baseline-quality` without per-field
  calibration on a v0.2 plan** (per `DESIGN.md` §7.1.1
  compat layer baseline-quality adaptation). The per-field
  protocol is what makes K > 1 plans defensible at G2;
  reverting to a baseline-wide single review surface would
  silently weaken the methodology's claim against
  baseline overfitting on multi-field tasks.
- **Multiplying the G2 verdict to per-field** (one verdict
  per OUTPUT_SCHEMA field instead of the consolidated
  single verdict). G2's enforcement pattern is single-
  verdict per baseline; multiplying the verdict to K
  verdicts would multiply the gate-evaluation surface and
  contradict the consolidation rule pinned in `DESIGN.md`
  §7.1.1 compat layer.
- **Changing the K=1 fallback semantics** (auto-promotion
  of v0.1.0 `LABEL_SPACE` to a one-field OUTPUT_SCHEMA at
  read time). Removing the fallback would break legacy
  plans; rewriting plans on disk would violate the
  plan.md-as-contract rule. The fallback must remain
  read-time-only and consistent with `/spp-loop` step 7's
  fallback (the runner-side fallback is implemented once
  across the four phase docs).

**Behavioral (= non-breaking):**

- Better wording in any prompt the command surfaces.
- Adding a new pre-condition check that does not change
  what the command outputs.
- Better failure-mode messages for existing failure modes.
- New defaults for splits-generation parameters that the
  user can override.
- Adding a new output column to `data/baseline.csv` that
  the user opts into (e.g., `confidence_score` for
  user-provided per-label confidence) — as long as the
  schema-check in §3 step 7 still treats the column as
  optional.
- Adding the optional per-row `language` column and the
  additive `splits.json` `language_stratified` field (v0.6,
  DESIGN.md §7.1.7). Both are backward-compatible: the column
  is optional and treated as such by the §3 step 7 check, the
  field defaults to `false` and is absent from pre-v0.6
  files, and language-aware stratification auto-activates from
  the data without changing the label-only path.

When in doubt, treat the change as breaking.

---

## Cross-references

- [`sub-skills/baseline-quality/SKILL.md`](../sub-skills/baseline-quality/SKILL.md)
  — the sub-skill the command invokes at step 7. The
  verdict the sub-skill returns is what gates G2 per §5.
- [`phases/spp-init.md`](spp-init.md) — the prior
  command. Patterns inherited from `/spp-init`: eight-
  section structure (§1–§8), atomic checkpoint writes
  (`tmp + fsync + rename`), literal-string gate enforcement
  (G2 and G3 follow the G1 shape), failure-mode pattern
  (loud and specific), invocation-from-project-root
  pre-condition, command-vs-agent / command-vs-sub-skill
  separation discipline.
- [`templates/plan.md.template`](../templates/plan.md.template)
  — read in pre-conditions, updated at steps 4-6 (status),
  step 7 (review-note + revision log), step 9 (no
  modifications). Validation rules 7 (`SACRED_TEST_ACK`),
  8 (`AUDITOR_CONFIG`), 9 (split-ratio sum), 11 (§9 gate
  phrases), and 12 (§11 revision log) are all relevant.
- `phases/spp-loop.md` — the next command in the
  methodology. Not yet written (Phase 2 step 8); the
  cross-reference is forward-looking. `/spp-loop`'s G4
  enforcement will inherit the same verdict-with-gate
  pattern established here for G2, applied per-iteration
  to the auditor agent's verdict.
- `DESIGN.md` §3 (canonical command list including this
  one), §10 glossary (gates G2 / G3, sacred test set,
  plan.md as contract — the rule that this command's
  `BASELINE_STATUS` updates and review-note go into
  `plan.md` rather than separate artifacts).
- `CLAUDE.md` §4 (Semantic Commits — applies to changes to
  this command), §5 (PR rules), §8 (auditor information
  isolation — referenced indirectly: this command must not
  expose the test partition to anything that runs later;
  the sacred-test-set guarantee per `DESIGN.md` §10 is
  preserved by this command's "do not read sacred test
  rows" rule in §8).
