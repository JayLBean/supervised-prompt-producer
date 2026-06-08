"""Pipeline mechanics for v0.11 decomposition (DESIGN §7.1.12).

A decomposition pipeline is a **linear chain** of nodes — node 1 -> 2 -> ... ->
terminal — each a self-contained spp task with its own node-local gold. This
module holds the reusable, model-free mechanics the phases drive:

- ``load_pipeline_spec`` — parse and **validate** the machine-readable pipeline
  config (the runnable form of ``pipeline.md``), enforcing the pipeline.md
  validation rules in code: a linear chain, node 1 with no upstream, upstream
  references that point only to earlier nodes, and a composite metric in the
  documented set.
- ``materialize_node_inputs`` — produce a downstream node's baseline by
  attaching the **frozen upstream output** as input columns, keyed by row id.
  This is the data-plane dependency of §7.1.12 (the deployed pipeline has it
  too); it carries no scores and reaches no isolated cognitive stage.
- ``compute_composite`` — roll per-node primary metrics into one composite
  (``terminal`` / ``mean`` / ``weighted`` / ``min``), the headline number the
  pipeline's finalize reports alongside the per-node scores.

The chain orchestration that calls ``run_inference`` per node, freezing
upstream between nodes, lives with the phase wiring (it is what
``/spp-baseline`` and ``/spp-loop`` drive); this module is the mechanics it
composes. No model runs here — every function is a pure transform of data
already in hand, so the per-stage isolation contract is untouched.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel

COMPOSITE_METRICS = frozenset({"terminal", "mean", "weighted", "min"})


class PipelineError(RuntimeError):
    """Malformed pipeline spec or materialization input; message is user-facing."""


class PipelineNodeSpec(BaseModel):
    """One node of a linear pipeline.

    ``input_columns`` are the original baseline columns the node reads.
    ``upstream_inputs`` maps a downstream input-column name to the
    ``"<upstream_node_id>.<output_field>"`` it is materialized from; empty for
    node 1 (nothing precedes it).
    """

    id: str
    input_columns: list[str] = []
    upstream_inputs: dict[str, str] = {}


class PipelineSpec(BaseModel):
    """A validated linear pipeline: ordered nodes plus the composite rule."""

    nodes: list[PipelineNodeSpec]
    composite_metric: str = "terminal"
    composite_weights: dict[str, float] | None = None


def load_pipeline_spec(data: dict[str, Any]) -> PipelineSpec:
    """Parse and validate a pipeline config dict (the runnable form of pipeline.md).

    Enforces the pipeline.md validation rules (DESIGN §7.1.12): a linear chain of
    at least two nodes with unique ids; node 1 declares no upstream input; every
    upstream reference ``"<node>.<field>"`` names a node that appears *earlier*
    in the order (so the chain is acyclic and strictly forward); and the
    composite metric is one of ``terminal`` / ``mean`` / ``weighted`` / ``min``
    (``weighted`` requires weights). Raises ``PipelineError`` on any violation.
    """
    raw_nodes = data.get("nodes")
    if not isinstance(raw_nodes, list) or len(raw_nodes) < 2:
        raise PipelineError("pipeline must declare a list of at least two nodes")
    nodes = [PipelineNodeSpec(**n) for n in raw_nodes]

    ids = [n.id for n in nodes]
    if len(set(ids)) != len(ids):
        raise PipelineError(f"node ids must be unique; got {ids}")

    if nodes[0].upstream_inputs:
        raise PipelineError(
            f"node 1 ('{nodes[0].id}') reads only original columns; "
            "it must declare no upstream_inputs (nothing precedes it)"
        )

    # Every upstream reference must point to a node earlier in the order — this
    # is what makes the chain linear and acyclic (no DAGs, no forward refs).
    seen: set[str] = set()
    for node in nodes:
        for col, ref in node.upstream_inputs.items():
            if "." not in ref:
                raise PipelineError(
                    f"node '{node.id}' input '{col}': upstream ref '{ref}' must "
                    "be '<node_id>.<output_field>'"
                )
            up_id = ref.split(".", 1)[0]
            if up_id not in seen:
                raise PipelineError(
                    f"node '{node.id}' input '{col}' references '{up_id}', which "
                    "is not an earlier node in the chain"
                )
        seen.add(node.id)

    metric = str(data.get("composite_metric", "terminal"))
    if metric not in COMPOSITE_METRICS:
        raise PipelineError(
            f"composite_metric '{metric}' not supported; "
            f"one of {sorted(COMPOSITE_METRICS)}"
        )
    weights = data.get("composite_weights")
    if metric == "weighted" and not weights:
        raise PipelineError("composite_metric 'weighted' requires composite_weights")

    return PipelineSpec(nodes=nodes, composite_metric=metric, composite_weights=weights)


def materialize_node_inputs(
    base_df: pd.DataFrame,
    node: PipelineNodeSpec,
    upstream_outputs: dict[str, dict[str, Any]],
    id_column: str = "row_id",
) -> pd.DataFrame:
    """Attach a node's frozen upstream outputs as input columns, keyed by row id.

    ``base_df`` is the node's own baseline (its row ids, original input columns,
    and node-local gold). ``upstream_outputs`` maps an upstream
    ``"<node_id>.<field>"`` reference to a ``{row_id: value}`` dict (the frozen
    upstream node's parsed output for that field). Returns a copy of ``base_df``
    with one new column per ``node.upstream_inputs`` entry. A row whose upstream
    value is missing raises ``PipelineError`` — a materialization gap is a hard
    failure, not a silently empty input.
    """
    df = base_df.copy()
    ids = df[id_column].astype(str).tolist()
    for col, ref in node.upstream_inputs.items():
        values = upstream_outputs.get(ref)
        if values is None:
            raise PipelineError(
                f"node '{node.id}': no materialized upstream output for '{ref}'"
            )
        missing = [rid for rid in ids if rid not in values]
        if missing:
            raise PipelineError(
                f"node '{node.id}' input '{col}' ({ref}): no upstream value for "
                f"{len(missing)} row(s); first: {missing[:5]}"
            )
        df[col] = [values[rid] for rid in ids]
    return df


def compute_composite(
    per_node: list[tuple[str, float]],
    strategy: str = "terminal",
    weights: dict[str, float] | None = None,
) -> float:
    """Roll ordered per-node primary metrics into one composite (DESIGN §7.1.12).

    ``per_node`` is ``[(node_id, primary_value), ...]`` in pipeline order, so the
    last entry is the terminal node. ``terminal`` returns the terminal node's
    value; ``mean`` the unweighted mean; ``weighted`` the weighted mean (a
    node's missing weight defaults to 1.0); ``min`` the worst node. Per-node
    scores are reported separately by the caller; this is only the headline.
    """
    if not per_node:
        raise PipelineError("no per-node values to compose")
    if strategy not in COMPOSITE_METRICS:
        raise PipelineError(
            f"composite strategy '{strategy}' not supported; "
            f"one of {sorted(COMPOSITE_METRICS)}"
        )
    values = [v for _, v in per_node]
    if strategy == "terminal":
        return per_node[-1][1]
    if strategy == "mean":
        return sum(values) / len(values)
    if strategy == "min":
        return min(values)
    w = {nid: float((weights or {}).get(nid, 1.0)) for nid, _ in per_node}
    total = sum(w.values())
    if total == 0:
        raise PipelineError("weighted composite has zero total weight")
    return sum(v * w[nid] for nid, v in per_node) / total
