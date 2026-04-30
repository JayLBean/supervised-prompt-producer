# Kickoff — `spp` (Supervised Prompt Producing) Skill

A Claude Code skill that helps users produce production-grade prompts for **classification tasks** through a disciplined, conversational, human-in-the-loop methodology. Open-source, MIT-licensed, distributed via GitHub.

This is a multi-phase build. Read all four phases before starting any of them — Phase 1 decisions cascade into the others. Each phase has its own HARD STOP for review before moving on.

---

## Phase 0 — Understand the project before writing anything

Before any code, any folder, any agent doc — read this entire kickoff and the linked source documents, then write a short `DESIGN.md` at the repo root summarizing your understanding. **HARD STOP** for my review before Phase 1 begins. If your `DESIGN.md` reflects something different from what I describe below, we discuss before you proceed.

### What this skill is

`spp` is a methodology, packaged as a Claude Code skill, for producing prompts that:

- Survive contact with real labeled data (not "looks good" prompts)
- Are accompanied by reproducible evaluation artifacts (baseline, splits, REPORTs, hashed prompts)
- Are honest about their limitations (overfitting modes, model lock-in, failure clusters)

The methodology came from a hair-loss-discourse classification project where the canonical workflow (label baseline → stratified split → optimization loop with dev-driven stop and overfitting guard → final test → REPORT) produced a Qwen-locked prompt with `test F1 = 0.941` and `recall = 1.0`. That project's full plan, runs, and REPORTs are reference material; ask me for them if you don't have them in context.

### What this skill is NOT

- Not an automated prompt optimizer (DSPy, APE-style). The user stays in the loop. The skill enforces discipline; it does not replace human judgment.
- Not task-agnostic. **v1 supports classification only** — binary, multi-class, fixed-schema labeling. Extraction, generation, RAG, agentic prompts are roadmap.
- Not a substitute for `prompt-architect` (the prompt-design template skill). `spp` invokes `prompt-architect`; `prompt-architect` remains independently useful.
- Not self-modifying. Versioned templates get copied into the user's project and frozen there for the duration. The skill itself is stable.

### Core design principles (these are non-negotiable; deviation must be flagged)

1. **Trust the model in the session to think; verify outputs against data.** The model is designer + executor + optimizer simultaneously. Sub-agents exist only when they have structurally different information access or posture, not as ceremony.

2. **Shape spp to the task, not the task to spp.** The designer agent's deepest job at `/spp-init` is figuring out *which version of spp applies* to this user's task. Stripped-down versions (no Phase 3, smaller splits, judge-based metric) are valid outputs. The canonical Phase 1/2/3 is a default, not a mandate.

3. **`plan.md` is a contract, not a wish list.** The designer produces it via consultation; subsequent commands re-read it fresh and check whether actions are still on-spec. Mid-loop changes update `plan.md` with timestamp and reason.

4. **Human-in-the-loop is structured, not ambient.** Specific gates with specific questions and specific allowed responses. No vague "the user can interject." See gate list in §"HITL gates" below.

5. **Two failure modes, treated differently:**
   - **Baseline overfitting** (prompt fits specific labels, fails on similar new data) → deal-breaker, the skill's primary defense target.
   - **Model overfitting** (prompt fits one model's instruction-following style) → contextually fine for production with model lock-in. Documented as a limitation, not prevented.

6. **The methodology has a real failure mode of its own.** Bad baselines produce polished noise. Phase 1 includes explicit baseline quality assurance (sub-skill `baseline-quality`).

7. **Composition over self-containment.** `spp` invokes `prompt-architect`, `metric-design`, `baseline-quality` — they remain independently useful outside `spp`. Resist the urge to absorb them.

### Slash commands (entry points)

The skill exposes four commands. Each is a separate file in `commands/` and operates on `spp/<task_name>/`.

| Command | Purpose | Output | HITL gate after |
|---|---|---|---|
| `/spp-init` | Consultation: read repo, ask informed questions, build `plan.md` | `spp/<task_name>/config/plan.md` | Yes — wait for "approved, proceed to baseline" |
| `/spp-baseline` | Phase 1 + 1.5: label data, generate stratified splits | `baseline.csv`, `splits.json` | Yes — manual baseline review (HARD STOP) |
| `/spp-loop` | Phase 2: optimization loop with auditor sub-agent active | `runs/<model>/run_NN/` | Per-iteration headers + after termination |
| `/spp-finalize` | Phase 3: final test on held-out + REPORT.md generation | `runs/<model>/REPORT.md`, `PROMPT_FROZEN_v01.md` | Yes — show results, recommend, wait for "ship it" or "iterate" |

`/spp-init` must be **idempotent and resumable**. Re-running mid-consultation reads partial `plan.md` and continues. Don't ever clobber a partial.

`/spp-init` must **read the repo first, ask only what it can't infer.** Never ask "do you have data?" when there's a `data/` folder full of files. Start by summarizing what was found and presenting a strawman plan for the user to correct.

`/spp-init` produces `plan.md` and **nothing else**. Not folder structure, not data files, not scripts. The next command does that.

### Sub-agents

Three real agents (each justified by structurally different information access):

1. **designer** — runs during `/spp-init`. Reads the repo, talks to the user, produces `plan.md`. **Distinct because it talks to the user, not the data.** Posture: senior engineer pairing with a junior, surfacing assumptions the user hasn't made explicit, documenting tradeoffs.

2. **auditor** — runs after each `/spp-loop` iteration. Reads the prompt diff and the iteration's discrepancy analysis. Asks: "is this rule edit categorical (addresses a class of rows) or row-specific (patches one weird row)?" **Distinct because it sees the diff but not the new scores**, which forces evaluation of rule generalizability without rationalizing via outcome. Categorical edits kept; row-specific flagged for revert or generalization. This is the single highest-leverage component for preventing baseline overfitting.

3. **adversary** — runs after each `/spp-loop` iteration (optional, configurable in `plan.md`). Generates 2-3 synthetic adversarial rows targeting the latest prompt's likely blind spots. **Distinct because it's deliberately trying to break the prompt**, which is a different posture than evaluating it. Synthetic adversarials are NOT added to the baseline — they're a thought experiment to surface fragility before it ships. Enable for high-stakes tasks; skip for low-cost ones.

Three things that look like agents but aren't (do not create separate agent files for these):

- "optimizer" — this is the loop's normal behavior; ceremony without insight
- "executor" — running scripts is not a cognitive job
- "documenter" — REPORT writing is templated output, not a separate role

If you find yourself wanting to add a fourth agent, justify it against this rule: *what information or posture does this agent have that none of the existing ones do?* If you can't answer, don't create it.

### Sub-skills

Three composable sub-skills (each useful outside `spp`):

1. **prompt-architect** — six-section XML template (Persona, Task, Rules, Output Format, Example Input, Example Output) for production-grade prompts. Already designed; port from existing project.

2. **metric-design** — guides the user through metric selection. Constraint enforced: *the metric must be computable independently of the model being optimized.* No GPT-4 judging GPT-4 prompts. Walks through F1 vs balanced accuracy vs precision-at-recall-floor based on task economics from `plan.md`.

3. **baseline-quality** — runs during Phase 1. Adversarial review of labels themselves, inter-rater spot-checking on borderline cases, calibration questions ("if I labeled this False but you labeled it True, who's right and why?"). Surfaces baseline noise *before* it becomes invisible polish in Phase 2.

### Project artifact layout (per user task)

```
spp/<task_name>/
├── config/
│   ├── plan.md                    # designer's output, becomes the contract
│   └── loop_spec.md               # task-specific instantiation of the loop
├── data/
│   ├── baseline.csv
│   ├── splits.json
│   └── (user's source data — symlinked or referenced, not copied)
└── runs/
    └── <model_identifier>/        # exact model env-var string, no aliasing
        ├── _dryrun/
        ├── run_01/
        │   ├── prompt_v01.md
        │   ├── results.json
        │   ├── eval.json
        │   └── discrepancy_analysis.md
        ├── run_02/
        ├── ...
        ├── PROMPT_FROZEN_v01.md   # production candidate
        ├── REPORT.md              # canonical per-model summary
        └── EARLY_STOP.md | SUCCESS.md | FAILED.md
```

Skill artifacts (the skill itself, installed by users):

```
.claude/skills/spp/
├── SKILL.md                       # router / trigger criteria
├── commands/
│   ├── spp-init.md
│   ├── spp-baseline.md
│   ├── spp-loop.md
│   └── spp-finalize.md
├── agents/
│   ├── designer.md
│   ├── auditor.md
│   └── adversary.md
├── sub-skills/
│   ├── prompt-architect/
│   │   └── SKILL.md
│   ├── metric-design/
│   │   └── SKILL.md
│   └── baseline-quality/
│       └── SKILL.md
└── templates/
    ├── plan.md.template
    ├── loop_spec.md.template
    ├── REPORT.md.template
    └── prompt_v01.md.template
```

Separation discipline (matters): skill files in `.claude/`, project state in `spp/<task_name>/`. Same separation as `git` (program vs. repo). The skill never writes outside `spp/<task_name>/`.

### HITL gates (specific points where the skill stops and waits)

Each gate has a specific question and an allowed-response set. Vague gates are not gates.

| Gate | Stops after | Question | Allowed responses |
|---|---|---|---|
| G1 — plan approval | `/spp-init` produces `plan.md` | "Does this plan reflect what you want? Specifically, are the success criteria, metric, and decision rules correct?" | "approved", or specific corrections |
| G2 — baseline review | Phase 1 labeling complete | "Here are the 100 labels and class balance. Borderline cases highlighted. Approve or correct?" | "approved", row-specific corrections, or "relabel rows X, Y, Z" |
| G3 — split confirmation | `splits.json` written | "Splits: train N (TpercentT/FpercentF), dev M, test K. Class balance preserved. Approve seed and proceed?" | "approved", "different seed", "different ratio" |
| G4 — dry-run gate | `/spp-loop` infrastructure validated on 3 rows | "5 plumbing checks passed. Approve loop start?" | "approved, start loop", or specific fixes |
| G5 — finalization | `/spp-loop` terminates | "Loop terminated via [success/early-stop/limit]. Best dev F1 = X on prompt vNN. Run final test?" | "yes, run final test", or "iterate further" |
| G6 — production decision | `REPORT.md` written | "Production recommendation: model M with prompt vNN. F1=X on test. Limitations: [...]. Ship?" | "ship", "test additional model", "back to loop" |

Each gate is enforced by the relevant command refusing to proceed without the explicit allowed response. Don't accept fuzzy approval; don't auto-proceed on silence.

### Build order discipline

**Build in this order, even though it's tempting to start with the loop runner:**

1. Templates first (`plan.md.template`, `REPORT.md.template`, `loop_spec.md.template`). If you can't articulate what these documents should contain, you don't have the right design.
2. Designer agent next, validated against 2-3 hypothetical example tasks. If it asks the same questions in the same order regardless of task, consultation isn't adapting; redesign.
3. `/spp-init` command, which uses the designer agent.
4. `/spp-baseline` command, with `baseline-quality` sub-skill integrated.
5. `/spp-loop` command, with auditor and (optional) adversary sub-agents.
6. `/spp-finalize` command + REPORT generation.
7. Polish: examples, documentation, contribution model.

Steps 1-2 are the leveraged work. The loop runner is the largest chunk by line count but the lowest risk by design — you have a working version of it from the source project. Don't start there.

### What needs to be in `DESIGN.md` (Phase 0 deliverable)

Before any code, write `DESIGN.md` at repo root containing:

1. One-sentence skill purpose.
2. The two failure modes (baseline vs. model overfitting) and how the skill defends against each.
3. Slash command list with one-line purpose for each.
4. Sub-agent list with the "what info does this agent uniquely have" justification for each.
5. Sub-skill list with one-line purpose for each.
6. Build order with rationale for steps 1-2 leverage.
7. v1 scope statement: classification only, English language assumption (note this), Python ecosystem assumption (note this — non-Python users may not be served by v1).
8. Three open design questions you have for me before proceeding.

Stop after writing `DESIGN.md`. **HARD STOP** for review.

---

## Phase 1 — Solid repo skeleton (no skill code yet)

Build a credible open-source repo *before* writing any skill content. Empty repos with promised features get ignored; well-structured repos with sparse content get starred.

### Files at repo root (in this exact order of creation)

1. **`LICENSE`** — MIT License, current year, your name (ask me for the name to use).

2. **`.gitignore`** — Python + Node + Claude Code conventions. Cover at minimum: `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `env/`, `.env`, `.env.local`, `node_modules/`, `dist/`, `build/`, `*.egg-info/`, `.DS_Store`, `Thumbs.db`, `.idea/`, `.vscode/`, `*.swp`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `coverage/`, `.coverage`, `htmlcov/`, and a section commented `# spp project artifacts (per-task user state, not the skill itself)` covering `spp/*/runs/*/results.json`, `spp/*/runs/*/test_results.json`, `spp/*/runs/*/eval.json`, `spp/*/_dryrun/`. Keep `plan.md`, `REPORT.md`, `PROMPT_FROZEN_*.md`, `splits.json`, and `baseline.csv` tracked — they're the durable artifacts.

3. **`README.md`** — this is the methodology document. See "README contents" below for required sections.

4. **`CODE_OF_CONDUCT.md`** — Contributor Covenant 2.1, unmodified except for the contact email (ask me).

5. **`CONTRIBUTING.md`** — covers: how to file issues, branch naming (`feat/`, `fix/`, `docs/`, `refactor/`), commit message format (Semantic Commits — see CLAUDE.md), how to propose new sub-skills, how to test changes locally before PR, the PR review checklist.

6. **`CHANGELOG.md`** — follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format. Versioned by [Semantic Versioning](https://semver.org/). Initial entry: `## [Unreleased]` with sections for Added/Changed/Deprecated/Removed/Fixed/Security, all empty. First release will be `[0.1.0]` with the v1-classification-only scope.

7. **`CLAUDE.md`** — development rules for Claude Code working on this repo. See "CLAUDE.md contents" below.

8. **`DESIGN.md`** — already written in Phase 0.

9. **Empty placeholder dirs with `.gitkeep`:**
   - `.claude/skills/spp/` (will be populated in Phase 2)
   - `examples/` (worked examples, populated in Phase 4)
   - `tests/` (skill validation tests, Phase 4)

### Development environment (`environment.yml`)

Create a conda `environment.yml` at repo root that contributors use to set up their local dev environment. The file is committed; the resulting `.conda/` or `venv/` directories are not (already covered by `.gitignore`).

#### Constraints on the env file

- **Python 3.11.** Matches the rule in CLAUDE.md. Don't pin to 3.12+ — broader compatibility for contributors with mixed system Pythons.
- **Conda-forge channel only.** Avoid the `defaults` channel for licensing clarity in an open-source project.
- **Pin minor versions, not patches.** `python>=3.11,<3.12` not `python=3.11.5`. Patches change for security; minors change behavior.
- **Group dependencies by purpose** with comments. Future contributors should be able to read the file and understand what each block is for.
- **Use pip section sparingly** — only for packages that aren't on conda-forge or where conda-forge versions lag behind. Each pip dep needs a comment explaining why it's not in the conda block.

#### Required dependency categories

1. **Core Python** — `python>=3.11,<3.12`, `pip`.
2. **Code quality** — `ruff` (linter + formatter, both in one tool), `mypy` (type checking, configured strict on public functions), `pytest` (test runner), `pytest-cov` (coverage).
3. **Data handling for examples** — `pandas`, `numpy`, `pyarrow`. The skill itself doesn't run code, but the worked examples in Phase 3 need to load `baseline.csv`, generate `splits.json`, etc. The dev env supports running examples end-to-end.
4. **ML eval** — `scikit-learn` (for `f1_score`, `confusion_matrix`, `train_test_split` with stratification — same library used in the source project).
5. **LLM clients** — `openai` (covers OpenAI direct and any OpenAI-compatible endpoint, including local MLX servers and GitHub Models if anyone wants to test). Pin `openai>=1.50,<2.0`.
6. **HTTP / async** — `httpx>=0.27,<1.0` (transitive via openai but worth pinning explicitly since `run.py` uses async client directly).
7. **Env management** — `python-dotenv>=1.0` for `.env` file loading in examples.
8. **Validation** — `pydantic>=2.7,<3.0` (used by templates and by sub-skill validation harness in Phase 4).
9. **Documentation tooling** (commented out for v1, listed for future) — `mkdocs`, `mkdocs-material` if you decide to publish docs at v0.2+. Don't include in v1 env.

#### What NOT to include

- No GPU-specific packages (CUDA, MLX, ROCm). Examples that need local inference document their own requirements separately. The default env runs against API endpoints.
- No heavy notebook dependencies. Add `jupyterlab` only if Phase 3 examples genuinely need notebooks; default to `.py` scripts.
- No specific model SDKs beyond OpenAI's. Anthropic's SDK, Google's, etc. can be added per-example if needed but bloat the default env.
- No linting tools beyond `ruff`. Don't add `black`, `isort`, `flake8` — `ruff` handles all of them.

#### Naming and activation

- Env name: `spp-dev` (short, distinct from any user-project envs).
- Activation: `conda env create -f environment.yml` then `conda activate spp-dev`.
- Document this in the "Development setup" section of CONTRIBUTING.md.

#### Update discipline

- Adding a dependency requires:
  1. Justification in the PR description (what does this enable; why isn't it possible with current deps).
  2. CHANGELOG entry under `### Changed` for the relevant unreleased version.
  3. Update to README quickstart if the dep changes the install story.
- Removing a dependency requires checking that no example or sub-skill imports it. Run the validation harness (Phase 4) before merging the removal.
- Bumping a major version (e.g. `pydantic 2.x → 3.x`) is a separate PR with explicit migration testing on all examples.

The `environment.yml` should be the second file created in Phase 1 (after `LICENSE`, before `.gitignore`), because subsequent files reference dev tools defined here. The file structure should look roughly like:

```yaml
# spp — supervised prompt producing
# Development environment for contributors.
# See CONTRIBUTING.md for setup instructions.

name: spp-dev
channels:
  - conda-forge
dependencies:
  # Core Python
  - python>=3.11,<3.12
  - pip

  # Code quality
  - ruff
  - mypy
  - pytest
  - pytest-cov

  # Data handling for worked examples
  - pandas>=2.2,<2.3
  - numpy>=1.26,<2.0
  - pyarrow>=16

  # ML evaluation utilities
  - scikit-learn>=1.4

  # Async HTTP (used by example run.py scripts)
  - httpx>=0.27,<1.0

  # Pip-only deps (not on conda-forge or version lag)
  - pip:
      # OpenAI-compatible client; covers OpenAI direct, MLX servers, etc.
      - openai>=1.50,<2.0

      # .env loading for examples
      - python-dotenv>=1.0

      # Schema validation (used by template linter in Phase 4)
      - pydantic>=2.7,<3.0
```

Treat this as a starting point. The actual `environment.yml` you commit may differ slightly based on what Phase 2/3 work actually needs. If you discover a missing dep during a later phase, add it via a `chore(deps):` PR with the justification rule above.

### README contents (the methodology document)

Structure:

1. **Headline** — one sentence: "A Claude Code skill for producing production-grade classification prompts through disciplined, human-in-the-loop supervised prompt learning."

2. **The problem** (2-3 paragraphs) — prompt engineering by feel produces prompts that look good and fail in production. Existing automation (DSPy, APE) trusts metrics that can lie, especially when the metric is computed against a single model on a single dataset. Both approaches miss two distinct failure modes.

3. **The two failure modes** (with concrete examples from the source project):
   - Baseline overfitting: prompt learns to game specific labels. Caught by stratified train/dev/test discipline with sacred test set.
   - Model overfitting: prompt learns to exploit one model's instruction-following style. Found in the source project when a Qwen-optimized prompt scored F1=0.76 on GPT-4o-mini and F1=0.91 on GPT-4o full, with a length-correlated cluster failing on both. Documented as a limitation; acceptable for production with model lock-in.

4. **The methodology** — Phase 1 (baseline + QA), Phase 1.5 (stratified split), Phase 2 (loop with dev-driven stop, overfitting early-stop guard, auditor sub-agent), Phase 3 (final held-out test + REPORT). Diagram if useful.

5. **What `spp` does and doesn't automate** — Honest table. Automates: scripts, evaluation, discrepancy analysis, REPORT generation. Doesn't automate: metric design, baseline labeling judgment, decision criteria, model selection. Human stays in those loops.

6. **When to use this** — Production prompts running ≥1000 times, classification tasks with definable labels, model lock-in known, willingness to label 50-100 baseline rows. **When NOT to use this** — one-shot chat prompts, generation tasks (v1 doesn't support), tasks without ground truth.

7. **Quickstart** — `/spp-init`, answer questions, follow gates. Link to a worked example.

8. **Comparison to alternatives** — short, fair section comparing to DSPy ("DSPy automates the search; spp helps you figure out what to search for and keeps you in the loop"), to manual prompt engineering ("spp adds discipline and reproducibility"), to no-methodology approaches ("spp produces prompts you can defend in code review").

9. **Roadmap** — v1 is classification. Future: extraction, generation, multi-judge metrics for subjective tasks, multi-model dev loop (the v2 methodology note from the source project).

10. **Citations / acknowledgements** — to DSPy, prompt-architect, the methodologies that inspired this. Honest crediting.

11. **License + contributing** — links to LICENSE, CONTRIBUTING, CODE_OF_CONDUCT.

The README is the artifact that gets read most. Write it well. It should stand alone as a methodology document even for someone who never installs the skill.

### CLAUDE.md contents (development rules)

This document tells Claude Code how to work on the repo. Sections:

1. **Repo purpose** — one-paragraph context. This is a Claude Code skill being built for open-source distribution. Quality bar: industry-standard, defensible in code review.

2. **Code quality rules:**
   - Python 3.11+ for any executable code (template scripts, validation harness).
   - Type hints required on public functions.
   - `ruff` for linting, `ruff format` for formatting. No exceptions; if a file isn't ruff-clean, the commit isn't ready.
   - Markdown files: no trailing whitespace, single trailing newline, line wrap at 100 chars where it doesn't break code blocks or links.
   - All skill `.md` files (SKILL.md, agent docs, command docs, templates) are user-facing. Write them as if a stranger will read them in 6 months.

3. **Version control rules:**
   - Branch naming: `feat/<short-description>`, `fix/<short-description>`, `docs/<...>`, `refactor/<...>`, `test/<...>`, `chore/<...>`. Lowercase, kebab-case after the prefix.
   - Never commit directly to `main`. Every change is a PR, even from the maintainer. The PR description follows the template in `.github/pull_request_template.md` (create this in Phase 1).
   - Squash-merge by default. Merge commits only for cross-branch integrations.
   - Tag releases with `v<MAJOR>.<MINOR>.<PATCH>` matching CHANGELOG entries.

4. **Commit message rules — Semantic Commits.** Required format from https://gist.github.com/joshbuchea/6f47e86d2510bce28f8e7f42ae84c716:
```
   <type>(<scope>): <subject>

   <body>

   <footer>
```
   Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `build`, `ci`, `revert`. Subject in imperative mood ("add", not "added"), no period, ≤72 chars. Body explains *why*, not *what* (the diff shows what). Footer for `BREAKING CHANGE:` notes and issue refs (`Refs: #42`, `Closes: #51`).
   - Examples (include in CLAUDE.md verbatim):
     - `feat(designer): add idempotent resumability to /spp-init`
     - `fix(auditor): handle empty discrepancy analysis without crashing`
     - `docs(readme): clarify v1 classification-only scope`
     - `refactor(loop): extract async runner into reusable module`

5. **PR rules:**
   - PR title follows commit message format (it becomes the squash-merge commit).
   - PR description must include: what changed, why, how to test it manually, any open questions for the reviewer.
   - All PRs require at least one approving review (self-review acceptable for solo dev, but the review must be a separate timestamped action — read the diff, not just merge).
   - PRs that change the methodology (any file under `.claude/skills/spp/` that's user-facing) must update CHANGELOG.md in the same PR.

6. **Testing rules:**
   - Skill agents and commands are tested by running them against fixture tasks in `examples/`. A change to an agent prompt requires re-running the relevant fixture and updating expected outputs if behavior changed (with rationale in PR description).
   - Templates are validated by a small linter (Phase 4 work) that checks they have all required placeholders.

7. **Documentation rules:**
   - User-facing docs (README, SKILL.md, command docs, agent docs, templates) must be reviewed for clarity by reading them aloud or having someone else read them. AI-style "let's explore" prose is forbidden in shipped docs.
   - Internal-only docs (DESIGN.md, this file) can be terser but must still be coherent.

8. **What Claude Code should NOT do:**
   - Do not add features not in the kickoff plan without writing a design note first and getting approval.
   - Do not modify the source project's reports or methodology document without explicit instruction.
   - Do not introduce dependencies (Python packages, npm modules) without justification in the PR description and a corresponding CHANGELOG entry.
   - Do not auto-version-bump or auto-tag releases. Releases are manual operations.

### Phase 1 deliverable

A repo at `main` that has all 9 root files plus the placeholder dirs, with one initial commit per file (or grouped sensibly: `chore: initial repo scaffold` is fine for the first batch). The README should be readable and standalone as a methodology overview, even though no skill code exists yet.

**HARD STOP** after Phase 1. I review the repo skeleton — especially README and CLAUDE.md — before any skill content is written.

---

## Phase 2 — Skill content (templates, agents, sub-skills, commands)

This is where the actual skill gets built, in the build order from Phase 0:

1. Templates (`plan.md.template`, `REPORT.md.template`, `loop_spec.md.template`, `prompt_v01.md.template`).
2. `designer.md` agent, validated against 2-3 hypothetical task fixtures.
3. `/spp-init` command file, integrating the designer agent.
4. `baseline-quality` sub-skill.
5. `/spp-baseline` command, integrating Phase 1 labeling and `baseline-quality` review.
6. `auditor.md` agent.
7. `adversary.md` agent (optional sub-component).
8. `/spp-loop` command, integrating auditor.
9. `/spp-finalize` command + REPORT generation.
10. `prompt-architect` sub-skill (port from source project).
11. `metric-design` sub-skill.
12. Top-level `SKILL.md` that routes between the four commands.

Each step is a separate PR. Each PR includes:
- The new/modified content
- A CHANGELOG entry
- Manual testing notes in the PR description
- Updates to README quickstart if the user-facing flow changed

**HARD STOP** after each PR for review. No batching agent or command implementations into one giant PR — they review badly and bugs hide.

---

## Phase 3 — Worked examples (the part that makes the skill credible)

Three example tasks in `examples/`:

1. **`examples/binary-classification/`** — port the source hair-loss project (sanitized if needed). This is the canonical example. Includes baseline.csv, splits.json, all three model REPORTs, the v01 frozen prompt, and a walkthrough doc explaining how the user would have used `spp` to produce these artifacts (since the original project predates the skill).

2. **`examples/multi-class-classification/`** — a hypothetical or real example of a 3-5 class labeling task. This proves the skill flexes beyond binary. Smaller scale (50 baseline rows) so it's quick to follow.

3. **`examples/edge-case-imbalanced/`** — a task with 90/10 class imbalance, where the metric has to be precision-at-recall-floor or balanced accuracy instead of plain F1. This proves the metric-design sub-skill earns its place.

Each example has its own `plan.md` (so users can see what a real one looks like), its own per-model REPORTs, and a top-level walkthrough doc.

The examples are the part that converts skeptical readers into users. Underweighted in most open-source skill projects.

---

## Phase 4 — Polish, tests, and v0.1.0 release

1. **Skill validation harness** — a small Python script in `tests/` that loads each agent and command file, validates the templates have all required placeholders, and runs the canonical example through a dry-run mode (no real LLM calls; just verifies the workflow doesn't crash on the structured inputs).

2. **CI** — GitHub Actions workflow that runs ruff, runs the validation harness on every PR, and checks that CHANGELOG.md was updated for any PR touching `.claude/skills/spp/`.

3. **Docs polish** — README final pass with diagrams, screenshots if applicable. CONTRIBUTING.md final pass with a "first PR" walkthrough.

4. **Release prep** — finalize CHANGELOG.md `[0.1.0]` entry, tag `v0.1.0`, write GitHub release notes, post to relevant communities (Anthropic Discord, r/LocalLLaMA, /r/MachineLearning, HN if you want).

5. **Roadmap doc** — `ROADMAP.md` at repo root with v0.2 (extraction tasks), v0.3 (multi-judge subjective metrics), v0.4 (multi-model dev loop) sketched out. Honest about what's not yet supported.

---

## Things to avoid throughout

- Building the loop runner first because it feels concrete. Steps 1-2 of Phase 2 are leveraged work; loop runner is execution.
- Adding sub-agents for ceremony. Three real agents is the right number for v1.
- Self-modifying skill behavior. Versioned templates, frozen at user-project time.
- Promising features in README that don't exist yet. Roadmap section is for those; main README is for shipped behavior.
- Shipping without examples. The methodology doc plus one canonical worked example is the minimum credible release.
- Forgetting that this is for distribution. Every doc, every prompt, every error message will be read by someone who has zero context. Write accordingly.

---

## Open questions to surface in `DESIGN.md`

Three I expect you'll have:

1. Should sub-skills (`prompt-architect`, `metric-design`, `baseline-quality`) live inside `.claude/skills/spp/sub-skills/` or as peer skills at `.claude/skills/`? Tradeoff: nesting makes them clearly part of `spp` but harder to use independently. Peer placement makes composition cleaner but the install story is "you need to install 4 skills." My current preference is nested for v1 (simpler install) with a note in README about how to extract them as peers in v0.2.

2. Does `/spp-loop` need to support resuming after interruption? An interrupted iteration is a real failure mode for long runs. My current preference: yes, but defer to v0.2 — for v1, document that interruption requires restart.

3. How does the skill handle users who have non-English data? My current preference: v1 assumes English, documents the assumption clearly, and accepts that translation/multilingual is a meaningful future scope question. Don't try to handle it implicitly.

Surface your answers to these (or different open questions) in `DESIGN.md` for review.

---

Begin Phase 0. Write `DESIGN.md`. Stop. Wait for review.