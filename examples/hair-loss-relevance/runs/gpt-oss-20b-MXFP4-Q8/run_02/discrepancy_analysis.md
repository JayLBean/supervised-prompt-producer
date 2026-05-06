# Discrepancy analysis — iteration 2

**Iteration:** 2
**Model:** gpt-oss-20b-MXFP4-Q8
**Prompt:** [`prompt_v02.md`](prompt_v02.md)
**Disagreed dev rows:** 2 of 20 (1 false positive, 1 unparsed)

This artifact references rows by ID only; row content is **not** persisted here.

---

## Failure clusters

### Cluster E — One-line exclamations / non-substantive comments mistaken for identity-acceptance content

**Member rows:** `row_id=50`
**Direction:** false positive (predicted `true`, ground truth `false`)
**Shared property:** A short, single-sentence comment that name-drops baldness or hair loss in an exclamatory or joking register without delivering substantive lived experience, peer advice, or sustained identity/acceptance argument. Rule 3 (identity/acceptance) is firing because the post superficially mentions bald-life favorably, but the comment is a one-liner reaction that does not engage with the topic. The category boundary needs a substantiveness floor for rules 1, 2, 3 to apply.
**Cluster proposes:** rule clarification — rules 1, 2, and 3 require the post to deliver substantive content (more than a single exclamatory or quip-shaped sentence). One-liner reactions, jokes, or name-drop comments without elaboration default to rule 5 (off-topic / joke / non-substantive).

### Cluster F — Unparsed completion (operational, not a rule failure)

**Member rows:** `row_id=68`
**Direction:** prediction = none (treated as wrong label by the runner; ground truth `true`)
**Shared property:** The model's response was empty — all completion tokens were consumed by `reasoning_content` (gpt-oss family reasoning trace) before any visible JSON could be emitted. This is a **runtime operational failure**, not a rule failure. The same row was correctly handled by the iteration-1 prompt (when it was a false-negative under the iteration-1 ruleset); the iteration-2 ruleset is broader and the model explored more reasoning paths, exhausting the 1500-token budget.
**Cluster proposes:** **No rule edit.** The fix is operational — bump `MAX_TOKENS` from 1500 to 3000 in `loop_spec.md` §5. Recorded as plan.md §11 v5 entry; not an `<rules>` change.

---

## Proposed rule edits

Only one categorical rule edit (cluster E). Cluster F has no rule edit.

1. **Add a substantiveness floor across rules 1, 2, 3:** "Rules 1, 2, and 3 apply only when the post delivers substantive content on hair loss — at minimum a few sentences of lived experience, peer advice, or identity/acceptance reasoning. One-line exclamations, single-sentence quips, or name-drop comments that mention baldness without elaboration are NOT substantive and default to NOT RELEVANT under rule 5."

---

## Motivating-row references (IDs only)

| Cluster | Member row IDs | Direction |
|---|---|---|
| E — one-line exclamations / non-substantive comments | row_id=50 | FP |
| F — unparsed completion (operational, not rule) | row_id=68 | unparsed |
