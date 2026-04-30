# Fixture 2 — stripped-scope, small baseline

A user with a high-stakes labeling task who can only afford 30
baseline rows. Labels are expensive (a domain expert's time at hours
per row, not minutes). The user wants the methodology's discipline but
must adapt to a constrained budget.

This fixture validates `DESIGN.md` core principle 2: shape spp to the
task, not the task to spp. A designer that pushes the user to 80 rows
because "the methodology says 50–100" is broken. A designer that
silently agrees to 30 rows without acknowledging the statistical
implications is also broken. The right response is a stripped-scope
plan that documents what is being skipped and why.

---

## What the user types

```
/spp-init clinical-note-deidentification-flag
```

## What the user says when the designer presents the strawman

> The strawman is wrong about the baseline size. We can label 30
> rows total — each row takes a clinician 20-40 minutes of careful
> review, and we have ~15 hours of clinician time budgeted total.
> 80 rows is impossible.
>
> Yes, this is high-stakes — these are clinical notes and the
> classification flags whether the note has correctly removed PHI.
> A false-negative (saying PHI is removed when it isn't) is a
> regulatory issue. A false-positive (saying PHI remains when it
> doesn't) is just a re-review.
>
> No, we don't want to skip the methodology entirely — the loop
> discipline is what we want — but the test split has to give us
> something. With 30 rows total, a 60/20/20 split gives us 6 test
> rows. That's not enough.

After follow-up:

> Model: I have to use a HIPAA-compliant deployment, so it's
> Azure-hosted GPT-4o (specifically `azure-gpt-4o-2024-11-20`).
> No swaps possible — that's the only HIPAA-eligible model in our
> infrastructure right now.
>
> No prior labels. The clinician will label all 30.
>
> Approval phrases: "approved" everywhere. I want low ceremony at
> the gates.
>
> What I'd actually like: skip Phase 3 (final test). Use a pilot
> deployment as the validation — we deploy the prompt against a
> shadow run on production traffic with clinician spot-check, and
> if the precision/recall reads acceptable over a week, we
> graduate it. The 6-row test split is too noisy to be honest
> about.
>
> Open question: whether 30 rows is even enough for the loop to
> not just chase the labels. I don't know the answer; it might
> not be.

---

## Repo context the designer discovers on its scan

### File tree (relevant subset)

```
.
├── README.md
├── pyproject.toml
├── data/
│   ├── notes_unlabeled.jsonl   (412 rows; columns: note_id,
│   │                            redacted_text, source_system)
│   └── annotation_protocol.md  (4 KB — clinician's labeling
│                                 protocol document)
├── docs/
│   └── compliance.md
└── tests/
```

### `README.md` excerpt

> # Clinical Note De-Identification Validator
>
> Validates that PHI removal pipelines have correctly redacted
> patient health information from free-text clinical notes. This
> repo holds an LLM-based second-pass classifier that flags
> redacted-but-still-leaky notes for re-review. HIPAA covered;
> deployment is Azure-only.

### `pyproject.toml` excerpt

```toml
[project]
name = "deid-validator"
dependencies = [
  "openai>=1.50",
  "pandas>=2.2",
]
```

### Recent git history (last 5 commits)

```
b1c2d3e  docs(compliance): note Azure-only deployment constraint
f4g5h6i  feat: add annotation_protocol.md for clinician labeling
j7k8l9m  refactor: drop sklearn dep; not used yet
n0o1p2q  fix(redactor): handle nested PHI in document footer
r3s4t5u  chore: initial scaffold
```

### No prior `spp/` artifacts

This is the user's first `spp` task in this repo.

---

## Notes for fixture review

The fixture exercises:

- The designer's adaptation when a default baseline target (50–100)
  is impossible.
- Stripped-scope plan generation (`SPP_SCOPE` ≠ `full`) with an
  honest `plan.md` §8 comment about what's skipped.
- The Phase 3 → pilot-deployment substitution as a stripped-scope
  variant the designer can produce.
- Awareness that small-baseline plans must call out the statistical
  risk in `plan.md` §6 and §10.

The fixture exercises the *adaptation*. A designer that produces
the same plan shape as fixture 1 has not adapted.
