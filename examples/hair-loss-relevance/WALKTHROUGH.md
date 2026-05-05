# Session Walkthrough

This is a brief narrative reconstruction of the session in which this example
was produced, written by the user who ran the methodology. The chat session
was not captured verbatim. This document conveys the rhythm and structure of
the human-in-the-loop experience; for the methodology's outputs and behavior,
see the artifacts in this directory.

The session ran on `2026-05-04` against `gpt-oss-20b-MXFP4-Q8` on a local mlx
server. Total wall-clock was on the order of an afternoon, including the
plan-shaping back-and-forth, baseline-quality audit, four loop iterations,
and finalization.

## 1. Initiation

I had a 100-row hand-labeled CSV from a previous labeling sprint and a
binary classification task (does this social-media post belong in a
hair-loss research cohort?) that I wanted to convert into a production-grade
prompt. I described the task to Claude Code and pointed it at the labeled
data. This run pre-dated the `/spp` entry-point framing — I didn't type
`/spp <task>` to invoke the skill; I just described the task, and Claude
Code recognized it as the kind `spp` is built for and routed through
`SKILL.md` from there. Going forward, the canonical invocation pattern is
`/spp <task-name>` (one slash command); the router then walks the four
internal phases — `/spp-init`, `/spp-baseline`, `/spp-loop`,
`/spp-finalize` — as the methodology prescribes. From inside the
conversation, the experience is the same either way; the difference is
that future users have a clean entry point to type rather than having to
hope Claude Code recognizes the task description.

It surprised me how light the orchestration overhead felt. The skill is a
script for a conversation, not a wizard. The agent's behavior was
human-paced: ask, listen, propose, wait for me to redirect.

## 2. Phase 1 — consultation (`/spp-init`)

The designer agent asked me to describe the cohort in one sentence, then
asked about audience, problem statement, and what currently went wrong
without the filter. It pulled out the existing labels' criterion taxonomy
and re-derived class definitions inline; I said "yes that's what those
codes mean" more than I generated definitions. The strawman it proposed
was almost right — it had the headline criterion at F1 ≥ 0.85 and I bumped
it to 0.90 because a noisier downstream cohort costs us specifically; that
became the v2 plan revision.

The two parts that took back-and-forth were the sacred-test-set
acknowledgment and the loop scope. I had been planning to keep iterating
against the dev partition until the metric was stable; the agent walked me
through why test-after-finalization-only is the methodology's load-bearing
guarantee against optimism in the headline number, and I settled into the
posture. The G1 approval was easier than I'd expected — the plan as a
whole was coherent enough that I could commit by reading it once.

## 3. Phase 2 — baseline and splits (`/spp-baseline`)

Because I had labels in hand, the baseline-quality sub-skill ran the
existing-baseline path with extra scrutiny rather than the fresh-labeling
path. The audit checked label-vs-criterion-code consistency across all 100
rows (zero mismatches), sampled 10 rows per class for class-definition
drift (every rationale cited a specific C-code), and noted that I had not
done a blind self-disagreement re-label session — this last point became
plan §10 open question 5.

What surprised me was the specificity of the audit. I'd been worried it
would feel like a pro-forma rubber-stamping; it wasn't. The audit asked me
to articulate why I'd accepted my own judgment as ground truth and pointed
at the criterion-code-and-rationale audit trail as the substituting
evidence. That framing — "you didn't blind re-label, so the audit trail in
the rationale column has to do that work" — felt right and is now part of
plan §6's `BASELINE_QUALITY_NOTE`.

I approved at G2 with the verdict `ready`. The stratified split came out
60/52% pos / 20/55% pos / 20/50% pos; G3 approved by inspection.

## 4. Phase 3 — optimization (`/spp-loop`)

This is the most important section.

**Pre-G4 plumbing.** The dry-run on three train rows surfaced a gpt-oss
quirk: the model returns its reasoning trace as `reasoning_content` and
the visible JSON as `content`, both counted against `max_tokens`. I'd
budgeted 200 tokens; reasoning ate it. We bumped to 1500 (plan v4) and the
dry-run passed; G4 approved.

**Iteration 1.** Five dev rows disagreed (3 FN, 2 FP). The discrepancy
agent surfaced four clusters: thin-but-earnest first-person product reviews
mistaken for promotion (cluster A), peer/community engagement without
first-person framing (B), body-hair / depilatory content (C), and
third-person clinician case write-ups (D). All four edits came back
`categorical` from the auditor. Dev F1: 0.76 → 0.91 going into iter 2.

**Iteration 2.** Two disagreements (1 FP, 1 unparsed). Cluster E was a
one-liner exclamation reading favorably about bald life; cluster F was a
rerun of the reasoning-trace token budget — bumped 1500 → 3000 (plan v5).
The substantiveness floor edit came back `categorical`. Dev F1 stayed at
0.91, train F1 dropped 0.84 → 0.72 — a yellow flag.

This was the moment that taught me what the auditor is for. The auditor
hadn't seen scores; it judged the substantiveness floor edit categorical
on its surface form, which it was. The over-broad scoping that crashed
train F1 was caught later, by iter-3's discrepancy agent looking at the
actual disagreements. That's the methodology working as designed: edit
quality is judged at edit time on its categorical form; edit *soundness*
is verified at the next iteration's discrepancy. The auditor isn't a
score-watcher and shouldn't be one.

**Iteration 3.** Two disagreements again (1 FN, 1 FP). Cluster G was the
substantiveness floor walkback — short-but-substantive posts shouldn't be
excluded just for being short. Cluster H was a body-hair rule that had
gotten shadowed by the substantiveness rewrite; the fix was structural —
promote the body-hair check to a topic-scope-first gate that fires before
rules 1–3 evaluate. Both edits came back `categorical`. Dev F1: 0.91.
Train F1 recovered to 0.75. The narrowing worked.

**Iteration 4.** One disagreement: a row about peer treatment advice that
mentioned beard styling, and the topic-scope gate read "beard" as
out-of-scope. Dev F1: 0.95.

This is where I stopped. I sat with the artifact for a while. The headline
criterion (F1 ≥ 0.90) was met. The dev plateau under the original
threshold (`<0.005 for 3 consecutive`) was not satisfied; under the
revised threshold (`<0.05 for 2 consecutive`, plan v6, justifiable at
N_dev=20 because one row swings F1 by ~0.05), it was.

But the relevant question wasn't really which threshold won. The
remaining failure was **one** dev row, and the only categorical edit
candidate was a "primary-topic anchor" exception to the topic-scope gate
— the kind of exception that exists to handle one specific row. I thought
about it for a few minutes and chose to stop. The methodology's discipline
is: don't iterate when the only available edit is row-specific patching
dressed as a categorical refinement. I'd rather ship a prompt with one
known dev failure than a prompt that fits the dev partition.

I told Claude Code to stop. It wrote `EARLY_STOP.md` (user-requested
manual stop). Later, recognizing the v6-threshold plateau condition was
also satisfied, it also wrote `SUCCESS.md`. Both files are shipped; the
operative termination is `EARLY_STOP` because that matches the in-the-
moment reasoning. (See [`README.md`](README.md) Findings §1 — this
collision is on the Phase 4 polish list.)

## 5. Phase 4 — finalization (`/spp-finalize`)

G5 is the moment you see the test number for the first time. I'd been
imagining 0.85–0.90 going in. It came back **0.75** — F1 on the positive
class, 1.00 precision, 0.60 recall.

The dev/test gap (0.95 → 0.75) is exactly what the loop is supposed to
flag and didn't, because at N_dev=20 a small partition can land on a
sub-population that's biased relative to train (dev ran 0.20 *higher* than
train across iters 2–4). I was reading dev as a confidence signal and it
was a noise signal.

The test failure pattern was clean: zero false positives, four false
negatives. Three categorical clusters (asker-side info-seeking community
queries, mixed-signal personal+future+community posts, topic-scope
boundary cases) the loop didn't have the data to surface. These are now in
REPORT §4.

G6: I accepted the runner's `iterate-further` recommendation. The path
forward is bigger baseline (200–300 rows), targeted seeding for the §4
clusters, fresh test partition, re-run from `/spp-loop`. The frozen
prompt is shipped as `PROMPT_FROZEN_v01.md` for reproducibility, with the
test scores as the honest baseline.

## 6. Reflection

What surprised me: the auditor's discipline. I went in expecting a quality
gate that would feel pedantic. It is more useful than that — its role is
specifically to keep edits on the categorical surface, not to second-guess
metric movement. I would not have arrived at "iter 2's substantiveness
floor was over-broadly scoped, recover at iter 3" without the auditor's
framing in my head.

What felt right: the EARLY_STOP at iter 4. The methodology gives you
permission to stop when you can see that further iteration would be
fishing for one row, and the early-stop carries a pedagogically clear
artifact.

What was onerous: the back-and-forth on plan §3 vs §11 over the plateau
threshold. The original `<0.005 for 3 consecutive` was below the dev noise
floor at N=20; we revised it during the loop. In hindsight I should have
pushed back at `/spp-init` time — the plateau-threshold default in the
designer agent didn't account for small-N dev partitions, and I shipped
the default rather than thinking about it.

What I'd do differently: expand the baseline before running the loop.
N=100 was set by the labeled data I had on hand; it was small enough that
dev-partition noise dominated the signal that was supposed to drive
iteration decisions. The REPORT's `iterate-further` recommendation is
honest, but a 200–300-row baseline would have made the loop stop conditions
informative rather than threshold-tuning artifacts.
