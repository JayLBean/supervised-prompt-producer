# CLAUDE.md — Development rules for working on `spp`

This document tells Claude Code (and any other AI assistant) how to
work on this repo. It is not the user-facing methodology document — for
that, see [`README.md`](README.md). It is not the design rationale —
for that, see [`DESIGN.md`](DESIGN.md). It is the rulebook for how
changes get made.

If you are working on `spp` and you have not read [`DESIGN.md`](DESIGN.md)
in this session, stop and read it before editing anything in
`.claude/skills/spp/`. Especially §4.2 (per-stage information isolation)
and §7.1 (non-goals).

---

## 1. Repo purpose

`spp` is a Claude Code skill being built for open-source distribution
(MIT, GitHub). The quality bar is **industry-standard, defensible in
code review** — not internal-team shorthand, not research-prototype
quality. Every doc, every prompt, every error message will be read by a
stranger who has zero context, possibly six months from now. Write
accordingly.

The methodology is settled. The implementation is being built in
phases (see [`DEVELOP_PLAN.md`](DEVELOP_PLAN.md) and
[`CHANGELOG.md`](CHANGELOG.md)). When in doubt about scope, defer to
[`DESIGN.md`](DESIGN.md) §7.1.

---

## 2. Code quality rules

### Python

- **Python 3.11+** for any executable code (template scripts, validation
  harness, example `run.py` files). Don't pin to 3.12+ — broader
  compatibility for contributors with mixed system Pythons.
- **Type hints required on public functions.** Internal helpers may skip
  hints if they're trivially obvious from a one-line body, but anything
  importable across modules gets hints.
- **`ruff` for linting and formatting.** No `black`, no `isort`, no
  `flake8` — `ruff` handles all of them. If a file is not `ruff` clean,
  the commit is not ready.
- **`mypy --strict` on public functions.** Internal helpers can be
  permissive; the boundary between modules cannot.

```sh
ruff check .
ruff format --check .
mypy <changed-file>
```

### Markdown

- No trailing whitespace on lines.
- Single trailing newline at end of file.
- Line wrap at 100 chars where it doesn't break code blocks, links, or
  tables.
- All skill `.md` files (SKILL.md, agent docs, command docs, templates)
  are user-facing. Write them as if a stranger will read them in 6
  months — not as if Claude is writing notes to itself.

### YAML and config

- Indent with 2 spaces.
- Comments explain *why*, not *what*. `# pin pydantic to <3.0 because
  pydantic 3.x changes validator API` is useful; `# pydantic dependency`
  is not.

---

## 3. Version control rules

### Branch naming

`<prefix>/<short-kebab-description>`. Lowercase. Prefixes: `feat/`,
`fix/`, `docs/`, `refactor/`, `test/`, `chore/`. See
[`CONTRIBUTING.md`](CONTRIBUTING.md) for examples.

### Direct commits to `main`

**Never.** Every change is a PR, even from the maintainer. The PR
description follows the template in
[`.github/pull_request_template.md`](.github/pull_request_template.md).

### Merge strategy

**Squash-merge by default.** Merge commits only for cross-branch
integrations where preserving the branch history is meaningful (rare in
this repo).

### Tags

Releases are tagged `v<MAJOR>.<MINOR>.<PATCH>` matching the
corresponding `CHANGELOG.md` entry. Releases are **manual operations** —
do not auto-tag, do not auto-bump versions, do not write release
automation in v1.

---

## 4. Commit message rules — Semantic Commits

Format (from
[joshbuchea/Semantic Commits](https://gist.github.com/joshbuchea/6f47e86d2510bce28f8e7f42ae84c716)):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`chore`, `build`, `ci`, `revert`.

**Subject:** imperative mood ("add", not "added"), no trailing period,
≤72 characters.

**Body:** explains *why*, not *what*. The diff shows what; the message
exists for the reasoning the diff cannot show.

**Footer:** `BREAKING CHANGE:` notes; `Refs: #42`; `Closes: #51`.

### Examples (use these as the canonical reference)

- `feat(designer): add idempotent resumability to /spp-init`
- `fix(auditor): handle empty discrepancy analysis without crashing`
- `docs(readme): clarify v1 classification-only scope`
- `refactor(loop): extract async runner into reusable module`
- `chore(deps): bump pyarrow to 16.x`
- `test(templates): add placeholder lint for plan.md.template`

---

## 5. PR rules

- **PR title** follows the commit-message format. The squash-merge
  produces a commit with that title; write it to be the canonical
  description of the change.
- **PR description** must include:
  1. *What* changed (one paragraph).
  2. *Why* the change is being made.
  3. *How to test it manually* — the reviewer needs to be able to verify
     without re-deriving the test from the diff.
  4. *Open questions* — anything you want the reviewer to weigh in on
     specifically.
- **At least one approving review** is required before merge. For solo
  contributors, the review must be a separate timestamped action — read
  the diff in a separate session, leave an explicit approval, then
  merge. Don't merge without review.
- **Methodology-affecting PRs** (anything touching agent information
  access, gate definitions, the auditor's isolation property, the
  test-set sacredness, or the build order in `DESIGN.md`) **must update
  `CHANGELOG.md` in the same PR** with a description of the
  methodological implication, not just the code change.

---

## 6. Testing rules

- **Skill agents and commands** are tested by running them against
  fixture tasks in `examples/` (populated in Phase 3). A change to an
  agent prompt requires re-running the relevant fixture and updating
  expected outputs if behavior changed, with rationale in the PR
  description.
- **Templates** are validated by a small linter (Phase 4 work) that
  checks they have all required placeholders. New templates require new
  lint coverage.
- **Python code** must pass `ruff check`, `ruff format --check`, `mypy`
  on the changed files, and any relevant `pytest` tests. Don't merge red
  tests. Don't merge with `# noqa` or `# type: ignore` unless the PR
  description justifies each one **and** an inline comment on the line
  itself records the same justification (or a short rationale plus a
  pointer to the PR). PR descriptions are lost to squash-merge; inline
  comments persist with the code, which is where future readers will
  encounter the suppression.

---

## 7. Documentation rules

- **User-facing docs** (`README.md`, all `SKILL.md` files, command docs,
  agent docs, templates) must be reviewed for clarity by reading them
  aloud or having someone else read them. AI-style "let's explore" prose
  is forbidden in shipped docs. Direct, declarative, and specific.
- **Internal-only docs** (`DESIGN.md`, this file) can be terser but must
  still be coherent. They are still read by humans.
- **No emojis** in shipped prose unless the user explicitly requested
  them. None of the user-facing docs in this repo use emojis; new docs
  should follow.

---

## 8. What Claude Code should NOT do

These are hard rules, not preferences:

- **Do not add features not in the kickoff plan** ([`DEVELOP_PLAN.md`](DEVELOP_PLAN.md))
  without first writing a design note (a paragraph in the PR
  description, or a longer comment-thread on an issue) and getting
  explicit approval.
- **Do not modify the source project's reports or methodology
  documents** without explicit instruction. If you are unsure whether a
  document is a reference document or fair game for editing, ask.
- **Do not introduce dependencies** (Python packages, npm modules,
  external services) without justification in the PR description and a
  corresponding `CHANGELOG.md` entry under `### Changed` or `### Added`.
- **Do not auto-version-bump or auto-tag releases.** Releases are
  manual.
- **Do not loosen per-stage information isolation in `/spp-loop`.**
  This is the load-bearing design property described in
  [`DESIGN.md`](DESIGN.md) §4.2 and operationalized in
  [`commands/spp-loop.md`](.claude/skills/spp/commands/spp-loop.md)
  §4 steps 8 (discrepancy), 10 (rule-edit), 11 (auditor), and 9
  (adversary). Each cognitive stage runs in an isolated subagent
  with an explicit allow-list of inputs; the orchestrator
  coordinates, it does not do cognitive work. Breaking changes
  include:
  - **Do not give the auditor sub-agent score access.** Any
    "improvement" that lets the auditor see post-edit dev/test
    scores (`eval.json`, `results.json`, derived hints, summary
    strings) breaks the methodology silently. The right escape
    valve for auditor cost concerns is **batch auditing**, not
    score access and not frequency reduction.
  - **Do not give the rule-edit subagent row-content access.**
    The discrepancy artifact references rows by ID only; the
    rule-edit subagent has no `baseline.csv` / `eval.json` /
    `results.json` access by contract. Adding any path that
    surfaces row content to this subagent reintroduces the
    leakage mode the per-stage architecture was designed
    against.
  - **Do not give the discrepancy subagent prior-iteration
    artifacts.** Its allow-list is the current iteration's
    `eval.json`, `results.json`, disagreed-row content from
    `baseline.csv`, current `prompt_v(N).md`, and `plan.md` §2.
    Prior `discrepancy_analysis.md`, prior `auditor_review.md`,
    or prior `prompt_v(M).md` are out of scope.
  - **Do not break the adversary's allow-list, score-blindness,
    or non-persistence guarantees.**

  PRs that loosen any of these — even accidentally, even in
  helper plumbing — must be rejected.
- **Do not merge PRs that change v1 scope without a design discussion.**
  The canonical scope is [`DESIGN.md`](DESIGN.md) §7 and §7.1. Adding
  extraction tasks, multilingual support, etc., is not a PR — it is a
  roadmap discussion.
- **Do not commit secrets, `.env` files, large binaries, or local
  configuration.** `.gitignore` covers the common cases; if `git status`
  shows something unexpected, investigate before staging.
