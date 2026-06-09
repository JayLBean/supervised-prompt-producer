# Contributing to `spp`

Thanks for your interest in contributing. `spp` is a methodology packaged
as a Claude Code skill, distributed open-source so that prompt
engineering for classification tasks can be more disciplined and
reproducible. This document explains how to contribute in a way that
keeps the methodology coherent and the repo reviewable.

Before opening a PR, please read [`DESIGN.md`](DESIGN.md) (especially
§7.1 Non-goals) and [`CLAUDE.md`](CLAUDE.md). Most contribution
questions are answered there.

---

## Table of contents

- [Development setup](#development-setup)
- [How to file an issue](#how-to-file-an-issue)
- [Branch naming](#branch-naming)
- [Commit message format](#commit-message-format)
- [Proposing a new sub-skill or sub-agent](#proposing-a-new-sub-skill-or-sub-agent)
- [Testing changes locally](#testing-changes-locally)
- [PR review checklist](#pr-review-checklist)
- [What is and isn't in v1 scope](#what-is-and-isnt-in-v1-scope)

---

## Development setup

`spp` uses a conda-based Python 3.11 environment for contributors. The
skill itself does not run code at use-time — the skill files are
instructions for Claude Code — but the worked examples and validation
harness need a real Python environment.

```sh
# From repo root
conda env create -f environment.yml
conda activate spp-dev
```

This installs:

- `ruff`, `mypy`, `pytest`, `pytest-cov` — code quality and tests
- `pandas`, `numpy`, `pyarrow`, `scikit-learn` — data handling for
  examples
- `httpx`, `openai`, `python-dotenv`, `pydantic` — async HTTP, LLM
  clients, env loading, schema validation

See [`environment.yml`](environment.yml) for the full pinned list. The
environment name is `spp-dev`.

To verify your setup:

```sh
ruff --version
pytest --version
python -c "import pandas, sklearn, openai, pydantic; print('ok')"
```

If any of those fail, the env didn't install cleanly. Open an issue with
the conda solver output rather than working around it.

---

## How to file an issue

Before opening an issue, search existing issues — `spp`'s scope is
narrow (see §7.1 of `DESIGN.md`) and many feature requests have already
been triaged.

A good issue includes:

- **What you tried.** Either a command sequence (`/spp-init`, etc.) or a
  link to the file you were editing.
- **What happened.** Exact output if relevant; screenshots if a UI
  artifact is involved.
- **What you expected.** This is the part that's easy to skip and
  costly to skip — the gap between expected and actual is where the
  conversation lives.
- **Environment.** OS, Python version (`python --version`), Claude Code
  version if relevant.

For feature requests, lead with the **problem you are solving**, not the
solution you have in mind. The maintainers may have a different solution
to the same problem.

---

## Branch naming

All branches follow `<prefix>/<short-kebab-description>`. Lowercase
only.

| Prefix | Purpose |
|---|---|
| `feat/` | New user-facing capability |
| `fix/` | Bug fix |
| `docs/` | Documentation changes only |
| `refactor/` | Internal restructuring without behavior change |
| `test/` | Adding or fixing tests / fixtures |
| `chore/` | Build, deps, repo hygiene (`chore(deps): bump pydantic`) |

Examples:

- `feat/auditor-batch-mode`
- `fix/spp-init-empty-data-dir`
- `docs/clarify-non-english-scope`
- `chore/deps-pyarrow-bump`

Never commit directly to `main`. Every change — even from the
maintainer — goes through a PR.

---

## Commit message format

`spp` follows
[Semantic Commits](https://gist.github.com/joshbuchea/6f47e86d2510bce28f8e7f42ae84c716):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`chore`, `build`, `ci`, `revert`.

**Subject:** imperative mood ("add", not "added"), no trailing period,
≤72 characters.

**Body:** explains *why*, not *what*. The diff already shows what
changed; the commit message exists to record the reasoning that the diff
cannot.

**Footer:** for `BREAKING CHANGE:` notes and issue references
(`Refs: #42`, `Closes: #51`).

Examples:

- `feat(designer): add idempotent resumability to /spp-init`
- `fix(auditor): handle empty discrepancy analysis without crashing`
- `docs(readme): clarify v1 classification-and-extraction scope`
- `refactor(loop): extract async runner into reusable module`

---

## Proposing a new sub-skill or sub-agent

`spp`'s sub-agent and sub-skill counts are **deliberately constrained**.
Adding either is a structural change that requires design discussion
before code.

### For a new sub-agent

Open an issue first. Justify the agent against the rule in
[`DESIGN.md`](DESIGN.md) §4: *what information or posture does this agent
have that none of the existing three (designer, auditor, adversary)
have?* If you can't answer that question, the agent should not exist —
its work belongs in one of the existing agents or in a command's normal
flow.

Common rejected patterns:

- "Optimizer" agent — the loop's normal behavior is the optimizer.
  Adding an agent is ceremony.
- "Documenter" agent — `REPORT.md` is templated output, not authored.
- "Executor" agent — running scripts is not a cognitive job.

### For a new sub-skill

Sub-skills must be **independently useful outside `spp`**. If the
sub-skill is only meaningful within a single command's flow, it is not a
sub-skill — it is part of that command. The current three
(`prompt-architect`, `metric-design`, `baseline-quality`) each meet this
bar.

Open an issue describing:

1. The standalone use case (someone using the sub-skill *without* `spp`).
2. The interface (what input it takes, what output it produces).
3. Why it doesn't fit inside an existing sub-skill.

---

## Testing changes locally

`spp` is a Claude Code skill, so "testing" comes in three flavors
depending on what you're changing.

### Changes to skill `.md` files (agents, commands, templates, sub-skills)

Run them against the canonical fixtures in `examples/`. A change to an
agent prompt requires re-running the relevant fixture and updating
expected outputs if behavior changed (with rationale in the PR
description).

If your change affects user-visible flow (a new question the designer
asks, a new gate, a new option in `plan.md`), include in the PR
description:

- Which example you ran the change against.
- Before/after of the user-visible behavior.
- Whether existing examples still produce equivalent outputs.

### Changes to templates, catalogs, and the frozen contracts

A linter family (DESIGN.md §7.1.13) mechanically enforces the frozen
surface: the six templates' placeholders and sections, the `ENTRY_SCHEMA`
catalog entries, the six-section prompt (#12), the REPORT §5 invariant
block (#21), and the `loop_spec.md` literal blocks (#18). Run the whole
family with one command before a PR (from `skills/run/`):

```sh
python -m scripts.lint_all
```

The same checks run under the test suite. Individual artifacts can be
validated directly:

```sh
# From skills/run/:
python -m scripts.lint_templates templates              # the shipped templates
python -m scripts.lint_templates plan path/to/plan.md   # a filled plan
python -m scripts.lint_templates prompt path/to/prompt_v01.md
python -m scripts.lint_catalogs                         # both advisor catalogs
```

### Changes to Python code (validation harness, example scripts)

```sh
ruff check .
ruff format --check .
mypy <changed-file>
pytest
```

PRs touching Python must be ruff-clean and mypy-clean on the changed
files.

---

## PR review checklist

Before requesting review, verify the following. The reviewer will
check the same list, so doing it yourself first saves a round-trip.

- [ ] Branch follows the naming convention (`feat/`, `fix/`, etc.).
- [ ] Commits follow the Semantic Commits format with `*why*`-focused
      bodies.
- [ ] PR title matches the squash-merge commit message format.
- [ ] PR description covers: what changed, why, how to test it manually,
      open questions for the reviewer.
- [ ] If the change is user-facing (touches anything under
      `skills/run/` that users see), [`CHANGELOG.md`](CHANGELOG.md)
      is updated in the same PR under `## [Unreleased]`.
- [ ] If the change introduces a Python dependency, the dep is added to
      [`environment.yml`](environment.yml) with a comment, and the PR
      description justifies it.
- [ ] If the change is methodology-affecting (touches an agent's
      information access, a gate's allowed responses, the auditor's
      isolation property, etc.), the PR description includes the
      design-rationale paragraph that future contributors will need to
      understand the choice.
- [ ] `ruff check .` passes on any Python files changed.
- [ ] No emojis in user-facing prose unless the user explicitly
      requested them.

PRs require **at least one approving review** before merge. Solo
contributors should self-review by reading the diff after a break — a
separate, timestamped action — rather than merging without review.

PRs are squash-merged by default. The squash-merge commit message is
the PR title plus the PR description body, so write both with that in
mind.

---

## What is and isn't in v1 scope

v1.0 is a **stabilization release** — the contract freeze. The whole v0.x
roadmap has shipped, so what v1 supports is broad, and what it will *never*
support is a small, permanent list. The canonical references are
[`DESIGN.md`](DESIGN.md) §7.1.13 (the frozen surface and the post-1.0 change
policy), §7.1.2 (the now-landed roadmap), and §7.1.3 (the deliberate
non-goals). Read those before opening a scope-related issue or PR.

**In scope (shipped through v0.11, frozen at v1.0).** Classification (binary,
multi-class, fixed-schema) and **structured extraction** (variable-cardinality,
span-grounded); multi-field structured output and hierarchical labels;
finalize-layer bootstrap statistics; the K>1 multi-field runner; failure-driven
technique suggestions; input preprocessing and **multilingual data**;
judge-panel-assisted baseline labeling; operational hardening (per-step loop
resumption, the sacred-test-set hook); batch I/O; and **prompt decomposition**
(a managed linear pipeline). If you read an older note calling extraction,
multilingual, decomposition, or loop resumption "future" or "not in v1 scope,"
that note is stale — they shipped.

**Deliberate non-goals (permanent, not roadmap — §7.1.3).** These are out of
scope by methodology design, not waiting for a future version:

- Generation-task methodologies (summarization, rewriting, instruction tuning,
  multi-turn conversation)
- Tool-use / agentic prompts
- RAG (retrieval-augmented) prompts
- Prompt-injection defense and jailbreak resistance
- Automated prompt search (DSPy / GEPA / APE composition)
- Auditor frequency reduction (the right escape valve is batch auditing — see
  §4.2)
- Cross-model synthesis (`spp` optimizes per target model; compare downstream)
- LLM-as-judge metrics inside the scoring path

Each of these would require a different validation primitive — most cross the
metric-independence line (invariant #13) — so admitting one is not a feature
request, it is a different methodology. Per the §7.1.13 change policy, anything
that touches the frozen surface or the non-goals is a **v2.0** discussion: start
it in an issue, not an unsolicited PR.

---

## Questions

If something in this document is unclear or you're not sure whether your
change fits, open an issue with the `question` label and ask. Better to
ask early than to write a PR that gets sent back for scope reasons.
