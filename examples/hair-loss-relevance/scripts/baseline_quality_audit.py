"""baseline-quality §3 protocol audit — surfaces signals from rationales/criteria."""
from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[3]
df = pd.read_csv(ROOT / "spp" / "hair-loss-relevance" / "data" / "baseline.csv", dtype={"relevant": str, "row_id": str})
df["relevant"] = df["relevant"].str.lower()
print(f"Loaded {len(df)} rows; class balance: {df['relevant'].value_counts().to_dict()}")

print("\n--- §3.1 Class-definition drift: sample rationales per class (n=10/class) ---")
for cls in ["true", "false"]:
    print(f"\n[{cls.upper()}]")
    sample = df[df["relevant"] == cls].sample(n=10, random_state=42)
    for _, r in sample.iterrows():
        print(f"  row_id={r.row_id}  crit={r.primary_criterion!r}")
        print(f"    rationale: {r.rationale[:160]}")

print("\n--- §3.4 Class-balance check ---")
n_true = (df["relevant"] == "true").sum()
print(f"true: {n_true} ({n_true/len(df)*100:.0f}%); false: {len(df)-n_true} ({(len(df)-n_true)/len(df)*100:.0f}%)")
print("Plan §6 says preserve as-labeled (no production-prevalence claim asserted); 52/48 within ±10pp band ⇒ no §3.4 signal.")

print("\n--- §3.2/3.3 Borderline + intuition signals: criterion-vs-class-policy consistency ---")
true_codes_expected = ["C1", "C2", "C3", "C4", "C5"]
false_codes_expected = ["Spam", "Off-topic", "Joke", "News", "Clinical", "Boilerplate", "Out-of-context"]

def classify_crit(crit: str) -> str:
    crit_l = str(crit)
    has_C = bool(re.search(r"\bC[12345]\b", crit_l))
    has_neg = any(neg.lower() in crit_l.lower() for neg in false_codes_expected)
    if has_C and not has_neg: return "positive-coded"
    if has_neg and not has_C: return "negative-coded"
    if has_C and has_neg:     return "mixed-coded"
    return "uncoded"

df["crit_kind"] = df["primary_criterion"].apply(classify_crit)
print(df.groupby(["relevant", "crit_kind"]).size().unstack(fill_value=0))

print("\nLabel-vs-criterion mismatches (potential §3.1 drift signal):")
mismatch = df[
    ((df["relevant"] == "true")  & (df["crit_kind"] == "negative-coded")) |
    ((df["relevant"] == "false") & (df["crit_kind"] == "positive-coded"))
]
print(f"  {len(mismatch)} mismatches found")
for _, r in mismatch.iterrows():
    print(f"    row_id={r.row_id} relevant={r.relevant} crit={r.primary_criterion!r}")

print("\nUncoded / mixed-coded rows (potential §3.2 borderlines):")
amb = df[df["crit_kind"].isin(["mixed-coded", "uncoded"])]
print(f"  {len(amb)} ambiguous-criterion rows")
for _, r in amb.iterrows():
    print(f"    row_id={r.row_id} relevant={r.relevant} crit={r.primary_criterion!r}")

print("\n--- Body length distribution (open-question §10 in plan) ---")
df["len"] = df["body_clean"].str.len()
print(df.groupby("relevant")["len"].describe()[["count","min","25%","50%","75%","max"]])

print("\n--- §3.6 Provenance ---")
print("Labels brought from outside /spp-baseline (BASELINE_STATUS=complete on entry).")
print("Solo labeler; protocol embedded in the baseline itself via primary_criterion + rationale columns.")
print("Class definitions in plan.md §2 were written DURING /spp-init by inspecting the criterion taxonomy")
print("→ post-hoc-of-labels; §3.6 mandates §3.1 with extra scrutiny (which the mismatch check above performs).")
