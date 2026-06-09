# spp scripts

The runnable substrate for `/spp-loop` and `/spp-finalize`. Four
mechanical implementations of schemas specified in the methodology
docs; the scripts produce no new methodology, just operationalize
what's already specified.

## Scripts

| Script | Role | Output schema |
|---|---|---|
| [`split.py`](split.py) | Stratified train/dev/test split. | `splits.json` per [`phases/spp-baseline.md`](../phases/spp-baseline.md) §4 step 9. |
| [`inference.py`](inference.py) | Async OpenAI-compatible inference. | `results.json` per [`phases/spp-loop.md`](../phases/spp-loop.md) §4 step 6. |
| [`eval.py`](eval.py) | Metric computation against ground truth. | `eval.json` per [`phases/spp-loop.md`](../phases/spp-loop.md) §4 step 7. |
| [`discrepancy.py`](discrepancy.py) | Discrepancy-analysis skeleton. | `discrepancy_analysis.md` per [`phases/spp-loop.md`](../phases/spp-loop.md) §4 step 8 (aggregate-patterns section is LLM-populated). |
| [`lint_templates.py`](lint_templates.py) | Template-contract + filled-`plan.md` / `prompt_v01.md` validation linter (DESIGN.md §7.1.13). | Exit 0 / non-zero; violations to stderr. `templates` checks the shipped templates; `plan <path>` validates a filled plan; `prompt <path>` checks the six-section prompt. |
| [`lint_catalogs.py`](lint_catalogs.py) | `ENTRY_SCHEMA` catalog linter for the technique/structure advisor entries (DESIGN.md §7.1.13). | Exit 0 / non-zero; violations to stderr. Checks required fields present + non-empty, `id` matches filename, ids unique. |

Each script is invokable as a CLI (`python -m
.claude.skills.spp.scripts.<name>`) or importable
(`from .claude.skills.spp.scripts import <module>`). The orchestrating
LLM in `/spp-loop` and `/spp-finalize` imports the primitives directly
to avoid subprocess error-handling complexity.

## Invocation examples

```bash
# Stratified splits.
python -m .claude.skills.spp.scripts.split \
  --baseline data/baseline.csv \
  --out data/splits.json \
  --stratify-key label \
  --seed 42 \
  --ratios 0.6,0.2,0.2

# Inference (requires OPENAI_API_KEY).
export OPENAI_API_KEY=sk-...
python -m .claude.skills.spp.scripts.inference \
  --prompt runs/gpt-4o-mini/run_01/prompt_v01.md \
  --baseline data/baseline.csv \
  --row-ids-from data/splits.json --partition train,dev \
  --model gpt-4o-mini-2024-07-18 \
  --concurrency 8 \
  --context-window 128000 \
  --out runs/gpt-4o-mini/run_01/results.json
# --context-window is optional: when given, a pre-flight warns about rows
# whose estimated prompt risks truncation (advisory; DESIGN.md §7.1.7).

# Eval (binary F1).
python -m .claude.skills.spp.scripts.eval \
  --results runs/gpt-4o-mini/run_01/results.json \
  --baseline data/baseline.csv \
  --row-ids-from data/splits.json --partition dev \
  --metric f1 \
  --positive-label Relevant \
  --out runs/gpt-4o-mini/run_01/eval.json

# Discrepancy skeleton (LLM populates aggregate patterns).
python -m .claude.skills.spp.scripts.discrepancy \
  --results runs/gpt-4o-mini/run_01/results.json \
  --baseline data/baseline.csv \
  --eval runs/gpt-4o-mini/run_01/eval.json \
  --row-ids-from data/splits.json --partition dev \
  --iteration 1 \
  --out runs/gpt-4o-mini/run_01/discrepancy_analysis.md
```

## Conventions

- **Atomic writes.** Every output is written via tmp + fsync + rename;
  partial writes never appear at the destination path.
- **Schema validation.** Each JSON output is validated against a
  Pydantic model in [`_schemas.py`](_schemas.py) before write.
- **Logging.** Python `logging` at INFO; `/spp-loop` surfaces these to
  the user.
- **Environment.** `OPENAI_API_KEY` is required for `inference.py`.
  Other scripts have no environment dependencies.

## Tests

`tests/` contains smoke tests that run without API access:

```bash
pytest skills/run/scripts/tests/
```

The inference test mocks the OpenAI client; split/eval/discrepancy
tests use synthetic fixture data.

## Cross-references

- [`phases/spp-loop.md`](../phases/spp-loop.md) — the command that
  invokes these scripts in iteration order
  (inference → eval → discrepancy → adversary? → audit).
- [`phases/spp-finalize.md`](../phases/spp-finalize.md) — invokes
  `inference.py` and `eval.py` against the sacred test partition.
- [`phases/spp-baseline.md`](../phases/spp-baseline.md) §4 step 9
  — the canonical `splits.json` schema.
- [`templates/loop_spec.md.template`](../templates/loop_spec.md.template)
  §5 — the canonical inference parameters (model, concurrency,
  timeouts, retries).
