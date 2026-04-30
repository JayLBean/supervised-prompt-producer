# Changelog

All notable changes to `spp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

Phase 2 step 3 ships under PR title
**feat(commands): scaffold /spp-init command and pattern lock for
subsequent commands**, targeting `dev`. Phase 1 and Phase 2 steps 1
and 2 already merged.

### Added

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
