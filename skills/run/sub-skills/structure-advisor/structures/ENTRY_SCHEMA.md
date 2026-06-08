# Structure catalog entry contract

Every file in this directory (`structures/<id>.yaml`) is one **structural**
change — a change to *how the prompt is run* rather than what shape its
output takes — that the `structure-advisor` sub-skill can recommend. This
document is the contract each entry conforms to. It is the reference a
contributor adding a structure follows (see `../SKILL.md` §6) and the shape
the entry linter checks.

A catalog entry is **reference material**, not executable code: it tells the
discrepancy stage which task property this structure addresses and what to
recommend, and tells a human what adopting it entails. Entries never carry
row content, labels, or scores (`../SKILL.md` §5).

This contract is the structural sibling of `technique-advisor`'s
[`ENTRY_SCHEMA`](../../technique-advisor/techniques/ENTRY_SCHEMA.md): the
same review discipline, with one added required field — `independence` —
because a structural change can place multiple input rows in one inference
call, and that is the one way a structure can quietly invalidate the score.

---

## Required fields

| Field | Type | Meaning |
|---|---|---|
| `id` | string (kebab-case) | Stable identifier; must equal the filename stem. |
| `name` | string | Human-readable structure name. |
| `symptom` | string | The checkable trigger that indicates this structure applies. From an allow-listed signal (observed cost/latency in `results.json`, task shape in `plan.md` §2) or a user-confirmed precondition (e.g. row-independence). Not a per-row failure and not a metric threshold. |
| `recommendation` | string | The categorical suggestion surfaced to the user. About how the task is run, never about specific rows. |
| `structure_form` | string | The runner-recognized structural shape adopting it produces (e.g. `batched_io`). Changes how the runner executes and how the input/output payload is packed — not which prompt sections exist. |
| `runner_support` | string | What `inference.py` execution + parsing the `structure_form` needs; `none` if it already runs on the current runner. |
| `independence` | string | How the structure preserves **per-row independence**, and the guard the runner applies. Required and non-trivial for any structure that co-locates multiple input rows in one inference call (name the contamination-safe batching rule and/or the batch-invariance check). Use `n/a — one row per call` only for structures that never co-locate rows. |
| `citation` | string | The source establishing the structure (paper / canonical reference / in-repo asset finding). No uncited folklore. |

All eight fields are required and non-empty. `id` must be unique across the
catalog and match the filename.

---

## Eligibility rules (enforced by review, per `../SKILL.md` §5)

An entry is **catalog-eligible** only if:

1. **The `symptom` is checkable** — from an allow-listed signal (observed
   cost/latency in `results.json`, task shape in `plan.md` §2) or a
   user-confirmed precondition (e.g. row-independence). Not "the score is
   low" and not a per-row condition. A structural change is driven by what
   the run/task *is*, not by which rows failed.
2. **The `recommendation` is categorical** — evaluable without exposing
   specific rows to any stage denied them. It references the task and the
   structure, never specific rows.
3. **`independence` holds for #13.** Any structure that co-locates rows in
   one call must specify a per-row-independence guard — contamination-safe
   batching and/or the **batch-invariance check** (a sampled
   batched-vs-single-row comparison with single-row fallback, recorded in
   `plan.md` §11) — so dev/test scores stay faithful to deployed single-row
   behavior (`DESIGN.md` §7.1.1 invariant #13). An entry that cannot is not
   eligible.
4. **The `structure_form` does not change the locked six-section prompt
   structure** (`DESIGN.md` §7.1.1 invariant #12). A structure may change
   the *content* of the input and `<output_format>` sections (e.g. a row
   array and a results array) but must add or remove no section. A change
   that adds a section is a design pass, not a catalog entry.
5. **Adding it changes no stage allow-list and no verdict gate.** The
   advisor is consultative; an entry that requires new information access
   for any cognitive stage is not eligible.

---

## Example entry shape

```yaml
id: example-structure
name: Example Structure
symptom: >
  A one-sentence, checkable trigger — an allow-listed signal (observed
  cost/latency in results.json, task shape in plan.md §2) or a user-confirmed
  precondition (e.g. row-independence). Not a metric value, not a per-row
  condition.
recommendation: >
  The categorical suggestion to surface to the user: what to change about how
  the task is run, phrased about the task, not specific rows.
structure_form: existing_or_new_form_name
runner_support: >
  What execution/parse the structure_form needs, or "none" if the current
  runner already handles it.
independence: >
  How per-row independence is preserved and which guard the runner applies
  (e.g. the batch-invariance check), or "n/a — one row per call".
citation: >
  Author/source establishing the structure (paper, canonical reference, or
  in-repo asset finding with a path).
```

YAML, 2-space indent (`CLAUDE.md` §2). Use block scalars (`>`) for the prose
fields so lines wrap within the 100-char limit.
