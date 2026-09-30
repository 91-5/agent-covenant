# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [SemVer](https://semver.org/spec/v2.0.0.html).

## [0.1.4] — 2026-09-30 (in review, not yet gated)

Three false claims shipped in the published README, and the gate that had
certified the release never saw them — the defect class this project exists to
prevent, occurring in the project itself. The text is corrected; more
importantly, two rules now make the class checkable.

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
