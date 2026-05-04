# spp scripts

The runnable substrate for `/spp-loop` and `/spp-finalize`. Four
mechanical implementations of schemas specified in the methodology
docs; the scripts produce no new methodology, just operationalize
what's already specified.

## Scripts

| Script | Role | Output schema |
|---|---|---|
| [`split.py`](split.py) | Stratified train/dev/test split. | `splits.json` per [`commands/spp-baseline.md`](../commands/spp-baseline.md) §4 step 9. |
| [`inference.py`](inference.py) | Async OpenAI-compatible inference. | `results.json` per [`commands/spp-loop.md`](../commands/spp-loop.md) §4 step 6. |
| [`eval.py`](eval.py) | Metric computation against ground truth. | `eval.json` per [`commands/spp-loop.md`](../commands/spp-loop.md) §4 step 7. |
| [`discrepancy.py`](discrepancy.py) | Discrepancy-analysis skeleton. | `discrepancy_analysis.md` per [`commands/spp-loop.md`](../commands/spp-loop.md) §4 step 8 (aggregate-patterns section is LLM-populated). |

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
  --out runs/gpt-4o-mini/run_01/results.json

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
pytest .claude/skills/spp/scripts/tests/
```

The inference test mocks the OpenAI client; split/eval/discrepancy
tests use synthetic fixture data.

## Cross-references

- [`commands/spp-loop.md`](../commands/spp-loop.md) — the command that
  invokes these scripts in iteration order
  (inference → eval → discrepancy → adversary? → audit).
- [`commands/spp-finalize.md`](../commands/spp-finalize.md) — invokes
  `inference.py` and `eval.py` against the sacred test partition.
- [`commands/spp-baseline.md`](../commands/spp-baseline.md) §4 step 9
  — the canonical `splits.json` schema.
- [`templates/loop_spec.md.template`](../templates/loop_spec.md.template)
  §5 — the canonical inference parameters (model, concurrency,
  timeouts, retries).
