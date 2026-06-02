"""End-to-end multilingual pipeline: preprocess -> split -> eval.

Exercises the v0.6 facets composing across the three stages (DESIGN.md
§7.1.7): the sample `preprocess.py` canonicalizes a raw multilingual
export (mapping a `lang` column to BCP-47 `language`), `split.py`
language-stratifies, and `eval.py` emits the per-language slice — all
keyed off the one canonical `language` column.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from spp_scripts.eval import compute_eval
from spp_scripts.split import make_splits

_PREPROCESS = (
    Path(__file__).resolve().parents[2]
    / "sub-skills"
    / "preprocess"
    / "fixtures"
    / "multilingual-reviews"
    / "preprocess.py"
)


def _raw(path: Path) -> None:
    """40 rows: 2 languages x 2 labels x 10, in the sample's raw schema."""
    rows = []
    i = 0
    for lang in ("English", "Spanish"):
        for stars in ("positive", "negative"):
            for _ in range(10):
                rows.append(
                    {
                        "review_id": f"r{i:03d}",
                        "body": f"text {i}",
                        "stars_label": stars,
                        "lang": lang,
                    }
                )
                i += 1
    pd.DataFrame(rows).to_csv(path, index=False)


def test_preprocess_split_eval_multilingual(tmp_path: Path) -> None:
    raw = tmp_path / "raw.csv"
    baseline = tmp_path / "baseline.csv"
    _raw(raw)

    # 1) preprocess: raw -> canonical (id/input/label/language).
    result = subprocess.run(
        [sys.executable, str(_PREPROCESS), "--raw", str(raw), "--out", str(baseline)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    canon = pd.read_csv(baseline)
    assert list(canon.columns) == ["id", "input", "label", "language"]
    assert set(canon["language"]) == {"en", "es"}

    # 2) split: language-stratified because the canonical data is multilingual.
    splits_path = tmp_path / "splits.json"
    splits = make_splits(baseline, "label", 42, (0.6, 0.2, 0.2), splits_path)
    assert splits.language_stratified is True
    df = pd.read_csv(baseline)
    df.index = df["id"].astype(str)
    for ids in (splits.row_ids.train, splits.row_ids.dev, splits.row_ids.test):
        assert set(df.loc[ids]["language"]) == {"en", "es"}

    # 3) eval: build a perfect-prediction results.json, score dev.
    preds = [
        {
            "row_id": rid,
            "raw_response": lbl,
            "parsed_label": lbl,
            "parse_error": None,
            "latency_ms": 1,
            "tokens_used": 1,
        }
        for rid, lbl in zip(df["id"].astype(str), df["label"].astype(str), strict=True)
    ]
    results_path = tmp_path / "results.json"
    results_path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "model": "t",
                "prompt_path": "p",
                "prompt_sha256": "h",
                "predictions": preds,
                "summary": {
                    "n_rows": len(preds),
                    "n_parsed": len(preds),
                    "n_parse_failures": 0,
                    "total_tokens": len(preds),
                    "total_latency_ms": len(preds),
                    "wall_clock_ms": 1,
                },
            }
        )
    )
    e = compute_eval(
        results_path, baseline, splits.row_ids.dev, "accuracy", tmp_path / "eval.json"
    )
    assert set(e.per_language) == {"en", "es"}
    assert e.per_language["en"].primary_value == 1.0
    assert e.per_language["es"].primary_value == 1.0
    assert e.primary_value == 1.0
