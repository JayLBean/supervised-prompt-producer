# Discrepancy analysis — run_04 (prompt_v04, dev 0.875)

Isolated discrepancy subagent; rows by ID only. Final-iteration scope: the one
remaining systematic weakness is Entity recall (0.73) — the step-5 fallback
over-routes concrete-thing answers to Description.

## Failure clusters

**Entity mislabeled as Description (target, x10):** 0314, 0514, 0334, 0916, 0654, 0663, 0670, 0989, 0585, 0679. Primary field `label`. Shared property: the answer is a concrete nameable thing (a color, a food, a substance/material, a named object/event/referent, or a composition) but the "What is/was X" phrasing reads as definitional.

**Guard — Description correctly stays Description (do NOT over-correct, x2):** 0790, 0453.

**Out of scope (idiosyncratic singletons, not chased):** 0609, 0855, 0889, 0840, 0685, 0196, 0136, 0787.

## Proposed rule edits

**Edit 1 — reframe the step-5 Entity-vs-Description fallback as a noun-first positive default** (`target_fields: [label]`)
Replace step 5 with: "Step 5 (Entity vs Description): Ask 'can this be answered with a noun, name, or concrete thing?' If YES — a color, a food, a substance/material, a named object/event/referent, or 'what is X made of / consist of / composed of', 'what does X eat' — label **Entity**. Choose **Description** ONLY when the answer is necessarily a sentence: an explanation (why), a manner/method (how), the meaning of an ordinary word, or the definition of an explicitly named subject (band/language/product). Default to Entity when in doubt."
Rationale: the current fallback over-routes concrete-thing answers to Description (Entity recall 0.73). Flipping to a noun-first default recovers the x10 cluster, while the "definition of a named subject" and "manner/how" carve-outs preserve 0790 and 0453, guarding against over-correction.

**Edit 2 — "made of / consist of / eat" composition cue** (`target_fields: [label]`)
Add one Entity bullet: "Composition and consumption questions — 'what is X made of', 'what does X consist of / contain', 'what do X eat' — name a substance, material, or food and are **Entity**, not Description." Distinct from definitional "what is <named subject>" which remains Description.
Rationale: these phrasings (0334, 0514, 0916) are the most reliably mislabeled sub-pattern; a categorical answer-shape cue (substance/material/food = noun = Entity) lifts them without naming any row.

## Technique recommendations
None. Single fallback-ordering defect addressable by the categorical step-5 reframe; few-shot exemplars / decomposition not warranted and would risk over-fitting the singletons.
