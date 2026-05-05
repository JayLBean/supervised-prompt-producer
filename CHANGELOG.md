# Changelog

All notable changes to `spp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

- Canonical `examples/hair-loss-relevance/` worked example
  demonstrating the `spp` methodology end-to-end on a binary
  classification task (relevance filtering for a hair-loss
  research cohort) run against `gpt-oss-20b-MXFP4-Q8` on a
  local mlx server. The loop terminated at iteration 4 by
  user-initiated `EARLY_STOP` after the dev headline criterion
  (F1 ≥ 0.90) was met but the only remaining failure was a
  single recurring row; the user judged that one more iteration
  risked row-specific patching dressed as categorical edits and
  exercised the methodology's discipline against fitting small-N
  dev signal. The example ships the actual artifact set —
  plan, loop-spec, four iterations of prompt + eval + discrepancy
  + auditor review, REPORT, frozen prompt, and both
  `SUCCESS.md` / `EARLY_STOP.md` (the operative termination is
  EARLY_STOP) — under NDA-driven sanitization: the 100-row
  baseline is not shipped (a `data/README.md` documents the
  schema for future users), every prediction's `raw` model
  output is redacted, and each prompt's `<example_input>` /
  `<example_output>` block is replaced with synthetic
  hair-loss-discourse-shaped content consistent across all five
  prompt files. Persona, task, rules, and output-format — the
  surface the loop optimized — are unchanged. A lean `README.md`
  frames the example and surfaces three findings to forward to
  Phase 4: the `SUCCESS.md` / `EARLY_STOP.md` collision under
  v6 plateau-threshold revision; the run pre-dating the
  per-stage information-isolation revision (PR #14); and the
  slash-command notation in `commands/*.md` being naming
  convention rather than Claude Code syntax. A `WALKTHROUGH.md`
  is a brief narrative reconstruction by the user (not a chat
  transcript) of the human-in-the-loop experience, with the
  iter-4 EARLY_STOP decision as its center.

### Notes

- Phase 3 step 1 (the v0.1.0 worked-example deliverable). Per
  `DESIGN.md` non-goals (§7.1) and the example's lean framing,
  no methodology changes are made in this PR — findings are
  recorded and forwarded to Phase 4. Versioning impact: none.

### Changed

- **`BREAKING CHANGE:` `commands/spp-loop.md` §4 introduces
  per-stage subagent isolation for discrepancy and rule-edit
  steps.** A dogfooding run surfaced a leakage mode: the
  orchestrator was reading disagreed rows during the
  discrepancy step (§4 step 8) and retaining that context
  across the rule-edit step (§4 step 10). Even when the
  persistent `discrepancy_analysis.md` abstracted disagreements
  into clusters, the rule-edit work had access to the
  underlying row content through the orchestrator's
  accumulated context, potentially driving rule generalization
  off specific rows. The auditor caught row-specific edits
  reactively at the verdict stage; this revision makes the
  isolation proactive at every cognitive stage. Three (four
  with adversary) per-stage isolated subagent invocations per
  iteration: discrepancy, rule-edit, auditor, adversary
  (when on). Each has an explicit allow-list of inputs; each
  subagent's context terminates when it returns; the
  orchestrator carries state in files between stages, not in
  its main context.
- **`BREAKING CHANGE:` `agents/auditor.md` §2 reframes the
  auditor as one of several isolated subagents.** The
  auditor's five score-access guarantees remain its specific
  contract; the broader allow-list discipline is now
  consistent across stages. The agent set stays closed at
  three (designer, auditor, adversary) — the discrepancy and
  rule-edit subagents are inlined in `/spp-loop.md` as
  implementation patterns of the orchestration, not
  first-class agents with distinct cognitive roles. The
  auditor's job has subtly shifted: it now reviews edits
  produced under per-stage isolation, which means score-
  driven row-specific patches are *a priori* less likely
  (the rule-edit subagent had no row exposure during
  generation). A row-specific edit reaching the auditor
  under per-stage isolation is now anomalous, not expected.
- **`BREAKING CHANGE:` `scripts/discrepancy.py` output
  structure removes row-content excerpts.** Previous output
  embedded "Raw response" and "Input excerpt" per disagreed
  row. Revised output references rows by ID only with
  predicted/ground-truth labels. The discrepancy subagent
  reads `data/baseline.csv` directly per its allow-list when
  generating cluster analysis; embedding row content in the
  persistent artifact would reintroduce leakage to the
  rule-edit subagent (which receives the artifact as input
  but has no row-content access otherwise). Tests updated to
  assert row content is absent from the persistent artifact.
- **`BREAKING CHANGE:` `templates/REPORT.md.template` §5
  requires per-stage invariant block.** The previous literal
  line `Auditor information-isolation invariant: preserved.`
  is replaced by a five-line block listing the four
  subagents (discrepancy, rule-edit, auditor, adversary) and
  the invariants each preserves. The Phase 4 REPORT linter
  checks for the four sub-statements when each subagent ran
  (the adversary line is conditional on `ADVERSARY_FLAG = on`).
- **`BREAKING CHANGE:` `templates/loop_spec.md.template` §3
  expands auditor block to per-stage block.** Previously
  three lines (auditor / score_access / frequency_reduction);
  now nine lines covering discrepancy, rule-edit, and
  auditor configurations. The literal-block check in
  `commands/spp-loop.md` §3 pre-condition 4 is updated to
  match.
- **`BREAKING CHANGE:` `DESIGN.md` §4.2 retitled to
  "Per-stage information isolation (the load-bearing design
  lock)"** and restructured to enumerate four isolated
  subagents (discrepancy, rule-edit, auditor, adversary)
  with one paragraph each on their distinct information-
  access contract. The auditor's score-access prohibition
  is now framed as the most stringent specific instance of
  the broader pattern, not the unique design lock.
- **`BREAKING CHANGE:` `CLAUDE.md` §8 expanded from auditor-
  score-access prohibition to per-stage information
  isolation rule.** The expanded rule covers discrepancy
  subagent prior-iteration access, rule-edit subagent row-
  content access, auditor score access, and adversary
  guarantees. Each is explicitly named as `BREAKING CHANGE:`
  if loosened.

### Notes

- Agent set unchanged (designer, auditor, adversary). The
  discrepancy and rule-edit subagents are inlined in
  `commands/spp-loop.md`, not separate agent docs.
- Sub-skill set unchanged (metric-design, baseline-quality,
  prompt-architect).
- Command, template counts unchanged.
- Gate count and shape unchanged (G1–G6).
- `/spp-init`, `/spp-baseline`, `/spp-finalize` unchanged.
- `scripts/split.py`, `scripts/inference.py`, `scripts/eval.py`
  unchanged.
- `README.md` updated to use "per-stage information
  isolation" framing, naming the discrepancy / rule-edit /
  auditor sub-agents that operate the discipline.

Phase 2.5 ships under PR title
**feat(scripts): add runnable substrate for /spp-loop and
/spp-finalize execution**, targeting `dev`. Phase 1 and Phase
2 (steps 1–11) already merged. Infrastructure-only PR; no
methodology changes.

### Added

- Phase 2.5 — runnable substrate at
  `.claude/skills/spp/scripts/`. Four Python scripts that
  operationalize the abstract execution flows specified
  across Phase 2's commands: `split.py` (stratified
  train/dev/test split per `commands/spp-baseline.md` §4
  step 9), `inference.py` (async OpenAI-compatible
  inference per `commands/spp-loop.md` §4 step 6),
  `eval.py` (metric computation per §4 step 7),
  `discrepancy.py` (discrepancy-analysis skeleton per §4
  step 8 — the aggregate-patterns section is left empty
  for the orchestrating LLM to populate). Each script is
  invokable as a CLI (`python -m
  .claude.skills.spp.scripts.<name>`) and importable
  (orchestration imports primitives directly; no
  subprocess error-handling complexity).
- Shared helpers: `_io.py` (atomic write helpers — tmp +
  fsync + rename per `/spp-loop.md` §4 discipline) and
  `_schemas.py` (Pydantic models for SplitsJSON,
  ResultsJSON, EvalJSON, validating every output before
  write).
- 26 smoke tests at `.claude/skills/spp/scripts/tests/`
  covering all four scripts. Tests run without API
  access (the inference test mocks the OpenAI client);
  pytest passes under `spp-dev`.
- `scripts/README.md` indexing the four scripts with
  CLI invocation examples and cross-references to the
  canonical schema docs in commands/.

### Notes

- Infrastructure-only; no agent / command / sub-skill /
  template / top-level doc changes. The scripts
  implement schemas already specified in Phase 2; no new
  methodology.
- No new dependencies. All imports are drawn from
  `environment.yml`'s existing pins (`pandas`, `numpy`,
  `scikit-learn`, `openai`, `pydantic`).
- Retry logic in `inference.py` is implemented manually
  with `asyncio.sleep` + exponential backoff + jitter
  rather than via `tenacity` (not in
  `environment.yml`); behavior is equivalent for the
  policies the `/spp-loop` `RETRY_POLICY` field
  encodes.

Phase 2 step 11 ships under PR title
**feat(skill): add top-level SKILL.md router and close
Phase 2**, targeting `dev`. Phase 1 and Phase 2 steps 1–10
already merged.

### Added

- Phase 2 step 11 — the top-level **`SKILL.md` router** at
  `.claude/skills/spp/SKILL.md`. The routing entry point
  for `spp` at the Claude Code skill level. When a user
  invokes any of the four commands, Claude Code reads
  this document first to understand what `spp` is, what
  it produces, and where the canonical detail for each
  component lives.
- Six-section structure appropriate to a router-shaped
  artifact (not the agent/sub-skill six, not the
  command eight): identity → methodology diagram →
  artifact taxonomy → where to start → load-bearing
  properties → what `spp` is NOT.
- §2 ASCII diagram showing the four phases, four
  commands, and six gates at a glance. Tighter than
  README's mermaid pipeline diagram; covers the same
  shape.
- §3 artifact taxonomy with three subsections (commands,
  agents, sub-skills) plus a fourth for templates.
  Each entry is a one-line description with a link to
  canonical detail. The taxonomy explicitly notes the
  v1 closure of each set: 4 commands, 3 agents, 3
  sub-skills.
- §4 three-paragraph orientation for distinct
  audiences: users new to `spp` (read README and
  DESIGN first), users with a classification task
  (`/spp-init` then follow pre-conditions), and Claude
  Code reading this skill (canonical detail lives in
  the commands' docs; if router and command appear to
  disagree, trust the command).
- §5 enumeration of the methodology's load-bearing
  properties (auditor information isolation, sacred
  test set, verdict-enforced gates, plan.md as
  contract, six-section prompt structure, literal-
  string gate approval, methodology-affecting changes
  as `BREAKING CHANGE:`). Each property is one
  sentence with a pointer to the canonical statement
  — the router does not re-derive properties; it
  points at where they live.
- §6 brief enumeration of out-of-scope concerns (not
  an automated optimizer, not generation, not
  multilingual, not multi-judge, not mid-iteration
  resumption, not cross-model synthesis, not a
  prompt-injection-defense tool). References
  `DESIGN.md` §7.1 as the canonical non-goals list.
- §"Versioning" enumerates a lighter list than the
  methodology-affecting artifacts because the router is
  mostly a directory. Breaking changes include
  removing artifacts from the taxonomy without
  updating `DESIGN.md`, misrepresenting any
  load-bearing property in §5, and adding routing
  logic that duplicates canonical artifacts' decision
  criteria (the router's failure mode is drift from
  the canonical detail it points at).
- YAML frontmatter (`name`, `description`) so Claude
  Code surfaces the skill correctly.

### Changed

- **Phase 2 is now structurally complete.** The v1
  implementation has 4 commands (`/spp-init`,
  `/spp-baseline`, `/spp-loop`, `/spp-finalize`), 3
  agents (`designer`, `auditor`, `adversary`), 3
  sub-skills (`metric-design`, `baseline-quality`,
  `prompt-architect`), 4 templates (`plan.md`,
  `loop_spec.md`, `prompt_v01.md`, `REPORT.md`), 1
  router (this `SKILL.md`), and supporting fixtures.
  Plus the top-level project docs from Phase 1
  (DESIGN.md, CLAUDE.md, README.md, CHANGELOG.md,
  CONTRIBUTING.md, CODE_OF_CONDUCT.md, environment.yml,
  LICENSE, .gitignore). Phase 3 (worked examples)
  follows: three illustrative examples — binary
  canonical (skeleton with dummy data per
  `DESIGN.md` §7.2), multi-class, edge-case-
  imbalanced — demonstrating the methodology
  end-to-end. Phase 3's design challenge is
  illustrative rather than architectural; the
  patterns are settled.

- Phase 2 step 10 — the **`prompt-architect`** sub-skill at
  `.claude/skills/spp/sub-skills/prompt-architect/SKILL.md`,
  the third and final v1 sub-skill. Six-section structure
  inheriting from `metric-design` and `baseline-quality`
  (identity → decision → decision tree → worked examples →
  cross-skill constraint → output spec). Read by the
  designer agent during `/spp-init` consultation, by Claude
  during `/spp-loop` when generating discrepancy analysis
  and applying rule edits, and by users wanting to
  understand the prompt-architecture rationale.
- The sub-skill's role is **structural reference**, not
  content prescription or quality judgment. It explains
  the six-section XML template's structural roles, when
  each section is initially populated and by whom, what
  evolves across iterations, and how the structure
  integrates with the methodology's other components. The
  doc is intentionally shorter than `baseline-quality`
  (no verdict-enforcement; informational reference) and
  resists the temptation to prescribe persona length, rule
  wording, or example shape — those are the auditor's job
  (per `<rules>` edit) and the metric's job (per
  iteration). `prompt-architect` is the structural layer
  beneath both.
- §3 specifies the **section walk** — per section
  (`<persona>`, `<task>`, `<rules>`, `<output_format>`,
  `<example_input>`, `<example_output>`): structural role,
  initial population (who and when), evolution across
  iterations, methodology interaction. Plus model-specific
  directives (header, outside the six-section body) for
  completeness. The asymmetry — `<rules>` evolves
  constantly while the other five sections evolve rarely
  — is intentional: the loop optimizes rules; the rest of
  the prompt is the loop's stable context. A summary table
  documents the auditor's default verdict for each
  section's edits.
- §4 worked examples cover five scenarios: the happy-path
  `<rules>` evolution, a row-specific patch caught at the
  auditor (the methodological defensive function), a
  `<persona>` change as methodology event, an
  `<output_format>` change mid-loop with two valid
  resolution paths, and a refusal scenario where proposed
  content ("try to be balanced and avoid biased outputs")
  doesn't fit any section's role and the sub-skill
  recommends one of three revision paths rather than
  silently accepting the misfit. The refusal posture is
  the discipline.
- §5 cross-skill constraint codifies the **six-section
  discipline as non-negotiable**: structure is fixed,
  iterations refine content within sections but do not
  add or remove sections. Rules out few-shot prompts,
  separate chain-of-thought sections, tool-use prompts,
  free-form prompts that don't fit the XML structure.
  Allows section content variation, model-specific
  directives at the header (outside the body), and
  iteration-driven `<rules>` evolution under auditor
  governance.
- §6 output spec — the sub-skill outputs structural
  guidance (section identification, populate-or-leave-
  alone judgment, audit-surface awareness, revision
  recommendation when content doesn't fit), not content,
  not verdicts, not scores. The sub-skill is the **first
  v1 sub-skill without verdict-enforcement authority** —
  `metric-design` produces a one-shot decision at
  consultation time, `baseline-quality` has gate teeth
  via its three-tier verdict, `prompt-architect` is purely
  informational. The structural discipline lands at the
  template-validation and auditor-review layers; this
  sub-skill does not need gate teeth of its own.
- §"Versioning" enumerates the breaking-change list:
  removing or adding sections to the six-section
  structure, allowing few-shot prompts, allowing silent
  acceptance of misfit content (the refusal posture is
  the discipline), removing the input/output
  correspondence requirement, allowing the sub-skill to
  start outputting content prescriptions, allowing
  `<rules>` edits to bypass the auditor.

### Changed

- The **v1 sub-skill set is now closed at three**:
  `metric-design` (which metric to optimize),
  `baseline-quality` (whether the baseline is ready to
  optimize against), `prompt-architect` (how the prompt's
  structure operates across the methodology). Each
  justified by a structurally distinct decision. Adding
  a fourth requires answering the same kind of
  distinctness question the agent set's closure raised:
  what decision does this sub-skill help make that none
  of the existing three does? The bar is high.

- Phase 2 step 9 — the **`/spp-finalize`** command at
  `.claude/skills/spp/commands/spp-finalize.md`, the fourth
  and final command in `spp` and the methodology's capstone.
  Runs Phase 3: reads the sacred test set exactly once,
  computes test-set metrics, identifies persistent failure
  clusters, generates `REPORT.md` per
  `templates/REPORT.md.template`, freezes the production
  prompt as `PROMPT_FROZEN_v01.md`, enforces gates G5
  (finalization) and G6 (production decision), closes the
  methodology's lifecycle.
- Eight-section structure inherited from `/spp-init`,
  `/spp-baseline`, and `/spp-loop`. Structurally simpler
  than `/spp-loop` (no iteration management) but
  comparably rigorous on the single resource that
  matters: the sacred test set.
- The **sacred-test-set discipline** is operationalized
  through layered defenses. (i) Pre-condition 8 refuses
  to re-finalize when `REPORT.md` exists; the user must
  manually delete four named artifacts and record a §11
  re-finalization reason — deliberate friction makes the
  methodology consequence visible. (ii) Pre-condition 6
  refuses to advance on `EARLY_STOP.md` or `FAILED.md`
  termination types with termination-type-specific
  recovery guidance; finalization is for `SUCCESS.md`
  loops only. (iii) §4 step 3's partial-deletion-on-
  failure rule distinguishes I/O failure (recoverable —
  delete partial `test_results.json` and re-read from
  scratch) from methodology violation (not recoverable —
  the user has seen scores incrementally). (iv) The
  resumption carve-outs at pre-condition 8 honor prior
  G5 / G6 halt state without re-reading the test set;
  the runner detects existing `test_eval.json` or
  `REPORT.md` and skips the stages they correspond to.
- §4 step 3 specifies positive-enumeration construction
  of the inference input set from `splits.json`'s
  `row_ids.test` array — never "all rows minus train and
  dev." Same allow-list pattern as `/spp-loop` §4 step 6
  applied to the test partition (which `/spp-loop`
  excluded; this command includes, exactly here).
- §4 step 7 specifies the **deterministic decision tree**
  for the draft recommendation in REPORT §6
  (`ship` / `ship-with-caveats` / `do-not-ship` /
  `iterate-further`). Inputs: test metric vs. headline
  criterion, persistent failure clusters'
  anticipation in `BASELINE_QUALITY_NOTE`, and
  `train_test_delta` vs. `dev_test_delta`. Same inputs
  always produce the same recommendation; the user
  revises at G6 if they disagree. An LLM-judgment-based
  recommendation was considered and rejected for v1 —
  predictability and auditability beat nuance for the
  ship decision.
- §5 specifies the **G6 structured-branch gate** as a
  justified departure from the binary G1-G5 pattern.
  Three branches: approve as drafted (record `G6
  approved` substring entry in `plan.md` §11); revise
  recommendation (literal-prefix match on `revise
  recommendation to {VALUE}` plus a justification
  paragraph; runner updates REPORT §6 in place and re-
  prompts for G6); halt (preserve REPORT and frozen
  prompt without writing §11 entry; resumption goes
  directly to G6). The recommendation enumeration is
  fixed at four values; expanding is `BREAKING CHANGE:`.
- §4 step 10 surfaces the **`iterate-further`
  pedagogical message** explicitly: continuing to
  iterate against the same test partition would silently
  invalidate the methodology's claim against baseline
  overfitting. The fresh-start recommendation is not
  optional advice — it is what the discipline requires.
- §4 step 7 §5 of REPORT requires the literal line
  **"Auditor information-isolation invariant:
  preserved."** — emitted unconditionally as the
  methodology's traceable assertion that the design
  lock was honored across the loop's lifecycle. Removing
  the line is `BREAKING CHANGE:`; absence is itself a
  methodology breakage signal.
- §7 failure-mode table covers 13+ specific shapes
  including the one-shot test-read discipline at
  multiple resumption surfaces. Resumability discipline
  distinguishes three surfaces: test-completed-G5-halted,
  REPORT-generated-G6-halted, test-failed-mid-run. The
  first two skip the test-set read; the third deletes
  the partial artifact and re-reads from scratch.
- §"Versioning" enumerates the project's most
  methodologically-load-bearing breaking-change list.
  Reading the test set more than once per lifecycle,
  advancing on non-`SUCCESS.md` terminations, removing
  the partial-deletion rule, allowing re-finalization
  without manual deletion, expanding the recommendation
  enumeration, removing the literal invariant-preserved
  line in REPORT §5 — each silently invalidates an
  upstream claim. When in doubt, treat the change as
  breaking.

### Changed

- The **v1 command set is now closed at four**:
  `/spp-init` (consultation), `/spp-baseline` (labeling
  and splits), `/spp-loop` (optimization),
  `/spp-finalize` (test-and-ship). The four commands
  map cleanly to the methodology's four phases. Adding
  a fifth command requires answering the structural
  question that `DESIGN.md` §3 establishes — what
  cognitive or orchestration job does the new command
  do that none of the existing four does? The bar is
  high; a fifth phase would require a methodology
  change, and the methodology is settled per
  `DESIGN.md`. Future PRs proposing a fifth command
  must include a `DESIGN.md` revision in the same PR
  per `CLAUDE.md` §5.

- Phase 2 step 8 — the **`/spp-loop`** command at
  `.claude/skills/spp/commands/spp-loop.md`, the third command
  in `spp` and the largest. Runs Phase 2 of the methodology:
  the optimization loop, integrating the contractual
  obligations from the auditor agent (5 operational
  enforcement guarantees), the adversary agent (4 operational
  contract guarantees), `/spp-baseline`'s verdict-enforced
  gate pattern (applied per-iteration, per-edit), and the
  literal-string methodology blocks in
  `loop_spec.md.template` (§3 auditor configuration, §4
  adversary boundaries, §7 sacred-test-set posture).
- Eight-section structure inherited from `/spp-init` and
  `/spp-baseline`. What is structurally new: iteration
  management (bounded loop with per-iteration artifacts
  under `runs/<model_identifier>/run_NN/` and explicit
  resumability), multi-agent orchestration in a single
  command (auditor every iteration, adversary optionally),
  per-iteration verdict-enforced gate (the third instance
  of the pattern in `spp`).
- §3 pre-conditions include the **`loop_spec.md` literal-
  block check** — the runner refuses to start when any of
  §3 / §4 / §7's literal blocks have been hand-edited.
  This is the runner's defense against silent methodology
  weakening (a future user or contributor removing the
  auditor isolation block to "speed up" the loop hits a
  hard refusal here).
- §3 pre-condition 5 resolves the architectural open
  question raised in `/spp-baseline` PR review:
  `loop_spec.md`'s `PLAN_VERSION` is **derivation
  provenance**, not a live pin. The runner surfaces the
  mismatch and offers two resolution paths (re-derive
  loop_spec, or add a `loop_spec re-validated` entry to
  `plan.md` §11).
- §4 execution flow has 16 steps in three layers (pre-loop,
  iteration, post-loop). Iteration ordering is contractual:
  edit → score → audit, with the adversary slotted between
  discrepancy generation and auditing. Reordering is
  `BREAKING CHANGE:` per §"Versioning".
- §4 step 2 introduces a **forbidden-set defense-in-depth
  posture** for the test partition — the runner constructs
  inference input sets by positive enumeration from train
  + dev row IDs, never as "all rows minus test." A runner
  sanity check verifies test row IDs are not in the
  inference input set; failure is a hard refusal, not a
  silent recovery.
- §4 step 11 specifies the auditor's allow-list inputs
  with concrete file paths, operationalizing the abstract
  contract in `agents/auditor.md` §2: prior + next prompt,
  prior discrepancy, `plan.md` §2 string slice, all prior
  `auditor_review.md` files. The runner builds this list
  explicitly and passes only the named files; future
  contributors should see a literal allow-list, not a
  deny-list.
- §4 step 12 specifies the per-iteration verdict-enforced
  gate. Categorical edits advance silently (the gate is
  invisible in the happy path); row-specific and unclear
  edits require an `auditor override` substring entry in
  `plan.md` §11 with a timestamp post-dating the auditor
  invocation. Without the override, the runner reverts the
  edit (rolling back the specific change while keeping
  categorical edits in the same iteration). Per-edit
  granularity, not per-iteration.
- §4 step 13 specifies three stop conditions evaluated in
  order: dev plateau (improvement over last K iterations
  below threshold), overfitting guard (`train_metric -
  dev_metric > OVERFIT_GUARD` for two consecutive
  iterations — the load-bearing failure mode is baseline
  overfitting per `DESIGN.md` §2.1), max iterations.
- §4 step 15 specifies the three termination artifact
  types and the schema each follows. `SUCCESS.md` requires
  both dev-plateau termination *and* the best iteration's
  metric meeting the headline criterion in `plan.md` §3.
  A loop that plateaus below the headline criterion writes
  `FAILED.md`, not `SUCCESS.md` — the runner does not
  silently mark success on an under-performing loop.
- §5 gate enforcement — two distinct patterns. G4 dry-run
  gate inherits the literal-string-equality match from
  G1 / G2 / G3. The per-iteration auditor verdict gate is
  the **third instance** of the verdict-enforced gate
  pattern: the verdict adds a literal override-substring
  check on top of the iteration's normal advancement; the
  runner reverts non-categorical edits in the absence of
  the override. The gate is invisible in the happy path
  and becomes visible only when a non-categorical verdict
  appears.
- §6 outputs include the run-directory layout, `plan.md`
  §11 update conditions (only `auditor override` and
  `loop_spec re-validated` entries are written by this
  command), and an explicit list of artifacts the command
  does **not** create (REPORT.md, PROMPT_FROZEN_v01.md,
  modified baseline.csv or splits.json, anything outside
  `runs/<model_identifier>/`).
- §7 failure-mode table covers 14+ specific failure
  shapes, each with the loud-and-specific exit pattern.
  Resumability discipline distinguishes complete iteration
  directories (all five artifacts present, skipped on
  resume) from partial directories (some present, surfaced
  to the user with a three-choice prompt — no silent
  recovery).
- §"Versioning" enumerates the project's longest
  breaking-change list. Loosening any of the auditor's
  five operational enforcement guarantees, the adversary's
  four operational contract guarantees, the sacred-test-
  set guarantee, the loop_spec literal-block check, the
  per-iteration verdict gate, the iteration ordering, or
  the runner sanity check on test row IDs is
  `BREAKING CHANGE:`. The methodological discipline
  hinges on this command's operational embodiment of the
  contracts the prior PRs established.

- Phase 2 step 7 — the **adversary** sub-agent at
  `.claude/skills/spp/agents/adversary.md`, the third and
  final v1 agent and the only one that is **opt-in** (gated
  on `ADVERSARY_FLAG = on` in `plan.md` §8 and
  `loop_spec.md` §4; off by default). Six-section structure
  inheriting from `designer.md` and `auditor.md`. The agent
  reads the current iteration's prompt and the prior
  iteration's discrepancy analysis, generates 2 or 3
  synthetic adversarial rows targeting likely blind spots,
  and surfaces them inline in the iteration's
  `discrepancy_analysis.md`. The synthetic rows are not
  persisted, not added to the baseline, not promoted to
  splits, and not scored.
- Forward-looking adversarial reasoning ("where would this
  prompt fail on data it has not seen?") in contrast to the
  auditor's backward-looking categorical reasoning. Same
  structural shape, different direction. Posture closer to
  red-team than code reviewer; informational rather than
  authoritative — the adversary produces no verdict and
  gates nothing.
- Information-access surface in §2: the adversary sees the
  current prompt, the prior iteration's discrepancy
  analysis, and `plan.md` §2 class definitions. It does
  **not** see scores, the sacred test set, or the labeled
  baseline. Score-blindness and test-set-blindness are
  load-bearing (same reasons as the auditor's); baseline-
  blindness is reinforcing discipline that keeps the
  generation from-the-rules rather than from copied real
  data.
- Non-persistence boundary made auditable through a
  literal-string header line at the top of the adversary's
  output: `Adversarial rows — generated for iteration N.
  Not persisted, not added to baseline, not promoted to
  splits.` The Phase 4 linter will check for this exact
  line in iterations where `ADVERSARY_FLAG = on`. Removing
  or rewording the line is `BREAKING CHANGE:` per
  §"Versioning".
- Generation pattern in §4: 2 or 3 synthetic rows per
  iteration, no more. Each row targets a categorical
  pattern from the prompt's rules (a row that satisfies a
  rule's literal condition while violating its intent), is
  realistic but not copied, and carries a plain-English
  annotation naming the rule probed, the user's intuitive
  label, and why the prompt would likely mislabel. The
  adversary does not predict the prompt's actual output on
  the synthetic rows — predicting would create scoring
  pressure and convert the agent from informational to
  evaluative.
- §5 establishes a deliberate departure from the auditor's
  strict determinism: the adversary's generation is
  intentionally non-deterministic within the constraints
  of "2-3 rows targeting blind spots." Re-invocation
  yielding different probes is signal (multiple blind
  spots), not failure. One invocation per iteration; the
  runner does not silently re-invoke.
- §6 operational contract for `/spp-loop` (Phase 2 step 8)
  mirrors the auditor's structure with a smaller surface:
  fixed allow-list of inputs, no score artifacts even if
  present, no persistence of synthetic rows beyond the
  iteration's `discrepancy_analysis.md`, one invocation
  per iteration gated on `ADVERSARY_FLAG`.
- "Pattern observations" section names the v1 agent set as
  **closed**: designer (consults user), auditor (reviews
  edits), adversary (probes blind spots). Each justified
  by structurally distinct information access. Adding a
  fourth agent requires answering the question
  `DESIGN.md` §4 establishes — what unique information or
  posture does the agent have that none of the existing
  three do? The bar is high.
- Two fixtures at
  `.claude/skills/spp/agents/adversary/fixtures/`
  (binary-classification-clear-rules and
  multi-class-with-subtle-distinctions). Two fixtures, not
  three, because the adversary has one job (generate
  adversarial rows from a prompt) and varies primarily by
  task shape. Each fixture: `inputs/prompt_v_N.md`,
  `inputs/discrepancy_analysis.md`,
  `inputs/plan_section_2.md`,
  `expected_adversarial_rows.md` (illustrative, not strict,
  given §5's intentional non-determinism), and
  `consultation_notes.md`. No fixture references real
  source-project data (`DESIGN.md` §7.2).
- Versioning section: methodology-affecting (= breaking)
  changes include persisting synthetic rows to any tracked
  artifact, adding scoring of synthetic rows, removing the
  literal non-persistence header line, removing the
  score-blindness or test-set-blindness constraint,
  allowing baseline access, adding verdict or gate
  authority to the adversary, and removing the bound on
  the number of synthetic rows. The breaking-change list
  is shorter than the auditor's because the adversary has
  fewer load-bearing constraints, but the items that *are*
  breaking are non-negotiable.

- Phase 2 step 6 — the **auditor** sub-agent at
  `.claude/skills/spp/agents/auditor.md`, framed as the
  **single highest-leverage component** in `spp` and the
  design lock that distinguishes the methodology from
  automated optimizers like DSPy / GEPA / APE
  (`DESIGN.md` §4.2). Six-section structure inheriting from
  `designer.md`. The agent reviews proposed prompt-rule
  edits per iteration of `/spp-loop` and returns a per-edit
  verdict (`categorical` / `row-specific` / `unclear`) plus
  an `auditor_review.md` document.
- Information-isolation property documented as the agent's
  defining property in §2. The auditor sees the prompt diff
  between iteration N-1 and N, the prior iteration's
  discrepancy analysis, `plan.md` §2 class definitions, and
  prior auditor reviews. The auditor does **not** see the
  new iteration's scores, post-edit evaluation outputs,
  train/test labels, or sacred test rows. The
  `DESIGN.md` §4.2 "future contributors will be tempted"
  warning paragraph is **lifted verbatim** into §2 because
  the wording is calibrated to anticipate the specific
  rationalization that breaks the design lock.
- §2 operational-enforcement subsection specifies what
  `/spp-loop` (Phase 2 step 8) must guarantee for the
  isolation property to hold: input construction from a
  positive allow-list (not a deny-list), no score
  artifacts in invocation context even though they exist
  on disk, stateless invocations across iterations, no
  score-derived "auditor hints," no test-set artifacts.
  The auditor doc pre-specifies the runner contract so the
  runner author has a clear interface and the agent is not
  left in a "maybe the runner will get this right"
  posture.
- §4 judgment pattern — the auditor's single question
  (categorical or row-specific?) and the **synthetic-rows
  test** that operationalizes it: imagine 5 hypothetical
  rows that satisfy the rule's stated condition; if the
  rule's predicted label applies correctly to all 5, the
  rule generalizes (categorical); if only the original
  motivating row satisfies the rule's exact wording, the
  rule is row-specific. The `unclear` verdict is the
  third option for cases where honest judgment requires
  user input — load-bearing, not a nice-to-have.
- §6 validation-gate output spec — the auditor produces a
  per-edit verdict (hard token, never confidence-weighted)
  and an `auditor_review.md` file with header, per-edit
  sections (edit text, verdict, reasoning including the
  synthetic-rows test, recommendation, generalization
  hints when applicable), and a cross-iteration-check
  section. The auditor does not silently advance any
  edit; non-categorical verdicts halt advancement until
  resolved.
- Three task fixtures at
  `.claude/skills/spp/agents/auditor/fixtures/`:
  - **`clean-categorical-edit/`** — happy-path categorical
    edit (third-party billing context rule). Validates the
    auditor recognizes well-formed categorical rules and
    returns `categorical` / `keep`.
  - **`row-specific-patch-disguised-as-rule/`** — the
    auditor's primary defensive function. A rule whose
    stated condition (literal-phrase match on "telemetry
    breadcrumb redirect") only the single motivating row
    satisfies. Validates the synthetic-rows test catches
    dressed-up patches; auditor returns `row-specific` /
    `generalize` with a hint at the categorical rule the
    next discrepancy analysis should articulate.
  - **`cross-iteration-contradiction/`** — the auditor's
    cross-iteration reasoning. An iteration-5 edit reverses
    a categorical rule that iteration 2's auditor approved;
    standing alone the new edit looks categorical, but the
    cross-iteration check (§3 step 4) surfaces the
    contradiction. Validates `unclear` / `clarify` shape
    with three resolution options for user (protocol
    change, mis-labeling, or genuine ambiguity).
  Each fixture contains `inputs/` (prompt_v_prev,
  prompt_v_next, discrepancy_analysis, plan_section_2,
  optionally prior_auditor_review_run_M for cross-iteration
  fixtures), an `expected_review.md`, and
  `consultation_notes.md` describing the scenario's
  defining properties.
- Versioning section names score-related changes,
  verdict-token-vs-confidence changes, removing the
  `unclear` option, removing the cross-iteration check,
  allowing the auditor to propose new edits, removing the
  per-edit verdict requirement, loosening the §2 input
  allow-list, and softening the verbatim warning paragraph
  as `BREAKING CHANGE:` under stronger-than-default
  language. The auditor is the most version-sensitive
  component in the project because score access and
  verdict-token-vs-confidence are silent failure modes.
- Post-PR-review revisions (single follow-up commit
  `fix(auditor): expand cross-iteration check to scope
  changes, name confidence as forbidden in output spec`):
  - **§3 step 4 cross-iteration check** now explicitly
    covers three modification cases: **direct
    contradiction** (rule reversed), **scope narrowing**
    (rule modified more restrictively, e.g., added
    conjunction), and **scope broadening** (rule
    modified more loosely, e.g., removed conjunction).
    All three trigger at-minimum `unclear` verdicts.
    Refinement disguises drift more effectively than
    reversal does; the expanded check catches both
    obvious contradictions and the subtler refinement-
    style drifts.
  - **§6 "What the auditor does not produce"** now
    explicitly names `auditor_confidence` as forbidden in
    the verdict output. The constraint was already in
    §"Versioning" but should be encounterable in the
    output spec too — a contributor designing the output
    schema should hit the prohibition there, not only
    when reading the breaking-change list.

Phase 2 step 5 ships under PR title
**feat(commands,sub-skills): scaffold /spp-baseline +
baseline-quality with verdict-enforced gate**, already merged.

### Added (Phase 2 step 5, already merged)

- Phase 2 step 5 — the `baseline-quality` sub-skill at
  `.claude/skills/spp/sub-skills/baseline-quality/SKILL.md`,
  framed as the **primary defense against baseline
  overfitting** (`DESIGN.md` §2.1's deal-breaker failure
  mode). Six-section structure inheriting from
  `metric-design`'s pattern lock. The sub-skill produces a
  three-tier verdict (`ready` / `revise` / `not-ready`)
  plus a `BASELINE_QUALITY_NOTE` paragraph for `plan.md` §6
  and a specific findings list naming row IDs and
  class-definition issues that need user action.
- Phase 2 step 5 — the `/spp-baseline` command at
  `.claude/skills/spp/commands/spp-baseline.md`. Eight-
  section structure inheriting from `/spp-init`. Two gates
  (G2 baseline review, G3 split confirmation) with the
  literal-string-equality match semantics established for
  G1. Two paths through the execution flow: fresh labeling
  (`BASELINE_STATUS = not-started`) and existing baseline
  (`BASELINE_STATUS = complete`). Atomic checkpoint writes
  for `data/baseline.csv` use the same `tmp + fsync +
  rename` pattern as `/spp-init`'s `plan.md` writes.
- The **verdict-enforced-gate pattern** is the structural
  precedent this PR establishes for `spp`: a sub-skill's
  verdict adds a literal-string check to the gate's
  approval-phrase enforcement. For G2 specifically, a
  `not-ready` verdict requires an explicit override entry
  in `plan.md` §11 with the literal substring "not-ready
  override"; a `revise` verdict requires an entry with the
  literal substring "baseline-quality"; a `ready` verdict
  advances on the user's approval phrase alone. The pattern
  is what the auditor agent (Phase 2 step 6) will inherit,
  applied per-iteration to the auditor's `categorical` /
  `row-specific` verdict.
- Six adversarial-review checks documented in the
  sub-skill's §3 protocol: class-definition drift,
  borderline-case visibility, intuition-vs-rule divergence,
  class-balance reality check, inter-rater calibration (or
  solo-labeler self-disagreement), and existing-baseline
  provenance. Each check has explicit thresholds tying its
  signal to `revise` or `not-ready` contributions.
- Five worked examples in the sub-skill: clean → `ready`,
  class-definition drift → `revise`, intuition-driven
  labels → `not-ready` then `ready` after refinement,
  severe class-balance drift → `revise` (or `not-ready` if
  unintentional), existing baseline with post-hoc class
  definitions → `not-ready` then `ready` after class
  refinement.
- `/spp-baseline` clarifies the **multi-file data-source
  expectation** in §3 step 7: when `plan.md` §6 describes a
  join (labels in one file, row content in another), the
  user assembles `data/baseline.csv` before invoking the
  command. The command does not perform joins itself in v1
  (joins are domain-specific and often involve filtering
  or de-duplication the command should not unilaterally
  interpret). The fixture-3 walkthrough surfaced this
  expectation; documenting it here forestalls confusion.
- Post-PR-review revisions (single follow-up commit
  `fix(baseline): define splits.json schema, clarify
  thresholds, document loop_spec staleness question`):
  - **`splits.json` schema (substantive).** `/spp-baseline`
    §4 step 9 now defines the schema explicitly:
    `schema_version`, `stratification_key`, `seed`,
    `ratios`, and `row_ids` (a per-partition array of
    string row IDs that match `data/baseline.csv`'s `id`
    column). The schema is settled in this PR because
    `/spp-loop` (Phase 2 step 8) reads it; schema changes
    after this PR are `BREAKING CHANGE:`. The file
    references row IDs only — no row content
    duplication — so partition diffs between PRs are
    human-auditable.
  - **`/spp-baseline` §2 disambiguation.** "Most recently
    approved" plan is the one with the most recent
    G1-approval entry in its `plan.md` §11 revision log,
    by `Date` column. Ties or missing/unparseable
    timestamps surface a candidate list; the command does
    not pick on the user's behalf.
  - **`/spp-baseline` §4 step 4 stop phrase.** Stop is
    `stop` or `enough labels` (whitespace-stripped,
    case-insensitive). On stop the command surfaces a
    "mark complete or continue later" prompt; the user
    decides whether to bump `BASELINE_STATUS` to
    `complete` in this session or exit with
    `in-progress` for resumption.
  - **`/spp-baseline` §4 step 9 sklearn note.** v1 uses
    `train_test_split` from scikit-learn directly. The
    Phase 4 harness will wrap with reproducibility
    logging; the wrapping does not change the produced
    `splits.json` schema, so the wrapping itself is
    non-breaking.
  - **`baseline-quality` Example 3 dual-denominator
    note.** Adds a clarifying paragraph that §3.2's 30%
    threshold applies to the total baseline while §3.3's
    25% threshold applies to borderlines specifically.
    Two different denominators; readers walking the
    protocol should track which population each check is
    evaluated against, or the thresholds will look
    inconsistent.
  - **`baseline-quality` §3.5 small-sample noise note.**
    The 25% self-disagreement threshold is a heuristic on
    a 10–15-row re-labeling exercise; users in the
    borderline range (~20–30%) should re-label a larger
    sample (25–30 rows) before treating the result as
    definitive. The expansion path is surfaced by the
    sub-skill.
  - **`baseline-quality` §3.6 re-labeling scope note.**
    "Re-label" in §3.6's bullets means **affected rows**
    (those surfaced by a focused §3.1 drift check), not
    the entire baseline. Full re-labeling is the
    escalation, appropriate only when §3.1 shows
    pervasive drift (>50% of sampled rows, or every
    class). Distinction matters because full re-labeling
    is days of work; targeted re-labeling is hours.

### Changed

- **`DESIGN.md` §7.1 non-goals** gains a new entry covering
  integration with automated prompt optimization frameworks
  (DSPy, GEPA, APE). v1 deliberately separates rule-edit
  proposal from rule-edit selection; metric-driven
  optimization frameworks fuse these in a way that violates
  the auditor information-isolation property. Roadmap
  consideration only if a defensible separation can be
  designed.
- **`README.md` "Comparison to alternatives"** the DSPy
  paragraph is replaced with an expanded version naming
  DSPy, GEPA, APE explicitly and explaining why
  `spp` deliberately rejects metric-driven optimization
  for v1 (the auditor information-isolation property
  depends on review *before* selection signal is applied;
  frameworks fusing proposal and selection cannot
  accommodate that separation). Adds the methodology-
  boundary framing: `spp` produces a labeled baseline,
  stratified split, defensible metric, and an audited
  prompt that downstream optimizers can use as a starting
  point.

Phase 2 step 4 ships under PR title
**feat(sub-skills): scaffold metric-design sub-skill and pattern
lock for subsequent sub-skills**, already merged.

### Added (Phase 2 step 4, already merged)

- Phase 2 step 4 — the `metric-design` sub-skill at
  `.claude/skills/spp/sub-skills/metric-design/SKILL.md`. The
  first sub-skill in `spp`, read by the designer agent during
  `/spp-init` consultation (`designer.md` §5.2 + §7) to help
  pick the right classification metric and to record the
  rationale in `plan.md` §4.
- Six-section sub-skill structure established as the template
  for `prompt-architect` (Phase 2 step 10) and
  `baseline-quality` (Phase 2 step 5): identity and scope →
  the decision the sub-skill helps make → the decision tree
  → worked examples → the cross-skill constraint → output
  specification. A "Pattern for subsequent sub-skills"
  section pins the structure as non-negotiable; a
  "Versioning" section mirrors the SemVer rule established in
  `designer.md` and `/spp-init.md` (changes that alter
  methodology guarantees are `BREAKING CHANGE:`).
- Six metric options documented with explicit decision-tree
  routing: `F1` (binary, balanced costs, mild imbalance),
  `balanced_accuracy` (binary severe imbalance or multi-class
  recall-equal), `macro_F1` (multi-class equal class weight),
  `precision_at_recall` (binary FN-catastrophic),
  `recall_at_precision` (binary FP-catastrophic), `custom`
  (none of the above; requires inline formula and §5
  independence proof).
- Five generic worked examples that exercise the decision
  tree against realistic task shapes (support-ticket triage,
  clinical PHI leak detection, GitHub issue categorization,
  spam moderation, and an LLM-as-judge request that the
  sub-skill refuses per the §5 independence rule). All
  examples are generic shapes — no source-project content
  per `DESIGN.md` §7.2.
- §5 independence rule restated and elaborated with explicit
  in-scope / out-of-scope / boundary-case lists. v1 forbids
  any LLM-as-judge metric (even cross-family judges); v0.3
  roadmap (`DESIGN.md` §7.1) is the path for tasks where
  ground truth itself requires LLM judgment.
- §6 output specification names the three fields the
  sub-skill writes back to `plan.md` §4: `METRIC_NAME`,
  `METRIC_RATIONALE`, `METRIC_INDEPENDENCE_NOTE`. Validation
  rules 4 and 5 from `plan.md.template` reference this
  contract.
- Post-PR-review revisions to `metric-design` (single
  follow-up commit `fix(metric-design): split Q3 imbalance
  from operational-meaning, reframe Example 5 refusal`):
  - **§3 decision tree restructured.** The original Q3
    folded class imbalance and operational-meaning of the
    positive class into one branch, which obscured the
    parallel with Q5's multi-class question and created an
    apparent contradiction between Example 1 (Billing in
    the mild-imbalance F1 path) and the original Q3
    "roughly balanced" branch (Billing as the example for
    F1-if-meaningful). Q3 now handles imbalance only; a
    new Q3a handles the operational-privilege distinction.
    The §3 summary table is expanded from 8 to 11 rows to
    reflect the new branches; Example 1's decision-tree
    walk now correctly traverses Q3 mild-imbalance →
    Q3a positive-class-privileged → F1.
  - **Example 5 reframed.** The original
    "v1 cannot support this use case" read as a limitation;
    the new framing leads with the methodology position —
    LLM-as-judge tasks are a fundamentally different
    methodology problem and v1 explicitly defers them to
    v0.3 where multi-judge subjective metrics will get
    their own treatment. The three honest-paths options
    (label, wait, reframe) are unchanged.
  - **§5 stricter-interpretation note added.** Calls out
    that this sub-skill takes a stricter operational
    position than `DESIGN.md` §5's textual rule. The design
    doc says "independent of the model being optimized";
    this sub-skill forbids any LLM judge at all (even
    cross-family) because v1 users cannot reliably draw
    the boundary. A future contributor applying §5
    literally might allow Claude judges of GPT prompts in
    good faith; this note prevents that.

Phase 2 step 3 ships under PR title
**feat(commands): scaffold /spp-init command and pattern lock for
subsequent commands**, already merged.

### Added (Phase 2 step 3, already merged)

- Phase 2 step 3 — the `/spp-init` command at
  `.claude/skills/spp/commands/spp-init.md`. The first command in
  `spp`, scaffolding a new task by invoking the designer agent
  through consultation, persisting the resulting `plan.md` and
  deriving `loop_spec.md`, and stopping at gate G1 for explicit
  user approval before any downstream command can run.
- Eight-section command-doc structure established as the template
  for `/spp-baseline`, `/spp-loop`, and `/spp-finalize`: identity →
  invocation → pre-conditions → execution flow → gate enforcement
  → outputs → failure modes → what-not-to-do. A "Pattern for
  subsequent commands" section pins the structure as
  non-negotiable; a "Versioning" section mirrors the SemVer rule
  established in `designer.md` (changes that alter methodology
  guarantees are `BREAKING CHANGE:`).
- Command-vs-agent separation explicitly documented: judgment
  lives in `designer.md`, orchestration and gate enforcement live
  in `spp-init.md`. Future contributors editing consultation logic
  should be editing the agent doc; editing filesystem orchestration
  means editing the command doc. Mixing them produces a system
  where every change touches both files.
- Gate G1 enforcement defined with literal-string-equality match
  semantics (after whitespace strip; case-normalized to the
  recorded phrase; punctuation matters; surrounding text is a
  non-match). Non-matching responses get a specific mismatch
  message naming both the recorded phrase and the user's input,
  with a "revise §9" branch for users who want to update the
  recorded phrase. The pattern is the precedent for G2/G3, G4,
  G5/G6 in subsequent commands.
- `loop_spec.md` derivation flow specified: mirror fields copy
  directly from `plan.md`; literal-string blocks (§3 auditor
  isolation, §4 adversary boundaries, §7 sacred-test-set posture)
  fill verbatim regardless of scope; a small batched run-time-
  mechanics consultation (`API_ENDPOINT`, `CONCURRENCY`,
  `MAX_TOKENS`, `TIMEOUT_SECONDS`, `RETRY_POLICY`, `TEMPERATURE`,
  `MODEL_DIRECTIVES`) surfaces the operations-only fields as one
  batch, separated from §5 methodology consultation.
- Post-PR-review revisions to `/spp-init` (single follow-up
  commit `fix(spp-init): atomic plan.md writes, concrete
  elicitation form, resumption clarifications`):
  - §4 step 6 now specifies **atomic checkpoint writes** —
    write to `plan.md.tmp`, fsync, rename to `plan.md` — at
    every consultation pause point. Without atomicity the
    resumability claim is silently broken; an interrupted
    session could leave the file mid-line and unreadable by
    the resumption logic. Also documents that concurrent
    invocations from two terminals are not supported in v1
    (no file lock).
  - §4 step 7 gains a **concrete elicitation block** showing
    the run-time mechanics consultation as a single
    formatted prompt with defaults in brackets and an `ok`-
    accepts-all reply pattern. `/spp-loop`'s analogous
    run-time block will follow the same elicitation
    pattern.
  - §5 "revise §9" branch now explicitly states that the
    prior G1 phrase is **replaced**, not appended (single
    phrase per plan, latest wins; revision history preserved
    in `plan.md` §11 plan revision log).
  - §3 step 4 clarifies that the resumption logic reads the
    **working-tree `plan.md`**, not any git index or HEAD
    version. Users who commit between sessions still resume
    from the working-tree state.
  - §4 step 5 adds a **resumption-mode contradiction**
    branch: when the fresh §3 scan surfaces facts that
    contradict the partial plan (referenced data file gone,
    model identifier unset, column renamed), the designer
    surfaces the contradiction as the first message of the
    resumed session. The command does not adjudicate.
  - §2 explains **why task names cannot be renamed
    mid-flow**: the name appears in `plan.md` §1, the
    directory path, `loop_spec.md`, eventual `runs/`
    artifacts, and `REPORT.md`'s SHA-256 verification
    command. A safe rename would require coordinated
    updates across all of these. v1 keeps the name
    immutable for the duration of the task.

Phase 2 step 2 ships under PR title
**feat(designer): scaffold designer agent and fixture suite**,
already merged.

### Added (Phase 2 step 2, already merged)

- Phase 2 step 2 — the designer sub-agent at
  `.claude/skills/spp/agents/designer.md`. Six-section structure
  (identity and posture; unique information access; reading checklist
  before asking; strawman pattern; consultation questions grouped by
  what they unblock in `plan.md`; resumability for mid-consultation
  re-entry) plus a §7 validation gate that runs `plan.md.template`'s
  twelve mechanical rules before declaring `plan.md` complete. The
  designer is the first agent in the project; its document structure
  is the template `auditor.md` and (optionally) `adversary.md` will
  reuse in subsequent build-order steps.
- Three task fixtures at
  `.claude/skills/spp/agents/designer/fixtures/`:
  - `full-scope-binary-classification/` — happy-path methodology
    (80 baseline rows, F1, full Phase 1 + 1.5 + 2 + 3).
  - `stripped-scope-small-baseline/` — 30-row labeling budget,
    HIPAA-locked Azure model, Phase 3 skipped in favor of shadow-
    deployment pilot, recall-at-precision metric. Validates the
    designer's adaptation per DESIGN.md core principle 2.
  - `multi-class-with-existing-baseline/` — 4-class categorization
    with 200 pre-existing labels. Validates that the designer
    recognizes user-provided labels (`BASELINE_STATUS = complete`
    on initial entry) and selects macro-F1 for balanced multi-class.
  Each fixture contains `task_description.md`, `consultation_notes.md`,
  and `expected_plan.md`.
- Designer doc §5.6 explicitly notes that methodology guarantees
  (`SACRED_TEST_ACK = acknowledged`, `AUDITOR_CONFIG = per-iteration,
  no-score-access`, and the corresponding `loop_spec.md` literal-
  string blocks) survive scope stripping. Scope stripping changes
  which workflow steps run; it does not change what the methodology
  promises.
- Post-PR-review revisions to the designer doc (single follow-up
  commit `fix(designer): clarify data-read scope, reorder baseline
  questions, document loop_spec derivation and agent versioning`):
  - §3.2 (the `data/` reading constraint) now includes the
    anchoring rationale — the designer reads structure (filenames,
    formats, row counts, column headers), not contents, because
    reading body rows at consultation time risks anchoring on
    specific examples instead of understanding the task abstractly.
    Without the rationale, a future contributor would reasonably
    soften the limit.
  - §5.4 baseline questions reordered: "do you already have
    labels?" comes first, with willingness-to-label and labeler
    provenance gated on the answer. The previous order forced an
    awkward double-take when the user already had labels (fixture
    3's path).
  - §1 identity gains a sentence noting the designer is versioned
    with the `spp` skill (not project-local), so users pulling
    skill updates get new designer behavior. Prevents the
    reasonable assumption that agents are per-task customizable.
  - §1 also documents the **loop_spec derivation model**:
    `loop_spec.md` is derived mechanically from the approved
    `plan.md`; literal-string blocks (auditor §3, sacred test set
    §7) are filled with non-negotiable values verbatim and never
    offered as consultation choices; only run-time mechanics
    (concurrency, retry, max_tokens, timeout, model directives)
    are surfaced as a short follow-up consultation, batched and
    not interleaved with §5 methodology questions.
  - New section "Agent versioning and methodology guarantees"
    establishes the SemVer rule that changes affecting methodology
    guarantees (literal-string locks, validation rules, reading-
    checklist boundaries) are `BREAKING CHANGE:` and require a
    major-version bump. Sets the precedent for `auditor.md` and
    (optionally) `adversary.md` — load-bearing for the auditor in
    particular, since a v0.2 auditor with score access would
    silently break v0.1 methodology claims.

Phase 2 step 1 ships under PR title
**feat(templates): scaffold v0.1.0 templates for Phase 2 build order**,
already merged.

### Added (Phase 2 step 1, already merged)

- Phase 2 step 1 — four templates under `.claude/skills/spp/templates/`,
  the leveraged work that defines what `spp` produces:
  - `plan.md.template` — the contract output of `/spp-init`. Sections
    cover task overview, class definition, success criteria, metric
    (with the metric-design independence check enforced as a
    validation rule), model lock-in posture, baseline status, splits
    (with the sacred-test-set acknowledgment as a literal-string
    validation), loop scope and stop criteria (with auditor
    `per-iteration, no-score-access` enforced as a literal-string
    validation rule), HITL gate approval phrases, open questions, and
    a plan revision log.
  - `loop_spec.md.template` — task-specific instantiation of Phase 2
    consumed by `/spp-loop`. Contains a non-parameterized
    "Auditor configuration" block (literal three lines:
    `auditor: per-iteration`, `score_access: forbidden`,
    `frequency_reduction: forbidden`) and a non-parameterized
    "Sacred test set posture" block; both are linter-checked
    verbatim. Adversary boundaries (non-persistence, no baseline
    promotion) are also stated rather than parameterized.
  - `prompt_v01.md.template` — the initial prompt skeleton with the
    six-section prompt-architect XML structure (`<persona>`,
    `<task>`, `<rules>`, `<output_format>`, `<example_input>`,
    `<example_output>`) plus a header slot for model-specific
    directives (e.g. Qwen `/no_think`) with explicit guidance that
    these are model-locked and must be stripped on migration.
  - `REPORT.md.template` — per-model summary written by
    `/spp-finalize`. Sections: run metadata, train/dev/test scores
    with confusion matrices, loop trajectory, persistent failure
    clusters, prompt-edit audit (with the literal assertion
    `Auditor information-isolation invariant: preserved.` as a
    validation rule), decision and recommendation, mandatory
    Limitations section (model lock-in, baseline scope, persistent
    clusters, loop interruption posture, other), cost-at-scale,
    and the production prompt artifact with SHA-256 hash field for
    deploy-vs-report verification.
- Removed the now-redundant `.claude/skills/spp/.gitkeep` placeholder;
  the directory now contains real tracked content (`templates/`).
- Post-PR-review revisions to Phase 2 step 1 (single follow-up commit):
  `prompt_v01.md.template` validation rule #5 explicitly notes that
  example-input/example-output correspondence is a manual review gate,
  not a mechanical lint check (mirrors the framing of rule #8);
  `REPORT.md.template` §8 cost-at-scale gains a comment that the
  1K/10K/100K projection volumes are illustrative defaults to be
  replaced with the user's actual production scale by `/spp-finalize`,
  not left as-is.
- README "When to use this" reframes baseline-row willingness as the
  user's call (50–100 rows is typical, but the methodology adapts;
  smaller baselines limit statistical confidence, larger baselines
  increase Phase 1 cost; bring-your-own-labels is supported); README
  Quickstart §3 now reflects that the user provides rows or labels
  rather than the skill prescribing a fixed count.
- README adds a Mermaid pipeline diagram between "The methodology" and
  the automation table, making the six HITL gates and the auditor's
  per-iteration categorical-vs-row-specific review visible at a
  glance. Dotted edges are revision/correction paths; solid edges are
  the on-spec forward flow.

Phase 1 ships under PR title
**chore: scaffold v0.1.0 repo skeleton (Phase 1)**, merged.

### Added (Phase 1, already merged)

- Initial repo scaffold (Phase 1 of the kickoff plan): `LICENSE`,
  `environment.yml`, `.gitignore`, `README.md`, `CODE_OF_CONDUCT.md`,
  `CONTRIBUTING.md`, `CHANGELOG.md`, `CLAUDE.md`, `DESIGN.md`,
  `.github/pull_request_template.md`, and placeholder directories
  (`.claude/skills/spp/`, `examples/`, `tests/`). Establishes the
  credible open-source repo structure that ships before any skill
  content is written.
- `DESIGN.md` (Phase 0 deliverable) with skill purpose, the two failure
  modes (baseline vs model overfitting), slash-command list, sub-agent
  justifications with the auditor's information-isolation property
  called out as load-bearing, sub-skill list, build order with
  `metric-design` moved to step 3 to reflect actual dependency on the
  designer agent, v1 scope statement, the §7.1 Non-goals canonical
  reference, the §7.2 examples-confidentiality clause (NDA-respecting
  scope for Phase 3 worked examples), and the §10 Glossary.
- Conda `environment.yml` defining the `spp-dev` Python 3.11
  development environment with conda-forge as the sole channel, pinned
  minor versions for `pandas`, `numpy`, `scikit-learn`, `httpx`, and
  pip-only deps for `openai`, `python-dotenv`, `pydantic`.
- Post-Phase-1-review revisions (single follow-up commit):
  `CLAUDE.md` §6 now requires inline-comment justification for any
  `# noqa` / `# type: ignore` (PR descriptions are lost to squash-
  merge; inline comments persist with the code); `README.md` "When to
  use this" softened from gating language to "typical fit" framing
  (only the classification scope remains a hard gate); `DESIGN.md`
  gained §7.2 establishing that Phase 3 worked examples are skeleton
  artifacts with placeholder data, distinguishing citable findings
  (aggregate metrics, cluster taxonomy) from non-reproducible
  protected content (row text, labels, prompt bodies) per the source
  project's NDA constraints.

### Changed

- _none_

### Deprecated

- _none_

### Removed

- _none_

### Fixed

- _none_

### Security

- _none_

### Provenance notes

- `CODE_OF_CONDUCT.md` is the unmodified Contributor Covenant 2.1, fetched
  from `https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md`
  during repo scaffolding. The only edit applied locally is the
  `[INSERT CONTACT METHOD]` placeholder being replaced with the
  maintainer's contact address. Fetch was used in lieu of inline
  generation because content classifiers misfire on the document's
  enumeration of prohibited behaviors; the canonical text is the
  authoritative source either way.

---

## [0.1.0] — _unreleased_

The first tagged release will scope to:

- Classification tasks only (binary, multi-class, fixed-schema labeling)
- English-language data
- Single-model dev loops (per-model `REPORT.md`, no cross-model summary)
- Loop resumption requires manual restart (mid-iteration interrupts are
  discarded; iteration is the unit of work)
- Auditor runs per-iteration, non-optionally (batch-auditing is the
  post-v1 escape valve, not frequency reduction)

See [`DESIGN.md`](DESIGN.md) §7 and §7.1 for the canonical scope and
non-goals lists.

[Unreleased]: https://github.com/JayLBean/spp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/JayLBean/spp/releases/tag/v0.1.0
