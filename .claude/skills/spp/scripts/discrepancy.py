"""Generate discrepancy_analysis.md skeleton for /spp-loop.

Mechanically lists disagreed rows for the LLM in /spp-loop's
orchestration to analyze. Does NOT propose rule edits — the LLM
reads the disagreed rows and writes the cluster analysis. The
script's job is to prepare the input material.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd

from ._io import atomic_write_text

log = logging.getLogger(__name__)

INPUT_EXCERPT_LEN = 300
RAW_RESPONSE_TRUNC = 200


class DiscrepancyError(RuntimeError):
    """Fatal error during discrepancy generation; message is user-facing."""


def _truncate(s: str, n: int) -> str:
    s = s.replace("\n", " ").replace("\r", " ")
    if len(s) <= n:
        return s
    return s[:n].rstrip() + "…"


def generate_discrepancy(
    results_path: Path,
    baseline_path: Path,
    eval_path: Path,
    row_ids: list[str],
    out_path: Path,
    iteration: int | None = None,
    label_column: str = "label",
    input_column: str = "input",
    id_column: str = "id",
) -> str:
    """Generate the discrepancy_analysis.md skeleton.

    Returns the rendered markdown text. The aggregate-patterns section
    is empty — the orchestrating LLM populates it.
    """
    for path in (results_path, baseline_path, eval_path):
        if not path.exists():
            raise DiscrepancyError(f"input not found: {path}")

    results = json.loads(results_path.read_text(encoding="utf-8"))
    eval_data = json.loads(eval_path.read_text(encoding="utf-8"))
    df = pd.read_csv(baseline_path)
    if label_column not in df.columns or input_column not in df.columns:
        raise DiscrepancyError(
            f"baseline missing required columns "
            f"(need '{label_column}' and '{input_column}')"
        )
    df_idx = df.set_index(df[id_column].astype(str))

    pred_by_row = {p["row_id"]: p for p in results["predictions"]}
    missing = [rid for rid in row_ids if rid not in pred_by_row]
    if missing:
        raise DiscrepancyError(
            f"{len(missing)} row IDs not in results.json; first missing: {missing[:5]}"
        )

    # Disagreed = parsed_label (after canonical match) != ground truth.
    # We don't redo the canonical match here; eval.py wrote the metric,
    # so we approximate by comparing parsed_label (case-insensitive
    # trim) to ground truth directly. Parse failures count as
    # disagreements.
    label_space = eval_data.get("labels", [])

    def canonicalize(s: str | None) -> str | None:
        if s is None:
            return None
        p = s.strip().lower()
        for canonical in label_space:
            if canonical == "__PARSE_FAILURE__":
                continue
            if p == canonical.strip().lower():
                return canonical
        return None

    disagreed: list[tuple[str, str, str | None, str, str]] = []
    for rid in row_ids:
        pred = pred_by_row[rid]
        truth = str(df_idx.loc[rid][label_column])
        canonical = canonicalize(pred.get("parsed_label"))
        if canonical != truth:
            disagreed.append(
                (
                    rid,
                    truth,
                    canonical,
                    pred.get("raw_response", ""),
                    str(df_idx.loc[rid][input_column]),
                )
            )

    iteration_label = (
        f"Iteration {iteration}" if iteration is not None else "(iteration unspecified)"
    )
    n = len(row_ids)
    m = len(disagreed)
    rate = (100.0 * m / n) if n else 0.0

    lines: list[str] = []
    lines.append(f"# Discrepancy Analysis — {iteration_label}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- {n} dev rows evaluated.")
    lines.append(f"- {m} predictions disagreed with ground truth.")
    lines.append(f"- Failure rate: {rate:.1f}%.")
    lines.append("")
    lines.append("## Disagreed Rows")
    lines.append("")

    if not disagreed:
        lines.append("(none)")
        lines.append("")
    else:
        for rid, truth, canonical, raw, input_text in disagreed:
            pred_display = canonical if canonical is not None else "(parse failure)"
            lines.append(f"### Row {rid}")
            lines.append("")
            lines.append(f"- **Ground truth:** {truth}")
            lines.append(f"- **Prediction:** {pred_display}")
            lines.append(f"- **Raw response:** {_truncate(raw, RAW_RESPONSE_TRUNC)}")
            lines.append(
                f"- **Input excerpt:** {_truncate(input_text, INPUT_EXCERPT_LEN)}"
            )
            lines.append("")

    lines.append("## Aggregate Patterns")
    lines.append("")
    lines.append(
        "(Empty section. The LLM running `/spp-loop` analyzes the "
        "disagreed rows above and populates this section with failure "
        "clusters and proposed rule edits.)"
    )
    lines.append("")

    text = "\n".join(lines)
    atomic_write_text(out_path, text)
    log.info(
        "discrepancy written: %d disagreed of %d rows -> %s",
        m,
        n,
        out_path,
    )
    return text


def _row_ids_from_splits(splits_path: Path, partitions: list[str]) -> list[str]:
    data = json.loads(splits_path.read_text(encoding="utf-8"))
    out: list[str] = []
    for p in partitions:
        if p not in data["row_ids"]:
            raise DiscrepancyError(f"partition '{p}' not in splits.json")
        out.extend(data["row_ids"][p])
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate discrepancy_analysis.md.")
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--eval", dest="eval_path", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)

    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--row-ids", type=str)
    src.add_argument("--row-ids-from", type=Path)
    parser.add_argument("--partition", type=str, default="dev")

    parser.add_argument("--iteration", type=int, default=None)
    parser.add_argument("--label-column", type=str, default="label")
    parser.add_argument("--input-column", type=str, default="input")
    parser.add_argument("--id-column", type=str, default="id")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        if args.row_ids:
            row_ids = [s.strip() for s in args.row_ids.split(",") if s.strip()]
        else:
            partitions = [s.strip() for s in args.partition.split(",") if s.strip()]
            row_ids = _row_ids_from_splits(args.row_ids_from, partitions)

        generate_discrepancy(
            results_path=args.results,
            baseline_path=args.baseline,
            eval_path=args.eval_path,
            row_ids=row_ids,
            out_path=args.out,
            iteration=args.iteration,
            label_column=args.label_column,
            input_column=args.input_column,
            id_column=args.id_column,
        )
    except DiscrepancyError as e:
        log.error("discrepancy generation failed: %s", e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
