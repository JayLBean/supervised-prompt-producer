# preprocess

A v0.6 sub-skill of `spp` that turns a user's **raw input data** into
spp's **canonical `baseline.csv`** by examining the data once and
authoring a deterministic, human-reviewed `preprocess.py`. It is the
front gate of `/spp-baseline`: every later phase operates on one known
shape, so no downstream stage has to re-accommodate arbitrary column
names, split fields, or missing identifiers.

This is the sixth sub-skill in `spp` (peer to `schema-designer`,
`metric-design`, `baseline-quality`, `prompt-architect`, and
`technique-advisor`). Like `schema-designer` it both *produces* an
artifact and *guards a gate* — but the artifact here is an executable
script, and the load-bearing rule is that **the sub-skill writes the
script; it never transforms rows itself.** The design contract this
sub-skill realizes is `DESIGN.md` §7.1.7.

A note on artifact shape before reading further. `spp` has three kinds
of artifact: **phases** (orchestration and gate enforcement; the
user-facing `/`-commands), **agents** (judgment with structurally
isolated information access), and **sub-skills** like this one
(opinionated reference material that informs a decision and, when
gated, blocks the gate it defends). A reader should come away knowing
how to map their own data to canonical form; if follow-up consultation
is needed, the **designer** agent runs it (and reads this doc to know
what to ask).

This sub-skill ships **standalone in its first PR** — the directory and
its contract land before any phase doc invokes it. Integration into the
live `/spp-baseline` flow (which gate the review uses, how the phase
runs the produced script) is a later bucket of the v0.6 sequence; see
"Cross-references." The sub-skill is functional and citable in design
discussions from this PR forward; it is not yet wired into a runnable
phase.

---

## 1. Identity and scope

`preprocess` performs two related jobs:

1. **Map** the user's raw data to spp's canonical `baseline.csv`
   columns — `id`, `input`, the label column(s) named after the
   `OUTPUT_SCHEMA` fields, and an optional `language` column.
2. **Author** a deterministic `preprocess.py` that performs that map
   mechanically, so the canonicalization is reproducible, inspectable,
   and reviewable before it touches the data the rest of the
   methodology depends on.

**The framing.** v0.1.0 assumed the data already arrived as
`baseline.csv` with canonical columns. Real datasets do not: the
language lives in `locale`, the text is split across `title` and
`body`, the gold label is called `category`, the row identifier is
missing entirely. Without a front gate, every downstream phase either
hard-codes column names or grows a thicket of `--*-column` flags, and
the user carries the wrangling burden. `preprocess` closes that gap
once, up front, so the canonical shape is a settled fact by the time
labeling, quality review, and splitting run.

**The risk it defends against** is a canonicalization that is *not
reproducible* — a one-off hand-edit, or an LLM rewriting rows — because
that silently breaks the guarantees the rest of the methodology rests
on: a non-deterministic map means the sacred test set is not a stable
artifact, and an LLM in the per-row path puts a model on top of the
data (including the test rows) before any split exists. The defense is
structural: the sub-skill emits a **deterministic script**, never a
transformed dataset it produced by hand or by model.

**In scope:**

- Profiling the raw data: column names, dtypes, sample values,
  cardinalities, row count, null and duplicate patterns.
- Mapping raw columns to canonical `id` / `input` / label(s) /
  optional `language`, including documented concatenation when the
  model's input is assembled from several columns, and synthesis of a
  stable `id` when none exists.
- Authoring a deterministic `preprocess.py` (pure `pandas` + standard
  library) that reads the raw file and writes the canonical
  `baseline.csv`.
- The **multilingual question** (§3.3): asking whether the data is
  multilingual, mapping an existing language column to a canonical
  BCP-47 `language` tag, or — only when the user cannot say —
  populating it via an on-demand deterministic language-identification
  library.
- A mechanical self-check the produced script runs on its own output
  (`id` unique and non-null, `input` non-null, every label column
  present), surfaced for the human review.

**Out of scope** (boundaries, not deferred work):

- **Inventing ground truth.** `preprocess` maps an *existing* label
  column to canonical form. It does not label unlabeled data — that is
  the v0.7 judge-panel concern (`DESIGN.md` §7.1.2), with its own
  protocol. A dataset with no label column is not a preprocessing
  problem; the phase routes it to baseline labeling instead.
- **Per-row LLM transformation.** The sub-skill writes a script; it is
  never itself in the per-row data path. No "ask the model to clean
  each row." Re-running `preprocess.py` on the same input must yield
  byte-identical output.
- **Schema design.** Which fields the task has, and their enums, is
  `schema-designer`'s job (`OUTPUT_SCHEMA`, `plan.md` §2). `preprocess`
  takes that schema as given and maps the gold columns to it; it does
  not propose or revise fields.
- **Touching splits or scores.** `preprocess` runs once, before any
  split exists, on the whole dataset uniformly. It never sees a
  partition, a score, or the loop. The sacred-test-set guarantee
  (`DESIGN.md` §10) is formed *downstream* of it, on its output.
- **A new `/`-command.** `preprocess` is the first step of
  `/spp-baseline`, not a fifth phase (invariant #20).

The cross-skill rule that governs every choice here is the
**plan.md-as-contract** rule (`DESIGN.md` §10): the column mapping is
recorded in `plan.md` for provenance, and the executable map is
`preprocess.py`. The full elaboration is in §5.

---

## 2. The decision the sub-skill helps make

The decision is **how each canonical column is produced from the raw
data** — concretely, a mapping the human can read and approve:

| Canonical column | The decision |
|---|---|
| `id` | Which raw column is a unique, stable key — or, if none, how to synthesize one (row index, or a hash of the input). |
| `input` | Which raw column is the model's input — or which columns concatenate, in what order, with what separator/template. |
| label(s) | Which raw column holds each `OUTPUT_SCHEMA` field's gold value, and whether its vocabulary already matches the schema's enums (canonical labels; `schema-designer` §3.5). |
| `language` | Whether the data is multilingual at all, and if so which raw column carries the language (or how it is detected). See §3.3. |

The output of the decision is not prose — it is `preprocess.py`. The
sub-skill's value is making the mapping *explicit and mechanical* so a
reviewer can see exactly what will happen to every row before it
happens, and so it happens the same way every time.

---

## 3. The protocol

### 3.1 Profile the raw data

Read the raw file and produce a compact profile the mapping decisions
are made against: each column's name, dtype, a few sample values, its
distinct-value count, its null count, and the total row count, plus
whether any candidate `id` column is unique. The profile is mechanical
— it is computed, not judged — and it is what the user and the
sub-skill read together to decide the mapping. It never needs the
*content* of every row; a sample per column is enough to recognize what
a column is.

### 3.2 Map to canonical columns

- **`id`.** Prefer an existing column that is unique and stable across
  re-exports. If none exists, synthesize one deterministically — a
  zero-padded row index (`row_00001`) when row order is stable, or a
  hash of the `input` when it is not. Never a random or time-based id:
  the split and every artifact reference rows by this key, so it must
  be reproducible.
- **`input`.** When one column is the model's input, map it directly.
  When the input is assembled from several (e.g. `title` + `body`),
  fix the concatenation in the script with an explicit, documented
  template (e.g. `f"{title}\n\n{body}"`) so every row is assembled
  identically.
- **label(s).** For each `OUTPUT_SCHEMA` field (`plan.md` §2), map the
  raw gold column to a canonical column named after the field. The
  label vocabulary stays canonical (`schema-designer` §3.5); if the raw
  values are a localized or aliased variant, the script maps them to
  the schema's enum values via an explicit, documented lookup — not a
  guess.

### 3.3 The multilingual question

Multilingual handling is one facet of preprocessing. Resolve it
explicitly, in this order:

1. **Ask the user** whether the data is multilingual and, if so, which
   raw column carries the language. This is a direct question, not an
   inference.
2. **If the user knows** — map that column to a canonical BCP-47
   `language` tag (`en`, `es`, `zh-Hans`), normalizing aliases
   (`English` → `en`) via an explicit lookup. If the user says the data
   is monolingual, write **no** `language` column; the downstream
   bookkeeping then stays in monolingual mode (`DESIGN.md` §7.1.7).
3. **If the user does not know** — and only then — populate `language`
   with a **deterministic language-identification library**, following
   the install instructions below. The detected tags are **surfaced as
   auto-detected** in the review so the human can correct them;
   detection is fallible and disclosed, never silent.

**On-demand language-ID (not a declared dependency).** `spp` does not
ship a language-ID library in its environment — it is needed only on
the unsure path, and only once, at preprocessing. When that path is
taken, install a deterministic identifier on demand and use it inside
`preprocess.py`:

```sh
# One-time, only on the "user unsure" path. Pick one:
pip install fasttext   # then load lid.176; or:
pip install langid     # pure-Python, no model download
```

The detector must be **deterministic** (same text → same tag every
run) and run **inside `preprocess.py`** so the populated `language`
column is reproducible. Never use an LLM to guess language per row: it
is non-deterministic and re-introduces a model in the per-row path. If
neither library can be installed in the environment, fall back to
asking the user to tag a `language` column by hand rather than guessing.

### 3.4 Author `preprocess.py`

Render the mapping into the `preprocess.py` contract
(`templates/preprocess.py.template`): a deterministic script that reads
the raw file and writes the canonical `baseline.csv`. It uses only
`pandas` and the standard library (plus, on the unsure path, the
on-demand language-ID library). It performs **no** network call other
than that optional one-time install, and **no** model call. It is
idempotent: re-running it on the same input produces byte-identical
output.

### 3.5 The deterministic contract (mechanical self-check)

The produced script ends by validating its own output, and the checks
are reported for the review:

1. `id` is present, unique, and non-null.
2. `input` is present and non-null for every row.
3. Every `OUTPUT_SCHEMA` label column is present.
4. Row count is reported, and any dropped rows are **listed with the
   reason** — preprocessing never silently discards data.
5. If a `language` column is written, every row has a non-null tag, and
   whether the tags were user-supplied or auto-detected is recorded.

A failed self-check is a hard stop: the script reports the failure and
does not write a half-canonical `baseline.csv`.

### 3.6 Review at the gate

The sub-skill surfaces, for human approval before the script runs: the
column mapping (the §2 table, filled in), the `preprocess.py` itself,
and — when language was auto-detected — a sample of the detected tags.
The phase that invokes the sub-skill gates on this approval; the
canonical `baseline.csv` is produced only after the human approves the
map. The approval and the mapping are recorded in `plan.md` (§5).

---

## 4. Worked examples

None references a real source-project dataset (`DESIGN.md` §7.2); each
is a generic shape.

### Example 1: rename and pass through

Raw `support.csv` has `ticket_id`, `message`, `queue`. The task is
binary `{label: Billing | Other}`. Mapping: `id ← ticket_id` (unique),
`input ← message`, `label ← queue` with the lookup
`{"billing": "Billing", "general": "Other", ...}`. Monolingual (user
confirms English). No `language` column. The script renames, applies
the label lookup, self-checks, writes `baseline.csv`.

### Example 2: synthesize an id and concatenate input

Raw `posts.jsonl` has `title`, `body`, `topic` — no id. Mapping:
`id ← row_{index:05d}` (export order is stable), `input ← f"{title}
\n\n{body}"`, `label ← topic`. The concatenation template is fixed in
the script so every row is assembled identically.

### Example 3: multilingual, column present

Raw `reviews.csv` has `id`, `text`, `sentiment`, `lang` with values
`English`, `Spanish`, `German`. User confirms multilingual; `lang` is
the language column. Mapping adds `language ← lang` via
`{"English": "en", "Spanish": "es", "German": "de"}`. Downstream the
split stratifies by language and `eval.py` reports the per-language
slice (`DESIGN.md` §7.1.7).

### Example 4: multilingual, user unsure

Raw `feedback.csv` has `id`, `comment`, `rating`; the user does not
know whether the comments are all English. The sub-skill installs a
deterministic identifier on demand (§3.3), populates `language` inside
`preprocess.py`, and surfaces a sample of the detected tags for review.
Two distinct tags appear → the project is multilingual; the human
spot-checks the auto-detected tags before approving.

---

## 5. The cross-skill constraint

The governing rule is **plan.md-as-contract** (`DESIGN.md` §10): the
durable record of the mapping lives in `plan.md` (the §6 data section
records which raw columns mapped to which canonical columns, and that a
`preprocess.py` exists), and the executable map is `preprocess.py` in
the task directory. The sub-skill writes **no** separate
`preprocess_review.md`.

Three constraints are load-bearing and are `BREAKING` to weaken
(§"Versioning"):

- **Determinism.** The artifact is a script whose output is a pure
  function of its input. No hand-edited dataset, no per-row model call.
  This is what makes the downstream sacred test set a stable artifact.
- **Runs once, pre-split, uniformly.** `preprocess.py` produces the
  canonical `baseline.csv` *before* any split exists, treating every
  row identically. It never sees a partition, so it cannot
  differentiate test rows (`DESIGN.md` §10 sacred test set).
- **Maps, never invents.** It maps existing columns; it does not
  synthesize labels (v0.7) and does not redefine the schema
  (`schema-designer`). Canonical-label discipline defers to
  `schema-designer` §3.5.

---

## 6. What the sub-skill outputs

- **`preprocess.py`** in the task directory — the deterministic
  raw → canonical map, rendered from
  `templates/preprocess.py.template`.
- **`data/baseline.csv`** — produced when the approved script runs (the
  invoking phase runs it; the sub-skill authors the script).
- **A `plan.md` §6 mapping record** — which raw columns mapped to which
  canonical columns, whether the data is multilingual, and how
  `language` was populated (user-supplied or auto-detected). Provenance,
  per the plan.md-as-contract rule.

The sub-skill does not write to any other artifact, does not annotate
`baseline.csv` rows beyond the canonical columns, and does not touch
splits, `eval.json`, or any loop artifact.

---

## Pattern for subsequent sub-skills

`preprocess` follows the shared six-section structure (identity and
scope → the decision the sub-skill helps make → the protocol → worked
examples → the cross-skill constraint → output specification). Its one
distinguishing trait is that its output artifact is **executable**, so
its cross-skill constraint centers on determinism and reproducibility
rather than on a returned verdict. Revisions happen here and propagate
by example.

---

## Versioning

Same rule as the predecessor sub-skills: changes that **alter
methodology guarantees** are flagged `BREAKING CHANGE:` in commit
messages and trigger a major-version bump per `CLAUDE.md` §4.

**Methodology-affecting (= breaking):**

- **Weakening determinism** — allowing a hand-edited dataset, a
  non-reproducible transform, or any per-row model call in the
  preprocessing path.
- **Allowing label synthesis** — letting `preprocess` invent or judge
  ground-truth values rather than map existing ones (that is the v0.7
  judge-panel boundary).
- **Running after the split, or differently per partition** — anything
  that lets preprocessing treat test rows differently from the rest, or
  run once a split exists.
- **Declaring the language-ID library as an `spp` dependency** rather
  than the on-demand, unsure-path-only install (`CLAUDE.md` §8).
- **Promoting `preprocess` to a fifth `/`-command** (invariant #20).
- **Writing to any artifact other than `preprocess.py`, the canonical
  `baseline.csv`, and the `plan.md` mapping record.**

**Behavioral (= non-breaking):**

- Better worked-example phrasing or new examples on existing paths.
- Clearer profiling output or mapping-summary wording.
- Additional documented label/language alias lookups.
- A different deterministic language-ID library on the unsure path, as
  long as it stays an on-demand install and stays deterministic.

When in doubt, treat the change as breaking. The cost of a release-notes
paragraph is low; the cost of silently making canonicalization
non-reproducible is high.

---

## Cross-references

- [`templates/preprocess.py.template`](../../templates/preprocess.py.template)
  — the deterministic-script contract this sub-skill renders.
- [`sub-skills/schema-designer/SKILL.md`](../schema-designer/SKILL.md)
  — defines the `OUTPUT_SCHEMA` whose fields name the label columns,
  and the canonical-label policy (§3.5) preprocessing maps onto.
- [`phases/spp-baseline.md`](../../phases/spp-baseline.md) — the phase
  that invokes `preprocess` as its first step and gates on the human
  review (wired in a later v0.6 bucket).
- [`DESIGN.md`](../../../../DESIGN.md) §7.1.7 — the design contract:
  preprocessing as the front gate, with multilingual as one facet.
