# Ledger note — XJ-20261006-002 review condition

**Round:** XJ-20261006-002 · **Verdict:** PASS, 0 blockers, 1 condition · **Verdict `ts`:** 2026-10-06T12:20:37+00:00
**Verdict file:** `verdicts/XJ-20261006-002.verdict.json` (unamended, as written by the reviewer)
**CWD of every measurement below:** `D:\15812\projects\agent-covenant`

**Why this file is in `ledger/` and not `.tasks/`:** same as `LEDGER-015-CONDITIONS.md` and
`LEDGER-001-CONDITIONS.md` — a note is not a round, and N1 would read any `.tasks/*.md`
as a task card.

---

## What the condition asked, and this note delivers

CHANGELOG `[0.1.18]` ends with:

> `ADR-0002.md`, `ADR-0001.md` (revisit-trigger item 3 footnote), `PROTOCOL.md` are the
> only files touched.

**Verified false before writing this note** (2026-10-06): `git show 643c321 --stat`
shows exactly 4 files — `ADR-0001.md`, `ADR-0002.md`, `CHANGELOG.md`, `PROTOCOL.md`
(+113/−1). The sentence omits `CHANGELOG.md` itself, i.e. the very file the sentence is
written in. The `[0.1.17]` entry's equivalent sentence lists all of its files; this one
was written sloppily against the same standard the neighbour entry set.

Same defect class as the previous two ledger conditions (`XJ-20260930-015`,
`XJ-20261006-001`): **a completeness claim asserted, not counted**. Third instance of
the class in this repository; the pattern is now formally: *when a changelog entry
says "only X, Y, Z are touched", run `git show <commit> --stat` and diff the two lists
before writing the sentence.*

The changelog entry is **not edited** (no-retrofit: the entry is the historical record
of what the author believed at release time, and the reviewer's condition asked for a
ledger note, not a mutation). This note is the correction of record.

## Colophon fact-check (from the same review, kept for the push commit message)

- The reviewer measured `58fe1ef..HEAD` = **28 commits** where the dispatch said 27;
  the dispatch's number was written before the card-opening commit `f860e8c` landed,
  so both were true at their respective times. Recorded here so the push message uses
  the reviewer's measured count.
- The push gate's two blocking STALE findings resolved independently after her verdict
  landed: `GATE: PASS (6 checked), exit 0` re-run by the author on the required ids.
