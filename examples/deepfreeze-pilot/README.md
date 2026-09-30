# Worked example: the deepfreeze pilot (real run, unedited)

This is a real pilot run, kept as it happened — including the parts that make us
look bad. That is the point of the directory. A worked example that only shows the
happy path teaches nothing.

## What the pilot was

A small PowerShell utility (`deepfreeze.ps1` — protect/restore/status/unprotect
over a directory, robocopy mirror + SHA-256 manifest) built as the first test of a
two-agent division of labour: one agent implements, a different agent reviews, the
author fixes, and an independent checker decides.

- `.tasks/` — the actual cards from that run, verbatim (three files, unmodified)
- `artifacts/` — the two scripts as they stood when the review closed
- `verdicts/` — the machine-readable twins (schema-conformant)
- `artifacts.json` — the id → paths map the gate uses for freshness

## The incident worth reading: `TASK-001.md`

The original card was named `TASK-001.md`. A bare name. It collides with any
other agent's internal `TASK-001` — and it did: a later card in the same project
was silently reviewed against the wrong artifact, producing a confident,
detailed, entirely irrelevant verdict. Nothing errored. See `postmortems.md`
§PM-1 for the full account.

The card in this directory keeps its historical name **on purpose**. It is the
evidence.

## Gate output (real, reproduced)

```bash
# 1) the pre-fix conditional verdict, against artifacts that have since changed
python tools/gate.py --verdict-dir verdicts --require AC-20260929-001 \
  --artifact-map artifacts.json --allow-conditional
```

```
[STALE_VERDICT] AC-20260929-001: artifact artifacts/deepfreeze.ps1 was modified after the verdict was issued (2026-09-29T12:31:51+00:00 > 2026-09-29T05:46:04+00:00)
[STALE_VERDICT] AC-20260929-001: artifact artifacts/verify.ps1 was modified after the verdict was issued (2026-09-29T12:31:51+00:00 > 2026-09-29T05:46:04+00:00)
GATE: FAIL (2 violations across 1 checked)
```

```bash
# 2) the post-fix verdict
python tools/gate.py --verdict-dir verdicts --require AC-20260929-002 \
  --artifact-map artifacts.json
```

```
GATE: PASS (1 checked)
```

Run 1 is the interesting one. The review said "conditional pass". The author then
edited both scripts. The verdict did not change, because nobody re-reviewed — and
the gate says so, loudly, instead of waving a stale review through. This is the
check that teams skip first (PROTOCOL.md §4.5).

> **Reproduction note:** paths inside `artifacts.json` are resolved against your
> current working directory, so run these commands from inside this directory
> (or point `--artifact-map` at paths valid from where you stand). Run from the
> repository root and you will get `ARTIFACT_MISSING` — which is the gate telling
> the truth about a path it cannot see.

## A lesson about the timestamps themselves

The first time we ran this example, run 1 **passed** — and it should not have.
The cause: the verdict timestamps had been written from a local clock and
labelled `Z`. The machine was UTC+8, so a "13:46 local" review was recorded as
"13:46 UTC" and appeared to be *newer* than the artifacts it judged.

A freshness check is only as honest as its clock. If your CI and your agents live
in different timezones, normalise to UTC at the source and be suspicious of any
timestamp that is suspiciously round. Fixed here; the corrected values are in the
verdict files.

## Linter output (real, reproduced)

```bash
python tools/lint_cards.py --dir .tasks --verdict-dir verdicts
```

```
[ERROR] REVIEW_MISSING_BLOCKERS REVIEW-001-REPLY.md: no '## Blockers' section (state the count, even if zero)
[ERROR] REVIEW_MISSING_VERDICT_LINE REVIEW-001.md: '## Verdict' section contains no PASS / CONDITIONAL / FAIL
[ERROR] REVIEW_MISSING_BLOCKERS REVIEW-001.md: no '## Blockers' section (state the count, even if zero)
[ERROR] NAMESPACE_MISSING TASK-001.md: filename must be <NS>-YYYYMMDD-NNN.md (PROTOCOL.md N1); got 'TASK-001.md' — a bare name can be hijacked by another agent
[ERROR] BARE_TASK_NAME TASK-001.md:1: bare TASK-001 reference — hand over the absolute path instead (PROTOCOL.md N2)
[WARN] ORPHAN_VERDICT AC-20260929-001.verdict.json: verdict has no matching card in the card directory
[WARN] ORPHAN_VERDICT AC-20260929-002.verdict.json: verdict has no matching card in the card directory
LINT: FAIL (5 errors, 2 warnings)
```

Read the findings, because every one is a true statement about a real run:

- **`TASK-001.md` is a bare name.** The exact defect of §PM-1, sitting in a
  directory, on disk. (The real project later renamed its cards to
  `XJ-20260929-002.md` and adopted the namespace rule.)
- **The review has no machine-readable verdict token.** The reviewer wrote a
  Chinese "总评: 有条件通过" — perfectly clear to a human, invisible to a gate.
  That is the whole reason the JSON twin exists.
- **No `## Blockers` sections.** "0 blockers" is information; silence is
  ambiguous.
- **The two `ORPHAN_VERDICT` warnings are a packaging artifact of this example,
  not a finding about the pilot:** the historical cards kept their old names
  while the verdicts were written to the new schema's ids. In a live project the
  ids would match.

We did not "fix" the cards to make the linter green. Evidence that has been
tidied is not evidence.

## What this example does not prove

The post-fix `PASS` is the **author's own re-verification** recorded honestly in
the verdict's `_provenance` field. A stronger claim needs a fresh external
reviewer. The gate cannot tell those two cases apart — which is precisely the
ceiling stated in `PROTOCOL.md` §10.3.
