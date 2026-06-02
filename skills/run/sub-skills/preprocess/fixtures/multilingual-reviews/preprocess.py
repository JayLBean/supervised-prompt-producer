"""Sample preprocess.py — a filled instance of the preprocess contract.

A worked example of what the `preprocess` sub-skill authors
(sub-skills/preprocess/SKILL.md; templates/preprocess.py.template). It
maps a raw multilingual review export to spp's canonical baseline.csv:

    raw columns:  review_id, body, stars_label, lang
    canonical:    id,        input, label,       language

It demonstrates all three mapping moves in one script — a rename
(review_id -> id, body -> input), a canonical-label lookup
(stars_label -> {positive: Positive, negative: Negative}), and a BCP-47
language map (lang -> {English: en, ...}). Deterministic and idempotent:
re-running on the same input yields byte-identical output. Pure pandas +
stdlib; no model call, no network, no randomness.

Run:  python preprocess.py --raw inputs/raw.csv --out /tmp/baseline.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

LABEL_COLUMNS: list[str] = ["label"]
HAS_LANGUAGE: bool = True

# Explicit, documented lookups — never a guess. A raw value missing from
# a lookup maps to NaN and is caught by the self-check, surfacing the gap
# rather than silently mislabeling.
_LABEL_MAP = {"positive": "Positive", "negative": "Negative"}
_LANGUAGE_MAP = {"English": "en", "Spanish": "es", "German": "de"}


class PreprocessError(RuntimeError):
    """Fatal error during preprocessing; message is user-facing."""


def _read_raw(raw_path: Path) -> pd.DataFrame:
    if not raw_path.exists():
        raise PreprocessError(f"raw input not found at {raw_path}")
    return pd.read_csv(raw_path)


def preprocess(raw_path: Path, out_path: Path) -> pd.DataFrame:
    """Map the raw review export to the canonical baseline.csv."""
    raw = _read_raw(raw_path)
    out = pd.DataFrame()
    out["id"] = raw["review_id"].astype(str)
    out["input"] = raw["body"].astype(str)
    out["label"] = raw["stars_label"].map(_LABEL_MAP)
    out["language"] = raw["lang"].map(_LANGUAGE_MAP)
    _self_check(out, n_raw=len(raw))
    _atomic_write_csv(out, out_path)
    return out


def _self_check(out: pd.DataFrame, n_raw: int) -> None:
    if "id" not in out.columns or out["id"].isna().any():
        raise PreprocessError("canonical 'id' missing or has null values")
    if out["id"].duplicated().any():
        dupes = out["id"][out["id"].duplicated()].tolist()[:5]
        raise PreprocessError(f"canonical 'id' is not unique; e.g. {dupes}")
    if "input" not in out.columns or out["input"].isna().any():
        raise PreprocessError("canonical 'input' missing or has null values")
    for col in LABEL_COLUMNS:
        if col not in out.columns:
            raise PreprocessError(f"label column '{col}' missing from output")
        if out[col].isna().any():
            raise PreprocessError(f"label column '{col}' has unmapped (NaN) values")
    if HAS_LANGUAGE and out["language"].isna().any():
        raise PreprocessError("multilingual data: some rows have no language tag")
    dropped = n_raw - len(out)
    if dropped:
        print(f"NOTE: {dropped} of {n_raw} raw rows dropped (document why).")


def _atomic_write_csv(df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(out_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Raw -> canonical baseline.csv.")
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        df = preprocess(args.raw, args.out)
    except PreprocessError as e:
        print(f"preprocess failed: {e}", file=sys.stderr)
        return 2
    print(f"wrote {len(df)} rows -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
