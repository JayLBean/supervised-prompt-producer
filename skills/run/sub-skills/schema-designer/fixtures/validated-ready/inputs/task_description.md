# Fixture 2 — validated happy path (Path 2, → ready)

A canonical Path 2 case. The user is a pydantic native and
brings a complete pydantic model that already describes the
task's output. `schema-designer` validates, calibrates per-field
intent, and renders into the user's chosen surface format
without adding interpretation.

This fixture exercises Path 2's "user has a complete artifact"
precondition. If `schema-designer` re-derives the schema rather
than treating the artifact as the input, Path 2's contract is
violated.

---

## What the user types when invoking the (forthcoming) gate

```
/spp-init ticket-triage
```

(See fixture 1 for the forward-looking note on slash-command
notation.)

## What the user says to the designer

> I already have the schema. Here's the pydantic model — please
> just validate it and render in YAML. I want this exact shape
> in production; I'm not looking for refinement.

The user pastes the model (see `inputs/user_pydantic_model.py`
below) and confirms YAML as the surface format.

The user articulates each field's intent during the calibration
walk:

> - `queue` — which of the three operational queues the ticket
>   routes to. Billing and abuse have dedicated triagers;
>   everything else is general.
> - `urgency` — the priority tier the queue picks the ticket
>   off in. Three tiers; high gets paged.
> - `requires_human_review` — true when the model's autonomous
>   routing falls below confidence; the ticket goes to a human
>   reviewer regardless of queue.

---

## Repo context

### `pyproject.toml` excerpt

```toml
[project]
name = "support-triage"
dependencies = [
  "pydantic>=2.5",
  "openai>=1.50",
  "pyyaml>=6.0",
]
```

The user's pydantic 2.5+ dep means `model_json_schema()`
exports natively to JSON Schema 2020-12.

### No prior `spp/` artifacts

This is the user's first `spp` task in the repo.

---

## Notes for fixture review

This fixture's `consultation_notes.md` describes what
`schema-designer` should do given the pydantic input. The
`expected_review.md` is the rendered output (verdict + schema
+ note) the sub-skill should produce.
