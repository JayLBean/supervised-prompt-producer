<task>Classify the given question by the TYPE OF ANSWER it expects (not its topic), choosing exactly one of: Description, Entity, Expression, Human, Location, Number.</task>

<rules>
- Description: the answer is a definition, explanation, manner, or reason — what something means (for an ordinary word), why, how, or the best way to do something.
- Entity: the answer is a concrete thing — a named term/word/name for something, a color, a substance/material/chemical, a food/plant/animal, or what something is made of, contains, or eats. Use Entity (not Description) for such things.
- Expression: the answer is an abbreviation or its expansion ONLY — the subject is an all-caps initialism, or the question contains "stand for", "abbreviation of", "short for", or "what does <ACRONYM> mean". Not for "term/word/name/fear of X" (Entity) or "meaning of <ordinary word>" (Description).
- Human: the answer is a person, king, fictional character, or a group acting as a unit — company, corporation, band/named group, sports team, police/military force, or organization — including when introduced by "what group/company/force/team/band."
- Location: the answer names a place — country, city, state, river, sea, lake, ocean, mountain, waterway/canal, island, region, building, library, landmark, or geographic feature — even when phrased "what river/mountain/country/city/waterway/library …" or asking for the largest/longest/highest/closest such place.
- Number: the answer is a quantitative value — count, date/date-of-birth, year, distance, dimension, money, temperature/oven setting, unit of weight/measure, or the time/season for doing something — even without an explicit "how many/how much."
- Always classify by the type of answer expected, not the question's topic; when a place, person, or thing appears only in the setup, label by what the answer itself will be.
</rules>

<output_format>Respond with exactly one of these words, capitalized as shown, and nothing else: Description, Entity, Expression, Human, Location, Number.</output_format>
