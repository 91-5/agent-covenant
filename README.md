# Agent Covenant

**A collaboration verification protocol: no deliverable is "done" until an independent reviewer has produced a machine-checkable verdict that passes a gate.**

Two files, zero dependencies:

```bash
python tools/gate.py --verdict-dir verdicts     # the gate
python tools/lint_cards.py --dir .tasks         # card schema + naming
```

---

## Why

An agent's own report of success is not evidence. The evidence for that claim is
a transcript, and transcripts are not checkable.

That is not a hunch. In the **MAST** taxonomy of multi-agent failure
([arXiv 2503.13657](https://arxiv.org/abs/2503.13657), NeurIPS 2025), failure
class **FC3 is task verification failure** — specifically *FM-3.2: no review, or
incomplete review*. An **ICML 2026 position paper** on multi-agent systems
reports **41–87% failure rates** on mainstream benchmarks, with **37.2%** of
failures caused by committing before the coordination barrier is satisfied.

The failures that get written up are the loud ones. The expensive ones are quiet:

- A coding agent created an isolated worktree, failed to migrate the changes,
  logged `Failed to migrate some changes... Continuing with worktree creation`,
  and destroyed several days of uncommitted work
  ([vscode #289973](https://github.com/microsoft/vscode/issues/289973), data loss).
- **Lost update is invisible to tests and to `git diff`.** The file looks fine.
  The only symptom is that something an agent *claimed* to do is no longer there.

This project takes the boring part seriously: make the judgement a file, make the
file checkable, and make "no verdict" mean "not done".

## What this is — and is not

| This is | This is **not** |
|---|---|
| A **file-schema spec** for task / review / handoff / decision artifacts | An orchestrator. We don't schedule agents. |
| A **CI-runnable gate** over reviewer verdicts | A swarm library. (`ruflo` 73k★, `oh-my-opencode` 70k★, `crewAI` 59k★, `langraph` 41k★ — the orchestration layer is a red ocean.) |
| A **failure-mode catalogue** that justifies each rule | A model router, memory store, or vector DB |
| **Harness-agnostic** — adapters are docs, not plugins | Bound to one vendor's plugin API |

**Why the empty space matters:** the quality-control layer is not crowded. Every
prior project we could find in this niche — `AAHP`, `agent-handoff-protocol`,
`agent-acceptance-gate` — sits at **0★**; `agents-template` at 5★. The demand is
stated out loud in community write-ups ("context loss is the #1 cause of
multi-agent failure") and nobody has shipped a reputation. The orchestration
layer, by contrast, is where the stars are. We build here on purpose.

**Adjacent standards.** MCP is agent↔*tool* (vertical). A2A is agent↔*agent*
transport and discovery (horizontal). Agent Covenant is agent↔*agent*
**accountability**: how a deliverable is *judged*, not how it is transmitted or
discovered.

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

1. **Author** copies `templates/TASK.md` → renames it to `AC-20260929-001.md`,
   writes acceptance criteria as commands with exit codes.
2. **Reviewer** is a *different* agent, given the **absolute path**, and told to
   read it first. It writes the review card **and** the verdict JSON. It does
   not touch the author's files.
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

## What the gate actually enforces

- A verdict file exists and parses; verdict ∈ {PASS, CONDITIONAL, FAIL}
- `blockers == 0` for PASS; CONDITIONAL needs `--allow-conditional` **and** a
  named `acknowledged_by`
- **`independent: true`** — the author may not approve itself
- `evidence` is a non-empty list — a verdict must show its work
- **Freshness:** the verdict's `ts` must not be older than the artifact it
  judges. A verdict that predates the code is stale, and stale blocks.
  *(This is the check teams skip first and it is the one that matters.)*

## Conformance levels — claim honestly

| Level | Requirement |
|---|---|
| **L0** Unstructured | Agents talk freely, no artifacts. The default today. |
| **L1** Carded | Namespaced cards, schemas, independence rule. Human relay allowed. |
| **L2** Gated | Machine verdicts, `gate.py` in CI, no human in the gate loop. |

If a person clicks "approve" in the loop, you are at **L1**. Say L1. Overstating
the level is precisely the failure this project exists to prevent.

## Adapters

Documentation, not code — deliberately, so the protocol cannot rot with a
vendor's API surface:

- `adapters/claude-code/SKILL.md` — reviewer as a skill; author rules via `AGENTS.md`
- `adapters/codex/AGENTS.md` — harness-neutral rules block for `AGENTS.md` readers
- `adapters/opencode/AGENTS.snippet.md` — rules placement + binding the gate as an MCP tool

Each marks version-dependent details as **verify** rather than inventing them.

## Status — v0.1, honest

Spec + two tested tools (45 unit tests) + one real pilot run
(`examples/deepfreeze-pilot/`). **Not** validated at scale. Known limitations are
listed in `PROTOCOL.md` §10 and include two we refuse to paper over: a file-based
protocol needs a human (or a poller) to wake the second agent, and a gate proves
a check *ran* — it cannot prove the reviewer was thorough.

## Roadmap

- [x] v0.1 — spec, gate, linter, templates, adapters, one worked example
- [ ] A second real pilot with a different harness (portability evidence)
- [ ] Verifier registry — shareable acceptance checkers, the most requested lever
- [ ] Postmortem corpus growth; a rule per named failure mode
- [ ] Optional `--junit` output for CI dashboards (only if asked for)

## Contributing

Read `PROTOCOL.md`, then `postmortems.md` — the second is why this project
exists. Adapters and verifiers are the two most welcome contributions. Your PR
runs the same gate as the project does; see `CONTRIBUTING.md`.

MIT © 15812
