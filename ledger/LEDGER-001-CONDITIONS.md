# Ledger note — XJ-20261006-001 review condition

**Round:** XJ-20261006-001 · **Verdict:** PASS, 0 blockers, 1 condition · **Verdict `ts`:** 2026-10-06T09:03:05+00:00
**Verdict file:** `verdicts/XJ-20261006-001.verdict.json` (unamended, as written by the reviewer)
**CWD of every measurement below:** `D:\15812\projects\agent-covenant`

**Why this file is in `ledger/` and not `.tasks/`:** same as `LEDGER-015-CONDITIONS.md` — a note
is not a round, and N1 would read any `.tasks/*.md` as a task card. Follows that precedent.

---

## What the condition asked, and this note delivers

The card's honest-gap-2 claimed:

> 本仓现有数据无此形态（001/002/004 全带前缀），此风险未实测。

**That claim is false, and I verified the reviewer's census before writing this note** (2026-10-06,
in-memory `re.match(r'^\s*([A-Za-z]+\d+)', cond)` over every conditions list in `verdicts/`):

| Verdict | Conditions | Prefixed? |
|---|---|---|
| `XJ-20260929-001` | 3 | **No** — free text, e.g. `Fix spec-implementation mismatch: PROTOCOL.md §6.6 claims …` |
| `XJ-20260930-015` | 2 | **No** — free text, e.g. `Card 'Baseline to hold' states …` |
| `XJ-20261003-001` / `-002` / `XJ-20261004-004` | 1/1/3 | Yes — `C1`, `C1`, `C1/C2/C3` |

**Where the census in the card's Context went wrong:** it enumerated the cards in the
`XJ-20261003`/`XJ-20261004` families only — the ones this session had been working with — and
generalised "all" from a sample that excluded the two oldest verdicts in the directory. The
claim was written as a census ("全带前缀") and executed as a spot check. That is the
unverified-claim defect class the reviewer named it as, the same class `XJ-20260930-015`'s
conditions recorded.

**Code behaviour is unaffected** (also re-verified): no `unblocks` reference targets either
prefixless verdict, and the prefixless path degrades to the honest `no id prefixes` WARN —
the reviewer's case X6 exercised exactly this and it reports rather than guesses.

## Correction to the card text

`.tasks/XJ-20261006-001.md`, honest-gap-2, should read with this note: the risk of
prefixless conditions is **not** hypothetical — it is the actual shape of 5 of the 10
condition entries in this repository, all in pre-October verdicts. The card is not edited
(no-retrofit: the card is the reviewer's reference, and the condition asked for a ledger
note, not a card mutation).
