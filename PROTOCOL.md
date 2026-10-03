# Agent Covenant — Collaboration Verification Protocol

**Status:** v0.1 (normative spec) · **License:** MIT · **Language of record:** English

A harness-agnostic protocol for multi-agent collaboration in which **no artifact is
"done" until an independent reviewer has produced a machine-checkable verdict that
passes a gate.**

---

## 1. What this is — and what it deliberately is not

| This IS | This is NOT |
|---|---|
| A **file-schema spec** for task/review/handoff/decision artifacts | An orchestrator (we don't schedule agents) |
| A **verification gate** convention (verdict contract + CI-runnable checker) | A swarm/topology library (see: ruflo, crewAI) |
| A **failure-mode catalogue** with linter rules | A model router, memory store, or vector DB |
| Harness-agnostic (adapters, not plugins) | Bound to one vendor's plugin system |

**Boundary with adjacent standards:** MCP is agent↔*tool* (vertical). A2A is
agent↔*agent* transport & discovery (horizontal). Agent Covenant is agent↔*agent*
**accountability** — it governs how a deliverable is *judged*, not how it is
transmitted or discovered.

**Anti-goal:** we do not want to be "another multi-agent orchestration framework".
The orchestration layer is a red ocean (73k★, 70k★, 59k★ projects). The
**verification layer is empty** (every prior attempt we found: 0★). We build here.

---

## 2. The problem this solves

Empirical evidence that unverified agent handoffs fail:

- **MAST** (arXiv 2503.13657, NeurIPS 2025): multi-agent failure taxonomy —
  FC1 spec failure, FC2 inter-agent misalignment, **FC3 task verification failure**
  (FM-3.2: no review / incomplete review).
- **ICML 2026 position paper**: mainstream multi-agent benchmarks fail at
  **41–87%**; **37.2%** commit prematurely due to missing synchronisation
  barriers; concurrency hazards (stale read, lost update, stale correction,
  action–message desync) masquerade as "coordination failure".
- **Industry incident**: a coding agent created an isolated worktree, failed to
  migrate changes, logged the failure, *continued anyway*, and destroyed
  multi-day uncommitted work (vscode #289973, data loss).
- **Lost update is invisible to tests**: a file looks fine; the only symptom is
  that what an agent *claimed* to do is no longer there.

Common thread: **an agent's own report of success is not evidence.** The protocol
below makes evidence a first-class, checkable artifact.

---

## 3. Roles and the trust model

| Role | May | May NOT |
|---|---|---|
| **Author** | create/edit code + artifacts for its task | approve its own work |
| **Reviewer** | read, question, write verdicts | edit the author's code |
| **Arbiter** | adjudicate disagreements, own the decision log | — |
| **Gate** (machine) | block release on verdict policy | judge quality |

**Hard rule R1 — independence.** A verdict must be produced by a party other than
the author. Self-review is lower trust than a separate agent or a human; it is
recorded as `independent: false` and the gate **blocks by default**.

**Hard rule R2 — single write ownership.** One artifact, one owner at a time. Two
agents editing the same file concurrently is the lost-update pattern; scope
disjointness is a *precondition* of parallelism, not an optimisation.

**Hard rule R3 — no silent success.** If an agent cannot complete a step, it must
emit a blocking question or a FAIL verdict. Absent output is never success.

---

## 4. Artifacts

All artifacts are plain files. Four kinds, fixed schemas.

### 4.1 Task card — `<NS>-YYYYMMDD-NNN.md`

`<NS>` = a namespace token (2–6 uppercase letters, unique per author/team).

```markdown
# TASK <id>: <title>
## Context          # what exists today, why this task exists
## Deliverables     # which files/behaviours will exist after
## Owned files      # paths this card exclusively owns (R2; the linter flags conflicts)
## Constraints      # boundaries: what must NOT be touched
## Acceptance       # checkable criteria (see §5)
## Review questions  # 1–4 adversarial questions, not "looks good?"
## Review handoff   # exact path + format the reviewer must write back
## Status           # OPEN → IN_REVIEW → GATED → CLOSED
```

### 4.2 Review card — `REVIEW-<id>.md`

```markdown
# REVIEW <id>: <artifact>
## Verdict          # PASS | CONDITIONAL | FAIL  (one line, machine-read too)
## Blockers         # count + list; 0 required for PASS
## Conditions       # what must be true for CONDITIONAL to stand
## Evidence         # verifier name, commands run, exit codes, output refs
## Independence     # reviewer is not the author: true/false
```

### 4.3 Handoff — `HANDOFF-<id>.md`

Short, for cross-session transfer. Five sections, ≤1 page: `Done` (with evidence
paths) / `Decisions` (with ADR refs) / `Open` / `Risks` / `Next single action`.

### 4.4 Decision record — `ADR-<NNNN>.md`

Context · Decision · Consequences · Revisit-trigger. **Revisit-trigger is
mandatory** — a decision without a stated condition for reversal is a debt.

### 4.5 Verdict file — `verdicts/<id>.verdict.json`

The machine contract. One per review.

```json
{
  "id": "AC-20260929-001",
  "artifact": "src/pipeline.py",
  "verdict": "PASS",
  "blockers": 0,
  "conditions": [],
  "independent": true,
  "verifier": "reviewer-agent@acme",
  "ts": "2026-09-29T20:31:00Z",
  "evidence": ["pytest -q → 27 passed", "linter exit 0"]
}
```

**Field semantics (normative):**

- `verdict` ∈ {`PASS`,`CONDITIONAL`,`FAIL`}. Unknown values are a policy error.
- `blockers` must be `0` for `PASS`; `CONDITIONAL` may have `0` blockers **only**
  with non-empty `conditions` and an `acknowledged_by` field.
- `independent` must be `true` unless the gate runs with `--allow-nonindependent`.
- `ts` **must be ≥ the artifact's mtime** when an artifact map is supplied.
  A verdict older than the thing it judges is *stale* and blocks. This is the
  single most-skipped check in real-world review flows.
  - **Superseded freshness.** One exception, and it exists because the rule above
    is otherwise unusable: if a **later** id in the artifact map also lists that
    file **and is itself a valid authority on it**, the earlier verdict's
    staleness on that file is reported as `SUPERSEDED` and does not block. The
    later round is the current authority on the file. Without this, a full-chain
    run can never return to green — any fix to a README outlives the verdict that
    read it, so the chain accumulates `STALE` forever and stops meaning anything.
  - **"Valid authority" means the successor passes the same bar.** It must have a
    verdict on disk, that verdict must be well-formed, independent, carry
    evidence, and not be future-dated beyond `--max-clock-skew`; and it must be
    **fresh on that file** — `mtime ≤ successor_ts ≤ now + skew`. A successor that
    is itself stale, or that judged an older copy of the file, retires nothing,
    because then nobody has judged the current file.
    - A successor that is **FAIL, or CONDITIONAL without acknowledgement**, is still
      a valid authority. It should retire the earlier claim *and* block on its own
      verdict. Requiring `PASS` here would be backwards: it would stop a later
      round from saying "this is worse than you thought".
    - This last requirement is not decoration. The first version of this rule
      accepted any later `ts`, and independent review reproduced two escapes at
      `exit 0` — a stale successor retiring a predecessor, and a **future-dated**
      successor retiring everything. The second is PM-9 reached through
      supersession instead of through its own timestamp.
  - `SUPERSEDED` is **reported, never dropped**: it appears in the human output and
    in a separate `advisories` array in `--json`. The strongest check must not
    vanish silently, so the count of superseded findings is always printed.
- `ts` **must not be in the future** beyond a small clock-skew allowance
  (`--max-clock-skew`, default 300s). A future-dated verdict never goes stale,
  so it silently defeats the rule above. This hole was found by a real reviewer
  in this repository's own first round — see `postmortems.md` PM-9.
- **Guidance for reviewers writing `ts`.** It must satisfy
  **newest reviewed artifact mtime ≤ ts ≤ now**. Check the mtimes you are
  judging (`Get-Item <f> \| Select LastWriteTimeUtc`, or `stat`), then stamp
  *after* the newest one and *before* the present moment. Two failure modes are
  on record in this repository: rounding to the half hour produced future-dated
  verdicts (rounds 1–2), and "stamp conservatively early" produced a verdict
  older than the artifacts it judged (round 3). **Do not round, and do not
  round down.** If you genuinely cannot see the filesystem (reviewing a remote
  diff), write the exact UTC time you finished reading and note the limitation
  in the verdict's `evidence` — an honest approximate beats a tidy lie.

---

## 5. Acceptance criteria must be executable

A criterion is admissible only if some agent or CI job can evaluate it to
true/false without human interpretation. Admissible: "pytest exits 0",
"`gate.py` exits 0", "row count == 21", "no TODO in diff". Inadmissible: "code
is clean", "works well", "reasonable error handling".

**Rule A1:** every `Acceptance` bullet maps to ≥1 evidence string in the verdict.

---

## 6. The gate

`tools/gate.py` implements this section. Contract:

| Exit | Meaning |
|---|---|
| `0` | every required id satisfied the policy |
| `1` | **gate violation** — machine-readable reasons on stdout/`--json` |
| `2` | usage / input error (bad manifest, unreadable verdict) |

Default policy (all must hold per required id):

1. a verdict file exists and parses;
2. `verdict == PASS`, or `CONDITIONAL` **and** `--allow-conditional` **and**
   `acknowledged_by` present;
3. `blockers == 0`;
4. `independent == true` unless `--allow-nonindependent`;
5. `evidence` is a non-empty list of strings;
6. `ts` is not in the future beyond `--max-clock-skew` (default 300s) — a
   future-dated verdict can never be reported stale, which would silently
   defeat check 7;
7. `ts >= artifact mtime` for every path in the artifact map, **except** where the
   finding is `SUPERSEDED` — see §6.1;
8. *(opt-in)* with `--evidence-must-match REGEX`, at least one evidence entry
   matches the pattern. Off by default; see §10.3 for why a pattern is not part
   of the default contract.

### 6.1 Superseded freshness

Check 7 is the strongest check the gate has, and applied to a chain it degenerates:
a README read by eight verdicts goes stale the moment any of them is followed by a fix,
so a full-chain run accumulates `STALE` forever and can never return to green. A check
whose result is constant carries no information.

**The exception.** If a **later** id in the artifact map also lists that file **and is
itself a valid, fresh authority on it**, the earlier finding becomes `SUPERSEDED` and does
not block. The later round is the current authority on the file.

**"Valid authority" means the successor clears the same bar:**

- it has a verdict file on disk, and that verdict is well-formed, passes
  `blockers == 0`, is `independent: true`, and carries non-empty `evidence`;
- its `ts` is not future-dated beyond `--max-clock-skew`;
- it is **fresh on that file**: `mtime <= successor_ts <= now + skew`.

A successor that is itself stale, or that judged an older copy of the file, retires
nothing — because then nobody has judged the current file.

**A `FAIL` or unacknowledged `CONDITIONAL` successor is still a valid authority.** It
retires the earlier claim *and* blocks on its own verdict. Requiring `PASS` would be
backwards: a later round must be able to say "this is worse than you thought".

**`SUPERSEDED` is reported, never dropped.** It prints in human output, appears in a
separate `advisories` array under `--json`, and the advisory count is printed even under
`--quiet`. A relaxation of the strongest check must be more visible than the check it
relaxes.

**Advisory, not enforced:** mapping every `Acceptance` bullet in the task card to
an evidence entry is currently the reviewer's job, performed by hand. v0.1 has no
machine-checkable acceptance *ids* to cross-reference (see ADR-0001: the card
schema would have to change first). Do not assume the gate has verified your
acceptance criteria — read the evidence.

Example:

```bash
python tools/gate.py \
  --verdict-dir verdicts \
  --require AC-20260929-001 \
  --artifact-map artifacts.json \
  --json
```

### 6.2 Pre-merge review: the push *is* the merge

A verdict only gates anything while it happens **before** the change reaches the trunk.
Once code sits on `main` — or in a published repository — the review has become an audit
of a decision already in force, which is the thing this protocol exists to prevent. Both
retroactive reviews in this repo's own history cost real time: the shim hardening landed
roughly a day before its first review, and a multi-point-snapshot change carried an
assertion count ("41 assertions") that no party had actually counted.

- **P1 — Verdict before push.** A required id may not be pushed to the trunk or to any
  published repository until its verdict file exists and the gate returns `0`. **Local
  commits are not merging**: they exist precisely so the reviewer inspects the real
  artifact instead of a description of it. Require the id in the pre-push check.
- **P2 — If it already landed, say so on the first screen.** A change already on the
  trunk gets a retrospective card whose opening block states that it landed unreviewed,
  how long ago, and what the blast radius is. A retrospective card may never be marked
  `GATED`; until a verdict exists it is a change record, and `CLOSED` must not be read
  as "passed review" (§4.1).
- **P3 — Review the artifact, not the branch tip.** The verdict's `commit` is the commit
  the reviewer actually inspected, and what merges must contain exactly that commit. If
  the trunk moved on, §6.1 decides whether the verdict still stands — and note the limit
  that §6.1 does not cover: a verdict on a *historical* commit says nothing about work
  layered on top of it. Reviewing `A` and shipping `A+B+C` is an unreviewed merge.
- **P4 — An unverified number is a defect.** Any figure in an `Acceptance` criterion
  ("41 assertions", "N files", "M ms") must carry the method that produced it. A number
  asserted by one party and merely re-copied by the next is a blocker: it gets inherited
  as an expectation, which is how a wrong count survives three rounds and two reviews.
- **P5 — The rule binds this protocol too.** This section was itself committed without
  an independent verdict. It carries the same debt it describes and is listed in the
  next review round rather than pretending otherwise.

`lint_cards.py` reports `VERDICT_WITHOUT_REVIEW` when a `GATED`/`CLOSED` card has no
verdict file. It stays a warning on purpose, because P2 allows honest change records.
Raising it to an error has to wait until cards can declare `retrospective: true`
explicitly — ADR-0001 covers why that needs a schema change first.

---

## 7. Naming: why cards are namespaced

**Observed failure (unpublished elsewhere as far as we could find):** a
collaboration card named `TASK-002.md` was silently hijacked by a second agent
that had its own unrelated `TASK-002` in context. The review came back confident,
detailed, and about the wrong artifact. Nothing errored. That is the dangerous
part.

**Rule N1:** every card filename carries a namespace token and a date:
`<NS>-YYYYMMDD-NNN.md`. Bare `TASK-N`/`REVIEW-N` names are non-conformant.

A review request may additionally carry a project prefix:
`<NS>-REVIEW-REQUEST-<NS2>-<date>-<NNN>.md`. Use it when a request travels through a
mailbox shared by several agents, so it cannot be mistaken for another project's. The
unprefixed `REVIEW-REQUEST-<NS>-<date>-<NNN>.md` remains valid and is the simpler choice.

**Rule N2:** the trigger handed to a reviewing agent is the **absolute path** of
the card, plus the instruction to read it *before* acting. Never "look at
TASK-002".

`tools/lint_cards.py` enforces N1, plus schema and orphan rules (see
`docs/lint-rules.md`).

---

## 8. Cleanup / TTL — the anti-bloat rule

Collaboration state is **not** memory. Without a hard rule, card directories grow
into an unsearchable attic that agents re-read instead of thinking.

- A card reaching `GATED` is **archived or deleted within one working day**.
- Only conclusions persist: decisions → ADR; durable lessons → the project's
  knowledge surface; process chatter → deleted.
- Mailboxes (inbox/outbox files) are **emptied on close**, capped at N items;
  when any mailbox exceeds the cap, the owning agent triages it unprompted.
- Verdict files referenced by an archived card are deleted together with it.

---

## 9. Conformance levels

| Level | Requirement | Who adopts it |
|---|---|---|
| **L0 Unstructured** | agents talk freely, no artifacts | the default today |
| **L1 Carded** | namespaced cards, schemas, independence rule, human relay allowed | small teams, one repo |
| **L2 Gated** | machine verdicts, `gate.py` in CI, no human in the gate loop | teams shipping to production |

Claiming L2 with a human clicking "approve" in the loop is L1 with extra steps.
Say which level you actually run.

---

## 10. Known limitations (stated honestly)

1. **Relay remains human in most deployments.** A file-based protocol needs
   something to wake the second agent. Until adapters ship a poller, a human
   usually relays "read <path>". This is a real gap, not a detail.
2. **A verdict proves a check ran, not that the work is good.** Gates raise the
   floor; they do not raise the ceiling.
3. **Reviewer quality variance.** A lazy reviewer produces a green verdict. The
   gate cannot detect a rubber stamp; it only guarantees someone *claimed* to
   check, with evidence attached.
4. **Adapters are documentation, not code.** Cross-harness support is
   instructions, not a runtime shim.
5. **Acceptance mapping is advisory.** The gate does **not** verify that every
   `Acceptance` bullet in your card is covered by an evidence entry. v0.1 has no
   machine-readable acceptance ids to cross-check, so the reviewer does this by
   hand and the gate checks only that *some* evidence exists. Demoted from
   normative policy after the first review round found the spec claiming more
   than the code did — see `ADR-0001.md`.
6. **Evidence quality is opt-in.** A non-empty `evidence` list passes; so does
   `evidence: ["ok"]`. We do not ship a default pattern because a regex that
   rejects honest short evidence trains people to pad. Teams that want the floor
   can opt in: `gate.py --evidence-must-match 'exit [0-9]|passed|failed'`.
7. **Gate counts are not reproducible across checkouts.** A violation count is a
   property of one working directory at one moment, not a property of the repository.
   `gate.py` resolves the relative paths in `artifacts.json` against the **process
   CWD**, and `_check_freshness` compares `path.stat().st_mtime` against each
   verdict's `ts`. A `git clone` or `git worktree add` writes every file with the
   current time, so in a clean checkout every artifact looks newer than every
   verdict: staleness approaches its maximum and nothing is `SUPERSEDED`, because a
   successor can never itself be fresh on the file it would retire. In this
   repository, commit `9928bec` reports 59 blocking / 0 advisories in a clean
   checkout (4 `VERDICT_FAIL`, 1 `CONDITIONAL_NOT_ALLOWED`, 54 `STALE_VERDICT`),
   while the working tree at `05a1e42` — after the 012 verdict landed — reports
   7 blocking / 42 advisories, and at `eed7ff7` 20 blocking / 31 advisories.
   Different trees, different commits, different CWDs, different answers. Two consequences for anyone citing a number from
    this gate: **a reproducibility claim needs three coordinates — a commit, a command,
    and a CWD** — and any count quoted without all three is not evidence, however
    plausible it looks. This is a limitation of the mtime-based freshness design, not a
    bug in the rule of round 11; the rule makes staleness reportable, not fixed.
    Since v0.1.12 the gate helps rather than just warns in prose: every run binds
    `cwd` (and a `split_run` flag, true when the verdict directory or artifact map
    sits outside the CWD's subtree) into its output, and a split run prints a banner
    saying the counts may not describe the checkout the caller thinks they are
    testing. The banner is advisory — it never changes findings or exit codes.

---

## 11. Repository map

```
PROTOCOL.md            this document (normative)
postmortems.md         failure-mode catalogue → each maps to a rule or lint
docs/lint-rules.md     rule-by-rule rationale
tools/gate.py          verdict gate (CI-runnable)
tools/lint_cards.py    card/schema linter
templates/             TASK / REVIEW / HANDOFF / ADR starting points
adapters/              per-harness integration notes (claude-code, codex, opencode)
examples/              a real, messy pilot run end-to-end
tests/                 the tools' own tests (the tools obey §5 too)
```

## 12. Contributing

Read `PROTOCOL.md`, then `postmortems.md` — the second one is why this project
exists. Adapters and verifiers are the two most welcome contributions. See
`CONTRIBUTING.md`.

Licensed under MIT. See `LICENSE`.
