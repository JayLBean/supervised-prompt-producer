# Discrepancy analysis — iteration 1

**Iteration:** 1
**Model:** gpt-oss-20b-MXFP4-Q8
**Prompt:** [`prompt_v01.md`](prompt_v01.md)
**Disagreed dev rows:** 5 of 20 (3 false negatives, 2 false positives)

This artifact references rows by ID only; row content is **not** persisted here. The rule-edit subagent reads cluster names and proposed edits, not row bodies.

---

## Failure clusters

### Cluster A — Thin earnest first-person product/treatment reviews mistaken for promotion

**Member rows:** `row_id=4`
**Direction:** false negative (predicted `false`, ground truth `true`)
**Shared property:** A short, first-person sentence or two reporting personal use of a hair / scalp product or treatment with a positive-results claim. No hashtags, no brand SKU, no clinic name, no "DM to order", no listicle structure, no evangelical-tone signals. The post is plausibly lived experience, just briefly stated. The current `<rules>` section has rule 4 (Spam/promotion) firing on the surface shape ("I used X and got Y") without distinguishing earnest brevity from promotional voice.
**Cluster proposes:** rule clarification — thin earnest first-person treatment/product reports are RELEVANT (rule 1 wins) unless they carry promotional markers.

### Cluster B — Substantive peer/community engagement on hair-loss topics without the author's own loss being the subject

**Member rows:** `row_id=36`, `row_id=68`
**Direction:** false negatives (predicted `false`, ground truth `true`)
**Shared property:** The author engages substantively with hair-loss content — directing treatment advice to another user, arguing about acceptance/identity for the bald community, contextualizing the broader hair-loss discourse — without describing their own hair-loss experience. Rule 2 (peer engagement) and rule 3 (identity/acceptance framing) already cover this in principle, but the model is reading "no first-person hair-loss claim" as decisive and overriding the peer/community engagement signal.
**Cluster proposes:** rule strengthening — peer/community engagement and identity/acceptance arguments on hair-loss topics are RELEVANT even when the author does not state their own hair loss; the engagement, not the autobiographical framing, is what the rule turns on.

### Cluster C — Body-hair / hair-removal / depilatory content (non-scalp hair management)

**Member rows:** `row_id=48`
**Direction:** false positive (predicted `true`, ground truth `false`)
**Shared property:** The post is about HAIR but not about HAIR LOSS — depilatory creams, shaving slowdown, body-hair regrowth management, beard care without baldness context. The current `<rules>` lists "Off-topic" generically; the model is anchoring on the word "hair" without checking whether the topic is hair *loss* (scalp / cohort-relevant) versus hair *removal* / body-hair management.
**Cluster proposes:** rule sharpening — explicitly call out hair-removal / depilatory / shaving / body-hair regrowth content as out of scope; the cohort is hair *loss*, not hair management generally.

### Cluster D — Third-person clinician/professional case write-ups about patients

**Member rows:** `row_id=72`
**Direction:** false positive (predicted `true`, ground truth `false`)
**Shared property:** A clinician, surgeon, or hair-restoration professional describes a patient's case in the third person, with rich substantive content about hair loss biology, transplant outcomes, treatment protocols, etc. The voice is professional/educational/marketing rather than lived. Often ends with a hashtag block or implicit-CTA pattern characteristic of practice-marketing content. The current rule 5 names "third-person clinical-study summaries" and "clinical/third-person" but the model under-applies it when the post is long, substantive, and discusses real-sounding patient details.
**Cluster proposes:** rule sharpening — clinician / professional first-person voice describing PATIENT cases (third-person on the patient) is NOT RELEVANT regardless of substantive medical detail; the cohort is patient-side lived experience, not professional case write-ups or practice-marketing content.

---

## Proposed rule edits

Each edit is a **categorical** rewording of an existing rule or an addition of a categorical clarifier. None refer to specific row IDs; none describe a single-row pattern.

1. **Refine rule 4 (Spam/promotion):** add a not-promotional carve-out. "Thin or short first-person product/treatment use reports are not promotion in themselves; classify them as RELEVANT under rule 1 unless they carry explicit promotional markers (hashtags, brand SKUs, listicle structure, copy-paste evangelism, clinic CTAs, 'DM to order'-style commerce framing, sponsored-content disclosures)."

2. **Strengthen rules 2 and 3 (peer engagement and identity/acceptance):** clarify that the criterion is engagement-with-the-topic, not autobiographical framing. "These rules apply when the author engages substantively with hair-loss topics (advising another user, articulating acceptance/identity arguments about bald life, contextualizing community discourse), regardless of whether the author describes their own hair-loss experience."

3. **Sharpen rule 5 (Off-topic) — body-hair clarifier:** add a categorical exclusion. "Posts about hair *removal* or non-scalp hair management — depilatory creams, shaving / shaving slowdown, body-hair regrowth, beard styling without baldness context — are NOT RELEVANT, even when the post mentions hair extensively. The cohort is hair LOSS, not hair management broadly."

4. **Sharpen rule 5 (Off-topic) — clinician/professional voice clarifier:** add a categorical exclusion. "Posts written by a clinician, surgeon, or hair-restoration professional describing a PATIENT'S case in the third person — even with rich substantive detail about hair loss biology, transplant outcomes, or treatment protocols — are NOT RELEVANT. The cohort is patient-side lived experience, not professional case write-ups, educational content, or practice-marketing posts."

---

## Motivating-row references (IDs only)

| Cluster | Member row IDs | Direction |
|---|---|---|
| A — thin earnest first-person product/treatment reports | row_id=4 | FN |
| B — peer/community engagement without first-person loss | row_id=36, row_id=68 | FN |
| C — body-hair / depilatory / non-scalp hair management | row_id=48 | FP |
| D — third-person clinician case write-ups | row_id=72 | FP |
