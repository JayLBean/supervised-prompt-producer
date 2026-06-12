# Discrepancy analysis — run_03 (prompt_v03, dev 0.85)

Isolated discrepancy subagent; rows by ID only. The remaining errors are a
PRECEDENCE / rule-application problem (model over-defaults to Entity/Description
when a stronger answer-type cue is present), not a coverage gap.

## Failure clusters

**Cluster A — Entity over-default suppresses Location** (place/Where/nationality answer mislabeled): 0664, 0490, 0540, 0103, 0879, 0883, 0136. Primary field `label`.

**Cluster B — Entity over-default suppresses Human** (named person/group/company/profession answer mislabeled): 0262, 0952, 0746, 0270, 0037, 0185, 0855. Primary field `label`.

**Cluster C — Description/Entity over-default suppresses other types**: 0670, 0809, 0334, 0663, 0916, 0585, 0514, 0679 (Entity→Description); 0693, 0790 (Description→Entity); 0402, 0840 (Number→Description); 0787 (Entity→Number). Primary field `label`.

**Singletons (do NOT chase — TREC-idiosyncratic)**: 0685, 0609, 0889.

## Proposed rule edits

**Edit 1 — Add an ordered decision procedure that runs BEFORE the Entity/Description fallback** (`target_fields: [label]`)
A numbered, first-match-wins decision order applied before the Entity/Description fallback:
```
DECISION ORDER (apply in sequence; first match wins):
1. EXPRESSION — the question asks what an abbreviation/acronym/initialism stands for or means (tight: abbreviations only, NOT ordinary words).
2. LOCATION — the answer is a place (country, city, region, body of water, mountain, building, landmark), any "Where…" question, or a nationality/origin. Choose Location even when a concrete named object would also satisfy the question.
3. HUMAN — the answer is a person, named group, company, organization, team, band, or profession/occupation. Choose Human even when the named entity "acts like a thing."
4. NUMBER — the answer is a quantity, count, date, year, temperature, distance, measurement, or unit.
5. ENTITY vs DESCRIPTION — ONLY if none of 1–4 fire: Entity if the answer is a concrete thing/substance/object/name; Description if the answer is a reason, manner, definition, or explanatory statement.
```
Rationale: every miss is the model collapsing to Entity/Description when a stronger answer-type cue (place, person/group, quantity) is present. A first-match-wins order forces the stronger type to be committed before the Entity/Description fallback. Targets Clusters A, B, and the Number→Description / Entity→Number misses in C. (Note: Expression kept tight — abbreviations/acronyms only — to avoid re-breaking the ordinary-word-meaning → Description boundary.)

**Edit 2 — Tie-break clarifications for the two dominant precedence traps** (`target_fields: [label]`)
```
- A named company, organization, team, band, or guerrilla/military group is HUMAN, even when phrased as "the X that did Y" or treated as a thing.
- A country, city, or other place answer is LOCATION, even when a specific named place/object is what's being asked for.
```
Rationale: reinforces the two highest-volume confusions at the point of decision, closing the Human (0.84) and Location (0.77) recall gaps without naming any row.

## Technique recommendations
None. The dev errors are a rule-application/precedence problem addressable with the categorical decision-order restructuring; the residual singletons (0685, 0609, 0889) are TREC-idiosyncratic and are not chased.
