# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [SemVer](https://semver.org/spec/v2.0.0.html).

## [0.1.11] - 2026-10-01

Round 012 was reviewed **FAIL, 2 blockers** — the ledger prose, not the rule. This round
fixes that prose and records what the two failures actually taught. No `tools/` or `tests/`
change; the rule is untouched since `0003db4`.

**What the 012 review found.** The `[0.1.9]` effect paragraph was labelled *stated
reproducibly* while none of its three figures was reachable, and the projected post-verdict
advisory count was wrong (40, where the run gives 42). Both are corrected above.

**The part worth keeping: how the wrong number was produced.** My evidence addendum for 012
claimed "a clean checkout of `9928bec` yields 17 blocking / 31 advisories". It did not run a
clean checkout. `gate.py` resolves `artifacts.json`'s relative paths against the process CWD,
and the run's CWD was the main repository, so it stat'ed the working tree and called it a
clone. A true clean checkout — CWD inside the worktree — reports **59 blocking / 0 advisories**.
Same commit, same command, different CWD. The independent reviewer read that addendum, took
17/31 as the clone's output, and wrote it into a signed verdict card; the error propagated
from my evidence into someone else's evidence because neither of us checked the CWD. That
makes this the first time in this repository's history that the author produced a false
figure and the reviewer repeated it, and it is the exact species of defect rounds 5, 7, 8 and
9 were all about.

**The rule this yields.** A reproducibility claim needs three coordinates — a commit, a
command, and a CWD. Naming two is how a working-tree reading becomes a "clean checkout"
reading. Added to `PROTOCOL.md §10` as a known limitation.

**A second figure, wrong in the same way.** My addendum also derived the post-verdict state
as "6 blocking / 42 advisories". Six assumed this round's verdict would be PASS; it was FAIL,
so the chain carries a fifth `VERDICT_FAIL` and checks 10 ids, not 9 — the reviewer measured
7 / 10 / 42. A projection about a verdict that had not landed is not a measurement, and this
project has now failed review twice over numbers of that kind.

**Option (b) rejected — no maintenance ids.** The 012 review asked how to clear the residual
`templates/TASK.md` staleness, whose only mapper is 001, and suggested "a maintenance id that
re-maps `templates/TASK.md`". Rejected: a round that maps a file it never changed would
attest freshness it did not earn, and once such a round exists, "re-map it next cycle" retires
any staleness on demand. That is the laundering channel the `SUPERSEDED` rule exists to close,
opened from the other side. The artifact map also carries two incompatible duties — claim-surface
coverage (must not omit a README, or `UNMAPPED_CLAIM_SURFACE` fires) and round-scope declaration
(a round should list what it edited) — which is why 012 had to list both READMEs it never
touched. Splitting those duties is the honest fix and belongs to a future round that touches
`gate.py`; 013 records the conflict and defers the change rather than quietly picking a side.

> **Correction filed against the 012 evidence.** `REVIEW-EVIDENCE-CORRECTION-XJ-20260930-012.md`
> in the reviewer's vault supersedes the clean-checkout figure in the original addendum. The
> 012 verdict and its card are left unamended, per the no-retrofit rule; this entry is where the
> error is recorded.

## [0.1.9] - 2026-09-30 (failed review: FAIL, 1 blocker)

This round changes a tool. Every round before it changed prose, which is the only thing
in this repository that had no checker.

**The defect.** `gate.py` marks a verdict stale when an artifact is newer than the
verdict's `ts`, and blocks. Correct in isolation, and unusable in practice: a full-chain
run with no `--require` reports **41 violations across 8 ids** on this repository, and
could never report anything else. `README.md` has been read by eight verdicts since
round 1; every fix since then made all of them stale at once. The chain could not
return to green no matter how correct the work was, so "the gate passes" stopped being a
statement about anything.

This is a failure mode the project already had a name for and did not apply to itself:
a check whose result is constant carries no information. `STALE_TEST_COUNT` exists
because a number nobody re-checks is a liability. A gate that can only ever fail is the
same thing wearing a different hat.

**The rule.** If a later id in the artifact map also lists that file **and has a verdict
of its own**, the earlier verdict's staleness on that file becomes `SUPERSEDED`: the
later round is the current authority on the file. Reported, never dropped - it appears
in the human output and in a separate `advisories` array under `--json`, and the count
is always printed, because a check that vanishes silently is worse than no check.

**What keeps this from being a laundering channel.** Independent review of the first
version of this rule returned **FAIL, 2 blockers**, and both escapes returned `exit 0`.
The first draft accepted any later `ts` as proof of authority; two things got through:

- **A successor that was itself stale retired its predecessor.** `AC-002` judged an older
  copy of the file than the one on disk, so nobody had judged the current file, yet `AC-001`
  came back `SUPERSEDED`. Full-chain still failed on `AC-002`, but `--require AC-001` — the
  acceptance command — passed with zero fresh coverage.
- **An unchecked successor laundered.** The candidate scan read only file existence and a
  parsable `ts`: no plausibility check, no verdict-value check. A successor stamped 30 days
  in the future retired everything. That is **PM-9 returning through a second door** — a
  future-dated verdict silently defeating the freshness rule, now via supersession instead
  of via its own timestamp. `independent: false` and `evidence: []` worked the same way.
  Six tests had passed.

The fix inverts the precondition: a successor must clear the same bar any checked id does,
and must itself be fresh on that file. `_successor_candidates` runs the real `_check_*`
helpers against each candidate and drops it if anything blocks; `_superseded_by`
additionally requires `mtime <= successor_ts <= now + max_clock_skew`.

**Requiring the successor to be PASS would have been the wrong fix**, and the reviewer said
so unprompted. A later `FAIL` is the legitimate current authority on a file: it should
retire the earlier claim *and* block on its own verdict. Demanding `PASS` would mean a later
round saying "this is worse than you thought" could not retire an earlier round's claim,
which is backwards. There is now a test that asserts exactly this, and checks that the
successor still blocks when examined directly.

**A separate defect, in my own fix.** While repairing the two escapes I wrote calls to
`validate_verdict`, `DEFAULT_EVIDENCE_PATTERN`, `DEFAULT_MAX_CLOCK_SKEW` and
`_NON_BLOCKING_CODES` — none of which exist in this codebase. I wrote them from memory
instead of reading `gate.py`, and the first run died on `NameError`. Same family as the
prose defects in rounds 5, 7 and 9: asserting a shape the code does not have. The real
checks are the `_check_*` helpers `evaluate` already calls, and the repair calls those.

**Verification.** `TestSupersededFreshness` (6) and `TestSuccessorMustEarnAuthority` (5).
The five new tests were confirmed to **fail** against the pre-fix `gate.py` and pass after,
so they pin the behaviour instead of trailing the implementation. 84 → 95 tests. Writing the
first six also surfaced a bug in the tests themselves: the fixtures used a bare relative
artifact path, which `gate.py` resolves against the process CWD, so three of them were
quietly testing this repository's real `README.md` instead of the sample file. They passed,
and they were checking the wrong object. The fixtures now pass absolute paths.

**Effect on this repository's own chain: a count is a property of a checkout, not of the
repository.** Earlier drafts of this entry carried figures — "41 blocking violations across
8 ids", "28 violations and 17 advisories", "once this round's own verdict landed, 6 blocking
across 9 ids plus 40 superseded advisories". A reader following that label cannot reproduce
any of them, and the reason is mechanical rather than rhetorical. `gate.py` resolves the
relative paths in `artifacts.json` against the **process CWD**, and `_check_freshness`
compares `path.stat().st_mtime` against each verdict's `ts`. A checkout writes every file
with the current time, so in a clean clone every artifact looks newer than every verdict —
nothing can be `SUPERSEDED` (a successor is never fresh on the file it would retire), and
staleness runs near its maximum. Measured at commit `9928bec`, in a worktree whose CWD is the
worktree root, the chain reports **59 blocking violations across 9 checked ids and 0
advisories** (4 `VERDICT_FAIL`, 1 `CONDITIONAL_NOT_ALLOWED`, 54 `STALE_VERDICT`). The same
commit in the author's working tree, same command, CWD = repo root, reports 7 blocking and 42
advisories. Same tree, same command, different CWD — different answer. What stays true across
checkouts is the *shape*, not the tally: one `VERDICT_FAIL` per failed review (006, 008, 009,
011, 012), one `CONDITIONAL_NOT_ALLOWED` on 001 unless `--allow-conditional` is passed, and
one residual `STALE_VERDICT` on `templates/TASK.md`, whose only mapper is still 001 because no
round has re-judged it since round 1. A figure is reproducible only when a commit, a command,
**and** a CWD are named together; this project's own first addendum for this round named two of
the three and got the third wrong — see the correction filed for the 012 review.

> **An earlier draft of this entry claimed "41 violations to 10" and listed
> `templates/TASK.md` among the files this round touched.** Both were false: neither
> count was reachable from any run, and `git show --stat 0003db4` lists nine files, not
> including `templates/TASK.md`. The rule, the tests and both READMEs were correct and
> are unchanged; the defect was the ledger describing them — the same failure as the prose
> defects in rounds 5, 7 and 9, made by the author this time.

## [0.1.8] - 2026-09-30 (failed review: FAIL, 1 blocker)

Round 7 (v0.1.7) returned **FAIL, 1 blocker**, and the blocker was a typo in the
getting-started section: `examples/deepreeze-pilot/` for a directory that is
`examples/deepfreeze-pilot/`. One character, in a file the reviewer had already verified
six times over, named correctly three other places in the same document.

**Fixed - B1.** One character. The section now resolves.

**The part worth recording.** The round-7 review request stated that every command in
`Your first round` had been walked against `--help` before being written down. That was
true, and it was the wrong check. I verified the *commands* and not the *paths* they
refer to, so a wrong path walked straight past a verification I described as thorough.
The reviewer's words: *"I walked the tutorial's commands against --help but not its
paths."*

This is the third time in four rounds that a wrong path in prose survived, and the
second time in a round whose own claim of care made it easier to miss. round 5's
phantom command, round 8's overstated disclosure, and this were all in the same family:
a statement about a file, in prose, that no tool reads.

**Guard rails shipped:** every path named in both `Your first round` sections is now
resolved against the working tree before this entry is written, and the reviewer
re-verifies by glob. A3 suggested extending the walk to paths; it should have been
there from the first version of the section.

**Also closed:** the round-7 and round-8 cards and review cards are archived to
`legacy/` in their committed form, and the two active-path deletions that were left
uncommitted in 6477b4c are recorded here, so that a `git checkout .` cannot resurrect
a duplicate (advisory A4).

## [0.1.7] - 2026-09-30 (failed review: FAIL, 1 blocker)

Round 6 (v0.1.6) returned **FAIL, 1 blocker**, and the blocker was in the sentence
that existed to be honest. Both fixes land here, plus the two advisories that were
waiting for a round to attach to.

**Fixed - B1, the disclosure that overstated itself.** Both READMEs opened the
disclosure with *"Every verdict in this repository was issued by `ximo@agnes-ai`"*. That
is false: two verdict files carry `ximo@agnes` without the suffix. A second sentence
said *"the seven verdicts here"* when six existed when it was written. Both claims were
falsifiable against the very directory they describe, and the reviewer falsified them.
The disclosure now names no signature and no count, states that the signature varies
across rounds and that no tool checks the field, and says that `evidence` is a
self-attested list the gate never re-runs. The substance of the disclosure was accepted
as correct; only the claim strings were wrong.

**Added - `Your first round`.** Six steps from clone to gated verdict: copy the two
tools, pick a namespace, fill `templates/TASK.md`, declare `artifacts.json`, ask for a
review, run the gate. `templates/` and `examples/deepfreeze-pilot/` were previously
unlinked from the README - a first-time reader had no documented path from an empty
directory to a passing gate.

**Fixed - A1, the stale Status header.** `## Status - v0.1.4, honest` sat above a
release that had passed three rounds earlier, always in the conservative direction,
which is why it survived review. Both READMEs now carry no version number in Status and
point at the newest verdict file instead. A header that cannot go stale is worth more
than a correct one that will.

**Added - PM-12.** The disclosure that overstated itself, as a postmortem: being
careful about which claim you are making is not a substitute for checking whether it
is true, and a limitation written down honestly can still be false.

**Deferred.** Advisory A2 asked to re-apply the reviewer's later draft of the round-6
verdict over the committed one. Declined: rewriting a committed verdict is the act this
protocol exists to prevent, and the committed version is the one that disclosed the
round-5 divergence. The draft remains on disk and uncommitted. A4 and A5 were absorbed
here (PM-12, and a recorded note on the id gap at 003).

## [0.1.6] - 2026-09-30 (failed review: FAIL, 1 blocker)

No rule, tool, or check changed in this round. One disclosure was added, and the
linter caught the omission that produced it.

**Added:** both READMEs now state, in the Status section, that the reviewer recorded
in `verdicts/` is `ximo@agnes-ai` — **an AI, not a human** — and that
`independent: true` is a claim the reviewer makes about itself rather than a property
this repository verifies. `PROTOCOL.md` §10.3 has said so since v0.1; the point of
this round is that a limitation documented only in the appendix is not disclosed. The
gate checks that the field is present and not `false`. It cannot check the thing the
word implies.

**Why now:** the repository is going public. Seven verdicts carrying
`independent: true`, read from outside, read as verified independence. That inference
is available to any reader and false, which makes it this project's own defect class —
a claim surface that outruns the tools. Round 006 was such a claim in the
overselling direction; this one is in the direction people mistake for modesty, which
is why it survived as long as it did.

**Caught by the tooling, in this round:** `CHANGELOG.md` was not listed under the new
id, so `UNMAPPED_CLAIM_SURFACE` warned that no freshness check covered the file this
entry lives in — written while editing two READMEs three lines above. The rule from
v0.1.4 fired on its own author in the same round it was meant to catch. It is recorded
here rather than left as a passing log line, because a warning that is only ever fixed
in the diff is a warning that is not yet a habit.

**Corrected:** the v0.1.5 header below said *"in review, not yet gated"* after round 6
returned `PASS` with zero blockers. False in the conservative direction — the harmless
direction, and the one that still needed fixing.

## [0.1.5] — 2026-09-30 (gated: PASS, 0 blockers, round 6)

Round 5 returned **FAIL, 1 blocker**. The reviewer was right on every point and
nothing was argued. This round clears the blocker and stops claiming more than
the tools do.

### Fixed

- **B1 — a README command naming a file that does not exist, asserted as removed
  when it was not.** The command appeared in `README.md`, `README.zh-CN.md` and
  `.github/workflows/gate.yml`; the round verified the removal in two of the three
  and the Chinese README kept it. The CHANGELOG entry and commit message for
  v0.1.4 both said the phantom step was "removed rather than shipped". That claim
  was false, and it claimed *more* diligence than existed — R3's no-silent-success
  rule, pointed at ourselves. Recorded as **PM-11**: asserting completion is
  itself a claim, and fixing one copy of a duplicated artifact is not fixing the
  defect.
- **F2 / F3 — the two READMEs taught different commands.** The Chinese CI example
  omitted `--artifact-map` (so freshness silently never ran — PM-10 re-enacted
  inside the example meant to teach the tool) and `--strict`. Both READMEs now
  carry byte-identical command blocks.
- **F4 — the "caught by a check instead of by a careful reader" claim, in both
  languages, narrowed** to the two shapes the rules actually check, with the
  unchecked shapes named: a wrong command, a stale flag, a bad path. B1 is the
  proof that the broader claim was false — the defect survived inside a fenced
  code block, through the very round that added the rules.

### Added

- **`TEST_COUNT_UNVERIFIED` (WARN)** — `STALE_TEST_COUNT` reads its baseline by
  importing the test suite, so "I could not run my own check" is reachable. It
  previously reported nothing in that state, which is PM-10 inverted: a check that
  switches itself off and looks like a pass. This rule shipped with that exact
  bug — `top_level_dir` made discovery refuse to import a non-package `tests/`,
  leaving the rule dead on this repository until a test caught it.
  Detected by walking the discovered suite for `_FailedTest`, because `unittest`
  does **not** raise on a broken import: it substitutes a placeholder and returns
  a count. An exception-only guard would have compared a declared number against a
  meaningless baseline — a confident answer from a broken instrument.
- **`--artifact-map` now defaults to `./artifacts.json`** when that file exists.
  A check that only runs when a flag is remembered is a check that will be
  forgotten (PM-10), and the flagless invocation is what a cold reader types. A
  project with neither the flag nor the file remains out of scope, since the rule
  would otherwise invent a baseline.

### Changed

- `STALE_TEST_COUNT` rationale sharpened to state the rule's own ground — *a
  claim the project makes about its own deliverable* — rather than the author's
  embarrassment at shipping the wrong number. The severity stays ERROR.

### Notes

- Round 5's card, review card and FAIL verdict are archived to
  `.tasks/legacy/` verbatim. They are the only record that this defect class was
  caught by a human and not by a tool, and the 006 artifact map is left intact
  because a FAIL is evidence, not a mistake to tidy away.
- 84 tests.

## [0.1.4] — 2026-09-30 — **superseded by 0.1.5; failed review**

Three false claims shipped in the published README, and the gate that had
certified the release never saw them — the defect class this project exists to
prevent, occurring in the project itself. The text is corrected; more
importantly, two rules now make the class checkable.

This round was reviewed and returned **FAIL with one blocker**
(`verdicts/XJ-20260930-006.verdict.json`): a phantom command survived in
`README.zh-CN.md` while this changelog claimed it had been removed. See
[0.1.5](#015--2026-09-30-in-review-not-yet-gated) for the fix. What follows is
the record of the round as it was submitted, including the claim that turned out
to be false.

### Fixed

- `README.md` claimed **45 tests** while the suite held 69. `README.zh-CN.md`
  claimed the same. Corrected to the real count, which the new rule enforces.
- Both READMEs reported `Status: v0.1` after the v0.1.3 tag.
- `README.md` stated the repository was *"deliberately not gated yet"* while
  carrying a PASS verdict with zero blockers. The error ran against the
  direction that undersells the work, which is the direction a careful reader
  is most likely to catch by eye.

### Added

- `STALE_TEST_COUNT` (ERROR) — reads the test count declared in the copy-pasteable
  command block of `README.md` / `README.zh-CN.md` back and compares it with the
  suite, discovered in-process with no subprocess. Covers English (`# 82 tests`)
  and Chinese (`82 个单测`) declarations, and reads **only fenced code blocks**:
  a number in a command a reader can run is a claim, a number in prose is
  commentary. `CHANGELOG.md` is exempt on purpose — a historical entry records
  what was true at that release, so re-counting it would punish honest history.
- `UNMAPPED_CLAIM_SURFACE` (WARN, opt-in via `--artifact-map`) — requires
  `README.md`, `README.zh-CN.md` and `CHANGELOG.md` to be mapped by the
  **newest** id in `artifacts.json`. "Mapped anywhere" was not enough: these
  files were still listed in the v0.1.0 maps, so a weaker check would have
  stayed green for the entire drift, because the file was mapped — just never
  by a round recent enough to be reading today's text.
- Install instructions, a CI workflow example, and a copy-pasteable reviewer
  instruction to both READMEs, and the instruction to `templates/REVIEW.md`.
- `.github/workflows/gate.yml`.
- `CHANGELOG.md` — 0.1.1 through 0.1.3, which were shipped but never recorded.
- `.tasks/XJ-20260930-006.md`; the consumed `XJ-20260930-005` card archived.

### Notes

- The 004/005 artifact maps were **not** edited to include the READMEs. Adding a
  file to a map that predates the change would assert that a reviewer read a
  document that did not exist in its current form. The maps are evidence; the
  correction is a new map on a new card, signed by a new reviewer.
- Three defects were found in the new rules *by the new rules' own tests* while
  writing them: a `break` outside its `if` left the Chinese pattern unreachable;
  a `top_level_dir` argument made discovery refuse to import a non-package
  `tests/` directory; and the first draft scanned all prose, so it flagged the
  paragraph documenting the very fix. All three are recorded because a rule that
  was never itself tested would be no better than the prose it replaced — and
  the third is the reminder that a linter which cries wolf on its own
  documentation is one people learn to ignore.
- A `tools/test_gate.py` step was added to the CI workflow and both READMEs
  before checking that the file exists. It does not; the gate self-test lives in
  `tests/test_gate.py` and already runs under unittest discovery. The phantom
  step was removed rather than left as a CI failure waiting to happen.
  **This line is the false claim that got this round a FAIL.** The step was
  removed from `README.md` and from the workflow, and survived in
  `README.zh-CN.md`; the independent review found it. The wording is left
  unedited on purpose — the FAIL verdict is the evidence, and tidying the
  sentence would repeat the failure it describes. See [PM-11](postmortems.md).
- Consequently `XJ-20260930-005` is now STALE for the files it maps. That is the
  expected outcome of a freshness check that works, not a regression.

## [0.1.3] — 2026-09-30

Maintenance round driven by the round-3 review, and by three of my own errors.

### Fixed

- `BARE_TASK_NAME` produced a false positive: quoting `TASK-002` in prose (as
  the postmortems do) is history, not an instruction. Now scoped to handover
  sections.
- **My own instruction produced the violation it was meant to prevent.** I told
  the reviewer to timestamp its verdict "conservatively early", reasoning that
  early stamps only expire sooner. It stamped 07:47Z; the files it had just
  reviewed were modified 07:53–07:59Z, so the strong gate reported STALE ×4 —
  a verdict dated before the artifacts it judges. `PROTOCOL.md` §4.5 now states
  the constraint correctly: **newest reviewed mtime ≤ ts ≤ now**. Recorded as
  PM-9: *guidance direction can defeat your own check*.
- My round-3 claim that the linter would report 0 errors was wrong; it reported
  4. Fixed by fixing the repository, not by editing the claim's evidence.

### Added

- `.tasks/legacy/` — archived cards are paired with their verdicts but no longer
  linted. Linting the past would force edits to evidence.
- `ORPHAN_VERDICT` promoted to the L2-mandatory list.

### Notes

- 68 tests. The 004/005 maps omitted the READMEs, which is the gap
  `UNMAPPED_CLAIM_SURFACE` later closed in 0.1.4.

## [0.1.2] — 2026-09-30

Maintenance round from the round-2 independent review (`XJ-20260929-002`, PASS).

### Fixed

- **PM-5 corrected an over-claim in the catalogue itself.** The postmortem said
  lost-update conflicts are "not enforced by a tool", but the planning-stage half
  has been lintable since v0.1.1 (`OWNED_FILES_CONFLICT`). Now it says what is
  true: the write-time race is not lintable, the planning-stage declaration is.
  The catalogue was committing the very defect class it documents.
- PM-9 occurrence log: round 1 arrived 8h in the future (reviewer timezone),
  round 2 arrived 9 minutes in the future (rounded to the half hour). Two rounds,
  the same rule firing twice — the habit looks systematic.

### Added

- `REVIEW-REQUEST-*.md` is exempt from the review-card rules. A request is a
  hand-over document and carries no verdict by definition, so requiring one made
  every well-formed request non-conformant — a false positive that trains people
  to ignore the linter. The namespace and path rules still apply.
- Per-conformance-level severity guidance in `docs/lint-rules.md`. Under
  `--strict` every WARN becomes an ERROR, so the WARN/ERROR distinction is
  deployment-dependent and must be stated as such.

### Notes

- 64 tests (+3 for the exemption).
- This round edited files inside `XJ-20260929-002`'s artifact map, so that
  verdict went stale and could not sign v0.1.2. Stated in the commit rather than
  discovered later — the round that invalidates the previous verdict is normal
  operation, not an incident.

## [0.1.1] — 2026-09-30

Closed the three conditions of the first external review (CONDITIONAL, 0
blockers), and found two more defects while handling it.

### Fixed

- **The spec exceeded the code.** `PROTOCOL.md` §6.6 claimed the gate enforced
  six policy points; `gate.py` implemented five. Demoted the unimplementable
  one to advisory, with `ADR-0001.md` recording the decision and its
  revisit-trigger. A spec that overstates its own enforcement is the same
  failure this project exists to catch, one level up.
- **A verdict could be dated in the future**, which made the freshness check
  permanently vacuous for that verdict. Found by handling the review: the
  reviewer's `ts` was eight hours ahead. `FUTURE_VERDICT` now blocks it, and
  `--max-clock-skew` exists.
- **`evidence: ["x"]` passed.** An opt-in `--evidence-must-match` floor was
  added.
- Third-party star counts in both READMEs had no provenance. Every number now
  carries a date and a source link.

### Added

- `OWNED_FILES_CONFLICT` — the planning-stage half of PM-5, which our own
  postmortem had wrongly written off as not statically checkable. The external
  reviewer pointed at the sentence that made that claim.
- PM-9 (future-dated verdicts); PM-3 gains the evidence-quality vector.

### Notes

- 13 new cases (7 gate, 6 linter). The round-2 verdict (`XJ-20260929-002`,
  PASS) then arrived, and v0.1.1 was the first state this repository published
  as **gated**.

## [0.1.0] — 2026-09-29

First public draft. The claim we are making is deliberately narrow: this is a
**spec plus two dependency-free checkers**, and it has been exercised on one real
pilot run, not a fleet.

### Added

- `PROTOCOL.md` — normative spec: roles and trust model (R1–R3), four artifact
  schemas, the machine-readable verdict contract, executable-acceptance rule,
  namespaced card ids (N1/N2), cleanup/TTL rule, and L0/L1/L2 conformance levels.
- `postmortems.md` — eight named failure modes mapped to rules and checks,
  including two from our own runs: a task-id collision that produced a confident
  review of the wrong artifact, and a verifier that crashed on hostile input
  instead of reporting a finding.
- `tools/gate.py` — verdict gate. Stdlib only. Exit `0` pass / `1` violation /
  `2` usage error. Enforces independence, zero blockers, evidence presence, and
  the staleness check (`STALE_VERDICT`: a verdict older than its artifact blocks).
- `tools/lint_cards.py` — card linter. Stdlib only. Enforces namespaced ids and
  path-based handovers, plus review/task schema and verdict-pairing rules.
- `tests/` — 45 unittest cases covering both tools, including the exit-code
  contract and the staleness path.
- `templates/` — `TASK`, `REVIEW`, `HANDOFF`, `ADR`, and a commented
  `verdict.json` with a conditional-pass example.
- `adapters/` — `claude-code/`, `codex/`, `opencode/`: per-harness integration
  notes, each explicitly marking version-dependent details as "verify".
- `docs/lint-rules.md` — per-rule rationale, including what is *not*
  machine-checkable and should live in an ADR instead.
- `examples/deepfreeze-pilot/` — one real, messy pilot run end to end: the task
  card, an adversarial review, the reply, and the gate output.

### Notes

- v0.1 is **spec-first**. The tools are real and tested, but the protocol has not
  been validated at scale; treat conformance claims sceptically and see
  `PROTOCOL.md` §10 for the honest limitations.
- No dependencies on purpose: `gate.py` and `lint_cards.py` must run anywhere
  Python does, including a locked-down CI image.
