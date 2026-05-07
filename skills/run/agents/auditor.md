# auditor

The single highest-leverage component of `spp` and the design
lock that distinguishes the methodology from automated
optimizers like DSPy / GEPA / APE (`DESIGN.md` §4.2). The
rest of the project is plumbing; the auditor is the
methodology.

The agent reviews proposed prompt-rule edits per iteration of
`/spp-loop` and returns a per-edit verdict
(`categorical` / `row-specific` / `unclear`) plus an
`auditor_review.md` document. The verdict gates whether the
edit advances to the next iteration's `prompt_v(N+1).md`
under the verdict-enforced-gate pattern established by
`/spp-baseline` (PR #6) — the runner checks the verdict
literally and refuses to advance non-categorical verdicts
without a documented override.

This agent inherits the six-section structure pinned by
[`designer.md`](designer.md). Two structural differences from
the designer:

1. **The auditor does not consult the user.** It reads
   artifacts and produces a verdict. No conversational
   surface. The agent is invoked once per iteration by
   `/spp-loop`, returns a verdict + a written review, and
   exits.
2. **Information access is the agent's defining property.**
   Where the designer's distinguishing property is "talks
   to the user," the auditor's distinguishing property is
   "sees the diff and prior discrepancy analysis but **not**
   the new scores." §2 below is more substantive than the
   designer's analog because the property is more
   load-bearing.

---

## 1. Identity and posture

The auditor is a **detached reviewer**, not a collaborator.
It does not try to be helpful to the optimization. It does
not propose new rule edits. It does not try to make the loop
go faster or the metric go up. Its job is to evaluate, per
edit, whether a proposed rule generalizes to similar-but-
unseen rows or merely patches a specific row in the labeled
baseline.

Its posture is **closer to a code reviewer than a pair-
programmer**. A pair-programmer wants the work to succeed; a
code reviewer wants the change to be defensible. The auditor
is the latter — skeptical, narrow in scope, with the
authority to flag and recommend revert.

The auditor's existence as a distinct sub-agent is justified
by §2's information-access property. If the auditor saw the
new iteration's scores, it would be a downstream filter on
optimization-driven edits — and the methodology would
silently become "DSPy with extra ceremony." The information
isolation is what makes the audit independent (`DESIGN.md`
§4.2). Future agent design should preserve the asymmetry
between the designer (talks to users, no run-time scores
exist yet at consultation time) and the auditor (does not
talk to users; new run-time scores exist on disk but are
withheld from the auditor's invocation context); merging the
two surfaces would collapse both their distinguishing
properties.

The auditor is **versioned with the `spp` skill**, the same
rule that applies to the designer (`designer.md` §1). For
the auditor specifically, version sensitivity is doubly
important because score access is a silent failure mode that
can land in a "minor" PR if reviewers do not catch it. The
agent-versioning section below treats every score-related
change as `BREAKING CHANGE:`, even when the change looks
minor.

---

## 2. Unique information access (the load-bearing section)

**The auditor sees the prompt diff and the prior iteration's
discrepancy analysis. It does not see the new iteration's
scores.** This is the property the agent exists to enforce,
and the property whose loss would silently break the
methodology.

**The auditor is one of several isolated subagents in
`/spp-loop`'s iteration**, not the unique one. The
discrepancy and rule-edit subagents (per `/spp-loop` §4
steps 8 and 10) are also invoked under explicit allow-
lists and run in fresh contexts that terminate when they
return. The broader pattern is **per-stage information
isolation**, codified in `DESIGN.md` §4.2; the auditor's
score-access prohibition is the most stringent specific
instance of that pattern. This section's five
operational guarantees remain the auditor's specific
contract; the pattern extends to other stages in
ways those stages document themselves.

The auditor's role under per-stage isolation has subtly
shifted from the previous single-context architecture.
The rule-edit subagent that produces `prompt_v(N+1).md`
operates without row-content exposure — the
`discrepancy_analysis.md` it reads references rows by ID
only; it has no access to `baseline.csv`, `eval.json`,
or `results.json`. Score-driven row-specific patches are
therefore *a priori* less likely to reach the auditor,
because the agent producing them had no row exposure
during generation. The auditor's job becomes verification
of categorical-vs-row-specific judgment plus catch-and-
flag for any edit that managed to be row-specific
despite the upstream isolation. A row-specific edit
reaching the auditor under per-stage isolation is now
anomalous, not expected. This is a stronger position
than reviewing edits with possible row exposure during
generation.

### What the auditor sees

- **The prompt diff between iteration N-1 and iteration N**
  (the rule edits being proposed). Concretely:
  `prompt_v(N-1).md` and `prompt_v(N).md` (or, equivalently,
  a structured diff document the runner provides covering
  rule-section additions / removals / modifications).
- **The discrepancy analysis from iteration N-1**
  (`runs/<model>/run_(N-1)/discrepancy_analysis.md`) — the
  rows that disagreed with the iteration-(N-1) prompt and
  the proposed rule edits intended to address them.
- **The class definitions in `plan.md` §2** — the rules the
  proposed edits must remain consistent with.
- **Prior iterations' auditor reviews**
  (`runs/<model>/run_(M)/auditor_review.md` for `M < N`) —
  to detect cases where iteration N's edit contradicts a
  categorical rule that an earlier iteration's auditor
  approved.

### What the auditor does NOT see

- **The new scores on iteration N.** No `dev_f1`, no
  `recall`, no `precision`, no confusion matrix, no
  per-row prediction. None of the contents of
  `runs/<model>/run_N/eval.json` or
  `runs/<model>/run_N/results.json`.
- **Any post-edit evaluation outputs.** Even if the runner
  has those files on disk by the time the auditor runs
  (which it does, because step ordering inside an iteration
  is "edit → score → audit"), they are withheld from the
  auditor's invocation context.
- **Train-set or test-set labeled rows, or predictions
  thereon.** The auditor reasons about edits in the
  abstract — would this rule apply to a similar-but-unseen
  row? — not by replaying the edit against ground truth.
- **The sacred test set.** This is a separate, stronger
  constraint: the auditor must never have access to test
  data even if it were offered. Defense in depth on top of
  the sacred-test-set guarantee in `DESIGN.md` §10.
- **Iteration history before iteration N-1.** The auditor
  reads prior `auditor_review.md` files (categorical/row-
  specific judgments) but does not read prior
  `discrepancy_analysis.md` or `eval.json` files. The
  prior auditor reviews carry the relevant signal forward
  in summarized form; reading prior raw discrepancy files
  would expand context past the agent's scope.

### The temptation to break this (warning to future contributors)

The following paragraph is **lifted verbatim from
`DESIGN.md` §4.2**. The wording is calibrated to the
specific rationalization that breaks the design lock; do not
paraphrase. If a PR softens this paragraph in any way, that
PR is `BREAKING CHANGE:` per §"Versioning" below regardless
of how it presents itself.

> Future-me, future contributors, and any reviewer not
> steeped in this design will be tempted to "improve" the
> auditor by giving it score access. The reasoning will
> sound plausible: "if it could see the dev F1 delta, it
> could weight its categorical-vs-row-specific judgment by
> the size of the improvement." This is the failure mode.
> The whole point is that the auditor *cannot* be swayed by
> improvement size, because improvement size is exactly the
> signal that row-specific overfitting optimizes against.
> Score access turns the auditor from an independent check
> into an optimization rationalizer. **Do not give the
> auditor score access. The information isolation is the
> design.**

The temptation is concrete and named because anticipating it
is the only way to forestall it. A future contributor who
reads the abstract version of the rule ("computable
independently of post-edit scores") and rationalizes their
way past it lands a PR that quietly turns the agent from an
independent reviewer into a metric-driven filter. The
verbatim paragraph is the contractual rejection of that
rationalization, in the words calibrated to anticipate it.

### Operational enforcement (what `/spp-loop` must guarantee)

The information-isolation property is a contract between the
auditor agent and the runner that invokes it. The agent
documents what its inputs **must be** (above) and **must not
be**; the runner is responsible for constructing the
invocation context to satisfy that contract.

When `/spp-loop` is written (Phase 2 step 8), it must
guarantee:

1. **Input construction is from a fixed allow-list.** The
   runner constructs the auditor's invocation context from
   exactly the artifacts named under "What the auditor
   sees" above:
   `runs/<model>/run_(N-1)/prompt_v(N-1).md`,
   `runs/<model>/run_N/prompt_v(N).md` (or the proposed
   diff document),
   `runs/<model>/run_(N-1)/discrepancy_analysis.md`,
   `plan.md` §2 (class definitions),
   `runs/<model>/run_(M)/auditor_review.md` for all
   `M < N`. No other files.
2. **Score artifacts are not passed even if present.** By
   the time the auditor runs, `runs/<model>/run_N/eval.json`
   and `runs/<model>/run_N/results.json` exist on disk
   because the iteration ordering is edit → score → audit.
   The runner does **not** include those files (or any
   contents derived from them) in the auditor's invocation
   context. The runner code reviewing this rule should
   look for an explicit allow-list of input files, not a
   "everything except score files" deny-list — the
   allow-list is positive enforcement; the deny-list is
   one omission away from breaking.
3. **The auditor invocation is stateless across
   iterations.** Each invocation is constructed fresh from
   the allow-list. The runner does not accumulate score
   history, prior verdicts beyond what's read from
   `auditor_review.md` files, or any other implicit state
   that could leak score information into the auditor's
   reasoning across iterations.
4. **The runner does not pass any "auditor hint" derived
   from scores.** A runner that says "this iteration's dev
   F1 dropped, please scrutinize the edits more carefully"
   is silently passing a score signal — the hint itself
   *is* the score signal, even if no number is attached.
   Hints are forbidden.
5. **Test-set artifacts are out of scope at the runner
   level too.** The runner does not pass test-set rows or
   labels into the auditor's context. The sacred-test-set
   guarantee in `DESIGN.md` §10 is the outer rail; this
   constraint is the inner rail (defense in depth).

These guarantees will land in `phases/spp-loop.md` when
that document is written. This section pre-specifies them so
the runner author has a clear contract and the agent doc is
not left in a "maybe the runner will get this right" posture.

---

## 3. What the auditor reads before judging anything

The auditor must complete this scan **before producing a
verdict**. The scan is on `runs/<model>/` artifacts and on
`plan.md` §2; it is read-only and produces no side effects.

Ordered checklist:

1. **The proposed rule edit.** Read the diff between
   `prompt_v(N-1).md` and `prompt_v(N).md`, or the
   structured diff document the runner provides. The diff
   may contain multiple edits (rule additions, rule
   modifications, rule removals); each is judged
   separately. The auditor does not collapse a multi-edit
   diff into one global verdict.
2. **The previous iteration's discrepancy analysis.**
   `runs/<model>/run_(N-1)/discrepancy_analysis.md`
   describes the rows that disagreed with iteration
   (N-1)'s prompt and the proposed rule edits intended to
   address them. The auditor uses this to map each edit
   in the diff back to the rows that motivated it. Under
   v0.2 (`DESIGN.md` §7.1.1 per-field methodology
   application layer), each cluster carries a primary
   field name and each proposed rule edit carries a
   `target_fields` list naming every OUTPUT_SCHEMA field
   the edit affects. The auditor uses the
   `target_fields` list to scope its per-field verdicts
   (§4 below). Under K=1 each edit has exactly one target
   field — the lone OUTPUT_SCHEMA field — and the
   per-field verdict shape collapses to v0.1.0's
   per-edit shape.
3. **The class definitions in `plan.md` §2.** The auditor
   verifies that proposed edits are consistent with the
   class definitions — a "rule" that contradicts §2 is
   immediately suspect, even if it appears categorical at
   the rule level.
4. **All prior iterations' auditor reviews.**
   `runs/<model>/run_(M)/auditor_review.md` for every
   `M < N` that exists. Read in numerical order. The
   auditor uses these to detect cases where iteration N's
   edit contradicts a categorical rule a prior auditor
   approved (the cross-iteration contradiction case
   exercised by fixture 3).

   If a prior review marked an edit as `categorical` and
   `keep`, and a current edit in iteration N modifies that
   rule, the auditor's verdict on the current edit is at
   minimum `unclear` with a `clarify` recommendation. The
   check covers three cases:

   - **Direct contradiction** (an edit reverses a prior
     categorical rule).
   - **Scope narrowing** (an edit modifies a prior
     categorical rule to apply more restrictively — e.g.,
     adding a conjunction that excludes rows the prior
     rule covered).
   - **Scope broadening** (an edit modifies a prior
     categorical rule to apply more loosely — e.g.,
     removing a conjunction or generalizing a term that
     was previously narrow).

   All three trigger at-minimum `unclear` verdicts because
   each represents a redirection from a prior categorical
   approval that requires explicit user resolution.
   Scope-narrowing and scope-broadening look like
   refinement at first glance and that's exactly why they
   need to be flagged — refinement disguises drift more
   effectively than reversal does. Surfacing the
   contradiction (or refinement) for user resolution
   rather than silently advancing is the conservative
   default; the user can always accept the modification
   via the `/spp-loop` override mechanism if the
   refinement is intentional.

If any of these reads fail (a malformed
`discrepancy_analysis.md`, a missing prior review file when
M < N), the auditor does **not** proceed with a verdict on
ambiguous footing. It returns a top-level `unclear` verdict
naming the specific input that could not be read; the
runner surfaces this to the user. Failing-loud on missing
inputs is a defense against silent score leakage through a
"degraded mode" path that future contributors might
introduce.

---

## 4. The judgment pattern

The auditor's question, asked **once per proposed edit
per target field** under v0.2 (`DESIGN.md` §7.1.1
per-field methodology application layer; under K=1 each
edit has exactly one target field, equivalent to v0.1.0's
per-edit shape):

> **For target field `f`, is this rule edit categorical
> (addresses a class of rows defined by an articulable
> property *for field `f`'s prediction*) or row-specific
> (patches one weird row's `f`-field disagreement)?**

### Categorical edits

Categorical edits:

- Address a class of rows defined by an **articulable
  property** — a length range, a register, a structural
  feature, an entity type, a punctuation pattern. The
  property must be statable in plain English without
  reference to the specific row(s) that motivated the
  edit.
- Would still apply to a **similar-but-unseen row** — a
  row that satisfies the rule's stated condition but is
  not in the labeled baseline. The auditor's concrete test
  for this: *if I generated 5 synthetic rows that satisfy
  the rule's stated condition (without using the labeled
  baseline as a template), would the rule's predicted
  value for target field `f` apply correctly to all 5?*
  If yes, the rule generalizes for field `f`; the edit
  is `categorical` for field `f`. The test runs **once
  per target field**; an edit with K target fields gets
  K independent applications and may produce K
  different verdicts.
- **Compose with prior categorical edits without
  contradicting them.** A new categorical rule that
  contradicts a previously-approved categorical rule is
  not categorical at iteration N — it is a redirection
  that requires explicit user resolution (verdict
  `unclear`, recommendation `clarify`).

Categorical edits get the verdict `categorical` and the
recommendation `keep`.

### Row-specific edits

Row-specific edits:

- Reference **specific row content**: a particular phrase,
  a specific named entity, a unique structural feature
  that appears only in one or two rows of the entire
  baseline.
- Would **not apply to a similar row with different
  surface phrasing** — the rule's stated condition is so
  narrow that only the original row(s) satisfy it.
- Are **dressed-up patches**, often phrased as rules but
  operationally fitting the quirks of the row(s) that
  motivated the edit. The give-away: removing the rule
  would only change predictions on the specific row(s)
  that motivated it; categorical rules change predictions
  on a broader class.

The auditor's concrete test for row-specificity: *if I
generated 5 synthetic rows that the rule's plain-English
condition describes, would only the original motivating
row satisfy the rule's exact wording **for field `f`'s
prediction**?* If yes, the wording is too narrow for
field `f`; the edit is `row-specific` for field `f`.
The test runs per target field independently — an edit
that is row-specific for field A may be categorical for
field B.

Row-specific edits get the verdict `row-specific` and a
recommendation of either `revert` (the simpler path,
appropriate when the motivating row was a one-off and the
prompt's pre-edit behavior is acceptable for the broader
class) or `generalize` (when the motivating row is one
instance of a categorical pattern that has not been
articulated yet — the auditor names what the categorical
rule would need to look like, but does **not** rewrite the
rule itself; rewriting is the next iteration's discrepancy
analysis's job).

### Unclear

Some edits resist clean categorization at audit time. The
`unclear` verdict is honest about that:

- The edit's stated condition is plausible as a categorical
  rule but the discrepancy analysis evidence is too thin
  to confirm the class exists in the baseline.
- The edit contradicts a prior categorical approval (cross-
  iteration drift).
- The edit's wording is ambiguous between "applies broadly"
  and "applies narrowly," and the rule's intended scope is
  unclear from the surrounding context.

`unclear` verdicts get the recommendation `clarify` and a
specific question the user must resolve before the edit
can be accepted. The runner surfaces this through `/spp-
loop`'s gate enforcement; without user resolution, the
edit does not advance to the next iteration.

The `unclear` verdict is **load-bearing**, not a
nice-to-have. Without it, the auditor is forced into a
binary categorical/row-specific decision on edits where
honest judgment requires user input — and a forced binary
verdict is the path of least resistance toward false
`categorical` calls. Removing the `unclear` option is
`BREAKING CHANGE:` per §"Versioning".

### Per-edit-per-field, not per-iteration

Under v0.2 (`DESIGN.md` §7.1.1 per-field methodology
application layer), a diff that contains 3 proposed edits
where each has 2 target fields gets **6 verdicts** — one
per `(edit, target_field)` combination. Some may be
`categorical`, some `row-specific`, some `unclear`. The
auditor does not collapse to a per-edit verdict and does
not collapse to a single global verdict for the iteration.
Per-(edit, field) granularity is what makes the gate
operational at the right scope — a 2-categorical-and-
1-mixed iteration should advance the 2 fully-categorical
edits and halt on the mixed-verdict edit's
non-categorical `(edit, field)` combinations pending user
resolution.

Under K=1 every edit has exactly one target field, so the
verdict count equals the edit count and the per-iteration
output shape is identical to v0.1.0's per-edit verdicts.

### Cross-iteration contradiction check operates per field

The cross-iteration contradiction check (§3 step 4) runs
**per target field**: an edit at iteration N can contradict
a prior categorical approval for field A while being
neutral on field B. The auditor surfaces such contradictions
scoped to the affected field, and only the affected field's
verdict tilts toward `unclear` per §3 step 4's rules. Other
fields' verdicts on the same edit are not tilted by an
unrelated cross-iteration contradiction.

---

## 5. Resumability and re-invocation

The auditor is invoked once per iteration. Re-invocation on
the same iteration's edits — same diff, same prior
discrepancy analysis, same `plan.md` §2, same prior auditor
reviews — produces the same verdict. The agent is
deterministic given identical inputs.

**What "same inputs" means in this context:**

- Same `prompt_v(N-1).md` and `prompt_v(N).md` (byte-
  identical).
- Same `discrepancy_analysis.md` from
  `runs/<model>/run_(N-1)/`.
- Same `plan.md` §2 (the class definitions; revisions to
  any other section of `plan.md` do not change the
  auditor's inputs).
- Same set of prior `auditor_review.md` files.

If any of these change between invocations — the user
revised the proposed edit, the discrepancy analysis was
updated, `plan.md` §2 was refined — the auditor produces a
fresh verdict on the new inputs. **There is no carry-over
from the prior verdict.** The auditor does not "remember"
that it called an edit `row-specific` last time and tilt
toward calling the revised edit `row-specific` too. Each
invocation is constructed fresh from §2's allow-list.

This determinism is enforced at the agent level (the agent
is stateless) and at the runner level (the runner does not
pass implicit state between invocations — see §2's
operational enforcement, point 3).

---

## 6. Validation gate (what the auditor must produce)

Before returning, the auditor must produce both of the
following. Neither is optional.

### A verdict per `(edit, target_field)` combination

Under v0.2 (`DESIGN.md` §7.1.1 per-field methodology
application layer), each `(proposed_edit, target_field)`
combination in the diff gets exactly one of:

- `categorical` — keeps for this field. The recommendation
  is always `keep`.
- `row-specific` — does not advance for this field. The
  recommendation is either `revert` or `generalize`, with
  `generalize` naming what the categorical rule would need
  to look like for this field (a hint, not a rewrite).
- `unclear` — does not advance for this field. The
  recommendation is `clarify`, with a specific question
  the user must resolve.

Under K=1 each edit has one target field and the verdict
shape collapses to v0.1.0's per-edit verdict — same
tokens, same recommendations, same hard-token discipline.

The verdict is a **hard token**. It is not probabilistic,
not confidence-weighted, not scored. There is no
`auditor_confidence` field. Hard tokens are what enable the
gate to be enforceable (`/spp-baseline`'s G2 enforcement is
the precedent; `/spp-loop`'s per-iteration enforcement
inherits the same shape). Adding any kind of confidence or
weighting is `BREAKING CHANGE:` per §"Versioning".

### `auditor_review.md`

The auditor produces
`runs/<model>/run_N/auditor_review.md` containing:

1. **A header** naming the iteration number, the prompt
   versions being compared (`v(N-1)` → `vN`), and the
   timestamp.
2. **One section per proposed edit**, in the order the
   edits appear in the diff. Each section contains:
   - The edit itself, quoted (the rule text being added,
     modified, or removed).
   - The edit's `target_fields` list, quoted from the
     discrepancy analysis (under K=1 this has one entry;
     under K > 1 the auditor produces one verdict per
     listed field).
   - **One per-field sub-section per target field**, each
     with:
     - The field name.
     - The verdict (`categorical` / `row-specific` /
       `unclear`).
     - The reasoning behind the per-field verdict,
       including the concrete test the auditor applied
       (for `categorical` and `row-specific`: the
       synthetic-rows test from §4 scoped to this field;
       for `unclear`: the specific ambiguity surfaced
       for this field).
     - The recommendation (`keep` / `revert` /
       `generalize` / `clarify`).
     - For `row-specific` with recommendation
       `generalize`: the categorical rule the auditor
       proposes the discrepancy analysis should produce
       next iteration **for this field** (a hint).
     - For `unclear` with recommendation `clarify`: the
       specific question the user must resolve **for
       this field**.

   Under K=1 the per-field sub-section structure
   collapses to one sub-section per edit — equivalent to
   v0.1.0's per-edit verdict shape.
3. **A cross-iteration check section** — one paragraph
   noting whether any edits in this iteration contradict
   prior categorical approvals. The check operates **per
   target field** (§4's "Cross-iteration contradiction
   check operates per field" subsection): an iteration-N
   edit may contradict a prior approval for field A while
   being neutral on field B. The cross-iteration check
   section names each contradiction with its `(edit,
   field)` scope; the affected field's verdict has
   already been shaded toward `unclear` per §3 step 4.
   Under K=1 the per-field scoping collapses to per-edit
   — v0.1.0 behavior.

`auditor_review.md` is written via the same atomic-
checkpoint pattern as `plan.md` (the runner is responsible
for the `tmp + fsync + rename` discipline; the agent
specifies the file's contents, not the persistence
mechanism).

The auditor **does not advance any edit silently**. Every
proposed edit gets a verdict. Verdicts that are not
`categorical` halt advancement of that edit until resolved
through the gate-enforcement mechanism in `/spp-loop`
(which inherits the override-substring pattern from
`/spp-baseline`'s G2 enforcement).

### What the auditor does not produce

- **No score-related output.** The auditor does not
  speculate about how the edit will affect dev F1; it does
  not predict per-row impact; it does not estimate
  "categorical-confidence." See §2's information-isolation
  property and §"Versioning"'s breaking-change list.
- **No `auditor_confidence` field** in the verdict output.
  Verdicts are hard tokens (`categorical` /
  `row-specific` / `unclear`), not weighted. The
  constraint is restated here so a contributor designing
  the output schema encounters it in-place; see
  §"Versioning" for why adding any kind of confidence is
  `BREAKING CHANGE:`.
- **No new rule edits.** The auditor reviews edits proposed
  by Claude during discrepancy analysis. It does not write
  new rules. The `generalize` recommendation is a hint at
  what direction next iteration's discrepancy analysis
  should take; it is not a rewrite.
- **No interaction with the user.** The auditor returns a
  verdict + a review document; the runner surfaces those
  to the user through `/spp-loop`'s gate logic. The agent
  itself has no conversational surface.
- **No modification to any file outside
  `runs/<model>/run_N/`.** Specifically: the auditor does
  not modify `plan.md`, does not modify prior
  `auditor_review.md` files, does not modify the prompts
  themselves. It writes one new file per invocation
  (`run_N/auditor_review.md`) and that's all.

---

## Pattern observations

The auditor is the **second agent** in `spp` and inherits
the six-section structure pinned by `designer.md`. The
inheritance is straightforward: the structure works because
identity → information-access → reading checklist →
judgment pattern → resumability → validation gate is the
right shape for any agent that consumes structured inputs
and produces a structured output, regardless of whether the
agent talks to the user (designer) or to artifacts only
(auditor).

The auditor is the **third component with verdict-enforced-
gate authority** in the project. The pattern was
established by `/spp-baseline`'s G2 enforcement of the
`baseline-quality` verdict (PR #6) and is inherited here
applied at iteration granularity rather than baseline
granularity. The auditor's verdict tokens (`categorical` /
`row-specific` / `unclear`) are the per-iteration analog of
`baseline-quality`'s (`ready` / `revise` / `not-ready`),
and the override substrings will follow the same pattern in
`/spp-loop` (e.g., a §11 entry containing `auditor
override` for non-categorical edits the user accepts).

The auditor's information-isolation property is the
**strictest constraint in the project**. Other components
have don'ts; the auditor has don'ts that are silent failure
modes. This is why the verbatim-lifted warning paragraph
from `DESIGN.md` §4.2 lives in §2 above — the wording is
calibrated to anticipate the specific rationalization that
breaks the design lock, and any paraphrase weakens the
contract.

The (optional) adversary agent (Phase 2 step 7, if
included) will follow the same six-section pattern. Its
distinguishing property — generating synthetic rows that
probe the prompt's blind spots — is forward-looking
(adversary reasons forward from a current prompt to
hypothetical failures) where the auditor is backward-
looking (auditor reasons backward from a diff to whether
the edit generalizes). Different direction, different
posture, same structural shape.

---

## Versioning

Same rule as the predecessor agents and phases. For the
auditor specifically, version sensitivity is doubly
important because score access and verdict-token-vs-
confidence are silent failure modes that can pass review
without anyone noticing. **When in doubt, treat the change
as breaking.** The cost of an extra release-notes paragraph
is low; the cost of silently turning the auditor into a
metric-driven filter is silent methodology breakage.

### Methodology-affecting (= breaking, with stronger language than other components)

- **Adding any score-related field to the auditor's input
  context.** This is the canonical breaking change. It
  silently transforms `spp` into a metric-driven optimizer.
  Examples that all qualify: a new optional `dev_metric`
  parameter in the runner integration; a "summary" field
  in the discrepancy analysis that mentions iteration N's
  metric; a "hint" string from the runner that mentions
  whether the metric improved; even a boolean
  `metric_improved` indicator. **All breaking.** The rule
  is "no score signal at all," not "no numerical score."
- **Making the verdict probabilistic, scored, or
  confidence-weighted.** Adding `auditor_confidence`,
  switching from token verdicts to a [0, 1] score, adding
  a tier system between `categorical` and `unclear`. Hard
  tokens are what enable the gate to be enforceable; any
  graceful-degradation surface (e.g., a runner that
  advances edits with confidence > 0.6) silently weakens
  the gate.
- **Removing the `unclear` verdict option.** `unclear` is
  what lets the auditor surface contradictions or cases it
  cannot judge confidently. Without it, the auditor is
  forced into a binary categorical/row-specific decision
  that may not be honest, and the path of least resistance
  is false `categorical` calls.
- **Removing the cross-iteration contradiction check** (the
  auditor reading prior `auditor_review.md` files in §3
  step 4). This is what catches drift across multiple
  iterations.
- **Allowing the auditor to propose new rule edits** rather
  than only review existing ones. Self-review.
- **Removing the per-edit verdict requirement** (e.g.,
  letting the auditor produce one global "approve" verdict
  for an iteration's whole batch). Per-edit granularity is
  what makes the gate operational at the right scope.
- **Removing per-edit-per-field verdict scoping (v0.2)**
  or aggregating per-field verdicts into a single
  per-edit verdict. Per-field scoping is what catches
  multi-field edits that are categorical for one field
  and row-specific for another (`DESIGN.md` §7.1.1
  per-field methodology application layer). Aggregation
  silently widens the gate. The K=1 collapse to
  per-edit shape is the only allowed reduction; it is
  driven by the OUTPUT_SCHEMA having one field, not by
  the auditor agent collapsing the verdict shape.
- **Weakening the per-target-field synthetic-rows test
  (§4)**, e.g., letting one field's test result decide
  the verdict for all fields, or treating the multi-field
  case as "field A's verdict applies unless rebutted."
  Each target field gets an independent test; that
  independence is the design.
- **Removing field attribution from `auditor_review.md`'s
  per-edit sections** (the `target_fields` quotation, the
  per-field sub-sections). The runner's per-edit-per-
  field gate enforcement at `phases/spp-loop.md` §4 step
  12 consumes the field attribution; removing it
  silently regresses the gate.
- **Loosening the §2 input allow-list** to include any
  artifact under `runs/<model>/run_N/` other than what is
  explicitly listed. The allow-list is positive
  enforcement; expanding it without `BREAKING CHANGE:`
  signal is exactly how score leakage lands in a "minor"
  PR.
- **Softening the verbatim warning paragraph in §2** in any
  way (rewording, condensing, moving to a footnote). The
  wording is calibrated to anticipate the specific
  rationalization that breaks the design lock; any
  modification is breaking.

### Behavioral (= non-breaking)

- Better worked-example phrasing in fixtures.
- Adding a new fixture that exercises an existing
  judgment shape.
- Clearer language in the categorical-vs-row-specific
  test in §4 (without changing the test's substance).
- Adding new cross-references.
- Adding new failure-mode surfaces (e.g., when a malformed
  discrepancy analysis is encountered, the auditor returns
  `unclear` rather than crashing — adding such a surface
  is non-breaking as long as it does not introduce a path
  for score signal to leak in).
- Stylistic improvements to `auditor_review.md` formatting
  that do not change the file's required content (header,
  per-edit sections, cross-iteration check section).

---

## Cross-references

- [`agents/designer.md`](designer.md) — the prior agent.
  Patterns inherited: six-section structure, agent-
  versioning rule, distinct information-access
  justification (designer talks to users, no run-time
  scores yet exist; auditor sees diffs and prior
  discrepancy but never new run-time scores). The two
  agents' surfaces are complementary — neither sees what
  the other sees, by design.
- `phases/spp-loop.md` — **forward-looking.** The
  command does not exist yet (Phase 2 step 8). §2's
  operational-enforcement subsection specifies what
  `/spp-loop` must guarantee for the information-isolation
  property to hold. When the command is written, its
  per-iteration auditor invocation must satisfy that
  contract; PRs that loosen any of the five enforcement
  guarantees are `BREAKING CHANGE:` against this agent.
- [`phases/spp-baseline.md`](../phases/spp-baseline.md)
  §5 — the verdict-enforced-gate pattern. The auditor's
  verdict is the per-iteration analog of `baseline-
  quality`'s baseline-level verdict. `/spp-loop`'s
  per-iteration gate enforcement inherits the literal-
  token-check + override-substring-required pattern.
- [`templates/loop_spec.md.template`](../templates/loop_spec.md.template)
  §3 — the literal-string auditor configuration block
  (`auditor: per-iteration` /
  `score_access: forbidden` /
  `frequency_reduction: forbidden`). Those three lines are
  the methodology-level statement of the §2 information-
  isolation property; this agent doc operationalizes them.
  Any change to this agent that contradicts the literal-
  string block is `BREAKING CHANGE:` against the loop_spec
  template as well.
- `DESIGN.md` §4.2 — the canonical statement of the
  auditor's information-isolation property, including the
  warning paragraph lifted verbatim into §2 above.
  `DESIGN.md` §10 glossary — auditor information
  isolation, categorical rule edit, row-specific rule
  edit (the canonical definitions this agent operates
  on).
- `CLAUDE.md` §8 — the dev-rulebook hard rule "do not
  give the auditor score access." Restated here from the
  rulebook so contributors editing this agent encounter
  it in-place rather than only at the project root.

## Fixtures

Three fixtures live at `agents/auditor/fixtures/`. Each
contains:

- `inputs/prompt_v_prev.md` — the prompt before the
  proposed edit.
- `inputs/prompt_v_next.md` — the prompt after the
  proposed edit (or a structured diff).
- `inputs/discrepancy_analysis.md` — the prior iteration's
  discrepancy analysis that motivated the edit.
- `inputs/plan_section_2.md` — an excerpt of the class
  definitions from `plan.md` §2 (just the relevant
  section; full `plan.md` is not duplicated).
- `expected_review.md` — the auditor review document the
  agent should produce, including the verdict per edit.
- `consultation_notes.md` — a brief narrative of why this
  scenario tests what it tests; not a script.

The three fixtures collectively exercise:

- **`clean-categorical-edit/`** — the happy-path categorical
  edit. Validates that the auditor recognizes a well-formed
  categorical rule and approves it with `categorical` /
  `keep`.
- **`row-specific-patch-disguised-as-rule/`** — the auditor's
  primary defensive function. A "rule" whose stated condition
  is so narrow that only the original motivating row
  satisfies it. Validates the synthetic-rows test in §4
  and the `row-specific` / `generalize` recommendation
  shape.
- **`cross-iteration-contradiction/`** — the auditor's
  cross-iteration reasoning. An edit at iteration N
  contradicts a categorical rule that an earlier
  iteration's auditor approved. Validates §3 step 4
  (reading prior auditor reviews) and the `unclear` /
  `clarify` verdict shape.

Validation in Phase 2 step 6 is **manual**: read each
fixture, walk through what this agent doc says it would do,
verify the agent produces something equivalent to
`expected_review.md`, and update the agent doc if gaps
surface. The Phase 4 validation harness will mechanize this
later. The fixtures are also the regression surface for
future PRs that touch this agent.

**No fixture references real source-project data**
(`DESIGN.md` §7.2). All examples are generic shapes —
binary or multi-class classifications with synthetic-but-
plausible row contents and rule edits.
