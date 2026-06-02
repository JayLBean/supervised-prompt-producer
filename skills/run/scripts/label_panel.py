"""Consensus aggregation and I/O for the v0.7 label panel (DESIGN.md §7.1.8).

The judging is the work of five score-blind Claude subagents; this script
does **only** the mechanical part — it never judges a row. It takes the
collected votes, runs the cross-family gate, tallies consensus, routes
splits to the escalation queue, and writes the audit trail
(``label_panel.json``). A second step writes the frozen ``label`` column
into ``baseline.csv`` once every row has a final label (auto-accepted or
human-resolved).

This runs **before any split exists** and feeds **no** scoring path:
``eval.py`` never reads ``label_panel.json``. The labels it freezes are
read downstream by the same mechanical metric as any other baseline, so
the panel creates ground truth without ever judging a prompt (invariant
#13; ``metric-design`` §5).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ._io import atomic_write_json, atomic_write_text
from ._models import assert_cross_family
from ._schemas import (
    LabelPanelJSON,
    LabelPanelRow,
    LabelPanelSummary,
    LabelVote,
)

_ESCALATED_EVER = ("escalated", "human_resolved")


class LabelPanelError(ValueError):
    """A vote set or panel artifact violated the label-panel contract."""


def _tally(votes: list[LabelVote]) -> tuple[dict[str, int], int, str]:
    """Return (label -> count, plurality count, plurality label).

    Ties on the plurality count are broken by sorted label order so the
    result is deterministic. A tie can only occur *below* the consensus
    threshold (a >=4-of-5 winner is unique), so the tie-break never decides
    an auto-accepted label.
    """
    counts: dict[str, int] = {}
    for v in votes:
        counts[v.label] = counts.get(v.label, 0) + 1
    n_agree = max(counts.values())
    winning = sorted(label for label, c in counts.items() if c == n_agree)[0]
    return counts, n_agree, winning


def _row_language_map(
    baseline_path: Path | None,
    vote_row_ids: list[str],
    id_column: str,
    language_column: str,
) -> dict[str, str | None]:
    """Map each judged row id to its language tag, only when multilingual.

    Mirrors ``eval._language_groups`` activation (DESIGN.md §7.1.7): returns
    ``{}`` unless the baseline carries ``language_column`` with two or more
    distinct non-null values among the judged rows. Monolingual or absent →
    no per-row language is surfaced, exactly as elsewhere in the pipeline.
    """
    if baseline_path is None:
        return {}
    df = pd.read_csv(baseline_path)
    if id_column not in df.columns or language_column not in df.columns:
        return {}
    df_idx = df.set_index(df[id_column].astype(str))
    tags: dict[str, str | None] = {}
    for rid in vote_row_ids:
        if rid not in df_idx.index:
            tags[rid] = None
            continue
        v = df_idx.loc[rid][language_column]
        tags[rid] = None if pd.isna(v) else str(v)
    if len({t for t in tags.values() if t is not None}) < 2:
        return {}
    return tags


def _summarize(rows: list[LabelPanelRow]) -> LabelPanelSummary:
    """Aggregate dispositions and the per-language escalation disclosure.

    ``per_language_escalation`` counts rows that escalated *at any point*
    (``escalated`` or ``human_resolved``) so the count is stable across the
    aggregate -> human-resolution transition. Populated only when two or
    more distinct languages are present among the rows.
    """
    n_auto = sum(r.disposition == "auto_accepted" for r in rows)
    n_esc = sum(r.disposition == "escalated" for r in rows)
    n_hr = sum(r.disposition == "human_resolved" for r in rows)
    n_ho = sum(r.disposition == "human_overridden" for r in rows)

    per_language: dict[str, int] = {}
    langs = {r.language for r in rows if r.language is not None}
    if len(langs) >= 2:
        for r in rows:
            if r.language is None or r.disposition not in _ESCALATED_EVER:
                continue
            per_language[r.language] = per_language.get(r.language, 0) + 1

    return LabelPanelSummary(
        n_rows=len(rows),
        n_auto_accepted=n_auto,
        n_escalated=n_esc,
        n_human_resolved=n_hr,
        n_human_overridden=n_ho,
        per_language_escalation=per_language,
    )


def aggregate_votes(
    raw_votes: dict[str, list[dict[str, str]]],
    production_model: str,
    label_space: list[str],
    *,
    declared_family: str | None = None,
    panel_size: int = 5,
    consensus_threshold: int = 4,
    judge_family: str = "anthropic",
    row_language: dict[str, str | None] | None = None,
) -> LabelPanelJSON:
    """Gate, tally, and route votes into a :class:`LabelPanelJSON`.

    The cross-family gate runs **first**: a same-family panel raises before
    any consensus is computed. Each row must have exactly ``panel_size``
    votes, and every voted label must be in ``label_space``. A row with
    ``>= consensus_threshold`` agreement is ``auto_accepted`` (its
    ``final_label`` set); anything weaker is ``escalated`` (``final_label``
    left ``None`` for human adjudication).
    """
    if consensus_threshold > panel_size:
        raise LabelPanelError(
            f"consensus_threshold ({consensus_threshold}) cannot exceed "
            f"panel_size ({panel_size})."
        )
    space = set(label_space)
    production_family = assert_cross_family(
        production_model, declared_family, judge_family
    )
    langs = row_language or {}

    rows: list[LabelPanelRow] = []
    for row_id, vote_dicts in raw_votes.items():
        votes = [LabelVote(**v) for v in vote_dicts]
        if len(votes) != panel_size:
            raise LabelPanelError(
                f"Row {row_id!r} has {len(votes)} votes; expected {panel_size}."
            )
        bad = sorted({v.label for v in votes} - space)
        if bad:
            raise LabelPanelError(
                f"Row {row_id!r} has votes outside the label space: {bad}. "
                "Judges choose only among the fixed OUTPUT_SCHEMA labels."
            )
        counts, n_agree, winning = _tally(votes)
        accepted = n_agree >= consensus_threshold
        rows.append(
            LabelPanelRow(
                row_id=row_id,
                language=langs.get(row_id),
                votes=votes,
                vote_counts=counts,
                n_agree=n_agree,
                winning_label=winning,
                disposition="auto_accepted" if accepted else "escalated",
                final_label=winning if accepted else None,
            )
        )

    return LabelPanelJSON(
        production_model=production_model,
        production_family=production_family,
        judge_family=judge_family.strip().lower(),
        panel_size=panel_size,
        consensus_threshold=consensus_threshold,
        label_space=list(label_space),
        rows=rows,
        summary=_summarize(rows),
    )


def write_labeled_baseline(
    panel: LabelPanelJSON,
    baseline_path: Path,
    out_path: Path,
    *,
    label_column: str = "label",
    id_column: str = "id",
) -> None:
    """Write the frozen ``label`` column into the baseline.

    Every panel row must carry a ``final_label`` — an unresolved escalation
    is a hard stop, never a silently dropped row. Every baseline row must
    have a panel label, and vice versa, so the labeled baseline is complete
    and the two artifacts cannot drift.
    """
    unresolved = [r.row_id for r in panel.rows if r.final_label is None]
    if unresolved:
        raise LabelPanelError(
            f"{len(unresolved)} row(s) still escalated and unresolved: "
            f"{unresolved[:10]}{' ...' if len(unresolved) > 10 else ''}. "
            "Resolve every escalation before writing the labeled baseline."
        )

    df = pd.read_csv(baseline_path)
    if id_column not in df.columns:
        raise LabelPanelError(f"Baseline has no {id_column!r} column.")
    ids = df[id_column].astype(str)

    labels = {r.row_id: r.final_label for r in panel.rows}
    baseline_ids = set(ids)
    panel_ids = set(labels)
    missing_in_panel = sorted(baseline_ids - panel_ids)
    missing_in_baseline = sorted(panel_ids - baseline_ids)
    if missing_in_panel:
        raise LabelPanelError(
            f"{len(missing_in_panel)} baseline row(s) absent from the panel: "
            f"{missing_in_panel[:10]}."
        )
    if missing_in_baseline:
        raise LabelPanelError(
            f"{len(missing_in_baseline)} panel row(s) absent from the "
            f"baseline: {missing_in_baseline[:10]}."
        )

    df[label_column] = ids.map(labels)
    atomic_write_text(out_path, df.to_csv(index=False))


def build_escalation_queue(
    panel: LabelPanelJSON,
    baseline_path: Path,
    *,
    id_column: str = "id",
    input_column: str = "input",
) -> dict[str, object]:
    """Build the human's adjudication worklist from escalated rows.

    Only ``escalated`` rows appear — this is the *mandatory* review set
    (DESIGN.md §7.1.8). Overriding an already-frozen label is a separate,
    discretionary act the human performs against the full ``label_panel.json``
    audit trail, so frozen rows are deliberately not in the queue. Each entry
    carries the row input, language, all five votes with rationales, the
    tally, and the plurality, so the human can decide without re-deriving
    anything. The decision is applied with :func:`apply_decisions`.
    """
    df = pd.read_csv(baseline_path)
    if id_column not in df.columns:
        raise LabelPanelError(f"Baseline has no {id_column!r} column.")
    df_idx = df.set_index(df[id_column].astype(str))
    has_input = input_column in df.columns

    items: list[dict[str, object]] = []
    for row in panel.rows:
        if row.disposition != "escalated":
            continue
        text = ""
        if has_input and row.row_id in df_idx.index:
            text = str(df_idx.loc[row.row_id][input_column])
        items.append(
            {
                "row_id": row.row_id,
                "language": row.language,
                "input": text,
                "votes": [v.model_dump() for v in row.votes],
                "vote_counts": row.vote_counts,
                "plurality": row.winning_label,
            }
        )
    return {
        "schema_version": "1",
        "label_space": list(panel.label_space),
        "n_escalated": len(items),
        "items": items,
    }


def apply_decisions(panel: LabelPanelJSON, decisions: dict[str, str]) -> LabelPanelJSON:
    """Apply human label decisions, resolving escalations and overrides.

    A decision on an ``escalated`` row resolves it (``human_resolved``); a
    decision that *changes* an already-frozen label is an override
    (``human_overridden``) — the operationalization of "human authority as
    override-plus-visibility," including over any test-set row. A decision
    equal to a row's current label is a no-op and leaves the disposition
    unchanged. Every decided label must be in the panel's label space, and
    every decided row id must exist. The summary is recomputed.
    """
    space = set(panel.label_space)
    by_id = {r.row_id: r for r in panel.rows}
    for row_id, label in decisions.items():
        if row_id not in by_id:
            raise LabelPanelError(f"Decision references unknown row {row_id!r}.")
        if label not in space:
            raise LabelPanelError(
                f"Decision for row {row_id!r} is outside the label space: {label!r}."
            )
        row = by_id[row_id]
        if row.disposition == "escalated":
            row.final_label = label
            row.disposition = "human_resolved"
        elif row.final_label != label:
            row.final_label = label
            row.disposition = "human_overridden"
    panel.summary = _summarize(panel.rows)
    return panel


def _load_votes_file(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise LabelPanelError("Votes file must be a JSON object.")
    for key in ("production_model", "label_space", "votes"):
        if key not in data:
            raise LabelPanelError(f"Votes file missing required key {key!r}.")
    return data


def _cmd_aggregate(args: argparse.Namespace) -> int:
    data = _load_votes_file(args.votes)
    raw_votes = data["votes"]
    if not isinstance(raw_votes, dict):
        raise LabelPanelError("`votes` must map row_id -> list of votes.")
    label_space = data["label_space"]
    if not isinstance(label_space, list):
        raise LabelPanelError("`label_space` must be a list.")
    row_language = _row_language_map(
        args.baseline,
        list(raw_votes.keys()),
        args.id_column,
        args.language_column,
    )
    panel = aggregate_votes(
        raw_votes,
        str(data["production_model"]),
        [str(x) for x in label_space],
        declared_family=(
            str(data["model_family"]) if data.get("model_family") else None
        ),
        panel_size=args.panel_size,
        consensus_threshold=args.consensus_threshold,
        row_language=row_language,
    )
    atomic_write_json(args.out, panel.model_dump())
    s = panel.summary
    print(
        f"label-panel: {s.n_rows} rows | {s.n_auto_accepted} auto-accepted | "
        f"{s.n_escalated} escalated -> {args.out}"
    )
    return 0


def _cmd_write_labels(args: argparse.Namespace) -> int:
    panel = LabelPanelJSON(**json.loads(args.panel.read_text(encoding="utf-8")))
    write_labeled_baseline(
        panel,
        args.baseline,
        args.out,
        label_column=args.label_column,
        id_column=args.id_column,
    )
    print(f"label-panel: wrote {len(panel.rows)} labels -> {args.out}")
    return 0


def _cmd_queue(args: argparse.Namespace) -> int:
    panel = LabelPanelJSON(**json.loads(args.panel.read_text(encoding="utf-8")))
    queue = build_escalation_queue(
        panel,
        args.baseline,
        id_column=args.id_column,
        input_column=args.input_column,
    )
    atomic_write_json(args.out, queue)
    print(f"label-panel: {queue['n_escalated']} row(s) to adjudicate -> {args.out}")
    return 0


def _cmd_resolve(args: argparse.Namespace) -> int:
    panel = LabelPanelJSON(**json.loads(args.panel.read_text(encoding="utf-8")))
    raw = json.loads(args.decisions.read_text(encoding="utf-8"))
    decisions = raw.get("decisions", raw) if isinstance(raw, dict) else None
    if not isinstance(decisions, dict):
        raise LabelPanelError("Decisions file must map row_id -> label.")
    updated = apply_decisions(panel, {str(k): str(v) for k, v in decisions.items()})
    atomic_write_json(args.out, updated.model_dump())
    s = updated.summary
    print(
        f"label-panel: applied {len(decisions)} decision(s) | "
        f"{s.n_human_resolved} resolved | {s.n_human_overridden} overridden | "
        f"{s.n_escalated} still escalated -> {args.out}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate label-panel votes and write frozen labels."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    agg = sub.add_parser("aggregate", help="Tally votes into label_panel.json.")
    agg.add_argument("--votes", type=Path, required=True)
    agg.add_argument("--out", type=Path, required=True)
    agg.add_argument("--baseline", type=Path, default=None)
    agg.add_argument("--panel-size", type=int, default=5)
    agg.add_argument("--consensus-threshold", type=int, default=4)
    agg.add_argument("--id-column", type=str, default="id")
    agg.add_argument("--language-column", type=str, default="language")
    agg.set_defaults(func=_cmd_aggregate)

    wl = sub.add_parser("write-labels", help="Write frozen labels into the baseline.")
    wl.add_argument("--panel", type=Path, required=True)
    wl.add_argument("--baseline", type=Path, required=True)
    wl.add_argument("--out", type=Path, required=True)
    wl.add_argument("--label-column", type=str, default="label")
    wl.add_argument("--id-column", type=str, default="id")
    wl.set_defaults(func=_cmd_write_labels)

    q = sub.add_parser(
        "queue", help="Build the human adjudication worklist (escalated rows)."
    )
    q.add_argument("--panel", type=Path, required=True)
    q.add_argument("--baseline", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True)
    q.add_argument("--id-column", type=str, default="id")
    q.add_argument("--input-column", type=str, default="input")
    q.set_defaults(func=_cmd_queue)

    rs = sub.add_parser(
        "resolve", help="Apply human decisions (resolve splits / override labels)."
    )
    rs.add_argument("--panel", type=Path, required=True)
    rs.add_argument("--decisions", type=Path, required=True)
    rs.add_argument("--out", type=Path, required=True)
    rs.set_defaults(func=_cmd_resolve)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
