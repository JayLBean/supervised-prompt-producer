# Auditor review — run_03 (edits proposed in run_02 → prompt_v03)

Score-blind auditor. Verdicts judge only categorical (generalizing answer-type
rule) vs. row-specific (patches particular rows / memorizes specific answers).

## Verdicts

### Edit 1 — Strengthen Location
Verdict: **categorical** — advance. Keys on interrogative cues ("Where…", "what city/country/nationality…") and place/place-derived answer-types, naming no specific country/city/landmark. The "named object is the place, not the answer" disambiguation is a general answer-type principle.

### Edit 2 — Broaden Human (name-parts, professions, named collectives)
Verdict: **categorical** — advance. "Profession/title → Human" and "named collective of people → Human" classify by the kind of entity the answer denotes (a person or group of persons), not by any specific company/band/person. The category list describes a class, not instances.

### Edit 3 — Sharper Entity vs Description by answer shape
Verdict: **categorical** — advance. The split is drawn by answer SHAPE (concrete nameable item vs explanation/definition), an abstract structural cue, explicitly ignoring the surface "what is/was/were" verb. The example types are generic answer-shape categories, not memorized rows.

### Edit 4 — Tie-breaker ordering
Verdict: **categorical** — advance. A pure precedence ordering over answer-type cues plus the generalizing guard "topic words never override the answer-type cue," which actively suppresses row-specific topic memorization. No dataset-specific content.

On the flagged concerns: "nationality/origin → Location" is defensible (a nationality answer is place-derived; TREC conventionally files it under Location; no specific nationality named). "Profession → Human" is a legitimate answer-type rule (the answer denotes a kind of person), not an arbitrary patch.

## Summary
Categorical: 4 / Row-specific: 0 / Unclear: 0. All advance. **No override needed** — every edit generalizes by interrogative/answer-type cue; none smuggles in a specific acronym, place, person, company, or gold answer.
