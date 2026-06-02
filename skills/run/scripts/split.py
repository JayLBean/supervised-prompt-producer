"""Stratified train/dev/test split for /spp-baseline.

Implements the schema documented in phases/spp-baseline.md §4 step 9.
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
    language_column: str = "language",
) -> SplitsJSON:
    """Generate stratified splits, validate, atomic-write to ``out_path``.

    Returns the validated SplitsJSON model. Raises SplitError on any
    user-facing failure (missing columns, NaN labels, missing class in
    a partition, ratio sum mismatch, etc.).

    Multilingual stratification (DESIGN.md §7.1.7) is data-driven: when
    ``language_column`` is present in the baseline with two or more
    distinct values, the split is stratified jointly on
    ``stratify_key`` x ``language_column`` so every split — including
    the sacred test set — is representative of the language
    distribution, and every language is verified present in every
    partition. With the column absent or single-valued the behavior is
    identical to the pre-v0.6 label-only split.
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

    # Multilingual detection is data-driven (DESIGN.md §7.1.7): the
    # `language` column is optional, and per-language stratification
    # engages only when it is present with >=2 distinct values. Absent or
    # single-valued, the split is identical to pre-v0.6 behavior.
    multilingual = (
        language_column in df.columns and df[language_column].nunique(dropna=True) >= 2
    )
    if multilingual:
        if df[language_column].isna().any():
            n_nan = int(df[language_column].isna().sum())
            raise SplitError(
                f"{n_nan} rows have NaN in language column "
                f"'{language_column}'; every row must carry a language "
                f"tag when the dataset is multilingual"
            )
        # Joint label x language key (\\x1f separator — never present in a
        # label or BCP-47 tag) so every (label, language) cell is
        # represented across splits, keeping each split — including the
        # sacred test set — representative of the language distribution.
        strat = df[stratify_key].astype(str) + "\x1f" + df[language_column].astype(str)
    else:
        strat = df[stratify_key]

    # Two-step split: peel test off, then split remainder into train/dev.
    test_size = test_pct
    df_remainder, df_test = train_test_split(
        df,
        test_size=test_size,
        random_state=seed,
        stratify=strat,
    )
    # dev's share of the remainder = dev_pct / (train_pct + dev_pct)
    dev_size = dev_pct / (train_pct + dev_pct)
    df_train, df_dev = train_test_split(
        df_remainder,
        test_size=dev_size,
        random_state=seed,
        stratify=strat.loc[df_remainder.index],
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

    # In multilingual mode, also verify every language appears in every
    # partition (DESIGN.md §7.1.7).
    if multilingual:
        all_langs = set(df[language_column].unique())
        for name, partition in (
            ("train", df_train),
            ("dev", df_dev),
            ("test", df_test),
        ):
            present = set(partition[language_column].unique())
            missing = all_langs - present
            if missing:
                raise SplitError(
                    f"partition '{name}' missing languages "
                    f"{sorted(missing)}; increase baseline size or "
                    f"rebalance language coverage"
                )

    splits = SplitsJSON(
        stratification_key=stratify_key,
        seed=seed,
        ratios={"train": train_pct, "dev": dev_pct, "test": test_pct},
        language_stratified=multilingual,
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
    parser.add_argument(
        "--language-column",
        type=str,
        default="language",
        help=(
            "Optional per-row language column (BCP-47). Per-language "
            "stratification auto-activates when it is present with >=2 "
            "distinct values (DESIGN.md §7.1.7)."
        ),
    )
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
            language_column=args.language_column,
        )
    except SplitError as e:
        log.error("split failed: %s", e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
