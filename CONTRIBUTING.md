# Contributing

Thanks for looking. This project is small on purpose, and the two things it
wants most are **adapters** and **verifiers** — not frameworks.

## Read these two files first

1. `PROTOCOL.md` — the normative spec.
2. `postmortems.md` — why each rule exists. Contribute a postmortem and you have
   contributed more than most PRs.

## The bar we hold ourselves to

This project is a gate. It would be embarrassing — and useless — to merge a
change that skipped its own gate. So, for your PR:

```bash
python -m unittest discover -s tests -v    # the tools' own tests
python tools/lint_cards.py --dir .tasks --strict
python tools/gate.py --verdict-dir verdicts
```

If your change needs a new linter rule, add it to `docs/lint-rules.md` with the
same three questions every existing rule answers: what breaks, why, and who fixes
it.

## What we want

| Contribution | Why it's high value |
|---|---|
| **Adapters** | The protocol is only useful across harnesses. A working `codex/` or `cursor/` adapter beats any amount of prose. |
| **Verifiers** | A new acceptance checker (a real test suite, a security scanner, a perf budget) is immediately usable by every adopter. |
| **Postmortems** | We have 8 named failure modes. The strongest contribution is naming a 9th, with evidence. |
| **Protocol changes** | Welcome, but expect "which failure mode does this prevent?" — if you can't answer, it may be YAGNI. |
| **Tooling polish** | Fine. `STALE_VERDICT` and `gate.py` are the parts people will actually run. |

## What we don't want

- Orchestration, swarm topology, model routers, or memory stores. Those fields
  have 70k★ incumbents; we are deliberately not competing there (PROTOCOL.md §1).
- Vendor-locked plugin architecture. Harness-agnostic or it isn't portable.
- A README that overstates what the tools do. §10 of the protocol lists the
  limitations; keep them accurate as the project grows. **Stating a limitation
  is a contribution, not a weakness.**

## Style

- Stdlib only for `tools/`. If a change needs a dependency, it probably wants to
  be an adapter instead.
- Windows-safe: reconfigure stdout encoding, prefer `pathlib`, no shell-specific
  syntax in committed scripts (postmortems §PM-7).
- Fail closed. A check that crashes on hostile input is a bug, not a pass
  (§PM-6).
- Comment the *why*. The code is small; the reasoning is the value.

## DCO

Not required. We use the MIT license and do not ask for a CLA. If you need one
for your employer, tell us in the PR and we'll work it out.

## Reporting a failure mode

Open an issue with: what happened, why it was **silent**, and where you think it
should have been caught. "Not machine-checkable" is a valid answer and we will
document it in `postmortems.md` if it's real.
