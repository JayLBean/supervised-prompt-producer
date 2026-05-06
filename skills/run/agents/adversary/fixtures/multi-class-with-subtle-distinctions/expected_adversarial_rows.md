Adversarial rows — generated for iteration 6. Not persisted, not added to baseline, not promoted to splits.

---

## Row 1

> "Is it intentional that `parse()` returns `None` on empty
> input? I expected an empty list. Repro: `parse('')` →
> `None`. Docs don't mention this case."

**Probes:** rule 4's tie-breaker (Bug when a reproduction is
present, even if phrased as a question).

**Intuitive label:** `Bug` per §2's known borderline — the
ticket has a reproduction and the docs do not cover the case,
which suggests undocumented behavior worth fixing or
documenting.

**Why the prompt would likely mislabel:** rule 4 says "if a
reproduction is included." A maintainer might reasonably read
"`parse('')` → `None`" as a reproduction; a strict literal-
parser reading rule 4 might require an explicit "Steps to
reproduce" section. The blind spot is the gap between
informal in-line repros and the formal repro shape rule 4
implicitly assumes.

---

## Row 2

> "How do I export the report as XLSX? CSV works fine but I
> need formatted columns for the finance team."

**Probes:** rule 5's tie-breaker (FeatureRequest when
answering requires new functionality), in tension with rule 2
(Question if asking about existing functionality).

**Intuitive label:** depends on a fact the prompt cannot
know — *does XLSX export exist today?* If yes, `Question`. If
no, `FeatureRequest`. §2 is silent on how to handle the
ambiguity when the prompt cannot verify the system's actual
capabilities.

**Why the prompt would likely mislabel:** the prompt has no
oracle for what exists today. Rule 5 routes to FeatureRequest
when the answer requires new code; rule 2 routes to Question
when existing functionality is in play. The prompt picks
based on surface phrasing ("how do I"), but the correct
classification depends on system state the prompt cannot
inspect. The blind spot is the implicit assumption in rules
2 and 5 that the classifier knows the system's feature set.

---

## Row 3

> "When I delete a workspace, the audit log is also deleted.
> This is concerning for compliance — could the audit log be
> retained even after workspace deletion?"

**Probes:** the three-way tension between Bug (deletion is
unexpected behavior), FeatureRequest (retention is new
functionality), and Question (clarifying intent).

**Intuitive label:** `FeatureRequest` — the user describes
existing behavior accurately and proposes a change. The
"concerning" framing is editorial, not a defect claim.

**Why the prompt would likely mislabel:** the issue mentions
unexpected/concerning behavior, which surface-matches rule 1
(Bug). It includes a reproducible scenario (delete workspace
→ audit log gone), which surface-matches rule 4. But the
*intent* is feature-request — the user is not claiming the
deletion is broken, only proposing a different policy. The
blind spot is that rules 1 and 4 trigger on surface signals
("unexpected", "repro") that align poorly with the
distinction between defect-reporting and policy-change-
requesting.
