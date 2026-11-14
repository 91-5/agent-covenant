# Historical review records (archived 2026-11-14)

This directory holds the **review records** (`REVIEW-<card-id>.md`) that were kept directly under
`.tasks/` from 2026-09-30 to 2026-10-28. They were moved here during a repository tidiness pass
(L2 cleanup) so that `.tasks/` contains only live cards plus the `legacy/` archive.

## Why this directory exists

`.tasks/` had accumulated 36 review records alongside the live-card archive, which made it hard to
tell "what is a card" from "what is a review of a card". The move is a **relocation, not a
reclassification**: every file here is a review record of a card that has long since been CLOSED
and archived under `.tasks/legacy/`.

## Known consequence: some in-card pointers now dangle

Several archived cards under `.tasks/legacy/` still contain pointers of the form
`.tasks/REVIEW-<card-id>.md`. Those pointers were **not** rewritten, because archived cards are
kept verbatim (changing them would invalidate the verdict freshness chain, and the pointers are
part of the historical record). To follow one of those pointers, substitute:

```
.tasks/REVIEW-<card-id>.md   ->   .tasks/legacy/reviews/REVIEW-<card-id>.md
```

Affected cards (22 pointer occurrences across the archive):

- `REVIEW-XJ-20261006-001.md`
- `XJ-20260930-008.md`
- `XJ-20260930-009.md`
- `XJ-20260930-011.md` / `-012` / `-013` / `-014` / `-015`
- plus the remainder of the `XJ-20260930-*` / `XJ-20261004-*` / `XJ-20261008-*` series

The affected cards are **historical and closed**; the pointers pointed at records that were already
final when the cards closed, so no live verdict depends on resolving them.

## What was NOT changed

- No card content was edited (only file locations moved via `git mv`)
- No `artifacts.json` entry was touched — none of these 36 files is listed there, so no verdict
  freshness check is affected
- No verdict, review, or ledger file was deleted
- The `verdicts/` machine-readable records are untouched and remain the authoritative index
