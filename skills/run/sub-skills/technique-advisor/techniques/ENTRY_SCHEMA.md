# Technique catalog entry contract

Every file in this directory (`techniques/<id>.yaml`) is one prompting
technique the `technique-advisor` sub-skill can recommend. This document
is the contract each entry conforms to. It is the reference a
contributor adding a technique follows (see `../SKILL.md` §6) and the
shape the entry linter checks.

A catalog entry is **reference material**, not executable code: it tells
the discrepancy stage which failure pattern this technique addresses and
what to recommend, and tells a human what adopting it entails. Entries
never carry row content, labels, or scores (`../SKILL.md` §5).

---

## Required fields

| Field | Type | Meaning |
|---|---|---|
| `id` | string (kebab-case) | Stable identifier; must equal the filename stem. |
| `name` | string | Human-readable technique name. |
| `symptom` | string | The detectable failure pattern — an articulable, checkable property of a field's failure cluster that indicates this technique applies. Not a metric threshold. |
| `recommendation` | string | The categorical suggestion surfaced to the user. About a class of rows / a field's behavior, never specific rows. |
| `output_form` | string | The runner-recognized field shape adopting the technique produces (e.g. `per_label_binary`). Use an existing form where the technique fits one. |
| `runner_support` | string | What `inference.py` parse + `eval.py` / metric scoring the `output_form` needs; `none` if it already runs on the current runner. |
| `citation` | string | The source establishing the technique (paper / canonical reference / in-repo asset finding). No uncited folklore. |

All seven fields are required and non-empty. `id` must be unique across
the catalog and match the filename.

---

## Eligibility rules (enforced by review, per `../SKILL.md` §5)

An entry is **catalog-eligible** only if:

1. **The `symptom` is an articulable failure-class property** — checkable
   by a reader against a discrepancy cluster, not "the score is low" and
   not a per-row condition.
2. **The `recommendation` is categorical** — evaluable without exposing
   specific rows to any stage denied them. It references a field and a
   class of failures.
3. **The `output_form` does not change the locked six-section prompt
   structure** (`DESIGN.md` §7.1.1 invariant #12). A technique that adds
   a prompt section, a reasoning field, or multi-shot example pairs is a
   design pass, not a catalog entry.
4. **Adding it changes no stage allow-list and no verdict gate.** The
   advisor is consultative; an entry that requires new information access
   for any cognitive stage is not eligible.

---

## Example entry shape

```yaml
id: example-technique
name: Example Technique
symptom: >
  A one-sentence, checkable description of the failure cluster shape that
  indicates this technique applies — stated about a field and a class of
  rows, not a metric value.
recommendation: >
  The categorical suggestion to surface to the user: what to change about
  how the field is asked for, phrased about the class, not specific rows.
output_form: existing_or_new_form_name
runner_support: >
  What parse/score the output_form needs, or "none" if the current runner
  already handles it.
citation: >
  Author/source establishing the technique (paper, canonical reference,
  or in-repo asset finding with a path).
```

YAML, 2-space indent (`CLAUDE.md` §2). Use block scalars (`>`) for the
prose fields so lines wrap within the 100-char limit.
