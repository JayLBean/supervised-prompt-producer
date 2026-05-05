# Example — hair-loss-relevance

The canonical worked example shipped alongside `spp` v0.1.0. Demonstrates the
methodology end-to-end on a binary classification task — relevance filtering
for a hair-loss research cohort — run against `gpt-oss-20b-MXFP4-Q8` on a
local mlx server. The loop terminated at iteration 4 by user-initiated
EARLY_STOP after the dev headline criterion (F1 ≥ 0.90) was met but the
remaining failure was a single recurring row; the user judged that one more
iteration risked row-specific patching dressed as categorical edits, and
exercised the methodology's discipline against fitting small-N dev signal.

The point of this example is to show what `spp` produces — what artifacts
each phase emits, what shape the human-in-the-loop experience took. It is not
a tutorial. It is the artifact set itself, sanitized for an NDA-protected
data source, with a brief walkthrough.

## NDA framing

The 100-row baseline is third-party-licensed and is not redistributable. See
[`data/README.md`](data/README.md) for the full sanitization contract and the
schema a future user would use to bring their own data. In short:

- **Data:** the 100 rows themselves are not shipped; only a schema/README
  pointer is.
- **Predictions:** every model prediction's `raw` JSON output (containing a
  rationale that paraphrases post content) is redacted to
  `"[REDACTED — NDA-protected]"`. The parsed binary `predicted` label and the
  `row_id` are kept — those drive the eval and need to be auditable.
- **Prompt example blocks:** each `prompt_v(N).md` and `PROMPT_FROZEN_v01.md`
  carries an `<example_input>` / `<example_output>` block that originally
  showed a real-data row. Every shipped prompt replaces that block with a
  synthetic hair-loss-discourse-shaped example, internally consistent across
  all five files per the skill's `prompt-architect` convention. The persona,
  task, rules, and output-format surface — i.e. the part of the prompt the
  loop actually optimized — is unchanged.
- **Everything else** (eval JSON, auditor reviews, discrepancy analyses,
  REPORT, plan, loop-spec, scripts) is the actual artifact set as the
  methodology produced it, with light editing only where a local user path
  appeared.

## Reading order

To get a feel for the workflow:

1. Start with [`WALKTHROUGH.md`](WALKTHROUGH.md) — a brief narrative
   reconstruction by the user who ran the methodology, conveying the rhythm
   of the human-in-the-loop session.

2. Read the contract: [`config/plan.md`](config/plan.md) and
   [`config/loop_spec.md`](config/loop_spec.md). The plan is the artifact G1
   approved; the loop-spec is the operational pinning. Plan §11 records every
   revision made during the methodology, with rationale.

3. Walk the loop iteration by iteration. For each iteration `N`, the relevant
   trio is at [`runs/gpt-oss-20b-MXFP4-Q8/run_0N/`](runs/gpt-oss-20b-MXFP4-Q8/):
   - `prompt_v0N.md` — the rule surface as it stood that iteration
   - `eval.json` — the dev/train metrics it produced
   - `discrepancy_analysis.md` — the cluster analysis of disagreements
   - `auditor_review.md` (in iter 2's directory onward, reviewing iter N-1's
     edits) — the categorical-vs-row-specific verdicts that gated the next
     iteration's prompt

4. End at the termination + finalization artifacts:
   [`runs/gpt-oss-20b-MXFP4-Q8/EARLY_STOP.md`](runs/gpt-oss-20b-MXFP4-Q8/EARLY_STOP.md)
   (operative — see "Findings" §1 below),
   [`runs/gpt-oss-20b-MXFP4-Q8/REPORT.md`](runs/gpt-oss-20b-MXFP4-Q8/REPORT.md),
   and
   [`runs/gpt-oss-20b-MXFP4-Q8/PROMPT_FROZEN_v01.md`](runs/gpt-oss-20b-MXFP4-Q8/PROMPT_FROZEN_v01.md).

## Findings from the run

Three observations from running the methodology end-to-end. They are recorded
here for Phase 4 polish; they did not feed back into the run's output.

**1. Both `SUCCESS.md` and `EARLY_STOP.md` exist; `EARLY_STOP.md` is operative.**
The plan's v6 revision (relaxing the dev plateau threshold from `<0.005 for 3
consecutive iterations` to `<0.05 for 2 consecutive`, justifiable at N_dev=20)
made the loop's terminal state qualify under both stop conditions
simultaneously. The runner wrote `EARLY_STOP.md` first when the user
manually called the iteration boundary; later, recognizing the plateau
condition was also met under v6, the runner additionally wrote `SUCCESS.md`.
Both are shipped; the operative one is the one matching the user's
in-the-moment reasoning, which was discipline-against-row-specific-patching
(EARLY_STOP). The current spec's lumping of all manual terminations under
EARLY_STOP — user-discipline, overfitting-guard trigger, manual abandon — may
need refinement into sub-types, and the SUCCESS / EARLY_STOP collision under
threshold revision needs an explicit precedence rule. **Forward to Phase 4.**

**2. The run was conducted under the prior methodology (pre-PR-#14).**
PR #14 introduced per-stage information isolation in `/spp-loop` — explicit
allow-lists for the discrepancy, rule-edit, auditor, and adversary subagents.
This run pre-dates that revision. The auditor verdicts (all 7 edits across
iterations 1–3 came back categorical) are consistent with what per-stage
isolation would have produced, and there is no evidence in the artifacts that
row-content leaked into rule-edit reasoning, but the run was not operated
under the strict per-stage discipline that v0.1.0 mandates. A future re-run
of the same task under per-stage isolation would be the better demonstration
of the current methodology; this example documents what the methodology was
*before* PR #14. **Forward to Phase 4** (consider whether to re-run for v0.2
or to keep this as a historical artifact.)

**3. The slash-command notation in `commands/*.md` is naming convention, not
Claude Code syntax.** The user did not type `/spp-init`, `/spp-baseline`, etc.
as slash commands — those four "commands" are skill-internal documentation,
not registered Claude Code slash commands. The user described the task to
Claude Code; Claude Code routed through `SKILL.md` and walked the four phases
documented in `commands/*.md`. The walkthrough reflects this. A future reader
expecting `/spp-init` to work as a literal slash command would be wrong, and
the user-facing docs (`README.md`, `SKILL.md`, the four `commands/*.md`) should
clarify the convention. **Forward to Phase 4.**

## What this example does NOT demonstrate

- Multi-class classification — this is binary.
- Fresh-labeling with `/spp-baseline` — the baseline was hand-labeled outside
  `/spp-baseline` ahead of time; the sub-skill ran the existing-baseline path
  with `BASELINE_STATUS=complete` on entry.
- A `SUCCESS`-typed termination — the operative termination is `EARLY_STOP`
  (see Findings §1).
- A test-set-passing prompt — the frozen prompt's test F1 (0.75) does not
  meet the §3 headline criterion (0.90); REPORT recommends `iterate-further`
  with an expanded baseline. The dev/test gap is itself instructive at
  N_dev=20.
- The adversary sub-agent — `ADVERSARY_FLAG=off` for this run.
- Cross-model robustness — the prompt was optimized against a single locked
  model, per the v1 model-overfitting-documented-not-prevented contract
  (`DESIGN.md` §2.2).

Future examples will demonstrate other shapes (multi-class, fresh-labeling,
SUCCESS termination, adversary on, larger baseline).
