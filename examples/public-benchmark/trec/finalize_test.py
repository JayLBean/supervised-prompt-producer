#!/usr/bin/env python
"""spp/trec FINALIZE — score the frozen-candidate prompt on the SACRED test set ONCE.

Reads the 500 sacred test rows (fixtures/trec/test.jsonl == test_holdout.csv == the
EXACT rows EvoPrompt scored) and runs them through EvoPrompt's identical inference
wrapper (`eval_prompt_text` + `classify`/`match_label`) — so the spp number is
apples-to-apples with EvoPrompt's 0.804 and the shared seed's 0.828. This is the
ONLY script that reads the test partition, and it is invoked once, at /spp-finalize.

Writes:
  runs/gpt-5-nano/finalize/test_results.json   (per-row predictions)
  runs/gpt-5-nano/finalize/test_eval.json       (accuracy, per-class, confusion)
  ../../../results/spp/trec/result.json         (benchmark canonical shape, w/ usage)
and appends the finalize token row to token_usage.md.
"""
from __future__ import annotations
import csv, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK_ROOT = HERE.parent.parent
REPO = TASK_ROOT.parent.parent
SCRIPTS = REPO / "scripts"
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
from run_evoprompt import eval_prompt_text  # noqa: E402

CLASSES = ["Description", "Entity", "Expression", "Human", "Location", "Number"]
TEST_JSONL = REPO / "fixtures" / "trec" / "test.jsonl"
SPLITS = HERE / "data" / "splits.json"
TOKEN_LOG = TASK_ROOT / "token_usage.md"
PROMPT = HERE / "runs" / "gpt-5-nano" / "run_05" / "prompt_v05.md"
OUT = HERE / "runs" / "gpt-5-nano" / "finalize"


def _append_token_log(tag, snap):
    txt = TOKEN_LOG.read_text()
    calls, in_tok, out_tok = snap["calls"], snap["input_tokens"], snap["output_tokens"]
    cum = 0
    for ln in txt.splitlines():
        if ln.startswith("| ") and ln.rstrip().endswith(" |"):
            c = [x.strip() for x in ln.strip().strip("|").split("|")]
            if len(c) == 7 and c[1] == "infer":
                try: cum = max(cum, int(c[-1].replace(",", "")))
                except ValueError: pass
    new = cum + in_tok + out_tok
    row = f"| {tag} | infer | {calls:,} | {in_tok:,} | {out_tok:,} | {in_tok+out_tok:,} | {new:,} |"
    i = txt.index("\n## spp cumulative total")
    TOKEN_LOG.write_text(txt[:i].rstrip("\n") + "\n" + row + "\n" + txt[i:])
    return new


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in TEST_JSONL.read_text().splitlines()]
    assert len(rows) == 500, f"expected 500 test rows, got {len(rows)}"
    # integrity: the test rows match the sacred test row_ids registered in splits
    test_ids = set(json.loads(SPLITS.read_text())["row_ids"]["test"])
    assert {r["row_id"] for r in rows} == test_ids, "test.jsonl ids != splits test ids"

    instruction = PROMPT.read_text().strip()
    usage_reset()

    def one(r):
        label, comp = classify(eval_prompt_text(instruction, r["text"]), CLASSES, max_tokens=1024)
        return {"id": r["row_id"], "label": r["label"], "pred": label, "raw": comp.content}

    preds = map_parallel(one, rows)
    snap = usage_snapshot()

    n = len(preds)
    correct = sum(p["pred"] == p["label"] for p in preds)
    acc = round(correct / n, 4)
    per = {}
    for c in CLASSES:
        cl = [p for p in preds if p["label"] == c]
        per[c] = {"n": len(cl),
                  "recall": round(sum(p["pred"] == c for p in cl) / len(cl), 4) if cl else None}
    conf = {t: {p: 0 for p in CLASSES} for t in CLASSES}
    for p in preds:
        if p["pred"] in CLASSES:
            conf[p["label"]][p["pred"]] += 1

    (OUT / "test_results.json").write_text(json.dumps(
        {"prompt": str(PROMPT), "model": "gpt-5-nano",
         "harness": "run_evoprompt.eval_prompt_text + match_label (identical to EvoPrompt)",
         "predictions": preds}, indent=2))
    (OUT / "test_eval.json").write_text(json.dumps(
        {"metric": "accuracy", "test_n": n, "test_acc": acc,
         "n_parse_failures": sum(p["pred"] is None for p in preds),
         "per_class": per, "confusion": conf}, indent=2))

    usage = {"calls": snap["calls"], "input_tokens": snap["input_tokens"],
             "output_tokens": snap["output_tokens"], "total_tokens": snap["total_tokens"]}
    canon = REPO / "results" / "spp" / "trec"
    canon.mkdir(parents=True, exist_ok=True)
    (canon / "result.json").write_text(json.dumps(
        {"task": "trec", "arm": "spp_gpt5nano", "test_n": n, "test_acc": acc,
         "prompt": instruction, "classes": CLASSES, "usage": usage}, indent=2) + "\n")

    cum = _append_token_log("finalize_test", snap)
    print(json.dumps({"test_acc": acc, "test_n": n, "correct": correct,
                      "n_parse_failures": sum(p["pred"] is None for p in preds),
                      "per_class_recall": {c: per[c]["recall"] for c in CLASSES},
                      "usage": usage, "cumulative_total": cum}, indent=2))


if __name__ == "__main__":
    main()
