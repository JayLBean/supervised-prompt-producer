# Fixture 4 — judgment violation (Path 2, → revise)

A Path 2 case where the user's complete artifact is
mechanically valid but fires multiple judgment-layer rules:
non-exhaustive enums, a vague `info` field name, and missing
borderline examples. The verdict is `revise` (not `not-ready`)
because none of the violations is severe enough to be
categorically disqualifying — the schema *describes* a task,
just not the right one.

This fixture exercises the §3.5 judgment layer's gradation
authority and the `revise` verdict's softer override mechanism
(no literal-substring requirement; just a §11 entry mentioning
`schema-designer`).

---

## What the user types when invoking the (forthcoming) gate

```
/spp-init issue-categorization
```

## What the user says to the designer

> I drafted this last week for a public bug-tracker
> classification task. Render in YAML, please.

The user pastes the schema (see `inputs/user_yaml_schema.yaml`).
During calibration:

> - `type` — bug, feature, or question. We'll route from
>   there.
> - `severity` — low or high. Maybe more later, this is what
>   we're starting with.
> - `info` — extra context the labeler thought was relevant.

The articulations surface the judgment-layer issues:

- `type`'s enum is missing `task` and `documentation` — common
  bug-tracker categories the user did not enumerate. The user
  acknowledges these exist but hasn't added them.
- `severity`'s two-tier enum collapses an inherently 3+ tier
  scale; the user's "maybe more later" hints at incompleteness.
- `info` is a shape, not a meaning — the user cannot articulate
  a single role for the field; it's a catch-all.

---

## Repo context

### `pyproject.toml` excerpt

```toml
[project]
name = "issue-router"
dependencies = [
  "pyyaml>=6.0",
  "openai>=1.50",
]
```

### No prior `spp/` artifacts

This is the user's first `spp` task in the repo.

---

## Notes for fixture review

This fixture demonstrates the judgment-layer's per-rule
findings discipline: each violation is named explicitly, with
a corrective action that lets the user act without re-deriving
the finding. The verdict is `revise` because the schema is
mechanically usable; the user can choose to fix the issues
(refine the enums, rename or remove `info`) and re-invoke for
`ready`, or proceed with a §11 acknowledgement that mentions
`schema-designer` (no literal-substring requirement).
