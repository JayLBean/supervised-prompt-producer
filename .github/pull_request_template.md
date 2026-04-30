<!--
Thanks for opening a PR. Please fill in each section below before requesting
review. PRs that skip sections are likely to be sent back without review.

The PR title should follow the Semantic Commits format used for commit
messages, since the squash-merge will use it as the canonical commit
subject. See CLAUDE.md §4 for the format and CONTRIBUTING.md for examples.

Example title: feat(designer): add idempotent resumability to /spp-init
-->

## What changed

<!-- One paragraph describing the change. The diff shows the details; this is
the executive summary. -->

## Why

<!-- The reasoning the diff cannot show. What problem does this solve? What
alternatives did you consider? If this is a methodology-affecting change
(touches an agent's information access, a HITL gate, the auditor's isolation
property, the test-set sacredness, etc.), include the design rationale here
that future contributors will need. -->

## How to test it manually

<!-- Specific steps a reviewer can run to verify the change. If you ran the
change against an example fixture, name the example and the before/after
output. If you ran ruff/mypy/pytest, mention the result. The reviewer needs
to be able to verify without re-deriving the test plan from the diff. -->

## Open questions for the reviewer

<!-- Anything you want the reviewer to weigh in on specifically. Leave this
empty if there are none, but check first — most non-trivial PRs have at
least one. -->

## Checklist

- [ ] Branch follows the `<prefix>/<short-kebab-description>` convention
      (`feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/`).
- [ ] Commits follow Semantic Commits format with `*why*`-focused bodies.
- [ ] PR title matches the squash-merge commit message format.
- [ ] If user-facing (touches anything under `.claude/skills/spp/` that users
      see), `CHANGELOG.md` is updated under `## [Unreleased]` in this PR.
- [ ] If a Python dependency is added or bumped, `environment.yml` is
      updated and the change is justified above under "Why".
- [ ] If methodology-affecting (auditor, gates, splits, scope), the design
      rationale is recorded above under "Why".
- [ ] `ruff check .` and `ruff format --check .` pass on Python files
      changed.
- [ ] `mypy` passes on Python files changed.
- [ ] No emojis added to user-facing prose.
- [ ] No secrets, `.env` files, or large binaries committed.
- [ ] Read the diff again after a break before requesting review.
