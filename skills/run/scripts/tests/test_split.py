"""Smoke tests for split.py."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spp_scripts.split import SplitError, make_splits


def _baseline(tmp_path: Path, n: int = 50) -> Path:
    rows = []
    # 30 Relevant, 20 Not Relevant — stratifiable.
    for i in range(n):
        label = "Relevant" if i < (n * 3 // 5) else "Not Relevant"
        rows.append({"id": f"row_{i:03d}", "input": f"text {i}", "label": label})
    df = pd.DataFrame(rows)
    p = tmp_path / "baseline.csv"
    df.to_csv(p, index=False)
    return p


def test_split_basic(tmp_path: Path) -> None:
    base = _baseline(tmp_path)
    out = tmp_path / "splits.json"
    splits = make_splits(
        baseline_path=base,
        stratify_key="label",
        seed=42,
        ratios=(0.6, 0.2, 0.2),
        out_path=out,
    )
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["seed"] == 42
    assert data["stratification_key"] == "label"
    train, dev, test = (
        splits.row_ids.train,
        splits.row_ids.dev,
        splits.row_ids.test,
    )
    # Disjoint and complete.
    all_ids = set(train) | set(dev) | set(test)
    assert len(all_ids) == 50
    assert len(set(train) & set(dev)) == 0
    assert len(set(dev) & set(test)) == 0
    assert len(set(train) & set(test)) == 0


def test_split_deterministic(tmp_path: Path) -> None:
    base = _baseline(tmp_path)
    out1 = tmp_path / "s1.json"
    out2 = tmp_path / "s2.json"
    s1 = make_splits(base, "label", 7, (0.6, 0.2, 0.2), out1)
    s2 = make_splits(base, "label", 7, (0.6, 0.2, 0.2), out2)
    assert s1.row_ids.train == s2.row_ids.train
    assert s1.row_ids.dev == s2.row_ids.dev
    assert s1.row_ids.test == s2.row_ids.test


def test_split_all_classes_in_partitions(tmp_path: Path) -> None:
    base = _baseline(tmp_path)
    out = tmp_path / "splits.json"
    splits = make_splits(base, "label", 42, (0.6, 0.2, 0.2), out)
    df = pd.read_csv(base).set_index(pd.read_csv(base)["id"].astype(str))
    for partition_name, ids in [
        ("train", splits.row_ids.train),
        ("dev", splits.row_ids.dev),
        ("test", splits.row_ids.test),
    ]:
        labels = set(df.loc[ids]["label"])
        assert labels == {"Relevant", "Not Relevant"}, (
            f"partition {partition_name} missing classes: {labels}"
        )


def test_split_missing_stratify_key(tmp_path: Path) -> None:
    base = _baseline(tmp_path)
    with pytest.raises(SplitError, match="stratification key"):
        make_splits(base, "no_such_column", 42, (0.6, 0.2, 0.2), tmp_path / "s.json")


def test_split_ratio_mismatch(tmp_path: Path) -> None:
    base = _baseline(tmp_path)
    with pytest.raises(SplitError, match="ratios must sum to 1.0"):
        make_splits(base, "label", 42, (0.5, 0.2, 0.2), tmp_path / "s.json")


def test_split_baseline_missing(tmp_path: Path) -> None:
    with pytest.raises(SplitError, match="baseline not found"):
        make_splits(
            tmp_path / "nope.csv", "label", 42, (0.6, 0.2, 0.2), tmp_path / "s.json"
        )


# ---- v0.6 multilingual stratification (DESIGN.md §7.1.7) ------------------


def _multilingual_baseline(tmp_path: Path, langs: tuple[str, ...]) -> Path:
    """Balanced baseline across labels x languages (10 rows per cell)."""
    rows = []
    i = 0
    for lang in langs:
        for label in ("Relevant", "Not Relevant"):
            for _ in range(10):
                rows.append(
                    {
                        "id": f"row_{i:03d}",
                        "input": f"text {i}",
                        "label": label,
                        "language": lang,
                    }
                )
                i += 1
    df = pd.DataFrame(rows)
    p = tmp_path / "baseline.csv"
    df.to_csv(p, index=False)
    return p


def test_split_multilingual_activates_and_covers(tmp_path: Path) -> None:
    base = _multilingual_baseline(tmp_path, ("en", "es", "de"))
    out = tmp_path / "splits.json"
    splits = make_splits(base, "label", 42, (0.6, 0.2, 0.2), out)
    assert splits.language_stratified is True
    data = json.loads(out.read_text())
    assert data["language_stratified"] is True

    df = pd.read_csv(base)
    df.index = df["id"].astype(str)
    for name, ids in (
        ("train", splits.row_ids.train),
        ("dev", splits.row_ids.dev),
        ("test", splits.row_ids.test),
    ):
        langs = set(df.loc[ids]["language"])
        assert langs == {"en", "es", "de"}, f"{name} missing languages: {langs}"
        labels = set(df.loc[ids]["label"])
        assert labels == {"Relevant", "Not Relevant"}


def test_split_single_language_short_circuits(tmp_path: Path) -> None:
    # A `language` column with one distinct value is monolingual: the flag
    # stays False and behavior matches the label-only split.
    base = _multilingual_baseline(tmp_path, ("en",))
    out = tmp_path / "splits.json"
    splits = make_splits(base, "label", 42, (0.6, 0.2, 0.2), out)
    assert splits.language_stratified is False


def test_split_no_language_column_is_monolingual(tmp_path: Path) -> None:
    base = _baseline(tmp_path)
    out = tmp_path / "splits.json"
    splits = make_splits(base, "label", 42, (0.6, 0.2, 0.2), out)
    assert splits.language_stratified is False


def test_split_multilingual_nan_language_errors(tmp_path: Path) -> None:
    base = _multilingual_baseline(tmp_path, ("en", "es"))
    df = pd.read_csv(base)
    df.loc[0, "language"] = None  # one missing tag in multilingual data
    df.to_csv(base, index=False)
    with pytest.raises(SplitError, match="NaN in language column"):
        make_splits(base, "label", 42, (0.6, 0.2, 0.2), tmp_path / "s.json")


def test_split_multilingual_deterministic(tmp_path: Path) -> None:
    base = _multilingual_baseline(tmp_path, ("en", "es", "de"))
    s1 = make_splits(base, "label", 7, (0.6, 0.2, 0.2), tmp_path / "s1.json")
    s2 = make_splits(base, "label", 7, (0.6, 0.2, 0.2), tmp_path / "s2.json")
    assert s1.row_ids.train == s2.row_ids.train
    assert s1.row_ids.dev == s2.row_ids.dev
    assert s1.row_ids.test == s2.row_ids.test
