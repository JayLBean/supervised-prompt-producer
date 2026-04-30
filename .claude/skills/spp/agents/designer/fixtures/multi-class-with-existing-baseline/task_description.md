# Fixture 3 — multi-class with existing baseline

A user who has already labeled 200 rows across 4 classes from a prior
labeling effort. They want to use `spp` to produce the prompt; they
do not want to redo the labeling. The designer must recognize this
path and adjust accordingly:

- `BASELINE_STATUS = complete` on initial entry, not after a
  Phase 1 labeling pass.
- The loop runs against the existing labels; `baseline-quality`
  applies as an *audit* of the user's labels rather than as a
  fresh-labeling sub-skill.
- Multi-class metric (4 classes) — F1 is replaced by macro-F1
  or balanced accuracy.
- Larger split percentages possible because data is more abundant
  (200 rows is comfortable for 60/20/20).

This fixture validates the designer's bring-your-own-labels path
that the README revision called out explicitly. A designer that
forces the user back through Phase 1 labeling is broken.

---

## What the user types

```
/spp-init issue-categorization-v2
```

## What the user says when the designer presents the strawman

> Stop — I already have labels. There's a `data/labels.csv` with
> 200 rows that one of our SREs labeled last quarter. I want to
> use those.
>
> Categories are: Bug, Feature, Question, Other. Roughly 80 / 50 /
> 50 / 20 split. Production model is `claude-haiku-4-5-20251001`
> via the Anthropic API — locked.
>
> The metric should weigh all four classes equally; we don't have
> a strong asymmetry between them. Use macro-F1.

After follow-up:

> Approval phrases: "approved" everywhere; "ship" / "send back" at
> G6.
>
> Borderline cases I know about: Question vs Bug when the user is
> describing a behavior they don't understand. Sometimes that's a
> bug they haven't recognized yet, sometimes it's a knowledge gap.
> The labeler called these by gut; I'd like the prompt to do
> better than gut.
>
> Open question: I'm not sure my SRE's labels are perfectly
> consistent — they were done in batches over a few weeks, and the
> "Other" class might have drifted. Worth flagging during
> baseline-quality review.

---

## Repo context the designer discovers on its scan

### File tree (relevant subset)

```
.
├── README.md
├── pyproject.toml
├── data/
│   ├── issues_unlabeled.csv    (1,200 rows; columns: issue_id,
│   │                            title, body, repo, opened_at)
│   └── labels.csv              (200 rows; columns: issue_id,
│                                 label, labeler, labeled_at)
├── src/
│   └── triage/
└── tests/
```

### `README.md` excerpt

> # Issue Triage v2
>
> Replaces the regex-based issue triage with an LLM classifier.
> Four-class categorization for incoming GitHub issues across our
> open-source repos. Routes to the right team based on category.
> Anthropic API.

### `pyproject.toml` excerpt

```toml
[project]
name = "issue-triage"
dependencies = [
  "anthropic>=0.30",
  "pandas>=2.2",
]
```

### Recent git history (last 5 commits)

```
c1d2e3f  feat(triage): add v2 stub for LLM replacement
g4h5i6j  data: add labels.csv from SRE labeling sprint
k7l8m9n  fix(regex): tighten "Question" matcher (still wrong)
o0p1q2r  refactor: drop labelbox dep
s3t4u5v  docs: triage v1 retrospective — 67% accuracy
```

### No prior `spp/` artifacts

This is the user's first `spp` task in this repo.

---

## Notes for fixture review

The fixture exercises:

- The designer detecting `data/labels.csv` and *not* asking "do
  you have labels?" — labels are right there.
- Multi-class label space, 4 classes, no class-asymmetric cost.
- Multi-class metric selection (macro-F1 vs balanced accuracy);
  the metric-design sub-skill must surface the difference even
  in a stub state.
- `BASELINE_STATUS = complete` from the start.
- `baseline-quality` repurposed: rather than "review labels as
  they are produced," it becomes "audit pre-existing labels for
  drift across the labeling timeline."
- Split percentages: with 200 rows, a 60/20/20 split is
  comfortable (120/40/40). A smaller test split (e.g. 70/15/15
  → 30 test rows) is also valid; the designer should propose the
  default and accept the user's preference if different.
