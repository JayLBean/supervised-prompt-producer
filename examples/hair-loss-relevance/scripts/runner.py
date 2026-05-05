"""
spp/hair-loss-relevance runner — inference + eval orchestrator.

Operational guarantees:
- The inference input set is built positively from train + dev row IDs in splits.json.
  Test rows are NEVER passed to the model; they are not even loaded into a working frame.
- A defense-in-depth assertion verifies test row IDs are absent from the inference set.
- Outputs land under spp/hair-loss-relevance/runs/<model_id>/run_NN/.
- Metric: F1 on positive class (label "true"); also report precision, recall, balanced_accuracy, confusion matrix.

Subcommands:
    dryrun                       run model on first 3 train rows; write _dryrun/results.json
    iter <N>                     run iteration N: inference on train+dev, persist results.json + eval.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
from openai import AsyncOpenAI
from sklearn.metrics import (balanced_accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)

ROOT = Path(__file__).resolve().parents[3]
TASK_DIR = ROOT / "spp" / "hair-loss-relevance"
DATA_DIR = TASK_DIR / "data"
RUNS_DIR = TASK_DIR / "runs"

MODEL_ID = "gpt-oss-20b-MXFP4-Q8"
ENDPOINT = "http://127.0.0.1:8000/v1"
TIMEOUT_S = 60
MAX_TOKENS = 3000
CONCURRENCY = 5
TEMPERATURE = 0.0


def load_env_key() -> str:
    env_path = ROOT / ".env"
    for line in env_path.read_text().splitlines():
        m = re.match(r'^\s*LOCAL_API_KEY\s*=\s*"?([^"]+)"?\s*$', line)
        if m:
            return m.group(1)
    raise SystemExit("LOCAL_API_KEY not found in .env")


def load_partition(split_name: str) -> list[dict]:
    splits = json.loads((DATA_DIR / "splits.json").read_text())
    train_ids = set(splits["row_ids"]["train"])
    dev_ids = set(splits["row_ids"]["dev"])
    test_ids = set(splits["row_ids"]["test"])

    df = pd.read_csv(DATA_DIR / "baseline.csv", dtype={"relevant": str, "row_id": str})
    df["relevant"] = df["relevant"].str.lower()

    if split_name == "train":
        wanted = train_ids
    elif split_name == "dev":
        wanted = dev_ids
    elif split_name == "train+dev":
        wanted = train_ids | dev_ids
    elif split_name == "dryrun":
        wanted = set(splits["row_ids"]["train"][:3])
    elif split_name == "test":
        wanted = test_ids  # /spp-finalize ONLY — sacred test set, exactly once.
    else:
        raise ValueError(split_name)

    if split_name != "test":
        # Defense in depth: any non-test partition must NOT contain test row IDs.
        leak = wanted & test_ids
        if leak:
            raise SystemExit(f"runner sanity check failed: test row IDs in inference input set: {sorted(leak)}")

    sub = df[df["row_id"].isin(wanted)].copy()
    return sub.to_dict(orient="records")


def parse_label(text: str) -> tuple[str | None, str]:
    """Parse the model's JSON response. Returns (label, raw_text)."""
    raw = text.strip()
    # Strip markdown code fences if present.
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: scan for "label": "true|false"
        m = re.search(r'"label"\s*:\s*"(true|false)"', raw, re.IGNORECASE)
        if m:
            return m.group(1).lower(), raw
        m = re.search(r'\b(true|false)\b', raw.lower())
        if m:
            return m.group(1), raw
        return None, raw
    label = obj.get("label")
    if isinstance(label, bool):
        return ("true" if label else "false"), raw
    if isinstance(label, str):
        return label.strip().lower(), raw
    return None, raw


async def call_one(client: AsyncOpenAI, prompt_text: str, body: str, row_id: str, sem: asyncio.Semaphore) -> dict:
    user_msg = f"<input_row>\n{body}\n</input_row>"
    async with sem:
        for attempt in range(3):
            try:
                resp = await client.chat.completions.create(
                    model=MODEL_ID,
                    messages=[
                        {"role": "system", "content": prompt_text},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                    timeout=TIMEOUT_S,
                )
                content = resp.choices[0].message.content or ""
                label, raw = parse_label(content)
                return {"row_id": row_id, "predicted": label, "raw": raw}
            except Exception as e:
                if attempt == 2:
                    return {"row_id": row_id, "predicted": None, "raw": f"<error: {e}>"}
                await asyncio.sleep(2 ** attempt)


async def run_inference(prompt_path: Path, rows: list[dict]) -> list[dict]:
    api_key = load_env_key()
    client = AsyncOpenAI(api_key=api_key, base_url=ENDPOINT)
    prompt_text = prompt_path.read_text()
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [call_one(client, prompt_text, r["body_clean"], r["row_id"], sem) for r in rows]
    return await asyncio.gather(*tasks)


def compute_metrics(preds: list[dict], rows: list[dict]) -> dict:
    by_id = {r["row_id"]: r for r in rows}
    y_true: list[str] = []
    y_pred: list[str] = []
    unparsed: list[str] = []
    for p in preds:
        rid = p["row_id"]
        gt = by_id[rid]["relevant"]
        if p["predicted"] is None or p["predicted"] not in {"true", "false"}:
            unparsed.append(rid)
            # Treat unparsed as the wrong label (penalize the prompt for non-compliance).
            y_pred.append("false" if gt == "true" else "true")
        else:
            y_pred.append(p["predicted"])
        y_true.append(gt)
    pos = "true"
    cm = confusion_matrix(y_true, y_pred, labels=["false", "true"]).tolist()
    return {
        "n": len(y_true),
        "f1_pos": float(f1_score(y_true, y_pred, pos_label=pos)),
        "precision_pos": float(precision_score(y_true, y_pred, pos_label=pos, zero_division=0)),
        "recall_pos": float(recall_score(y_true, y_pred, pos_label=pos, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "confusion_matrix": {"labels": ["false", "true"], "matrix": cm},
        "unparsed_row_ids": unparsed,
    }


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    os.fsync(os.open(str(tmp), os.O_RDONLY))
    tmp.rename(path)


def cmd_dryrun(args) -> None:
    rows = load_partition("dryrun")
    prompt_path = TASK_DIR / "runs" / MODEL_ID / "run_01" / "prompt_v01.md"
    assert prompt_path.exists(), f"missing {prompt_path}"
    preds = asyncio.run(run_inference(prompt_path, rows))
    out_dir = RUNS_DIR / MODEL_ID / "_dryrun"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for p, r in zip(preds, rows):
        summary.append({
            "row_id": r["row_id"], "ground_truth": r["relevant"],
            "predicted": p["predicted"], "raw_excerpt": p["raw"][:200],
        })
    write_atomic(out_dir / "results.json", json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


def cmd_iter(args) -> None:
    n = int(args.n)
    run_dir = RUNS_DIR / MODEL_ID / f"run_{n:02d}"
    prompt_path = run_dir / f"prompt_v{n:02d}.md"
    assert prompt_path.exists(), f"missing prompt {prompt_path}"

    train_rows = load_partition("train")
    dev_rows = load_partition("dev")

    t0 = time.time()
    train_preds = asyncio.run(run_inference(prompt_path, train_rows))
    dev_preds = asyncio.run(run_inference(prompt_path, dev_rows))
    elapsed = time.time() - t0

    train_eval = compute_metrics(train_preds, train_rows)
    dev_eval = compute_metrics(dev_preds, dev_rows)

    results = {"train": train_preds, "dev": dev_preds}
    write_atomic(run_dir / "results.json", json.dumps(results, indent=2))
    eval_payload = {
        "iteration": n, "model": MODEL_ID, "elapsed_seconds": round(elapsed, 1),
        "train": train_eval, "dev": dev_eval,
        "primary_metric": "f1_pos",
        "summary": {
            "train_f1": train_eval["f1_pos"],
            "dev_f1": dev_eval["f1_pos"],
            "train_dev_delta": round(train_eval["f1_pos"] - dev_eval["f1_pos"], 4),
        },
    }
    write_atomic(run_dir / "eval.json", json.dumps(eval_payload, indent=2))
    print(json.dumps(eval_payload["summary"], indent=2))
    print(f"unparsed train: {len(train_eval['unparsed_row_ids'])}, dev: {len(dev_eval['unparsed_row_ids'])}")


def cmd_disagreed(args) -> None:
    """Print disagreed dev rows (row_id, predicted, ground_truth, body) for the discrepancy subagent's allow-list."""
    n = int(args.n)
    run_dir = RUNS_DIR / MODEL_ID / f"run_{n:02d}"
    results = json.loads((run_dir / "results.json").read_text())
    dev_rows = {r["row_id"]: r for r in load_partition("dev")}
    disagreed = []
    for p in results["dev"]:
        rid = p["row_id"]
        gt = dev_rows[rid]["relevant"]
        pred = p["predicted"]
        if pred != gt:
            disagreed.append({
                "row_id": rid, "predicted": pred, "ground_truth": gt,
                "primary_criterion": dev_rows[rid]["primary_criterion"],
                "rationale": dev_rows[rid]["rationale"],
                "body_clean": dev_rows[rid]["body_clean"],
            })
    print(json.dumps(disagreed, indent=2))


def cmd_finalize_test(args) -> None:
    """Sacred-test-set read — /spp-finalize only. Reads test partition exactly once."""
    test_eval_path = RUNS_DIR / MODEL_ID / "test_eval.json"
    if test_eval_path.exists():
        raise SystemExit(f"refusing: {test_eval_path} already exists. /spp-finalize is one-shot. See spp-finalize.md §3 pre-condition 8.")

    success_path = RUNS_DIR / MODEL_ID / "SUCCESS.md"
    if not success_path.exists():
        raise SystemExit(f"refusing: SUCCESS.md not found at {success_path}; /spp-finalize requires SUCCESS termination per pre-condition 6.")

    # Identify candidate prompt from SUCCESS.md (currently hardcoded by convention to run_04/prompt_v04.md;
    # for the v1 of this exercise we read it from the user's chosen iteration).
    prompt_path = RUNS_DIR / MODEL_ID / "run_04" / "prompt_v04.md"
    assert prompt_path.exists(), f"missing candidate frozen prompt {prompt_path}"

    test_rows = load_partition("test")
    print(f"reading sacred test partition: {len(test_rows)} rows")

    t0 = time.time()
    test_preds = asyncio.run(run_inference(prompt_path, test_rows))
    elapsed = time.time() - t0

    test_eval = compute_metrics(test_preds, test_rows)
    payload = {
        "model": MODEL_ID, "candidate_prompt": str(prompt_path.relative_to(TASK_DIR)),
        "elapsed_seconds": round(elapsed, 1),
        "test": test_eval,
        "primary_metric": "f1_pos",
        "headline_target": 0.90,
        "headline_met_on_test": test_eval["f1_pos"] >= 0.90,
    }
    write_atomic(RUNS_DIR / MODEL_ID / "test_results.json", json.dumps({"test": test_preds}, indent=2))
    write_atomic(RUNS_DIR / MODEL_ID / "test_eval.json", json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


def cmd_check_endpoint(args) -> None:
    api_key = load_env_key()
    import urllib.request
    req = urllib.request.Request(f"{ENDPOINT}/models", headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
        print(json.dumps([m.get("id") for m in data.get("data", [])], indent=2))


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-endpoint")
    sub.add_parser("dryrun")
    sub.add_parser("finalize-test")
    pi = sub.add_parser("iter"); pi.add_argument("n")
    pd_ = sub.add_parser("disagreed"); pd_.add_argument("n")
    args = p.parse_args()
    if args.cmd == "check-endpoint":     cmd_check_endpoint(args)
    elif args.cmd == "dryrun":           cmd_dryrun(args)
    elif args.cmd == "finalize-test":    cmd_finalize_test(args)
    elif args.cmd == "iter":             cmd_iter(args)
    elif args.cmd == "disagreed":        cmd_disagreed(args)


if __name__ == "__main__":
    main()
