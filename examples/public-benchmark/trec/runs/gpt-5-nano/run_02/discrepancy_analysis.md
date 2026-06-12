# Discrepancy analysis — run_02 (prompt_v02, dev 0.82)

Isolated discrepancy subagent; reasoned over disagreed dev row content + dev
confusion; artifact references rows by ID only.

## Failure clusters

**Cluster A — Location read as Entity (0664, 0490, 0504, 0205, 0103, 0222, 0594, 0879, 0883):** all want a PLACE or place-derived answer (city/country/landmark/man-made geographic feature/nationality), but contain a salient concrete noun (library, waterway, mountain, city, pope) that pulls the model to Entity. Most carry a "Where …" or "What city/country/nationality …" cue. Primary field `label`.

**Cluster B — Human read as Entity (0262, 0740, 0678, 0952, 0746, 0855, 0270, 0185, 0037):** all want a PERSON, NAMED GROUP/ORG/COMPANY/BAND, a person's name component (middle name), or a PROFESSION. The model treats the named org/company/group as a generic "thing." Primary field `label`.

**Cluster C — Entity over-corrected to Description (0670, 0705, 0916, 0585, 0514, 0732, 0679):** want a concrete thing (a phrase/words, a material/substance, a food, a phobia term-name, a named referent) but phrased with "What was/were …" so they read as wanting an explanation. Primary field `label`.

**Cluster D — Description over-corrected to Entity (0134, 0693, 0790, 0889, 0453):** want a definition/classification of a named or specific subject. The model now grabs Entity because a concrete noun is present. Primary field `label`.

**Singletons (do not chase):** 0787, 0685 (units → Number), 0609 (DEET expansion → Expression), 0136 (origin of a name → Location), 0840 (chemical reactivity → Description). TREC-idiosyncratic; left to general rules.

## Proposed rule edits

**Edit 1 — Strengthen Location routing on interrogative + place-noun cues.**
"If the answer would be a PLACE or place-derived value — a country, city, river, mountain, landmark, man-made geographic feature (canal/waterway/road), the location where an event occurred, or a NATIONALITY / origin — label Location. The interrogatives 'Where …' and 'What city/country/nationality …' default to Location even when the sentence names a concrete object (library, monument, building); the named object is the place, not the answer."
`target_fields: [label]`
Rationale: lifts the weakest class (0.65) by binding the "Where/what city/country/nationality" cue and place-features to Location over the distracting concrete noun (Cluster A).

**Edit 2 — Broaden Human to named orgs/groups, name-parts, and professions.**
"Label Human when the answer is a person, a person's name or name-part (first/middle/last name, nickname), a profession or title, OR a NAMED collective of people: company, band, police force, military/guerrilla unit, organization, club, or newsgroup/community. A named company or group is Human, not Entity, even when it acts like a 'thing.'"
`target_fields: [label]`
Rationale: recovers Cluster B by routing named companies/groups and name-parts/professions to Human.

**Edit 3 — Sharper Entity-vs-Description discriminator (answer shape, not surface verb).**
"Decide Entity vs Description by the SHAPE of the answer, ignoring 'What is/was/were': (a) Entity if the answer is a concrete item that can be named in a few words — a color, term/name, food, animal, material/substance, phrase or set of words, or a phobia/term-name. (b) Description if the answer is an explanation, method, reason, function, or a definition/classification of a specific named or singular subject (a language, band, product, or 'what is X?' asking what X is)."
`target_fields: [label]`
Rationale: fixes BOTH over-corrections — phrase/material/food/term-name → Entity (Cluster C); "define this named subject / how did / what is X" → Description (Cluster D) — using answer shape rather than the misleading "What was…" verb.

**Edit 4 — Tie-breaker ordering note.**
"When two classes seem plausible, apply this priority by cue strength: an explicit place cue (Where / what city / country / nationality) → Location; an explicit person/group/profession/name-part cue → Human; otherwise judge Entity vs Description by answer shape. Topic words (a person, place, or product merely mentioned in the question) never override the answer-type cue."
`target_fields: [label]`
Rationale: prevents Location/Human questions that mention a concrete object from collapsing into Entity (root cause shared by Clusters A and B).

## Technique recommendations
None.
