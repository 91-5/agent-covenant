# Agent Covenant — a collaboration verification protocol

**No deliverable is "done" until an independent reviewer has produced a
machine-checkable verdict that passes a gate.**

Zero dependencies, Python 3.9+:

```bash
python tools/gate.py --verdict-dir verdicts     # the gate
python tools/lint_cards.py --dir .tasks         # card schema + naming
python -m unittest discover -s tests            # 45 tests
```

## Why

An agent's own report of success is not evidence — the evidence is a transcript,
and transcripts are not checkable. The **MAST** taxonomy
([arXiv 2503.13657](https://arxiv.org/abs/2503.13657), NeurIPS 2025) names this
failure class: *FM-3.2 — no review, or incomplete review*. An **ICML 2026**
position paper reports **41–87%** multi-agent benchmark failure rates, with
**37.2%** from committing before the coordination barrier is satisfied. The
documented incidents are loud; the expensive ones are quiet — a coding agent
logged `Failed to migrate some changes... Continuing with worktree creation` and
destroyed days of uncommitted work
([vscode #289973](https://github.com/microsoft/vscode/issues/289973)), and lost
updates are invisible to both tests and `git diff`: the file looks fine, the only
symptom is that something an agent *claimed* to do is no longer there.

This project takes the boring part: make the judgement a file, make the file
checkable, and make "no verdict" mean "not done".

## What this is — and is not

| This is | This is **not** |
|---|---|
| A **file-schema spec** for task / review / handoff / decision artifacts | An orchestrator. We don't schedule agents. |
| A **CI-runnable gate** over reviewer verdicts | A swarm library. The orchestration layer is a red ocean: `ruflo` 73k★, `superpowers` 293k★, `oh-my-opencode` 70k★, `crewAI` 59k★, `langgraph` 41k★. |
| A **failure-mode catalogue** justifying each rule | A model router, memory store, or vector DB |
| **Harness-agnostic** — adapters are docs, not plugins | Bound to one vendor's plugin API |

**Why the empty space matters:** every prior project we found in the
quality-control niche — `AAHP`, `agent-handoff-protocol`,
`agent-acceptance-gate` — sits at **0★**; `agents-template` at 5★. The demand is
stated in community write-ups ("context loss is the #1 cause of multi-agent
failure"); nobody has shipped a reputation.

**Adjacent standards.** MCP is agent↔*tool* (vertical). A2A is agent↔*agent*
transport and discovery (horizontal). This project is agent↔*agent*
**accountability**: how a deliverable is *judged*.

## 60 seconds

```
your-project/
├─ .tasks/
│  ├─ AC-20260929-001.md              ← task card (namespaced id!)
│  └─ REVIEW-AC-20260929-001.md       ← review card
├─ verdicts/
│  └─ AC-20260929-001.verdict.json    ← machine-readable verdict
└─ artifacts.json                     ← {"AC-20260929-001": ["src/pipeline.py"]}
```

1. **Author** copies `templates/TASK.md`, renames it to `AC-20260929-001.md`, and
   writes acceptance criteria as commands with exit codes.
2. **Reviewer** is a *different* agent, handed the **absolute path**, told to read
   it first. It writes the review card **and** the verdict JSON, and does not
   touch the author's files.
3. **Gate**:

```bash
python tools/gate.py --verdict-dir verdicts \
  --require AC-20260929-001 --artifact-map artifacts.json
```

| Exit | Meaning |
|---|---|
| `0` | every required id satisfied the policy |
| `1` | **gate violation** — reasons printed, or `--json` for machines |
| `2` | usage/input error (bad dir, unreadable verdict). **Not a pass.** |

## What the gate enforces

- verdict exists, parses, and is `PASS` / `CONDITIONAL` / `FAIL`
- `blockers == 0` for PASS; CONDITIONAL needs `--allow-conditional` **and** a
  named `acknowledged_by`
- **`independent: true`** — the author may not approve itself
- `evidence` is a non-empty list
- **Freshness:** the verdict's `ts` must not be older than the artifact it judges.
  A verdict that predates the code is stale, and stale blocks.

## Conformance — claim honestly

| Level | Requirement |
|---|---|
| **L0** | Agents talk freely, no artifacts. The default today. |
| **L1** | Namespaced cards, schemas, independence rule. Human relay allowed. |
| **L2** | Machine verdicts, `gate.py` in CI, no human in the gate loop. |

If a person clicks "approve" in the loop, you are at **L1**. Say L1.

## Adapters

Documentation, not code, so the protocol cannot rot with a vendor's API:
`adapters/claude-code/SKILL.md`, `adapters/codex/AGENTS.md`,
`adapters/opencode/AGENTS.snippet.md`. Each marks version-dependent details as
**verify** rather than inventing them.

## Status — v0.1, honest

Spec + two tested tools + one real pilot run (`examples/deepfreeze-pilot/`), **not**
validated at scale. This repository is built with its own protocol and is
deliberately **not gated yet**: the author does not sign their own work. Known
limitations are in `PROTOCOL.md` §10, including two we refuse to paper over — a
file-based protocol needs a human (or a poller) to wake the second agent, and a
gate proves a check *ran*, not that the reviewer was thorough.

## Roadmap

- [x] v0.1 — spec, gate, linter, templates, adapters, one unedited worked example
- [ ] A second pilot on a different harness (portability evidence)
- [ ] Verifier registry — shareable acceptance checkers
- [ ] Postmortem corpus growth; a rule per named failure mode

## Contributing

Read `PROTOCOL.md`, then `postmortems.md` — the second is why this project
exists. Adapters and verifiers are the two most welcome contributions. Your PR
runs the same gate the project does; see `CONTRIBUTING.md`.

MIT © 15812
