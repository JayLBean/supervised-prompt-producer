# technique-advisor

A sub-skill of `spp` that maps an observed failure pattern to a
prompting technique that addresses it, and recommends that technique to
the user. Read by the **discrepancy** stage during `/spp-loop`
(`spp-loop.md` §4 step 8) when it needs to decide whether a field's
failures match a known, fixable pattern, and by users curious why a
technique was suggested for their task.

`technique-advisor` follows the established sub-skill structure
(identity → decision → decision procedure → worked examples →
cross-skill constraint → output spec), the same shape `metric-design`,
`schema-designer`, `prompt-architect`, and `baseline-quality` use. Like
`metric-design`, it is **consultative and ungated**: it advises and its
recommendation is recorded, but it does not block a gate and it never
edits a prompt, schema, or plan itself.

A note on artifact shape, as the other sub-skill docs carry: `spp` has
**phases** (orchestration, gate enforcement), **agents** (judgment with
structurally distinct information access), and **sub-skills** like this
one (opinionated reference material that informs decisions). A sub-skill
is not a chat and not invoked as a conversational entity. A reader
should come away able to make the call themselves; when follow-up is
needed, the stage that consults this doc (the discrepancy subagent)
does it.

---

## 1. Identity and scope

`technique-advisor` makes one decision well: **given a field's observed
failure pattern, which prompting technique (if any) is the kind that
addresses it, and what is the categorical recommendation to surface to
the user?**

The techniques are not hardcoded here. They live in a **catalog** —
`techniques/*.yaml`, one structured entry per technique — that the
project grows over time. The sub-skill's job is to (a) define the entry
contract, (b) hold the procedure for matching an observed symptom to a
catalog entry, and (c) specify what the resulting recommendation looks
like. Adding a technique is **adding a catalog entry** (see §6, "How to
add a technique"), not changing this procedure or the loop.

This is deliberate. `spp` ships open-source; a contributor who finds a
prompting technique that fixes a recurring failure class should be able
to extend the advisor by adding a reviewable entry — without touching
the per-stage information-isolation core (`DESIGN.md` §4.2).

**In scope:**

- **The catalog entry contract** — the structured shape every technique
  entry conforms to (§3.1).
- **Symptom matching** — the procedure the discrepancy stage uses to
  decide whether observed failures match an entry's `symptom` (§3.2).
- **The recommendation** — the categorical suggestion surfaced to the
  user, and what it does and does not contain (§3.3).
- **The seed catalog** — the two asset-validated entries shipped in
  v0.5: per-label binary / one-vs-rest, and gated-boolean (§4).

**Out of scope:**

- **Applying a technique.** The advisor recommends; the **user** adopts
  a technique by revising `plan.md` / OUTPUT_SCHEMA (`plan.md` §11
  revision log). Nothing here auto-edits an artifact.
- **Techniques that change the locked prompt structure.** CoT as a
  dedicated reasoning section/field, multi-shot few-shot (more than one
  example pair), and anchored-CoT change `<output_format>` or the
  example-pair cardinality — BREAKING against the six-section structure
  (`DESIGN.md` §7.1.1 invariant #12). They are not catalog-eligible
  under v0.5's contract; admitting them needs its own design pass.
- **Plan-time / schema-shape-only suggestions.** v0.5's advisor is
  loop-time and failure-driven (§2). A technique is suggested on
  evidence of a real gap, not from schema shape before any run.
- **A verdict gate.** `technique-advisor` does not gate. Its output is a
  recommendation recorded in `discrepancy_analysis.md`, not a
  pass/blocker.

**The cross-skill rule** that governs every entry (full statement in
§5): a technique recommendation is a **categorical statement surfaced to
the human**, never a new data path. Consulting the catalog adds no input
to any stage's allow-list, surfaces no row content to the rule-edit
stage, and surfaces no score to the auditor.

---

## 2. The decision the sub-skill helps make

During `/spp-loop`, the discrepancy stage examines the rows a candidate
prompt got wrong and clusters them by shared property (`spp-loop.md` §4
step 8). Some failure clusters are **idiosyncratic** — they need a
specific rule edit. Others have a **recognizable shape** that a known
prompting technique is built to fix; for those, the better move is not
another hand-written rule but a change to how the field is *asked for*.

`technique-advisor` is consulted for the second case. The decision is:

> Does this field's failure cluster match a catalogued symptom — and if
> so, what technique does the catalog recommend, and how is that
> recommendation phrased to the user?

The output is one of:

- **A technique recommendation** — the matched entry's
  `recommendation`, naming the field, the symptom observed, and the
  technique, recorded in `discrepancy_analysis.md` and surfaced to the
  user at the iteration's HITL gate.
- **No recommendation** — the failures do not match any catalogued
  symptom; the discrepancy stage proceeds with ordinary rule-edit
  reasoning. A non-match is the common case and is not a failure of the
  advisor.

The recommendation is **advisory**. The user decides whether to adopt
the technique (a `plan.md` / OUTPUT_SCHEMA revision) or to keep
iterating with rule edits. The advisor never makes the change.

---

## 3. The decision procedure

### 3.1 The catalog entry contract

Each technique is one file, `techniques/<technique-id>.yaml`, conforming
to the contract documented in
[`techniques/ENTRY_SCHEMA.md`](techniques/ENTRY_SCHEMA.md). Every entry
carries these fields:

- **`id`** — kebab-case stable identifier (matches the filename stem).
- **`name`** — human-readable technique name.
- **`symptom`** — the detectable failure pattern: what in the
  discrepancy analysis indicates this technique applies. Stated as an
  articulable, checkable property of a field's failure cluster (not "the
  metric is low").
- **`recommendation`** — the categorical suggestion text surfaced to the
  user, written as a recommendation about a *class* of rows / a field's
  behavior, never about specific rows.
- **`output_form`** — the runner-recognized field shape that adopting
  the technique produces (e.g. `per_label_binary`), and a one-line gloss
  of the schema/prompt change it implies.
- **`runner_support`** — what `inference.py` parsing and `eval.py` /
  metric scoring the `output_form` requires; `none` if the form already
  runs on the current runner.
- **`citation`** — the source establishing the technique (paper,
  canonical reference, or an in-repo asset finding). No uncited
  folklore; this is the repo's quality bar.

### 3.2 Symptom matching

The discrepancy subagent, having clustered a field's failures, checks
each catalog entry's `symptom` against the cluster:

1. **Identify the field and the cluster's shared property** — the same
   clustering the discrepancy stage already produces.
2. **Compare against each entry's `symptom`** — does the cluster's
   shared property match the articulable pattern the entry describes?
   The match is on the *shape of the failure*, not the metric value.
3. **On a match, take that entry's `recommendation`.** If more than one
   entry matches, surface each — they are not mutually exclusive (a
   field can have both a default-attractor problem and a multi-label
   problem); the user chooses.
4. **On no match, recommend nothing.** Do not stretch a symptom to fit;
   a forced recommendation is worse than none.

Matching is judgment, not a regex — the `symptom` field is written to be
checkable by a reader, and the discrepancy subagent applies it the way
the auditor applies "categorical vs row-specific."

### 3.3 The recommendation

A recommendation names: the **field**, the **symptom observed** (in
categorical terms), the **technique**, and the **output_form** adopting
it would produce. It is recorded in `discrepancy_analysis.md` and
surfaced to the user at the gate.

What a recommendation **must not** contain: specific row contents,
labels, or any per-row data. It is a statement about a field and a class
of failures — the same categorical discipline the auditor's verdicts
follow. The recommendation crosses to the user; row content does not
ride along (§5).

---

## 4. The seed catalog (v0.5)

v0.5 ships two entries, both validated against real `spp` runs (the
hair-loss multi-field annotation work; see
[`spp-reference-harnesses`] usage in the runs, not reproduced here per
`DESIGN.md` §7.2). Full entries in `techniques/`.

### Per-label binary / one-vs-rest — `techniques/one-vs-rest.yaml`

- **Symptom:** a multi-select field underperforms (low set-overlap) and
  the failures show the model treating mutually-compatible labels as
  exclusive — picking one label where several apply, or dropping
  co-occurring labels.
- **Recommendation:** ask for each candidate label as an independent
  yes/no decision and union the positives, rather than one
  pick-the-set decision.
- **`output_form`:** `per_label_binary`.
- **Runner support:** parse per-label yes/no → union; score with
  `set_f1` (the existing multi-select metric).

### Gated-boolean — `techniques/gated-boolean.yaml`

- **Symptom:** a field with a catch-all / default value (e.g. `none`,
  `other`) shows that value, or a populated value, **systematically
  over-predicted** — the model defaults into the attractor when unsure
  rather than abstaining cleanly.
- **Recommendation:** introduce an is-addressed gate (a boolean) that
  must be true before the conditional sub-labels are populated, so
  "unsure" routes to gate=false instead of the attractor.
- **`output_form`:** `gated_per_label_binary` / `gated_single_select`.
- **Runner support:** parse the gate then the conditional sub-field;
  score the gate (boolean) and the sub-field (its own metric) per the
  field's `metric-design` choice.

---

## 5. The cross-skill constraint — a suggestion is not a data path

This is the load-bearing rule, and it is the one a contributor adding an
entry is most likely to break by accident.

A technique recommendation is a **categorical statement surfaced to the
human** (`DESIGN.md` §7.1.6). Consulting the catalog:

- **adds no input to any stage's allow-list.** The discrepancy subagent
  consults this reference material; it gains no new artifact access. The
  recommendation it writes is derived from failures it already legitimately
  sees (`DESIGN.md` §4.2).
- **surfaces no row content to the rule-edit subagent.** The rule-edit
  stage still receives no row content under any path (invariant #3). A
  recommendation references a field and a symptom class — never rows.
- **surfaces no score to the auditor.** The auditor stays score-blind
  (invariant #2). A technique recommendation is not a back-channel for
  scores or row data.
- **never auto-applies.** The advisor does not edit the prompt, schema,
  or plan. The user adopts a technique via a `plan.md` §11 revision,
  which every downstream phase re-reads (the `plan.md`-as-contract rule,
  invariant #15).

An entry whose `symptom` or `recommendation` can only be evaluated by
exposing specific rows to a stage that is denied them is **not
catalog-eligible**. Symptoms are articulable properties of a failure
class; recommendations are categorical. If you cannot phrase an entry
that way, it does not belong in the catalog as written.

---

## 6. What the sub-skill outputs, and how to add a technique

### Output

When consulted, `technique-advisor` yields zero or more **technique
recommendations**, each: `{field, symptom_observed, technique_id,
output_form}` in prose, recorded in the iteration's
`discrepancy_analysis.md` and surfaced to the user at the HITL gate.
There is no verdict and no gate.

### How to add a technique (the contributor path)

The catalog is meant to grow. To add a technique:

1. **Write the entry.** Add `techniques/<technique-id>.yaml` conforming
   to [`techniques/ENTRY_SCHEMA.md`](techniques/ENTRY_SCHEMA.md) — all
   six fields, with a real `citation`.
2. **Check the cross-skill constraint (§5).** The `symptom` must be an
   articulable property of a failure class and the `recommendation` must
   be categorical — evaluable without exposing specific rows to a stage
   denied them. If not, the entry is not eligible.
3. **Add runner support if the `output_form` is novel.** If the form is
   not one the runner already parses/scores, that support is its own
   change (`inference.py` parse + `eval.py` / metric scoring), landed
   before or with the entry. Reuse an existing `output_form` where the
   technique fits one.
4. **Add a fixture.** A small example exercising the symptom →
   recommendation → adopted-form path end-to-end, mirroring the v0.5
   seed-entry fixtures.
5. **Confirm the structural invariants.** Adding an entry must not change
   any stage allow-list, the six-section prompt structure, or any
   verdict gate. If a proposed technique would, it is a methodology
   change (a DESIGN pin + design discussion), not a catalog addition.

A technique that changes the locked prompt structure (a new section, a
reasoning field, multi-shot examples) is **out of scope for the catalog**
under v0.5's §7.1.6 contract — it needs its own design pass, not a
catalog entry.

---

## Versioning

`technique-advisor` and its catalog are introduced in **v0.5**
(`DESIGN.md` §7.1.6). The sub-skill is consultative and ungated, like
`metric-design`; it is **not** a fifth `/`-command (invariant #20
holds). The two seed entries (one-vs-rest, gated-boolean) are the
catalog's v0.5 contents; the catalog is designed to grow by additive
entry PRs (§6) without methodology changes.

Changes that **are** methodology-affecting (and need a DESIGN update +
`CHANGELOG.md` entry per `CLAUDE.md` §5): admitting a technique that
changes the six-section structure; giving the advisor a verdict gate;
wiring a recommendation to carry row content or scores across a stage
boundary. The first must be rejected as a catalog entry (it is a design
pass); the latter two must be rejected outright (they break §4.2).

---

## Cross-references

- `DESIGN.md` §7.1.6 — the v0.5 design pin this sub-skill realizes.
- `DESIGN.md` §4.2 — per-stage information isolation (the constraint §5
  enforces).
- `skills/run/phases/spp-loop.md` §4 step 8 — the discrepancy stage that
  consults this sub-skill.
- `skills/run/sub-skills/metric-design/SKILL.md` — the consultative,
  ungated sibling whose structure this doc mirrors; the `output_form`
  field connects to its per-field metric choices.
- `techniques/ENTRY_SCHEMA.md` — the catalog entry contract.
