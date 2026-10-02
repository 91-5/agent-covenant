# Agent Covenant 鈥?a collaboration verification protocol

**No deliverable is "done" until an independent reviewer has produced a
machine-checkable verdict that passes a gate.**

Zero dependencies, Python 3.9+:

```bash
git clone https://github.com/91-5/agent-covenant.git
cd agent-covenant
python tools/gate.py --verdict-dir verdicts     # the gate
python tools/lint_cards.py --dir .tasks         # card schema + naming
python -m unittest discover -s tests            # 109 tests
```

## Install

There is nothing to install. Both tools are stdlib-only Python scripts and there
are no third-party packages, so a `git clone` and a `python` on `PATH` is the
whole setup 鈥?deliberately, so the gate can run in a locked-down CI image with
nothing to allow-list. Python 3.9 or newer.

## Your first round

Six steps, about ten minutes. Nothing below is required to *read* this repo 鈥?skip it
if you are only here for the spec.

**1. Copy the tools.** `tools/gate.py` and `tools/lint_cards.py` are standalone and
stdlib-only. Copy them into your own project as-is; they do not import anything from
this repository.

**2. Pick a namespace.** Two or more uppercase letters, unique per author or team 鈥?
`AC`, `MYTEAM`, `SIR`. This token prefixes every card id. A bare `TASK-001.md` can be
hijacked by another agent, so it is rejected on purpose (`NAMESPACE_MISSING`).

**3. Write the first task card.** Copy `templates/TASK.md` to
`.tasks/<NS>-YYYYMMDD-001.md` and fill in Context, Deliverables, Owned files and
Acceptance. The card is what the reviewer reads 鈥?if it does not say what "done" means,
the reviewer has to guess, and a guess is not a review.

**4. Declare the artifact surface.** Copy `examples/deepfreeze-pilot/artifacts.json` as
a starting point and list every file the reviewer is judging. Anything you later change
that is *not* on this list has no freshness check covering it, and `lint_cards.py` warns
about exactly that (`UNMAPPED_CLAIM_SURFACE`). This file is what makes the gate's
freshness rule bite 鈥?without it the gate cannot tell a verdict that predates your code
from one that covers it.

**5. Ask for a review.** The prompt in the next section is the one that works. Give the
reviewer an absolute path to the card and nothing else. The reviewer writes
`.tasks/REVIEW-<id>.md` and `verdicts/<id>.verdict.json`; it must not touch the files
under review. A worked example of the whole exchange, including a round that came back
FAIL, is in `examples/deepfreeze-pilot/`.

**6. Run the gate.**

```bash
python tools/lint_cards.py --dir .tasks --verdict-dir verdicts --strict
python tools/gate.py --verdict-dir verdicts --artifact-map artifacts.json --require <NS>-YYYYMMDD-001
```

Exit `0` means the verdict satisfies the policy. Exit `1` means it does not 鈥?read the
printed reason rather than retrying. Exit `2` is a usage error, which is not a pass.

Then wire the same two commands into CI (next section) so the answer is enforced rather
than remembered.

Templates for every artifact live in `templates/`; a complete worked run, with its FAIL
round included, in `examples/deepfreeze-pilot/`.

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
> **newest reviewed artifact mtime 鈮?ts 鈮?now** 鈥?check the mtimes, then stamp
> between the newest one and the present moment. If you find a blocker, say so
> in `## Blockers` and return `FAIL`; a green verdict you did not earn is worse
> than no verdict.


## Why

An agent's own report of success is not evidence 鈥?the evidence is a transcript,
and transcripts are not checkable. The **MAST** taxonomy
([arXiv 2503.13657](https://arxiv.org/abs/2503.13657), NeurIPS 2025) names this
failure class: *FM-3.2 鈥?no review, or incomplete review*. An **ICML 2026**
position paper reports **41鈥?7%** multi-agent benchmark failure rates, with
**37.2%** from committing before the coordination barrier is satisfied. The
documented incidents are loud; the expensive ones are quiet 鈥?a coding agent
logged `Failed to migrate some changes... Continuing with worktree creation` and
destroyed days of uncommitted work
([vscode #289973](https://github.com/microsoft/vscode/issues/289973)), and lost
updates are invisible to both tests and `git diff`: the file looks fine, the only
symptom is that something an agent *claimed* to do is no longer there.

This project takes the boring part: make the judgement a file, make the file
checkable, and make "no verdict" mean "not done".

## What this is 鈥?and is not

| This is | This is **not** |
|---|---|
| A **file-schema spec** for task / review / handoff / decision artifacts | An orchestrator. We don't schedule agents. |
| A **CI-runnable gate** over reviewer verdicts | A swarm library. The orchestration layer is a red ocean: `ruflo` 73k鈽? `superpowers` 293k鈽? `oh-my-opencode` 70k鈽? `crewAI` 59k鈽? `langgraph` 41k鈽? |
| A **failure-mode catalogue** justifying each rule | A model router, memory store, or vector DB |
| **Harness-agnostic** 鈥?adapters are docs, not plugins | Bound to one vendor's plugin API |

**Why the empty space matters:** every prior project we found in the
quality-control niche 鈥?`AAHP`, `agent-handoff-protocol`,
`agent-acceptance-gate` 鈥?sits at **0鈽?*; `agents-template` at 5鈽? The demand is
stated in community write-ups ("context loss is the #1 cause of multi-agent
failure"); nobody has shipped a reputation.

> **Provenance of third-party numbers** 鈥?star counts and maintenance status are
> a snapshot, not a claim in perpetuity. All observed **2026-09-29** via the
> GitHub API: [ruflo 73k](https://github.com/ruvnet/ruflo) 路
> [superpowers 293k](https://github.com/obra/superpowers) 路
> [oh-my-opencode 70k](https://github.com/code-yeongyu/oh-my-openagent) 路
> [crewAI 59k](https://github.com/crewAIInc/crewAI) 路
> [langgraph 41k](https://github.com/langchain-ai/langgraph) 路
> [AAHP 0](https://github.com/homeofe/AAHP) 路
> [agent-handoff-protocol 0](https://github.com/amkentech/agent-handoff-protocol) 路
> [agent-acceptance-gate 0](https://github.com/yanqr213/agent-acceptance-gate) 路
> [agents-template 5](https://github.com/pedrofuentes/agents-template).
> Our own first review round flagged the missing provenance here; the fix is in
> `ADR-0001.md`'s sibling commit.

**Adjacent standards.** MCP is agent鈫?tool* (vertical). A2A is agent鈫?agent*
transport and discovery (horizontal). This project is agent鈫?agent*
**accountability**: how a deliverable is *judged*.

## 60 seconds

```
your-project/
鈹溾攢 .tasks/
鈹? 鈹溾攢 AC-20260929-001.md              鈫?task card (namespaced id!)
鈹? 鈹斺攢 REVIEW-AC-20260929-001.md       鈫?review card
鈹溾攢 verdicts/
鈹? 鈹斺攢 AC-20260929-001.verdict.json    鈫?machine-readable verdict
鈹斺攢 artifacts.json                     鈫?{"AC-20260929-001": ["src/pipeline.py"]}
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
| `1` | **gate violation** 鈥?reasons printed, or `--json` for machines |
| `2` | usage/input error (bad dir, unreadable verdict). **Not a pass.** |

## What the gate enforces

- verdict exists, parses, and is `PASS` / `CONDITIONAL` / `FAIL`
- `blockers == 0` for PASS; CONDITIONAL needs `--allow-conditional` **and** a
  named `acknowledged_by`
- **`independent: true`** 鈥?the author may not approve itself
- `evidence` is a non-empty list
- **Freshness:** the verdict's `ts` must not be older than the artifact it judges.
  A verdict that predates the code is stale, and stale blocks.
  - **One exception.** If a *later* id in the map also lists that file **and is itself a
    valid authority on it** 鈥?its own verdict on disk, well-formed, independent, with
    evidence, not future-dated, and fresh on that file 鈥?then the older verdict is
    `SUPERSEDED`: the later round is the current authority. Without this, no full-chain run
    could ever go green again, because any fix to a README outlives the verdict that read
    it. A successor that is itself stale, or that has no verdict yet, retires nothing, so
    an in-flight round cannot whitewash the one before it. A successor that returned `FAIL`
    is still an authority 鈥?it retires the older claim *and* blocks on its own verdict.
    `SUPERSEDED` is always printed, never dropped.

## Conformance 鈥?claim honestly

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

## Status 鈥?honest, and version-free on purpose

**This repository is gated.** Every release below has a reviewer verdict in
`verdicts/`, and the current state of that chain is whatever the newest verdict file
says 鈥?read it rather than trusting a version number typed in prose. That sentence is
deliberate: hand-maintained version headers went stale for three consecutive rounds
(`v0.1.4, in review` while v0.1.5 was gated), always in the conservative direction,
which is exactly why they survived review.

> Correction, and it is the instructive part: the previous README said
> *"deliberately not gated yet"* while shipping a PASS verdict. It was false in
> the direction that undersells the work, which is the direction most people
> would have caught by eye. The same README claimed 45 tests while the suite held
> 69. Both statements were in prose, and the gate only ever read `.tasks/`. The
> v0.1.4 round adds `STALE_TEST_COUNT` and `UNMAPPED_CLAIM_SURFACE` so that
> **these two shapes** of defect are caught by a check instead of by a careful
> reader: a stale test count in a copy-pasteable block, and a claim surface that
> no verdict covers.
>
> Narrower than it first sounds, and deliberately so. The same round shipped a
> README command naming a file that does not exist, and the CHANGELOG asserted it
> had been removed 鈥?it had been removed from two of the three places it appeared.
> An independent review caught it
> (`verdicts/XJ-20260930-006.verdict.json`, FAIL, 1 blocker). A wrong command, a
> stale flag, a bad path in prose: none of that is checked, and no rule here
> claims otherwise.

What is not claimed: this is a **spec plus two tested tools, exercised on one real
pilot run** (`examples/deepfreeze-pilot/`) and on this repository's own history 鈥?
not a fleet, and not validated at scale. Known limitations are in `PROTOCOL.md`
搂10, including two we refuse to paper over: a file-based protocol needs a human
(or a poller) to wake the second agent, and a gate proves a check *ran*, not that
the reviewer was thorough.

> ### The reviewer in `verdicts/` is an AI, and `independent: true` is its claim about itself
>
> Every verdict in this directory was issued by the same reviewer 鈥?**an AI, not a
> human.** It signs itself inconsistently across rounds (`ximo@agnes` on the earlier
> ones, `ximo@agnes-ai` on later ones), and no tool here checks the signature field.
> Read the verdicts here as **one AI reviewing another**, checked for consistency and
> honesty by machine, not as independent human sign-offs.
>
> Each verdict carries `independent: true`, and that field is a **claim the reviewer
> makes about itself**, not a property this repository verifies. Nothing in the format
> distinguishes a reviewer that genuinely never touched the work from one that did;
> `PROTOCOL.md` 搂10.3 states this at greater length, and this note exists so that a
> reader does not have to go looking for it.
>
> What the gate actually checks is that the field is *present and readable* 鈥?that
> `independent` is not `false`. It cannot check the thing the word implies. The same
> holds for `evidence`: a self-attested list of commands the reviewer says it ran,
> never re-run by the gate. The evidence is a claim, not a receipt.
>
> We consider a limitation documented only in the appendix to be undisclosed, which is
> why it is here rather than only in 搂10.3.

## Roadmap

- [x] v0.1 鈥?spec, gate, linter, templates, adapters, one unedited worked example
- [x] v0.1.1鈥搗0.1.3 鈥?lint false positive removed, reviewer timestamp guidance
      corrected, the repository gated by an independent reviewer and published
- [ ] A second pilot on a different harness (portability evidence)
- [ ] Verifier registry 鈥?shareable acceptance checkers
- [ ] Postmortem corpus growth; a rule per named failure mode

## Contributing

Read `PROTOCOL.md`, then `postmortems.md` 鈥?the second is why this project
exists. Adapters and verifiers are the two most welcome contributions. Your PR
runs the same gate the project does; see `CONTRIBUTING.md`.

MIT 漏 15812
