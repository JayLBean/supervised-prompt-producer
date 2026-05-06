# Fixture 1 — consultation shape

This is a narrative, not a script. The designer adapts; the notes
describe the *shape* of the consultation, not specific phrasings.

---

## What the designer should do before its first message

Run the §3 reading checklist:

- See `data/tickets.csv` exists, 4,287 rows, columns include
  `closed_by` (a routing target — informative for stratification)
  and `language` (recently added — surfaces a bilingual concern).
- Read `README.md`: heuristic classifier, plateau at 73%, looking
  for LLM replacement. The task is concrete and already framed.
- See `pyproject.toml` lists `openai>=1.50` — OpenAI-compatible
  client is available.
- Note recent commit `feat(routing): add language column for
  bilingual support` — surfaces a possible scope question
  (English-only baseline vs. bilingual).
- Note `q3r4s5t docs: note the 73% accuracy plateau` — confirms
  the user's motivation.

The designer does **not** ask "do you have data?" — `data/` is
right there. It does not ask "what does this project do?" — the
README answers it.

## The strawman the designer presents first

A specific proposal that demonstrates the scan paid off:

- **Task:** binary classification of support tickets as
  Billing-relevant or Not, replacing the 73%-accuracy heuristic.
- **Production model:** `gpt-4o-mini` (since `openai` is already
  a dep and you mentioned looking for a cheap LLM replacement).
- **Baseline:** 80 rows sampled stratified-uniform on
  `closed_by`, since the README and your `closed_by` column
  imply team-by-team variance.
- **Metric:** F1, with rationale that mis-routing is the cost
  function — invite the user to weight precision vs recall by
  the asymmetry of mis-routing.
- **Scope:** full Phase 1 + 1.5 + 2 + 3 (no constraints visible
  that argue for stripping).
- **Open question:** the recent `language` column suggests a
  bilingual concern — should the baseline be English-only and
  the Spanish stream be tracked as a follow-on, or should
  baseline include both?

## Where the user's reply diverges from the strawman

- Pins the model to `gpt-4o-mini-2024-07-18` (no aliasing —
  `DESIGN.md` §2.2 + plan.md.template validation rule 6).
- Refines stratification to `closed_by` × class (joint
  stratification).
- Confirms FP/FN asymmetry is ~2:1 against false-positives —
  metric should be **F1** but the designer should note this as
  a precision-leaning task in the metric rationale (and feed
  metric-design with the asymmetry).
- Clarifies labels are not yet collected; `BASELINE_STATUS` is
  `not-started` on initial entry.

## Follow-up questions the designer asks

After the rebuttal, the designer asks:

- §5.1 borderline class question: "give me a row that's clearly
  Billing and one that you might disagree with someone else
  about." User volunteers the "subscription cancelled without
  charge dispute" boundary — this becomes a known borderline in
  `plan.md` §2 `BORDERLINE_NOTES`.
- §5.2 headline criterion: user implicitly already gave it
  (precision-leaning F1); the designer confirms but does not
  re-interrogate.
- §5.3 lock-in posture: user says "we're locked on
  `gpt-4o-mini-2024-07-18` for cost reasons" → posture =
  `locked`.
- §5.4 baseline questions:
  - Source: `data/tickets.csv` confirmed.
  - Size: 80 confirmed.
  - Class balance: production prevalence (~20% billing per the
    user's heuristic) — the designer captures the asymmetry as
    a stratified-stratify-on-class plus retain-prevalence
    instruction.
  - Provenance: solo labeler (one of the user's team), with the
    `baseline-quality` adversarial review applied.
- §5.5 gate phrases: "approved" for G1-G5, "ship it" or "send
  back" for G6.
- §5.7 open questions: the bilingual question stays open; user
  defers it to the baseline review. Recorded in `plan.md` §10.

The designer does **not** re-ask things the user has already
answered. It does not ask the lock-in posture question if the
user already said "we're locked on X for cost reasons" before
the question was raised.

## What's *not* in this consultation

- No stripped-scope discussion — no constraints argue for
  stripping.
- No discussion of `BASELINE_STATUS = complete` — the user has no
  labels yet.
- No discussion of multi-judge metrics — `DESIGN.md` §7.1 says
  they're forbidden in v1, and metric independence per §5.4 is
  satisfied by F1 vs ground-truth labels.

## Validation gate behavior

When the designer assembles `plan.md`, it runs the 12 mechanical
validation rules. All pass on first attempt for this fixture
because the user's answers are unambiguous. The designer presents
the plan at G1 and waits for "approved."

If `plan.md.template` validation rule 11 fails (some gate row
empty), the designer returns with: "G2 approval phrase is empty;
which phrase counts as approval at the baseline-review gate?"
That doesn't happen here — the user provided all six.

---

## Key behaviors this fixture exercises

- The strawman is **task-shaped** (mentions `closed_by`,
  `language`, the 73% plateau) — not generic.
- The designer reads first, asks second.
- The designer accepts the user's pinned model exactly without
  re-interrogating.
- Joint stratification (`closed_by` × class) is captured even
  though it's a refinement of the strawman.
- A stripped-scope path is *not* taken because no constraint
  argues for it — full Phase 1 + 1.5 + 2 + 3 is the default and
  the default is correct here.
