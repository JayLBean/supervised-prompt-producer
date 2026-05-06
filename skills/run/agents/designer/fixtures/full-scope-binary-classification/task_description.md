# Fixture 1 — full-scope binary classification

A canonical happy-path task. The user types `/spp-init
support-billing-triage` from the root of a Python project that already
has unlabeled data, knows roughly what they want, and has chosen a
production model. Expected outcome: a full-scope plan (Phase 1 + 1.5
+ 2 + 3 with default budgets).

This fixture validates the on-spec methodology shape. If the designer
fails this fixture, every later fixture fails too.

---

## What the user types

```
/spp-init support-billing-triage
```

## What the user says when the designer presents the strawman

> Looks roughly right. Couple of corrections:
> - Use `gpt-4o-mini-2024-07-18` exactly, not `gpt-4o-mini`. Pinned
>   for prod.
> - 80 baseline rows is fine, but stratify on `closed_by` *and*
>   class — we've seen team-by-team variance.
> - For the metric: false-positives (routing a non-billing ticket to
>   billing) cost us ~2x what false-negatives do. Bias slightly
>   toward precision.
> - We don't have labels yet; we'll label this week.

After follow-up questions the user adds:

> - Borderline cases: tickets that mention "subscription cancelled"
>   without a charge dispute — those are *not* billing-team work,
>   they're customer success. Surprisingly common.
> - Approval phrases: "approved" everywhere except G6, which is
>   "ship it" or "send back."
> - Open questions: whether bilingual (English/Spanish) tickets
>   should be in the baseline or held out — we have a small
>   Spanish stream and aren't sure how the prompt will handle it.

---

## Repo context the designer discovers on its scan

(This is what the designer's §3 reading checklist would surface.)

### File tree (relevant subset)

```
.
├── README.md
├── pyproject.toml
├── data/
│   └── tickets.csv          (4,287 rows; columns: id, body,
│                             created_at, closed_by, language)
├── src/
│   └── triage/
└── tests/
```

### `README.md` excerpt

> # Triage Service
>
> Internal queue routing for the support inbox. Routes tickets to
> Billing, CS, and General queues based on a heuristic classifier
> (`src/triage/heuristic.py`). The heuristic has plateaued at ~73%
> accuracy on a recent eval; we're exploring an LLM replacement.

### `pyproject.toml` excerpt

```toml
[project]
name = "triage-service"
dependencies = [
  "openai>=1.50",
  "pandas>=2.2",
  "fastapi>=0.110",
]
```

### Recent git history (last 5 commits)

```
a1b2c3d  feat(routing): add language column for bilingual support
e4f5g6h  fix(heuristic): relax billing keywords for "subscription"
i7j8k9l  chore: bump openai to 1.50 for tool-use API
m0n1o2p  refactor(triage): factor common preprocessing
q3r4s5t  docs: note the 73% accuracy plateau
```

### No prior `spp/` artifacts

This is the user's first `spp` task in this repo.

---

## Notes for fixture review

This fixture's `consultation_notes.md` describes the consultation
shape the designer should produce given this input. The
`expected_plan.md` is the plan the designer should output after the
consultation completes and gate G1 is reached.

The fixture is exercised manually for Phase 2 step 2: read this
file, walk through `consultation_notes.md` against `designer.md`'s
behavior, confirm `expected_plan.md` is what `plan.md.template`
would produce. The Phase 4 validation harness will mechanize the
walk later.
