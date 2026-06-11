# spp roadmap

Direction after v1.0. This is a planning document: it surfaces candidates and states the
release posture. It does not approve, schedule, or implement anything. It honors the
project's hard rules (`CLAUDE.md` §8): nothing here loosens per-stage isolation, auditor
score-blindness, the rule-edit no-row-content rule, or the sacred test set; no locked
invariant ([`DESIGN.md`](DESIGN.md) §7.1.1) is weakened, and no §7.1.3 non-goal is
reclassified as roadmap.

---

## Release posture — slow, patch-first

v1.0.0 froze the methodology ([`DESIGN.md`](DESIGN.md) §7.1.13). The cadence after the
freeze is deliberately slow:

- **Near term is patch-only (`v1.0.x`).** Under the §7.1.13 change policy a patch is bug
  fixes, documentation corrections, and advisor-catalog entries that conform to the frozen
  contract. These ship as `v1.0.1`, `v1.0.2`, … — not `v1.1.0`. Holding minor releases
  back keeps the public surface visibly stable while the project settles.
- **New capability is deferred to `v2.0`.** Anything that changes the frozen surface — a
  new command, a new phase, a new user-facing behavior at the front door — is a major bump
  under §7.1.13, and waits for a dedicated v2.0 design arc opened against the same
  arc-opening convention the v0.x arcs used (a `DESIGN.md` §7.x pin draft, then a small
  sequence of additive PRs, each locked before the next depends on it).

The rest of this document is the holding pen for v2.0 candidates.

---

## v2.0 candidate — front-door onboarding (scan-and-confirm)

**The experience.** Today the user activates `/spp:run` and the consultation begins; the
per-phase `/spp-*` names are internal, not separately invokable. This candidate adds a
discovery front door so the flow becomes:

> run the plugin → it reads the project and understands the current status → it confirms
> what it found → it starts the methodology already configured.

The user no longer hand-writes a long kickoff describing where the baseline, schema, seed
prompt, and test set live; the plugin discovers and confirms them.

**What already exists.** spp does not start from zero here. spp-init runs a reading
checklist over the repo's top-level structure, already detects an existing
`data/baseline.csv` (switching to the bring-your-own-labels path instead of forcing a
fresh labeling pass), and already resumes from an existing `plan.md`. This candidate
promotes that internal reading step into an explicit, user-facing discover → confirm → seed
step.

**The new work.**

1. **Proactive asset discovery** — scan the working directory for candidate roles by
   *shape*, not just by expected path: a CSV shaped like `row_id,text,label` → baseline; a
   JSON Schema → output schema; a held-out split → sacred test; a `prompt_v*.md` → seed
   prompt.
2. **Structured confirmation** — one pass of explicit questions ("`baseline.csv` (N rows):
   your gold baseline? `test_holdout.csv`: register as the sacred test? `prompt_v0.md`:
   start from this?") so discovery is always user-confirmed, never silently assumed.
3. **Auto-seed the plan** from the confirmed answers, so the consultation starts pre-filled
   from real assets rather than a blank task description.

**Why it is v2.0, not v1.0.x.** It adds a user-facing behavior at the command front door —
a surface change under §7.1.13, hence a major bump. It is additive and runs *before* the
methodology proper, so it touches none of the 21 locked invariants. That makes it a clean
v2.0 feature — but a v2.0 feature nonetheless.

**The guardrail.** Discovery *proposes*; the invariants *dispose*. The scan is convenience
only:

- A detected held-out/test file is registered as **sacred** and is never exposed to any
  loop stage — auto-discovery must not become a path that leaks the test set.
- A detected labeled baseline still requires explicit "treat these labels as gold?"
  confirmation; absent that, normal labeling and the `baseline-quality` audit apply.
- Nothing discovered changes a stage allow-list. The front door seeds `plan.md`; it does
  not touch the loop's per-stage isolation.

---

## Other candidates

Reserved. Each future entry must clear the same bar: state the change, name why it is major
versus patch under §7.1.13, and show it weakens no §7.1.1 invariant and reclassifies no
§7.1.3 non-goal.
