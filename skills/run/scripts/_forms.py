"""Output-form reconstruction for adopted prompting techniques (DESIGN §7.1.6).

When a user adopts a `technique-advisor` technique (one-vs-rest or gated-boolean),
a logical field is emitted across *several* OUTPUT_SCHEMA keys rather than one:

- **one-vs-rest (`per_label_binary`).** A multi-select field `tags` is emitted as
  one boolean per candidate label (`tag_urgent: true`, `tag_vip: false`, …). The
  effective predicted set is the union of the labels whose booleans are truthy.
- **gated-boolean (`gated_single_select` / `gated_per_label_binary`).** A field is
  split into an is-addressed boolean gate plus a conditional sub-field. When the
  gate is false the effective value is "nothing" (empty); when true it is the
  sub-field's value (a single select, or — for `gated_per_label_binary` — the
  union of its per-label booleans).

This module reconstructs the **effective predicted value** for the logical field
from its constituent parsed keys, so the existing per-field metrics score it
unchanged (`set_f1` for the union forms, the field's own metric for a gated
single-select). It adds field-shape handling, not a new metric family
(DESIGN §7.1.6): ``inference.py`` already parses the constituent keys as ordinary
top-level fields; reconstruction is a scoring-time concern only. No new dependency.
"""

from __future__ import annotations

import json
from typing import Any


class FormError(RuntimeError):
    """Malformed output-form spec; message is user-facing."""


# Recognized output forms (technique-advisor catalog `output_form` values).
PER_LABEL_BINARY = "per_label_binary"
GATED_SINGLE_SELECT = "gated_single_select"
GATED_PER_LABEL_BINARY = "gated_per_label_binary"
SUPPORTED_FORMS = frozenset(
    {PER_LABEL_BINARY, GATED_SINGLE_SELECT, GATED_PER_LABEL_BINARY}
)

# Truthy string renderings a boolean gate / per-label flag may take. inference.py
# stringifies JSON booleans to "true"/"false"; models also emit "yes"/"1".
_TRUTHY = frozenset({"true", "yes", "y", "1"})


def _truthy(value: str | None) -> bool:
    """Whether a stringified boolean prediction counts as ``true``.

    Unparseable / absent values are false — a missing gate routes to "not
    addressed", matching the gated-boolean intent (abstain rather than attract).
    """
    if value is None:
        return False
    return value.strip().lower() in _TRUTHY


def _union_positives(
    parsed: dict[str, str | None], labels: dict[str, str]
) -> list[str]:
    """Union the labels whose per-label boolean is truthy (one-vs-rest).

    ``labels`` maps each schema key to the catalog label it stands for, e.g.
    ``{"tag_urgent": "urgent", "tag_vip": "vip"}``. The result is the predicted
    set, JSON-encoded so the existing ``set_f1`` consumes it like any list field.
    """
    out = [label for key, label in labels.items() if _truthy(parsed.get(key))]
    return out


def _encode(value: list[str] | str) -> str:
    """Render a reconstructed value the way ``inference.py`` renders parsed fields.

    Lists become compact sorted JSON (matching ``_parse_structured``), so the
    metric layer's ``_as_set`` parses them identically to a directly-parsed field.
    Scalars pass through as their string form.
    """
    if isinstance(value, list):
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    return value


def reconstruct_field(form: dict[str, Any], parsed: dict[str, str | None]) -> str:
    """Reconstruct one logical field's effective predicted value from its keys.

    ``form`` is the field's ``output_form`` spec (see module docstring / the
    example configs). ``parsed`` is one row's ``parsed_fields`` from results.json.
    Returns the effective value as a string, in the same rendering the metric
    layer expects for a directly-parsed field. Raises ``FormError`` on a malformed
    spec (missing keys), never on a missing prediction — an absent constituent key
    scores as a negative / "not addressed", not a crash.
    """
    ftype = form.get("type")
    if ftype not in SUPPORTED_FORMS:
        raise FormError(
            f"output_form type '{ftype}' not supported; "
            f"supported: {sorted(SUPPORTED_FORMS)}"
        )

    if ftype == PER_LABEL_BINARY:
        labels = form.get("labels")
        if not isinstance(labels, dict) or not labels:
            raise FormError(
                f"{PER_LABEL_BINARY} form requires a non-empty 'labels' map "
                "{schema_key: label}"
            )
        return _encode(_union_positives(parsed, labels))

    # Gated forms: a boolean gate plus a conditional sub-field.
    gate_key = form.get("gate")
    if not isinstance(gate_key, str) or not gate_key:
        raise FormError(f"{ftype} form requires a 'gate' key naming the boolean")
    if not _truthy(parsed.get(gate_key)):
        # Gate closed → "not addressed": empty set for the per-label variant,
        # the empty string for the single-select variant.
        return _encode([]) if ftype == GATED_PER_LABEL_BINARY else ""

    if ftype == GATED_SINGLE_SELECT:
        sub_key = form.get("sub_field")
        if not isinstance(sub_key, str) or not sub_key:
            raise FormError(f"{GATED_SINGLE_SELECT} form requires a 'sub_field' key")
        return parsed.get(sub_key) or ""

    # GATED_PER_LABEL_BINARY: union the sub-field's per-label booleans.
    labels = form.get("labels")
    if not isinstance(labels, dict) or not labels:
        raise FormError(
            f"{GATED_PER_LABEL_BINARY} form requires a non-empty 'labels' map"
        )
    return _encode(_union_positives(parsed, labels))


def constituent_keys(form: dict[str, Any]) -> list[str]:
    """The OUTPUT_SCHEMA keys a form consumes — for parse-failure accounting.

    A reconstructed field counts as a parse failure for a row when *none* of its
    constituent keys parsed (the model emitted nothing usable for the field).
    """
    ftype = form.get("type")
    if ftype == PER_LABEL_BINARY:
        return list((form.get("labels") or {}).keys())
    keys: list[str] = []
    gate = form.get("gate")
    if isinstance(gate, str):
        keys.append(gate)
    if ftype == GATED_SINGLE_SELECT and isinstance(form.get("sub_field"), str):
        keys.append(form["sub_field"])
    if ftype == GATED_PER_LABEL_BINARY:
        keys.extend((form.get("labels") or {}).keys())
    return keys
