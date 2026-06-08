# /spp-init

The first phase in `spp`. Sets up a new task by running the
**designer** agent's consultation, persisting the resulting
`plan.md` and `loop_spec.md`, and waiting at gate G1 for the
user's approval before any downstream phase can run.

> **Note on slash-command notation.** `/spp-init` (and the other
> phase names — `/spp-baseline`, `/spp-loop`, `/spp-finalize`)
> are methodology phase identifiers used internally during a
> `/spp:run` session. Users do not invoke these as separate
> slash commands. The user-facing entry point is `/spp:run
> <task-name>` (or describing a classification task to Claude
> Code, which activates the skill from its `description`
> frontmatter); the agent then walks these four phases in order
> per the docs in this directory. The slash-prefixed naming is
> retained as a stable identifier for cross-references.

This document is the template the other three phases
(`/spp-baseline`, `/spp-loop`, `/spp-finalize`) inherit. The
eight-section structure (identity → invocation → pre-conditions
→ execution flow → gate enforcement → outputs → failure modes →
what-not-to-do) is not negotiable for them; see "Pattern for
subsequent phases" below.

---

## 1. Command identity

`/spp-init` is the consultation entry point: it scaffolds a new
task directory, runs the designer agent against the user's repo
and goals, persists the consultation's output as `plan.md` and
`loop_spec.md`, and stops at gate G1 (`DESIGN.md` §3, §10
glossary).

It produces exactly two files (`plan.md` and `loop_spec.md`)
under `spp/<task_name>/config/`. It does not label data, does
not start the optimization loop, does not create any
`runs/<model>/` directory, and does not touch any file outside
`spp/<task_name>/config/`. Those jobs belong to `/spp-baseline`,
`/spp-loop`, and `/spp-finalize` respectively.

The judgment lives in [`designer.md`](../agents/designer.md)
(the agent). The orchestration and gate enforcement live here
(the command). Editing the consultation logic means editing the
agent doc; editing the filesystem orchestration means editing
this command. The separation is load-bearing — mixing them
produces a system where every change touches both files. Future
contributors should use the file location of a change as the
diagnostic for what kind of change it is.

---

## 2. Invocation

```
/spp-init [<task-name>]
```

**`<task-name>`** is an optional positional argument.

- **Provided:** the command takes the argument verbatim and
  uses it as the directory name under `spp/`. The argument
  must be **kebab-case, lowercase, no spaces, no slashes, no
  leading or trailing hyphens**. These constraints are not
  style preferences; they are filesystem-portability rules
  (`plan.md.template` validation rule 2 enforces them on the
  resulting `TASK_NAME` field). The command rejects an
  out-of-shape argument with a specific error message and
  does not silently rewrite the user's input.

  Example: `/spp-init support-billing-triage` →
  `spp/support-billing-triage/config/`.

- **Absent:** the command begins the consultation and the
  designer asks for a task name as the very first
  consultation question, applying the same kebab-case
  constraint to the user's answer (`designer.md` §1's
  loop_spec note assumes the task name is settled before
  any other field, since the directory cannot be created
  without it).

  Example: `/spp-init` → designer asks "what should I call
  this task?" → user answers `support-billing-triage` →
  `spp/support-billing-triage/config/`.

The argument is not interactive-prompt-able later. If the user
realizes they want a different task name after consultation
has begun, the correct response is to abort, manually rename
the directory if anything was written, and re-invoke. There is
no rename-mid-consultation flow in v1 (`DESIGN.md` §3 task_name
semantics).

**Why no rename-mid-flow:** the task name appears in `plan.md`
§1 (`TASK_NAME`), in the directory path
`spp/<task-name>/config/`, in `loop_spec.md`'s plan reference
and run-directory pattern (`runs/<model_identifier>/run_NN/`
under `spp/<task-name>/`), and eventually in `REPORT.md`'s
artifact paths and SHA-256 verification command. A safe rename
would require coordinated updates across all of these plus
re-validation of the consistency invariants. v1 keeps the
name immutable for the duration of the task; users who need
to rename do it before the consultation has produced any
durable artifact.

---

## 3. Pre-conditions

The command refuses to proceed unless all of the following are
true. Pre-condition failures exit with a specific error message
naming the missing piece, not a generic "something went wrong."

1. **Working directory is the user's project root.** The
   command must run from a directory that looks like a
   project root (contains a `README.md`, `pyproject.toml`,
   `package.json`, or `.git/`). Running from an arbitrary
   subdirectory is rejected because the designer's §3
   reading checklist depends on the repo's top-level
   structure being visible. If detection is ambiguous, the
   command asks the user to confirm.

2. **The `spp` skill is installed.** The command verifies
   that [`designer.md`](../agents/designer.md) and
   `templates/plan.md.template` and
   `templates/loop_spec.md.template` are readable. A missing
   designer agent file is a fatal pre-condition error — the
   command does not attempt to consult without the agent
   doc.

3. **`spp/` is writable** (or doesn't exist yet, in which
   case the parent directory is writable). The command does
   not require write access to any other path; if write to
   `spp/<task_name>/config/` later fails for filesystem
   reasons, that's a step-7 failure (§7), not a
   pre-condition.

4. **Resumption check.** If a `<task-name>` argument is
   provided **and** `spp/<task-name>/config/plan.md` already
   exists, the command treats the run as a resumption rather
   than a fresh task. Resumption is the only safe behavior
   when a partial plan is on disk — clobbering would discard
   the user's prior work. The designer's §6 resumability
   protocol applies: re-read the partial, identify open
   sections (any literal `{{...}}` placeholder remaining),
   resume the consultation from the first open section, and
   never silently overwrite a filled section.

   The user can force a fresh start by deleting the existing
   `spp/<task-name>/` directory before re-invoking; this is
   a deliberate friction.

   **The resumption logic reads the working-tree
   `plan.md` file, not any git index or `HEAD` version.**
   Users who commit between sessions still resume from the
   working-tree state — `git stash`, `git checkout` of a
   prior commit, or a partially-staged file all behave as
   their working-tree contents indicate, not as their
   committed state indicates.

---

## 4. Execution flow

The orchestration sequence. Steps that happen before the user
sees anything are marked **(pre-display)**; steps that involve
back-and-forth with the user are marked **(consultation)**;
steps that happen after gate G1 approval is received are marked
**(post-G1)**.

1. **(pre-display) Parse arguments.** Validate `<task-name>`
   against the kebab-case constraint. Reject with a specific
   error if invalid; otherwise carry forward.

2. **(pre-display) Verify pre-conditions.** Run the §3 checks.
   Exit with a specific error if any fail.

3. **(pre-display) Determine mode.** Fresh vs. resumption,
   per the §3 resumption check. If task name was not
   provided, mode is fresh by definition (no existing path
   to check).

4. **(pre-display) Create the task directory.** Fresh mode
   only: create `spp/<task_name>/config/` if it doesn't
   exist. Resumption mode: assert the directory exists and
   `plan.md` is readable. Either way, no other directories
   (`data/`, `runs/`) are created here — those are downstream
   phases' jobs.

5. **(consultation) Invoke the designer agent.**
   - **Fresh mode:** invoke with the §3 reading-checklist
     context (repo file tree, `data/` headers, project
     metadata, prior `spp/` artifacts, recent git history).
     The designer's first user-visible message is the
     strawman per `designer.md` §4.
   - **Resumption mode:** invoke with the partial `plan.md`
     contents plus a fresh §3 scan (repo state may have
     changed since the prior session). The designer's first
     user-visible message is the resumption summary per
     `designer.md` §6 step 4 ("Resuming the consultation
     for `{{TASK_NAME}}`. Sections already filled: [list].
     Sections still open: [list]. Pick up with [first open
     section]?").

   The command does not interject during consultation. The
   designer drives the back-and-forth; the command's only
   role here is to relay user messages to the agent and the
   agent's outputs back to the user.

   **Resumption-mode contradictions** (the fresh §3 scan
   surfaces facts that contradict the partial `plan.md` —
   e.g. the referenced `data/` file no longer exists, the
   `MODEL_IDENTIFIER` is unset in the environment, the
   `closed_by` column referenced in §6 has been renamed):
   the designer surfaces the contradiction to the user as
   the first message of the resumed session and asks how to
   resolve it (typically: revise the affected `plan.md`
   section with a `PLAN_VERSION` bump per §11 of the plan).
   The command does not adjudicate; the resolution is part
   of the consultation and goes through the designer's
   normal §6 resumability protocol.

6. **(consultation) Persist the designer's output at
   checkpoints.** The command writes the current state of
   `plan.md` to disk **at each consultation pause point** —
   every time the agent yields control back to the user for
   a response. Writes are **atomic**: the command writes to
   `spp/<task_name>/config/plan.md.tmp`, `fsync`s the temp
   file, then renames it to `plan.md`. This guarantees that
   an interrupted session leaves the file in a coherent
   state (either the prior checkpoint or the new one, never
   a mid-write partial). Without atomicity the resumability
   claim is silently broken — a session interrupted
   mid-line would leave the file in a state the resumption
   logic cannot read.

   The file's **correctness** (validation rules) is enforced
   at step 8, not at each checkpoint — partial files with
   unresolved `{{...}}` placeholders are valid intermediate
   states, and the placeholders themselves are the
   resumption marker (`designer.md` §6).

   **Concurrent invocations** of `/spp-init <task-name>`
   from two terminals are not supported in v1; the second
   invocation may see a partial file written by the first.
   Users running long consultations should not background
   them. (No file lock is taken in v1; adding one is roadmap
   if multi-terminal use becomes a real workflow.)

7. **(consultation) Derive `loop_spec.md`.** Once `plan.md`
   has been filled through §10 by the designer, the command
   derives `loop_spec.md` per the model documented in
   `designer.md` §1 ("loop_spec is derived mechanically
   from plan.md"):

   - Mirror fields copy directly: `TASK_NAME`,
     `PLAN_VERSION`, `MODEL_IDENTIFIER`, `SPP_SCOPE`,
     `MAX_ITERATIONS`, `DEV_PLATEAU_THRESHOLD`,
     `OVERFIT_GUARD`, `ADVERSARY_FLAG`.
   - **Literal-string blocks** are filled with their
     non-negotiable values verbatim, regardless of scope:
     - `loop_spec.md` §3: the three lines `auditor:
       per-iteration` / `score_access: forbidden` /
       `frequency_reduction: forbidden`. Always present.
       Always unmodified. The command does not offer them as
       consultation choices.
     - `loop_spec.md` §7: the two lines
       `test_set_access_during_loop: forbidden` /
       `test_set_first_use: /spp-finalize only`. Always
       present, always unmodified.
   - The §4 adversary-boundaries block (non-persistence,
     no-baseline-promotion) is also filled verbatim.
   - **A short follow-up consultation** surfaces the
     run-time mechanics that don't fit naturally into the
     methodology consultation. The command asks these as
     **one batch, not interleaved with §5 methodology
     questions**, because context-switching dilutes both:
     - `API_ENDPOINT` (e.g. `https://api.openai.com/v1`,
       `http://localhost:1234/v1`).
     - `CONCURRENCY` (default 5).
     - `MAX_TOKENS` (default 200 for classification).
     - `TIMEOUT_SECONDS` (default 60).
     - `RETRY_POLICY` (default "3 retries with exponential
       backoff on 5xx and timeout").
     - `TEMPERATURE` (default 0; non-zero requires the user
       to provide a one-line justification, which becomes a
       comment in `loop_spec.md`).
     - `MODEL_DIRECTIVES` (e.g. Qwen `/no_think`; default
       empty; user adds if applicable).
   - For each defaulted field, the command offers the
     default and accepts a one-word "ok" rather than
     re-asking.

   The command presents these as a **single consultation
   block**, formatted as one field per line with the default
   in brackets:

   ```
   Run-time mechanics — accept defaults with "ok", or
   override field-by-field:
     API_ENDPOINT      [https://api.openai.com/v1]:
     CONCURRENCY       [5]:
     MAX_TOKENS        [200]:
     TIMEOUT_SECONDS   [60]:
     RETRY_POLICY      [3 retries, exponential backoff on 5xx and timeout]:
     TEMPERATURE       [0]:
     MODEL_DIRECTIVES  []:
   ```

   A user reply of `ok` accepts all defaults. Any other reply
   is parsed line-by-line; unmentioned fields keep their
   defaults. `/spp-loop`'s analogous run-time block follows
   the same elicitation pattern when it is written
   (`/spp-loop` will surface its dry-run mechanics block this
   way at gate G4).

8. **(consultation) Run validation.** Once both `plan.md`
   and `loop_spec.md` are filled, run all of:

   - `plan.md.template`'s 12 mechanical rules
     (`designer.md` §7).
   - `loop_spec.md.template`'s 10 mechanical rules,
     including the literal-string presence checks for the
     §3 auditor block, the §4 adversary-boundaries block,
     and the §7 sacred-test-set posture block.

   If any rule fails, the command surfaces **specific
   corrections needed** — exact field names, current
   values, expected values — and returns control to the
   designer for the user-facing back-and-forth that will
   resolve them. The plan is not declared complete until
   all rules pass. See §7 below for the failure-mode
   pattern.

9. **(post-validation) Present at G1.** Once validation
   passes, the command shows the user the completed plan,
   names the file paths it has written, summarizes the
   verdict-gated preconditions (under v0.2 — see §5
   below), and explicitly asks for the §9 G1 approval
   phrase recorded earlier in `plan.md`. The exact prompt
   text under v0.2:

   > Plan for `{{TASK_NAME}}` is ready. Validation rules
   > pass. Schema-designer verdict:
   > `{{SCHEMA_DESIGNER_VERDICT}}` (`ready` /
   > `revise` / `not-ready`).
   > {{IF VERDICT != ready: }}§11 override entry: present
   > / missing.
   > To approve and proceed to `/spp-baseline`,
   > reply with the exact G1 approval phrase you recorded
   > in §9: `{{G1_APPROVAL_PHRASE}}`.

   Under K=1 (single-output) the common case is
   `SCHEMA_DESIGNER_VERDICT = ready` and the override-
   entry line is omitted; the prompt then reads
   identically to v0.1.0's. Under K > 1 with a
   `not-ready` verdict, the override-entry line names
   whether `plan.md` §11 carries the literal substring
   `schema-not-ready override` referencing
   `schema-designer`.

   The command **does not advance** until the user
   responds **and** the verdict-gated precondition is
   satisfied. See §5 below for the dual-check
   enforcement pattern.

10. **(post-G1) Print confirmation.** Once the G1 phrase is
    received exactly, the command prints a confirmation
    message naming the two output files and pointing at
    the next command. Exact text:

    > Plan approved at G1. Files written:
    >   spp/{{TASK_NAME}}/config/plan.md
    >   spp/{{TASK_NAME}}/config/loop_spec.md
    > Next step: `/spp-baseline`.

    The command exits cleanly. No further action.

---

## 5. Gate G1 enforcement

The command reads `plan.md` §9's recorded G1 approval phrase
and **refuses to mark the plan as approved** without that exact
phrase from the user. Under v0.2, G1 is a **dual check**:
both the user's approval substring and the `schema-designer`
verdict-gated precondition must be satisfied for the gate to
advance (`DESIGN.md` §7.1.1 sub-skill ordering layer; §10
glossary HITL gate verdict-gated-preconditions addendum). This
is the pattern that subsequent phases' gate enforcements
(G2/G3 in `/spp-baseline`, G4 in `/spp-loop`, G5/G6 in
`/spp-finalize`) will follow; G2 already carries an analogous
precondition for `baseline-quality`.

**The two checks (both must pass for G1 to advance):**

1. **Approval-substring check** (existing v0.1.0 check). The
   user's response is matched literally — see "Match
   semantics" below.
2. **Schema-designer precondition check** (v0.2 addition).
   EITHER `schema-designer`'s most recent verdict for the
   plan is `ready`, OR `plan.md` §11 contains an entry
   whose Reason field contains the literal substring
   `schema-not-ready override` (case-sensitive,
   exact-substring) and references the `schema-designer`
   sub-skill.

**K=1 backward compatibility.** When the user is on the K=1
path and `schema-designer` returned `ready` (the common case
for K=1 OUTPUT_SCHEMAs produced from a familiar single-class
label space), the second check passes without requiring a
§11 override; the gate's behavior is indistinguishable from
v0.1.0's single-check behavior. The override path is
exercised only for `not-ready` verdicts, which are rare for
K=1.

**On a check failure:** the runner refuses to advance and
names which check failed:

- **Approval-substring mismatch** → the §"Match semantics"
  message below.
- **Schema-designer verdict not `ready` and no override
  entry** → "Schema-designer's verdict for this plan is
  `{{VERDICT}}`. To advance G1, either fix the schema
  findings and re-invoke the designer, or record a
  `plan.md` §11 entry whose Reason contains the literal
  substring `schema-not-ready override` and references the
  `schema-designer` sub-skill. Refer to `schema-designer`
  SKILL.md §6 for the override mechanics."

The runner does not silently accept one check while the
other fails. Both must pass; both surface their own
specific mismatch when they don't.

**Match semantics (approval-substring check):**

- The match is **literal string equality after stripping
  leading and trailing whitespace** on the user's response.
  Capitalization is normalized to whatever the recorded phrase
  uses; the recorded phrase's case is authoritative.
- Punctuation matters: if the recorded phrase is `approved,
  proceed to baseline` and the user types `approved!`, the
  command treats it as a non-match.
- Newlines and surrounding text matter: if the user types a
  paragraph that contains the recorded phrase, the command
  treats it as a non-match. The user's response must be only
  the phrase.

**On a non-match (approval substring):** the command does
not guess intent. It surfaces the mismatch with a specific
message:

> That doesn't match the G1 approval phrase recorded in
> §9. Recorded phrase: `{{G1_APPROVAL_PHRASE}}`. You
> entered: `{{USER_INPUT}}`. Either reply with the recorded
> phrase exactly, or, if you want to revise §9 of the plan,
> say "revise §9".

The "revise §9" branch returns control to the designer for a
plan-revision-log update (`plan.md` §11), bumps
`PLAN_VERSION`, and re-runs §4 step 9 from the top with the
new phrase. **The prior G1 phrase is replaced**, not appended:
there is a single G1 approval phrase per plan, latest wins.
The revision history is preserved in `plan.md` §11 (the plan
revision log), with the date, version bump, and reason; if a
user wants to recover a superseded phrase exactly, the file's
git history is the source of truth.

**Why this strictness:** the whole point of recording the
approval phrase in `plan.md` §9 is that the command can check
for it literally. "Approximately matching" approval ratifies
defaults by silence — exactly the failure mode the
recorded-phrase pattern was built to prevent (`DESIGN.md` §10
glossary, HITL gate). A future contributor who proposes a
fuzzy-match flag in the name of UX is proposing to break the
gate; that's a `BREAKING CHANGE:` per the §"Versioning" section
below.

---

## 6. Outputs

**On successful completion, exactly two files exist** and no
others:

| Path | Contents | Validation status |
|---|---|---|
| `spp/<task_name>/config/plan.md` | Fully populated per `plan.md.template`; all 12 mechanical rules pass; G1 approval recorded. | clean |
| `spp/<task_name>/config/loop_spec.md` | Mechanically derived per `designer.md` §1 + the small batched run-time-mechanics consultation (§4 step 7); all 10 mechanical rules pass; literal-string blocks verbatim. | clean |

**The command does not create:**

- `data/` directories or `baseline.csv` (those are
  `/spp-baseline`'s output, after gate G2/G3).
- `splits.json` (also `/spp-baseline`'s output).
- `runs/` or any `runs/<model>/` subdirectory (that is
  `/spp-loop`'s output, after gate G4).
- `prompt_v01.md` or any prompt-versioned file (also
  `/spp-loop`'s output).
- `REPORT.md` or `PROMPT_FROZEN_v01.md` (those are
  `/spp-finalize`'s output, after gates G5/G6).

**Terminal/chat output** (what the user sees, in order):

1. The designer's strawman or resumption summary (§4 step 5).
2. Whatever back-and-forth the consultation produces.
3. The validation status report after step 8 — either
   "Validation rules pass" or specific corrections needed.
4. The G1 prompt at step 9.
5. The confirmation message at step 10 (only after G1 is
   matched).

If the command exits before G1 (validation failure, user
abandonment), the user does not see step 5. The partial
`plan.md` remains on disk for the next `/spp-init` invocation
to resume from.

---

## 7. Failure modes and recovery

The pattern: **failures are loud and specific, never silent or
generic**. Each failure mode below names what the command does
and what the user can do to recover. This is the pattern the
other three phases follow.

| Failure | What the command does | How the user recovers |
|---|---|---|
| Invalid `<task-name>` argument (not kebab-case, contains slashes, etc.) | Exit immediately with `task-name '{{ARG}}' is not valid: must be kebab-case, lowercase, no slashes or spaces. See plan.md.template validation rule 2.` | Re-invoke with a valid argument. |
| Working directory is not a project root | Exit with `current directory does not look like a project root (no README.md, pyproject.toml, package.json, or .git/ found). spp/ tasks scaffold from the user's project root. cd to the right directory and re-invoke.` | `cd` to the project root and re-invoke. |
| Skill files missing or unreadable | Exit with `cannot read skills/run/agents/designer.md (or templates/plan.md.template, etc.). The spp plugin may not be installed. See README installation section.` | Install or repair the plugin, then re-invoke. |
| `spp/<task_name>/config/plan.md` already exists (resumption case) | Treat as resumption per §3 step 4; do **not** clobber. | The user can opt into a fresh start by deleting `spp/<task_name>/` first. |
| Validation rules fail after consultation | Surface specific corrections (field name, current value, expected value or rule reference); return to designer for follow-up. The plan is not marked complete. The on-disk `plan.md` remains in its partially-validated state. | The designer asks the user follow-ups, the user responds, the command re-runs validation. Loops until rules pass. |
| User types a non-matching G1 phrase | Re-prompt with the §5 mismatch message; do **not** advance, do **not** guess intent. | Either retype the phrase exactly, or say "revise §9" to take the plan-revision branch. |
| User abandons consultation mid-way (closes session, types `Ctrl-C` equivalent, walks away) | Partial `plan.md` is preserved on disk. The command exits cleanly without writing a "complete" marker. | Re-invoke `/spp-init <task-name>` to resume per §3 step 4 + `designer.md` §6. |
| Filesystem permission error (e.g. `spp/` is not writable) | Exit with `cannot write to spp/{{TASK_NAME}}/config/: {{OS_ERROR}}. The spp/ directory must be writable from the project root.` | Fix permissions, re-invoke. |
| Designer agent surfaces an unrecoverable consultation error (rare; the user provides contradictory inputs the designer cannot reconcile) | Designer surfaces the specific contradiction; command waits for the user to resolve. The command itself does not adjudicate. | The user resolves the contradiction in the consultation. |

The command never writes a `plan.md` or `loop_spec.md` that
would fail validation if read by a downstream command. If
validation fails after consultation, the on-disk file is the
partial in its current state — clearly incomplete due to
unresolved placeholders — not a "looks complete but is
broken" state. Downstream phases like `/spp-baseline`
re-validate before reading, so the contract is enforced at
both ends.

---

## 8. What `/spp-init` does NOT do

Mirroring `designer.md` §2 ("What the designer does not have"):

- Does not label data. That's `/spp-baseline`'s job, after
  gate G2.
- Does not generate splits. Also `/spp-baseline`'s job,
  after gate G3.
- Does not start the optimization loop, run any iteration,
  or invoke the auditor or adversary agents. That's
  `/spp-loop`'s job, after gate G4.
- Does not run the sacred test set or generate `REPORT.md`
  or `PROMPT_FROZEN_v01.md`. That's `/spp-finalize`'s job,
  after gate G5/G6.
- Does not create any `data/`, `runs/`, or `splits.json`
  artifact.
- Does not modify any file outside
  `spp/<task_name>/config/`. The user's source code, README,
  data files, and any sibling `spp/<other_task>/` task
  directories are not touched.
- Does not read sacred test rows. None exist yet at this
  command's stage, but the rule is stated to set the
  precedent — `/spp-loop`, in particular, must not read test
  rows during iteration (`DESIGN.md` §10 glossary, sacred
  test set).
- Does not parameterize the literal-string blocks during
  loop_spec derivation. The auditor isolation block and the
  sacred-test-set posture block are filled verbatim,
  unconditionally, regardless of the user's scope choice or
  any other consultation answer (`CLAUDE.md` §8).
- Does not commit the produced files to git or run any git
  operation. Persistence to disk is the command's
  responsibility; version control is the user's choice.

---

## Pattern for subsequent phases

`/spp-baseline`, `/spp-loop`, and `/spp-finalize` follow this
same eight-section structure (identity, invocation,
pre-conditions, execution flow, gate enforcement, outputs,
failure modes, what-not-to-do). The structure is not negotiable
for them; revisions to the shape happen here in `/spp-init.md`
and propagate by example.

Specifically:

- **`/spp-baseline`** (Phase 2 step 5+ in the build order)
  enforces gates **G2** (baseline review) and **G3** (split
  confirmation). Invokes the `baseline-quality` sub-skill.
  Outputs `data/baseline.csv` and `data/splits.json` under
  `spp/<task_name>/`. Does not invoke any agent.
- **`/spp-loop`** (Phase 2 step 9) enforces gate **G4**
  (dry-run gate) plus per-iteration auditor invocations.
  Invokes the auditor agent (and optionally the adversary).
  Outputs `runs/<model_identifier>/run_NN/` artifacts plus
  `PROMPT_FROZEN_v01.md` and one of `SUCCESS.md` /
  `EARLY_STOP.md` / `FAILED.md` at termination. Does not
  invoke the designer.
- **`/spp-finalize`** (Phase 2 step 10) enforces gates **G5**
  (finalization) and **G6** (production decision). Invokes
  no agent. Outputs `runs/<model_identifier>/REPORT.md`. Is
  the only command that reads sacred test rows, and reads
  them exactly once (`DESIGN.md` §10 glossary).

When those phases are written, their authors should treat
the eight-section shape and the gate-enforcement strictness
established here as the contract, not the suggestion. Adding
a section, removing a section, or weakening gate enforcement
is a `BREAKING CHANGE:` per the §"Versioning" rule below.

---

## Pipeline mode (v0.11)

When the user adopts a **decomposition** — the `structure-advisor`
`decomposition` recommendation, surfaced during the designer's
feature-group identification (`agents/designer.md`) for a task whose
feature groups need different reasoning patterns — `/spp-init`
produces a **parent pipeline** instead of a single task
(`DESIGN.md` §7.1.12):

- A parent **`pipeline.md`** (from `templates/pipeline.md.template`)
  declaring the node order, the inter-node wiring (which upstream
  output feeds which downstream input column), the composite metric,
  and the sequencing/freezing posture.
- One **normal spp task per node** under `sub-tasks/<node-id>/`, each
  produced by its own `/spp-init` run with its own `plan.md`,
  OUTPUT_SCHEMA, metric, and floor. A node is a single-node task in
  every respect; the pipeline is the parent that orders and wires
  them.

This is the **managed** form of the manual feature-group splitting
practice (`DESIGN.md` §10 glossary); the manual practice — independent
`sub-tasks/` the user coordinates by hand — stays valid and coexists.
It runs under the **same four commands** (invariant #20): `/spp-loop`
optimizes the active node, there is no fifth "pipeline" command. A
single-node task needs **no** `pipeline.md` and is unchanged. The
pipeline arc is **linear chains with node-local gold** only (DAGs and
end-to-end credit assignment are out of scope, §7.1.12).

---

## Versioning

Same rule as for `designer.md`: changes to `/spp-init` that
**alter methodology guarantees** must be flagged as
`BREAKING CHANGE:` in commit messages and trigger a
major-version bump per `CLAUDE.md` §4.

Examples of methodology-affecting (= breaking) changes:

- Loosening gate G1 enforcement (fuzzy-matching the approval
  phrase, advancing on a timeout, accepting any non-empty
  response). The recorded-phrase pattern is what makes the
  gate operational; weakening it weakens the methodology's
  HITL claim.
- **Weakening the v0.2 G1 dual check** — collapsing back to
  approval-substring-only enforcement, accepting a missing
  `schema-designer` verdict as if it were `ready`, or
  loosening the literal-substring requirement on
  `schema-not-ready override`. The dual-check
  operationalizes the schema-designer precondition pinned in
  `DESIGN.md` §7.1.1 sub-skill ordering layer; collapsing it
  would silently advance K > 1 plans whose schema failed
  mechanical-layer validation. The K=1 fallback (where the
  v0.1.0 LABEL_SPACE-based path satisfies the precondition by
  trivially-`ready` schema-designer verdict) is the only
  allowed reduction; removing it would break v0.1.0 backward
  compatibility.
- Allowing the command to write outside
  `spp/<task_name>/config/` (e.g. creating `data/`,
  `runs/`, modifying README). The output scope is part of
  the command's contract with downstream phases.
- Parameterizing the literal-string blocks in
  `loop_spec.md` derivation (auditor isolation,
  sacred-test-set posture). The whole point of the
  literal-string blocks is that they cannot be turned off.
- Removing or weakening the kebab-case constraint on
  `<task-name>` (the constraint is a filesystem-portability
  guarantee that other phases depend on).
- Changing the eight-section structure of this command in a
  way that propagates to subsequent phases.

Examples of behavioral (= non-breaking) changes:

- Better wording in the strawman, validation, or G1 prompts.
- Adding a new pre-condition check that does not change what
  the command outputs.
- Adding a new defaulted field to the loop_spec mechanics
  consultation (e.g. a new `RATE_LIMIT_RPS` field with a
  sensible default), as long as it doesn't change the
  literal-string blocks or the validation rules' set.
- Better error messages on existing failure modes.

When in doubt, treat the change as breaking. The cost of an
extra release-notes paragraph is low; the cost of a silent
methodology break is high.

---

## Cross-references

- [`agents/designer.md`](../agents/designer.md) — the
  consultation agent the command invokes. Specifically: §1
  (identity, plus the loop_spec derivation model the
  command follows in §4 step 7), §3 (reading checklist —
  the designer's, but the command shapes the
  pre-consultation context around it), §6 (resumability —
  the command's resumption mode in §3 step 4 + §4 step 5
  defers to the agent's logic), §7 (validation gate — the
  command runs the agent's mechanical rules in §4 step 8).
- [`templates/plan.md.template`](../templates/plan.md.template) —
  the document the command persists. Validation rules 1-12
  are enforced at §4 step 8.
- [`templates/loop_spec.md.template`](../templates/loop_spec.md.template) —
  the document the command derives. Validation rules 1-10
  are enforced at §4 step 8, including the literal-string
  presence checks for the §3 auditor block, §4 adversary
  boundaries, and §7 sacred-test-set posture.
- `DESIGN.md` §3 (canonical command list), §4.1 (designer
  posture), §4.2 (auditor information isolation — the
  command must not weaken the loop_spec's §3 block during
  derivation), §10 glossary (gate G1, plan.md as contract).
- `CLAUDE.md` §4 (Semantic Commits — applies to changes to
  this command), §5 (PR rules), §8 (auditor score-access
  prohibition — the command must not parameterize the
  loop_spec's literal-string locks during derivation).
