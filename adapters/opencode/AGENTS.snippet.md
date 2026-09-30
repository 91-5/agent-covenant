# Snippet: opencode `AGENTS.md` / `.opencode/rules/`

> Drop-in rules for opencode projects. opencode reads `AGENTS.md` from the
> project root; `.opencode/rules/*.md` is also picked up as scoped rules in
> current versions — **verify which paths your version honours** before relying
> on the subdirectory form.
>
> The canonical text lives in `adapters/codex/AGENTS.md` (harness-neutral). This
> file shows the same content with opencode-specific wiring: the global rules
> file, the per-project file, and the plugin/MCP surface opencode exposes that a
> harness-independent protocol can bind to.

## Where to put it

| Purpose | File | Scope |
|---|---|---|
| Project-wide covenant | `<project>/AGENTS.md` | that repo |
| Your defaults across projects | `~/.config/opencode/AGENTS.md` | every session |
| Scoped, opt-in variant | `<project>/.opencode/rules/covenant.md` | rules-enabled setups |

## Snippet (paste into any of the above)

```markdown
## Agent Covenant

- Work cards: `<NS>-YYYYMMDD-NNN.md` in `.tasks/`. Bare `TASK-N` is invalid
  (collision → silent wrong review; see postmortems §PM-1).
- Done means: `verdicts/<id>.verdict.json` exists AND
  `python tools/gate.py --verdict-dir verdicts --require <id>` exits 0.
- Never review your own change; if you must, mark `independent: false` and say why.
- Acceptance criteria are commands and exit codes, not adjectives.
- Handing work over? Absolute path + "read this first". Never a bare id.
- Unreadable input is a finding. Missing verdict is not an approval.
- Close the loop: cards are archived or deleted within a working day.
```

## Binding the gate into opencode's tool surface

opencode is MCP- and plugin-capable, so two integrations are natural. Both are
**optional** and neither is required by the protocol:

1. **Expose the gate as an MCP tool** so the model can run it without shell
   gymnastics: wrap `python tools/gate.py …` behind a `gate_check` tool taking
   `(verdict_dir, require[])`. A shell MCP already available in many setups can
   do this with no code. *(We do not ship a server here — the protocol must not
   depend on a vendor's plugin API; §10.4.)*
2. **A hook on session end** that refuses to end while a card is `IN_REVIEW` with
   no verdict file. Useful, but note the failure mode from `postmortems.md` §PM-2:
   a hook that only *warns* is decoration. If you wire it, make it a real error.

## Subagents as reviewers

opencode's subagent-style specialists (a reviewer/architect role) fit the
reviewer half of the protocol. Two rules keep this honest:

- The reviewer must be a **different agent** than the author, and the verdict
  records which. If the only available reviewer is yourself, the honest verdict
  is `independent: false`, which the gate blocks by default.
- Reviewers in a shared session inherit the author's framing. Fresh context
  beats a fancier prompt.

## Verification

```bash
python -m unittest discover -s tests -v     # the tools' own gate
python tools/lint_cards.py --dir .tasks      # card schema + naming
python tools/gate.py --verdict-dir verdicts  # the gate itself
```

If the first two pass, your setup is at least **L1**; you are at **L2** only when
the last command runs in CI unattended.
