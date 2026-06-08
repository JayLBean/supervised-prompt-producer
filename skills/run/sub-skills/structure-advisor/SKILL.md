# structure-advisor

A sub-skill of `spp` that maps a checkable task property to a **structural**
change — a change to *how the prompt is run* rather than what shape its
output takes — and recommends that structure to the user. Consulted by the
**discrepancy** stage during `/spp-loop` (`spp-loop.md` §4 step 8) — wired in
a later bucket of the v0.9 arc — the same step that consults
`technique-advisor`, and read by users curious why a structure was suggested
for their task.

`structure-advisor` is the **structural sibling** of v0.5's
`technique-advisor` (`DESIGN.md` §7.1.10): same machinery (an extensible
catalog, an entry contract, symptom matching, a categorical recommendation),
a different axis of advice. Where `technique-advisor` suggests *output-form*
changes (per-label binary, gated boolean), `structure-advisor` suggests
*structural* ones (how input rows are packed into a call). Like
`metric-design` and `technique-advisor`, it is **consultative and ungated**:
it advises and its recommendation is recorded, but it does not block a gate
and it never edits a prompt, schema, or plan itself.

A note on artifact shape, as the other sub-skill docs carry: `spp` has
**phases** (orchestration, gate enforcement), **agents** (judgment with
structurally distinct information access), and **sub-skills** like this one
(opinionated reference material that informs decisions). A sub-skill is not a
chat and not invoked as a conversational entity. A reader should come away
able to make the call themselves; when follow-up is needed, the stage that
consults this doc (the discrepancy subagent) does it.

---

## 1. Identity and scope

`structure-advisor` makes one decision well: **given a task's properties,
which structural change (if any) is the kind that fits it, and what is the
categorical recommendation to surface to the user?**

The structures are not hardcoded here. They live in a **catalog** —
`structures/*.yaml`, one structured entry per structure — that the project
grows over time. The sub-skill's job is to (a) define the entry contract,
(b) hold the procedure for matching a task property to a catalog entry, and
(c) specify what the resulting recommendation looks like. Adding a structure
is **adding a catalog entry** (see §6, "How to add a structure"), not
changing this procedure or the loop.

This is deliberate. `spp` ships open-source; a contributor who finds a
structural change that helps a recurring task class should be able to extend
the advisor by adding a reviewable entry — without touching the per-stage
information-isolation core (`DESIGN.md` §4.2).

**In scope:**

- **The catalog entry contract** — the structured shape every structure
  entry conforms to (§3.1).
- **Symptom matching** — the procedure the discrepancy stage uses to decide
  whether a task's properties match an entry's `symptom` (§3.2).
- **The recommendation** — the categorical suggestion surfaced to the user,
  and what it does and does not contain (§3.3).
- **The seed catalog** — the one asset-validated entry seeded in v0.9: batch
  I/O (§4).

**Out of scope:**

- **Applying a structure.** The advisor recommends; the **user** adopts a
  structure by revising `plan.md` (`plan.md` §11 revision log). Nothing here
  auto-edits an artifact.
- **Multi-prompt / decomposition.** Splitting a classifier into a pipeline
  turns the runner into a prompt-graph and extends the per-stage isolation
  contract (per-node failure attribution). That is the **v0.10** arc
  (`DESIGN.md` §7.1.2), not a v0.9 catalog entry, and it must reconcile with
  the README's manual feature-group-splitting guidance.
- **Structures that add or remove a prompt section.** A structural change
  may alter the *content* of the input and `<output_format>` sections; one
  that adds a section is BREAKING against the six-section structure
  (`DESIGN.md` §7.1.1 invariant #12) and needs its own design pass, not a
  catalog entry.
- **A verdict gate.** `structure-advisor` does not gate. Its output is a
  recommendation recorded in `discrepancy_analysis.md`, not a pass/blocker.

**The cross-skill rule** that governs every entry (full statement in §5): a
structure recommendation is a **categorical statement surfaced to the
human**, never a new data path; and any structure that co-locates rows in
one call must preserve **per-row independence** so the score stays honest.

---

## 2. The decision the sub-skill helps make

`technique-advisor` is **failure-driven**: it fires on evidence of a real
gap in a field's predictions. `structure-advisor` is **task-property-driven**:
a structural change is the right move because of what the task *is*, not
because particular rows failed. The two are consulted at the same step, but
they read different signals.

During `/spp-loop`, the discrepancy stage already reads `plan.md` §2 (the
task and label shape) and the run's **observed** cost/latency from
`results.json` — per-row `tokens_used` / `latency_ms` and the run summary's
`total_tokens` / `total_latency_ms` — both already on its allow-list.
`structure-advisor` is consulted with those signals. **Row-independence** —
the precondition that makes a structural change *safe* — is not read from a
field; it is surfaced as a precondition for the user to confirm and then
verified empirically by the runner's batch-invariance check. The decision is:

> Do this task's properties match a catalogued structure's symptom — and if
> so, what structure does the catalog recommend, how is that recommendation
> phrased to the user, and what guard keeps the score honest?

The output is one of:

- **A structure recommendation** — the matched entry's `recommendation`,
  naming the task property observed and the structure, recorded in
  `discrepancy_analysis.md` and surfaced to the user at the iteration's HITL
  gate.
- **No recommendation** — the task's properties do not match any catalogued
  symptom; the discrepancy stage proceeds with ordinary reasoning. A
  non-match is the common case and is not a failure of the advisor.

The recommendation is **advisory**. The user decides whether to adopt the
structure (a `plan.md` §11 revision) or to keep the current run shape. The
advisor never makes the change.

---

## 3. The decision procedure

### 3.1 The catalog entry contract

Each structure is one file, `structures/<id>.yaml`, conforming to the
contract documented in [`structures/ENTRY_SCHEMA.md`](structures/ENTRY_SCHEMA.md).
Every entry carries these fields:

- **`id`** — kebab-case stable identifier (matches the filename stem).
- **`name`** — human-readable structure name.
- **`symptom`** — the checkable trigger that indicates this structure
  applies: an allow-listed signal (observed cost/latency in `results.json`,
  task shape in `plan.md` §2) or a user-confirmed precondition — not a
  per-row failure and not a metric value.
- **`recommendation`** — the categorical suggestion text surfaced to the
  user, written about the task and how it is run, never about specific rows.
- **`structure_form`** — the runner-recognized structural shape adopting it
  produces (e.g. `batched_io`), with a one-line gloss of the runner change
  it implies.
- **`runner_support`** — what `inference.py` execution/parsing the
  `structure_form` requires; `none` if it already runs on the current runner.
- **`independence`** — how the structure preserves per-row independence and
  the guard the runner applies; the load-bearing field for any structure
  that co-locates rows in one call (§5).
- **`citation`** — the source establishing the structure. No uncited
  folklore; this is the repo's quality bar.

### 3.2 Symptom matching

The discrepancy subagent, reading the run's signals (the observed
cost/latency in `results.json` and the task shape in `plan.md` §2), checks
each catalog entry's `symptom`:

1. **Identify the relevant signals** — the observed per-row cost/latency from
   `results.json` and the label shape from `plan.md` §2 (both allow-listed).
   Row-independence is a precondition the recommendation surfaces for the
   user to confirm, not a signal read here.
2. **Compare against each entry's `symptom`** — does the task match the
   articulable property the entry describes? The match is on the *task's
   shape*, not a metric value.
3. **On a match, take that entry's `recommendation`** and its
   `independence` guard. If more than one entry matches, surface each — they
   are not mutually exclusive; the user chooses.
4. **On no match, recommend nothing.** Do not stretch a symptom to fit; a
   forced recommendation is worse than none.

Matching is judgment, not a regex — the `symptom` field is written to be
checkable by a reader, and the discrepancy subagent applies it the way the
auditor applies "categorical vs row-specific."

### 3.3 The recommendation

A recommendation names: the **task property observed** (in categorical
terms), the **structure**, the **structure_form** adopting it would produce,
and the **independence guard** that keeps the score honest. It is recorded
in `discrepancy_analysis.md` and surfaced to the user at the gate.

What a recommendation **must not** contain: specific row contents, labels,
or any per-row data. It is a statement about the task and how it is run — the
same categorical discipline the auditor's verdicts follow. The
recommendation crosses to the user; row content does not ride along (§5).

---

## 4. The seed catalog (v0.9)

v0.9 seeds one structure, validated against real `spp` runs (the hair-loss
multi-field annotation work, whose v6 generation ran batched I/O; see
`DESIGN.md` §7.2, findings only). The entry file ships as
`structures/batch-io.yaml` with the catalog bucket; its shape:

### Batch I/O — `structures/batch-io.yaml`

- **Symptom:** the run shows **high per-row cost/latency** with one call per
  row (observed in `results.json` — `tokens_used` / `latency_ms`), so the
  shared prompt is paid for once per row. Batch I/O applies when the task's
  rows are **mutually independent** — a precondition the user confirms, then
  verified empirically by the runner's batch-invariance check.
- **Recommendation:** send multiple input rows per inference call (a row
  array in, a results array out) to amortize the shared prompt across rows,
  cutting cost and latency — provided per-row independence is preserved.
- **`structure_form`:** `batched_io`. Changes the *content* of the input and
  `<output_format>` sections (a row array and a `results` array); adds no
  section, so the six-section structure (#12) is preserved.
- **Runner support:** `inference.py` packs N rows per call and parses the
  results array back to per-row predictions, with the batch-invariance check
  (next).
- **Independence (load-bearing):** a model that can attend to sibling rows
  in one call could decide a row's label from another's content, inflating
  dev/test scores above deployed single-row behavior. The runner applies the
  **batch-invariance check** — a sampled batched-vs-single-row comparison;
  divergence beyond threshold flags contamination and the runner falls back
  to single-row scoring — and records the result with the adoption in
  `plan.md` §11.

---

## 5. The cross-skill constraint — not a data path, not a cross-row channel

This is the load-bearing rule, and the one a contributor adding an entry is
most likely to break by accident. It has two parts: a recommendation is not a
data path, and a batch is not a back-channel between rows.

**Part 1 — a recommendation is a categorical statement, not a data path**
(`DESIGN.md` §4.2, §7.1.10). Consulting the catalog:

- **adds no input to any stage's allow-list.** The discrepancy subagent
  consults this reference material; it gains no new artifact access. The
  recommendation it writes is derived from signals it already legitimately
  sees — the observed cost/latency in `results.json` and the task shape in
  `plan.md` §2 — and from row-independence stated as a precondition for the
  user to confirm, never from a new field.
- **surfaces no row content to the rule-edit subagent.** The rule-edit stage
  still receives no row content under any path (invariant #3). A
  recommendation references the task and a structure — never rows.
- **surfaces no score to the auditor.** The auditor stays score-blind
  (invariant #2). A structure recommendation is not a back-channel for
  scores or row data.
- **never auto-applies.** The advisor does not edit the prompt, schema, or
  plan. The user adopts a structure via a `plan.md` §11 revision, which every
  downstream phase re-reads (the `plan.md`-as-contract rule, invariant #15).

**Part 2 — a batched call must not become a back-channel between rows**
(invariant #13). A structure that co-locates input rows in one inference
call must preserve per-row independence: the dev/test score must reflect what
the deployed single-row prompt achieves, not a number a model lifted by
reading sibling rows. The guard is the **batch-invariance check** named in
the entry's `independence` field. Mechanical scoring is unchanged — the
metric still reads frozen baseline labels and compares them to parsed
predictions with the same model-agnostic functions — but a structure that
contaminates the predictions would make that honest metric measure the wrong
thing. An entry whose `independence` cannot be stated is **not
catalog-eligible**.

An entry whose `symptom` or `recommendation` can only be evaluated by
exposing specific rows to a stage that is denied them is likewise not
catalog-eligible. Symptoms are checkable task properties; recommendations are
categorical. If you cannot phrase an entry that way, it does not belong in
the catalog as written.

---

## 6. What the sub-skill outputs, and how to add a structure

### Output

When consulted, `structure-advisor` yields zero or more **structure
recommendations**, each: `{task_property_observed, structure_id,
structure_form, independence_guard}` in prose, recorded in the iteration's
`discrepancy_analysis.md` and surfaced to the user at the HITL gate. There is
no verdict and no gate.

### How to add a structure (the contributor path)

The catalog is meant to grow. To add a structure:

1. **Write the entry.** Add `structures/<id>.yaml` conforming to
   [`structures/ENTRY_SCHEMA.md`](structures/ENTRY_SCHEMA.md) — all eight
   fields, with a real `citation`.
2. **Check the cross-skill constraint (§5).** The `symptom` must be a
   checkable task property and the `recommendation` must be categorical. If
   the structure co-locates rows, its `independence` must name a guard that
   keeps the score honest (#13). If you cannot, the entry is not eligible.
3. **Add runner support if the `structure_form` is novel.** If the form is
   not one the runner already executes/parses, that support is its own change
   (`inference.py` execution + parse, plus any invariance guard), landed
   before or with the entry.
4. **Add a fixture.** A small example exercising the symptom →
   recommendation → adopted-form path end-to-end, mirroring the v0.9 seed
   fixture (including the invariance check where rows are co-located).
5. **Confirm the structural invariants.** Adding an entry must not change any
   stage allow-list, the six-section prompt structure (#12), or any verdict
   gate, and must not let a batched call carry information between rows into
   the score (#13). If a proposed structure would, it is a methodology change
   (a DESIGN pin + design discussion), not a catalog addition.

A structure that adds a prompt section, or that splits the classifier into a
multi-prompt pipeline, is **out of scope for the catalog** under v0.9's
§7.1.10 contract — the former needs its own design pass; the latter is the
v0.10 decomposition arc.

---

## Versioning

`structure-advisor` and its catalog are introduced in **v0.9** (`DESIGN.md`
§7.1.10), seeded with batch I/O. The sub-skill is consultative and ungated,
like `metric-design` and `technique-advisor`; it is **not** a fifth
`/`-command (invariant #20 holds). The catalog is designed to grow by
additive entry PRs (§6) without methodology changes.

Changes that **are** methodology-affecting (and need a DESIGN update +
`CHANGELOG.md` entry per `CLAUDE.md` §5): admitting a structure that changes
the six-section structure or adds the multi-prompt prompt-graph (the v0.10
arc); giving the advisor a verdict gate; wiring a recommendation to carry row
content or scores across a stage boundary; or admitting a row-co-locating
structure without a per-row-independence guard. The first is a design pass;
the rest must be rejected outright (they break §4.2 or #13).

---

## Cross-references

- `DESIGN.md` §7.1.10 — the v0.9 design pin this sub-skill realizes.
- `DESIGN.md` §7.1.2 — the roadmap; v0.10 carries the decomposition seed.
- `DESIGN.md` §4.2 — per-stage information isolation (the constraint §5
  Part 1 enforces).
- `skills/run/phases/spp-loop.md` §4 step 8 — the discrepancy stage that
  consults this sub-skill.
- `skills/run/sub-skills/technique-advisor/SKILL.md` — the output-form
  sibling whose structure this doc mirrors.
- `structures/ENTRY_SCHEMA.md` — the catalog entry contract.
