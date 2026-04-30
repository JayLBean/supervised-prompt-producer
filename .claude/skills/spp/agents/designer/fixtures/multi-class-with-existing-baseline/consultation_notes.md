# Fixture 3 — consultation shape

The defining property: the user **already has labels**. The designer
must detect this from the §3 reading checklist and not ask "do you
have labels?" — `data/labels.csv` is right there.

A designer that asks "do you have labels?" when the file is visible
is asking a question the scan already answered. That's the failure
mode this fixture protects against.

---

## What the designer should do before its first message

Run the §3 reading checklist:

- See `data/issues_unlabeled.csv` (1,200 rows) and
  `data/labels.csv` (200 rows). Two files; the second is clearly
  a labeling output.
- Read `data/labels.csv` headers: `issue_id, label, labeler,
  labeled_at`. The `labeler` and `labeled_at` columns suggest a
  multi-week or multi-batch labeling effort (informative — flags a
  consistency-drift concern for `baseline-quality`).
- Read `README.md`: 4-class categorization (Bug, Feature, Question,
  Other), Anthropic API.
- Note recent commit `g4h5i6j data: add labels.csv from SRE
  labeling sprint` — confirms the labels are recent and from a
  single labeler ("SRE"). Confirms `labeler` will be a single
  value or a small set.
- Note `s3t4u5v docs: triage v1 retrospective — 67% accuracy` —
  the user's motivation: replace a 67%-accurate regex.
- See `anthropic>=0.30` dep — Anthropic-compatible client is
  available; the model is likely Anthropic-hosted.

## The strawman the designer presents first

The strawman should reflect that labels exist:

- **Task:** 4-class categorization of GitHub issues (Bug,
  Feature, Question, Other) — drawn from the README's 4-class
  description and `data/labels.csv`'s label column.
- **Production model:** `claude-haiku-4-5-20251001` via
  Anthropic API (since `anthropic>=0.30` is a dep). (Or pin a
  different version?)
- **Baseline:** the existing 200 labeled rows in
  `data/labels.csv` — so `BASELINE_STATUS = complete` from
  initial entry. The Phase 1 labeling step is replaced by a
  `baseline-quality` audit pass over the existing labels,
  particularly checking for drift across `labeled_at` (the
  labeler's `data: add labels.csv from SRE labeling sprint`
  commit suggests a multi-batch effort).
- **Metric:** macro-F1 (default for multi-class with no stated
  asymmetry). Balanced accuracy is the alternative; the
  metric-design sub-skill helps choose.
- **Splits:** 60/20/20 on 200 rows = 120 train / 40 dev / 40
  test. (Or different ratios?)
- **Scope:** full Phase 1 + 1.5 + 2 + 3, with Phase 1
  re-purposed as audit-of-existing-labels rather than
  fresh-labeling.

The fifth bullet — re-interpreting Phase 1 — is the designer
showing it has read the kickoff context and adapted.

## Where the user's reply diverges from the strawman

- Confirms the strawman's interpretation: `data/labels.csv` is the
  baseline, do not redo labeling.
- Pins the model exactly (`claude-haiku-4-5-20251001`) — which
  matches the strawman.
- Confirms macro-F1 and equal-cost-across-classes.
- Volunteers the Question-vs-Bug borderline case.
- Volunteers the open question about "Other" class drift across
  the labeling timeline.

## The designer's adaptation

Compared to fixture 1 (no labels) and fixture 2 (constrained
budget), the differences here are:

1. `BASELINE_STATUS = complete` on initial entry. The user's
   `/spp-baseline` invocation will run `baseline-quality` over
   the existing labels rather than producing new ones. The
   designer captures this in `plan.md` §6's status field and
   §6's `LABEL_PROVENANCE` field (single SRE labeler, multi-week
   batches, drift concern flagged).

2. Multi-class metric. F1 is wrong here; the user has 4 balanced
   classes with no cost asymmetry, so macro-F1 (or balanced
   accuracy) is right. The metric-design sub-skill is invoked
   to help the user understand the trade-off (macro-F1 weights
   all classes equally regardless of frequency; balanced
   accuracy weights per-class recall equally). The user picks
   macro-F1.

3. Larger splits. With 200 rows, 60/20/20 is honest (40 test
   rows is a meaningful signal). The designer does not need to
   propose a stripped scope.

4. Stratification key: the 4-class label, with the prevalence
   imbalance (~40/25/25/10) preserved.

5. Open question recorded: the "Other" class drift concern
   becomes `plan.md` §10 entry, and the designer specifically
   asks `baseline-quality` to focus its audit on
   `Other`-labeled rows across `labeled_at` batches.

## What the designer does NOT do

- Does not ask "do you have labels?"
- Does not ask "what's your data source?" — `data/labels.csv` is
  the source.
- Does not propose a stripped scope — the data supports full
  Phase 1 + 1.5 + 2 + 3.
- Does not offer to redo labeling — the user already has labels;
  redoing them would discard the user's work.
- Does not pretend the labels are perfect — surfaces the drift
  concern as an open question.

## Validation gate behavior

12 mechanical rules, all passing on first attempt:

- Rule 7 `SACRED_TEST_ACK = acknowledged` — passes.
- Rule 8 `AUDITOR_CONFIG = per-iteration, no-score-access` —
  passes.
- Rule 9 ratios 60 + 20 + 20 = 100 — passes.
- Rule 10 `SPP_SCOPE = full` — passes.

Manual review:

- Borderline case (Question vs Bug) is concrete enough for
  Phase 2 rule articulation.
- §10 open question (Other drift) is non-empty.
- §6 explicitly says "labels exist; baseline-quality audits
  rather than collects."

---

## Key behaviors this fixture exercises

- **Pre-existing-labels recognition.** The designer reads
  `data/labels.csv` and treats it as the baseline.
- **Multi-class metric selection.** The designer picks
  macro-F1 for 4 balanced classes with equal cost.
- **`baseline-quality` repurposed as audit.** Phase 1 in this
  plan is "audit existing labels for drift," not "label fresh
  rows."
- **Pre-existing labels are not infallible.** The designer
  surfaces the `Other`-drift concern in §10 rather than
  treating the labels as ground truth without scrutiny.

A designer that fails this fixture either (a) asks "do you have
labels?" with `data/labels.csv` visible, (b) offers to redo
labeling, (c) defaults to F1 instead of macro-F1 for
multi-class, or (d) treats the existing labels as correct
without surfacing the consistency concern.
