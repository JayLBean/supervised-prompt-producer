"""Stratified train/dev/test split for /spp-baseline.

Implements the schema documented in commands/spp-baseline.md §4 step 9.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from ._io import atomic_write_json
from ._schemas import SplitsJSON, SplitsRowIds

log = logging.getLogger(__name__)


class SplitError(RuntimeError):
    """Fatal error during split generation; message is user-facing."""


def make_splits(
    baseline_path: Path,
    stratify_key: str,
    seed: int,
    ratios: tuple[float, float, float],
    out_path: Path,
    id_column: str = "id",
) -> SplitsJSON:
    """Generate stratified splits, validate, atomic-write to ``out_path``.

    Returns the validated SplitsJSON model. Raises SplitError on any
    user-facing failure (missing columns, NaN labels, missing class in
    a partition, ratio sum mismatch, etc.).
    """
    if abs(sum(ratios) - 1.0) > 1e-6:
        raise SplitError(
            f"ratios must sum to 1.0; got {ratios} summing to {sum(ratios)}"
        )

    train_pct, dev_pct, test_pct = ratios

    if not baseline_path.exists():
        raise SplitError(f"baseline not found at {baseline_path}")

    df = pd.read_csv(baseline_path)
    if id_column not in df.columns:
        raise SplitError(
            f"baseline missing required id column '{id_column}'; "
            f"columns present: {list(df.columns)}"
        )
    if stratify_key not in df.columns:
        raise SplitError(
            f"stratification key '{stratify_key}' not in baseline columns: "
            f"{list(df.columns)}"
        )
    if df[stratify_key].isna().any():
        n_nan = int(df[stratify_key].isna().sum())
        raise SplitError(
            f"{n_nan} rows have NaN in stratification key '{stratify_key}'"
        )

    # Two-step split: peel test off, then split remainder into train/dev.
    test_size = test_pct
    df_remainder, df_test = train_test_split(
        df,
        test_size=test_size,
        random_state=seed,
        stratify=df[stratify_key],
    )
    # dev's share of the remainder = dev_pct / (train_pct + dev_pct)
    dev_size = dev_pct / (train_pct + dev_pct)
    df_train, df_dev = train_test_split(
        df_remainder,
        test_size=dev_size,
        random_state=seed,
        stratify=df_remainder[stratify_key],
    )

    # Verify every label appears in every partition.
    all_labels = set(df[stratify_key].unique())
    for name, partition in (("train", df_train), ("dev", df_dev), ("test", df_test)):
        present = set(partition[stratify_key].unique())
        missing = all_labels - present
        if missing:
            raise SplitError(
                f"partition '{name}' missing classes {sorted(missing)}; "
                f"increase baseline size or adjust stratification"
            )

    splits = SplitsJSON(
        stratification_key=stratify_key,
        seed=seed,
        ratios={"train": train_pct, "dev": dev_pct, "test": test_pct},
        row_ids=SplitsRowIds(
            train=df_train[id_column].astype(str).tolist(),
            dev=df_dev[id_column].astype(str).tolist(),
            test=df_test[id_column].astype(str).tolist(),
        ),
    )
    atomic_write_json(out_path, splits.model_dump())
    log.info(
        "splits written: train=%d dev=%d test=%d -> %s",
        len(splits.row_ids.train),
        len(splits.row_ids.dev),
        len(splits.row_ids.test),
        out_path,
    )
    return splits


def _parse_ratios(s: str) -> tuple[float, float, float]:
    parts = [float(x) for x in s.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            f"--ratios expects 'train,dev,test' (3 values); got {parts}"
        )
    return (parts[0], parts[1], parts[2])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stratified train/dev/test split.")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--stratify-key", type=str, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument(
        "--ratios",
        type=_parse_ratios,
        default=(0.6, 0.2, 0.2),
        help="Comma-separated train,dev,test (default: 0.6,0.2,0.2)",
    )
    parser.add_argument("--id-column", type=str, default="id")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        make_splits(
            baseline_path=args.baseline,
            stratify_key=args.stratify_key,
            seed=args.seed,
            ratios=args.ratios,
            out_path=args.out,
            id_column=args.id_column,
        )
    except SplitError as e:
        log.error("split failed: %s", e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
