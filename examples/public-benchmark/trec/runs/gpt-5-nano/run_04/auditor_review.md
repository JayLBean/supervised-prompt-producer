# Auditor review — run_04 (edits proposed in run_03 → prompt_v04)

Score-blind auditor. Verdicts judge categorical vs. row-specific only.

## Verdicts

### Edit 1 — Ordered decision procedure (`<decision_order>`)
Verdict: **categorical** — advance. The order Expression→Location→Human→Number→else-Entity/Description is a general answer-type taxonomy precedence that names zero rows and applies to any unseen question. It restructures HOW the existing six-class rules are applied (resolving overlap by precedence), adds no new class content, and keeping Expression tight (abbreviation/acronym only) actively guards against memorizing word-specific answers. Precedence ordering is a legitimate categorical generalization, not smuggled dataset bias.

### Edit 2 — Tie-break clarifications
Verdict: **categorical** — advance. Both clarifications assert class-membership principles by abstract type ("a named company/group is Human even when phrased 'the X that did Y'"; "a country/city/place answer is Location even when a specific named place/object is asked for"), using placeholders rather than any actual acronym/place/person/company. They generalize the Human-vs-Entity and Location-vs-Entity boundaries and do not patch particular rows.

## Summary
Categorical: 2 / Row-specific: 0 / Unclear: 0. Both advance. **No override needed** — both edits restructure or clarify class precedence/membership by general answer-type cues, name no specific row, and keep Expression tight.
