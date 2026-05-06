# Fixture 3 — mechanical violation (Path 2, → not-ready)

A Path 2 case where the user's complete artifact passes parser
validation but violates a mechanical rule that the parser does
not catch on its own — specifically, an enum field rendered as
`"type": "string"` with no `enum` clause, contradicting the
user's articulated intent during calibration.

This fixture exercises the §3.4 mechanical layer's
disqualification authority: a mechanically-failing schema
returns `not-ready` regardless of how reasonable it looks. It
also demonstrates the override mechanism the integration PR
(bucket 4) will wire into the runner.

---

## What the user types when invoking the (forthcoming) gate

```
/spp-init content-moderation
```

## What the user says to the designer

> I have a JSON Schema already, here it is. Render in JSON; we
> use JSON throughout.

The user pastes the schema (see `inputs/user_json_schema.json`).
During the calibration walk, the user articulates the
`category` field's intent:

> `category` should be one of `harassment`, `spam`, `csam`,
> `violence`, `self-harm`, or `other-violation`. Six values,
> the moderation team has been operating with these for
> 18 months.

The articulation **contradicts** the schema, which has
`category` as a freeform string.

---

## Repo context

### `pyproject.toml` excerpt

```toml
[project]
name = "moderation-router"
dependencies = [
  "openai>=1.50",
]
```

JSON dependencies; the user picks JSON for the surface format.

### No prior `spp/` artifacts

This is the user's first `spp` task in the repo.

---

## Notes for fixture review

This fixture demonstrates `schema-designer`'s mechanical-
dominance: even when judgment-layer rules would otherwise pass,
a mechanical violation forces `not-ready`. The fixture also
exercises the `schema-not-ready override` literal-substring
mechanism — the second half of `expected_review.md` shows what
the user would record in `plan.md` §11 if they chose to ship
the schema as-is rather than fixing it.
