# Discrepancy analysis — run_01 (prompt_v01, dev 0.765)

Isolated discrepancy subagent. Reasoned over disagreed dev row content + dev
confusion; the persistent artifact references rows by ID only. Scored on
EvoPrompt's harness (`{instruction}\n\nSentence: …\nLabel:`, match_label).

## Failure clusters

### Entity-as-thing read as Description
Primary field: `label`
Members: 0670, 0809, 0334, 0971, 0663, 0058, 0916, 0314, 0514, 0561, 0790, 0196
Shared property: Questions that look definitional ("what is / what's the term for / what color / what does X consist of / eat / made of") but whose answer is a concrete *thing* — a named term/word, a color, a substance/material, a food/vegetable, a phobia-name, or the name people give to something. The interrogative wraps a request for a noun-label, not an explanation. The model over-applies Description to anything starting "what is/what does."

### Location cues misread as Entity
Primary field: `label`
Members: 0664, 0490, 0386, 0540, 0103, 0434, 0468, 0879, 0883
Shared property: Questions whose answer is a place — country, river, man-made waterway, library/landmark, mountain, or city — phrased around an attribute ("longest river," "highest mountain," "what country has," "what man-made waterway," "what library," "largest city to..."). The place noun is embedded, so the model picks Entity.

### Human cues (groups/orgs/companies/bands) misread as Entity
Primary field: `label`
Members: 0262, 0678, 0728, 0746, 0270, 0037, 0185, 0633
Shared property: Questions whose answer is a person, king/character, or a collective of people — a company, band/group, police/military force, team, or organization — phrased with "what group/company/force/police" so the model treats the answer as a generic thing rather than a human entity.

### Expression class never fires; bleeds both directions
Primary field: `label`
Members: 0609, 0858, 0220 (gold Expression, missed) ; 0705, 0032, 0585, 0732 (Entity over-tagged Expression) ; 0806, 0091, 0564 (Description over-tagged Expression) ; 0402 (Number over-tagged Expression)
Shared property: Two confusions collapsed. (a) True Expression rows — an all-caps acronym/initialism as subject, or "stand for"/"what does <acronym> mean" — read as Description. (b) Non-acronym questions about a *term/word/fear-of X*, the *meaning of a foreign word*, *opening words*, *best way*, or *when to plant* get spuriously routed to Expression. The boundary is undefined, so it both under- and over-fires.

### Numeric-answer cues misread
Primary field: `label`
Members: 0365, 0787, 0685, 0402, 0840
Shared property: Questions whose answer is a numeric value — date of birth, oven temperature, unit of weight/measure, planting time, or a quantitative property — phrased without an explicit "how many," so the model misroutes to Human/Entity/Expression/Description.

## Proposed rule edits

**Edit 1 — Entity vs Description boundary**
Rule: "If the expected answer is a concrete *thing* — a named term, word, or name for something; a color; a substance, material, or chemical; a food, plant, or animal; or what something is made of, contains, or eats — classify as Entity, NOT Description. Reserve Description for answers that are a definition, explanation, manner, or reason (genuine what-is-X / why / how)."
`target_fields: [label]`
Rationale: Fixes the largest cluster (Entity->Description x10) by separating noun-label answers from explanatory ones.

**Edit 2 — Location cue rule**
Rule: "If the expected answer names a place — country, city, state, river, sea, lake, ocean, mountain, waterway/canal, island, region, building, library, landmark, or other geographic feature — classify as Location, even when the question is phrased as 'what river/mountain/country/city/waterway/library ...' or asks for the largest/longest/highest/closest such place."
`target_fields: [label]`
Rationale: Recovers Location->Entity x9 by making any place-naming answer Location regardless of attribute phrasing.

**Edit 3 — Human cue rule (collectives included)**
Rule: "Classify as Human when the answer is a person, king, fictional character, or any group of people acting as a unit — a company, corporation, band, musical or named group, sports team, police or military force, or organization — including when introduced by 'what group/company/force/team/band.'"
`target_fields: [label]`
Rationale: Recovers Human->Entity x7 by ruling that collectives of people are Human, not generic things.

**Edit 4 — Tight Expression rule**
Rule: "Classify as Expression ONLY when the answer is an abbreviation or its expansion: the question asks what an acronym/initialism stands for or means (e.g. subject is an all-caps initialism, or contains 'stand for', 'abbreviation of', 'short for', or 'what does <ACRONYM> mean'). Do NOT use Expression for 'what is the term/word/name/fear of X' (that is Entity) or for 'what is the meaning of <ordinary word>', 'why', 'how', or 'best way' questions (that is Description)."
`target_fields: [label]`
Rationale: Makes Expression fire on the 3 missed acronym rows while blocking the 4 Entity and 3 Description over-tags; encodes the exact acronym/abbreviation cue.

**Edit 5 — Numeric-answer rule**
Rule: "Classify as Number when the expected answer is a quantitative value — a count, date or date-of-birth, year, distance, dimension, money, temperature/oven setting, unit of weight or measure, or a time/season for doing something — even when the question is not phrased as 'how many' or 'how much.'"
`target_fields: [label]`
Rationale: Recovers the scattered numeric singletons that lack an explicit quantity interrogative.

**Edit 6 — Answer-type-over-topic tiebreaker**
Rule: "Always classify by the TYPE OF ANSWER expected, not the topic of the question. When a question mentions a place, person, or thing as part of its setup, label by what the answer itself will be, not by the nouns in the question."
`target_fields: [label]`
Rationale: General guard against topic-driven misroutes, reinforcing the answer-type contract underlying every cluster.

## Technique recommendations
None (no catalogued symptom matched; the failures are class-boundary definition gaps, addressed by categorical `<rules>` edits).
