# spp plan — trec

**Created:** 2026-06-12

**Designer session:** spp-init-trec-20260612

**Plan version:** v3

---

## 1. Task overview

**Task mode:** classification

**One-sentence description:** Classify a question by the *type of answer it expects* (not its topic) into exactly one of six classes — Description, Entity, Expression, Human, Location, Number — emitting one label per row.

**Audience for the prompt's output:** A benchmark accuracy scorer (spp-vs-EvoPrompt arm comparison on a shared sacred test set). The "downstream consumer" is the accuracy metric itself.

**Problem statement** (2–3 sentences):
TREC question classification is answer-type, not topic: "What is the capital of France?" → Location (the answer is a place), even though the topic is France. The hard boundaries are Entity vs Description (a "what is X" question can want a thing or a definition) and the syntactically-marked-but-rare Expression class (abbreviation/expansion questions). The shared bare seed already scores **0.828** on gpt-5-nano and EvoPrompt's GA *failed to beat it* (0.804); spp's job is to refine the seed — without seeing the sacred test — by adding categorical answer-type rules and disambiguation that lift cleanly above 0.828.

---

## 2. Output schema and per-field definitions

**Output schema** (JSON Schema draft 2020-12; mirrors `schema.json`):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "trec output schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["label"],
  "properties": {
    "label": {
      "type": "string",
      "enum": ["Description", "Entity", "Expression", "Human", "Location", "Number"],
      "description": "The type of answer the question expects (not the question's topic)."
    }
  }
}
```

**Per-field definitions:**

- **`label`:** the single answer-type class for the question. Per-class meanings (from `schema.json` labelDefinitions / SEED.md):
  - `Description` — answer is a definition, description, manner, or reason (what/why/how). e.g. "What is autism?", "Why does the moon turn orange?"
  - `Entity` — answer is a thing: animal, color, product, substance, work, etc. e.g. "What is the best-selling cookie?"
  - `Expression` — answer is an abbreviation or its expansion (what does X stand for / abbreviation of X). e.g. "What does IOC stand for?"
  - `Human` — answer is a person, group, or organization (who). e.g. "Who discovered radium?"
  - `Location` — answer is a place: city, country, geographic feature (where). e.g. "What is the capital of France?"
  - `Number` — answer is a count, date, distance, money, or other numeric value (how many/when/how far). e.g. "When did WWII end?"

**Known borderline cases:**
- **Entity vs Description.** "What is X?" can want a *thing* (Entity) or a *definition/explanation* (Description). This is the dominant confusion pair and where prompt wording earns the most accuracy.
- **Expression is rare and syntactically marked.** Only ~15 of 1000 baseline rows (1.5%); cued by "stand for", "abbreviation (of/for)", "what does <acronym> mean". A clean categorical rule on those cues should capture it without needing many dev examples. One baseline row is a borderline gold call ("What is Mikhail Gorbachev's middle initial?" → Expression); kept as-is per the no-relabel contract (see §6).
- **Human vs Entity** for organizations, and **Location vs Entity** for "what country/place" phrasings, are secondary confusions.

---

## 3. Success criteria

**Production decision rule:**
The emitted `label` is compared for exact equality against the gold label; the row scores 1 if equal, 0 otherwise. Accuracy = mean over rows.

**Headline success criterion:**
Accuracy on the sacred test set (500 rows, `test_holdout.csv`) **> 0.828** — the shared seed's manual-init test accuracy, which EvoPrompt's GA could not beat. Secondary bar: beat the same-model EvoPrompt arm's best test accuracy of **0.804**. Beating 0.828 *cleanly* is the real target. The optimization target during the loop is dev accuracy; the test number is read only once at finalization.

**Acceptable trade-offs:**
Token efficiency is a reported axis but not a gate: spp may spend more input tokens per call (richer prompt) so long as it makes far fewer total task-model calls than EvoPrompt's population search (4,688 calls). A clean accuracy gain over 0.828 at a fraction of EvoPrompt's calls is the win. No precision/recall asymmetry — accuracy weights all six classes by prevalence; the rare Expression class contributes little to the headline number but is watched as a correctness check.

---

## 4. Per-field metrics, aggregate strategy, and floors

**Aggregate strategy:**

- **`AGGREGATE_STRATEGY`:** macro
- **`AGGREGATE_WEIGHTS`:** n/a (single field)
- **`AGGREGATE_RATIONALE`:** Single-output classification (K=1); the aggregate is the identity on the lone field's metric. "macro" is the trivial choice over one field.

**Per-field metrics:**

- **Field `label`:**
  - `METRIC_NAME`: accuracy
  - `METRIC_RATIONALE`: The benchmark fixes the metric as accuracy (SEED.md, schema.json). It is the mechanically correct comparator against the EvoPrompt arm, which also reports accuracy. Plain accuracy (not macro-F1) is deliberate: the test set is prevalence-distributed and accuracy is the headline number both arms are scored on.
  - `METRIC_INDEPENDENCE_NOTE`: Accuracy is computed by exact string match of the predicted label against the frozen gold label — fully deterministic, no LLM in the scoring path (DESIGN.md §5). Gold labels are the bring-your-own baseline + sacred holdout; no judge metric.

**Per-field floors:**
None gating. (Single metric, single field; the headline accuracy criterion in §3 governs.) Expression per-class recall is *watched* and reported at finalization, but is not a gate — at ~1.8% test prevalence it cannot move the headline accuracy meaningfully, and re-labeling is forbidden.

---

## 5. Model and lock-in posture

**Production model identifier:** `gpt-5-nano`

**Production model family:** openai

**Lock-in posture:** locked

**Cross-model fragility plan:**
The prompt is optimized for `gpt-5-nano` only; this is a single-model benchmark arm. We will not swap models. If a different model were ever targeted, the correct response is to re-run `/spp-loop` against it from the same seed. Any gpt-5-specific handling (reasoning_effort "low", max_completion_tokens, omitted temperature) is an API-call concern in the runner, not prompt content, so the frozen prompt itself stays model-portable text.

---

## 6. Baseline

**Data source:** `baseline.csv` (1000 labeled rows, columns `row_id,text,label`), already prepared by the benchmark harness. Bring-your-own-labels path — labels are treated as GOLD; no re-labeling. The sacred test is the separate `test_holdout.csv` (500 rows), the identical rows the EvoPrompt arm scored on.

**Preprocess mapping:** `row_id → id`, `text → input`, `label → label`; rename-only, no content change (data already canonical in substance). Written to `spp/trec/data/baseline.csv` during `/spp-baseline`.

**Target baseline size:** 1000 rows available. **dev = the EvoPrompt arm's exact 200 dev rows** (`fixtures/trec/dev.jsonl`, registered by `row_id`); these are a stratified subset OF this baseline pool (verified: all 200 ids present in `baseline.csv`, 0 label disagreements). train = 100 stratified-proportional from the remaining 800 baseline rows (pool minus dev), disjoint from dev by construction. The other ~700 baseline rows are an unused labeled reserve. (See §7.)

**Class balance target:** preserve baseline prevalence (cannot see the sacred test to stratify toward it). Baseline is moderately imbalanced (Entity 230, Human 225, Description 213, Number 164, Location 153, **Expression 15**) and notably **Expression is rare (1.5%)**. The dev split is EvoPrompt's exact 200-row stratified sample (Description 43, Entity 45, Human 45, Number 33, Location 31, Expression 3); train is stratified *proportional to the remaining 800-row pool* so the overfit-guard reference is class-representative. **Known characteristic:** the sacred test has a different prevalence (Description 27.6%, Human 13.0%, Number 22.6% vs baseline 21.3 / 22.5 / 16.4) — a real distribution shift we cannot design around without peeking at the test; this means dev-accuracy may diverge from test-accuracy in a predictable direction (test over-weights the Description class). Documented as a §10 known unknown, not corrected.

**Language coverage:** monolingual (English).

**Label provenance:** Upstream TREC-QC (Li & Roth 2002, SetFit/TREC-QC) gold, label names following EvoPrompt verbalizers; identical provenance and label names as the rows the EvoPrompt arm used. `baseline-quality` audits these labels (G2) but does not re-label.

**Label synthesis:** none (labels human-provided / already present).

**Status:** complete
<!-- Existing-baseline (bring-your-own gold) path: labels imported, audited not
     relabeled. Canonical baseline written to spp/trec/data/baseline.csv
     (rename-only id/input/label). -->

**Baseline-quality review** (audit-of-existing-labels mode, K=1 field `label`):
Reviewed the 1000-row imported gold baseline. Checks run:
- **Integrity:** 1000/1000 valid enum labels; 0 empty inputs; 0 duplicate ids; **0 exact-text overlap with the sacred test set** (no leakage). 2 duplicate input texts found, both **label-consistent** ("what fraction of a beaver's life is spent swimming?" ×2 → both Number; "what is a virtual ip address?" ×2 → both Description) — harmless redundancy, not a labeling conflict; left as-is (re-dedup would change the shared pool both arms draw from).
- **Class balance vs sacred test (aggregate):** notable distribution shift — test over-weights Description (27.6% vs 21.3%, +6.3pp) and Number (22.6 vs 16.4, +6.2) and under-weights Human (13.0 vs 22.5, −9.5) and Entity (18.8 vs 23.0, −4.2); Expression (+0.3) and Location (+0.9) track. Recorded as a §10 known unknown — dev (EvoPrompt's rows, baseline-distributed) cannot be stratified toward a test we may not peek at, so dev→test may diverge predictably. Not a labeling defect.
- **Spot-check (4/class, seed 20260612) against §2 definitions:** all sampled labels plausible. Confirmed two real boundaries the loop must encode: (1) "what does X mean/stand for" → Expression only when X is an abbreviation/acronym (LASER, SIDS, S.O.S.), else Description (the word "opera"); (2) "What is X?" → Description for a definition (aortic abdominal aneurysm), Entity for a named thing (the part on a matchbook).
- **Expression (rarity flag — all 15 eyeballed):** 14/15 are unambiguous abbreviation/expansion questions ("What does IOC stand for?", "abbreviation of the International Olympic Committee", "What is DEET?"). One borderline gold call — "What is Mikhail Gorbachev's middle initial?" → Expression (an initial abbreviates a name; arguable but defensible under the ABBR family). **Kept as-is** per the bring-your-own-gold no-relabel contract: it is the shared gold both arms are scored against (the sacred test has 9 Expression rows on the same provenance); relabeling would break apples-to-apples and is unnecessary — the loop's job is to fit this gold, not change it.
- **Provenance:** upstream TREC-QC (Li & Roth 2002; SetFit/TREC-QC train split), label names per EvoPrompt verbalizers; identical provenance to the rows the EvoPrompt arm scored.

**Verdict: ready.**

---

## 7. Splits

**Split ratios:** train 12.5% / dev 25% / test 62.5%
<!-- Proportions of spp's labeled working corpus (train 100 + dev 200 + test 500
     external holdout = 800 rows): 100/800=12.5, 200/800=25, 500/800=62.5; sums
     to 100. dev IS the EvoPrompt arm's exact 200 dev rows (fixtures/trec/
     dev.jsonl) — not just the same size but the SAME ROWS, so both arms optimize
     and dev-score against an identical set (maximal apples-to-apples; the only
     difference is the prompt). At 200 rows the rare Expression class is present
     with 3 dev rows. train=100 is stratified-proportional from the remaining 800
     baseline rows (pool minus dev), disjoint from dev; it is the overfit-guard
     reference + few-shot source, kept smaller to limit task-model cost (the
     guard needs a rate estimate, not parity with dev). The TEST partition is the
     external sacred holdout (test_holdout.csv), NOT carved from baseline. The
     other ~700 baseline rows are an unused reserve. -->

**Random seed:** 20260612
<!-- dev uses no seed (it is EvoPrompt's fixed row set, built upstream with
     seed 6); the 20260612 seed governs only the train draw from the remaining
     800-row pool. -->

**Stratification key:** `label`. dev inherits EvoPrompt's stratified-to-baseline composition (Expression 3); train is stratified proportional to the remaining 800-row pool (Expression ~1–2). The loop handles Expression primarily by a categorical "abbreviation/expansion" rule (definitional, not example-driven) rather than relying on dev coverage.

**Sacred test set acknowledgment:** acknowledged

---

## 8. Loop scope and stop criteria

**spp scope:** full
<!-- Full Phase 1 + 1.5 + 2 + 3. Phase 1 labeling is skipped (bring-your-own gold
     labels, audited not relabeled), but Phase 3's sacred-test discipline is fully
     in force — the external 500-row holdout is the whole point of the
     apples-to-apples comparison. -->

**MAX_ITERATIONS:** 10

**Dev plateau threshold:** < 0.01 dev-accuracy improvement for 3 consecutive iterations.

**Overfitting early-stop guard:** train accuracy − dev accuracy > 0.15 for 2 consecutive iterations triggers EARLY_STOP.

**Auditor configuration:** per-iteration, no-score-access

**Adversary:** off
<!-- Single-model accuracy benchmark with abundant real labeled data; synthetic
     adversarial rows add cost without a clear win, and the comparison is about
     refining the seed on real dev. Expression is rare but syntactically marked
     and rule-coverable, so it does not need synthetic augmentation. Can flip on
     via a §11 revision if the loop stalls on a specific answer-type boundary. -->

---

## 9. Decision rules at HITL gates

| Gate | Approval phrase | Notes |
|---|---|---|
| G1 — plan approval | `approved, proceed to baseline` | |
| G2 — baseline review | `approved, proceed to splits` | |
| G3 — split confirmation | `approved, start the loop` | |
| G4 — dry-run gate | `approved, run iteration 1` | |
| G5 — finalization | `approved, score the test set` | |
| G6 — production decision | `approved, freeze the prompt` | |

---

## 10. Open questions / known unknowns

- **Dev composition.** Resolved at G1 (v2): dev = EvoPrompt's *exact* 200 dev rows (not just same size) so the dev-scoring set is identical across arms — the strongest apples-to-apples control. train=100 from the disjoint 800-row remainder. 300 task-model calls/iteration.
- **Baseline↔test prevalence shift.** The sacred test over-weights Description (27.6% vs baseline 21.3%) and under-weights Human (13.0% vs 22.5%). Dev is stratified to baseline (cannot peek at test), so dev-accuracy is a biased-low estimate of test-accuracy if the prompt is stronger on Description than Human, or vice-versa. Watched, not corrected.
- **Expression measurability.** With ~3 Expression rows in dev, Expression accuracy is measured weakly on dev; the test set has 9 Expression rows for a finalization read. The loop covers Expression by rule, not by dev fitting.
- **Few-shot examples.** Whether the loop adds worked examples (and from which partition — only train, never dev/test) is left to the discrepancy/rule-edit stages. If added they come from the train split exclusively.
- **max_completion_tokens ceiling.** Must be generous enough that low-effort reasoning does not exhaust the budget and return empty content; the dry-run validates the chosen ceiling (loop_spec sets 2000).

---

## 11. Plan revision log

| Date | Plan version | Reason | By |
|---|---|---|---|
| 2026-06-12 | v1 | Initial plan via /spp-init (bring-your-own-labels path; gpt-5-nano arm; train 100 / dev 200 stratified-proportional; Expression rarity flagged) | spp-init-trec-20260612 |
| 2026-06-12 | v2 | G1 pre-approval revision (user: "Make sure the dev train set is the same with evoprompt"): dev is now the EvoPrompt arm's EXACT 200 dev rows (fixtures/trec/dev.jsonl, registered by row_id — verified all 200 present in baseline.csv, 0 label disagreements), not just a same-size resample; train=100 stratified-proportional from the disjoint remaining 800-row pool. §6/§7/§10 updated. | spp-init-trec-20260612 |
| 2026-06-12 | v2 | **G1 approved** by user (phrase: "approved, proceed to baseline") — gate event, no contract change | user |
| 2026-06-12 | v3 | /spp-baseline: canonicalized baseline (rename-only id/input/label) → spp/trec/data/baseline.csv; baseline-quality AUDIT of imported gold (integrity clean, 0 leakage, 2 label-consistent dup texts, all 15 Expression rows eyeballed — 1 borderline kept per no-relabel contract) → verdict **ready**; §6 BASELINE_QUALITY_NOTE added; BASELINE_STATUS → complete | spp-baseline-trec-20260612 |
| 2026-06-12 | v3 | **G2 approved** by user (phrase: "approved, proceed to splits") — gate event | user |
| 2026-06-12 | v3 | /spp-baseline: generated splits.json — dev = EvoPrompt's exact 200 rows (registered by row_id), train = 100 largest-remainder stratified-proportional (seed 20260612) from the disjoint 800-row remainder, test = external sacred holdout (500 rows, test_holdout.csv); verified train/dev/test pairwise-disjoint, 0 test leakage. train Expression 2 / dev Expression 3 / 10 reserve | spp-baseline-trec-20260612 |
| 2026-06-12 | v3 | **G3 approved** by user (phrase: "approved, start the loop") — gate event | user |
| 2026-06-12 | v3 | /spp-loop: built run_infer.py (gpt-5-nano reasoning path already merged in scripts/inference.py — no patch needed); built run_01/prompt_v01.md (bare seed + output-format directive only, no enrichment); G4 dry-run on first 3 sorted train rows passed (3/3 parse, 3/3 schema-valid, 3/3 correct; 540 tokens) | spp-loop-trec-20260612 |
| 2026-06-12 | v3 | **G4 approved** by user (phrase: "approved, run iteration 1") — gate event | user |
| 2026-06-12 | v3 | /spp-loop HARNESS RECAL: first v01 pass via the plugin chat harness (system+user) scored dev 0.72 — a harness mismatch vs the bar (0.828 was produced by run_evoprompt's `{instruction}\\n\\nSentence:…\\nLabel:` single-message wrapper + match_label, which scripts/score_prompt.py reuses to score the spp arm). Switched the loop scorer to that EXACT wrapper (new spp/trec/score_split.py) so dev/train scoring is identical to the bar and to finalization; reset v01 to the EXACT bare seed (no added directive — wrapper handles parsing). The 303 plugin-harness calls are folded into a transparent `calibration` row in token_usage.md (all spent tokens counted). | spp-loop-trec-20260612 |
| 2026-06-12 | v3 | /spp-loop ran 4 iterations (14 edits, ALL auditor-categorical via isolated discrepancy/rule-edit/auditor subagents, 0 overrides, overfit guard never tripped). dev climbed monotonically 0.765(v01)→0.820→0.850→0.875→**0.895(v05)**; train 0.93, train−dev 0.035. Edits: 6-class categorical answer-type rules → Location/Human strengthening → ordered decision-procedure (Expression→Location→Human→Number→Entity/Description) → noun-first Entity/Description fallback. Terminated at convergence (remaining dev errors idiosyncratic/balanced seesaw); EARLY_STOP, **selected prompt_v05** (dev-argmax). | spp-loop-trec-20260612 |
| 2026-06-12 | v3 | **G5 approved** by user (phrase: "approved, score the test set") — gate event | user |
| 2026-06-12 | v3 | /spp-finalize: scored prompt_v05 on the sacred test (500 rows, EvoPrompt-identical harness, single read) → **test accuracy 0.924** (vs EvoPrompt 0.804, shared seed 0.828 — beats the bar cleanly by +9.6/+12.0); 0 parse failures; Expression 9/9. dev 0.895 → test 0.924 (generalized). Final: 2,303 calls / 1,962,997 gpt-5-nano tokens / $0.16. Wrote REPORT.md, finalize/test_eval.json + test_results.json, results/spp/trec/result.json. | spp-finalize-trec-20260612 |
| 2026-06-12 | v3 | **G6 approved** by user (phrase: "approved, freeze the prompt") — froze prompt_v05 → PROMPT_FROZEN_v01.md (SHA-256 2f7b4854…638c, verified identical). Run complete. | user |
