# Lint rules — rationale

Every rule answers three questions: what it forbids, what actually broke, and can
a tool actually catch it. Rules marked "not machine-checkable" are organisational
and belong in your ADRs, not in a linter.

Run: `python tools/lint_cards.py --dir .tasks`

With the artifact map. `--artifact-map` may be omitted when `artifacts.json`
sits next to `.tasks/`, in which case it is picked up automatically:

    python tools/lint_cards.py --dir .tasks --verdict-dir verdicts --artifact-map artifacts.json
    python tools/lint_cards.py --dir .tasks          # same, if ./artifacts.json exists

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
| `STALE_TEST_COUNT` | ERROR | — | This repository shipped a README claiming **45 tests while the suite held 69**, and no rule read prose. ERROR on these grounds: *this number is the project making a claim about its own deliverable*, and the protocol's entire subject is claims about deliverables that nothing re-checks. That is the one lie a verification protocol cannot afford to be relaxed about — not the author's embarrassment at the number, which is not an argument. A count that drifts 45 → 69 → 82 → 84 across four releases is not a cosmetic slip. `CHANGELOG.md` is exempt by design: a historical entry records what was true at that release, so re-counting it would punish honest history. Only fenced code blocks are read — a number in a copy-pasteable command is a claim, a number in prose is commentary. | Update the number, or delete it. A count nobody re-checks is a liability. |
| `TEST_COUNT_UNVERIFIED` | WARN | — | The rule above reads its baseline by importing the test suite, so "I could not run my own check" is a reachable state. Reporting nothing in that state is PM-10 inverted: there a check weakened itself when a flag was forgotten, here a check switches itself off and returns "nothing to compare". This rule shipped with exactly that bug — `top_level_dir` made discovery refuse to import a non-package `tests/`, leaving the rule dead on this very repository until a test caught it. WARN because a broken suite is a problem to report, not a verdict on the README. | Fix the suite's imports, or the discovery call. Silence here means the check is off. |
| `UNMAPPED_CLAIM_SURFACE` | WARN | §8 | The claim surface is still listed in the v0.1.0 maps, so a "is it mapped anywhere" check would have stayed green the whole time the drift lasted: the file *was* mapped, just never by a round recent enough to be reading today's text. Round 3 and round 4 maps both omitted the READMEs, and three false claims shipped. The rule first compared against the **newest** id, on the reasoning that it was the only comparison catching the real gap. Round 013 falsified that reasoning: `current = ids[-1]` *demanded* the listing, so a ledger-only round that never touched the READMEs had to attest to them anyway, and the gate then retired `XJ-20260929-001`'s staleness on that fiction. Round 014 listed the same two files honestly, because 014 had actually edited them — the same rule produced opposite results depending on coincidence. The rule now asks who *holds* the claim instead: some round listing the file must hold a verdict that is **PASS** and signed **at or after the file's mtime**. FAIL holds nothing, and a PASS predating the text holds nothing. Where a project has no verdicts at all there is no signature to read, and the rule degrades to the old newest-id comparison rather than inventing a baseline; that fallback is what keeps the original drift case (`test_mapping_from_an_old_round_does_not_count`) meaningful. `--artifact-map` defaults to `./artifacts.json` when that file exists: a check that only runs when a flag is remembered is a check that will be forgotten, and the flagless invocation is exactly what a cold reader types. | Have a round that actually reads the file sign for it with a PASS verdict, and list it in that round's map. |

## Deliberate exemptions

| Pattern | Exempt from | Why |
|---|---|---|
| `REVIEW-REQUEST-*.md` | the review-card rules (`REVIEW_MISSING_VERDICT_LINE`, `REVIEW_MISSING_BLOCKERS`) | A request is a hand-over document: it asks someone to produce a verdict, so it has none by definition. Requiring one would make every well-formed request non-conformant. |
| `<NS>-REVIEW-REQUEST-<NS2>-<date>-<NNN>.md` | the namespace rule's leading-token requirement | The namespaced request form, and the one to use when a request must survive a shared mailbox. The bare `REVIEW-REQUEST-*` prefix and N1's `<NS>-<date>-<NNN>` pattern cannot both be satisfied by one filename, so a namespaced request previously had to break one of them: drop the namespace (which is the hijack N1 exists to prevent, PM-1) or take an N1 error. `NAMESPACED_REQUEST_RE` accepts the namespaced form *and* classifies it as a request, so the namespace leads and the type survives. Deliberately narrow: the leading token must be a namespace and the name must end in a date-number id, so `DSB-REVIEW-REQUEST-XJ.md` and `REVIEW-REQUEST-whatever.md` still fail. Bare `REVIEW-REQUEST-<NS>-<date>-<NNN>.md` remains non-conformant. |
| `HANDOFF-*.md`, `ADR-*.md` | the namespace rule | Their identity is their prefix; a date-suffixed id adds nothing. |
| `README.md`, `README.<locale>.md` in the card directory | the namespace rule | Directory documentation, not a card. N1's rationale is hijacking (PM-1): a bare `TASK-002` resolved against another agent's context. No agent will mint a card called `README`, so the collision it prevents cannot occur. Observed 2026-10-02 in the deepseek-brain review run — the only way to silence the finding there was to rename the file to something that lied about its type, which then got parsed as a task card and produced four `TASK_MISSING_SECTION` warnings instead. Deliberately narrow: widening this to "any unnamespaced `.md`" would exempt the bare names N1 exists to catch. |
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
- `TEST_COUNT_UNVERIFIED` — under `--strict` a silently disabled check is worse
  than a failing one, because nothing in the output says the rule did not run.

The rest (`TASK_MISSING_*`, `CLOSED_NOT_ARCHIVED`, `NON_ASCII_FILENAME`) are
hygiene and can stay advisory at L2 without misleading a machine.
