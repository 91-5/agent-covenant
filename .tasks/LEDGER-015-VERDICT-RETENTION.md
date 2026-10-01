# Ledger note — 015 verdict retention, and the contradiction it creates

**Round:** 015 · **Verdict:** PASS, 0 blockers, 2 conditions · **Verdict `ts`:** 2026-10-01T11:03:34.304331Z
**Committed at:** `dbc55b4` (verdict + `LEDGER-015-CONDITIONS.md`), retained byte-for-byte
**CWD of every measurement below:** `D:\15812\projects\agent-covenant`

## What was decided

After `dbc55b4` pushed the signed verdict, the reviewer produced `.tasks/REVIEW-XJ-20260930-015.md`
and simultaneously edited two evidence lines inside `verdicts/XJ-20260930-015.verdict.json`:

1. added `8 SUPERSEDED advisories lost` to the T1→T2 line (a figure that had been omitted), and
2. replaced "Post-verdict lifecycle check **on the real tree**" with an admission that the run was
   performed on mtime-preserving `copy2` snapshots, not the real tree, deferring the real-tree
   confirmation to a later round.

The author's instruction was to keep the verdict exactly as signed (**option A**). `git checkout
HEAD -- verdicts/XJ-20260930-015.verdict.json` was executed; the file is byte-identical to the
`dbc55b4` version and its `ts` is unchanged. **The amendment was discarded, not applied.**

The reasoning, recorded because the discarded edit was not dishonest: the amendment was a
voluntary correction of an overstated claim, and correcting it was the right instinct. It was still
rejected on process. `ts` is the verdict's signature; changing content while keeping `ts` signs new
text with an old signature, and 013's precedent is that a verdict on disk is evidence rather than
draft. The correction belongs in a card or a ledger note, both of which are append-only.

## The contradiction this leaves on disk

Two committed records now disagree, on two points:

| | `.tasks/LEDGER-015-CONDITIONS.md` (`dbc55b4`) | `.tasks/REVIEW-XJ-20260930-015.md` §"Reviewer disclosure" |
|---|---|---|
| Was the verdict's evidence amended? | **No** — retained byte-for-byte | "The verdict file's evidence line was amended" |
| Has the real-tree run happened? | **Yes** — `LINT: PASS (1 warnings)`, 0 `UNMAPPED_CLAIM_SURFACE` | "remains a follow-up for the next round" |

Both statements are the reviewer's or the author's, and each was true at the moment it was written.
Neither is retracted by this note; both stand as written, and the disagreement is recorded here
rather than resolved by editing either document.

What is actually true on disk, for the avoidance of doubt:

- The verdict file at `dbc55b4` **contains the overstated real-tree claim**, unmodified. §156's
  admission describes a version of the file that does not exist in the repository.
- The real-tree run **was performed**, before `dbc55b4` was committed:

  ```
  python tools/lint_cards.py --dir .tasks --verdict-dir verdicts
  -> [WARN] VERDICT_WITHOUT_REVIEW XJ-20260930-010.md: card has no machine-readable verdict file
     LINT: PASS (1 warnings)
  ```

  **Zero `UNMAPPED_CLAIM_SURFACE` findings.** The 015 PASS at `11:03:34.304331Z` post-dates every
  mtime in the map entry (max `2026-10-01T09:28:03.395213Z`), so the rule goes quiet on a real
  landing. The single remaining warning concerns round 010 and predates this round.
- Therefore the behaviour the verdict over-claims is true; only its attribution to a real-tree run
  was unsupported when written, and is now supported by the run above.

## Why option A was still right

Option B (apply the amendment and re-note) and option C (re-issue under a new `ts`) both create a
larger integrity problem than the one they fix. B means the verdict's content and its stated
amendment history disagree unless every reader also reads this note; C breaks the timestamp relation
the gate reasons about, which is the same mtime trap `PROTOCOL.md §10` item 7 warns about. A keeps
the signature honest and lets the disagreement be visible instead of reconciled away.

The cost of A is that the ledger ships with an overstated line in a signed verdict and a card that
describes a file state that never existed. That cost is real and is the point: it is what a ledger
that refuses to edit evidence looks like when the evidence needs editing.

## Carried to 016

This is the fourth instance in one round of the same failure mode — a figure asserted without
execution, or evidence claimed without the run behind it (the card's "six", the card's "seven
files", the request's first-draft reproduction command, and this verdict's real-tree line). Three
were caught before publishing. This one shipped inside a signed verdict and was caught after.

`PROTOCOL.md §10` item 7's three-coordinate rule (commit, command, CWD) is necessary but, as §156
demonstrates, **unenforced**: nothing detected either the card's bare "six"/"seven" or the verdict's
unsupported attribution. §9 of the review card proposes a lint rule over numeric claims in ledger
documents lacking a coordinate. That proposal is recorded, not adopted. This note is the supporting
evidence for treating it as more than an option.