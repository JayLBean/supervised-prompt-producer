"""Deterministic model -> family resolution and the cross-family gate.

The v0.7 label panel (DESIGN.md §7.1.8) judges baseline labels with five
Claude Code subagents (the Anthropic family). The cross-family guarantee —
the load-bearing property of the whole protocol — holds only when the
panel is a *different* family than the model being optimized: same-family
judges launder the predictor's own bias as "consensus," and majority vote
then reduces variance without touching that bias.

This module resolves a model string to a family **deterministically**
(never an LLM guess), and the gate hard-blocks when the production model
and the judge panel share a family. A recognized model classifies itself;
an *unrecognized* model is never silently passed — the caller must supply
an explicit ``model_family`` (from ``plan.md``) instead.
"""

from __future__ import annotations

# Ordered (substring, family) patterns matched against the lowercased model
# string. A recognized match wins over any declared family, so a human
# cannot mislabel a known model to bypass the gate; the declared family is
# strictly the fallback for an *unrecognized* string. Substrings are chosen
# to be unambiguous within current model naming; extend with care.
_MODEL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("claude", "anthropic"),
    ("gpt", "openai"),
    ("chatgpt", "openai"),
    ("davinci", "openai"),
    ("o1-", "openai"),
    ("o3-", "openai"),
    ("o4-", "openai"),
    ("gemini", "google"),
    ("gemma", "google"),
    ("palm", "google"),
    ("bison", "google"),
    ("llama", "meta"),
    ("mixtral", "mistral"),
    ("mistral", "mistral"),
    ("codestral", "mistral"),
    ("command", "cohere"),
    ("cohere", "cohere"),
    ("deepseek", "deepseek"),
    ("grok", "xai"),
    ("qwen", "qwen"),
)


class UnknownModelFamilyError(ValueError):
    """The production model could not be resolved and no family was declared.

    Raised when the model string matches no known pattern and the caller
    supplied no ``declared_family``. The methodology refuses to default an
    unknown model to a passing family — the human must record an explicit
    ``model_family`` in ``plan.md`` so the gate decision is on record.
    """

    def __init__(self, model: str) -> None:
        self.model = model
        super().__init__(
            f"Could not resolve a model family for {model!r}. The cross-family "
            "gate must not guess. Record an explicit `model_family` in plan.md "
            "(e.g. anthropic, openai, google, meta) and pass it as "
            "declared_family."
        )


class SameFamilyError(ValueError):
    """The production model and the judge panel are the same family.

    The cross-family guarantee fails, so the gate hard-blocks rather than
    produce a silently contaminated baseline. The two honest options are to
    label by hand, or to bring a judge panel from a different family than
    the production model.
    """

    def __init__(self, model: str, family: str, judge_family: str) -> None:
        self.model = model
        self.family = family
        self.judge_family = judge_family
        super().__init__(
            f"Cross-family gate blocked: production model {model!r} resolves to "
            f"family {family!r}, the same family as the judge panel "
            f"({judge_family!r}). Five same-family judges are not a cross-family "
            "panel — 'consensus' would launder the predictor's own bias. "
            "Either label by hand, or use a judge panel from a different "
            "family than the production model."
        )


def resolve_family(model: str, declared_family: str | None = None) -> str:
    """Resolve ``model`` to a canonical (lowercased) family string.

    A recognized model classifies itself and that match **wins** over any
    ``declared_family`` — a human cannot relabel a known model to slip past
    the gate. ``declared_family`` is used only when the model string matches
    no known pattern. An unrecognized model with no declared family raises
    :class:`UnknownModelFamilyError`; the resolution never guesses.
    """
    normalized = model.strip().lower()
    for substring, family in _MODEL_PATTERNS:
        if substring in normalized:
            return family
    if declared_family is not None and declared_family.strip():
        return declared_family.strip().lower()
    raise UnknownModelFamilyError(model)


def assert_cross_family(
    production_model: str,
    declared_family: str | None = None,
    judge_family: str = "anthropic",
) -> str:
    """Resolve and gate the production model against the judge family.

    Returns the resolved production family (to record in ``label_panel.json``)
    when the gate passes. Raises :class:`SameFamilyError` when the production
    model is the same family as the judge panel, or
    :class:`UnknownModelFamilyError` when the model cannot be resolved and no
    family was declared.
    """
    family = resolve_family(production_model, declared_family)
    if family == judge_family.strip().lower():
        raise SameFamilyError(production_model, family, judge_family.strip().lower())
    return family
