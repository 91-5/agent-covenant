# REVIEW <NS>-YYYYMMDD-NNN: <artifact under review>

- **Reviewer:** <agent/human id> — must not be the author (R1)
- **Reviewed at:** <ISO-8601, UTC, e.g. 2026-09-29T20:31:00Z>
- **Author:** <id>

## Verdict

<!-- EXACTLY ONE TOKEN. The linter looks for it; the gate reads the JSON twin. -->

`PASS`

## Blockers

<!-- Count first, then list. PASS requires 0. -->

0

- _none_

## Conditions

<!-- Required non-empty when verdict is CONDITIONAL and blockers > 0. -->

_Not applicable (verdict is PASS)._

## Evidence

<!-- Every Acceptance bullet from the task card maps to a line here (§5, rule A1).
     Commands with their exit codes, counts, file paths — not adjectives. -->

| Acceptance criterion | How verified | Result |
|---|---|---|
| `unittest` exits 0 | `python -m unittest discover -s tests` | 45 passed, exit 0 |
| gate exits 0 | `python tools/gate.py --verdict-dir verdicts` | `GATE: PASS`, exit 0 |

## Independence

<!-- true only if you did not author the artifact under review. -->

`true`

## Machine-readable twin

This verdict is only real once written. Copy `templates/verdict.json`, fill it in,
and save it as `verdicts/<NS>-YYYYMMDD-NNN.verdict.json`. Then:

```bash
python tools/gate.py --verdict-dir verdicts --require <NS>-YYYYMMDD-NNN
```

`CONDITIONAL` additionally requires `--allow-conditional` **and** a non-empty
`acknowledged_by` — a conditional pass that nobody signed for is not a pass.
