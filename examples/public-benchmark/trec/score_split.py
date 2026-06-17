#!/usr/bin/env python
"""spp/trec loop+finalize scorer — EvoPrompt's EXACT inference harness (gpt-5-nano).

WHY THIS EXISTS (apples-to-apples): the bar to beat (shared seed 0.828, EvoPrompt
0.804) was produced by `scripts/run_evoprompt.evaluate`, which wraps every row as a
SINGLE user message `f"{instruction}\n\nSentence: {text}\nLabel:"` and recovers the
label with `llm_client.match_label` (exact / case-insensitive / substring). The
benchmark's `scripts/score_prompt.py` reuses that same wrapper to score the spp arm.
So the spp loop MUST score dev/train through the identical wrapper — otherwise
"beat 0.828" compares two different inference harnesses, not two prompts. This
driver reuses `eval_prompt_text` (verbatim) + `llm_client.classify` (verbatim);
spp's only contribution is the instruction text. The sacred test is refused here.

Usage:
  score_split.py --prompt <p.md> --partition dev --out-dir <run_dir> --tag run_01
  score_split.py --prompt <p.md> --partition train,dev --out-dir <run_dir> --tag run_01
"""
from __future__ import annotations
import argparse, csv, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent              # spp/trec
TASK_ROOT = HERE.parent.parent                       # baselines/trec
REPO = TASK_ROOT.parent.parent                       # spp-bm
SCRIPTS = REPO / "scripts"

# .env -> OPENAI_API_KEY, then point llm_client at gpt-5-nano (EXACTLY like
# scripts/run_gpt5nano.sh) BEFORE importing it (it reads env at import time).
for line in (TASK_ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ.setdefault(k, v)
os.environ["OMLX_BASE_URL"] = "https://api.openai.com/v1"
os.environ["OMLX_API_KEY"] = os.environ["OPENAI_API_KEY"]
os.environ["OMLX_MODEL"] = "gpt-5-nano"
os.environ["OMLX_REASONING"] = "low"
os.environ.setdefault("OMLX_WORKERS", "8")

sys.path.insert(0, str(SCRIPTS))
from llm_client import classify, usage_reset, usage_snapshot, map_parallel  # noqa: E402
from run_evoprompt import eval_prompt_text  # noqa: E402  (verbatim wrapper)

BASELINE = HERE / "data" / "baseline.csv"
SPLITS = HERE / "data" / "splits.json"
CLASSES = ["Description", "Entity", "Expression", "Human", "Location", "Number"]
TOKEN_LOG = TASK_ROOT / "token_usage.md"
FORBIDDEN_TEST = set(json.loads(SPLITS.read_text())["row_ids"]["test"])


def _rows(partition: str) -> list[dict]:
    base = {r["id"]: r for r in csv.DictReader(open(BASELINE))}
    ids = json.loads(SPLITS.read_text())["row_ids"]
    out = []
    for p in partition.split(","):
        if p == "test":
            raise SystemExit("REFUSED: test partition is sacred until /spp-finalize")
        for rid in ids[p]:
            if rid in FORBIDDEN_TEST:
                raise SystemExit(f"REFUSED: test row {rid} leaked into '{partition}'")
            out.append({"id": rid, "text": base[rid]["input"], "label": base[rid]["label"], "part": p})
    return out


def _confusion(preds: list[dict]) -> dict:
    m = {t: {p: 0 for p in CLASSES} for t in CLASSES}
    for r in preds:
        pred = r["pred"] if r["pred"] in CLASSES else None
        if pred is not None:
            m[r["label"]][pred] += 1
    return m


def _eval(preds: list[dict]) -> dict:
    n = len(preds)
    correct = sum(p["pred"] == p["label"] for p in preds)
    per = {}
    for c in CLASSES:
        cls = [p for p in preds if p["label"] == c]
        per[c] = {
            "n": len(cls),
            "recall": round(sum(p["pred"] == c for p in cls) / len(cls), 4) if cls else None,
        }
    return {
        "metric": "accuracy", "n": n, "accuracy": round(correct / n, 4),
        "n_parse_failures": sum(p["pred"] is None for p in preds),
        "per_class": per, "confusion": _confusion(preds),
    }


def _append_token_log(tag: str, snap: dict) -> int:
    txt = TOKEN_LOG.read_text()
    calls, in_tok, out_tok = snap["calls"], snap["input_tokens"], snap["output_tokens"]
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
    anchor = "\n## spp cumulative total"
    i = txt.index(anchor)
    TOKEN_LOG.write_text(txt[:i].rstrip("\n") + "\n" + row + "\n" + txt[i:])
    return new_cum


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", type=Path, required=True)
    ap.add_argument("--partition", default="dev")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--no-token-log", action="store_true")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    instruction = args.prompt.read_text().strip()
    rows = _rows(args.partition)
    usage_reset()

    def one(r):
        label, comp = classify(eval_prompt_text(instruction, r["text"]), CLASSES, max_tokens=1024)
        return {"id": r["id"], "part": r["part"], "label": r["label"],
                "pred": label, "raw": comp.content}

    preds = map_parallel(one, rows)
    snap = usage_snapshot()

    (args.out_dir / "results.json").write_text(json.dumps(
        {"prompt": str(args.prompt), "model": "gpt-5-nano",
         "harness": "run_evoprompt.eval_prompt_text (Sentence:/Label:, match_label)",
         "predictions": preds}, indent=2))
    accs = {}
    for p in args.partition.split(","):
        sub = [x for x in preds if x["part"] == p]
        ev = _eval(sub)
        (args.out_dir / f"eval_{p}.json").write_text(json.dumps(ev, indent=2))
        accs[p] = ev["accuracy"]

    cum = _append_token_log(args.tag, snap) if not args.no_token_log else None
    print(json.dumps({"tag": args.tag, "partition": args.partition,
                      "calls": snap["calls"], "input_tokens": snap["input_tokens"],
                      "output_tokens": snap["output_tokens"], "total_tokens": snap["total_tokens"],
                      "cumulative_total": cum, "accuracy": accs,
                      "n_parse_failures": sum(p["pred"] is None for p in preds)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
