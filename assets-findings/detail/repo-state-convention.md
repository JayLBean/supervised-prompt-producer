# Repo state + arc-opening convention — deep dive

Companion detail doc to `assets-findings/spp-repo.md`. Goes deeper on (1) the
arc-opening convention, (2) the full v1.0 forwarded roadmap from STATE, (3) the
four worked examples' output shapes, (4) the supported-task-types / scope
boundary statements, and (5) the CHANGELOG structure for methodology-affecting
changes. All paths absolute. Verbatim quotes are flagged and line-referenced.

---

## 1. The arc-opening convention

### (a) What a DESIGN.md §7.x "pin" PR is and does

An arc opens with a **`docs(design)` PR that pins the design in `DESIGN.md`
before any code, template, agent, or sub-skill file changes.** The pin locks the
contracts and the invariant-inventory frame; downstream PRs are written *against*
that frozen contract.

v0.2 opened with **PR #19 — `docs(design): pin v0.2 schema-layer design`**.
Verbatim from the squash-merged release commit body
(`git -C /Users/jiafuli/Desktop/Project/spp show a2872b2`, PR #19 section):

> docs(design): pin v0.2 schema-layer design (#19)
>
> Expand DESIGN.md §7.1.1 from a flat six-bullet sketch into a "Bookkeeping
> changes by layer" frame with the schema layer fully fleshed out and the
> remaining six v0.2 layers (metrics, per-field methodology application,
> sub-skill ordering, compat, locked-invariants inventory, fixtures) flagged as
> covered in subsequent v0.2 design PRs.
>
> This is bucket 1 of 7 in the v0.2 planning sequence. … No code, template,
> agent, or sub-skill files change in this PR — the DESIGN.md revision is the
> contract subsequent code PRs will be written against.

The pin specifically establishes, for v0.2: **OUTPUT_SCHEMA's home** (`plan.md`
§2, replacing `LABEL_SPACE`, kept as one cohesive block so the auditor's
allow-listed slice per §4.2 stays clean — `DESIGN.md:552-562`); the **schema
language** (JSON Schema draft 2020-12, `DESIGN.md:564`); single-output
classification rendered as a degenerate one-enum-field OUTPUT_SCHEMA (no
shorthand); and it **declares the six-section structure preserved**. The "pin
draft convention" is also flagged in the prior pass at
`assets-findings/spp-repo.md:464-471`.

The frame the pin introduces is headed **"Bookkeeping changes by layer"** at
`/Users/jiafuli/Desktop/Project/spp/DESIGN.md:501`. Verbatim:

> **Bookkeeping changes by layer.** The v0.2 generalization is bigger than a
> single change. It is partitioned into seven layers, each locked in its own PR
> before downstream layers depend on it. (`DESIGN.md:501-503`)

And the closing additivity statement at `DESIGN.md:544-548`, verbatim:

> All seven layers are locked below. The structure was intentionally additive
> across the v0.2 planning arc — each bucket's PR slotted into this frame without
> disturbing prior buckets — and remains additive for future v0.x layers if the
> methodology gains new bookkeeping shapes.

### (b) The ~seven-bucket additive-PR pattern

The generalization is partitioned into **seven layers, each locked in its own PR
before downstream layers depend on it**, and the partition is **intentionally
additive** (each bucket slots into the frame without disturbing prior buckets).
The canonical bucket list is enumerated verbatim at
`/Users/jiafuli/Desktop/Project/spp/DESIGN.md:504-542`:

1. **Schema layer** — what `plan.md` records as the task's output shape.
   (`DESIGN.md:506-507`)
2. **Metrics layer** — how `metric-design` adapts to per-field metrics plus an
   aggregate. (`DESIGN.md:508-509`)
3. **Per-field methodology application layer** — `/spp-loop` scoring,
   `discrepancy_analysis.md` field attribution, auditor per-field verdict
   scoping, `REPORT.md` per-field trajectories. (`DESIGN.md:510-514`)
4. **Sub-skill ordering layer** — where `schema-designer` lands in consultation
   order, and how its verdict gate renumbers/interleaves with G1–G6.
   (`DESIGN.md:515-518`)
5. **Compat layer** — `plan.md.template` v0.2 surface + the consumers that read
   those fields + the migration story for existing v0.1.0 plans.
   (`DESIGN.md:519-527`)
6. **Locked-invariants inventory** — explicit list of v0.1.0 guarantees v0.2
   preserves verbatim or with shape-changes-but-substance-preservation.
   (`DESIGN.md:528-534`)
7. **Fixtures layer** — the canonical `examples/` that validate the scope
   end-to-end. (`DESIGN.md:535-542`)

**The locked-invariants inventory IS one of the seven buckets (bucket 6).** This
is the preservation-audit bucket — its job is to make "what's preserved across
releases" auditable, and it is the template for the downstream impact table. The
prior pass documents the inventory's full contents at
`assets-findings/spp-repo.md:322-411` (item 7); the inventory lives at
`DESIGN.md:1331-1847`.

PR-level mapping of the seven buckets (from STATE doc
`/Users/jiafuli/Desktop/Project/spp/STATE-as-of-v0.2.0.md:22-41` and the PR #30
squash-commit body):

- **PR #19** = bucket 1 (schema-layer design pin; DESIGN-only).
- **PR #20** = `feat(schema-designer)` — realizes the schema-layer contract as a
  standalone verdict-gated sub-skill + four fixtures (shipped standalone, not yet
  integrated). This is the recurring "ships standalone before integration"
  motif.
- **PR #21–#23** = buckets 2 (metrics), 3 (per-field methodology application), 4
  (sub-skill ordering), 5 (compat layer).
- **PR #24–#28** = bucket 6 (locked-invariants inventory) + incremental
  schema-designer / multi-field-fixture work.
- **PR #29** = bucket 7 (fixtures: `multi-field-extraction/`, `nested-schema/`).
- **PR #30** = `chore: release v0.2.0` — the release PR; tag cut on `main` after
  dev → main merge.

Recurring motif inside each bucket (confirmed across the CHANGELOG `### Added` /
`### Changed` entries and DESIGN §7.1.1 subsections): a piece "ships standalone
before integration", carries a **K=1 backward-compatibility fallback**, and ends
with a locked-invariants / Versioning treatment. `examples/feature-group-split/`
was added **post-bucket-7** as an additive fixture (not a new bucket — the "all
seven layers are locked below" framing is preserved per `DESIGN.md:1965`).

### (c) Explicit STATE/DEVELOP_PLAN instruction to repeat the convention

STATE doc says to repeat this exact convention for v1.0. Verbatim
(`/Users/jiafuli/Desktop/Project/spp/STATE-as-of-v0.2.0.md:154`):

> - **v1.0 design PR?** Start with `docs(design): pin v1.0 compound-system
> bookkeeping`, parallel structure to PR #19. Bucket out into ~7 PRs again.

Reinforced at `STATE-as-of-v0.2.0.md:118`, verbatim:

> [PENDING] v1.0 design arc opens with a DESIGN.md §7.1.2 (or equivalent) PR
> establishing what compound-system bookkeeping means concretely, before any code
> changes.

Note: `DEVELOP_PLAN.md` is the **original v1 (= v0.1.0) kickoff** — it predates
the seven-bucket convention entirely (its Phase 3 still names the never-built
`binary-classification` / `multi-class-classification` / `edge-case-imbalanced`
examples, `DEVELOP_PLAN.md:437-441`). The seven-bucket / pin convention lives in
the STATE doc and DESIGN §7.1.1, **not** in `DEVELOP_PLAN.md`. The convention is
also invisible in `git log --oneline` because v0.2 PRs #19–#29 were squashed into
the single release merge `a2872b2 (#30)`; the per-PR narrative survives only in
that commit's body and in the STATE doc.

---

## 2. The full v1.0 / forwarded roadmap from STATE

All line refs into `/Users/jiafuli/Desktop/Project/spp/STATE-as-of-v0.2.0.md`.

### Three concrete arcs queued after v0.2.0 ("Path forward", STATE:110-116)

1. **Decide whether to publish `spp-ex/`** as an external comparison record —
   the PUPA-vs-DSPy/GEPA justification report (options: link from `examples/`,
   keep separate, or integrate selectively). (`STATE:114`)
2. **v1.0 design arc: compound-system bookkeeping as first-class.**
   (`STATE:115`) Likely components, verbatim: "a `compound-system-designer`
   sub-skill (peer to schema-designer); plan.md §2 generalization to
   PIPELINE_SCHEMA (per-module signatures with module-boundary contracts);
   per-module auditor verdicts; per-module REPORT trajectories with composite
   reconciliation at finalize." (`STATE:115`)
3. **Continue closing the v0.2 contract-only items** from §7.1.1 bucket 6's
   findings: atomic-checkpoint Versioning bullet; `/spp-finalize` Versioning
   entry for `early_stop_floor_unmet`. "Small-PR work, not v1.0-blocking."
   (`STATE:116`)

### Methodology gaps surfaced by the spp-ex run, forwarded to v1.0 (STATE:100-108)

1. **Compound-system bookkeeping is contract-only in v0.2** — the PUPA 2-module
   pipeline was optimized via the feature-group-split workaround (two task dirs),
   but per-module composite reconciliation was stitched at finalize manually.
   v1.0 should formalize it first-class. (`STATE:104`)
2. **Per-field auditor verdicts not exercised on PUPA** (composite-over-implicit-
   dimensions metric, not schema-typed); spp's auditor ran at task level. v1.0
   should make compound-output auditor verdicts first-class, parallel to per-field
   for multi-field IE. (`STATE:105`)
3. **Process-isolated auditor enforcement deviation in spp-ex** — `respond` iter 1
   ran the auditor under in-context allow-list discipline rather than process-
   isolated subagent; documented and re-validated by iter 2. Runner-implementation
   concern, not methodology weakness; the contract held. (`STATE:106`)
4. **No bootstrap CIs / paired permutation tests** — the statistics gap (quoted
   verbatim below). (`STATE:107`)
5. **Single-task external validity** — spp-ex is PUPA only; `spp_compare` is
   hair-loss only; two data points. A third public-benchmark run is the next
   leverage point. (`STATE:108`)

### Findings forwarded to v1.0+ (the consolidated list, STATE:120-129)

1. **Compound-system bookkeeping** (= Path-forward item 2). (`STATE:124`)
2. **Per-module auditor isolation contract** — a v1.0 invariant analogous to
   per-stage information isolation: "Module M's auditor must not see module N's
   new-iteration outputs (for N ≠ M)." (`STATE:125`)
3. **Robustness-probe shape** — promote the LM-swap probe to a first-class,
   gated, opt-in `/spp-finalize` sub-step producing a REPORT §2.x table.
   (`STATE:126`)
4. **Cost ledger framing** — the three-line-item ledger (student inference /
   optimizer LM / subscription) could be promoted to a `cost-ledger` sub-skill or
   REPORT §8 expansion. (`STATE:127`)
5. **EARLY_STOP sub-typing** (carried from v0.1.0): user-discipline /
   overfitting-guard / manual-abandon / floor-unmet (the last landed in v0.2);
   user-discipline still lumped, v1.0 should sub-type. (`STATE:128`)
6. **PR #15 hair-loss example pre-dated PR #14 per-stage isolation** — already
   documented in that example's findings. (`STATE:129`)

Also queued as candidate arcs at STATE:151-156: publish spp-ex?; v1.0 design PR
(the pin); small-PR cleanup; EARLY_STOP sub-typing PR.

### The bootstrap-CI / permutation-test gap statement — VERBATIM

`/Users/jiafuli/Desktop/Project/spp/STATE-as-of-v0.2.0.md:107`, under the heading
"### Methodology gaps surfaced by the spp-ex run (forwarded to v1.0)" (line 100),
as item 4 in that list:

> 4. **No bootstrap CIs / paired permutation tests** on row-level scores. Same
> limit as the prior `spp_compare`. Cheap to add at finalize.

Surrounding context (verbatim, the two adjacent list items, STATE:106 and
STATE:108):

> 3. **Process-isolated auditor enforcement deviation in spp-ex**. One iteration
> (`respond` iter 1) ran the auditor under in-context allow-list discipline rather
> than process-isolated subagent. … The report `§2.4` records this as a documented
> asymmetry. …
>
> 5. **Single-task external validity**. spp-ex is PUPA only; `spp_compare` is
> hair-loss only. Two-data-point external validity. A third public-benchmark run
> is the next leverage point.

Implementation corroboration (from the prior pass, `spp-repo.md:211-247`): the
runnable `eval.py` defines `SUPPORTED_METRICS = {"f1", "accuracy", "precision",
"recall"}` (`skills/run/scripts/eval.py:32`) and computes point estimates only —
**no bootstrap, no CIs, no permutation tests anywhere in the codebase**
(grep-verified). REPORT emits a `TRAIN_DEV_AGGREGATE_DELTA` overfitting-guard
number but no interval/significance number. So the statistics gap is both
**logged as a forwarded v1.0 item (STATE:107)** and **verified absent in code**.

---

## 3. The four worked examples — output shapes already demonstrated

All under `/Users/jiafuli/Desktop/Project/spp/examples/`. This is the catalog of
output shapes the planner can treat as already demonstrated.

| Example | Task shape | K / fields | Field types | Aggregate | Floor | Feature-group split? | Nested schema? | Multi-field extraction? |
|---|---|---|---|---|---|---|---|---|
| `hair-loss-relevance/` | Binary single-output classification (v0.1.0 canonical, real NDA-redacted artifacts) | K=1, one `label` | binary enum | n/a (K=1) | n/a | No (single task) | No | No |
| `multi-field-extraction/` | Unified multi-field structured-output classification (v0.2 skeleton) | K=4 (`title`, `price`, `category`, `in_stock`) | `string`, `number`, `enum`, `boolean` | `min` (heterogeneous scales) | `category` (`macro_F1 ≥ 0.85`) | No — exemplifies the unified **exception** case | No | **Yes** |
| `nested-schema/` | Hierarchical labels via JSON Schema conditionals (v0.2 skeleton) | K=2 (`top_level`, `sub_category`) | `enum` + conditional `enum` (`allOf` + `if/then`) | `macro` (homogeneous; both `macro_F1`) | `top_level` (`macro_F1 ≥ 0.90`) | No — unified exception (hierarchical conditional reasoning) | **Yes** | Partial (structured multi-field, conditional) |
| `feature-group-split/` | Decomposition: one task → 3 sub-tasks (sentiment / topic / urgency), each its own `spp/` task dir (v0.2 skeleton) | 3 sub-tasks, each internally K=1 enum | enum per sub-task (3-value enums) | `macro` (K=1 identity per sub-task) | optional per sub-task (e.g. `immediate` on urgency) | **Yes** — the **default** case the principle exemplifies | No | No |

Detail per example:

- **`hair-loss-relevance/`** (`examples/hair-loss-relevance/README.md`): the only
  example with a **real run** (gpt-oss-20b-MXFP4-Q8, EARLY_STOP at iter 4, NDA
  sanitization). Predates PR #14 per-stage isolation (`README.md:89-100`).
  Explicitly does NOT demonstrate: multi-class, fresh-labeling via
  `/spp-baseline`, SUCCESS termination, adversary-on, cross-model robustness
  (`README.md:117-135`). Output space: single binary label.

- **`multi-field-extraction/`** (`examples/multi-field-extraction/README.md`):
  the canonical **multi-field-extraction shape** — K=4, four distinct JSON
  Schema scalar types, aggregate `min` (heterogeneous metric scales force
  min-over-fields), per-field floor on `category`. Exercises buckets 1, 2, 3, 5
  explicitly; 4, 6 implicitly (`README.md:18-50`). Exemplifies the
  **unified-multi-field exception** to feature-group splitting (shared input
  dependency; splitting would pay 4× invocation cost with no reasoning gain,
  `README.md:52-71`). Data shape: one CSV column per OUTPUT_SCHEMA field plus
  `row_id` and `body`.

- **`nested-schema/`** (`examples/nested-schema/README.md`): the **nested /
  hierarchical-schema shape** — K=2, `top_level` enum + `sub_category` enum
  conditional on `top_level` via `allOf` + `if/then/else`; aggregate `macro`
  (homogeneous), floor on `top_level`. Canonical discrepancy pattern: "rows where
  `top_level` was right but `sub_category` was wrong" (`README.md:37-43`).
  Exemplifies the unified exception via **hierarchical conditional reasoning**
  (`README.md:55-69`). This is the example that exercises the schema layer's
  "adjacent output shapes the schema layer subsumes" commitment.

- **`feature-group-split/`** (`examples/feature-group-split/README.md`): the
  **decomposition / split shape** — a unified customer-feedback task split into
  three sub-task dirs (`sub-tasks/{sentiment,topic,urgency}/`), each a complete
  independent K=1 `spp/` task. The split (not the internal K-shape) is what makes
  it exemplify the principle (`README.md:35-38`). Carries the granularity
  guidance: big gains on the first split (monolithic → feature-group),
  diminishing returns on further subdivision (feature-group → per-class); split
  natural reasoning-pattern groups, not maximally (`README.md:40-64`).
  **Cross-task composition is out of `spp`'s scope** — the user owns the
  production-pipeline composition layer (`README.md:79-83, 117-119`).

**Coverage summary for the planner:** the examples already demonstrate (a) binary
single-output, (b) unified K>1 multi-field with mixed scalar types + `min`
aggregate + per-field floor, (c) hierarchical/conditional nested schema with
`macro` aggregate, and (d) feature-group decomposition into independent K=1
tasks. **Not demonstrated by any example:** multi-class single-output as its own
example, a SUCCESS-typed termination, adversary-on, a real (non-skeleton) K>1
run, regression/continuous (`number`/MAE/RMSE) as a *primary* target end-to-end
(the `price` field in multi-field-extraction is a skeleton, and the runner can't
score MAE yet — see §5 of `spp-repo.md`), and any **compound/multi-module
pipeline** as a first-class shape (only the user-owned feature-group-split
workaround exists).

---

## 4. Supported task types / output space / scope boundaries

### Supported today (v0.2.0)

`README.md:8-13` (verbatim): "**v0.2.0 supports single-output classification
(binary, multi-class, fixed-schema labeling) plus multi-field structured output,
hierarchical labels (via JSON Schema conditional structures), and freeform
extraction with structured ground truth.**" Restated in "When to use this"
(`README.md:230-236`) and the Roadmap (`README.md:375-379`).

Caveat the planner must carry: per `spp-repo.md:211-227`, K>1 multi-field is
**contract-only** — fully specified in phase/SKILL docs but the runnable
`eval.py` is still v0.1.0 classification-only (`SUPPORTED_METRICS` = f1 / accuracy
/ precision / recall). Regression/continuous (`number` + MAE/RMSE) is named in
the methodology (metric-design SKILL §3.1) and sits **inside** the fixed-output-
space boundary, but is blocked by implementation, not by a methodology
prohibition.

### Explicitly NOT classification-only

This is a key correction the planner needs: v0.2.0 is **no longer
classification-only**. v0.1.0 was scoped to single-output classification
(`CHANGELOG.md:442-460`; `DEVELOP_PLAN.md:26` "v1 supports classification only");
v0.2 generalized the bookkeeping to structured fields / hierarchical labels /
freeform extraction with structured ground truth. The methodology principles are
**output-shape-agnostic** (`README.md:3-7`, `CHANGELOG.md:21-25`).

### Deliberate non-goals (scope boundaries, not roadmap)

`README.md:266-278` ("When NOT to use this") and `DESIGN.md` §7.1.3 (per
`spp-repo.md:430-453`): free-form **generation** (unbounded output, no fixed
label), **tool-use / agentic** prompts, **RAG**, **prompt-injection defense**,
**automated prompt search (DSPy/GEPA/APE fusion)**, **auditor frequency
reduction**, **LLM-as-judge metrics under v1's independence rule**. These are a
different methodology, not a generalization.

### Future (roadmap, §7.1.2)

`README.md:388-401` / DESIGN §7.1.2 (per `spp-repo.md:417-428`): **v0.3**
multi-judge subjective metrics + multilingual; **v0.4** multi-model dev loops /
cross-model synthesis; **TBD** loop resumption mid-iteration, native multi-prompt
support inside `spp` (feature-group splitting is guidance-only today). Generation
/ RAG / agentic explicitly named "separate design pass" (`README.md:401`).

**Guidance for borderline directions** (DESIGN §7.1.3, `spp-repo.md:449-453`):
"When in doubt, lean toward roadmap rather than deliberate." Statistics
(direction 2) and continuous/regression (direction 3) are on **neither** list —
they are new bookkeeping/implementation work inside the existing fixed-output-
space methodology, closest in spirit to the v0.2 seven-bucket precedent.

---

## 5. CHANGELOG structure + how methodology-affecting changes are recorded

### Structure

`/Users/jiafuli/Desktop/Project/spp/CHANGELOG.md` follows **Keep a Changelog
1.1.0 + SemVer** (`CHANGELOG.md:5-6`). Top-down: `## [Unreleased]` (currently
empty, "(Nothing yet.)", `CHANGELOG.md:10-12`), then a `## [X.Y.Z] — YYYY-MM-DD`
section per release (`[0.2.0] — 2026-05-14`, `[0.1.0] — 2026-05-06`).

Each release section opens with **one or more narrative prose paragraphs** (the
release's framing — e.g. the v0.2 paragraph names the bookkeeping generalization,
the methodology-unchanged claim, the seven buckets, and the K=1 backward-compat
guarantee, `CHANGELOG.md:18-41`), then **`### Added` / `### Changed`** subsections
(v0.2 has no Deprecated/Removed/Fixed/Security). v0.1.0 additionally interleaves
several `### Added` / `### Changed` / `### Notes` blocks — one cluster per
underlying PR — because v0.1.0's entries were consolidated at release
(`CHANGELOG.md:574-587`).

### How methodology-affecting changes are recorded (per CLAUDE.md §5)

CLAUDE.md §5 rule: **methodology-affecting PRs** — anything touching agent
information access, gate definitions, the auditor's isolation property, test-set
sacredness, or the build order in DESIGN.md — **must update `CHANGELOG.md` in the
same PR with a description of the methodological implication, not just the code
change.** This is what the planner must write per bucket.

Observed patterns the planner should follow:

- **`BREAKING CHANGE:` prefix in the entry text** for methodology-affecting
  changes. The PR #14 per-stage-isolation entries are the canonical model —
  `CHANGELOG.md:751-825` carries six consecutive `BREAKING CHANGE:` entries
  (spp-loop.md §4 subagent isolation; auditor.md §2 reframe; discrepancy.py
  row-content removal; REPORT.md.template §5 invariant block; loop_spec.md.template
  §3 block expansion; DESIGN.md §4.2 retitle; CLAUDE.md §8 expansion). Each entry
  names the *file*, the *what*, and the *why* (the leakage mode it closes).

- **Each methodology entry states the preservation/shape status.** v0.2 entries
  consistently say either "preserved verbatim" or describe the shape change and
  why substance is preserved, and call out **K=1 backward compatibility**
  (e.g. `CHANGELOG.md:293-308` for the `/spp-loop` step generalizations;
  `CHANGELOG.md:309-318` for auditor per-edit-per-field scoping; "K=1 collapses
  to v0.1.0's per-edit shape").

- **The locked-invariants inventory is recorded as an `### Added` entry**
  (`CHANGELOG.md:103-128`) that enumerates which guarantees are preserved verbatim
  vs shape-changed, plus closing documentation findings — i.e. bucket 6 produces a
  CHANGELOG entry whose body is the preservation audit. This is the template the
  v1.0 inventory bucket should mirror.

- **`### Notes` blocks** record "no methodology changes" explicitly when a PR is
  infrastructure-only (e.g. the scripts PR, `CHANGELOG.md:879-893`: "Infrastructure-
  only; no agent / command / sub-skill / template / top-level doc changes"). The
  planner should write a parallel "Versioning impact: none" / "no methodology
  changes" note for any non-methodology bucket.

- **Dependency changes** go under `### Changed`/`### Added` with justification
  (CLAUDE.md §8); v0.2/v0.1.0 added no new deps (the scripts PR explicitly notes
  "No new dependencies", `CHANGELOG.md:884`).

Per-bucket CHANGELOG implication, concretely: a bucket that touches the auditor's
isolation, a gate, test-set handling, or the build order must (a) carry a
`BREAKING CHANGE:`-flagged entry if it loosens or restructures the contract, or an
ordinary entry stating "preserved verbatim" / the shape change if it generalizes,
and (b) name the K=1 (or compound K=1-equivalent) backward-compat fallback. A
new locked-invariants-inventory bucket records its preservation audit as a single
`### Added` entry mirroring `CHANGELOG.md:103-128`.

---

## Provenance

- STATE doc read in full (162 lines + closing); §1 / §2 quotes are verbatim with
  line refs.
- DESIGN §7.1.1 "Bookkeeping changes by layer" intro (`:491-548`) read directly;
  the seven-bucket list and additivity statement quoted verbatim.
- PR-by-PR arc reconstructed from the PR #30 squash-merge commit body
  (`git show a2872b2`) cross-checked against `STATE:22-41` — individual v0.2 PRs
  #19–#29 are not visible in `git log --oneline` (squashed into `a2872b2 (#30)`).
- All four example READMEs read in full; walkthroughs grepped for field/shape
  details. The shape table is built from the READMEs' "What this example teaches"
  and "Relationship to feature-group splitting" sections.
- CHANGELOG read across both release sections (lines 1-587 + the §5 / PR-#14
  region); the BREAKING-CHANGE pattern verified against `:751-825`.
- Runner-vs-spec statistics gap cross-referenced to `spp-repo.md` §4 (prior pass,
  grep-verified absence of bootstrap/CI/permutation code).
