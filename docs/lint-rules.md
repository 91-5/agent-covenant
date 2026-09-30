# Lint rules — rationale

Every rule answers three questions: what it forbids, what actually broke, and can
a tool actually catch it. Rules marked "not machine-checkable" are organisational
and belong in your ADRs, not in a linter.

Run: `python tools/lint_cards.py --dir .tasks`

With the artifact map (what the gate runs, and the only way the last rule is
enabled):

    python tools/lint_cards.py --dir .tasks --verdict-dir verdicts --artifact-map artifacts.json

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
| `OWNED_FILES_CONFLICT` | WARN | R2 | Two **active** cards claiming the same path is the planning-stage form of the lost-update hazard (postmortems §PM-5). A directory claim owns everything beneath it; glob claims are compared on their literal prefix. Raised by our first external reviewer, who pointed out that we had written "not statically checkable" in the postmortem when the planning-stage half *is* checkable. | Give each card disjoint ownership, or close the finished one. |
| `NON_ASCII_FILENAME` | WARN | — | Non-ASCII filenames break tooling across platforms (our own experience: legacy-codepage shells and CI). Real risk, not hypothetical. | Transliterate or accept the warning. |
| `STALE_TEST_COUNT` | ERROR | — | This repository shipped a README claiming **45 tests while the suite held 69**, and no rule read prose. The claim surface is part of the deliverable: a reader who trusts a stale number is misled as surely as a machine is by a bad verdict. ERROR, because the protocol is being asserted falsely about itself. `CHANGELOG.md` is deliberately exempt — a historical entry records what was true at that release, so re-counting it would punish honest history. | Update the number, or delete it. A count nobody re-checks is a liability. |
| `UNMAPPED_CLAIM_SURFACE` | WARN | §8 | The claim surface is still listed in the v0.1.0 maps, so a "is it mapped anywhere" check would have stayed green the whole time the drift lasted: the file *was* mapped, just never by a round recent enough to be reading today's text. Round 3 and round 4 maps both omitted the READMEs, and three false claims shipped. The rule therefore compares against the **newest** id, which is the only comparison that catches the real gap. WARN, and off unless `--artifact-map` is passed — the rule has no baseline of its own, and a rule that invents one would be a rule you could not trust. | List the file under the newest id in `artifacts.json`. |

## Deliberate exemptions

| Pattern | Exempt from | Why |
|---|---|---|
| `REVIEW-REQUEST-*.md` | the review-card rules (`REVIEW_MISSING_VERDICT_LINE`, `REVIEW_MISSING_BLOCKERS`) | A request is a hand-over document: it asks someone to produce a verdict, so it has none by definition. Requiring one would make every well-formed request non-conformant. The namespace rule still applies. |
| `HANDOFF-*.md`, `ADR-*.md` | the namespace rule | Their identity is their prefix; a date-suffixed id adds nothing. |
| `<dir>/legacy/**` | everything | Historical evidence, kept verbatim and deliberately not linted. Linting the past would force edits to evidence, which is the behaviour this project exists to prevent. |


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

**Which WARNs matter at L2.** Under `--strict` every WARN becomes an ERROR, so
the distinction is deployment-dependent by design. For teams running the gate in
CI with nobody reading the output, these are the ones to treat as mandatory:

- `OWNED_FILES_CONFLICT` — it guards against data loss (two agents owning one
  file), not against style. At L2 **this should be an ERROR**; run `--strict`.
- `VERDICT_WITHOUT_REVIEW` — a task marked done with no verdict file is the
  §PM-2 failure in miniature.
- `ORPHAN_VERDICT` — a verdict with no card is a broken evidence chain: somebody
  signed something, and the thing they signed no longer exists in the record.
  At L2 **this should be an ERROR**; run `--strict`.
- `UNMAPPED_CLAIM_SURFACE` — a file nobody re-checks is a file that will drift,
  and we have already published a drifted one. At L2 **this should be an ERROR**;
  run `--strict` so the omission cannot pass unnoticed.

The rest (`TASK_MISSING_*`, `CLOSED_NOT_ARCHIVED`, `NON_ASCII_FILENAME`) are
hygiene and can stay advisory at L2 without misleading a machine.
