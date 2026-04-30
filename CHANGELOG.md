# Changelog

All notable changes to `spp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

- Initial repo scaffold (Phase 1 of the kickoff plan): `LICENSE`,
  `environment.yml`, `.gitignore`, `README.md`, `CODE_OF_CONDUCT.md`,
  `CONTRIBUTING.md`, `CHANGELOG.md`, `CLAUDE.md`, `DESIGN.md`,
  `.github/pull_request_template.md`, and placeholder directories
  (`.claude/skills/spp/`, `examples/`, `tests/`).
- `DESIGN.md` (Phase 0 deliverable) with skill purpose, the two failure
  modes (baseline vs model overfitting), slash-command list, sub-agent
  justifications with the auditor's information-isolation property
  called out as load-bearing, sub-skill list, build order with
  `metric-design` moved to step 3 to reflect actual dependency on the
  designer agent, v1 scope statement, the §7.1 Non-goals canonical
  reference, and the §10 Glossary.
- Conda `environment.yml` defining the `spp-dev` Python 3.11
  development environment with conda-forge as the sole channel, pinned
  minor versions for `pandas`, `numpy`, `scikit-learn`, `httpx`, and
  pip-only deps for `openai`, `python-dotenv`, `pydantic`.

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
