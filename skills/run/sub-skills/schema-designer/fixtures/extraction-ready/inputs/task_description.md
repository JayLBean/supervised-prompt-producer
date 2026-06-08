# Fixture 5 — extraction happy path (Path 1, → ready)

A canonical extraction case (`TASK_MODE = extraction`; v0.10,
`DESIGN.md` §7.1.11). The user wants a variable-cardinality set of
items pulled out of each input — not a fixed label or a fixed object
of fields. The designer records `TASK_MODE = extraction` during
task-mode identification, then renders an item-array OUTPUT_SCHEMA
that passes both validation layers, including the v0.10 mechanical
rule 8 (`TASK_MODE` / schema-shape consistency).

This fixture exercises the on-spec extraction path. If
`schema-designer` renders a fixed object (or a bare enum) for an
extraction task, rule 8 should fail it; this fixture is the positive
case that confirms the consistent shape passes.

---

## What the user types when invoking the (forthcoming) gate

```
/spp-init support-email-entity-extraction
```

(Verbatim slash-command notation is forward-looking — read it as
"the designer agent reaches the schema-design gate during the
consultation that this fixture is the input to.")

## What the user says to the designer when prompted

During task-mode identification the designer asks: "for a single
email, is the answer one choice from a fixed list, or an open-ended
set of things found in the text?" The user answers:

> An open-ended set. Pull every product mention and every
> organization name out of the email body — there can be zero, one,
> or many of each. I need the exact text plus where it appears
> (character offsets) so the UI can highlight it.

So `TASK_MODE = extraction` is recorded. During §5.1's extraction
reframe, the designer establishes:

> One item is one contiguous mention. If "Acme" and "Acme Corp"
> both appear, extract the longest contiguous mention at each
> location, not nested sub-spans. A row with no product or org
> mentions yields an empty list — that is a valid answer, not a
> failure.

The user picks YAML and accepts after the designer renders the
item-array strawman.

---

## Repo context the designer discovers on its scan

(What `agents/designer.md` §3 reading checklist would surface.)

### File tree (relevant subset)

```
.
├── README.md
├── pyproject.toml
├── data/
│   └── emails.csv            (3,100 rows; columns: id, subject,
│                              body, received_at)
├── src/
│   └── highlighter/
└── tests/
```

### `data/emails.csv` notes

Free-text `body` column. The downstream highlighter UI consumes
character offsets into `body`, which is why the schema carries
`start` / `end` rather than text-only items.

### `pyproject.toml` excerpt

```toml
[project]
name = "support-highlighter"
dependencies = [
  "openai>=1.50",
  "pandas>=2.2",
  "pyyaml>=6.0",
]
```

### No prior `spp/` artifacts

This is the user's first `spp` task in the repo.

---

## Notes for fixture review

This fixture's `consultation_notes.md` describes what
`schema-designer` should do given this input. The
`expected_review.md` is the rendered output (verdict + schema +
note) the sub-skill should produce after the consultation walk.

The fixture is exercised manually: read this file, walk
`consultation_notes.md` against `SKILL.md`'s protocol, confirm
`expected_review.md` matches what the protocol would produce.
