#!/usr/bin/env python
"""spp/trec inference+eval driver (gpt-5-nano arm).

Wraps the spp runner (scripts/inference.py) + scorer (scripts/eval.py) for the
trec loop. Loads OPENAI_API_KEY from baselines/trec/.env, runs inference on a
named split partition, computes accuracy, and (unless --no-token-log) appends
cumulative gpt-5-nano token usage to token_usage.md in the cost_report.py shape
{calls, input_tokens, output_tokens, total_tokens}.

A usage-tee proxy around AsyncOpenAI captures exact prompt_tokens /
completion_tokens (reasoning tokens count as output) per call while reusing the
runner's parsing/retry/concurrency. The sacred test partition is never read here
(hard refusal).

Usage:
  run_infer.py --prompt <p.md> --partition dev --out-dir <run_dir> --tag run_01
  run_infer.py --prompt <p.md> --partition train,dev --out-dir <run_dir> --tag run_01
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent              # spp/trec
TASK_ROOT = HERE.parent.parent                       # baselines/trec
# The spp plugin's runner (scripts/inference.py, scripts/eval.py). In the original
# benchmark this was an absolute path to the installed plugin; here it resolves to
# this repository's own skills/run. Override with SPP_RUN_DIR if running elsewhere.
SPP_RUN = Path(os.environ.get("SPP_RUN_DIR", Path(__file__).resolve().parents[3] / "skills" / "run"))
sys.path.insert(0, str(SPP_RUN))

for line in (TASK_ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ.setdefault(k, v)
os.environ.setdefault("SPP_REASONING_EFFORT", "low")  # gpt-5-nano reasoning_effort

from scripts.inference import run_inference   # noqa: E402
from scripts.eval import compute_eval         # noqa: E402

BASELINE = HERE / "data" / "baseline.csv"
SPLITS = HERE / "data" / "splits.json"
MODEL = "gpt-5-nano"
ENDPOINT = "https://api.openai.com/v1"
TOKEN_LOG = TASK_ROOT / "token_usage.md"
FORBIDDEN_TEST = set(json.loads(SPLITS.read_text())["row_ids"]["test"])


# ---- usage-tee proxy: exact input/output token capture --------------------
class _CompletionsProxy:
    def __init__(self, real, tee): self._real, self._tee = real, tee
    async def create(self, **kw):
        resp = await self._real.create(**kw)
        u = getattr(resp, "usage", None)
        if u:
            self._tee["input"] += getattr(u, "prompt_tokens", 0) or 0
            self._tee["output"] += getattr(u, "completion_tokens", 0) or 0
        self._tee["calls"] += 1
        return resp


class _ChatProxy:
    def __init__(self, real, tee): self.completions = _CompletionsProxy(real.completions, tee)


class _ClientProxy:
    def __init__(self, real, tee): self.chat = _ChatProxy(real.chat, tee)


def _ids(partition: str) -> list[str]:
    d = json.loads(SPLITS.read_text())["row_ids"]
    out = []
    for p in partition.split(","):
        if p == "test":
            raise SystemExit("REFUSED: test partition is sacred until /spp-finalize")
        out.extend(d[p])
    leak = set(out) & FORBIDDEN_TEST
    if leak:
        raise SystemExit(f"REFUSED: {len(leak)} test rows leaked into '{partition}'")
    return out


def _append_token_log(tag: str, calls: int, in_tok: int, out_tok: int) -> int:
    txt = TOKEN_LOG.read_text()
    # cumulative = last ledger row's cumulative cell + this run
    cum = 0
    for ln in txt.splitlines():
        if ln.startswith("| ") and ln.rstrip().endswith(" |"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) == 7 and cells[1] == "infer":
                try:
                    cum = max(cum, int(cells[-1].replace(",", "")))
                except ValueError:
                    pass
    new_cum = cum + in_tok + out_tok
    row = (f"| {tag} | infer | {calls:,} | {in_tok:,} | {out_tok:,} "
           f"| {in_tok+out_tok:,} | {new_cum:,} |")
    placeholder = ("| _(none yet — populated after each inference run starting at "
                   "the G4 dry-run)_ | | | | | | |")
    if placeholder in txt:
        txt = txt.replace(placeholder, row)
    else:
        anchor = "\n## spp cumulative total"
        i = txt.index(anchor)
        txt = txt[:i].rstrip("\n") + "\n" + row + "\n" + txt[i:]
    TOKEN_LOG.write_text(txt)
    return new_cum


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", type=Path, required=True)
    ap.add_argument("--partition", default="dev")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--max-tokens", type=int, default=2000)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=90.0)
    ap.add_argument("--no-token-log", action="store_true")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    ids = _ids(args.partition)
    from openai import AsyncOpenAI
    tee = {"input": 0, "output": 0, "calls": 0}
    client = _ClientProxy(AsyncOpenAI(base_url=ENDPOINT, api_key=os.environ["OPENAI_API_KEY"]), tee)

    results_path = args.out_dir / "results.json"
    res = run_inference(
        prompt_path=args.prompt, baseline_path=BASELINE, row_ids=ids,
        model=MODEL, api_endpoint=ENDPOINT, concurrency=args.concurrency,
        max_tokens=args.max_tokens, timeout=args.timeout, temperature=1.0,
        out_path=results_path, input_column="input", id_column="id",
        schema_path=None, client=client,
    )

    accs = {}
    splits = json.loads(SPLITS.read_text())["row_ids"]
    for part in args.partition.split(","):
        ev = compute_eval(
            results_path=results_path, baseline_path=BASELINE,
            row_ids=splits[part], metric="accuracy",
            out_path=args.out_dir / f"eval_{part}.json",
            label_column="label", id_column="id",
        )
        accs[part] = round(ev.primary_value, 4)

    cum = None
    if not args.no_token_log:
        cum = _append_token_log(args.tag, tee["calls"], tee["input"], tee["output"])

    print(json.dumps({
        "tag": args.tag, "partition": args.partition,
        "calls": tee["calls"], "input_tokens": tee["input"],
        "output_tokens": tee["output"], "total_tokens": tee["input"] + tee["output"],
        "cumulative_total": cum, "accuracy": accs,
        "n_parsed": res.summary.n_parsed, "n_parse_failures": res.summary.n_parse_failures,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
