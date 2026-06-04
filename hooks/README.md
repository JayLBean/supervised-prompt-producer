# spp hooks

This directory holds spp's Claude Code plugin hooks. **spp ships exactly
one hook**, added in v0.8; it shipped zero through v0.7 by deliberate
design (`DESIGN.md` §7.1.9). A hook is a heavy instrument — it intercepts
tool calls for everyone who installs the plugin — so spp adds one only when
a guarantee genuinely warrants mechanical enforcement.

## `sacred_test_guard.py` — the sacred-test-set guard

A `PreToolUse` hook (registered in [`hooks.json`](hooks.json), matcher
`Read|Bash`) that makes the methodology's **read-once** protection of the
sacred test set mechanical instead of disciplinary.

**What it does.** It denies any read of a task's `data/test.csv` unless the
co-located access ledger (`data/.test_access.json`) has
`status: "authorized"`. The optimization loop (`/spp-loop`) reads
`data/train_dev.csv`, which contains no test rows, and never authorizes — so
a test-set read during optimization is always a mistake, and now a blocked
one. The one legitimate reader, `/spp-finalize`, opens the ledger for its
single held-out evaluation and seals it (`consumed`) afterward, so a second
finalize cannot re-read the test set.

**Fail-closed.** A missing, unreadable, or non-`authorized` ledger results
in a deny. The sacred test set is the one place spp errs toward refusing.

**What it guards (and what it does not).** It matches a `Read` whose
`file_path` is a `test.csv` directly inside a `data/` directory, and a
`Bash` command that names a `.../data/test.csv` path. Everything else passes
untouched.

> **Honest boundary.** This is a guardrail, not a sandbox. It blocks the
> realistic leak paths — the `Read` tool and shell reads that name the path
> — but a determined *indirect* read (a script that computes the path at
> runtime so the string never appears in the command) can evade string
> matching. It raises test-set protection from a matter of discipline to a
> harness that refuses the common paths; it does not claim more.

## The ledger contract

`data/.test_access.json` is the handshake between `/spp-finalize` (the
writer, via [`scripts/_ledger.py`](../skills/run/scripts/_ledger.py)) and
this hook (an independent reader). They agree on the file name and the
`status` field:

| status | meaning | hook behavior |
|---|---|---|
| `sealed` (also absent / malformed) | test set closed | deny |
| `authorized` | finalize's single read window is open | allow |
| `consumed` | evaluation done; permanently sealed | deny |

The hook is kept standalone (no import of the `spp` scripts package) because
it runs as a plugin hook in the end user's environment; the writer and the
reader therefore duplicate only the trivial file-name + status contract,
which is covered by an end-to-end test
([`test_ledger.py`](../skills/run/scripts/tests/test_ledger.py)).

## Mechanism notes

- Plugin hooks live in `hooks/hooks.json` at the plugin root (not in
  `.claude-plugin/`). The harness discovers it on plugin load.
- The hook is invoked as `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/sacred_test_guard.py`;
  it reads the PreToolUse event JSON on stdin and, to deny, prints a
  `hookSpecificOutput` with `permissionDecision: "deny"` and exits 0. Allow
  and pass-through are silent (exit 0, no output).
- Tests live with the rest of the suite
  ([`test_sacred_test_guard.py`](../skills/run/scripts/tests/test_sacred_test_guard.py));
  the guard module is loaded by path, so its `test_csv_target` helper is not
  collected as a test.
