# Agent Covenant — a collaboration verification protocol

**No deliverable is "done" until an independent reviewer has produced a
machine-checkable verdict that passes a gate.**

Zero dependencies, Python 3.9+:

```bash
git clone https://github.com/91-5/agent-covenant.git
cd agent-covenant
python tools/gate.py --verdict-dir verdicts     # the gate
python tools/lint_cards.py --dir .tasks         # card schema + naming
python -m unittest discover -s tests            # 82 tests
```

## Install

There is nothing to install. Both tools are stdlib-only Python scripts and there
are no third-party packages, so a `git clone` and a `python` on `PATH` is the
whole setup — deliberately, so the gate can run in a locked-down CI image with
nothing to allow-list. Python 3.9 or newer.

## Run it in CI

`.github/workflows/gate.yml` runs the same three commands this README does. Copy
it as a starting point:

```yaml
name: covenant
on: [push, pull_request]
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.9' }
      - run: python -m unittest discover -s tests
      - run: python tools/lint_cards.py --dir .tasks --verdict-dir verdicts --artifact-map artifacts.json --strict
      - run: python tools/gate.py --verdict-dir verdicts --artifact-map artifacts.json
```

A non-zero exit is a failure, not a warning. Note what the gate can and cannot
tell you: it proves a check *ran* and that a verdict satisfies the policy. It
cannot tell you the reviewer was thorough, and no exit code here should be cited
as evidence that it was.

## Ask for a review

Give a reviewer the absolute path and nothing else. This is the instruction that
works, copied from a real round:

> Read `D:\path\to\project\.tasks\<NS>-YYYYMMDD-NNN.md` first. It names the
> artifacts you are judging and the acceptance criteria you must check yourself.
> Do not modify any file under review; you own only the review card and the
> verdict. Write the review to `.tasks/REVIEW-<id>.md` and the machine-readable
> twin to `verdicts/<id>.verdict.json`. Your `ts` must satisfy
> **newest reviewed artifact mtime ≤ ts ≤ now** — check the mtimes, then stamp
> between the newest one and the present moment. If you find a blocker, say so
> in `## Blockers` and return `FAIL`; a green verdict you did not earn is worse
> than no verdict.


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

> **Provenance of third-party numbers** — star counts and maintenance status are
> a snapshot, not a claim in perpetuity. All observed **2026-09-29** via the
> GitHub API: [ruflo 73k](https://github.com/ruvnet/ruflo) ·
> [superpowers 293k](https://github.com/obra/superpowers) ·
> [oh-my-opencode 70k](https://github.com/code-yeongyu/oh-my-openagent) ·
> [crewAI 59k](https://github.com/crewAIInc/crewAI) ·
> [langgraph 41k](https://github.com/langchain-ai/langgraph) ·
> [AAHP 0](https://github.com/homeofe/AAHP) ·
> [agent-handoff-protocol 0](https://github.com/amkentech/agent-handoff-protocol) ·
> [agent-acceptance-gate 0](https://github.com/yanqr213/agent-acceptance-gate) ·
> [agents-template 5](https://github.com/pedrofuentes/agents-template).
> Our own first review round flagged the missing provenance here; the fix is in
> `ADR-0001.md`'s sibling commit.

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

## Status — v0.1.4, honest

**This repository is gated, and has been since v0.1.3.** The v0.1.3 round passed
with zero blockers from an independent reviewer
(`verdicts/XJ-20260930-005.verdict.json`, `independent: true`). v0.1.4 is in
review as of this writing; the claim below covers v0.1.3, not v0.1.4.

> Correction, and it is the instructive part: the previous README said
> *"deliberately not gated yet"* while shipping a PASS verdict. It was false in
> the direction that undersells the work, which is the direction most people
> would have caught by eye. The same README claimed 45 tests while the suite held
> 69. Both statements were in prose, and the gate only ever read `.tasks/`. The
> v0.1.4 round adds `STALE_TEST_COUNT` and `UNMAPPED_CLAIM_SURFACE` so that this
> class of defect is caught by a check instead of by a careful reader.

What is not claimed: this is a **spec plus two tested tools, exercised on one real
pilot run** (`examples/deepreeze-pilot/`) and on this repository's own history —
not a fleet, and not validated at scale. Known limitations are in `PROTOCOL.md`
§10, including two we refuse to paper over: a file-based protocol needs a human
(or a poller) to wake the second agent, and a gate proves a check *ran*, not that
the reviewer was thorough.

## Roadmap

- [x] v0.1 — spec, gate, linter, templates, adapters, one unedited worked example
- [x] v0.1.1–v0.1.3 — lint false positive removed, reviewer timestamp guidance
      corrected, the repository gated by an independent reviewer and published
- [ ] A second pilot on a different harness (portability evidence)
- [ ] Verifier registry — shareable acceptance checkers
- [ ] Postmortem corpus growth; a rule per named failure mode

## Contributing

Read `PROTOCOL.md`, then `postmortems.md` — the second is why this project
exists. Adapters and verifiers are the two most welcome contributions. Your PR
runs the same gate the project does; see `CONTRIBUTING.md`.

MIT © 15812
