# TASK <NS>-YYYYMMDD-NNN: <title>

> ⚠️ Rename this file to `<NS>-YYYYMMDD-NNN.md` before use. A bare `TASK-N.md`
> name can be hijacked by another agent (postmortems.md §PM-1) and will fail
> `lint_cards.py` with `NAMESPACE_MISSING`.
> `<NS>` = your namespace token, 2–6 uppercase letters, unique per author/team.

- **Author:** <agent/human id>
- **Created:** <YYYY-MM-DD>
- **Gated by:** `verdicts/<id>.verdict.json` (see template)

## Context

What exists today, and why this task exists. Link the prior decision record
(`ADR-NNNN.md`) if this work follows one. A reviewer must be able to read only
this section and know why they are being asked.

## Deliverables

- `path/to/file.ext` — what it will contain
- behaviour: <observable change, stated as an outcome not an activity>

## Owned files

<!-- Paths this card exclusively owns while it is active. Two active cards
     claiming the same path is the planning-stage form of the lost-update
     hazard; `lint_cards.py` reports it as OWNED_FILES_CONFLICT. Use one path
     per line. A directory claim owns everything beneath it. -->

- `path/to/exclusive/file.py`

## Constraints

- Files/directories that must NOT be touched
- Interfaces that must not change (compatibility surface)
- Budget: time, tokens, blast radius
- Single write ownership: this task owns <scope> exclusively (R2)

## Acceptance

Every bullet must be machine-checkable (PROTOCOL.md §5). Each line becomes an
evidence string in the verdict.

- [ ] `python -m unittest discover -s tests` exits 0
- [ ] `python tools/gate.py --verdict-dir verdicts --require <id>` exits 0
- [ ] <observable property, e.g. "row count == 21", "no TODO in diff">

## Review questions

Adversarial, not "looks good?". Ask the reviewer to find the thing that is wrong.

1. What input would make this fail that the current tests do not cover?
2. Which of these constraints is load-bearing, and which is cargo cult?
3. If this ships and fails at 3am, what will the operator see?

## Review handoff

Give the reviewer **this exact path** and this exact instruction:

> Read `<absolute-path>/<NS>-YYYYMMDD-NNN.md` in full, then write your verdict to
> `<absolute-path>/REVIEW-<NS>-YYYYMMDD-NNN.md` and a machine-readable
> `<verdicts-dir>/<NS>-YYYYMMDD-NNN.verdict.json`. Do not edit the author's files.

## Status

`OPEN` → `IN_REVIEW` → `GATED` → `CLOSED`

*(On CLOSED/GATED: archive or delete this card within one working day —
PROTOCOL.md §8. `lint_cards.py` warns while a closed card lingers.)*
