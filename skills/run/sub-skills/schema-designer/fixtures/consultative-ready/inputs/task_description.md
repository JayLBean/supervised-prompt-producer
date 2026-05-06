# Fixture 1 — consultative happy path (Path 1, → ready)

A canonical Path 1 case. The user has prose, a CSV they reference,
and no machine-readable schema artifact. The designer reads the
repo, builds a strawman, the user refines, and the rendered
OUTPUT_SCHEMA passes both validation layers cleanly.

This fixture exercises the on-spec Path 1 shape. If
`schema-designer` fails this fixture, every later fixture's path
selection cannot be trusted.

---

## What the user types when invoking the (forthcoming) gate

```
/spp-init product-listing-extraction
```

(Verbatim slash-command notation is forward-looking — the gate
slot has not yet been wired into a phase. Read the invocation as
"the designer agent reaches the schema-design gate during the
consultation that this fixture is the input to.")

## What the user says to the designer when prompted

> I want to pull product attributes out of marketplace listings
> for downstream search ranking. Each row needs: the cleaned
> title, the price as a number, the marketplace category bucket
> (about a dozen of those — they're fixed), and the brand name
> if we can extract one. Sometimes brand isn't extractable; we
> need to encode that case explicitly so the downstream ranker
> doesn't treat "missing" as "unknown brand vs no brand."

After the designer presents a strawman with `category` as a
12-value enum, the user adds:

> One more — `health` is a 13th category we ship, I forgot to
> mention it. Add that.

After the designer adds it and re-renders, the user accepts.
> Looks right. YAML is fine — we use YAML elsewhere in the repo.

---

## Repo context the designer discovers on its scan

(This is what `agents/designer.md` §3 reading checklist would
surface.)

### File tree (relevant subset)

```
.
├── README.md
├── pyproject.toml
├── data/
│   └── listings.csv          (4,200 rows; columns: id, title,
│                               body, seller_id, source_marketplace,
│                               raw_category)
├── src/
│   └── ranker/
└── tests/
```

### `data/listings.csv` notes

Free-text `title` and `body` columns. `raw_category` has 13
distinct values: `electronics, apparel, home, toys, beauty,
sports, books, automotive, garden, pet, grocery, health, other`.
The 13th (`health`) was added in a recent merchandising launch.

### `pyproject.toml` excerpt

```toml
[project]
name = "marketplace-ranker"
dependencies = [
  "openai>=1.50",
  "pandas>=2.2",
  "pyyaml>=6.0",
]
```

The `pyyaml` dependency is a soft signal toward YAML surface
format; the user confirms.

### No prior `spp/` artifacts

This is the user's first `spp` task in the repo.

---

## Notes for fixture review

This fixture's `consultation_notes.md` describes what
`schema-designer` should do given this input. The
`expected_review.md` is the rendered output (verdict + schema +
note) the sub-skill should produce after the consultation walk
completes.

The fixture is exercised manually: read this file, walk
`consultation_notes.md` against `SKILL.md`'s protocol, confirm
`expected_review.md` matches what the protocol would produce.
The Phase 4 validation harness will mechanize this walk in a
later v0.2 bucket.
