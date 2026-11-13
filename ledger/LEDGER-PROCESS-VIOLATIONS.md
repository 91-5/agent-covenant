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

## How to use
When Jarvis or any implementer merges without a verdict on file:
1. Do not proceed any further merges in the same batch.
2. Open this ledger, add an entry with: card id, PR, timestamp, claimed basis, CI state, reviewer verdict outcome (or "pending").
3. Decide revert / fix-forward with sir + AgnesCode per AGENTS.md §4.2.8.
