"""Generate discrepancy_analysis.md skeleton for /spp-loop.

Mechanically lists disagreed row IDs (with predicted/ground-truth
labels) for the discrepancy subagent in /spp-loop's orchestration
to analyze. Does NOT propose rule edits and does NOT embed row
content — the subagent reads `data/baseline.csv` filtered to the
disagreed row IDs directly per its allow-list (per /spp-loop.md §4
step 8) and writes the cluster analysis with rows referenced by ID
only.

The persistent artifact must reference rows by ID only because the
rule-edit subagent at the next stage receives this artifact under
its allow-list and is forbidden from row-content exposure (per
/spp-loop.md §4 step 10's per-stage information-isolation
discipline). Embedding row content excerpts would reintroduce the
leakage mode this revision was designed to prevent.
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


class DiscrepancyError(RuntimeError):
    """Fatal error during discrepancy generation; message is user-facing."""


def generate_discrepancy(
    results_path: Path,
    baseline_path: Path,
    eval_path: Path,
    row_ids: list[str],
    out_path: Path,
    iteration: int | None = None,
    label_column: str = "label",
    id_column: str = "id",
    language_column: str = "language",
) -> str:
    """Generate the discrepancy_analysis.md skeleton.

    Lists disagreed row IDs with predicted/ground-truth labels only.
    Row content is **not** embedded — the discrepancy subagent reads
    rows directly from baseline.csv per its allow-list. The persistent
    artifact stays content-free so the rule-edit subagent (next stage,
    no row-content access) is not exposed to row content through it.

    Returns the rendered markdown text. The aggregate-patterns section
    is empty — the discrepancy subagent populates it.
    """
    for path in (results_path, baseline_path, eval_path):
        if not path.exists():
            raise DiscrepancyError(f"input not found: {path}")

    results = json.loads(results_path.read_text(encoding="utf-8"))
    eval_data = json.loads(eval_path.read_text(encoding="utf-8"))
    df = pd.read_csv(baseline_path)
    if label_column not in df.columns:
        raise DiscrepancyError(
            f"baseline missing required label column '{label_column}'"
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

    disagreed: list[tuple[str, str, str | None]] = []
    for rid in row_ids:
        pred = pred_by_row[rid]
        truth = str(df_idx.loc[rid][label_column])
        canonical = canonicalize(pred.get("parsed_label"))
        if canonical != truth:
            disagreed.append((rid, truth, canonical))

    # Per-language failure rate (DESIGN §7.1.7): data-driven — only when the
    # baseline carries a `language` column with >=2 distinct values among the
    # evaluated rows. Counts only, so no row content enters the artifact; it
    # gives the discrepancy subagent the which-language-fails signal directly.
    lang_lines: list[str] = []
    if language_column in df.columns:
        row_lang = {rid: df_idx.loc[rid][language_column] for rid in row_ids}
        if len({str(v) for v in row_lang.values() if pd.notna(v)}) >= 2:
            disagreed_ids = {rid for rid, _, _ in disagreed}
            per_lang: dict[str, list[int]] = {}  # lang -> [total, disagreed]
            for rid in row_ids:
                v = row_lang[rid]
                key = str(v) if pd.notna(v) else "unknown"
                cell = per_lang.setdefault(key, [0, 0])
                cell[0] += 1
                if rid in disagreed_ids:
                    cell[1] += 1
            for lang in sorted(per_lang):
                tot, dis = per_lang[lang]
                r = (100.0 * dis / tot) if tot else 0.0
                lang_lines.append(f"  - `{lang}`: {dis}/{tot} disagreed ({r:.1f}%).")

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
    if lang_lines:
        lines.append("- Per-language failure rate (DESIGN §7.1.7):")
        lines.extend(lang_lines)
    lines.append("")
    lines.append("## Disagreed Rows (IDs only)")
    lines.append("")

    if not disagreed:
        lines.append("(none)")
        lines.append("")
    else:
        for rid, truth, canonical in disagreed:
            pred_display = canonical if canonical is not None else "(parse failure)"
            lines.append(f"- `{rid}`: predicted {pred_display}, ground truth {truth}")
        lines.append("")

    lines.append("## Aggregate Patterns")
    lines.append("")
    lines.append(
        "(Empty section. The discrepancy subagent will analyze the "
        "disagreed rows by reading them directly from `data/baseline.csv` "
        "and populate this section with failure clusters and proposed "
        "rule edits, referenced by row ID. Row content does not appear "
        "in this artifact — the next stage's rule-edit subagent has no "
        "row-content access by contract.)"
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
    parser.add_argument("--id-column", type=str, default="id")
    parser.add_argument("--language-column", type=str, default="language")
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
            id_column=args.id_column,
            language_column=args.language_column,
        )
    except DiscrepancyError as e:
        log.error("discrepancy generation failed: %s", e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
