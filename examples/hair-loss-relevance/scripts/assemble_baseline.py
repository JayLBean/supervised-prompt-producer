"""Assemble spp/hair-loss-relevance/data/baseline.csv from data/baseline.csv + data/sample.csv (positional join)."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
src_baseline = pd.read_csv(ROOT / "data" / "baseline.csv")
src_sample = pd.read_csv(ROOT / "data" / "sample.csv")

assert len(src_baseline) == len(src_sample) == 100, (len(src_baseline), len(src_sample))
assert list(src_baseline["row_id"]) == list(range(100)), "baseline.row_id must be 0..99"

joined = pd.DataFrame({
    "row_id": src_baseline["row_id"].astype(str),
    "document_id": src_sample["Document ID"],
    "body_clean": src_sample["body_clean"],
    "relevant": src_baseline["relevant"].astype(str).str.lower(),
    "primary_criterion": src_baseline["primary_criterion"],
    "rationale": src_baseline["rationale"],
})

assert set(joined["relevant"].unique()) <= {"true", "false"}, joined["relevant"].unique()

out = ROOT / "spp" / "hair-loss-relevance" / "data" / "baseline.csv"
out.parent.mkdir(parents=True, exist_ok=True)
joined.to_csv(out, index=False)
print(f"Wrote {out} with {len(joined)} rows; class balance:")
print(joined["relevant"].value_counts().to_dict())
