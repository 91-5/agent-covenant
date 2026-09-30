# Postmortems — the failure catalogue

Every rule in `PROTOCOL.md` exists because something went wrong. This file is the
"why". Provenance is marked honestly: **[ours]** = observed in our own runs,
**[literature]** = documented elsewhere and cited.

---

## PM-1 · Task-ID collision produced a confident review of the wrong artifact

**[ours]** A collaboration card named `TASK-002.md` was written for a memory-plugin
selection task. A second agent had its own unrelated `TASK-002` (a dorm-allocator
script project) in context. It reviewed *that*.

The dangerous part was not the mistake — it was that **nothing errored**. The
review came back long, specific, well-structured, with 3 blockers, 5 suggestions
and 8 test cases. All of it about files the reviewer had never been asked to look
at. A less careful reader would have merged it.

Root causes, in order of damage:
1. **No namespace.** `TASK-002` is a name two agents can both legitimately hold.
2. **The trigger was a bare name** ("read TASK-002"), not a path, so the reviewer
   resolved it against its own context instead of the filesystem.
3. **No cross-check that the artifact under review matched the task.** Nothing in
   the protocol forced the reviewer to prove it was looking at the right thing.

**Rules:** N1 (namespaced card ids), N2 (hand over absolute paths), R2 (single
write ownership).
**Enforced by:** `lint_cards.py` → `NAMESPACE_MISSING`, `BARE_TASK_NAME`.
**Search note:** we could not find any published postmortem for this specific
mode. The nearest public material covers lost updates and context drift, not
identifier collision. If you have seen it, please open an issue — the rule set is
better with more evidence.

---

## PM-2 · The gate that was never run

**[literature + ours]** In the ICML 2026 position paper on multi-agent systems,
37.2% of failures come from committing before the coordination barrier is
satisfied; the MAST taxonomy (arXiv 2503.13657) names the same class as
*FM-3.2 — no review or incomplete review*. Meanwhile the default state of most
agent setups is L0: no artifacts, no verdict, everybody trusts the transcript.

The failure is not that a human lied. It is that **"the agent said it was done"**
is the only evidence that exists.

**Rule:** §5 (acceptance criteria must be executable), §6 (the gate).
**Enforced by:** `gate.py` — no verdict file means no pass, and a missing
required id is a violation, not a skip.

---

## PM-3 · A rubber-stamp verdict

**[literature + ours]** Existing harnesses ship review as an *optional* role: a
consulting architect agent, a `code-reviewer` subagent, a human clicking approve.
A reviewer that has not actually read the diff still produces a green run, and
the transcript looks identical to a real review.

**Rule:** R1 (independence), §4.5 (verdict must carry evidence), R3 (no silent
success).
**Enforced by:** `gate.py` → `NO_EVIDENCE`, `NOT_INDEPENDENT`, and the opt-in
`--evidence-must-match` floor.
**Known limits (stated in PROTOCOL.md §10.3 and §10.6):** the gate cannot detect
a rubber stamp. It raises the floor; it does not raise the ceiling. A non-empty
evidence list passes — `evidence: ["ok"]` is a passing verdict unless the team
opts into a pattern.

---

## PM-9 · A verdict dated in the future can never go stale

**[ours — found by our own external reviewer, on this repository, first round]**

The freshness check (§4.5) compares the verdict's `ts` against the artifact's
mtime. It worked exactly as designed on the worked example… and then the first
real review of this project arrived with `ts: 2026-09-30T00:00:00Z` — eight hours
in the future, because the reviewer's clock was in a different timezone than the
one we stamped the files with. With a future-dated `ts`:

- the artifact is never newer than the verdict, so `STALE_VERDICT` can never fire;
- the check that everyone agrees is the important one silently degrades to a
  no-op **for that verdict, forever**;
- nothing looks wrong. The verdict says PASS. The gate says PASS.

A round number like `00:00:00Z` is the tell: nobody finishes a review at exactly
midnight UTC. The same class of bug bit us one layer down in the worked example
(local time labelled `Z`), which is why the lesson appears in two places — the
example README and here.

**Rule:** §4.5 — `ts` must not be in the future beyond `--max-clock-skew`
(default 300s).
**Enforced by:** `gate.py` → `FUTURE_VERDICT`.
**Transferable lesson:** any check phrased as a comparison between two timestamps
is only as good as the *direction* you check. We checked "too old" and forgot
"not yet". Ask what a hostile or merely careless input would make vacuous.

*Occurrences, for pattern recognition:* round 1 of this repository's own review
arrived with `ts` **+8h** (timezone confusion). Round 2 arrived with `ts`
**+9 min** — `07:30:00Z` against a 07:23:20Z clock, because the reviewer
timestamped to the half hour. Round 3 arrived with `ts` **−11 min** — *older
than the artifacts it judged* — because **the author's own handoff instruction
told the reviewer to "stamp conservatively early"**.

Three rounds, three malformed timestamps, all caught by this rule and its
sibling. The third one deserves attention because it was not carelessness by the
reviewer: the author wrote an instruction that *guaranteed* the failure, while
believing they were being careful. "Be conservative with timestamps" is
meaningless without a direction; the correct instruction is "after the newest
thing you read, before now".

**Transferable lesson:** guidance you give another agent is part of the check's
threat surface. If your handover instruction can be satisfied in a way that
defeats the gate you also wrote, you have shipped a bug in prose. Every such
instruction belongs in the same test suite as the code.

---

## PM-10 · The gate quietly weakened itself when a flag was forgotten

**[ours — same review round, second defect]**

Hours after fixing PM-9, we ran the gate on that same verdict and it returned
**PASS**. We had expected a block. Two causes, both instructive:

1. The verdict's `ts` was a round number in the future *at review time*. By the
   time we ran the check, the clock had caught up — which is the correct
   behaviour of the new rule, and a reminder that a timestamp check is only as
   stable as its calibration.
2. **We had not passed `--artifact-map`, so the freshness rule never ran at
   all.** Exit code 0. No warning. The strongest check in the tool was simply
   absent, and the output looked exactly like a clean pass.

A verifier that reports success while silently skipping its most important check
is worse than no verifier, because it transfers false confidence. This is the
same family as PM-6, one layer up: there, a checker crashed; here, a checker
*shrank*.

**Rule:** §6 — the gate prints a `NOTICE` for every checked id that has no entry
in the artifact map, stating that freshness was not checked. Silently, under
`--quiet`/`--json`, it is suppressed for machine consumers — which is a
documented trade, not an oversight.
**Enforced by:** `gate.py` notice path + three tests
(`TestSilentDegradationGuard`).
**Transferable lesson:** when a check is conditional on configuration, the
configuration gap must be *loud*. A default that quietly disables the check is
the same class of bug as a default that quietly enables destructive behaviour —
inverted.

---

## PM-11 · Asserting a fix you did not finish, because the artifact exists in three copies

**[ours — round 5, `verdicts/XJ-20260930-006.verdict.json`, FAIL, 1 blocker]**

We wrote a command into a CI example naming a file that does not exist
(`tools/test_gate.py`). We found it, deleted it, and confirmed the file was gone.
Then we wrote the following sentence in a CHANGELOG entry and a commit message:

> the phantom step was **removed rather than shipped**

It was shipped. The command appeared in **three** places — `README.md`,
`README.zh-CN.md`, and the CI workflow — and we verified the removal in two of
them. The Chinese README kept it, in a fenced code block, for the reader least
likely to eyeball it. The independent reviewer found it on the first pass.

Two failures, not one:

1. **A claim that ran ahead of the work.** The false sentence is the more
   damaging half, and its direction matters: it claimed *more* diligence than
   existed. This is R3's "no silent success" family pointed at ourselves. A
   reviewer reading that CHANGELOG would have been told the defect class was
   closed.
2. **Fixing one instance of a duplicated artifact is not fixing the defect.**
   The check we ran — "does the file exist?" — was the wrong check. The right one
   enumerates every copy.

**Rule:** §4.1 — acceptance criteria are stated as commands, and a fix is
complete when every copy of the artifact satisfies them, not when one does.
For duplicated text specifically: enumerate the copies *before* editing, so the
count is known.
**Enforced by:** none. This is not machine-checkable in general — verifying that
a command in a README names a file that exists is a documentation linter, not
this project. Stated here because the gap is deliberate and must be visible.
**Transferable lesson:** *asserting completion is itself a claim, and it is the
one claim nothing in your pipeline re-reads.* The irony is load-bearing: this
defect survived inside a fenced code block through a round whose stated purpose
was making prose checkable, and the new rule could not see it, because the rule
reads a number and not a command. Two rules narrowed the class; the honest claim
is "these two shapes", never "this class".

---

## PM-4 · The verdict that outlived its artifact

**[ours]** Reviews are point-in-time judgements. Code keeps moving. A verdict file
that said PASS last week still sits in the directory, still green, while the
artifact underneath it has been rewritten twice — possibly by the very agent the
review was supposed to constrain.

This is the quietest failure in the whole catalogue, because every individual
step looked correct. The review was valid; the verdict just wasn't *about the
current thing any more*.

**Rule:** §4.5 — `ts` must be ≥ the artifact's mtime.
**Enforced by:** `gate.py` → `STALE_VERDICT`, `ARTIFACT_MISSING`.
This is the check we expect teams to skip first, and the one that matters most.

---

## PM-5 · Lost update: the file looks fine

**[literature]** Documented across worktree-based multi-agent setups: agent A
creates a file, agent B runs a clean checkout and wipes it. The characteristic
property, noted in community write-ups, is that **you cannot catch it with tests
or a diff — the file looks fine**; the only symptom is that something an agent
claimed to do is no longer there. MAST classifies the family as concurrency
hazards: stale read, lost update, stale correction, action–message desync.

**Rule:** R2 (single write ownership) — disjoint scopes are a precondition of
parallelism, not an optimisation.
**Partially enforced.** The *write-time race* is not lintable — it needs a
runtime lock. The **planning-stage declaration is lintable**: cards declare
ownership in `## Owned files` and `lint_cards.py` reports two active cards
claiming the same path (`OWNED_FILES_CONFLICT`). The runtime conflict remains
organisational. An earlier version of this file claimed the whole family was
"not enforced by a tool"; our first external reviewer caught the over-claim —
the same defect class this catalogue documents, committed by the catalogue
itself.

---

## PM-6 · A verifier that crashes on hostile input is not a verifier

**[ours]** The first version of our restore-checker hashed every file after a
restore. With one file held open by another process, the hash call *threw* — and
because the script ran with `$ErrorActionPreference = 'Stop'`, the process died
**before it could report anything**. The check that was supposed to catch
"something did not restore" was itself the thing that failed, silently, with a
non-zero exit code that looked like a pass to any CI step reading only the exit
status of the caller.

The lesson generalises: **a verifier must degrade to a finding, never to a
crash.** Any input it cannot read is itself a finding ("unreadable → drift"),
because unreadable means unverified.

**Rules:** §5 (criteria must be executable *by the checker*), §6 (exit codes are
a public contract: 0 pass, 1 violation, 2 usage error — never an accidental
third meaning).
**Enforced by:** the gate's own test suite, which asserts the exit-code contract
explicitly.

---

## PM-7 · Encoding and platform rot

**[ours]** A PowerShell 5.1 script written as UTF-8 without a BOM was parsed as
GBK; the mangled bytes broke the parser, not the text. Separately, a CLI invoked
through `powershell.exe -File` cannot bind `-Confirm:$false` (string → switch
conversion), which pushed us into designing an explicit `-AutoConfirm` instead
of leaning on the host default.

**Rule:** §5 in practice — a criterion whose *checker* depends on an implicit
environment is not executable. Make the environment explicit or the check is a
coin flip.
**Guard rails shipped:** non-ASCII-safe stdout in both tools; stdlib-only
implementation; the linter flags non-ASCII filenames.

---

## PM-8 · The human in the switchboard

**[ours, and still true]** Our file-based mailbox works because a human says
"read `<path>`". Two agents do not, on their own, wake each other. Every
deployment we can think of either has a human relay or a poller daemon. We
chose not to ship a daemon: it turns a spec repository into a service with
lifecycle, upgrades and failure modes.

**Stated as a limitation, not hidden:** PROTOCOL.md §10.1, and L1 in the
conformance table is explicitly "human relay allowed". A project that claims L2
while a person clicks approve is doing L1 with extra steps.
**When it changes:** if a second harness adapter plus a wake mechanism land,
this entry becomes a design note instead of a limitation.

---

## How to use this file

Adding a postmortem is the highest-value contribution this project accepts. A
good one names the failure, shows that it was **silent**, identifies the layer
where it should have been caught, and states honestly whether a tool can catch
it at all. "Not enforceable by a tool" is a valid and welcome answer.
