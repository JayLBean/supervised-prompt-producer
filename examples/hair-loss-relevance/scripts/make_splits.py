"""Generate stratified train/dev/test split per plan.md §7."""
from pathlib import Path
import json
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "spp" / "hair-loss-relevance"
df = pd.read_csv(TASK / "data" / "baseline.csv", dtype={"relevant": str, "row_id": str})
df["relevant"] = df["relevant"].str.lower()

SEED = 42
TRAIN_PCT, DEV_PCT, TEST_PCT = 60, 20, 20

train_idx, holdout_idx = train_test_split(
    df.index, test_size=(DEV_PCT + TEST_PCT) / 100,
    stratify=df["relevant"], random_state=SEED,
)
dev_idx, test_idx = train_test_split(
    holdout_idx, test_size=TEST_PCT / (DEV_PCT + TEST_PCT),
    stratify=df.loc[holdout_idx, "relevant"], random_state=SEED,
)

splits = {
    "schema_version": 1,
    "stratification_key": "relevant",
    "seed": SEED,
    "ratios": {"train": TRAIN_PCT, "dev": DEV_PCT, "test": TEST_PCT},
    "row_ids": {
        "train": sorted(df.loc[train_idx, "row_id"].tolist(), key=int),
        "dev":   sorted(df.loc[dev_idx,   "row_id"].tolist(), key=int),
        "test":  sorted(df.loc[test_idx,  "row_id"].tolist(), key=int),
    },
}

assert len(set(splits["row_ids"]["train"]) | set(splits["row_ids"]["dev"]) | set(splits["row_ids"]["test"])) == len(df)
assert not (set(splits["row_ids"]["train"]) & set(splits["row_ids"]["dev"]))
assert not (set(splits["row_ids"]["train"]) & set(splits["row_ids"]["test"]))
assert not (set(splits["row_ids"]["dev"])   & set(splits["row_ids"]["test"]))

out = TASK / "data" / "splits.json"
tmp = out.with_suffix(".json.tmp")
tmp.write_text(json.dumps(splits, indent=2))
tmp.rename(out)

for name, ids in splits["row_ids"].items():
    sub = df[df["row_id"].isin(ids)]
    pos = (sub["relevant"] == "true").sum()
    print(f"{name:5s}  n={len(sub):3d}  true={pos} ({pos/len(sub)*100:.0f}%)  false={len(sub)-pos}")
print(f"\nWrote {out}")
