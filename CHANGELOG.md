# Changelog

All notable changes to `spp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

- **Community health files** — `SECURITY.md` (private vulnerability reporting and
  a supported-version policy) and GitHub issue templates (bug report; feature /
  roadmap idea with a scope check against the §7.1.3 non-goals; plus a config
  with documentation links). Repository infrastructure only — no skill, prompt,
  gate, or contract change.

---

## [1.0.1] — 2026-06-17

Patch release: documentation and a runner compatibility fix. No methodology or
contract change — the frozen v1.0 surface ([`DESIGN.md`](DESIGN.md) §7.1.13) is
untouched.

### Added

- **`examples/public-benchmark/` — the first example backed by a real,
  reproducible run on public data.** Ships the complete `spp` artifact set from a
  TREC (6-class question-type) run on `gpt-5-nano` — plan, loop-spec, every
  iteration's prompt/eval/discrepancy/auditor trio, the frozen prompt, and the
  single sacred-test read — plus `RESULTS.md`, a three-way comparison against
  EvoPrompt and DSPy (same model, same seed, same sacred test) across AG News,
  SST-5, and TREC. Unlike the other examples (placeholder skeletons), every row,
  prediction, and prompt here is genuine and unredacted (TREC is public,
  redistributable data). The README's "Compared to alternatives" section now
  carries the benchmark summary table. No methodology change — documentation and
  a worked artifact set only; the frozen v1.0 contract is untouched.
- **README now links the live benchmark site**
  (<https://jaylbean.github.io/spp-benchmark/>) — the published home of the
  three-way comparison, with per-task loop logs documenting every iteration and
  the human-in-the-loop gate exchange. Documentation pointer only; no contract or
  methodology change.

### Changed

- **README Quickstart now names the four phases as phases, not `/spp-*`
  commands.** `/spp:run` is the only command the user types; `Init` / `Baseline`
  / `Loop` / `Finalize` are internal phase steps the router runs after that one
  invocation. Wording correction only — the phases were already described as
  internal steps; this drops the misleading slash prefix. No contract or
  methodology change; matches the documentation site
  (<https://jaylbean.github.io/spp-site/>).

### Fixed

- **`inference.py` now supports OpenAI reasoning models (`gpt-5*`, `o`-series).**
  The runner previously sent `max_tokens` + `temperature` on every call, which
  these models reject (they require `max_completion_tokens`, forbid a non-default
  `temperature`, and take a `reasoning_effort` knob). A name-based
  `_is_reasoning_model` check now branches the `chat.completions.create` kwargs;
  the classic path for non-reasoning models is unchanged, so this is a pure
  compatibility fix with no contract or methodology impact. `reasoning_effort`
  defaults to `low`, overridable via `SPP_REASONING_EFFORT`.

---

## [1.0.0] — 2026-06-08

The v1.0 development arc: **stabilization (the contract freeze).** No new
capability — v1.0 declares the public surface stable now that the v0.x roadmap
has landed, and makes that declaration mechanically enforceable.

### Added

- **DESIGN.md §7.1.13 — v1.0 freeze spec + post-1.0 change policy.** Enumerates
  the frozen surface (the four commands, three loop agents, six-section prompt,
  six templates, script CLIs, eight sub-skills, two advisor catalogs and their
  `ENTRY_SCHEMA`, the `MODEL_IDENTIFIER` contract, the gate strings and verdict
  tokens, and the twenty-one §7.1.1 invariants) and defines the post-1.0
  semantic-versioning policy: patch = fixes / docs / conforming catalog entries,
  minor = additive backward-compatible capability touching no invariant, major
  (v2.0) = any contract change. All eight §7.1.3 deliberate non-goals (e.g.
  generation, RAG, agentic, prompt-search, LLM-judge-in-scoring) are
  **permanent**. Methodological implication: this pins the boundary the rest of
  the v1.0 arc hardens and the linters mechanically enforce.
- **DESIGN.md §7.1.14 — consolidated locked-invariants audit (v1.0).** A single
  canonically numbered list of all twenty-one §7.1.1 invariants (#1–#21), each
  with its one-line guarantee and current enforcing site (file + section / step /
  literal guard string). It supersedes the per-arc audits in §7.1.4–§7.1.12 and
  reconciles their uneven referencing: about half the invariants had only ever
  been cited by number, the rest lived unnumbered in the §7.1.1 thematic
  inventory, and #2 was named two ways. Methodological implication: this is the
  authoritative numbered index the freeze (§7.1.13) and the post-1.0 change
  policy point at — adding, removing, or weakening any entry is a `BREAKING
  CHANGE:` and a v2.0 action.
- **Linter harness + template / plan.md linters (the first "Phase 4" linters).**
  New `scripts/_lint.py` (shared `Violation` record + placeholder/section/field
  helpers) and `scripts/lint_templates.py`, exposed both as pytest coverage
  (`tests/test_lint_templates.py`, 22 tests) and an optional CLI
  (`python -m scripts.lint_templates templates | plan <path>`). The
  template-contract check asserts each of the six shipped `.template` files still
  carries its required placeholders and section headings (a freeze guard — the
  templates are frozen surface); the `plan.md` check validates a filled plan
  against the mechanically robust subset of the template's validation rules
  (no unresolved placeholders, kebab task name, the sacred-test and
  auditor-isolation literals guarding invariants #6/#4, split percentages,
  HITL gate phrases, a monotonic revision log, and a valid `TASK_MODE`). Rules
  needing a JSON-Schema parse or the metric catalog (3, 4, 5) remain the
  schema-designer / metric-design job at G1. Methodological implication: none —
  the linters add no capability; they make already-locked contracts
  machine-checkable. Updated the `CONTRIBUTING.md` and `scripts/README.md`
  references to the real command. Suite: 326 → 350 tests.
- **Catalog and six-section prompt linters (the second "Phase 4" slice).** New
  `scripts/lint_catalogs.py` validates the `ENTRY_SCHEMA` contract for both
  advisor catalogs (`technique-advisor/techniques/*.yaml` —
  seven required fields; `structure-advisor/structures/*.yaml` — eight, adding
  `independence`): every required top-level field present and non-empty, `id`
  equal to the filename stem, ids unique. It parses the entries' controlled
  flat-key format directly rather than adding a YAML dependency for a presence
  check; the ENTRY_SCHEMA *eligibility* rules stay review-enforced as both
  schema docs state. A new `check_prompt` in `lint_templates.py` (CLI
  `python -m scripts.lint_catalogs`; `python -m scripts.lint_templates
  prompt <path>`) validates a filled `prompt_v01.md` against the six-section
  structure (invariant #12): the six XML sections present exactly once, in
  canonical order, with matching close tags, a non-empty enumerated `<rules>`,
  and non-empty example sections — counting only standalone-line tags so an
  inline mention in a comment is not mistaken for a section. Rules needing
  semantic judgment (output-format compliance, example correspondence,
  no-real-data) stay manual PR gates (`PROMPT_RULES_DELEGATED`). Methodological
  implication: none — mechanical enforcement of locked contracts. Suite:
  350 → 372 tests.
- **REPORT §5 / loop_spec literal-block linters + one-command runner (the final
  "Phase 4" slice).** `check_report` verifies the `REPORT.md` §5 per-stage
  information-isolation invariant block is present verbatim (header + all four
  sub-statements — invariant #21); `check_loop_spec` verifies the `loop_spec.md`
  non-negotiable literal blocks are unmodified — the §3 per-stage isolation lines
  and §7 sacred-test lines verbatim, and the §4 adversary-boundary guarantees
  (matched after whitespace normalization, since they ship as wrapped prose) —
  invariant #18. Both are added to `lint_templates.py` (CLI subcommands `report`
  and `loop-spec`). New `scripts/lint_all.py` aggregates the whole family —
  templates, catalogs, REPORT §5, loop_spec literal blocks — behind one command
  (`python -m scripts.lint_all`), the single freeze-guard check, also run under
  the suite. With this, all six "Phase 4 linter" promises in the docs are
  discharged; updated the remaining "forward work" references in `SKILL.md` §3.4,
  `plan.md.template`, `CONTRIBUTING.md`, and `scripts/README.md` to the real
  commands. Methodological implication: none — these enforce the §7.1.1
  invariants #18 and #21 mechanically. Suite: 372 → 382 tests.

### Changed

- **Docs hardening — stale-scope and roadmap sweep.** Now that the v0.x roadmap
  has landed, corrected documentation that still framed shipped capabilities as
  future work or non-goals. `CONTRIBUTING.md` "What is and isn't in v1 scope" was
  rewritten to separate what shipped (classification + extraction, multilingual,
  decomposition, loop resumption, etc.) from the permanent §7.1.3 deliberate
  non-goals, and to state the post-1.0 = v2.0 policy. `skills/run/SKILL.md` was
  corrected: the artifact taxonomy now reads eight sub-skills and six templates
  (was three / four), the §3.3 sub-skill table adds the missing `label-panel`
  (v0.7) and `structure-advisor` (v0.9) rows, the §3.4 template list adds
  `preprocess.py` and `pipeline.md`, and the §6 non-goals list no longer calls
  spp "classification-only" or "English-only" or labels shipped features as
  "v0.3/v0.4 roadmap". Mislabeled "cross-model synthesis is v0.4 roadmap" and
  "v0.3 roadmap" references in `phases/spp-finalize.md`,
  `sub-skills/metric-design/SKILL.md`, `sub-skills/prompt-architect/SKILL.md`,
  the `examples/hair-loss-relevance` plan, and the `CONTRIBUTING.md` / `CLAUDE.md`
  commit-message examples were corrected to point at the §7.1.3 deliberate
  non-goals. Methodological implication: none — the scope boundary is unchanged;
  the docs now describe it accurately. The finalize-phase edits are pure
  roadmap-framing corrections and touch no isolation, sacred-test, or allow-list
  language.
- **Examples re-verified for the v1.0 freeze.** Added a top-level
  `examples/README.md` indexing all six worked examples (task type, what each
  demonstrates, how each is verified) and documenting the canonical run-all
  command. Confirmed the full test suite is green (326 tests) and that the four
  config-backed examples (`multi-field-extraction`, `nested-schema`,
  `entity-extraction`, `decomposition-pipeline`) are exercised end to end; the
  other two (`hair-loss-relevance`, `feature-group-split`) are illustrative
  skeletons (placeholder data, no machine-readable scoring configs), documented
  as read-not-run. No methodology change.
- **README rewritten for concision.** Cut the README from ~525 to ~195 lines —
  a value-prop-first, scannable structure (Why / the two failure modes + the
  cross-model table / How it works / When to use / Install / Quickstart /
  Compared to / Contributing). Removed the heavy repetition (the multi-paragraph
  Status block, a Roadmap section that nearly duplicated the intro, two of three
  redundant pipeline diagrams) and made the prose version-light, pointing to
  `CHANGELOG.md` and `DESIGN.md` §7.1 for version and scope detail rather than
  restating them. No methodology change; the load-bearing content (the two
  failure modes, the methodology shape, the honest scope and non-goals) is
  preserved.

### Fixed

- **Two pre-existing doc inaccuracies, ahead of the freeze.** `DESIGN.md`'s
  title said "Supervised Prompt Produc*ing*" (the canonical name, per the plugin
  manifests and the README, is "Supervised Prompt Produc*er*"), and a
  `spp-finalize.md` error-recovery row referenced a non-existent gate `G7` (the
  gate set is G1–G6; the resumption path proceeds `G5 → G6`). Surfaced during the
  README review. No methodology change.

---

## [0.11.0] — 2026-06-08

The v0.11 development arc: **prompt decomposition.** spp gains the second
`structure-advisor` seed — **decomposition**, splitting one task into a
**linear pipeline** of prompts (node 1 → … → terminal), the managed form of the
manual feature-group splitting practice. It is scoped to **node-local gold**:
each node has its own labeled ground truth and metric, so the per-stage
isolation contract applies **per node, unchanged** — each node's discrepancy /
rule-edit / auditor stages see only that node's local input → output → gold,
with no cognitive cross-node flow. A node is optimized **upstream-frozen**
(optimize to its dev floor, freeze, materialize the next node's baseline from
the frozen output), the sacred test set is read **exactly once** across the
whole pipeline at a single composite `/spp-finalize`, and the four-command set
stays closed (#20) — `/spp-loop` optimizes the active node, not a fifth command.
Every node keeps a **mechanical metric on its own gold** and the composite is a
pure roll-up (`terminal | mean | weighted | min`), so **invariant #13 holds**
end to end; the contract-extending end-to-end credit-assignment form is
deferred. Scoped to **linear chains** only (general DAGs deferred). The pipeline
spec (`pipeline.md` + a runnable config), the `_pipeline.py` mechanics and CLI,
and the phase wiring are all additive and backward-compatible: a plan with no
pipeline declaration is a single-node task and runs exactly as before. All
twenty-one §7.1.1 invariants remain intact (DESIGN.md §7.1.12 audit). Suite:
289 → 326 tests.

### Added

- **v0.11 pipeline REPORT branch + end-to-end example**
  (`skills/run/templates/REPORT.md.template` §2.4; `examples/decomposition-pipeline/`;
  `skills/run/scripts/tests/test_examples_pipeline.py`). `REPORT.md.template`
  gains a §2.4 "Pipeline composite" block — present only for a pipeline — that
  reports the per-node test scores plus the composite from the single composite
  finalize (each per-node value is that node's mechanical metric on its own
  node-local gold; #13). A new `examples/decomposition-pipeline/` skeleton
  demonstrates a two-node `extract → classify` linear pipeline: `extract` pulls
  product mentions (`extraction_f1`), `classify` classifies sentiment
  (`macro_f1`) reading the review plus the **frozen `extract` output**
  materialized as an input column. Each node is a normal spp task under
  `sub-tasks/<id>/`; `pipeline.json` / `pipeline.md` is the parent that orders
  and wires them (`mean` composite). The end-to-end test scores `extract`,
  materializes `classify`'s baseline from `extract`'s frozen output, scores
  `classify`, and computes the composite — through the real
  `compute_eval_multifield` + `_pipeline` functions (synthetic predictions, no
  model call), including an upstream-miss case that pulls the composite down.
  Suite: 323 → 326.

- **v0.11 pipeline phase wiring** (`skills/run/phases/spp-init.md`,
  `spp-baseline.md`, `spp-loop.md`, `spp-finalize.md`). Each phase gains a
  "Pipeline mode (v0.11)" section describing how it behaves for a decomposition
  pipeline (`DESIGN.md` §7.1.12): `/spp-init` produces a parent `pipeline.md`
  plus one normal node task per `sub-tasks/<node-id>/`; `/spp-baseline`
  materializes each downstream node's baseline from the **frozen upstream**
  (the data-plane step, after the upstream node freezes); `/spp-loop` optimizes
  the **active node** with the ordinary loop; and there is **exactly one**
  composite `/spp-finalize` — the only sacred-test read across the whole
  pipeline. Methodological implication: the per-stage isolation contract applies
  **per node, unchanged** — each node's discrepancy / rule-edit / auditor stages
  see only that node's local input → output → gold with their existing
  allow-lists; no cognitive cross-node flow. A new `BREAKING CHANGE:` guard in
  `spp-loop.md` forbids any pipeline path that gives a node's isolated stage
  another node's prompt/scores/discrepancy/rows (#1–#3), or that replaces the
  single composite finalize with a per-node sacred-test read (#6/#7); the benign
  frozen-output-as-input-column dependency is explicitly the data plane, not a
  violation. The four-command set stays closed (#20) — `/spp-loop` optimizes a
  node, not a fifth "pipeline" command. Doc-only; a single-node task is
  unchanged.

- **v0.11 pipeline orchestration CLI** (`skills/run/scripts/_pipeline.py`
  `main()`; `skills/run/scripts/tests/test_pipeline.py`). Gives the phases two
  concrete tools, both built on the bucket-4 mechanics: `materialize` produces a
  downstream node's baseline from one or more **frozen upstream** `results.json`
  files (extracting each upstream node's `parsed_fields` by row id, attaching
  them as input columns, and composing the single `input` column the node's
  prompt reads), and `composite` rolls per-node `eval.json` `primary_value`s into
  the headline composite. New helpers: `extract_node_outputs` (node results →
  `{"<node>.<field>": {row_id: value}}`) and `compose_node_input` (a node's
  effective input — raw for a single input, a stable labeled block
  `"<col>:\n<value>"` for several — so the runner passes one user message while
  the node's prompt reads named fields). Still **no model in this module**: the
  CLI only transforms data already produced by the per-node runs, so the
  per-stage isolation contract is untouched. The phase wiring that drives these
  tools (sequencing, freezing) lands in the next bucket. The CLI surfaces
  malformed/missing inputs (bad pipeline config, upstream results, baseline, or
  per-node eval) as clean errors, not tracebacks. Suite: 312 → 323.

- **v0.11 pipeline mechanics** (`skills/run/scripts/_pipeline.py`;
  `skills/run/scripts/tests/test_pipeline.py`). The model-free building blocks
  the decomposition phases compose: `load_pipeline_spec` parses and
  **validates** the runnable pipeline config, enforcing the `pipeline.md`
  validation rules in code (a linear chain of ≥2 nodes, node 1 with no upstream,
  upstream references that point only to earlier nodes — so the chain is acyclic
  and forward — and a composite metric in `terminal | mean | weighted | min`);
  `materialize_node_inputs` attaches a node's **frozen upstream output** as input
  columns keyed by row id (the §7.1.12 data-plane step — it carries no scores
  and reaches no isolated cognitive stage, and a missing upstream value is a hard
  error, not a silent gap); `compute_composite` rolls ordered per-node primary
  metrics into the headline composite. Every function is a pure transform of data
  already in hand — **no model runs here**, so the per-stage isolation contract
  is untouched. The chain orchestration that calls `run_inference` per node
  (freezing upstream between nodes) is driven by the phase wiring and lands in
  the next bucket; this is the mechanics it composes. Additive; nothing existing
  changes. Suite: 289 → 312 tests.

- **v0.11 pipeline spec** (`skills/run/templates/pipeline.md.template`). Adds
  the parent contract for a decomposition pipeline: a `pipeline.md` declaring
  the **node order** and the **inter-node wiring** (which upstream output feeds
  which downstream input column), plus composite scoring and the
  sequencing/freezing posture. Each node remains a normal spp task under
  `sub-tasks/<node-id>/` with its **own** `plan.md` (OUTPUT_SCHEMA / metric /
  floor) — so the per-node contract is unchanged and the per-stage isolation
  contract applies per node exactly as for a single-node task (DESIGN.md
  §7.1.12). Resolves the bucket-1 open question toward a **sibling
  `pipeline.md`** (not a `plan.md` block): each node reuses the existing
  single-node machinery, and the parent file adds only the ordering and wiring
  — matching the existing `sub-tasks/<node>/` layout of the manual
  feature-group-split example. Validation rules enforce a **linear chain**
  (no DAGs), **node-local gold** (no terminal-only credit assignment),
  earlier-only upstream references, and a `terminal | mean | weighted | min`
  composite metric. Backward-compatible: a single-node task needs no
  `pipeline.md` and runs exactly as before. The runner/phase wiring that reads
  this spec lands in later buckets.

- **v0.11 structure-advisor decomposition entry**
  (`skills/run/sub-skills/structure-advisor/structures/decomposition.yaml`;
  `SKILL.md` §1, §4). Adds the second catalog entry (sibling to v0.9's batch
  I/O): **decomposition**, recommending a split into a **linear pipeline** of
  prompts when the OUTPUT_SCHEMA (`plan.md` §2) spans feature groups needing
  different reasoning patterns and each group has node-local gold. The entry's
  `structure_form` is `linear_pipeline` — the runner walks a chain, each node a
  full six-section prompt (so #12 is preserved per node), with `independence:
  n/a — one row per call` (a pipeline never co-locates rows, so the #13
  batch-contamination hazard does not arise). Consultative and ungated like
  every catalog entry; it adds no stage allow-list and no gate. SKILL.md moves
  decomposition from "out of scope" to a catalog entry under the locked
  node-local scope; the contract-extending end-to-end credit-assignment version
  stays out of scope (`DESIGN.md` §7.1.12). Wiring (where the advisor surfaces
  the recommendation) lands in a later bucket of the v0.11 arc.

- **v0.11 design pin — prompt decomposition (a managed linear pipeline)**
  (`DESIGN.md` §7.1.12, §7.1.2). Opens the v0.11 arc: the second
  `structure-advisor` seed, **decomposition** — splitting one task into a
  **linear pipeline** of prompts (node 1 → 2 → … → terminal), the managed form
  of the README's manual feature-group splitting. Methodological implication:
  the arc is scoped to **node-local gold** (every node has its own labeled
  ground truth and metric), which is the contract-preserving choice — because
  each node is a self-contained supervised sub-problem, the per-stage isolation
  contract applies **per node, unchanged**, with the loop sequenced
  upstream-frozen (optimize a node to its floor, freeze it, materialize the next
  node's baseline from the frozen output, optimize that node). The discrepancy /
  rule-edit / auditor subagents run on the active node's local input → output →
  gold with their existing allow-lists; there is **no new cross-node
  information flow into any isolated stage**, so the contract is preserved
  (applied N times), **not extended**. End-to-end credit assignment (only the
  terminal output labeled; a new stage attributing failures to nodes) is the
  contract-extending version and is **deferred**. Decomposition is advisory (the
  advisor recommends; the user declares the pipeline; nothing auto-splits) and
  runs under the same four commands (#20) — `/spp-loop` optimizes the active
  node, not a fifth "pipeline" command. Scope boundary: **linear chains only**
  (general DAGs deferred), node-local gold only. Backward-compatible: a plan
  with no pipeline declaration is a single-node task and runs exactly as before.

### Changed

- **v0.11 close-out: retrospective audit + README reconcile** (`DESIGN.md`
  §7.1.12; `README.md`). The §7.1.12 locked-invariants posture is upgraded to a
  **retrospective audit** with per-invariant file citations (#1–#3 per-node
  isolation + the data-plane/isolation-plane line, #6/#7 single composite
  finalize, #13 mechanical per-node metrics + composite roll-up, #15
  `pipeline.md`/`plan.md` contracts, #20 four commands; suite 326). The README
  "Feature-group prompt splitting" section now reconciles the **manual** practice
  with the v0.11 **managed** linear pipeline — the two coexist; the managed form
  automates sequencing, freezing, and baseline materialization for the
  sequential case — pointing to `examples/decomposition-pipeline/`.

---

## [0.10.0] — 2026-06-08

The v0.10 development arc: **structured extraction as a designer-agent mode.**
spp generalizes from classification to its first new task family since v0.2 —
variable-cardinality, span-grounded **extraction** (named entities, spans,
redaction targets) — added as a **mode the designer selects** during
`/spp-init`, recorded once in `plan.md` §1 as `TASK_MODE` and re-read by every
phase. Extraction is admitted as a *generalization* of the methodology, not a
new one, because it keeps a fixed ground truth and a mechanical metric:
alignment-based `extraction_f1` / `span_f1` and deterministic `leakage` are
pure functions of (prediction, gold), so **invariant #13 holds** — the dividing
line that keeps generation and RAG out of scope (§7.1.3). The load-bearing
property across the discrepancy and auditor stages is that each isolated
stage's allow-list **membership is unchanged**; only the *content shape* inside
already-allowed artifacts changes (item-level "disagreed", span-effect
judgment), so the per-stage isolation invariants (#1–#3) and the four-command
set (#20) are preserved — extraction is a mode, not a fifth command.
Multi-prompt / decomposition is resequenced to its own v0.11 arc because it
extends the isolation contract while extraction does not. `TASK_MODE` and the
extraction metric/parse paths are additive and backward-compatible (absent →
`classification`). All twenty-one §7.1.1 invariants remain intact (DESIGN.md
§7.1.11 audit). Suite: 253 → 289 tests.

### Added

- **v0.10 extraction REPORT branch + end-to-end example**
  (`skills/run/templates/REPORT.md.template` §2.1;
  `examples/entity-extraction/`;
  `skills/run/scripts/tests/test_examples_multifield.py`). The REPORT
  template's §2.1 auxiliary-structures list gains an extraction entry: a
  **failure-mode breakdown** (aggregate counts of missed / spurious / mistyped
  / boundary errors, plus per-type P/R/F1 and the IoU distribution for span
  fields), aggregate-only with no extracted row content (DESIGN.md §7.2). A new
  `examples/entity-extraction/` skeleton demonstrates the full extraction flow
  — `TASK_MODE = extraction`, an item-array OUTPUT_SCHEMA, `span_f1` on
  offset-grounded entities and `extraction_f1` on free-text topics, a `macro`
  aggregate, and an `entities` floor — with runnable scoring configs exercised
  end to end (synthetic predictions, no model call): a perfect run, a
  sub-threshold span (IoU 0.4 < 0.5) dropping `span_f1`, and a dropped topic
  dropping `extraction_f1`. The empty-mention row (`row_004`) demonstrates that
  an empty item array is a valid answer, not a parse failure. Suite: 286 → 289.
- **v0.10 extraction discrepancy + auditor (content shape, not allow-list)**
  (`skills/run/phases/spp-loop.md` §4 step 8 + step 11;
  `skills/run/agents/auditor.md` §4). Under `TASK_MODE = extraction` the
  discrepancy stage's notion of "disagreed" becomes **item-level** (a row
  disagrees when an extraction field's per-row metric is imperfect — an item
  missed, spurious, mistyped, or mis-bounded — not when a label mismatches),
  and failure clusters group by **failure mode** (missed / spurious / mistyped
  / boundary). The auditor's categorical-vs-row-specific synthetic-row test
  reframes to judge a rule's **span/item effect** rather than its label effect.
  Methodological implication — the load-bearing property of the whole arc: the
  **allow-list membership of every isolated stage is unchanged**; only the
  *content shape* inside the already-allowed artifacts changes. The discrepancy
  subagent reads the same files and computes the item-level view from
  predictions and disagreed-row gold it already has; the auditor stays
  **score-blind** (`eval.json` / `results.json` withheld) with an identical
  allow-list; the rule-edit subagent still gets row IDs only. A new
  `BREAKING CHANGE:` guard in `spp-loop.md` forbids any extraction "shape
  change" that smuggles in a new stage input — span-offsets-vs-gold or a
  per-row score to the auditor (#2), row content to rule-edit (#3), or a new
  file to the discrepancy allow-list (#1). Doc-only; no runner/scoring change.
- **v0.10 extraction scoring wired end-to-end** (`skills/run/scripts/eval.py`;
  `skills/run/scripts/tests/test_eval_extraction.py`;
  `skills/run/scripts/tests/test_inference_structured.py`). The K>1
  multi-field scoring path now scores extraction fields: the runner already
  JSON-encodes list/object field values (`inference.py` `_parse_structured`)
  and `_metrics` parses a JSON string or a real list, so an extraction field's
  variable-length item array flows from model output → `parsed_fields` →
  `compute_field_metric` with no special-casing. `compute_eval_multifield`
  gains an optional per-field `gold_column` override so a metric whose gold
  lives in a differently-named column scores correctly — the `leakage` metric
  predicts a rewritten text in the field but scores it against a
  forbidden-token column (the spp-ex Module 1 shape; DESIGN §7.1.11). An
  extraction prediction that is an empty array is a valid "nothing to extract"
  answer (F1 1.0), not a parse failure; only a missing/null field is a failure.
  Methodological implication: scoring stays mechanical — gold and prediction
  are compared by the pure alignment functions from bucket 3, no model in the
  path (**invariant #13**). Additive and backward-compatible: `gold_column`
  defaults to the field name, so every existing plan is unchanged. Suite:
  279 → 286 tests.
- **v0.10 extraction metric family** (`skills/run/scripts/_metrics.py`;
  `skills/run/sub-skills/metric-design/SKILL.md` §3.1, §6;
  `skills/run/scripts/tests/test_extraction_metrics.py`). Adds the
  alignment-based metrics the extraction mode scores against:
  `extraction_f1` / `extraction_precision` / `extraction_recall` (align
  predicted items to gold one-to-one by normalized text, with type-awareness
  on by default), `span_f1` (align by character-offset Intersection-over-Union
  at or above a configurable `iou_threshold`, default 0.5), and `leakage` (the
  deterministic redaction metric — 1 − the fraction of forbidden gold tokens
  surviving in the output). Methodological implication: every extraction metric
  is a **pure function of (prediction, gold)** with no model in the scoring path
  — **invariant #13 holds**, the same way it does for classification; this is
  the property that admits extraction while generation/RAG (which would need an
  LLM judge) stay out (§7.1.3). The metrics settle the alignment-policy knob the
  §7.1.11 pin deferred: span matching is overlap-threshold (configurable IoU),
  text matching is exact-normalized, type-awareness via `match_type`. Additive
  and backward-compatible — no existing metric changes; the `metric-design`
  extraction sub-table activates only when `plan.md` §1 `TASK_MODE` is
  `extraction`. Suite: 253 → 278 tests.
- **v0.10 design pin — structured extraction as a designer-agent mode**
  (`DESIGN.md` §7.1.11, §7, §7.1.2; `skills/run/templates/plan.md.template`
  §1). Opens the v0.10 arc: variable-cardinality, span-grounded **extraction**
  (named entities, spans, redaction targets) added as a **mode the designer
  selects** during `/spp-init`, recorded once in `plan.md` §1 as a new
  `TASK_MODE: {classification | extraction}` field and re-read by every phase.
  Methodological implication: extraction is admitted as a *generalization* of
  the methodology, not a new one, because it keeps a fixed ground truth and a
  mechanical metric — **invariant #13 holds** (span/alignment metrics are pure
  functions of prediction and gold, no model in the scoring path), which is
  the dividing line that excludes generation and RAG (they would need an LLM
  judge or a non-prompt fix; §7.1.3). The load-bearing property the arc is
  held to is that each isolated stage's allow-list **membership is unchanged**
  — only the **content shape** inside already-allowed artifacts changes (a
  "disagreed" row becomes a span misalignment, not a label mismatch) — so the
  per-stage isolation invariants (#1–#3) and the four-command set (#20) are
  preserved; extraction is a mode, not a fifth command. `TASK_MODE` is
  additive and backward-compatible: absent or unset reads as `classification`,
  so every pre-v0.10 plan is unchanged.
- **v0.10 designer mode selection + schema-designer extraction branch**
  (`skills/run/agents/designer.md`; `skills/run/sub-skills/schema-designer/`).
  The designer now runs a **task-mode identification** step first in the
  consultation (before feature-grouping and the schema-designer invocation),
  asking classification vs extraction and recording `TASK_MODE` in `plan.md`
  §1; §5.1's task-definition questions gain an extraction reframe (item/entity
  types, span-boundary calibration, the empty-item case). The `schema-designer`
  sub-skill admits the **extraction schema shape** (a variable-cardinality
  `array` of items — strings, or objects with `text`, an optional `type` enum,
  and optional `start`/`end` offsets) and gains **mechanical rule 8**:
  `TASK_MODE` / schema-shape consistency. Methodological implication: rule 8 is
  a new precondition on the **G1 schema-designer verdict gate** — an extraction
  mode with a bare-enum schema, or a classification mode with an unbounded
  item-array schema, is a mechanical `not-ready`. The check reads `TASK_MODE`
  only to select which shape is required; it adds no other stage input.
  Worked Example 5 and the `extraction-ready` fixture demonstrate the path;
  the four existing schema-designer fixtures are updated to account for rule 8
  (all classification, all consistent).

### Changed

- **Roadmap resequenced** (`DESIGN.md` §7.1.2): structured extraction takes
  the **v0.10** slot; multi-prompt / **decomposition** moves to **v0.11**,
  because extraction is self-contained (it does not change the isolation
  contract) while decomposition does. The `DESIGN.md` §7 v1 scope statement is
  amended accordingly — classification **and** extraction are in scope, and
  generation / RAG / agentic prompts are reaffirmed as deliberate non-goals
  (§7.1.3), correcting the prior "roadmap (v0.2+)" wording that conflicted
  with §7.1.3.
- **v0.10 close-out: retrospective audit + README roadmap** (`DESIGN.md`
  §7.1.11; `README.md` roadmap). The §7.1.11 locked-invariants posture is
  upgraded to a **retrospective audit** with per-invariant file citations
  (#13 model-free metrics, #1–#3 membership-unchanged isolation, #15
  `TASK_MODE` contract, #12 six-section prompt, #20 four-command set; suite
  289). The README roadmap is resequenced to match: **v0.10** is structured
  extraction, **v0.11** is prompt decomposition, **v1.0** is stabilization.

---

## [0.9.0] — 2026-06-08

The v0.9 development arc: **a prompt-structure advisor.** spp gains a
`structure-advisor` sub-skill — the structural sibling of v0.5's output-form
`technique-advisor` — seeded with **batch I/O**. The `/spp-loop` discrepancy
stage consults it and can surface, as advisory, ungated output, a
recommendation to send multiple input rows per inference call to amortize the
shared prompt; the trigger is matched only from signals already on the
discrepancy allow-list (observed cost/latency in `results.json`, task shape in
`plan.md` §2), so it **expands no allow-list**, and row-independence is a
user-confirmed precondition. Adopting it is a `plan.md` §11 revision; the
batched runner (`--batch-size N`, default 1 = single-row, unchanged) then runs
a **mandatory batch-invariance check** — a sample is run one-per-call and
N-per-call, and any divergence beyond threshold falls back to single-row
scoring — so a batch that reads across rows can never inflate the score that
drives stop/ship decisions (**invariant #13** held mechanically, not by
trust). Multi-prompt / decomposition is deferred to its own v0.10 arc because
it extends the per-stage isolation contract. All twenty-one §7.1.1 invariants
remain intact (DESIGN.md §7.1.10 audit). Suite: 234 → 253 tests.

### Added

- **v0.9 design pin — prompt-structure advisor (batch I/O)** (`DESIGN.md`
  §7.1.10, §7.1.2). Opens the v0.9 arc: a `structure-advisor` sub-skill,
  the structural sibling of v0.5's output-form `technique-advisor`, seeded
  with **batch I/O** only. Methodological implication: batch I/O is an
  inference-time efficiency change whose hazard is cross-row contamination
  (a model attending to sibling rows would inflate dev/test scores above
  deployed single-row behavior). The pin commits the runner to
  contamination-safe batching plus a **batch-invariance check** (sampled
  batched-vs-single-row comparison with single-row fallback, recorded in
  `plan.md` §11), so invariant **#13**'s mechanical scoring keeps measuring
  the deployed prompt, not a batching artifact. The advisor is consultative
  and ungated, consulted by the discrepancy stage exactly as
  `technique-advisor` is (#1/#2/#3 preserved), adopted via `plan.md` §11
  (#15), and adds no command (#20) or gate (#8–#11). All twenty-one §7.1.1
  invariants remain intact (DESIGN.md §7.1.10 audit).
- **`structure-advisor` sub-skill scaffold** (`skills/run/sub-skills/structure-advisor/SKILL.md`,
  `structures/ENTRY_SCHEMA.md`). The sub-skill doc and the catalog entry
  contract, mirroring `technique-advisor`'s identity → decision → procedure →
  worked-examples → cross-skill-constraint → output-spec shape. The entry
  contract adds one required field over `technique-advisor`'s — `independence`
  — capturing the per-row-independence guard, since a structural change can
  co-locate rows in one call (the one way a structure can quietly invalidate
  the score, #13). The advisor's trigger is sourced only from the discrepancy
  stage's existing allow-list — observed cost/latency in `results.json` and
  task shape in `plan.md` §2 — with row-independence surfaced as a
  user-confirmed precondition (empirically enforced by the batch-invariance
  check), so consulting it adds no new data path and the §7.1.10 audit's
  "expanding no allow-list" claim holds. Doc-only; the batch-I/O catalog entry,
  the runner batch path, and the discrepancy-stage wiring land in later
  buckets.
- **Batch-I/O catalog entry** (`skills/run/sub-skills/structure-advisor/structures/batch-io.yaml`).
  The v0.9 seed structure: send multiple independent rows per inference call
  (row array in, results array out keyed by index) to amortize the shared
  prompt. Its `symptom` triggers on observed per-row cost/latency in
  `results.json` (latency_ms always present; tokens_used when reported); its
  `independence` field carries the per-row-independence guard (the
  batch-invariance check with single-row fallback, recorded in `plan.md` §11)
  that keeps #13's mechanical scoring faithful to single-row behavior; and its
  `structure_form` changes only input/`<output_format>` section *content*, so
  the six-section structure (#12) is preserved. Reference-only; the runner
  batch path + invariance check land in the next bucket.
- **Runner batched-I/O path + per-row-independence guard**
  (`skills/run/scripts/inference.py`, `_schemas.py`). `inference.py` gains an
  opt-in batched mode (`--batch-size N`, default 1 = single-row, unchanged):
  it packs N rows per call as a JSON array (`[{index, input}]`) and parses a
  `{"results": [{index, …}]}` array back to per-row predictions by index — a
  missing/duplicate/out-of-range index degrades to a per-row parse failure,
  never a whole-batch failure; batch latency/tokens are attributed to the
  lead row so summary totals stay exact. Batched mode runs the **mandatory
  batch-invariance guard**: a deterministic prefix sample is run both
  one-per-call and N-per-call and, if the prediction divergence rate exceeds
  `--invariance-threshold` (default 0.1), the whole run falls back to
  single-row scoring. The outcome is recorded in the new
  `BatchInvarianceResult` schema on `results.json` (`batch_invariance`,
  `None` on single-row runs — backward-compatible). This realizes the
  §7.1.10 commitment that keeps invariant **#13**'s mechanical score faithful
  to deployed single-row behavior. Suite 234 → 251.
- **`structure-advisor` wired into the discrepancy stage + `plan.md` §11
  adoption path** (`skills/run/phases/spp-loop.md`,
  `skills/run/templates/plan.md.template`). The `/spp-loop` discrepancy stage
  now consults `structure-advisor` once per iteration (alongside the
  per-cluster `technique-advisor` check) and surfaces any structure
  recommendation as **advisory, ungated** output, exactly like a technique
  recommendation. The trigger is matched only from signals already on the
  discrepancy allow-list — observed cost/latency in `results.json` and the
  task shape in `plan.md` §2 — so the wiring **expands no allow-list**
  (#1/#2/#3 intact); row-independence is a user-confirmed precondition, not a
  read. Adoption is a user-initiated `plan.md` §11 revision marked
  `structure adoption` (new conventional marker), which records the
  batch-invariance result; nothing is auto-applied (#15). A new
  `BREAKING CHANGE:` guard documents that turning the consultation into a
  data path, a gate, an allow-list expansion, or a row-co-locating structure
  without the invariance guard is forbidden (#13). Docs/templates only.
- **End-to-end batch-I/O eval fixture**
  (`skills/run/scripts/tests/test_fixtures_batch_io.py`). Proves an adopted
  batch-I/O structure runs **inference → eval** and scores correctly with no
  network/model call (mirroring `test_fixtures_technique_forms` for output
  forms): a clean batched run scores through the real `compute_eval` like any
  other run, and — the guard's payoff — a *contaminating* batched run is
  caught by the invariance check and scored single-row, so the eval that
  drives stop/ship decisions stays faithful to deployed behavior (#13 held
  mechanically). Suite 251 → 253.
- **v0.9 closing docs + locked-invariants audit** (`DESIGN.md` §7.1.10,
  `README.md`, `structures/batch-io.yaml`). `DESIGN.md` §7.1.10's
  **Locked-invariants audit (v0.9)** is upgraded from forward-looking to a
  retrospective audit citing the shipped artifacts (the batched runner path
  and guard, the `BatchInvarianceResult` schema, the discrepancy wiring, the
  `structure adoption` marker, and the tests). `README.md`'s roadmap is
  updated for the v0.9 (batch-I/O) / v0.10 (decomposition) split. The
  `batch-io.yaml` `runner_support` is corrected — the batched path is now
  implemented (it previously read "not yet on the current runner").

### Changed

- **Roadmap re-sequenced** (`DESIGN.md` §7.1.2): v0.9 narrowed to the
  batch-I/O seed; **multi-prompt / decomposition** split into its own
  **v0.10** arc (prompt-graph runner + per-node failure attribution), which
  extends the isolation contract and must reconcile with the README's
  manual feature-group-splitting guidance. The version slots remain
  sequencing intent, not a contract (§7.1.2).

---

## [0.8.0] — 2026-06-04

The v0.8 development arc: **operational hardening** — making two robustness
properties the methodology already relied on *mechanical*, ahead of the 1.0
freeze. (1) **Per-step loop resumption:** an interrupted `/spp-loop`
iteration now resumes at its first incomplete step instead of being
discarded, via a `run_NN/state.json` journal that records step completion
and artifact hashes; a resumed stage re-enters with its **original
allow-list**, so resumption changes *when* a stage runs, never *what it
sees*. (2) **The sacred test set, enforced mechanically:** `split.py`
materializes the test partition as its own read-once `data/test.csv` (the
loop reads a test-free `data/train_dev.csv`), and spp's **first
`PreToolUse` hook** denies any `data/test.csv` read unless the access
ledger is `authorized` — `/spp-finalize` authorizes its single held-out
read and seals the ledger afterward, so the loop is barred and a second
finalize is refused. Both items **strengthen** existing invariants (#6/#7
sacred test set; #1/#2/#3 per-stage isolation) and extend the
atomic-checkpoint discipline (#16); no metric, output space, gate, or
command changes. The hook is a guardrail against the common leak paths, not
a sandbox (documented honest boundary). All twenty-one §7.1.1 invariants
remain intact (DESIGN.md §7.1.9 audit). Suite: 176 → 234 tests.

### Added

- **v0.8 closing docs + locked-invariants audit** (`DESIGN.md` §7.1.9,
  `hooks/README.md`). Closes the v0.8 arc. `DESIGN.md` §7.1.9's
  **Locked-invariants audit (v0.8)** is upgraded from the forward-looking
  pin to the detailed, evidence-backed per-invariant form (matching the
  v0.6/v0.7 audits), confirming all twenty-one §7.1.1 invariants and citing
  the shipped journal (`_journal.py`), hook (`sacred_test_guard.py`), ledger
  (`_ledger.py`), the split materialization, and the tests for the two
  *strengthened* groups (#6/#7 mechanical read-once; #1/#2/#3
  allow-list-preserving resume) plus #16's extension. New `hooks/README.md`
  documents spp's first shipped hook: what it guards, the fail-closed
  ledger contract (`sealed`/`authorized`/`consumed`), the plugin-hook
  mechanism, and the honest boundary (a guardrail against the common leak
  paths, not a sandbox). Docs-only; 234 tests unchanged.

- **Sacred-test-set ledger handshake — the hook goes live**
  (`skills/run/scripts/_ledger.py`, `phases/spp-finalize.md`,
  `test_ledger.py`). `_ledger.py` is the writer side of the access ledger
  (`data/.test_access.json`): states `sealed` (default; also absent/
  malformed — fail-closed) / `authorized` / `consumed`, with `authorize`
  refusing once `consumed` (a second `/spp-finalize` cannot re-read the
  test set). `/spp-finalize` now **authorizes** before its single read
  (step 3), reads the test rows from `data/test.csv` (pre-v0.8 fallback:
  `baseline.csv`), and **consumes** (seals) after the evaluation completes
  (step 5, before any score reaches the user at G5) — the mechanical
  embodiment of read-exactly-once, complementing pre-condition 8. The
  ledger is added to finalize's outputs. The writer (`_ledger`) and the
  independent reader (the hook) agree on the file and `status` field; an
  end-to-end test proves the hook denies a `test.csv` read until
  `authorize`, allows it while authorized, and denies again after
  `consume`. 9 new tests; suite now 234 green.

- **Sacred-test-set `PreToolUse` hook — spp's first shipped hook**
  (`hooks/hooks.json`, `hooks/sacred_test_guard.py`,
  `test_sacred_test_guard.py`). Makes read-once protection of the test set
  **mechanical** instead of disciplinary (DESIGN.md §7.1.9). The hook
  matches `Read|Bash` and **denies** any read of a task's `data/test.csv`
  unless the co-located ledger (`data/.test_access.json`) has
  `status: "authorized"` — **fail-closed**: a missing, unreadable, or
  non-authorized ledger denies. It guards a `Read` whose `file_path` is a
  `test.csv` directly inside a `data/` dir, and a `Bash` command that names
  a `.../data/test.csv` path (best-effort string match). Everything else
  passes untouched; denies emit the current `hookSpecificOutput` /
  `permissionDecision: "deny"` form. The honest boundary is documented: a
  guardrail against the common leak paths, not a sandbox. This bucket ships
  the **guard mechanism only** (default-deny; the ledger is read, never
  written) — `/spp-finalize`'s authorization handshake and its single
  authorized `test.csv` read land in the next bucket, making the guard
  live. The `Bash` path match is anchored (segment-boundary lookbehind +
  extension lookahead) so it does not over-block adjacent files like
  `data/test.csv.gz` or a different `mydata/test.csv`, while still denying
  `./`, nested, and absolute `data/test.csv` paths. 21 new tests (decision
  logic + path-matching edges + the stdin/stdout contract); suite now 225
  green.

### Changed

- **Loop reads the test-free train+dev view** (`phases/spp-loop.md`). The
  v0.8 data-source switch: `/spp-loop` now reads all train+dev row content
  (inference inputs, ground-truth labels, discrepancy disagreed-row
  content) from `data/train_dev.csv` — the materialized view that
  **physically contains no test rows** — instead of filtering
  `baseline.csv`, so the loop never opens a file holding the sacred test
  set. Pre-v0.8 splits (no `train_dev_csv` in `splits.json`) fall back to
  the prior `baseline.csv`-by-row-id behavior. This **strengthens the
  discrepancy allow-list**: its data file now physically excludes the test
  partition, so the stage cannot surface a test row even by mistake. The
  rule-edit "no row content" exclusion list (and the matching Versioning
  breaking-change clause) now name both `train_dev.csv` and `baseline.csv`,
  and the §8 sacred-test-set statement reflects the separate `test.csv`
  (guarded by the forthcoming hook). Doc-only; 204 tests unchanged. The
  per-stage isolation contract is preserved/strengthened (DESIGN.md
  §7.1.9, §4.2).

### Added

- **Read-once `test.csv` + train+dev view materialization**
  (`skills/run/scripts/split.py`, `_schemas.py`, `test_split.py`). The first
  bucket of the v0.8 sacred-test-set-hook sub-arc (DESIGN.md §7.1.9).
  `make_splits` now materializes the test partition as its own
  `data/test.csv` — the file spp's forthcoming `PreToolUse` hook will guard
  — and a `data/train_dev.csv` view the loop reads, which **contains no test
  rows**, so the loop never opens a file holding the sacred test set. Both
  preserve the baseline's columns and row order; `SplitsJSON` gains additive
  `test_csv` / `train_dev_csv` fields (None in pre-v0.8 splits, where the
  loop falls back to reading `baseline.csv` by row-id filter). Materialization
  is on by default (`materialize_partitions=True`). 6 new tests; suite now
  204 green. Wiring the loop's reads to `train_dev.csv` and the hook
  enforcement land in the next buckets.

### Changed

- **Loop doc recovery model: discard → per-step resume**
  (`phases/spp-loop.md`). Closes the v0.8 resumption sub-arc's
  user-facing docs. The two failure-mode rows bucket 3 missed — *User
  Ctrl-C mid-iteration* and *Filesystem write error* — are rewritten from
  the old "discard the partial iteration / re-run steps 6–13" model to the
  journal-backed per-step resume (re-enter at the first incomplete step;
  completed steps are not re-run; discard-and-restart remains an explicit
  fallback). The README needed no change — it carries no stale
  restart-on-interruption statement, and its resumability description is a
  v0.8-release update, not a correction.

### Added

- **Resume-isolation audit** (`skills/run/scripts/tests/test_resume_isolation.py`).
  Codifies, as executable assertions, that per-step resume (DESIGN.md
  §7.1.9) does not weaken the §4.2 isolation contract: the journal records
  step **identity** (a SHA-256) only — never artifact content — so even a
  score-bearing `eval.json` cannot leak through it; its public surface
  (`first_incomplete` / `load_journal`) returns a step name or names+hashes,
  consumed only by the orchestrator for control flow, never read by a stage.
  A structural test pins the journal's serialized shape to identity/control
  fields only, so a future change that smuggled a stage input into the
  journal (an `inputs` field, an inlined body, a cached score) fails the
  test. 4 new tests; suite now 198 green.

- **Per-step loop resume detection + contract** (`skills/run/scripts/_journal.py`,
  `phases/spp-loop.md`, `test_journal.py`). Adds the `first_incomplete`
  resume-point primitive (first step that is not present-and-integral; the
  torn/edited/deleted step is the resume point, not the one after it) and
  the canonical `LOOP_STEPS` order — with `scoring` journaled as its two
  sub-steps (`inference` → `results.json`, `metrics` → `eval.json`) so a
  crash after the expensive inference re-enters at the cheap metrics
  recompute. `phases/spp-loop.md` now documents the resume contract: the
  orchestrator records each step after its artifact commits and, on entry,
  re-enters at `first_incomplete` — re-invoking each remaining stage with
  its **original allow-list** (the journal feeds no stage new inputs;
  resumed discrepancy gets no prior-iteration artifacts, rule-edit no row
  content, auditor stays score-blind). §7 resumability and pre-condition 10
  are rewritten from discard-the-iteration to per-step resume, with the
  iteration-unit discard kept as an explicit fallback (DESIGN.md §7.1.9,
  §8.2). 5 new tests; suite now 194 green.

- **Iteration state journal** (`skills/run/scripts/_journal.py`,
  `_schemas.py`, `test_journal.py`). The v0.8 loop-resumption foundation:
  `StepRecord` / `IterationJournal` schemas plus `_journal.py` helpers —
  `sha256_file`, `record_step` (atomic, idempotent in-place replace,
  relative-keyed artifact hashes), `load_journal`, and `step_is_complete`
  (a step counts as done only when recorded **and** every artifact is
  present with a matching hash, so torn writes / post-hoc edits are re-run,
  not trusted). `record_step` rejects an empty artifact list (which would
  make a step vacuously "complete") and an artifact outside the iteration
  directory, both with explicit guard messages. The journal records step
  **completion and artifact identity only** — never a stage's inputs — so
  resuming from it cannot widen any allow-list (auditor stays score-blind,
  rule-edit gets no row content, discrepancy gets no prior-iteration
  artifacts; DESIGN.md §7.1.9, §4.2). Resume-point selection is a later
  bucket. 13 new tests; suite now 189 green.

- **v0.8 design pin: operational hardening** (`DESIGN.md` §7.1.9). Pins the
  v0.8 arc — two robustness items before the 1.0 freeze, shipped as two
  sub-arcs, **resumption first**. (1) **Loop resumption mid-iteration**: the
  cognitive step becomes the unit of recovery, journaled in
  `run_NN/state.json` (per-step completion + artifact hashes, atomic
  writes), re-entering each stage with its **original allow-list** so a
  resumed auditor stays score-blind, rule-edit gets no row content, and
  discrepancy gets no prior-iteration artifacts — resumption changes *when*
  a stage runs, never *what it sees*. (2) **Sacred-test-set hook**: `split.py`
  materializes the test partition as a read-once `data/test.csv`, and spp's
  **first `PreToolUse` hook hard-blocks** any read of it outside the single
  `/spp-finalize` read (tracked by a ledger), turning read-once protection
  from disciplinary to mechanical — with a documented honest boundary (a
  guardrail against the common leak paths, not a sandbox). Two invariant
  groups are *strengthened* (#6/#7 mechanical read-once; #1/#2/#3
  isolation-preserving resume) and #16 extended; all twenty-one §7.1.1
  invariants remain intact. **Supersedes** the §8.2 "interruption requires
  restart" stance (the iteration-unit fallback remains valid). DESIGN-only;
  no code yet.

### Changed

- **DESIGN.md §8.2 marked superseded by v0.8** (§7.1.9). The pre-v0.8
  defer-to-restart stance is retained as the rationale for why the
  iteration-unit fallback still exists, but per-step resumption is now the
  documented default.

---

## [0.7.0] — 2026-06-02

The v0.7 development arc: **judge-panel-assisted baseline labeling**. A new
`label-panel` sub-skill synthesizes gold labels for tasks whose label space
is fixed but whose ground truth requires judgment (tone, helpfulness,
coherence, style) — and **only where the canonical baseline arrives with no
label column**, completing `preprocess`'s "maps existing columns, never
invents labels" boundary. Five score-blind Claude subagents judge each row;
≥4-of-5 agreement auto-accepts, weaker splits escalate to human
adjudication. The load-bearing lock is the **cross-family gate**:
same-family judges launder the predictor's bias as "consensus," so the gate
resolves the production model's family deterministically and hard-blocks an
Anthropic-family predictor against the Claude panel. The human keeps
authority as **override-plus-visibility** — confident-consensus labels
freeze, the human signs off escalated splits and can override any frozen
label including test-set rows via the `label_panel.json` audit trail. Labels
freeze **once, pre-split, uniformly** (sacred test set preserved) and are
read downstream by the same mechanical metric — no LLM enters the scoring
path, so the LLM-as-judge-in-scoring non-goal (DESIGN.md §7.1.3) is not
re-opened and metric independence (#13) is intact. Wired into
`/spp-baseline` as a sub-skill branch, not a new gate or command. All
twenty-one §7.1.1 invariants are unchanged (DESIGN.md §7.1.8 audit).

### Added

- **v0.7 integration test + locked-invariants audit**
  (`skills/run/scripts/tests/test_label_panel_pipeline.py`, `DESIGN.md`
  §7.1.8). Closes the v0.7 arc. The integration test drives a panel-labeled
  baseline through `split.py` and `eval.py`, proving the frozen labels flow
  into mechanical scoring and that `eval.py` never reads `label_panel.json`
  — invariant #13 demonstrated in practice. `DESIGN.md` §7.1.8's
  **Locked-invariants audit (v0.7)** is upgraded from the forward-looking
  pin to the detailed, evidence-backed per-invariant form (matching the
  v0.6 audit), confirming all twenty-one §7.1.1 invariants untouched and
  citing the shipped gate (`_models.py`), aggregator (`label_panel.py`),
  and integration test for the seven actively preserved (#1/#2/#3, #6/#7,
  #13, #20). Suite now 176 green.

- **Label-panel support-tone fixture**
  (`skills/run/sub-skills/label-panel/fixtures/support-tone/`,
  `test_label_panel_fixture.py`). A subjective-label task (support-reply
  tone) whose canonical baseline arrives with **no label column** — the
  case label-panel exists for. Ships `baseline_unlabeled.csv`, `votes.json`
  (a non-Anthropic predictor so the gate passes; 8 confident rows + 2
  splits), `decisions.json` (human adjudication), and the golden
  `expected_baseline.csv`. The test drives the real pipeline
  (aggregate → queue → resolve → write) and asserts it reproduces the
  golden, plus the escalation routing and queue contents. 3 new tests;
  suite now 175 green. Realizes `DESIGN.md` §7.1.8.

- **Wire `label-panel` into `/spp-baseline`**
  (`skills/run/phases/spp-baseline.md`). Step 4 (preprocess) now notes that
  a missing label column is not invented — it routes to step 5, which
  gains a **label-synthesis branch**: when the ground truth requires
  judgment and labels are absent, the command offers the v0.7 `label-panel`
  sub-skill (cross-family gate first, 5-judge / ≥4-of-5, splits escalate to
  human adjudication, human override of any frozen label via
  `label_panel.json`, run once pre-split, never in the scoring path).
  Manual labeling stays the override surface — the panel is offered, not
  imposed (placement decision: a sub-skill branch, not a new gate/command,
  so the four-command / six-gate vocabulary is unchanged). §6 Outputs adds
  the conditional `data/label_panel.json` row and the `LABEL_SYNTHESIS`
  plan record; Versioning gains the matching breaking/non-breaking notes.
  Methodology-affecting; realizes `DESIGN.md` §7.1.8.

- **v0.7 plan template fields** (`skills/run/templates/plan.md.template`,
  `examples/*/config/plan.md`). §5 gains **`MODEL_FAMILY`** (default
  `auto` — the cross-family gate resolves the family from
  `MODEL_IDENTIFIER`; an explicit family is the on-record fallback only
  when the resolver doesn't recognize the model, and never overrides a
  recognized one). §6 gains **`LABEL_SYNTHESIS`** (default
  `none (labels human-provided or already present)`; when the `label-panel`
  sub-skill synthesized labels it records the resolved production family,
  the panel size/consensus rule, and the human-adjudicated escalation
  count). Validation rules 15–16 added. The six example plans get both
  fields filled with their defaults. Realizes `DESIGN.md` §7.1.8.

- **Label-panel adjudication workflow** (`skills/run/scripts/label_panel.py`,
  `test_label_panel.py`). `build_escalation_queue` produces the human's
  worklist — **only** escalated rows (the mandatory review set), each with
  the row input, language, all five votes + rationales, the tally, and the
  plurality. `apply_decisions` applies human labels: a decision on an
  escalated row marks `human_resolved`; a decision that *changes* an
  already-frozen label marks `human_overridden` (the operationalization of
  "authority as override-plus-visibility," including over test-set rows); a
  decision equal to the current label is a no-op. Validates row ids and
  label space; recomputes the summary. CLI gains `queue` and `resolve`. 7
  new tests; suite now 172 green. Realizes `DESIGN.md` §7.1.8.

- **`label_panel.py` consensus + I/O** (`skills/run/scripts/label_panel.py`,
  `test_label_panel.py`). The mechanical half of the panel — it never
  judges a row. `aggregate_votes` runs the cross-family gate **first**,
  validates each row has exactly `panel_size` votes within the label space,
  tallies consensus (≥`consensus_threshold` → `auto_accepted` with
  `final_label` set; weaker → `escalated`), and records the deterministic
  plurality plus the per-language escalation disclosure (stable across the
  aggregate→resolution transition; populated only when ≥2 languages).
  `write_labeled_baseline` freezes the `label` column only when every row
  is resolved and the panel and baseline row sets match exactly (no
  silent drops, no drift). CLI: `aggregate` / `write-labels`. 15 new
  tests; suite now 165 green. Realizes `DESIGN.md` §7.1.8.
- **Cross-family gate** (`skills/run/scripts/_models.py`, `test_models.py`).
  The load-bearing v0.7 lock: `resolve_family` maps a model string to a
  canonical family **deterministically** (a recognized model classifies
  itself and that match wins over any declared family, so a known model
  cannot be relabeled to bypass the gate; an unrecognized model with no
  declared `model_family` raises `UnknownModelFamilyError` rather than
  defaulting). `assert_cross_family` hard-blocks with `SameFamilyError`
  when the production model shares the judge panel's family (Anthropic),
  and returns the resolved family to record in `label_panel.json`. 24 new
  tests; suite now 150 green. Realizes `DESIGN.md` §7.1.8.
- **`label_panel.json` schemas** (`skills/run/scripts/_schemas.py`).
  `LabelVote` (one judge's label + rationale), `LabelPanelRow` (per-row
  votes, `vote_counts` source-of-truth tally, plurality, `disposition` in
  {`auto_accepted`, `escalated`, `human_resolved`, `human_overridden`},
  `final_label`, optional `language`), `LabelPanelSummary` (disposition
  counts + `per_language_escalation` disclosure), and `LabelPanelJSON`
  (records the cross-family gate decision — `production_family` vs
  `judge_family` — panel config, label space, and rows). The artifact is
  created before any split and feeds no scoring path; `eval.py` never
  reads it. Additive; existing 126 tests green. Realizes `DESIGN.md`
  §7.1.8.
- **`label-panel` sub-skill** (`skills/run/sub-skills/label-panel/SKILL.md`).
  The v0.7 baseline-labeling sub-skill (seventh in `spp`), shipped
  standalone ahead of phase wiring. Defines the protocol: the
  cross-family **family gate** (run first, hard-blocks an
  Anthropic-family predictor against the Claude judge panel, deterministic
  model→family resolution with a `plan.md` `model_family` fallback), the
  **five score-blind independent judges** (each returns one fixed label +
  rationale; independence makes the majority meaningful), **≥4-of-5
  consensus** with splits escalating to human adjudication, **human
  authority as override-plus-visibility** (auto-accepted labels freeze,
  the human resolves splits and can override any frozen label including
  test-set rows via `label_panel.json`), and the **judge-language
  coupling** disclosure. §5 pins the LLM-judge boundary: the panel creates
  a frozen baseline and never enters the scoring path, so `metric-design`
  §5 and invariant #13 are intact. Realizes `DESIGN.md` §7.1.8.
- **v0.7 design pin: judge-panel-assisted baseline labeling**
  (`DESIGN.md` §7.1.8). Pins the v0.7 arc — a `label-panel` sub-skill
  that synthesizes gold labels **only where the canonical `label` column
  is absent**, via a five-judge Claude-subagent panel (score-blind,
  ≥4-of-5 consensus auto-accepts, splits escalate to human
  adjudication). Methodological core: a **cross-family family gate** that
  hard-blocks when the production model is Anthropic-family (same-family
  judges launder the predictor's bias as consensus), and **human
  authority as override-plus-visibility** — confident-consensus labels
  auto-freeze, the human signs off escalated splits and can override any
  frozen label including test-set rows via the `label_panel.json` audit
  trail. The panel creates a **frozen baseline**, never enters the
  scoring path, so it does not re-open the LLM-as-judge-in-scoring
  non-goal (§7.1.3) and leaves metric independence (#13) intact. Includes
  the **Locked-invariants audit (v0.7)**: all twenty-one §7.1.1
  invariants untouched, with the seven actively preserved (#1/#2/#3,
  #6/#7, #13, #20) called out. DESIGN-only; no code yet.

---

## [0.6.0] — 2026-06-02

The v0.6 development arc: **input preprocessing, of which multilingual is
one facet**. A new `preprocess` sub-skill is the front gate of
`/spp-baseline` — it profiles a user's raw data, proposes a column
mapping, and authors a deterministic, human-reviewed `preprocess.py` that
maps it to spp's canonical `baseline.csv`. The agent examines columns
once and writes a script; it is never in the per-row data path, runs once
pre-split on the whole dataset (sacred test set preserved), and maps
existing columns rather than inventing labels. Multilingual handling
rides on that canonical shape: language-stratified splits, a per-language
metric slice in `eval.json`, Unicode-correct (NFC + case-fold) string
comparison, per-language failure attribution in the discrepancy stage,
and a dependency-free truncation pre-flight. Everything is data-driven
and backward-compatible — the per-language machinery auto-activates only
when an optional BCP-47 `language` column carries two or more distinct
values, so single-language projects are unaffected. All twenty-one
§7.1.1 invariants are unchanged (DESIGN.md §7.1.7 audit).

### Added

- **v0.6 locked-invariants audit + fixtures** (`DESIGN.md` §7.1.7,
  `examples/*/config/plan.md`, integration test). Closes the v0.6 arc.
  `DESIGN.md` §7.1.7 gains a **Locked-invariants audit (v0.6)** block
  confirming all twenty-one §7.1.1 invariants are untouched, calling out
  the seven the arc had to actively preserve — the isolation set
  (#1/#2/#3), the sacred test set (#6/#7), metric independence (#13), and
  the four-command set (#20). A new end-to-end integration test chains the
  real `preprocess.py` → `split.py` → `eval.py` on a multilingual dataset,
  proving the facets compose off the one canonical `language` column. The
  six shipped example plans gain the `LANGUAGE_COVERAGE` (`monolingual`)
  and `PREPROCESS_MAPPING` (`identity (data already canonical)`) §6 fields
  for template conformance.

- **v0.6 per-language attribution in the discrepancy stage**
  (`discrepancy.py`, `phases/spp-loop.md`). The discrepancy skeleton now
  reports a **per-language failure rate** in its Summary (disagreed/total
  per `language` tag) when the baseline carries a `language` column with
  two or more distinct values — data-driven, counts only, no row content.
  `spp-loop.md` §4 step 8 documents that the discrepancy subagent
  consumes the `per_language` slice from the already-allow-listed
  `eval.json` plus the `language` tag on disagreed rows to surface which
  language(s) underperform and attribute clusters by language.
  Methodological note: this is descriptive attribution, **not a new data
  path** — language is a metric slice plus a column the subagent already
  reads, so the discrepancy allow-list and row-content non-persistence are
  unchanged, and the rule-edit and auditor stages are untouched. New
  `--language-column` flag on `discrepancy.py`.

- **v0.6 truncation pre-flight** (`inference.py`, `scripts/README.md`).
  A dependency-free token-budget pre-flight: when `inference.py` is given
  a `--context-window`, it warns about rows whose estimated prompt
  (system prompt + row input) exceeds the window minus the response
  reservation (`--max-tokens`), worst rows first. `estimate_tokens`
  counts ASCII at ~4 chars/token and every non-ASCII character as one
  token, so it errs high for verbose-tokenizing scripts (CJK, Thai,
  Devanagari) — a silently truncated row yields a wrong prediction. The
  check is **advisory and never blocks**, is **keyed on token count, not
  language** (it is a correctness safeguard for any long row, not a
  multilingual feature), and is skipped entirely when no context window
  is supplied (spp does not guess a model's window). No new dependency.

- **`preprocess` wired into `/spp-baseline`** (v0.6;
  `phases/spp-baseline.md`, `templates/plan.md.template`). Preprocessing
  is now the first consultation step (new step 4): the command invokes
  the `preprocess` sub-skill to profile the raw data, propose a column
  mapping, and author `preprocess.py`; the user **reviews and approves
  the mapping and the script before it runs** (a review that precedes G2
  and reuses gate discipline **without adding to the G1–G6 set** —
  invariant #20). On approval the script runs once, pre-split, producing
  the canonical `baseline.csv`; when the data is already canonical the
  step is a recorded no-op. The column mapping is recorded in a new
  `plan.md` §6 `PREPROCESS_MAPPING` field (validation rule 14), and
  `preprocess.py` is a new (third) command output. The numbered steps
  renumber 4→12 accordingly. Methodological implication: canonicalization
  is human-reviewed and deterministic, runs once pre-split (sacred test
  set preserved), and the agent authors a script rather than entering the
  per-row data path.

- **Sample `preprocess.py` (worked, tested)** (v0.6;
  `sub-skills/preprocess/fixtures/multilingual-reviews/`). A filled,
  runnable instance of the preprocess contract that maps a raw
  multilingual review export (`review_id`/`body`/`stars_label`/`lang`) to
  the canonical `baseline.csv` (`id`/`input`/`label`/`language`),
  demonstrating a rename, a canonical-label lookup, and a BCP-47 language
  map in one script. A new test runs it end-to-end and asserts it matches
  the committed expected output and is byte-identical on re-run (the
  determinism contract).
- **`preprocess` sub-skill + `preprocess.py` contract** (v0.6;
  `sub-skills/preprocess/SKILL.md`, `templates/preprocess.py.template`).
  A consultative sub-skill (parallel to `schema-designer`) that profiles
  a user's raw data, maps it to spp's canonical `baseline.csv` columns
  (`id` / `input` / label(s) / optional `language`), and authors a
  deterministic, human-reviewed `preprocess.py` that performs the map
  mechanically. The agent examines columns once and writes a script — it
  is never in the per-row data path; re-running the script is
  reproducible. Multilingual handling is one facet: the sub-skill asks
  whether the data is multilingual and maps an existing language column
  to canonical BCP-47 tags, falling back — only when the user is unsure —
  to an on-demand deterministic language-ID library (documented install,
  not a declared dependency). Ships standalone; wiring into
  `/spp-baseline` and end-to-end fixtures land in later v0.6 buckets.
- **v0.6 scope reframe: input preprocessing** (`DESIGN.md` §7.1.7). The
  v0.6 arc expands from "multilingual data" to "input preprocessing, of
  which multilingual is one facet." A new **preprocess step** — the first
  step of `/spp-baseline` — examines arbitrary raw data via a `preprocess`
  sub-skill and authors a deterministic, human-reviewed `preprocess.py`
  that maps it to spp's canonical `baseline.csv` (`id` / `input` /
  label(s) / optional `language`). Methodological implication: the agent
  examines columns once and writes a script; it is never in the per-row
  data path, runs once pre-split on the whole dataset uniformly (sacred
  test set preserved, #6/#7), adds no fifth command (#20), and maps
  existing columns rather than inventing labels (#13). Language is asked
  of the user, and only when they are unsure does the sub-skill instruct
  the agent to install a deterministic language-ID library on demand — not
  a declared dependency (CLAUDE.md §8). Mapping a `lang`/`locale` column
  onto the canonical `language` tag becomes part of preprocessing. The
  arc bucket plan is revised to 10 buckets.
- **v0.6 multilingual-data arc design pin** (`DESIGN.md` §7.1.7). Pins the
  arc scope and the four settled directions — mixed-language datasets,
  canonical fixed labels, per-language metrics with language-stratified
  splits, and Unicode-correct string metrics plus a truncation warning —
  as bookkeeping that adds no metric family, no output shape, and no stage
  information access. The per-language machinery is **data-driven and
  backward-compatible**: it auto-activates from an optional BCP-47
  `language` column only when the data spans two or more languages, so
  single-language projects are unaffected; normalization and the
  truncation warning are correctness fixes that run unconditionally.
  Methodological implication: per-language is a metric slice like
  per-class, so all twenty-one §7.1.1 invariants are expected untouched
  (to be confirmed in the arc's final-bucket audit).
- **v0.6 multilingual contract** (`plan.md` template + `schema-designer`
  / `metric-design` sub-skills). The `plan.md` template gains an optional
  `LANGUAGE_COVERAGE` field (§6) documenting the optional BCP-47
  `language` column and the data-driven activation trigger, a
  canonical-label note (§2), a language-stratification note on the split
  key (§7), and validation rule 13. `schema-designer` §3.5 documents the
  canonical-label policy for multilingual input (per-language label
  variants are a `revise` signal); `metric-design` documents per-language
  reporting as a metric *slice* (reuses the field's chosen mechanical
  metric — no new metric family, §5 independence untouched). Contract
  only; no runner behavior yet.
- **v0.6 language-stratified splits** (`split.py`, `_schemas.py`,
  `spp-baseline.md`). When `baseline.csv` carries the optional per-row
  `language` column with two or more distinct values, `split.py`
  stratifies jointly on the label × `language` key so every split —
  including the sacred test set — is representative of the language
  distribution, and verifies every language is present in every
  partition (a missing language tag in multilingual data is a hard
  error). Data-driven, not a flag: absent or single-valued, the split is
  identical to the pre-v0.6 label-only behavior. `splits.json` gains an
  additive, backward-compatible `language_stratified` boolean recording
  the outcome (defaults to `false`; absent in pre-v0.6 files). New CLI
  flag `--language-column` (default `language`).
- **v0.6 metrics core: Unicode-correct comparison + per-language slice**
  (`_metrics.py`, `eval.py`, `_schemas.py`, `spp-loop.md`). String metric
  comparison (`exact_match`, `set_f1`, `set_jaccard`, corpus-class, and
  K=1 canonical-label matching) now NFC-normalizes and Unicode case-folds
  instead of plain lowercasing, so a correct prediction is not scored
  wrong on an invisible encoding difference (composed vs. decomposed
  accents, German `ß`↔`SS`, Turkish `İ`↔`i`). This is identical to the
  prior behavior on ASCII, so K=1 and monolingual scoring are unchanged
  for ASCII data. `eval.json` gains an additive `per_language` section
  (both the K=1 and K>1 paths): for each language present it reports the
  same mechanical metric — the field metric (K=1) or the cross-field
  aggregate plus a `per_field` breakdown (K>1) — over that language's
  rows. Data-driven and backward-compatible: emitted only when the
  `language` column has two or more distinct values, empty otherwise.
  Methodological implication: per-language is a metric *slice* like
  per-class — no new metric family, no LLM judge (invariant #13 intact),
  and the section lives in `eval.json`, withheld from the auditor and
  rule-edit stages (no allow-list change). New `eval.py` CLI flag
  `--language-column` (default `language`).

### Changed

- **Sub-skill registry corrected** (`skills/run/SKILL.md` §3.3). The
  table listed only the original three sub-skills and claimed the set was
  "closed at three"; it now lists all six — adding `schema-designer`
  (v0.2), `technique-advisor` (v0.5), and `preprocess` (v0.6) — and
  reframes the roster as growing by version per a structural-distinctness
  justification, rather than fixed.
- **Roadmap staged through v1.0.0** (`DESIGN.md` §7.1.2). The remaining
  post-v0.5 roadmap is sequenced into concrete minor versions: v0.6
  multilingual data, v0.7 judge-panel-assisted baseline labeling, v0.8
  operational hardening (mid-iteration loop resumption + the first
  `PreToolUse` sacred-test-set hook), v0.9 a `structure-advisor`
  sub-skill (batch I/O and multi-prompt/decomposition seeds), and v1.0.0
  stabilization. Sequencing is ordered by risk to the isolation and
  validation primitives; slots are intent, not contract.
- **Multi-judge subjective metrics reframed to v0.7
  judge-panel-assisted baseline labeling** (`DESIGN.md` §7.1.2, §7.1.3).
  Methodological implication: judgment moves to baseline label
  *creation* — frozen into the gold set, cross-family judges enforced,
  human adjudicating split votes — rather than the scoring path, so
  invariant #13 (no LLM judge in the scoring path) holds. The
  LLM-as-judge ban is now stated as a permanent boundary on the scoring
  path, not a temporary one awaiting a future metric.

### Removed

- **Cross-model synthesis removed from the roadmap, reclassified as a
  deliberate non-goal** (`DESIGN.md` §7.1.3). Methodological
  implication: `spp` optimizes a prompt for one target model, so
  specializing to that model is the objective, not overfitting to be
  corrected; synthesizing one prompt across models contradicts per-model
  optimization. Cross-model comparison remains valid as downstream model
  selection, outside spp.

---

## [0.5.0] — 2026-05-31

The v0.5 development arc: **failure-driven prompting-technique
suggestions**. v0.5 makes a small set of prompting techniques part of
spp's diagnostic methodology rather than a default output shape — when
`/spp-loop`'s real failures show a recognizable symptom, the agent names
the gap and recommends a technique to the user, who adopts it (or not)
via a `plan.md` revision; nothing is auto-applied. The vocabulary is two
asset-validated techniques (per-label binary / one-vs-rest for
competing-multi-label fields; gated-boolean for default-attractor
fields). The suggestion is a categorical recommendation surfaced to the
human, not a new data path — the discrepancy stage's allow-list is
unchanged, rule-edit still gets no row content, and the auditor stays
score-blind (all twenty-one §7.1.1 invariants preserved). The arc is
partitioned into buckets per the v0.2/v0.3/v0.4 convention.

### Added

- **v0.5 technique-suggestions design pin** —
  [`DESIGN.md`](DESIGN.md) §7.1.6 establishes the diagnostic→suggestion
  methodology as the contract subsequent PRs are written against. The
  techniques live in a new consultative **`technique-advisor` sub-skill**
  (parallel to `schema-designer` / `metric-design`) — an **extensible
  catalog** of structured registry entries (`symptom` /
  `recommendation` / `output_form` / `runner_support` / citation) that
  the project grows over time, with a "How to add a technique"
  contributor guide; the methodology core consults the catalog rather
  than hardcoding a vocabulary. The pin records the loop-time
  failure-driven origin, the isolation contract (a suggestion is a
  categorical recommendation to the human, never a row-content or score
  back-channel; adopting it is a user-approved `plan.md` revision, never
  auto-applied), the runner support needed to act on it, the two seed
  entries (one-vs-rest, gated-boolean), and the seven-bucket breakdown.
  CoT-as-field, multi-shot few-shot, and anchored-CoT are explicitly
  deferred (BREAKING / need a later arc). DESIGN-only; no code,
  template, agent, or sub-skill files change in this PR. (bucket 1 of 7)
- **`technique-advisor` sub-skill** —
  [`skills/run/sub-skills/technique-advisor/`](skills/run/sub-skills/technique-advisor/)
  adds the consultative, ungated sub-skill that maps an observed failure
  pattern to a prompting technique and recommends it to the user
  (`DESIGN.md` §7.1.6). The techniques live in an **extensible catalog**
  (`techniques/*.yaml`), each a structured entry — `id` / `name` /
  `symptom` / `recommendation` / `output_form` / `runner_support` /
  `citation` — conforming to
  [`techniques/ENTRY_SCHEMA.md`](skills/run/sub-skills/technique-advisor/techniques/ENTRY_SCHEMA.md);
  the SKILL.md carries the "How to add a technique" contributor guide.
  Seeds the catalog with the two asset-validated entries (one-vs-rest,
  gated-boolean). Consultative and ungated like `metric-design` (no
  verdict gate, not a fifth command — invariant #20 holds); the
  cross-skill rule (§5) keeps a recommendation a categorical statement to
  the human, never a row-content or score back-channel. Not yet wired
  into the discrepancy stage — that is bucket 3. (bucket 2 of 7)
- **Discrepancy stage consults the `technique-advisor`** —
  [`spp-loop.md`](skills/run/phases/spp-loop.md) §4 step 8 wires the
  discrepancy subagent to read the `technique-advisor` catalog as
  **reference material** (the same category as `prompt-architect` for
  the rule-edit subagent at step 10) and, after clustering, match each
  cluster's shared property against catalogued symptoms, recording an
  advisory **technique recommendation** in a new `discrepancy_analysis.md`
  section (field, categorical symptom observed, technique id,
  `output_form`). Methodology-affecting but isolation-preserving:
  consulting the catalog adds **no data input** to the stage's
  allow-list (the catalog carries no row content, scores, or
  prior-iteration artifacts), the recommendation is categorical and
  never carries row content, and the technique is never auto-applied —
  adopting it stays a user-initiated `plan.md` / OUTPUT_SCHEMA revision.
  New §"Versioning" breaking-change clauses guard against turning the
  consultation into a data path or making a recommendation row-specific;
  growing the catalog with a catalog-eligible entry is explicitly
  non-breaking. All twenty-one §7.1.1 invariants preserved. Surfacing
  the recommendation at the gate is bucket 4. (bucket 3 of 7)
- **Surface technique recommendations at the HITL gate (ungated)** —
  [`spp-loop.md`](skills/run/phases/spp-loop.md) §4 step 12 surfaces any
  technique recommendations from `discrepancy_analysis.md` to the user as
  **advisory output** after the verdict gate resolves. It is explicitly
  **not a gate** — it never halts the loop, reverts an edit, or blocks
  advancement (`technique-advisor` SKILL.md §2). Adopting a technique is a
  **user-initiated `plan.md` revision**: update §2 `OUTPUT_SCHEMA` to the
  technique's `output_form` and append a §11 revision-log entry whose
  Reason contains the literal substring `technique adoption` (plus a
  `PLAN_VERSION` bump); the change takes effect on the next `/spp-loop`
  invocation. [`plan.md.template`](skills/run/templates/plan.md.template)
  §11 documents the three conventional Reason markers (`auditor override`,
  `loop_spec re-validated`, `technique adoption`). The runner never
  auto-edits `plan.md` or rebuilds the prompt mid-iteration. New
  §"Versioning" clause: making the surfacing a blocking gate, or having
  the runner auto-apply a technique, is `BREAKING`. All twenty-one §7.1.1
  invariants preserved; runner support for the adopted forms is bucket 5.
  (bucket 4 of 7)
- **Runner support for the adopted technique forms** —
  [`_forms.py`](skills/run/scripts/_forms.py) reconstructs a logical field's
  effective predicted value from the constituent OUTPUT_SCHEMA keys an adopted
  technique produces, and [`eval.py`](skills/run/scripts/eval.py)'s K>1 scorer
  consumes an optional per-field `"form"` block to score it. `per_label_binary`
  (one-vs-rest) unions the truthy per-label booleans into a predicted set scored
  by the existing `set_f1`; `gated_single_select` / `gated_per_label_binary`
  read the boolean gate first and route a closed gate to "not addressed" (empty)
  before scoring the conditional sub-field with its own metric. This is
  **field-shape handling, not a new metric family** (DESIGN §7.1.6): a row is a
  parse failure only when none of a form's constituent keys parsed, and a
  field with no `"form"` block scores exactly as in v0.4 (bit-for-bit).
  `inference.py` is unchanged — it already parses the constituent keys as
  ordinary top-level fields, so reconstruction is a scoring-time concern only.
  No new dependency; new `test_forms.py` covers both forms and the gate/edge
  cases. The suggested→adopted end-to-end fixture is bucket 7. (bucket 5 of 7)
- **v0.5 locked-invariants audit** — [`DESIGN.md`](DESIGN.md) §7.1.6 gains a
  `Locked-invariants audit (v0.5)` block recording all twenty-one §7.1.1
  invariants as untouched by the arc, mirroring the v0.3 / v0.4 audits. It
  calls out the six the arc had to actively preserve: the isolation set
  (#1 per-stage isolated subagents — the catalog is reference material, not a
  data input; #2 auditor score-blindness; #3 no-row-content-to-rule-edit) plus
  the three a casual reading might think the feature touches (#12 six-section
  prompt structure — OvR/gated are within-field shapes, not new sections;
  #14 categorical-descriptive verdict tokens — the surfacing is ungated
  advisory output; #20 four-command set — `technique-advisor` is a sub-skill,
  not a fifth command). The remaining fifteen are recorded as untouched on
  their face (no new metric family #13, sacred test set #6/#7, gate strings
  #8–#11, atomic-checkpoint #16, plan.md contract #15, REPORT §5 block #21).
  DESIGN-only; no code, template, agent, or sub-skill files change. (bucket 6
  of 7)
- **End-to-end fixture + finalize-CI rider for the multi-field aggregate** —
  closes the v0.5 arc. A new
  [`test_fixtures_technique_forms.py`](skills/run/scripts/tests/test_fixtures_technique_forms.py)
  exercises a suggested→adopted technique end-to-end: a one-vs-rest `tags` field
  and a gated-boolean `status` field are scored through the real
  `compute_eval_multifield` from their constituent OUTPUT_SCHEMA keys, covering
  the gate-closed and all-keys-absent (parse-failure) paths. The rider adds
  [`_stats.bootstrap_multifield_aggregate_ci`](skills/run/scripts/_stats.py),
  generalizing the v0.3 finalize percentile bootstrap CI (DESIGN §7.1.4) to the
  K>1 aggregate: it draws one shared row-index resample across all fields
  (preserving cross-field row correlation), recomputes each field's metric, and
  re-aggregates with the run's strategy — the same path `compute_eval_multifield`
  uses. Descriptive and finalize-only: never gates the loop or weights a verdict
  (#14), and resamples the in-memory per-row columns rather than re-reading the
  sacred test set (#6 / #7). No new dependency. (bucket 7 of 7)

### Changed

- **Roadmap reshuffle: multi-judge subjective metrics, multilingual
  data, and cross-model synthesis move to v0.6** —
  [`DESIGN.md`](DESIGN.md) §7.1.2. The v0.5 slot is now failure-driven
  technique suggestions (§7.1.6); the three previously-v0.5 roadmap
  items re-point to v0.6. Roadmap scheduling only — no methodology
  change.

---

## [0.4.0] — 2026-05-30

The v0.4 release: **the K>1 multi-field runner**. v0.4 is
implementation, not new methodology — it turns the multi-field scoring
layer v0.2 specified in prose into working runner code. v0.2 generalized
the bookkeeping (OUTPUT_SCHEMA, the per-field metric set, the
three-section `eval.json`, per-field verdict scoping) but the runnable
scripts stayed v0.1.0-shaped (`eval.py` scores one label with
`{f1, accuracy, precision, recall}`; `inference.py` parses one label;
`EvalJSON` is confusion-matrix/per-class, not three-section). v0.4 makes
multi-field tasks runnable, preserving all twenty-one §7.1.1 invariants
(the methodology is unchanged; the runner only computes what the docs
already promise). The arc is partitioned into buckets per the v0.2/v0.3
convention, each landed in its own PR before downstream buckets depend
on it.

### Added

- **v0.4 K>1 multi-field-runner design pin** —
  [`DESIGN.md`](DESIGN.md) §7.1.5 establishes the runner-implementation
  layer as the contract subsequent PRs are written against: the
  canonical metric set (`metric-design` §3.1) the runner implements,
  the aggregate strategies and dimensional-nonsense refusal, the
  isolation-generalized-in-shape-not-weakened property, K=1 backward
  compatibility, the no-new-dependency decision, and the seven-bucket
  breakdown. DESIGN-only; no code, template, agent, or sub-skill files
  change in this PR. (bucket 1 of 7)
- **Structured multi-field parse (K>1)** —
  [`inference.py`](skills/run/scripts/inference.py) gains a schema-driven
  structured parse: given an OUTPUT_SCHEMA (`--schema`),
  `_parse_structured` extracts each top-level field from the model's JSON
  response as a raw string (scalars stringified, arrays/objects
  compact-JSON-encoded) with per-field parse-error tracking, and
  `_output_schema_field_names` loads the field set from the schema's
  `properties`. `_schemas.PredictionRow` gains `parsed_fields` +
  `field_parse_errors`; K=1 keeps `parsed_label`/`parse_error` and the new
  fields default to `None`/`{}`, so existing `results.json` read unchanged.
  Routing is by `--schema` presence — the v0.1.0 single-label path is
  untouched when no schema is given. Parsing stays minimal
  (canonicalization/scoring remain `eval.py`'s job, bucket 3); no new
  dependency. (bucket 2 of 7)
- **Per-field metric primitives** —
  [`_metrics.py`](skills/run/scripts/_metrics.py) is the single source of
  per-field metric computation for the canonical set (`metric-design` §3.1):
  `compute_field_metric(metric, y_true, y_pred, kwargs)` dispatches per-row
  metrics (`exact_match`, `set_jaccard`/`iou`, `set_f1`, `within_tolerance` —
  normalized comparison, empty-both = 1.0, accepted-alternative partial credit,
  mirroring spp's genuine multi-field annotation scorer, not the DSPy/GEPA
  baseline) and corpus metrics (`f1`/`macro_f1`/`balanced_accuracy`/`precision`/
  `recall`/`mae`/`rmse` over the field's column). Numeric `mae`/`rmse` score
  numeric-parseable rows; non-parseable preds surface as parse failures, not
  silent scores. No new dependency (sklearn). Standalone, unit-tested module;
  `eval.py` delegates to it in the per-field scoring wiring. (bucket 3 of 7,
  part 1 of 2 — primitives; the `eval.py` `per_field` wiring is part 2)
- **Per-field scoring in `eval.py` (K>1)** —
  [`eval.py`](skills/run/scripts/eval.py) gains `compute_eval_multifield`, which
  scores each OUTPUT_SCHEMA field's metric over its own column (gold from the
  `baseline.csv` column named after the field, predictions from `results.json`'s
  `parsed_fields`) by delegating to `_metrics.compute_field_metric`, and emits
  the `per_field` section of the three-section `eval.json` (`_schemas.FieldEval`:
  per-field metric, value, row count, parse-failure count). Routed by the new
  `--field-metrics` CLI arg ({field: {metric, kwargs}}). An absent predicted
  field scores as a mismatch and is counted as a parse failure. **Additive and
  K=1-backward-compatible**: `EvalJSON.per_field` defaults to `None` and the
  single-label `compute_eval` path is untouched. The cross-field **aggregate**
  (macro/weighted/min + dimensional-nonsense refusal) and **floor_compliance**
  are buckets 4–5, so the top-level `primary_value` is a provisional unweighted
  mean for now. No new dependency. (bucket 3 of 7, part 2 of 2)
- **Cross-field aggregate (K>1)** —
  [`eval.py`](skills/run/scripts/eval.py) `compute_eval_multifield` now computes
  the `aggregate` section of the three-section `eval.json` via
  [`_metrics.compute_aggregate`](skills/run/scripts/_metrics.py):
  `macro` (unweighted mean), `weighted` (weighted mean; missing weights default
  to 1.0), or `min` (worst field / bottleneck), selected by the new `--aggregate`
  CLI arg (default `macro`). The top-level `primary_value` is now this aggregate
  (replacing the provisional mean) — the number the loop's stop-discipline reads.
  **Dimensional-nonsense refusal** (`DESIGN.md` §7.1.5): averaging an error-family
  metric (`mae`/`rmse`, unbounded, lower-is-better) into the `[0,1]`-higher-better
  composite is refused with a guiding error — runner-side defense-in-depth behind
  `metric-design`'s plan-time revise signal. `_schemas.Aggregate` +
  `EvalJSON.aggregate` added; K=1 unaffected (`aggregate` defaults to `None`).
  Aligns with spp's genuine annotation scorer (weighted/min rollup). No new
  dependency. (bucket 4 of 7)
- **Per-field floor compliance (K>1)** —
  [`eval.py`](skills/run/scripts/eval.py) `compute_eval_multifield` now emits the
  third section of the three-section `eval.json`, `floor_compliance`
  (`_schemas.FloorCompliance`): each field's floor (from the new `--floors` JSON
  map `{field: floor_value}`) and a `met` / `unmet` / `not_specified` status
  (`met` iff the field's primary metric ≥ its floor). This is what the loop's
  `EARLY_STOP_FLOOR_UNMET` branch reads (an unmet floor while the aggregate sits
  at target) — `eval.py` emits the section; the loop owns the stop decision.
  Aligns with the genuine spp run's `thresholds.yaml` + `field_pass_soft`
  pattern (JSON instead of YAML to avoid a new dependency). The three-section
  `eval.json` (`per_field` + `aggregate` + `floor_compliance`) is now complete;
  K=1 unaffected (`floor_compliance` defaults to `None`). (bucket 5 of 7)
- **v0.4 locked-invariants audit** — [`DESIGN.md`](DESIGN.md) §7.1.5 records
  all twenty-one §7.1.1 invariants as untouched under the K>1 runner
  generalization, calling out the four the implementation had to actively
  preserve (#1 isolated subagents — content shape grows, allow-list membership
  unchanged; #3 no row content to rule-edit; #2 auditor score-blindness; #13
  per-field metric independence) and noting the scorer is the existing `eval.py`,
  not a fifth command (#20). The preservation-audit bucket, mirroring v0.2/v0.3.
  Docs-only. (bucket 6 of 7)
- **Multi-field example fixtures run end-to-end (K>1)** — the
  `multi-field-extraction` and `nested-schema` examples gain runnable scoring
  configs (`config/{schema,field_metrics,aggregate,floors}.json`) derived from
  each plan's §2/§4, plus end-to-end fixture tests
  ([`test_examples_multifield.py`](skills/run/scripts/tests/test_examples_multifield.py))
  that score each example through the real `compute_eval_multifield` against
  synthetic predictions (no model call). These are the first multi-field runs
  exercised end-to-end; they caught that the multi-field eval path now honors a
  non-default `id_column` (the examples key on `row_id`). `multi-field-extraction`
  scores `price` with `within_tolerance` (±5.0) rather than `MAE`, the §7.1.5
  resolution for including a numeric field in a bounded composite. Completes the
  v0.4 K>1 multi-field-runner arc. (bucket 7 of 7)

---

## [0.3.0] — 2026-05-29

The v0.3 release: **finalize-layer statistics**. v0.3
adds inferential statistics — a bootstrap confidence interval on the
frozen prompt's test-set aggregate (and, optionally, on the dev→test
gap) — on the per-row scores the loop already computes, reported at
`/spp-finalize`. The statistics are
**finalize-only**: computed after the loop terminates and never written
into any artifact a `/spp-loop` subagent reads, so auditor
score-blindness ([`DESIGN.md`](DESIGN.md) §4.2; invariant #2), the
sacred test set's read-exactly-once guarantee (invariants #6/#7), and
the categorical hard-token verdicts (invariant #14) are all preserved
verbatim. The arc is partitioned into buckets per the v0.2 convention,
each landed in its own PR before downstream buckets depend on it.

### Added

- **v0.3 finalize-statistics design pin** —
  [`DESIGN.md`](DESIGN.md) §7.1.4 establishes the v0.3 measurement
  layer as the contract subsequent PRs are written against: what the
  statistics are (a single-sample bootstrap CI on the frozen prompt's
  test-set aggregate, plus an optional dev→test gap CI), the
  load-bearing finalize-only safety property, the seven-bucket
  breakdown, and the scope boundary. DESIGN-only; no code, template,
  agent, or sub-skill files change in this PR. (bucket 1 of 7; the
  paired-comparison framing was corrected during implementation when
  finalize was confirmed to score a single prompt on the sacred set)
- **Per-row score retention at scoring time** —
  [`eval.py`](skills/run/scripts/eval.py) now persists a `per_row` array
  (`row_id`, `y_true`, `y_pred`, `correct`) into `eval.json` /
  `test_eval.json` (`_schemas.EvalJSON.per_row`). This is the per-row score
  vector the v0.3 finalize statistics (the bootstrap CI on the test
  aggregate, bucket 3) resample. Additive and backward-compatible — legacy
  `eval.json` without the field reads unchanged, and the K=1 classification
  path is otherwise identical. Methodology note: the array lives inside
  `eval.json`, which is already withheld from the auditor and rule-edit
  stages ([`DESIGN.md`](DESIGN.md) §4.2; invariants #2, #3), so retaining it
  changes no per-stage isolation allow-list; the discrepancy stage, which
  legitimately has score access, gains nothing it could not already derive
  from `results.json`. Doc sync: [`spp-loop.md`](skills/run/phases/spp-loop.md)
  §4 step 7 and [`spp-finalize.md`](skills/run/phases/spp-finalize.md) §4
  step 4. (bucket 2 of 7)
- **Bootstrap CI on the test aggregate** —
  [`_stats.py`](skills/run/scripts/_stats.py) computes a percentile
  bootstrap confidence interval on a scored partition's aggregate metric
  by resampling the retained `per_row` vector, and writes it into the
  `eval.json`'s `aggregate_ci` block (`_schemas.BootstrapCI`); `eval.py`
  factors out `compute_primary_metric` so a resample is scored by the same
  function as the headline number (correct for set-level metrics like F1,
  not just accuracy). At `/spp-finalize` this brackets the frozen prompt's
  test-set aggregate — the generalization interval REPORT §2 will quote
  (bucket 5). Methodology note: the CI is computed **only at finalize**,
  from an in-memory resample of an already-read score vector — no model
  calls, no second test-partition read (invariants #6/#7), never written
  into any `/spp-loop` artifact (auditor stays score-blind, invariant #2),
  and never feeds the ship-decision tree or any verdict (invariant #14).
  No new dependency — stdlib `random` only; `scipy` deliberately not added.
  Default 10,000 resamples, fixed seed. Doc:
  [`spp-finalize.md`](skills/run/phases/spp-finalize.md) §4 step 4.
  (bucket 3 of 7)
- **Bootstrap CI on the dev→test gap (overfitting interval)** —
  [`_stats.py`](skills/run/scripts/_stats.py) adds a two-sample difference
  bootstrap recording the uncertainty band on `dev_test_delta` (the gap the
  ship-decision tree reports as a point value), written into the test
  `eval.json`'s `dev_test_gap_ci` block. Dev and test are different rows, so
  the two samples are resampled independently (an unpaired difference). Opt-in
  via the `_stats.py` `--dev-eval` flag. Same finalize-only, descriptive,
  never-gating discipline as the aggregate CI (invariants #2, #6/#7, #14).
  Doc: [`spp-finalize.md`](skills/run/phases/spp-finalize.md) §4 step 4.
  (bucket 4 of 7)
- **REPORT surfaces the bootstrap intervals** —
  [`REPORT.md.template`](skills/run/templates/REPORT.md.template) §2.2 now
  renders the test-set CI (the generalization interval to quote) and the
  dev→test gap CI; §3.2 renders the best-dev-iteration CI as a labeled
  diagnostic ("not a generalization claim"); and a new §7.7 caveat explains
  that the intervals are percentile bootstraps and run wide at small N, so a
  wide interval calls for more labeled data rather than more iterations. All
  three are explicitly descriptive and non-gating (invariant #14).
  `/spp-finalize` §4 step 4 also bootstraps the best-iteration dev `eval.json`
  (for the §3 diagnostic) and §7 step 7 maps the placeholders to the
  `aggregate_ci` / `dev_test_gap_ci` blocks. Template + docs only; no code
  change. (bucket 5 of 7)
- **v0.3 locked-invariants audit** — [`DESIGN.md`](DESIGN.md) §7.1.4 records
  all twenty-one §7.1.1 invariants as untouched under the finalize-statistics
  layer, calling out the four it had to actively preserve (#2 auditor
  score-blindness, #6/#7 sacred test read-once, #14 categorical hard-token
  verdicts) and noting the estimator is a finalize-time script, not a fifth
  command (#20). The preservation-audit bucket, mirroring v0.2's bucket 6.
  Docs-only. (bucket 6 of 7)
- **`metric-design` records the v0.3 interval reporting; finalize CI fixture**
  — [`metric-design` SKILL.md](skills/run/sub-skills/metric-design/SKILL.md) §6
  documents that `/spp-finalize` reports a bootstrap CI on the aggregate metric
  (descriptive, non-gating, invariant #14) and that the sub-skill does not pick
  the interval's parameters (fixed finalize defaults), only the metric it is
  computed on; per-field intervals are future K>1 work. Adds end-to-end fixture
  tests exercising the `_stats.py` CLI on the K=1 finalize path
  (`test_stats.py`): `--eval`/`--dev-eval` writes both `aggregate_ci` and
  `dev_test_gap_ci`, and a missing `per_row` vector exits non-zero. Closes the
  v0.3 finalize-statistics arc. (bucket 7 of 7)

### Changed

- **Roadmap reshuffle: multi-judge subjective metrics and multilingual
  data move from v0.3 to v0.4** — [`DESIGN.md`](DESIGN.md) §7.1.2. The
  v0.3 slot is now the finalize-statistics layer (§7.1.4); the two
  previously-v0.3 roadmap items are re-pointed to v0.4. Roadmap
  scheduling only — no methodology change.

---

## [0.2.0] — 2026-05-14

The v0.2 release: bookkeeping generalization from single-output
classification (v0.1.0's hardcoded scope) to multi-field structured
output, hierarchical labels, and freeform extraction with
structured ground truth. The methodology principles (per-stage
information isolation, auditor judgment, sacred test set,
verdict-enforced gates, six-section prompt structure, `plan.md` as
contract) are unchanged from v0.1.0 — [`DESIGN.md`](DESIGN.md)
§7.1.1's locked-invariants inventory (bucket 6) documents which
v0.1.0 guarantees survived verbatim and which carry shape changes
that preserve substance. v0.2's planning arc partitioned the work
into seven buckets (schema layer; metrics layer; per-field
methodology application layer; sub-skill ordering layer; compat
layer; locked-invariants inventory; fixtures layer), each landed
in its own PR before downstream buckets depended on it. The
release also encodes one post-bucket-7 methodology principle
(feature-group prompt splitting) and a v0.2 example that
exemplifies its default case.

K=1 (single-output classification — v0.1.0's scope) backward
compatibility is preserved end-to-end. Legacy v0.1.0 plans
(`LABEL_SPACE` + scalar metric fields) continue to work without
modification via the runner's K=1 fallback; migration to the v0.2
template surface is opt-in via documented manual upgrade steps in
[`DESIGN.md`](DESIGN.md) §7.1.1 compat layer.

### Added

- **schema-designer recognized as G1 precondition** —
  `/spp-init` G1 dual-check operationalizes the schema-designer
  verdict precondition; gate placement (folds into G1's
  contents, no renumbering of G1–G6) pinned in
  [`DESIGN.md`](DESIGN.md) §7.1.1 sub-skill ordering layer
  (bucket 4 of 7). Mirrors `baseline-quality`'s precondition
  at G2.
- **`schema-designer` sub-skill** added at
  [`skills/run/sub-skills/schema-designer/SKILL.md`](skills/run/sub-skills/schema-designer/SKILL.md)
  as v0.2 work in progress, shipped standalone and not yet
  integrated into any phase's flow.
- **Aggregate-strategy consultation stage** in
  [`skills/run/sub-skills/metric-design/SKILL.md`](skills/run/sub-skills/metric-design/SKILL.md)
  §3.2 — picks `macro` / `weighted` / `min` across K
  per-field metrics; surfaces dimensional mismatches as
  documentary `revise` signals.
- **Per-field-floor consultation stage** in
  [`skills/run/sub-skills/metric-design/SKILL.md`](skills/run/sub-skills/metric-design/SKILL.md)
  §3.3 — optional floor per field, suggested for
  required-and-unrecoverable fields.
- **`early_stop_floor_unmet` EARLY_STOP variant** in
  [`skills/run/phases/spp-loop.md`](skills/run/phases/spp-loop.md)
  §4 step 13 — triggers at loop termination when the
  aggregate dev metric plateaus at-or-above target but
  one or more per-field floors are unmet on the best
  iteration.
- **`multi-field-per-field-verdict` auditor fixture** at
  [`skills/run/agents/auditor/fixtures/multi-field-per-field-verdict/`](skills/run/agents/auditor/fixtures/multi-field-per-field-verdict/)
  exercising per-edit-per-field verdict independence on a
  K=2 OUTPUT_SCHEMA — one rule edit, two target fields,
  mixed verdicts (`categorical` for one field,
  `row-specific` for the other).
- **Manual upgrade steps** for migrating an existing v0.1.0
  `plan.md` to the v0.2 template surface — documented in
  [`DESIGN.md`](DESIGN.md) §7.1.1 compat layer (bucket 5 of
  7). Six mechanical steps; preserves the methodology
  contract (no decisions change; only the bookkeeping shape
  moves to v0.2). No `/spp-migrate-plan` command —
  upgrade is opt-in, the runner's K=1 fallback handles
  legacy plans without modification.
- **Multi-field worked example (Example 6)** in
  [`skills/run/sub-skills/baseline-quality/SKILL.md`](skills/run/sub-skills/baseline-quality/SKILL.md)
  §4 exercising the per-field calibration end-to-end on a
  K=3 OUTPUT_SCHEMA — per-field within-field synthesis on
  `category` / `brand_known` / `defect_severity`,
  cross-field consolidation per the
  "any-not-ready dominates" rule, field-targeted
  remediation.
- **`EARLY_STOP.md/early_stop_floor_unmet` advancement
  branch** in
  [`skills/run/phases/spp-finalize.md`](skills/run/phases/spp-finalize.md)
  §3 pre-condition 6 — `/spp-finalize` accepts the
  `early_stop_floor_unmet` termination variant (added in
  bucket 3) with a user-confirmation prompt that surfaces
  the unmet floors before the sacred-test-set read. Other
  EARLY_STOP variants and FAILED.md continue to refuse per
  v0.1.0 behavior. Unmet floors propagate into REPORT
  §7.5 (acknowledged-risk overrides).
- **Locked-invariants inventory** in
  [`DESIGN.md`](DESIGN.md) §7.1.1 (bucket 6 of 7) — explicit
  list of v0.1.0 methodology guarantees v0.2 preserves
  verbatim (auditor score-blindness; no row content to
  rule-edit subagent; auditor frequency lock; sacred-test-
  set read-once discipline; HITL gate literal-string
  matching; six-section prompt structure; verdict tokens as
  categorical hard tokens; MODEL_IDENTIFIER no-aliasing;
  loop_spec.md literal-block check; v1 command set closed
  at four; REPORT.md §5 invariant block) or with shape
  changes that preserve substance (per-stage isolated
  subagents; adversary score-blindness + non-persistence;
  auditor / baseline-quality / schema-designer verdict
  gates; metric independence rule; plan.md-as-contract;
  `/spp-finalize` advances only on `SUCCESS.md` with one
  documented v0.2 exception). Each entry names the
  invariant, canonical reference, what it guarantees,
  verification status, and the BREAKING CHANGE triggers in
  the relevant Versioning sections that protect it. Closes
  with two minor documentation findings (atomic-checkpoint
  discipline lacks an explicit BREAKING CHANGE bullet;
  `/spp-finalize` Versioning bullet "Allowing
  `/spp-finalize` to advance on `EARLY_STOP.md` or
  `FAILED.md`" did not get updated when bucket 5 added the
  `early_stop_floor_unmet` exception) for maintainer
  disposition; no weakened invariants found.
- **`examples/multi-field-extraction/`** — canonical v0.2
  skeleton example for multi-field structured-output
  classification. Six files (`README.md`, `walkthrough.md`,
  `config/plan.md`, `data/baseline.csv`,
  `prompts/prompt_v01.md`,
  `runs/placeholder-model/REPORT.md`) covering K=4 fields of
  diverse JSON Schema types (`string` `title` /
  `number` `price` / `enum` `category` / `boolean`
  `in_stock`), aggregate strategy `min` for heterogeneous
  metric types, and a per-field floor on `category`.
  Exercises v0.2 buckets 1, 2, 3, 5 explicitly; 4, 6
  implicitly. Skeleton per
  [`DESIGN.md`](DESIGN.md) §7.2 — file structure and
  walkthrough are real; data, baseline labels, and prompt
  content are placeholder.
- **`examples/nested-schema/`** — canonical v0.2 skeleton
  example for hierarchical labels via JSON Schema
  conditional structures. Six files (same shape as
  multi-field-extraction). OUTPUT_SCHEMA uses `allOf` +
  `if/then` clauses to constrain `sub_category`'s value
  space per `top_level` branch (`billing` /
  `technical` / `account` / `other`). Exercises the
  schema layer's "adjacent output shapes the schema layer
  subsumes" commitment ([`DESIGN.md`](DESIGN.md) §7.1.1
  schema layer). Aggregate strategy `macro` (homogeneous
  metric types — both fields use `macro_F1`); per-field
  floor on `top_level` (`macro_F1 ≥ 0.90`) because
  top-level routing is unrecoverable. Buckets 1, 2, 3, 5
  explicitly; 4, 6 implicitly.
- **DESIGN.md §7.1.1 fixtures layer subsection** (bucket
  7 of 7); the canonical examples that validate v0.2's
  scope end-to-end and the closing-out paragraph naming
  v0.2's planning arc as complete. With this PR merged,
  all seven layers of v0.2's planning sequence are
  locked.
- **Feature-group prompt splitting** as a methodology
  principle. Adds an entry to [`DESIGN.md`](DESIGN.md)
  §7.1's principles paragraph (output-shape-agnostic
  methodology-as-substance list) and a substantive
  glossary entry in §10 placed after the
  `plan.md`-as-contract entry. When a task's OUTPUT_SCHEMA
  spans multiple feature groups — subsets of fields
  sharing a reasoning pattern, an input dependency, or a
  metric profile — the methodology defaults to one prompt
  per group, each in its own `spp/` task directory.
  Cross-task composition stays out of `spp`'s scope; the
  user owns the production-pipeline composition layer.
  K=1, hierarchical conditional reasoning, dense
  interdependencies, and shared-input cases are the
  documented exceptions (the canonical bucket-7 examples
  exemplify the unified-task exception).
- **`designer.md` §5.0 feature-group identification
  consultation substep** — runs before §5.1's
  task-definition questions and before the bucket-4
  schema-designer invocation, so the feature-grouping
  decision shapes everything downstream. Designer-led
  (not a sub-skill invocation). For any K > 1 strawman
  the substep runs and the explicit decision is
  recorded; for K=1 strawmans it's skipped (the question
  is trivial). The decision lands as either "split into
  N `spp/` task directories" (the methodology default)
  or "keep unified" (the documented exception, with the
  rationale recorded in `plan.md` §10).
- **`prompt-architect` SKILL.md sub-task scoping note** —
  new sub-section in §5 documenting how the six-section
  structure scopes when a prompt is part of a split
  task: `<persona>`, `<task>`, `<rules>`,
  `<output_format>`, `<example_input>`, `<example_output>`
  all describe the sub-task's fields, not the full
  original task's fields. Reusability follows from the
  scoping discipline.
- **README.md "When to use this" mention** of feature-group
  splitting with cross-reference to the `DESIGN.md` §10
  glossary entry.
- **`examples/feature-group-split/`** — third v0.2 example,
  post-bucket-7 addition that exemplifies the feature-group
  prompt splitting principle's **default case**. Parent
  `README.md` + `walkthrough.md` document the decomposition
  rationale, the production-pipeline composition layer (out of
  `spp`'s scope), and the granularity guidance (significant
  gains on first split; diminishing returns on further
  subdivision; identify natural groups by distinct reasoning
  patterns, not mechanical separability). Three sub-task
  skeletons (`sub-tasks/sentiment/`, `sub-tasks/topic/`,
  `sub-tasks/urgency/`), each a complete independent `spp/`
  task with `README.md`, `config/plan.md`, `data/baseline.csv`,
  `prompts/prompt_v01.md`, `runs/placeholder-model/REPORT.md`.
  Each sub-task is internally K=1 (single-output classification
  under the v0.2 protocol); the decomposition is what makes the
  example exemplify the principle, not the internal K-shape.
  Body text is shared across sub-task baselines (same
  production input feeds all three prompts); label columns
  differ. Sub-tasks share consistent naming
  (`feature-group-split-<group>`) and the prompt-architect
  sub-task scoping discipline.

### Changed

- **`examples/multi-field-extraction/README.md`** gains a
  "Relationship to the feature-group splitting principle"
  section acknowledging that the example exemplifies the
  unified-multi-field **exception case** (all four fields share
  input dependency; splitting would pay four model invocations'
  worth of cost with no reasoning gain). Cross-references the
  new `examples/feature-group-split/` for the default case.
- **`examples/nested-schema/README.md`** gains a parallel
  section explaining that hierarchical conditional reasoning
  is the second canonical exception case — splitting would
  fragment the conditional reasoning across two prompts and
  require the sub-category prompt to read the top-level
  prompt's output.
- **DESIGN.md §6 Phase 3 example-naming list** extended to
  include the new `examples/feature-group-split/` (v0.2
  post-bucket-7 addition) and updated to note which examples
  exemplify the principle's default case vs. exception cases.
  The methodology-gradient framing now spans single-output
  binary → unified multi-field structured output → unified
  conditional/hierarchical → feature-group-decomposed.
- **DESIGN.md §7.1.1 fixtures-layer subsection** gains a
  post-bucket-7-example addendum noting the new example as an
  additive v0.2 fixture (not a new bucket — the "all seven
  layers are locked below" framing is preserved). The addendum
  documents the relationship between the default-case example
  (this PR's new addition) and the bucket-7 exception-case
  pair, plus the granularity guidance.
- **DESIGN.md §7.1.1 intro paragraph** rewritten to mark all
  seven layers locked. The previous "buckets 1, 2, 3, 4, 5,
  and 6 of 7; the remaining fixtures layer is flagged above
  and pinned in a subsequent PR" framing is replaced by "All
  seven layers are locked below" — closes v0.2's planning
  arc.
- **DESIGN.md §6 Phase 3 example-naming list** updated to
  reflect on-disk reality. Replaces the planned-three list
  (`binary-classification` / `multi-class-classification` /
  `edge-case-imbalanced`, none of which were created on disk
  during v0.1.0 work) with the actual list:
  `examples/hair-loss-relevance/` (v0.1.0; named by domain
  rather than task-type, with a one-sentence note that the
  task-type-naming convention was set after this example
  was created), plus the two new v0.2 examples
  (`multi-field-extraction` and `nested-schema`). The
  methodology-gradient framing is preserved; the gradient
  is now binary single-output → multi-field structured
  output → conditional/hierarchical.
- **`metric-design` SKILL.md re-scoped per-field** for v0.2
  multi-field tasks (`DESIGN.md` §7.1.1 metrics layer); the
  v0.1.0 single-output decision tree now runs once per
  OUTPUT_SCHEMA field, with K=1 (single-output classification)
  preserved as the degenerate case that produces v0.1.0-
  equivalent behavior.
- **DESIGN.md §7.1.1** expanded with the metrics-layer
  subsection (bucket 2 of 7); per-field metric types,
  aggregate-strategy choice, headline-criterion two-component
  shape, stop discipline, `eval.json` schema, sub-skill
  adaptation, and K=1 backward compatibility now locked in
  prose.
- **DESIGN.md §7.1.1** expanded with the per-field
  methodology application layer subsection (bucket 3 of 7);
  field-bounded discrepancy clusters with cross-field
  correlation visibility, any-field-disagreed disagreed-row
  filter, per-edit-per-field auditor verdict scoping,
  per-field REPORT trajectories, the `early_stop_floor_unmet`
  variant, and structured-ground-truth adversarial rows now
  locked in prose.
- **`/spp-loop` phase doc steps 7, 8, 9, 11, 12, 13, 15**
  generalized for v0.2 multi-field tasks. Step 7 computes
  per-field + aggregate metrics and persists the v0.2
  `eval.json` shape (`per_field` / `aggregate` /
  `floor_compliance`); step 8 produces field-attributed
  clusters and `target_fields`-tagged rule edits in
  `discrepancy_analysis.md`; step 11 produces per-edit-per-
  field auditor verdicts; step 12 enforces the gate per
  `(edit, field)` combination with bracketed
  `[edit-N.field]` override-syntax tokens (K=1 backward
  compat: an unscoped `auditor override` Reason covers the
  lone field implicitly); step 13's stop conditions read
  from `aggregate`; step 15's termination artifact gains
  `early_stop_floor_unmet` and per-field floor compliance.
  K=1 (v0.1.0 LABEL_SPACE fallback) backward compat
  preserved end-to-end.
- **`auditor` agent verdict scoping** changed to
  per-edit-per-field. Each rule edit listed in
  `discrepancy_analysis.md` with K target fields gets K
  independent verdicts; `auditor_review.md` per-edit
  sections now contain per-field sub-sections. Hard-token
  discipline preserved (`categorical` / `row-specific` /
  `unclear`). K=1 collapses to v0.1.0's per-edit shape.
- **`adversary` agent synthetic rows** now carry full
  OUTPUT_SCHEMA-shaped ground truth (one value per field).
  K=1 collapses to v0.1.0's "label" field.
- **`REPORT.md.template`** §2 reorganized into per-field /
  aggregate / floor_compliance blocks; §3 adds per-field
  trajectory tables alongside the aggregate trajectory; §4
  clusters carry a primary-field tag; §7 adds an
  acknowledged-risk-overrides subsection that surfaces
  `not-ready override` and `auditor override` (with v0.2
  bracketed tokens) entries from `plan.md` §11. v0.1.0
  LABEL_SPACE fallback renders as the K=1 degenerate case.
- **DESIGN.md §7.1.1** expanded with the sub-skill ordering
  layer subsection (bucket 4 of 7); resolves the gate-
  placement question deferred in bucket 1 (schema-designer's
  verdict folds into G1's contents, no renumbering of G1–G6)
  and pins the consultation order (`schema-designer` before
  `metric-design` per data dependency). DESIGN.md §10
  glossary HITL gate entry gains a verdict-gated-
  preconditions addendum acknowledging schema-designer at G1
  and baseline-quality at G2.
- **`designer.md` §5 consultation order** — schema-designer
  invocation lands between §5.1 (task definition) and §5.2
  (production-economics / metric-design feed), determined by
  `metric-design`'s data dependency on OUTPUT_SCHEMA.
- **`designer.md` §7 rules 3, 4, and 5 generalized** for
  v0.2. Rule 3 (`LABEL_SPACE` is enumerable) → "OUTPUT_SCHEMA
  passes the mechanical layer" per `schema-designer`
  SKILL.md §3.4. Rule 4 (`METRIC_NAME` is one of the listed
  values) now applies **per OUTPUT_SCHEMA field**
  (`METRIC_NAME[f]` for each field `f`); under K=1 this is
  the lone field's `METRIC_NAME`, equivalent to v0.1.0.
  Rule 5 (`METRIC_INDEPENDENCE_NOTE` present) → per-field
  `METRIC_INDEPENDENCE_NOTE[f]` for each OUTPUT_SCHEMA field
  per `metric-design` SKILL.md §6. K > 1 contract-only until
  bucket 5; K=1 path continues to use v0.1.0 scalar fields.
- **`/spp-init` G1 enforcement** is a dual check under v0.2:
  the user's approval-substring match (existing v0.1.0
  check) plus the `schema-designer` verdict-gated
  precondition (`ready` OR `plan.md` §11 entry containing
  `schema-not-ready override`). Refuses to advance to
  `/spp-baseline` if either check fails; refusal message
  names the specific failed check. K=1 path's common case
  (`ready` verdict, no override needed) is indistinguishable
  from v0.1.0's single-check behavior.
- **DESIGN.md §7.1.1** expanded with the compat layer
  subsection (bucket 5 of 7); locks the migration story
  for existing v0.1.0 `plan.md` files (runner-level
  auto-promotion plus documented manual upgrade — no
  `/spp-migrate-plan` command), the `baseline-quality`
  per-field calibration with consolidated single verdict,
  and the phase-doc read-pattern updates with K=1 backward
  compatibility. Bucket-list bullet 5 marked "Locked
  below"; subsection summary updated to "buckets 1, 2, 3,
  4, and 5 of 7".
- **`plan.md.template` §2 generalized** — the v0.1.0
  `LABEL_SPACE` + per-class definitions structure is
  replaced by an `OUTPUT_SCHEMA` block (JSON Schema draft
  2020-12; YAML or JSON surface) plus per-field definition
  sub-blocks (one per OUTPUT_SCHEMA field, with positive
  and borderline examples and edge cases). Single-output
  classification writes the same shape with one field; no
  shorthand, no `LABEL_SPACE` legacy alias. Legacy v0.1.0
  plans continue to work via the runner's K=1 fallback.
- **`plan.md.template` §3 + §4 generalized** — §3's
  headline criterion takes the aggregate-metric target
  (`AGGREGATE_METRIC_TARGET`); §4 carries an
  `AGGREGATE_STRATEGY` block (with `AGGREGATE_WEIGHTS`
  when `weighted`; `AGGREGATE_RATIONALE` always),
  per-field metric sub-blocks (one per field, each with
  `METRIC_NAME[f]` / `METRIC_RATIONALE[f]` /
  `METRIC_INDEPENDENCE_NOTE[f]`), and per-field `FLOOR`
  sub-blocks (optional; absent for fields without).
  Validation rules 3, 4, 5 updated to v0.2 forms. K=1
  collapses to one per-field metric sub-block, trivial
  aggregate strategy, and at most one floor — equivalent
  to v0.1.0's scalar fields.
- **`designer.md` §7 forward-notes lifted on rules 3, 4,
  5** — the "K > 1 is contract-only until bucket 5"
  forward-notes are removed; rules now unconditionally
  K > 1 deployable. The K=1 fallback paragraphs stay so
  legacy v0.1.0 plans persisting `LABEL_SPACE` / scalar
  `METRIC_NAME` / scalar `METRIC_INDEPENDENCE_NOTE`
  validate via the runner's auto-promotion to a one-field
  OUTPUT_SCHEMA.
- **`baseline-quality` SKILL.md per-field calibration** —
  §3 review questions (drift check, intuition-vs-rule,
  calibration, etc.) re-scoped to run **per OUTPUT_SCHEMA
  field**. §3.7 verdict synthesis is now two-stage:
  within-field synthesis per field, then cross-field
  consolidation via the "any-not-ready dominates,
  any-revise dominates ready" rule. The verdict remains
  one token per baseline (G2 enforcement unchanged). §6
  outputs (`BASELINE_QUALITY_NOTE`, findings list)
  re-shaped per field. K=1 collapses to v0.1.0's flat
  single-stage shape.
- **`/spp-baseline.md` per-field invocation pattern** —
  pre-condition 7's existing-baseline schema check
  supports the v0.2 OUTPUT_SCHEMA shape (one column per
  field) plus the v0.1.0 fallback (one `label` column);
  step 4 labels rows per OUTPUT_SCHEMA field; step 7
  invokes `baseline-quality` with per-field calibration
  and reads back the consolidated verdict + per-field
  findings. K=1 backward-compat paragraph + versioning
  bullets added.
- **`/spp-finalize.md` v0.2 read pattern** — step 2 reads
  `plan.md` §2 OUTPUT_SCHEMA + §3 aggregate target + §4
  per-field metric sub-blocks + aggregate-strategy block
  + per-field floor sub-blocks; step 4 computes per-field
  metrics + aggregate per `AGGREGATE_STRATEGY`, persisting
  the v0.2 `test_eval.json` shape (`per_field` /
  `aggregate` / `floor_compliance`); step 5 tags failure
  clusters with their primary OUTPUT_SCHEMA field; step 7
  populates the bucket-3 v0.2 REPORT sections (§2 per-field
  / aggregate / floor compliance; §3 per-field
  trajectories + aggregate trajectory; §4 primary-field
  clusters; §6 deterministic decision tree generalized to
  read aggregate + floor compliance; §7.5
  acknowledged-risk overrides surfaces unmet floors when
  the entry path was
  `EARLY_STOP.md/early_stop_floor_unmet`). K=1
  backward-compat paragraph + versioning bullets added.

---

## [0.1.0] — 2026-05-06

The first tagged release of `spp`. v0.1.0 is the first
instantiation of the spp methodology — disciplined, human-in-
the-loop supervised prompt learning — scoped to **single-output
classification** (binary, multi-class, or fixed-schema labeling
where each row resolves to one categorical label). The
methodology principles (per-stage information isolation between
the discrepancy / rule-edit / auditor / adversary subagents; the
auditor's categorical-vs-row-specific judgment as the design
lock against score-driven row-specific patches; the sacred test
set; the six-section prompt structure; verdict-enforced gates;
`plan.md` as contract) are output-shape-agnostic. v0.1.0's
bookkeeping (`plan.md` schema, `metric-design`'s metric list,
`/spp-loop`'s scoring step, `REPORT.md`'s shape) is hardcoded
for single-output classification; v0.2 will generalize the
bookkeeping to multi-field structured output, hierarchical
labels, and freeform extraction with structured ground truth.
See [`DESIGN.md`](DESIGN.md) §7.1 for the methodology-vs-
bookkeeping distinction, the v0.2 roadmap, and the deliberate
non-goals.

`spp` is distributed as a Claude Code plugin via this
repository's marketplace; users install with `/plugin
marketplace add JayLBean/supervised-prompt-producer` followed
by `/plugin install spp@supervised-prompt-producer`. The
methodology is operationalized as a single skill (`run`); the
user invokes the plugin once per task with `/spp:run
<task-name>` (or by describing a classification task to Claude
Code, which activates the skill from its `description`
frontmatter), and the agent walks four phases — consultation,
baseline-and-splits, optimization loop, finalization —
pausing at six human-in-the-loop gates (G1–G6) for explicit
user approval.

### Highlights

- **Plugin distribution and marketplace install** — `spp`
  ships at `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`; install via `/plugin
  marketplace add` + `/plugin install`. Local development:
  `claude --plugin-dir ./`.
- **Four-phase methodology** — consultation, baseline-and-
  splits, optimization loop, finalization — operationalized as
  the `run` skill at `skills/run/SKILL.md` and the four phase
  docs at `skills/run/phases/`. The agent walks the phases in
  order; the user reviews and approves at gates.
- **Per-stage information isolation** between the discrepancy,
  rule-edit, auditor, and (optional) adversary subagents
  inside `/spp-loop`. The auditor's score-blindness is the
  design lock against score-driven row-specific patches and
  the property that distinguishes `spp` from automated
  optimizers (DSPy / GEPA / APE). Canonical statement:
  [`DESIGN.md`](DESIGN.md) §4.2.
- **Sacred test set discipline** — the test partition is read
  exactly once, by `/spp-finalize`, after gates G1–G4 have
  approved. The methodology's claim against baseline
  overfitting hinges on this discipline.
- **Three agents** (designer, auditor, adversary), **three
  sub-skills** (metric-design, baseline-quality,
  prompt-architect), **four templates** (plan.md, loop_spec.md,
  prompt_v01.md, REPORT.md). Each set is closed at v0.1.0;
  expansion requires a methodology change documented in
  `DESIGN.md`.
- **Runnable substrate** — four Python primitives at
  `skills/run/scripts/` (split, inference, eval, discrepancy)
  with 26 smoke tests passing. The skill's docs prescribe
  schemas; the substrate operationalizes them.
- **Canonical worked example** at
  `examples/hair-loss-relevance/` — the methodology run
  end-to-end against `gpt-oss-20b-MXFP4-Q8` on a real
  classification task, terminated at iteration 4 by user-
  initiated `EARLY_STOP` exemplifying the methodology's
  discipline against row-specific patching. NDA-driven
  sanitization applied to the data and prediction outputs;
  the methodology artifacts (plan, prompts, eval, REPORT)
  ship intact.

### Changed

- **`DESIGN.md` §7.1 reframed around the
  methodology-vs-bookkeeping distinction.** The previous flat
  "non-goals" list lumped roadmap items (where the methodology
  applies but v0.1.0's bookkeeping is intentionally narrow)
  together with deliberate non-goals (where the methodology
  itself does not apply). The new §7.1 opens with a paragraph
  naming the two layers — methodology principles (per-stage
  information isolation, auditor judgment, sacred test set,
  six-section prompt structure) are output-shape-agnostic;
  v0.1.0's bookkeeping (`plan.md` schema, `metric-design`'s
  metric list, `/spp-loop`'s scoring step, `REPORT.md`'s shape)
  is hardcoded for single-output classification — and then
  splits the non-goals into three subsections: §7.1.1 (v0.2
  roadmap: bookkeeping generalization for broader output shapes
  including multi-field structured output, hierarchical labels,
  and freeform extraction with structured ground truth),
  §7.1.2 (further-out roadmap: multi-judge subjective metrics
  v0.3, multilingual v0.3, cross-model synthesis v0.4,
  mid-iteration resumption TBD), and §7.1.3 (deliberate
  non-goals where the underlying problem is methodologically
  different: generation tasks, tool-use / agentic prompts, RAG,
  prompt-injection defense, automated prompt search,
  auditor frequency reduction). The distinction lets a future
  reader tell which limitations are temporary instantiation
  choices and which are scope boundaries the methodology will
  not cross.
- **`README.md` opening reframed to surface the
  methodology-vs-instantiation distinction.** The opening
  paragraph now names spp as "a Claude Code plugin for
  disciplined, human-in-the-loop supervised prompt learning"
  whose methodology is output-shape-agnostic, with v0.1.0
  instantiating it for single-output classification and v0.2
  generalizing the bookkeeping for broader output shapes. The
  "When to use this" section's classification-task bullet now
  explicitly says "single-output classification task" and
  notes which other shapes the methodology applies to but
  v0.1.0's bookkeeping does not yet handle. The "When NOT to
  use this" list now distinguishes deliberate non-goals
  (generation, tool-use, prompt-injection defense, ad-hoc
  exploration) from cases where the methodology applies but
  the bookkeeping is narrow.
- **Slash-command-notation clarifier added to all four phase
  docs.** Each of `skills/run/phases/spp-init.md`,
  `spp-baseline.md`, `spp-loop.md`, and `spp-finalize.md` now
  carries a one-paragraph note near the top explaining that
  the slash-prefixed phase names (`/spp-init` etc.) are
  methodology phase identifiers used internally during a
  `/spp:run` session, not separate slash commands the user
  types. The phase docs' canonical identifiers are unchanged
  for cross-reference stability; only the framing is
  clarified. The section titles ("1. Command identity" etc.)
  are deliberately left as-is to preserve cross-reference
  stability — a heading rename is methodology-affecting in a
  way this PR is not.
- **`CHANGELOG.md` consolidated for v0.1.0 release.** All
  prior `[Unreleased]` entries (covering Phases 1, 2 steps
  1–11, 2.5, 3, 4 step 1, plus this PR's release-prep) are
  moved into a new `[0.1.0]` section dated `2026-05-06`. The
  forward-looking placeholder `[0.1.0] — _unreleased_` block
  at the bottom of CHANGELOG (which described v0.1.0's scope
  in advance) is replaced by the actual `[0.1.0]` entry; its
  scope-in-advance prose is folded into the new `[0.1.0]`
  section's opening narrative paragraph and `### Highlights`
  block. A new empty `[Unreleased]` section is added above
  `[0.1.0]` for post-release entries. Comparison links at the
  bottom updated for the v0.1.0 tag (which is anticipated but
  not yet applied — tagging is a separate manual operation).

### Notes

- Final pre-release polish PR before v0.1.0 tags. Doc-only,
  no methodology / template / agent / sub-skill / script /
  plugin-manifest changes. After this PR merges to `dev`, the
  path to v0.1.0 release is `dev` → `main` merge + manual tag
  per `CLAUDE.md` §3.

### Added

- **Plugin distribution.** `spp` now ships as a Claude Code
  plugin. New `.claude-plugin/plugin.json` manifest at the
  repo root declares the plugin (name `spp`, version
  `0.1.0`, license MIT, category `ai-and-ml`). New
  `.claude-plugin/marketplace.json` declares the repo as a
  single-plugin Claude Code marketplace named
  `supervised-prompt-producer`, with the plugin sourced
  from `./` (repo root). Users install with
  `/plugin marketplace add JayLBean/supervised-prompt-producer`
  followed by `/plugin install spp@supervised-prompt-producer`;
  local development loads via `claude --plugin-dir ./`.

### Changed

- **`BREAKING CHANGE:` plugin-format restructure of the
  skill tree.** The prior `.claude/skills/spp/` layout has
  been replaced with the plugin layout: the skill content
  now lives at `skills/run/`, and the prior `commands/`
  subdirectory has been renamed to `phases/`. The skill
  itself is now the single skill the `spp` plugin ships,
  named `run` — invoked as `/spp:run <task-name>` (or
  activated automatically when the user describes a
  classification task to Claude Code). The four phase docs
  retain their `/spp-*` slash-prefixed names (`spp-init`,
  `spp-baseline`, `spp-loop`, `spp-finalize`) as a naming
  convention for methodology phases the agent walks
  through; they are not separate user-facing slash
  commands. The methodology itself is unchanged: every
  agent's information-isolation guarantee, every gate's
  literal-string approval contract, every sub-skill's
  verdict shape, every template's structure remains as
  documented. Only the file layout and the distribution
  mechanism change. Existing manual installs of the prior
  `.claude/skills/spp/` layout will need to migrate; the
  recommended path is to uninstall the manual install and
  re-install via the plugin marketplace.
- **`skills/run/SKILL.md`** rewritten as the plugin skill's
  entry point. New YAML frontmatter `name: run` with a
  description tuned for automatic skill activation when
  the user describes a classification task. The artifact
  taxonomy (§3), load-bearing properties (§5), and "what
  `spp` is NOT" (§6) sections are carried forward
  substantively unchanged but now consistently use "phase"
  rather than "command" terminology. Internal relative
  paths shortened from `../../../*.md` to `../../*.md`
  (the SKILL.md is now two levels deep under the repo
  root rather than three).
- **`README.md`** updated with the plugin marketplace
  install path as the primary install instruction, and the
  pipeline mermaid diagram simplified from a 20-node
  detailed-mechanics view to a six-node phase-and-gate
  view. The previous diagram's per-iteration detail
  (discrepancy → propose → audit → keep/flag → check-stop)
  was the loop's internal mechanics that already lives at
  `skills/run/phases/spp-loop.md` §4; surfacing it at the
  top-level README crowded the high-level shape. The new
  diagram shows four phases, six gates, and one loop —
  what users deciding whether to adopt the methodology
  need to see. A phase-mapping paragraph beneath the
  diagram links each phase to its canonical doc.
- **External cross-references** in `CLAUDE.md`, `DESIGN.md`,
  `CONTRIBUTING.md`, `.github/pull_request_template.md`,
  and `examples/hair-loss-relevance/` updated to use the
  new paths (`skills/run/...`, `phases/`). Historical
  CHANGELOG entries describing prior PRs retain their
  original paths as accurate-as-of-then; the migration is
  documented in this entry.

### Notes

- Phase 4 step 1 (the v0.1.0 plugin-conversion deliverable).
  No methodology changes — the per-stage information
  isolation contract, the auditor / adversary / designer
  agent boundaries, the sacred-test-set discipline, and the
  six-section prompt structure are all unchanged. What
  changes is where the files live and how users install
  the skill.
- v0.1.0 milestone is approaching but not tagged in this
  PR. The version field in `plugin.json` and
  `marketplace.json` is set to `0.1.0` in anticipation of
  the release; the actual git tag is a separate manual
  operation per `CLAUDE.md` §3.

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

### Changed

- Top-level `README.md` Quickstart and methodology mermaid
  diagram now present `/spp <task-name>` as the canonical
  user-facing slash command for invoking the skill. The four
  `/spp-init`, `/spp-baseline`, `/spp-loop`, `/spp-finalize`
  names are presented as the router's internal phase commands —
  documentation for what the skill does at each step rather than
  separate slash commands a user types. Quickstart steps 3–6 now
  read as "**Phase N — `/spp-<phase>`:** ..." with an explicit
  callout that the four are not separately invoked. The mermaid
  entry node was renamed from `/spp-init <task-name>` to
  `/spp <task-name>` and the four phase nodes were prefixed
  with their phase number. Cascade revisions in
  `examples/hair-loss-relevance/README.md` (Findings §3
  reframed positively as design-confirmation, no longer flagged
  as a Phase 4 doc gap) and `examples/hair-loss-relevance/WALKTHROUGH.md`
  §1 (notes that the historical run pre-dated `/spp` entry-point
  framing — the user described the task rather than typing
  `/spp` — but the canonical invocation going forward is
  `/spp <task>`).

### Notes

- Phase 3 step 1 (the v0.1.0 worked-example deliverable). Per
  `DESIGN.md` non-goals (§7.1) and the example's lean framing,
  no methodology changes are made in this PR — remaining
  findings (`SUCCESS.md` / `EARLY_STOP.md` collision under v6
  plateau-threshold revision; the run pre-dating the per-stage
  information-isolation revision in PR #14) are recorded and
  forwarded to Phase 4. The slash-command-invocation finding has
  been resolved in this PR rather than deferred. Versioning
  impact: none.

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

[Unreleased]: https://github.com/JayLBean/supervised-prompt-producer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/JayLBean/supervised-prompt-producer/releases/tag/v0.1.0
