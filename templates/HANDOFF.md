# HANDOFF <NS>-YYYYMMDD-NNN

> **Hard limit: one page.** A handoff that needs a scroll is a handoff nobody
> reads. Link out; do not inline.

- **From:** <agent id> · **To:** <agent id> · **At:** <ISO-8601 UTC>

## Done

- <what is finished> — with an **evidence path or verdict id**, not a claim.
  - ✅ `verdicts/AC-20260929-001.verdict.json` → PASS, 45/45 tests
  - ✅ `src/pipeline.py:88-134`

## Decisions

- <decision> → see `ADR-0007.md`
  *(If a decision has no reversal condition, it is debt. Write the trigger.)*

## Open

- <what is unfinished, and who owns it now>
- <known-broken thing, with the workaround being used meanwhile>

## Risks

- <what could bite during the next work session> — and the early-warning sign
- <assumption that was never verified>

## Next single action

**One** action, owned by **one** agent, verifiable when done:

> `python tools/gate.py --verdict-dir verdicts --require AC-20260929-002`

Do not write "continue the work". The next agent is not you.
