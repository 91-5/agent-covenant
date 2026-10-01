# Ledger note — 015 review conditions

**Round:** 015 · **Verdict:** PASS, 0 blockers, 2 conditions · **Verdict `ts`:** 2026-10-01T11:03:34.304331Z
**Verdict file:** `verdicts/XJ-20260930-015.verdict.json` (unamended, as written by the reviewer)
**CWD of every measurement below:** `D:\15812\projects\agent-covenant`

**Why this file is in `ledger/` and not `.tasks/`:** a note is not a round. `PROTOCOL.md` rule N1
requires every `.tasks/*.md` filename to be `<NS>-YYYYMMDD-NNN.md`, and `tools/lint_cards.py`
derives a round's identity from that filename — so any note inside `.tasks/` is read as a task card
and judged against the task-card schema. These notes were first written as `LEDGER-*.md`, which the
linter rejected with `NAMESPACE_MISSING` (2 errors); renaming them to `XJ-20261001-001/002.md` to
satisfy N1 traded those 2 errors for 14 warnings (`VERDICT_WITHOUT_REVIEW`,
`TASK_MISSING_SECTION`, `TASK_MISSING_REVIEW_QUESTIONS`) because the renamed id *is* a round. Neither
name can satisfy the rule, because the rule has no category for a note. `check_verdict_pairs` and the
card scan both read `--dir` non-recursively, so a sibling directory needs no code change. The gap is
recorded for 016: the project has no note category, and `PROTOCOL.md` §11's layout does not say where
one belongs.

This note exists instead of edits to `.tasks/XJ-20260930-015.md`. The card is the eighth entry in
015's own artifact map, and its mtime (`2026-10-01T10:56:06.826640Z`) currently sits *before* this
round's verdict `ts`. Editing it would push its mtime past `ts` and make the card a
`STALE_VERDICT` against the very verdict that passed it — the rule 015 just installed would fire on
015's own paperwork. The reviewer's instruction to "correct it in a ledger note" is therefore the
only path that does not manufacture a new finding.

## Condition 1 — "six" should be eight (confirmed)

`.tasks/XJ-20260930-015.md:133` reads:

> The six `SUPERSEDED` advisories those rounds lose is the same effect seen from the other side.

Measured, at the two states the card itself defines (T1 and T2):

| | checked | violations | advisories |
|---|---|---|---|
| T1 — `d5410f0`-era mtimes | 12 | 25 | **37** |
| T2 — the two lint files pushed past every verdict | 12 | 35 | **29** |

37 → 29 retires **eight** advisories, not six. The reviewer independently reached the same pair.
The ten added violations quoted in the same paragraph are exact.

## Condition 2 — "seven files" should be eight (confirmed)

`.tasks/XJ-20260930-015.md:181` reads `git diff HEAD~1 --stat` shows "the seven files above".
`git diff --name-only d5410f0 d16f080` lists **8**:

```
.tasks/XJ-20260930-015.md   CHANGELOG.md   README.md   README.zh-CN.md
artifacts.json   docs/lint-rules.md   tests/test_lint_cards.py   tools/lint_cards.py
```

The deliverables list has 8 entries; `docs/lint-rules.md` is the one the count missed. The
"Baseline to hold" invariant — findings may move only in ways attributable to files this round
edited — is the accurate statement, and it holds exactly: the T2 → HEAD diff is +25 `STALE_VERDICT`
and −20 `SUPERSEDED`, every one naming only `README.md`, `README.zh-CN.md` or
`docs/lint-rules.md`. The acceptance bullet's narrower enumeration ("the two lint files") was written
for the intermediate T2 state and is the weaker claim.

## Neither is a behaviour defect

Both conditions are of the project's recurring class: a figure asserted in prose and never run.
Neither touches `tools/lint_cards.py`, whose rule is unchanged since `d16f080`. This note records
them; it does not amend the card, and the card stays on disk as the round wrote it.

## Third correction — the verdict's own evidence wording, resolved by re-running

The reviewer's evidence line reads "Post-verdict lifecycle check **on the real tree**". The execution
that produced that figure was a `copy2` snapshot preserving mtimes, and the reviewer flagged the
wording as stronger than the work performed. The verdict file is not amended — it is the reviewer's
signed document, and 013's precedent is that verdicts are evidence, not draft.

Instead, the claim has been run as written, on the real tree, after this verdict landed:

```
python tools/lint_cards.py --dir .tasks --verdict-dir verdicts
-> [WARN] VERDICT_WITHOUT_REVIEW XJ-20260930-010.md: card has no machine-readable verdict file
   LINT: PASS (1 warnings)
```

**Zero `UNMAPPED_CLAIM_SURFACE` findings.** The rule goes quiet on a real PASS landing — the
behaviour 015 claims, on the tree the card names, not on a stand-in. The one remaining warning is
unrelated to 015 (010 has a card and no verdict file, predating this round). So the wording is now
accurate, though it was overstated when written.

## Carried to 016

The reviewer's Judgement 4 identifies the asymmetry that outlives 015: `tools/lint_cards.py` now
demands a fresh PASS signature, while `tools/gate.py`'s untouched `_superseded_by` (L250-266) still
accepts *any-status* fresh successor as the current authority. The coercion that manufactured such
entries is gone; the gate-side channel is what the deferred `edited`/`reviewed` split must close.
Recorded here so the deferral carries its reason forward rather than becoming an unexplained gap.