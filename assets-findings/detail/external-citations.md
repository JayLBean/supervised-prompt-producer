# External citation pack — prompting / classification techniques

Citation support for the "more prompting techniques" development direction. Assembled so the
planner can attach a real primary source to each candidate technique instead of asserting
folklore. One entry per technique: canonical name, short description, primary citation, an
spp-loop interaction note, and a **structured-output flag** (does the technique touch
`<output_format>`?).

## Why the structured-output flag matters for spp

spp's prompt has a **locked six-section structure** (`<persona> <task> <rules> <output_format>
<example_input> <example_output>`), fixed order, preserved verbatim (DESIGN §5; prompt-architect
SKILL; §7.1.1 locked-invariant "Six-section prompt structure"). Per the inventory
(`assets-findings/spp-repo.md` item 1), the prompt-architect sub-skill treats `<output_format>`
as **"Avoid"** on the edit-frequency scale, and explicitly lists chain-of-thought-as-a-section,
multiple example pairs (few-shot), and tool-use prompts as **out of scope / BREAKING** if added
as structural changes. CoT is permitted *only* as an inline request inside `<task>` ("explain
your reasoning briefly before the label"), never as a separate section.

The load-bearing flag below is therefore: **does the technique require a reasoning/intermediate
field in the model's output before the answer?** If yes, it changes `<output_format>` (and the
single `<example_output>` shape), which collides with the "Avoid" discipline, the template
validation rules (six tags in exact order), and REPORT §5 aggregation. Such a technique is not
"just a prompt tweak" in spp — it is a methodology-touching change.

---

## 1. Chain-of-Thought (CoT) prompting

**What it is.** Prompt the model to produce a series of intermediate natural-language reasoning
steps before its final answer; few-shot CoT supplies exemplars that themselves show the reasoning
trace. Improves performance on multi-step arithmetic, commonsense, and symbolic reasoning.

**Primary citation.** Wei, Wang, Schuurmans, Bosma, Ichter, Xia, Chi, Le, Zhou. *Chain-of-Thought
Prompting Elicits Reasoning in Large Language Models.* NeurIPS 2022. arXiv:2201.11903.

**spp-loop interaction.** Maps onto spp's permitted inline form (a `<task>` instruction to reason
briefly before the label). The breaking variant is a dedicated reasoning *section* or a required
reasoning *field*. Note the paper's own caveat: CoT gains appear mainly at large model scale and
can hurt models below ~10B parameters.

**Touches structured output?** **YES if implemented as a reasoning field** — a CoT trace emitted
before the label changes `<output_format>` and the `<example_output>` shape. **NO if kept as the
permitted inline `<task>` request** that asks for brief reasoning but the format still emits only
the label. This is the central methodology fork for the planner.

---

## 2. Self-consistency (majority vote over sampled reasoning chains)

**What it is.** A decoding strategy on top of CoT: sample multiple diverse reasoning paths at
nonzero temperature, then marginalize over the reasoning and take the **majority-vote answer**
rather than the single greedy decode. Substantial gains on reasoning benchmarks (e.g. GSM8K
+17.9%).

**Primary citation.** Wang, Wei, Schuurmans, Le, Chi, Narang, Chowdhery, Zhou. *Self-Consistency
Improves Chain of Thought Reasoning in Language Models.* ICLR 2023. arXiv:2203.11171.

**spp-loop interaction.** This is an **inference-time / decoding** mechanism, not a prompt-text
change — it would live in the runner (`inference.py` / `eval.py`), sampling K completions per row
and aggregating. It interacts with spp's statistics direction (run-to-run variance, point
estimates) more than with the prompt structure. Caution: it presumes a discrete, votable answer,
which classification has, but it multiplies inference cost K-fold and needs a deterministic
tie-break rule.

**Touches structured output?** Indirectly — it depends on a parseable final answer to vote over.
If paired with CoT-as-field it inherits #1's `<output_format>` change; on its own (vote over the
bare label) it does not change the prompt's sections, only the runner.

---

## 3. Binary relevance / one-vs-rest for multi-label classification

**What it is.** The foundational problem-transformation method for multi-label classification:
decompose a K-label problem into K independent binary classifiers (one "is-label-present" decision
per label), then union the positive predictions. The standard ML baseline against which multi-label
methods are compared.

**Primary citations (ML-foundational, not a prompt blog).**
- Tsoumakas, Katakis. *Multi-Label Classification: An Overview.* International Journal of Data
  Warehousing and Mining (IJDWM) 3(3):1–13, 2007. — introduces and structures the multi-label task
  and the problem-transformation taxonomy (binary relevance, label powerset, etc.).
- Zhang, Li, Liu, Geng. *Binary relevance for multi-label learning: an overview.* Frontiers of
  Computer Science 12(2):191–202, 2018. doi:10.1007/s11704-017-7031-7. — dedicated modern overview
  of binary relevance, its assumptions (label independence) and limitations.

**spp-loop interaction.** Directly relevant to spp's **feature-group prompt splitting** (item 10
of the inventory) and the K>1 multi-field path: binary-relevance is the conceptual justification
for "one prompt per label/field, scored independently," and its known weakness (ignoring label
correlation) is exactly what spp's "keep unified when fields are densely interdependent" exception
guards against. Cite it to ground the split-vs-unified decision, not as a new prompting trick.

**Touches structured output?** **NO** at the single-prompt level — each binary task keeps the
standard six-section shape with a boolean/enum `<output_format>`. It changes *how many prompts /
task directories* exist (an orchestration decision spp pushes to the user), not any one prompt's
format.

---

## 4. Few-shot / in-context learning

**What it is.** Condition the model on a few input→output demonstrations in the prompt; the model
performs the task with no gradient updates ("in-context learning"). The foundational demonstration
that scale makes models task-general few-shot learners.

**Primary citation.** Brown, Mann, Ryder, Subbiah, Kaplan, Dhariwal, Neelakantan, Shyam, Sastry,
Askell, et al. *Language Models are Few-Shot Learners.* NeurIPS 2020. arXiv:2005.14165. (GPT-3.)

**spp-loop interaction.** spp already ships a **single** `<example_input>`/`<example_output>` pair
(effectively one-shot). The technique here is *multi-shot* — multiple example pairs — which
prompt-architect explicitly lists as **out of scope / BREAKING** because it breaks the
single-example-pair section shape and the template validation. Worth citing precisely so the
planner can state the boundary with a source rather than asserting it.

**Touches structured output?** **YES (structurally).** More than one example pair changes the
`<example_input>`/`<example_output>` section cardinality — a six-section-structure change, not an
`<output_format>` change per se, but it lands on the same locked-invariant.

---

## 5. Decomposition / least-to-most prompting

**What it is.** Decompose a complex problem into an ordered list of simpler sub-problems, then
solve them sequentially, feeding earlier answers into later sub-prompts. Generalizes to harder
problems than the exemplars (e.g. 99%+ on SCAN length-split vs 16% for plain CoT).

**Primary citation.** Zhou, Schärli, Hou, Wei, Scales, Wang, Schuurmans, Cui, Bousquet, Le, Chi.
*Least-to-Most Prompting Enables Complex Reasoning in Large Language Models.* ICLR 2023.
arXiv:2205.10625.

**spp-loop interaction.** Conceptually overlaps spp's **feature-group / sub-task splitting** (item
10): decompose a multi-field task into ordered sub-prompts. But least-to-most's *sequential
dependency* (later sub-prompt consumes earlier output) is precisely the **cross-task composition
that spp declares out of scope** ("one spp/ task = one prompt = one loop"; composition is the
user's production layer). Cite it to frame what a future *compound-system* bookkeeping arc would
formalize — not something a single spp prompt should do internally.

**Touches structured output?** **NO** for a single spp prompt (each sub-prompt keeps the standard
format). The decomposition lives *above* the prompt, in orchestration spp intentionally does not
own.

---

## 6. CoT can hurt / overthinking findings (BREAKING-CHANGE-risk evidence)

**What it is.** Empirical evidence that chain-of-thought / explicit reasoning is **not uniformly
beneficial** and can degrade accuracy on certain task families — the honest counterweight the
planner needs before recommending CoT.

**Primary citations (use the meta-analysis as the headline).**
- **Sprague, Yin, Rodriguez, Jiang, Wadhwa, Singhal, Zhao, Ye, Mahowald, Durrett.** *To CoT or not
  to CoT? Chain-of-thought helps mainly on math and symbolic reasoning.* ICLR 2025.
  arXiv:2409.12183. — meta-analysis over 100+ papers + 20 datasets / 14 models: CoT's gains are
  concentrated on math/symbolic tasks and are **small or negligible on most non-math tasks**
  (which is what most classification is).
- Liu, Liu, Bartolo, et al. *Mind Your Step (by Step): Chain-of-Thought can Reduce Performance on
  Tasks where Thinking Makes Humans Worse.* 2024. arXiv:2410.21333. — constructs task families
  where CoT **lowers** accuracy.
- Wei et al. 2022 (entry #1) also documents CoT hurting sub-10B models.

**spp-loop interaction.** This is the evidence base for treating "add CoT" as a risk, not a free
win: spp targets classification, the exact regime where the meta-analysis finds CoT gains are
weakest, while the cost (an `<output_format>` change, more tokens, more variance) is real and
falls on a locked invariant. The planner should require CoT to *earn* its keep on the dev set,
audited like any other rule edit, never assumed.

**Touches structured output?** **YES (as the warning).** The whole caveat exists because the
tempting implementation — a reasoning field before the label — changes `<output_format>`. The
finding says: that structural cost is often paid for little-to-no classification gain.

---

## 7. Prompt ensembling for classification (optional)

**What it is.** Combine the predictions of multiple prompts (or multiple phrasings of one task)
into a single, more reliable prediction — typically by aggregating noisy per-prompt outputs.

**Primary citations.**
- Arora, Narayan, Chen, Orr, Guha, Bhatia, Chami, Sala, Ré. *Ask Me Anything: A simple strategy for
  prompting language models.* ICLR 2023. arXiv:2210.02441. — reformat a task into multiple QA-style
  prompts and combine via weak supervision; +10.2% avg over few-shot baseline.
- Pitis, Zhang, Wang, Ba. *Boosted Prompt Ensembles for Large Language Models.* 2023.
  arXiv:2304.05970. — boosting-style construction of a prompt ensemble.

**spp-loop interaction.** An ensemble of prompts is, like self-consistency (#2), an
**inference/aggregation** mechanism living in the runner, and it collides head-on with spp's core
contract: spp produces **one** optimized prompt per task and per-stage isolation assumes a single
edit surface (`<rules>`). An ensemble is closer to the explicitly-out-of-scope "automated prompt
search / composition" territory (DESIGN §7.1.3) and should be framed as *downstream composition*
(spp produces members; an ensembler combines them), never fused into the loop.

**Touches structured output?** **NO** per member prompt (each keeps the standard format); the
aggregation sits above the prompt. The methodology tension is with the single-prompt contract and
per-stage isolation, not with `<output_format>`.

---

## Cross-cutting summary for the planner

- **Solid primary sources exist for all seven** candidate techniques (six required + the optional
  ensembling), all primary papers (arXiv / NeurIPS / ICLR) or canonical ML overviews — no folklore
  needed.
- **Structured-output flag is the decisive triage axis.** Only two techniques *necessarily* touch
  the locked six-section structure: CoT-as-a-reasoning-field (#1) changes `<output_format>`, and
  multi-shot few-shot (#4) changes the example-pair cardinality. Both land on a §7.1.1 locked
  invariant and are BREAKING as structural changes. CoT survives only in spp's permitted inline
  `<task>` form.
- **Self-consistency (#2), prompt ensembling (#7) are runner/decoding mechanisms,** not prompt-text
  changes — they belong to the statistics/inference direction and the out-of-scope
  "composition not fusion" boundary, respectively.
- **Binary relevance (#3) and least-to-most (#5) are splitting/decomposition** — they ground spp's
  existing feature-group-split and the future compound-system arc, not new in-prompt tricks.
- **Single most important caveat (cite Sprague et al. 2024, arXiv:2409.12183):** chain-of-thought's
  measured benefit is concentrated on math/symbolic reasoning and is **small-to-negligible on the
  non-math classification tasks spp targets**, while the cost — a reasoning field that changes
  `<output_format>`, more tokens, higher variance — is real and falls on a locked invariant. CoT
  should be treated as a hypothesis the dev set must confirm, not a default improvement.
