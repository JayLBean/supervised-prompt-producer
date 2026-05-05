# Discrepancy analysis — iteration 3

**Iteration:** 3
**Model:** gpt-oss-20b-MXFP4-Q8
**Prompt:** [`prompt_v03.md`](prompt_v03.md)
**Disagreed dev rows:** 2 of 20 (1 false negative, 1 false positive)

This artifact references rows by ID only; row content is **not** persisted here.

---

## Failure clusters

### Cluster G — Short-but-substantive personal/experience posts misclassified by an overly broad substantiveness floor

**Member rows:** `row_id=45`
**Direction:** false negative (predicted `false`, ground truth `true`)
**Shared property:** A first-person hair-loss / experience post whose body is concise (a short paragraph) but contains substantive personal content — onset, treatment use, or sustained experience claim. The substantiveness floor introduced in iteration 3 was intended to keep one-line jokes and name-drop comments out (cluster E from iter 2); its current wording in `prompt_v03.md` is misfiring on short but genuine first-person content because the model is reading "few sentences" as "non-substantive." Train-side movement supports this reading: 13 of 14 train false-negatives in iteration 3 are positive-coded posts with C1 / C2 / C3 / C5 criteria, the same shape as cluster G. The dev-disagreement count (1 row) understates the breadth of the over-correction; the train signal is the supporting evidence.
**Cluster proposes:** rule narrowing — the substantiveness floor should only exclude posts that are *both* very short (≤1 sentence) *and* lack first-person experiential / peer-advice / acceptance content. A short post with first-person onset, treatment use, or experience framing satisfies rules 1–3 even if it's brief.

### Cluster H — Body-hair / depilatory rule getting de-prioritized

**Member rows:** `row_id=48`
**Direction:** false positive (predicted `true`, ground truth `false`)
**Shared property:** The body-hair / depilatory exclusion in rule 5 (introduced in iter 1 cluster C, verdict: categorical) is being over-ruled by other parts of the prompt. Specifically, this row is a question about a depilatory cream — the type the rule-5 clarifier was written to exclude. Iteration 2's prompt got this row right; iteration 3's prompt does not. The likely cause is that the substantiveness floor's expansion of rule 1–3 scope is shadowing rule 5's body-hair exclusion — the model reads "discusses a hair-management question" → "personal experience" → relevant.
**Cluster proposes:** rule clarification — the rule-5 body-hair / hair-management clarifier should appear as a **threshold check** that runs *before* rules 1–3 evaluate, so that the topic boundary (hair LOSS vs hair-management generally) is settled first. This is structural rather than a content edit.

---

## Proposed rule edits

Two edits, both categorical.

1. **Narrow the substantiveness floor.** Replace the iteration-3 substantiveness clause with: "The substantiveness floor applies only to posts that are both (a) ≤1 sentence in length AND (b) carry no first-person experience, peer advice, or identity/acceptance framing. Short posts that contain a first-person hair-loss claim, a peer treatment recommendation, or an acceptance/identity argument satisfy rules 1–3 regardless of length."

2. **Topic-scope-first ordering for rule 5.** Add a leading clause to rule 5: "**This topic-scope check runs before rules 1–3 evaluate.** If the post is about hair removal, depilatory creams, shaving / shaving slowdown, body-hair regrowth management, or beard styling without a baldness context, classify NOT RELEVANT regardless of how substantive the discussion is. The cohort is hair LOSS (scalp, baldness, alopecia, hair thinning), not hair management broadly."

---

## Motivating-row references (IDs only)

| Cluster | Member row IDs | Direction |
|---|---|---|
| G — overly broad substantiveness floor | row_id=45 (dev), with train-side support across positive-coded short posts | FN |
| H — body-hair rule de-prioritized | row_id=48 | FP |
