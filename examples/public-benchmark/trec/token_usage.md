# Token usage — spp arm, trec (gpt-5-nano)

Cumulative gpt-5-nano task-model tokens consumed by the spp loop, in the same
shape as `../../scripts/cost_report.py` so it is directly comparable to the
EvoPrompt arm. spp's "optimizer cost" (Claude subagent tokens + human time)
lives elsewhere and is not billed here — only gpt-5-nano task-model tokens.

**Comparison target — EvoPrompt arm (same model, gpt-5-nano):**

| arm | calls | input_tokens | output_tokens | total_tokens | test_acc |
|---|---:|---:|---:|---:|---:|
| evoprompt_gpt5nano | 4,688 | 246,696 | 575,620 | 822,316 | 0.804 |

Shared seed (manual-init) test accuracy: **0.828** — EvoPrompt's GA did not beat
it (best_test 0.804 < seed 0.828). The real bar for spp is to beat **0.828** cleanly.

## spp per-run ledger

All gpt-5-nano tokens spp actually spent are counted (honest accounting). The
first three calls (G4 dry-run) plus an initial 300-call pass on prompt_v01 were
run through the plugin's chat harness (system+user messages) before the run was
recalibrated to EvoPrompt's EXACT harness (`{instruction}\n\nSentence: …\nLabel:`,
single user message) so that dev/train scoring is identical to how the bar (0.828)
and the final test are measured. Those 303 calls are folded into the `calibration`
row below; every loop iteration from run_01 onward uses the EvoPrompt harness via
`score_split.py`.

| run | stage | calls | input_tokens | output_tokens | total_tokens | cumulative_total |
|---|---|---:|---:|---:|---:|---:|
| calibration (dryrun + harness recal) | infer | 303 | 25,080 | 25,437 | 50,517 | 50,517 |
| run_01 | infer | 300 | 13,125 | 35,909 | 49,034 | 99,551 |
| run_02 | infer | 300 | 151,125 | 22,017 | 173,142 | 272,693 |
| run_03 | infer | 300 | 221,925 | 20,413 | 242,338 | 515,031 |
| run_04 | infer | 300 | 339,525 | 23,678 | 363,203 | 878,234 |
| run_05 | infer | 300 | 387,825 | 22,081 | 409,906 | 1,288,140 |
| finalize_test | infer | 500 | 644,572 | 30,285 | 674,857 | 1,962,997 |

## spp cumulative total

Final, at /spp-finalize (search loop + sacred-test scoring), gpt-5-nano
task-model tokens only. **Verified against the OpenAI dashboard (Jun 12):**
total requests **2,303 ✓** and total (input) tokens **1,783,177 ✓** both match the
ledger exactly; actual **total spend $0.11**. (The dashboard's "Total tokens"
headline counts *input/prompt* tokens; completion/reasoning output tokens are
billed separately and included in the $ spend.)

| arm | calls | input_tokens | output_tokens | total_tokens | **cost (USD)** | test_acc |
|---|---:|---:|---:|---:|---:|---:|
| **spp_gpt5nano** | **2,303** | **1,783,177** | **179,820** | **1,962,997** | **$0.11** | **0.924** |
| evoprompt_gpt5nano | 4,688 | 246,696 | 575,620 | 822,316 | $0.24 | 0.804 |
| shared seed (manual-init) | — | — | — | — | — | 0.828 |

The dashboard's **$0.11** is *below* the naive list-price estimate ($0.16 at
$0.05/1M input + $0.40/1M output) because of **prompt caching**: spp's six-section
prompt grew to ~1.3k tokens — above gpt-5-nano's 1024-token cache threshold — and
is replayed per row, so a large share of input tokens were billed at the
cached-input rate (~10× cheaper). (This differs from the sst5 arm, whose ~430-token
prompt stayed below the threshold and saw no caching.) EvoPrompt's short prompts
(~50–100 tokens) cache nothing and its cost is output-dominated, so its ~$0.24 is
unaffected.

**Read (the efficiency axis):** spp wins on every axis that matters —
**+12.0 accuracy points over EvoPrompt (0.924 vs 0.804), +9.6 over the shared seed
(0.828), 2.0× fewer task-model calls (2,303 vs 4,688), and ~2.2× cheaper
($0.11 vs $0.24).** Raw *token count* is the one misleading metric: spp's total
(1.96M) is 2.4× EvoPrompt's (822k), but output tokens cost 8× input (and cached
input is cheaper still), and the two arms have opposite profiles — spp is
**input-heavy / output-light** (one rich, static, *cacheable* six-section prompt
replayed per row; 180k output) while EvoPrompt is **output-heavy** (GA population ×
generations of prompt text + per-call reasoning; 576k output). On the axis that
bills — dollars — spp is less than half the cost. ~50,517 of spp's tokens (the
`calibration` row) were spent before the harness was aligned and are counted
honestly here (~2.6% of total). Per cost_report.py's framing, spp additionally
offloads the optimization *reasoning* to Claude subagents + the human, which this
gpt-5-nano ledger does not bill at all.
