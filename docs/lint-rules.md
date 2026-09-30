# Lint rules — rationale

Every rule answers three questions: what it forbids, what actually broke, and can
a tool actually catch it. Rules marked "not machine-checkable" are organisational
and belong in your ADRs, not in a linter.

Run: `python tools/lint_cards.py --dir .tasks`

| Rule | Level | Clause | Why it exists | Fix |
|---|---|---|---|---|
| `NAMESPACE_MISSING` | ERROR | N1 (§7) | A card named `TASK-002.md` collided with a second agent's internal `TASK-002`. The reviewer produced a confident, detailed verdict about the wrong artifact and **nothing errored** (postmortems §PM-1). | Rename to `<NS>-YYYYMMDD-NNN.md`. |
| `BARE_TASK_NAME` | ERROR | N2 (§7) | Handing over "TASK-002" instead of a path lets the receiver resolve it against its own context. Same root cause as above, different moment — the trigger, not the filename. | Reference the absolute path: `D:\work\.tasks\TASK-002.md`. |
| `REVIEW_MISSING_VERDICT_LINE` | ERROR | §4.2 | A review without a machine-readable `PASS`/`CONDITIONAL`/`FAIL` token cannot gate anything. Most agent "reviews" in the wild are prose; prose is not checkable. | Add a `## Verdict` section with one token. |
| `REVIEW_MISSING_BLOCKERS` | ERROR | §4.2 | "0 blockers" is information. Silence is ambiguous — it might mean zero, or it might mean the reviewer never counted. | Add `## Blockers` with the count first. |
| `TASK_MISSING_SECTION` | WARN | §4.1 | Skipping `Acceptance` means the reviewer has nothing executable to verify, so the verdict degrades to opinion. WARN not ERROR: a two-line card is sometimes the right size. | Fill the section or accept the warning knowingly. |
| `TASK_MISSING_REVIEW_QUESTIONS` | WARN | §4.1 | "Review this" invites rubber-stamping. Adversarial questions ("what input breaks this?") are what convert a review into a review. | Add `## Review questions`. |
| `ORPHAN_VERDICT` | WARN | §8 | A verdict with no card means the evidence trail is broken: nobody can reconstruct what was judged. | Delete the verdict or restore the card. |
| `VERDICT_WITHOUT_REVIEW` | WARN | §6 | A task marked done with no verdict file is the PM-2 failure in miniature: the claim exists, the evidence doesn't. | Produce the verdict, or downgrade the status. |
| `CLOSED_NOT_ARCHIVED` | WARN | §8 | Card directories become unsearchable attics; agents re-read stale cards instead of thinking. A card that reached `GATED` and is still there is TTL debt. | Archive or delete within one working day. |
| `NON_ASCII_FILENAME` | WARN | — | Non-ASCII filenames break tooling across platforms (our own experience: legacy-codepage shells and CI). Real risk, not hypothetical. | Transliterate or accept the warning. |

## Not machine-checkable

These belong in your constitution and ADRs, not in a linter:

- **R2 single write ownership** — two agents owning one file causes lost updates
  that no test or diff can catch; the file looks fine (postmortems §PM-5).
- **Independence in spirit** — the gate reads `independent: true` as a field. It
  cannot verify the reviewer was actually independent. That is the ceiling, and
  we say so in PROTOCOL.md §10.3.
- **Reviewer quality** — a lazy reviewer produces a green verdict with plausible
  evidence strings. No static check separates a real review from a confident one.

## Severity philosophy

ERROR means "the protocol cannot be evaluated here" — a machine reading this
directory would be misled. WARN means "this smells" and a human may have a good
reason. `--strict` promotes warnings to errors for teams that want a clean board.
