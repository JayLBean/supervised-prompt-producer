# baseline-quality

The **primary defense against baseline overfitting** — the
deal-breaker failure mode in `DESIGN.md` §2.1. An adversarial
review of the labeled baseline that surfaces the kinds of
inconsistencies which, left in place, become the rows the
optimization loop quietly memorizes and a Phase 2 prompt
silently learns to game.

This is not a generic label-quality checklist. The sub-skill
has the methodology authority to return a `not-ready` verdict
that halts `/spp-baseline` before splits are generated, even
when the user wants to proceed. A sub-skill that recommends but
does not block is back to being a checklist; this one blocks.
The verdict-enforced-gate pattern set here is what the auditor
agent (Phase 2 step 6) will inherit.

`baseline-quality` is the second sub-skill in `spp` and follows
the six-section structure pinned by `metric-design`'s pattern-
lock paragraph. It is read by `/spp-baseline` (when labeling
happens inside `spp`) and is also invoked when labels are
brought in from outside (the bring-your-own-labels path tested
by the multi-class-with-existing-baseline fixture).

---

## 1. Identity and scope

`baseline-quality` performs an adversarial review of the
labeled baseline before splits are generated, and returns a
verdict that gates whether `/spp-baseline` is allowed to
advance to G3.

In v0.2 the §3 review questions run **per OUTPUT_SCHEMA
field** (`DESIGN.md` §7.1.1 compat layer). Verdict tokens
(`ready` / `revise` / `not-ready`) are unchanged; the output
is per-field findings consolidated into a single verdict on
the baseline as a whole (see "Verdict consolidation" in §3.7
below). The single-verdict consolidation preserves G2's
enforcement pattern unchanged — one verdict per baseline
gates G2, not K verdicts. K=1 backward compat: with one
OUTPUT_SCHEMA field the per-field protocol runs once and the
findings + verdict shape collapses to v0.1.0's. Legacy
v0.1.0 plans persisting `LABEL_SPACE` continue to work via
the runner's K=1 fallback (`/spp-baseline` §4 step 7).

**The framing:** in the source-project work that produced this
methodology, baseline overfitting was the deal-breaker
(`DESIGN.md` §2.1). Two things contributed: an implicit
auditor (no audit trail for which rule edits got pushed back
vs. accepted — fixed by the auditor agent in Phase 2 step 6),
and label-quality issues that the loop quietly absorbed as if
they were ground truth. `baseline-quality` is the upstream
defense for the second issue. If it does its job, the
optimization loop is operating on a baseline whose
inconsistencies have been surfaced; if it doesn't, every
later phase is a high-effort exercise in optimizing toward
noise.

**In scope:**

- Class-definition drift (the user's articulated reasoning
  for a row's label diverges from the written class
  definition).
- Intuition-vs-rule divergence (borderline rows labeled "by
  feel" rather than by the written rule).
- Class-balance reality check against production prevalence.
- Inter-rater calibration (multi-labeler) or self-disagreement
  spot-check (solo labeler).
- Existing-baseline provenance check (labels brought in from
  outside `spp`).

**Out of scope:**

- Generating new labels. The sub-skill reviews existing
  labels; labeling itself is `/spp-baseline`'s job (or, in
  the bring-your-own-labels path, the user's prior work).
- Statistical-power analysis of the baseline size. Baseline
  size is set in `plan.md` §6 by the user during the
  designer consultation; reviewing whether the chosen size
  is "enough" is the designer's job at consultation time,
  not this sub-skill's job after the fact.
- Touching the test set. Splits do not exist yet at the
  time `baseline-quality` runs (`/spp-baseline` runs the
  review *before* generating `splits.json`, so the sacred-
  test-set guarantee per `DESIGN.md` §10 is not at risk
  here).
- Multi-judge subjective metrics. v1 non-goal per
  `DESIGN.md` §7.1; if the metric in `plan.md` §4 violates
  the independence rule, that's caught upstream by
  `metric-design`, not here.

The cross-skill rule that governs this sub-skill is the
**plan.md-as-contract** rule (`DESIGN.md` §10): findings
flow back into `plan.md`, not into a separate document.
The full elaboration is in §5 below.

---

## 2. The decision the sub-skill helps make

**Is this baseline ready for Phase 2 to start, or does it
need work before splits are generated?**

The output of consulting `baseline-quality` is three things,
all of which feed into `/spp-baseline`'s gate G2 enforcement:

- **A verdict**, one of:
  - `ready` — splits can be generated; G2 advances on the
    user's approval phrase.
  - `revise` — specific issues exist that should be fixed
    before splits, but the user can choose to proceed with
    a documented justification in `plan.md` §11.
  - `not-ready` — substantive issues exist that, left in
    place, are likely to make the methodology's claim
    against baseline overfitting hollow. G2 does **not**
    advance on the user's approval phrase alone; the user
    must either resolve the issues (and re-invoke) or
    record an explicit override entry in `plan.md` §11
    that propagates into `REPORT.md` §7.2 limitations.
- **A `BASELINE_QUALITY_NOTE`** paragraph for `plan.md` §6
  (the "baseline-quality review" subsection): names what
  was reviewed, what was found, and what was resolved. The
  paragraph is required regardless of verdict — even a
  `ready` baseline gets a note saying "review performed, no
  issues surfaced."
- **A list of specific rows or class-definition issues**
  (only when the verdict is `revise` or `not-ready`):
  named row identifiers and the specific concern for each,
  so the user can act without re-deriving the findings.

The verdict has gate-enforcement teeth via `/spp-baseline`'s
§5 gate-G2 logic. Future contributors must not weaken this
authority — see §"Versioning" below; weakening is a
`BREAKING CHANGE:`.

---

## 3. The decision tree (the adversarial review protocol)

Walk the protocol in order. Each question surfaces a specific
failure mode and contributes to the verdict. Stop and surface
findings as soon as a `not-ready` condition is reached; do not
sandbag the user with a list-at-the-end summary when the
labeling needs structural work.

**Per-field application (v0.2).** Each check below runs **per
OUTPUT_SCHEMA field**. For a K-field schema, the reviewer walks
§3.1 once per field, §3.3 once per field, and so on; findings
are recorded per field. The thresholds (e.g., the 25% drift
threshold in §3.1) apply within each field's sample
independently — a field whose drift sample crosses the threshold
contributes a `not-ready` signal regardless of whether other
fields are clean. K=1 (single-output classification) is the
degenerate case: each check runs once on the lone field and
produces v0.1.0-equivalent output. Cross-field calibration —
checking whether the same row is consistently labeled across
fields — is part of §3.5's calibration check rather than a
separate stage; the unit of review remains the field.

### 3.1 Class-definition drift (canonical baseline-overfitting precursor)

Sample 5–10 labeled rows per class. For each sampled row, ask
the user to articulate, **without re-reading the class
definition in `plan.md` §2**, what makes the row's label
correct. The articulation should be a sentence or two of
plain-English reasoning.

Compare each articulation to the written class definition.

- **Articulations match the written definition** for all
  sampled rows → no drift signal. Proceed to §3.2.
- **Articulations diverge from the written definition** for
  one or two rows → a `revise` signal. Either refine the
  class definition in `plan.md` §2 to capture the
  articulated reasoning, or relabel the divergent rows to
  match the existing rule. The sub-skill does not
  unilaterally pick — the user decides which side to update.
- **Articulations diverge for more than ~25% of sampled
  rows** → a `not-ready` signal. The labeling and the class
  definition were operating on different rules; treating
  the labels as ground truth without resolving this is a
  classic baseline-overfitting setup. Halt the protocol and
  surface; the user must reconcile before the rest of the
  protocol is even meaningful.

This check is canonical — the gap between articulated
reasoning and written rule is exactly the gap that the loop
will optimize a prompt to span, producing rules that fit
specific labels rather than generalizing the underlying
class.

### 3.2 Borderline-case visibility

Ask the user to flag rows where labeling took noticeably
longer than typical, or where they considered changing the
label, or where they still feel uncertain. These are the
**rows where row-specific phrasing is most likely to leak
into the prompt** — the auditor in Phase 2 step 6 will be
watching for it, but cleaner inputs make its job possible.

- **No borderlines flagged** in a baseline of 50+ rows →
  suspicious, not necessarily blocking. The sub-skill
  presses once: "are you sure no rows felt close to the
  boundary?" Often a second look surfaces 2–5 rows.
- **A handful of borderlines flagged** (typically 5–15% of
  the baseline) → expected and healthy. Proceed to §3.3 to
  examine each.
- **Many borderlines flagged** (>30% of the baseline) →
  the class definition is genuinely ambiguous; mark for
  `revise` and recommend either a class definition refinement
  or an explicit `Uncertain` / `Other` class.

### 3.3 Intuition-vs-rule divergence (per borderline row)

For each flagged borderline row, ask: was the final label
applied because of the **written rule** or because of the
labeler's **intuition** about the row's intent?

- **Rule-based labeling** (the user can articulate which
  clause of the class definition decided the label) → no
  signal. Move to next borderline row.
- **Intuition-based labeling** (the label is "what felt
  right" but not derivable from the written rule) → a
  rule-articulation gap. Flag the row and contribute to a
  `revise` verdict. Two paths to close the gap:
  1. Refine the class definition in `plan.md` §2 to
     articulate the intuition as a rule.
  2. Relabel the row to match the existing rule, even if
     the user disagrees with the result.
- **>25% of borderline rows are intuition-based** → a
  `not-ready` signal. The class definition is acting as a
  decoration over the labeler's intuition rather than as
  the actual rule, and the loop will fit prompts to the
  intuition without ever surfacing it.

### 3.4 Class-balance reality check

Compute the labeled distribution and compare to the
production prevalence the user named in `plan.md` §6
(`CLASS_BALANCE_TARGET`).

- **Labeled distribution within ~10 percentage points of
  production** → no signal. Proceed to §3.5.
- **Labeled distribution drifts >10 percentage points but
  the drift is intentional** (the user oversampled the
  positive class for label efficiency, e.g., the clinical
  PHI fixture) → no signal as long as the drift is
  documented in `plan.md` §6's class-balance rationale and
  is consistent with the metric chosen in §4.
- **Labeled distribution drifts >10 percentage points and
  the drift is unintentional** → a `revise` signal. The
  loop will optimize against the labeled distribution, not
  the production distribution; without correction the
  prompt's behavior at deploy time will be calibrated to
  the wrong base rate. Recommend resampling.
- **Distribution drift is severe (>30 percentage points,
  unintentional)** → `not-ready`. The baseline is not
  representative of production; resampling or a documented
  acceptance with explicit limitations is required before
  proceeding.

### 3.5 Inter-rater calibration (multi-labeler) or self-disagreement (solo)

The check depends on the labeling provenance from `plan.md`
§6.

**Multi-labeler:** sample 10–15 rows for double-labeling.
Ideally the second labeler does not see the first labeler's
output. Surface any disagreement.

- **Disagreement on 0–5% of the sample** → no signal.
  Proceed to §3.6.
- **Disagreement on 5–15%** → a `revise` signal. Walk the
  user through each disagreed row and reach consensus; the
  consensus rationale goes into `plan.md` §11 if it
  motivated a class-definition refinement.
- **Disagreement on >15%** → `not-ready`. The labelers were
  applying different rules; either calibrate (and re-label
  the affected sample) or accept the noise explicitly via
  `plan.md` §11 override.

**Solo labeler:** ask the user to re-label a small sample
(10–15 rows) blind — without seeing the original labels —
and compare.

- **Self-disagreement on <10%** → no signal.
- **Self-disagreement on 10–25%** → a `revise` signal.
  Examine the disagreed rows and either reconcile them or
  document them as known noise.
- **Self-disagreement on >25%** → `not-ready`. The labeler
  is not internally calibrated, and treating their labels
  as ground truth makes the methodology's claim hollow.
  Either re-label after refining the class definition, or
  proceed with an explicit `not-ready` override in
  `plan.md` §11.

The 25% threshold is a **heuristic** on a small-sample
(10–15 row) re-labeling exercise; the binomial noise at
that sample size is non-trivial. Users near the threshold
(self-disagreement of ~20–30% on the small sample) should
re-label a larger sample (25–30 rows) before treating the
result as definitive. The sub-skill will surface this
expansion path when the small-sample result is in the
borderline range; the user's choice to expand or accept
the small-sample verdict is recorded in
`BASELINE_QUALITY_NOTE`.

### 3.6 Existing-baseline provenance check (skip if labels were generated inside `/spp-baseline`)

If labels were brought in from outside `spp` —
`BASELINE_STATUS = complete` on entry to `/spp-baseline`,
the bring-your-own-labels path — run this check. Otherwise
skip.

- **Labeling protocol is documented** (an
  `annotation_protocol.md` or equivalent exists in the
  repo, the labeler is reachable, and the protocol matches
  the class definition in `plan.md` §2) → no signal.
  Proceed to §3.7.
- **Labeling protocol is implicit** (no document, single
  labeler whose intent is recoverable but undocumented) →
  a `revise` signal. The user articulates the protocol
  retroactively; the articulation goes into `plan.md` §6
  as the `LABEL_PROVENANCE` field's content.
- **Labeling protocol is unrecoverable** (labels exist but
  the original labeler is unavailable or the criteria they
  used cannot be reconstructed) → `not-ready`. Either
  re-label, or accept explicitly via `plan.md` §11
  override and propagate the limitation into `REPORT.md`
  §7.2 at finalization time.
- **Class definition in `plan.md` §2 was written after the
  labels** → run §3.1 (drift check) with extra scrutiny.
  Post-hoc class definitions are particularly likely to
  diverge from the original labeling; if they diverge,
  the post-hoc definition is the one that needs to be
  refined to match the labels (or the labels need to be
  refined to match the definition — the user picks).

**Note on re-labeling scope.** When this section says
"re-label" (in any of the bullets above), the scope is
the **affected rows** — those surfaced by a focused §3.1
drift check on a sample, plus any neighbors that the user
identifies during reconciliation. **Re-labeling the entire
baseline from scratch is appropriate only if the §3.1
drift check shows pervasive drift** (e.g., articulations
diverge from the written definition for >50% of sampled
rows, or for every class). Targeted re-labeling is the
default; full re-labeling is the escalation. The
distinction matters because full re-labeling can be days
of work, while targeted re-labeling is usually hours.

### 3.7 Verdict synthesis

Aggregate signals from §§3.1–3.6 into a single verdict. Under
v0.2 the synthesis runs in two stages — within-field synthesis
first, then cross-field consolidation — and produces one
verdict on the baseline as a whole.

**Within-field synthesis** (run once per OUTPUT_SCHEMA field):

| Signal pattern within a field | Field verdict |
|---|---|
| All checks pass on the field | `ready` |
| At least one `revise` signal on the field, no `not-ready` | `revise` |
| Any `not-ready` signal on the field | `not-ready` |

**Cross-field consolidation** (the verdict on the baseline as a
whole; per `DESIGN.md` §7.1.1 compat layer's
"any-not-ready dominates, any-revise dominates ready" rule):

| Pattern across the K field verdicts | Baseline verdict |
|---|---|
| Every field is `ready` | `ready` |
| At least one field is `revise`; none is `not-ready` | `revise` |
| Any field is `not-ready` | `not-ready` |

The consolidation keeps G2's enforcement pattern unchanged: one
verdict per baseline gates G2, not K verdicts. The findings
document records per-field findings (which field surfaced
what); the verdict is one token. Under K=1 the within-field
synthesis runs once and the consolidation is the identity —
the field verdict is the baseline verdict, equivalent to
v0.1.0's single-stage synthesis.

The verdict and its evidence flow into the `BASELINE_QUALITY_NOTE`
output (§6 below) and into `/spp-baseline`'s G2 enforcement.

---

## 4. Worked examples

Five generic scenarios. None references a real source-project
task (`DESIGN.md` §7.2). Each shows the protocol walk, the
verdict, and the outputs.

### Example 1: clean baseline → `ready`

**Setup.** Binary classification (Billing vs Not), 80 rows
labeled by a single team member with documented criteria,
class balance ~20% positive matching production, no prior
issues flagged in consultation.

**Protocol walk.**
- §3.1 (drift): sample 8 rows, all articulations match the
  written definition. ✓
- §3.2 (borderlines): user flags 6 rows (~7%) — expected
  range. ✓
- §3.3 (intuition): all 6 borderlines were rule-based; user
  cites which class-definition clause decided each. ✓
- §3.4 (balance): 22% positive in baseline, 20% in
  production, drift 2pp. ✓
- §3.5 (calibration, solo): re-label 12 rows blind,
  self-agreement 12/12. ✓
- §3.6 (provenance): not applicable — labels were
  generated inside `/spp-baseline`.

**Verdict:** `ready`.

**`BASELINE_QUALITY_NOTE`:** "Reviewed 80 labels for
class-definition drift, borderline-case visibility,
intuition-vs-rule divergence, and class-balance match to
production. Spot-checked 8 rows per class for drift (none
found), 6 borderline rows for rule-vs-intuition (all
rule-based), and 12 rows for solo-labeler self-agreement
(12/12). Baseline is consistent with the class definition
in §2 and the production distribution stated in §6.
Verdict: ready."

**Outputs:** verdict `ready`, `BASELINE_QUALITY_NOTE` above,
no row list (none needed for `ready`). `/spp-baseline`
proceeds to G2.

### Example 2: class-definition drift → `revise`

**Setup.** Binary classification (Spam vs Not), 100 rows
labeled, user flagged ~10 rows during labeling as "edge
cases."

**Protocol walk.**
- §3.1 (drift): sample 10 rows, ask the user to articulate
  why each is its label. For 3 of them, the articulation
  mentions "the message is from a known low-quality
  domain" — the written class definition does not mention
  domain reputation. The labeler used domain reputation as
  an unstated rule.

**Verdict (early-exit at §3.1):** `revise` (not yet
`not-ready` — 3 of 10, ~30% but the threshold is firm at
25% — actually this is borderline; the sub-skill should
report it as `revise` with strong language and let the
user decide whether the threshold has been crossed, by
sampling more rows if needed).

**Findings list:**
- Row IDs 0017, 0042, 0089: labeled `Spam` based on domain
  reputation, which is not in the §2 class definition.
- Recommendation: either add a domain-reputation clause to
  §2 (and update §11 with the refinement), or relabel
  these three rows to match the existing rule (which would
  make them `Not Spam` if the message body alone does not
  meet the existing criteria).

**`BASELINE_QUALITY_NOTE`:** "Reviewed 100 labels for
class-definition drift. Found 3 rows (0017, 0042, 0089)
where the labeler applied an unstated domain-reputation
rule. Class definition in §2 has been refined per §11
revision log entry to include domain reputation as an
explicit signal; affected rows re-validated against the
refined definition. Verdict at re-invocation: ready."

**Outputs:** verdict `revise`. `/spp-baseline` surfaces the
findings, user updates §2 (or relabels), re-invokes
`baseline-quality`, gets `ready` on re-run, advances to G2.

### Example 3: intuition-driven labels → `revise`

**Setup.** Multi-class (Bug / Feature / Question / Other),
200 rows from a prior labeling sprint. User flags 40
borderlines (20% — high but within range) during §3.2.

**Protocol walk through §3.3.** For each of the 40
borderlines, ask: rule-based or intuition-based? User
answers honestly: 28 are rule-based (cites the §2 clause),
12 are intuition-based ("I just felt like this was a
Question, not a Bug").

12 of 40 = 30%; 12 of the 200-row baseline = 6%. The
sub-skill applies the threshold to **borderlines**, not to
the total baseline. 30% of borderlines being intuition-
based crosses the §3.3 `not-ready` threshold (>25%).

**Note on dual denominators.** §3.2's 30% threshold applies
to the **total baseline** (40 of 200 = 20%, below the
threshold, so no §3.2 signal fires here). §3.3's 25%
threshold applies to **borderlines specifically** (12 of
40 = 30%, above the threshold, triggers `not-ready`).
Two different denominators; readers walking through the
protocol should track which check is being evaluated
against which population, or the thresholds will look
inconsistent. This dual denominator is intentional —
§3.2 measures whether the class definition itself is
ambiguous (an effect on the whole baseline), while §3.3
measures rule-articulation discipline at the boundary
where it matters most (the borderlines themselves).

**Verdict:** `not-ready`.

**Findings list:**
- 12 borderline rows where the Bug-vs-Question distinction
  was made by intuition.
- Recommendation: the §2 class definition needs an explicit
  rule for the Bug-vs-Question boundary. The user proposes
  a refinement during the consultation: "behavior the user
  has not asserted to be a defect, even if confusing, is a
  Question; behavior the user explicitly says is wrong is
  a Bug." Refinement goes into §11 revision log; the 12
  rows are re-validated.

**`BASELINE_QUALITY_NOTE`:** initial pass returned
`not-ready`. After §2 refinement and re-validation of the
12 affected rows, re-invocation returned `ready`. Note
records both passes for traceability.

**Outputs:** verdict `not-ready` initially. `/spp-baseline`
does not advance. User refines §2, re-invokes, gets
`ready`, then proceeds to G2.

### Example 4: severe class-balance drift → `not-ready`

**Setup.** Binary classification, 50 labeled rows. User's
plan.md §6 says production prevalence is ~5% positive (a
rare event). The labeler oversampled positives to make
labeling efficient; the labeled baseline is 60% positive.

**Protocol walk through §3.4.** Labeled 60%, production 5%,
drift 55 percentage points. Drift is intentional (the user
explicitly oversampled), and the metric chosen in §4 is
`precision_at_recall` with a documented recall floor — so
the prevalence drift is methodologically defensible
**provided** §6 documents it.

Check `plan.md` §6's `CLASS_BALANCE_TARGET` field: it
says "preserve production prevalence (~5%)." This
contradicts the actual labeled distribution.

**Verdict:** `revise` (not `not-ready` — the methodology
*can* support oversampling, but the contract has to say
so). The fix is in `plan.md` §6, not in the labels.

**Findings list:**
- §6 `CLASS_BALANCE_TARGET` says "preserve production
  prevalence (~5%)" but actual labeled distribution is
  60% positive.
- Recommendation: update §6 to "deliberately oversample
  positives for label efficiency; class-balance drift
  from production (5% → 60%) is intentional and
  acknowledged. The metric in §4 is `precision_at_recall`
  with a recall floor, which is robust to prevalence
  drift at training time. Production threshold
  calibration is a deploy-time concern, recorded as a §10
  open question."
- After §6 update and §11 revision-log entry, re-invoke;
  re-invocation returns `ready`.

**Outputs:** verdict `revise` initially → `ready` after
§6 update.

(Note: a *truly* `not-ready` example for §3.4 would be
**unintentional** drift the user cannot justify — e.g., the
labeler grabbed the first 50 rows from a non-uniform
sampling and ended up with 60% positive without realizing
the production rate was 5%. In that case the recommendation
is resample-from-scratch, and the verdict stays `not-ready`
until that happens.)

### Example 5: existing baseline, post-hoc class definitions → `not-ready`

**Setup.** User brings labels from a prior project (300
rows, 4 classes). The class definitions in `plan.md` §2
were written during the `/spp-init` consultation, *after*
the labels existed. Original labeler is reachable but did
not document criteria.

**Protocol walk.**
- §3.6 (provenance): labeling protocol is implicit; class
  definition in `plan.md` §2 was written post-hoc.
  Triggers a §3.1 drift check with extra scrutiny.
- §3.1 (drift, with scrutiny): sample 8 rows per class.
  For 1 of 4 classes (`Other`), the user's articulations
  diverge from the written §2 definition for 5 of 8
  sampled rows (>60%). The post-hoc definition of `Other`
  said "anything that doesn't fit Bug, Feature, or
  Question"; the original labeler had been using `Other`
  to mean "issues that need triage by a human." The two
  are not the same.

**Verdict (early-exit at §3.1):** `not-ready`. The
post-hoc `Other` definition does not describe the
existing labels.

**Findings list:**
- The `Other` class in §2 needs to be re-defined to match
  the original labeling intent (which the user
  reconstructs during the consultation: "issues that need
  human triage but aren't otherwise categorizable").
- After §2 update and §11 revision-log entry, re-validate
  the 8 sampled rows: 8/8 now match. Re-run §3.1 on a
  fresh sample of 8 from `Other`: 7/8 match (acceptable —
  one row is a borderline that gets relabeled).
- Re-invocation returns `ready`.

**Outputs:** verdict `not-ready` on first pass.
`/spp-baseline` halts at G2 — does not advance even if
user types the G2 approval phrase. User updates §2,
relabels one row, re-invokes, gets `ready`, advances.

If the user had wanted to override the `not-ready` verdict
without refining (rare and discouraged), they would record
an explicit override in `plan.md` §11 stating "accepting
post-hoc class-definition mismatch as a known limitation;
this is expected to inflate the loop's optimism about
generalization." The override propagates into `REPORT.md`
§7.2 at finalization time.

### Example 6: multi-field per-field calibration → mixed signals consolidate to `revise`

**Setup.** Multi-field structured-output classification (K=3
fields per OUTPUT_SCHEMA: `category` (enum of 4 values),
`brand_known` (boolean), `defect_severity` (enum of 3
values)). 120 labeled rows; one labeler with documented
criteria. The user surfaces this example specifically to
exercise per-field calibration on a non-trivial multi-field
schema (`DESIGN.md` §7.1.1 compat layer baseline-quality
adaptation).

**Protocol walk.** §3.1 / §3.3 / §3.5 each run per
OUTPUT_SCHEMA field; thresholds apply within each field's
sample independently.

- §3.1 (drift) on field `category`: sample 8 rows per class,
  all articulations match the written definition for the
  field. ✓
- §3.1 (drift) on field `brand_known`: sample 12 rows (6
  true, 6 false), all articulations match. ✓
- §3.1 (drift) on field `defect_severity`: sample 7 rows per
  class. Articulations diverge from the written definition
  for 2 of 7 rows in `severity = high` — the labeler is
  applying an unstated "user-reported impact" criterion
  alongside the written "objective severity" rule. Two of
  seven crosses §3.1's `revise` threshold (~28% on a small
  sample); the field's drift signal contributes `revise`.
- §3.2 (borderlines) across the baseline: 12 rows flagged
  (10%) — within the expected range for 120 rows.
- §3.3 (intuition-vs-rule) per field, on the borderline rows
  that touch each field: all `category` borderlines are
  rule-based; all `brand_known` borderlines are rule-based;
  3 of 6 `defect_severity` borderlines are intuition-based.
  Half the field's borderlines are intuition-driven —
  field-internal `not-ready` signal threshold is >25%, and
  3 of 6 = 50%. The `defect_severity` field contributes a
  `not-ready` signal.
- §3.5 (calibration, solo, blind re-label of 15 rows):
  per-field self-agreement is 14/15 on `category`, 15/15
  on `brand_known`, 12/15 on `defect_severity`. The 12/15
  on `defect_severity` is 20% self-disagreement, in the
  `revise` range (10–25%). This corroborates the §3.3
  finding: the labeler is not internally calibrated on
  `defect_severity`'s rule.
- §3.6 (provenance): not applicable — labels generated
  inside `/spp-baseline`.

**Within-field synthesis:**

| Field | Within-field verdict |
|---|---|
| `category` | `ready` |
| `brand_known` | `ready` |
| `defect_severity` | `not-ready` (§3.3 + §3.5 corroboration) |

**Cross-field consolidation:** any `not-ready` field
dominates → baseline-as-a-whole verdict is **`not-ready`**.
The user is not allowed to advance G2 on the approval phrase
alone; either resolve the `defect_severity` issues
(refine the field's definition in `plan.md` §2's per-field
sub-block, then re-validate the affected rows) or record a
`not-ready override` entry in `plan.md` §11.

**Findings list:**

- Field `defect_severity`, §3.1: rows ID'd 0019, 0073
  exhibit drift — the labeler applied an unstated
  user-reported-impact criterion. Recommendation: either
  refine the field's per-field definition in `plan.md` §2 to
  articulate the impact criterion, or relabel these rows to
  match the existing rule.
- Field `defect_severity`, §3.3: 3 of 6 borderlines
  (50%) intuition-based, with disagreement on which
  classes the borderlines belonged to. Recommendation:
  refine the field's per-field definition to articulate
  the boundary; relabel after refinement.
- Field `defect_severity`, §3.5: solo self-disagreement
  on `defect_severity` is 3 of 15 (20%), corroborating the
  §3.3 finding.

**`BASELINE_QUALITY_NOTE`:** initial pass returned
`not-ready` consolidated from per-field findings (per
`DESIGN.md` §7.1.1 compat layer baseline-quality
consolidation rule). After §2 per-field-definition
refinement on `defect_severity` and re-validation of the
affected rows, re-invocation returned `ready` per field
across all three fields, consolidating to baseline-as-a-whole
`ready`. Note records both passes for traceability.

**Outputs:** verdict `not-ready` initially → `ready` after
field-targeted refinement. `/spp-baseline` does not advance
on the first pass; advances after the second pass.

**Why this example matters.** It exercises the K > 1 path
end-to-end: §3 checks run per field, signals consolidate
according to the bucket-5 rule, and the user's correction is
field-targeted (only `defect_severity` needs work — the
other fields stay clean). Under K=1 the same protocol runs
exactly once on the lone field and the consolidation is the
identity — the within-field verdict becomes the baseline
verdict, equivalent to v0.1.0's behavior.

---

## 5. The cross-skill constraint

**Findings flow into `plan.md`, not into a separate
artifact.** This is the operational form of the
plan.md-as-contract rule (`DESIGN.md` §10 glossary). Two
specific destinations:

- **`plan.md` §6 (baseline section)** gains a
  `BASELINE_QUALITY_NOTE` paragraph (the §6 output of this
  sub-skill). The paragraph names what was reviewed, what
  was found, and what was resolved. It is required even
  when the verdict is `ready` — a `ready` verdict still
  attests that the review happened.
- **`plan.md` §11 (revision log)** gains a row whenever the
  baseline-quality review caused a change to §2 (class
  definition refinement), §6 (label changes, balance-target
  update), or §10 (new open question surfaced). The row
  follows the standard `plan.md.template` §11 schema
  (date, plan version, reason, by) and **bumps
  `PLAN_VERSION`** because the contract has changed.

What the sub-skill **does not** do:

- It does not write to a separate `baseline_quality_review.md`
  document. The review is part of the contract; separating
  it would create two sources of truth.
- It does not silently fix labels. Findings are surfaced;
  the user decides. The verdict reflects the surfaced
  findings, not the sub-skill's preferred fix.
- It does not annotate `data/baseline.csv` rows directly
  with quality metadata. The CSV is the raw labeled data;
  the review's findings live in `plan.md`'s prose, not in
  per-row metadata. (This decision keeps `data/baseline.csv`
  reproducible from labels alone.)

There is one place where the sub-skill's verdict
**does** have force outside `plan.md`: it gates whether
`/spp-baseline` advances past G2. That force is operational
(the command consults the verdict at the gate), not
documentary (no separate verdict file is written). See
`spp-baseline.md` §5 for the gate-enforcement mechanism.

---

## 6. What the sub-skill outputs

Three things the designer (or `/spp-baseline`) collects after
the protocol walk, all of which feed into the gate-G2
enforcement and the `plan.md` updates.

### Verdict

One of:

- `ready` — splits can be generated; G2 advances on user
  approval phrase alone.
- `revise` — issues exist; user can fix and re-invoke, or
  proceed with a documented justification in `plan.md` §11.
- `not-ready` — substantive issues exist; G2 does not
  advance on user approval phrase alone. Override requires
  an explicit `plan.md` §11 entry that propagates into
  `REPORT.md` §7.2.

The verdict is a single token; downstream tooling and the
Phase 4 validation harness can match it as a literal
string.

### `BASELINE_QUALITY_NOTE`

A paragraph for `plan.md` §6's "baseline-quality review"
subsection. Required regardless of verdict. Names what was
reviewed (which protocol checks ran per OUTPUT_SCHEMA field;
sample sizes), what was found (specific per-field findings
with row references when applicable), and what was resolved
(changes made before the final verdict). Under v0.2 the note
reports per-field findings followed by the consolidated
baseline-as-a-whole verdict (per §3.7's two-stage synthesis
and the "any-not-ready dominates" rule); under K=1 the
per-field summary collapses to a single field-section,
equivalent to v0.1.0's note shape.

The note is the audit trail. Future readers of `plan.md`
should be able to reconstruct what `baseline-quality`
checked per field and how the user responded, without
re-running the review.

### Findings list (only for `revise` and `not-ready`)

A list of specific per-field findings that need user
attention. Under v0.2 each finding is **scoped per
OUTPUT_SCHEMA field**: the finding names which field
surfaced the issue, the protocol check that surfaced it,
and the recommended action. Findings are grouped per field
in the document, so the user can address each field's
issues without cross-field interference. Under K=1 the
group has one section (the lone field), equivalent to
v0.1.0's flat findings shape.

Each item names:

- The OUTPUT_SCHEMA field involved (under K=1 this is the
  lone field; under v0.1.0's `LABEL_SPACE` fallback this is
  the auto-promoted `label` field).
- The row ID(s) involved (or "field-level definition" if
  the finding is at the per-field-definition level).
- The protocol check that surfaced the finding (§3.1,
  §3.3, etc.).
- The recommended action (refine field's per-field
  definition, relabel rows, resample baseline, etc.).
- An indication of whether the finding contributed to a
  `revise` or `not-ready` signal **for that field's
  within-field verdict** (per §3.7 within-field synthesis).

The list is **specific, not generic**. "Some rows look
inconsistent" is not a finding; "field `category`, rows
0017, 0042, 0089 were labeled `Spam` based on domain
reputation, which is not in the §2 per-field definition" is.

`/spp-baseline` surfaces this list to the user before
expecting any G2-related action.

---

## Pattern for subsequent sub-skills

`prompt-architect` (Phase 2 step 10) is the third and final
v1 sub-skill. It will follow the same six-section structure
established by `metric-design` and refined here:

- **Identity and scope**: what `prompt-architect` does
  (assembles a six-section XML prompt skeleton from
  `plan.md` §2 class definitions and §4 metric); who
  reads it (the designer agent during loop iteration; the
  Phase 2 step 10 spec is what defines this exactly).
- **The decision**: which prompt-architecture sections are
  required, which are optional, how they're populated
  from `plan.md`.
- **Decision tree**: the per-section walk.
- **Worked examples**: generic shapes, never source-
  project content.
- **Cross-skill constraint**: the prompt-architect output
  is the input to `/spp-loop`'s iteration-1 prompt; the
  six-section discipline is non-negotiable.
- **Output specification**: the file the sub-skill produces
  (`prompt_v01.md` per the existing
  `templates/prompt_v01.md.template`), written via the
  same atomic-write pattern as `plan.md`.

The verdict-with-gate-enforcement pattern established here
is **specific to `baseline-quality`** — not every sub-skill
needs gate authority. `prompt-architect` does not have a
verdict; its output is consumed directly by `/spp-loop`. The
auditor agent (Phase 2 step 6), however, *does* have a
verdict — `categorical` or `row-specific` — that gates
whether a rule edit advances to the next iteration. The
auditor's verdict-enforcement pattern is the analog of this
sub-skill's, applied per-iteration rather than per-baseline.
The agent doc for the auditor will adopt the same
verdict-token + enforcement-at-gate shape pinned here.

---

## Versioning

Same rule as `designer.md`, `/spp-init`, and `metric-design`:
changes that alter methodology guarantees are flagged as
`BREAKING CHANGE:` in commit messages and trigger a major-
version bump per `CLAUDE.md` §4.

**Methodology-affecting (= breaking):**

- **Loosening the `not-ready` verdict's gate-blocking
  authority.** This is the single most load-bearing rule
  in the sub-skill. A `baseline-quality` that recommends
  but does not block is a checklist, not a defense.
- **Removing class-definition drift (§3.1) or
  intuition-vs-rule divergence (§3.3) from the decision
  tree.** Both are designed to surface the precursors of
  baseline overfitting; removing them removes the
  defense.
- **Allowing the sub-skill to silently fix labels** rather
  than surfacing for user decision. The user is the only
  authority on what their labels mean; the sub-skill's
  authority is methodological.
- **Allowing findings to flow outside `plan.md`** (a
  separate `baseline_quality_review.md`, per-row CSV
  annotations, etc.). The plan.md-as-contract rule is what
  keeps the methodology auditable.
- **Removing the `BASELINE_QUALITY_NOTE` requirement on
  `ready` verdicts.** A `ready` verdict is itself an
  attestation; without the note, "we reviewed and found
  nothing" is indistinguishable from "we did not review."
- **Removing the v0.2 per-field re-scoping** of §3 review
  questions (`DESIGN.md` §7.1.1 compat layer
  baseline-quality adaptation). Reverting to a
  baseline-wide single review surface would silently break
  multi-field bookkeeping — fields that need attention
  would be aggregated into a single signal that hides
  which field surfaced what.
- **Promoting baseline-quality to per-field-verdict** (one
  verdict per field instead of consolidated single
  verdict). G2's enforcement pattern is single-verdict per
  baseline; multiplying the verdict to K verdicts would
  multiply the gate-evaluation surface, contradict the
  consolidation rule pinned in `DESIGN.md` §7.1.1 compat
  layer, and require coordinated changes to
  `/spp-baseline` §5 and the override-substring matching.
- **Changing the consolidation rule** (§3.7's
  "any-not-ready dominates, any-revise dominates ready").
  Specifically: requiring all fields to be `not-ready`
  before consolidating to `not-ready` (would silently
  weaken the gate); requiring all fields to be `ready`
  before consolidating to `ready` (would tighten in a way
  that makes K > 1 plans nearly always block at G2);
  averaging or weighted-voting verdict tokens instead of
  applying the dominance rule.

**Behavioral (= non-breaking):**

- Better worked-example phrasing.
- Adjusting threshold percentages in §3 with rationale
  (e.g., 25% → 20% for §3.1 drift) as long as the
  three-tier `ready` / `revise` / `not-ready` structure
  is preserved.
- New protocol checks added to §3 that satisfy the same
  verdict-tier discipline.
- Clearer findings-list formatting in §6.
- New cross-references.

When in doubt, treat the change as breaking.

---

## Cross-references

- [`agents/designer.md`](../../agents/designer.md) — the
  designer references this sub-skill in §5.4 (baseline
  questions). The reference was a stub at the time
  `designer.md` was written (Phase 2 step 2); this
  sub-skill is the fill-in.
- [`phases/spp-baseline.md`](../../phases/spp-baseline.md)
  — the command that invokes this sub-skill. Specifically:
  §4 (execution flow, the post-labeling
  `baseline-quality` invocation point) and §5 (gate G2
  enforcement, where the verdict has operational force).
- [`templates/plan.md.template`](../../templates/plan.md.template)
  — the destination for the sub-skill's findings. §6
  (baseline section, `BASELINE_QUALITY_NOTE` subsection)
  and §11 (revision log, when findings cause a change to
  §2 / §6 / §10).
- [`../schema-designer/SKILL.md`](../schema-designer/SKILL.md)
  — the verdict-gated sibling sub-skill (bucket 1 of v0.2)
  whose OUTPUT_SCHEMA fields this sub-skill calibrates
  against per-field. `baseline-quality`'s per-field protocol
  consumes `schema-designer`'s output (the OUTPUT_SCHEMA in
  `plan.md` §2 and the per-field definitions below it); the
  unit of review is the field, not the row.
- [`../metric-design/SKILL.md`](../metric-design/SKILL.md)
  — the per-field protocol pattern this sub-skill's
  per-field calibration parallels (`DESIGN.md` §7.1.1
  metrics layer; bucket 2 of v0.2). The asymmetry is
  intentional: `metric-design` is review-and-record,
  `baseline-quality` retains verdict-gate authority. Future
  contributors proposing to align the two should read
  `metric-design`'s "Versioning" section (specifically the
  rationale for why `metric-design` does not gate) before
  editing.
- `DESIGN.md` §2.1 (baseline overfitting failure mode —
  the deal-breaker this sub-skill defends against),
  §7.1.1 compat layer (the v0.2 contract this sub-skill's
  per-field calibration realizes — per-field re-scoping of
  §3 review questions; consolidation rule for the
  single-verdict G2 gate; K=1 backward compatibility),
  §10 glossary (sacred test set — clarifies that
  baseline-quality runs *before* splits exist, so the
  test-set guarantee is not at risk; plan.md as contract
  — the rule that findings flow into `plan.md`, not into
  separate documents), §7.1 non-goals (the new DSPy /
  GEPA / APE entry that this PR adds).
- `CLAUDE.md` §4 (Semantic Commits — applies to changes
  to this sub-skill), §8 (auditor information isolation
  — referenced indirectly: the loop's auditor must not
  be exposed to the test set, and `baseline-quality`
  does not interact with the test set because it runs
  before splits exist).
