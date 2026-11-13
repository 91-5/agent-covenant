# LEDGER-PROCESS-VIOLATIONS — 4.2.7 process violations (verdict-on-file)

This ledger records violations of AGENTS.md §4.2 item 7/8 (merge without verdict).
A violation is entered regardless of code quality. Code quality outcome is recorded separately.

**Opened:** 2026-11-13 (EVO-20261113-001, verdict-on-file hard gate shipped as AGENTS.md v0.8)
**Maintained by:** Jarvis (OpenCode). Reviewer of record: AgnesCode. Arbitration: sir.

## Entries

### 2026-11-13 · ColdStore P7 (OC-20261113-002) · merged to main without verdict
- **What happened:** PR #3 (commit `adae985`) was merged to main at 2026-11-13T05:50:46Z before the formal machine-readable verdict (`OC-20261113-002-P7.verdict.json`) was on file. Executor-claimed merge basis: sir directive + CI green + independent read-only sub-agent PASS (0 blocking) + non-release-blocker. Executor honestly disclosed in the delivery doc (`OC-20261113-002.delivery.md` §P7.10) and review request §6.
- **Rating:** process violation (4.2.7); code itself: no defect (CI 5/5 green, release binary seam zero hits, B16 zero hits, independent reviewer re-ran build+test: 82/82 PASS; 7 code rulings all accepted/confirmed by AgnesCode).
- **Retroactive review:** `review/agnes/REVIEW-OC-20261113-002-P7.md` — verdict PASS/MERGE ACCEPTED (0 blockers), ts 2026-11-13T06:08Z. Not reverted (merge already completed; scope would be single commit if blocking judged later).
- **Closure:** merged accepted; violation recorded advisory-tier. Root-cause remediation = EVO-20261113-001 (verdict-on-file hard gate, AGENTS.md v0.8, 2026-11-13 GATED by sir). P7 retroactive verdict remains on file; round-1 CONDITIONAL verdict for EVO kept as-is per §6.3 R2.

## Provenance registrations (NOT violations)

This section records merges where the *execution environment was not reproducible from the
commit record* — i.e. the merge gate itself was run from a working-tree version that differed
from the committed version. These are **not** 4.2.7/4.2.8 violations (a PASS verdict was on
file in every case); they are recorded so that a later auditor can answer "which gate version
judged this merge?" without guessing.

### 2026-11-13 · agent-covenant 轮十六 (XJ-20261113-003) · gate script version not traceable from commit history
- **What happened:** merge `385374f` was gated with the **working-tree** version of
  `scripts/verdict_gate.ps1` (file sha256 `b9e12cc903a7…`, git blob `0e597f9`, uncommitted)
  while the committed version was `bb8bd06` (commit `a5088a5`). The verdict
  (`XJ-20261113-003.verdict.json`, PASS, blockers 0) was legitimately on file, so 4.2.8 was
  satisfied; the defect is traceability, not authorization.
- **Why it happened:** an out-of-band edit (PowerShell empty-collection / single-element
  truth-value hardening, 4 insertions / 3 deletions) appeared in the working tree during the
  round; the round's executor did not touch the file and honestly disclosed it (round-16 request
  §6.5, report §6.7). Orchestrator pre-review flagged it; AgnesCode ruled in the round-16 verdict
  (ADV-2) that it must be collected by a dedicated EVO card rather than folded into the round.
- **Mitigation already applied:** merge message for `385374f` carries the actual gate version
  (`sha256 b9e12cc9 (uncommitted hardening; committed blob bb8bd06)`), so this one merge *is*
  answerable from the commit record despite the ledger entry.
- **Root-cause remediation:** EVO-20261114-001 — commit the hardened version, obtain an
  incremental AgnesCode verdict on the script change alone, and add a standing rule that any
  merge whose executed gate version differs from `HEAD` must record the version identifier in
  the merge message. Behavior-equivalence measured: 6/6 truth-table cases identical (the change
  is a no-op for every input shape tested), so no previously-gated merge outcome is affected.
- **Scope note:** the verdict-on-file gate only became effective 2026-11-13 (EVO-20261113-001
  GATED), so the window of possible drift is limited to merges from that date forward.

## How to use
When Jarvis or any implementer merges without a verdict on file:
1. Do not proceed any further merges in the same batch.
2. Open this ledger, add an entry with: card id, PR, timestamp, claimed basis, CI state, reviewer verdict outcome (or "pending").
3. Decide revert / fix-forward with sir + AgnesCode per AGENTS.md §4.2.8.
