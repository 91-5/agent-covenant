# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [SemVer](https://semver.org/spec/v2.0.0.html).

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
