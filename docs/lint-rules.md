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
| `ORPHAN_VERDICT` | WARN | §8 | A verdict with no card **anywhere** means the evidence trail is broken: nobody can reconstruct what was judged. Deliberately narrow — a verdict whose card was archived still counts as paired, because `lint_cards.py` reads ids out of `<card-dir>/legacy/` too. Archiving a card must never force a choice between deleting its verdict and keeping a live record; the v0.1.17 §8 correction fixed the clause that said otherwise (see `PROTOCOL.md` §8). | Restore the card (active or under `legacy/`), or delete the verdict of a card that never existed. |
| `VERDICT_WITHOUT_REVIEW` | WARN | §6 | A task marked done with no verdict file is the PM-2 failure in miniature: the claim exists, the evidence doesn't. | Produce the verdict, or downgrade the status. |
| `CLOSED_NOT_ARCHIVED` | WARN | §8 | Card directories become unsearchable attics; agents re-read stale cards instead of thinking. A card that reached `GATED` and is still there is TTL debt. | Archive or delete within one working day. |
| `OWNED_FILES_CONFLICT` | WARN | R2 | Two **active** cards claiming the same path is the planning-stage form of the lost-update hazard (postmortems §PM-5). A directory claim owns everything beneath it; glob claims are compared on their literal prefix. Raised by our first external reviewer, who pointed out that we had written "not statically checkable" in the postmortem when the planning-stage half *is* checkable. | Give each card disjoint ownership, or close the finished one. |
| `NON_ASCII_FILENAME` | WARN | — | Non-ASCII filenames break tooling across platforms (our own experience: legacy-codepage shells and CI). Real risk, not hypothetical. | Transliterate or accept the warning. |
| `STALE_TEST_COUNT` | ERROR | — | This repository shipped a README claiming **45 tests while the suite held 69**, and no rule read prose. ERROR on these grounds: *this number is the project making a claim about its own deliverable*, and the protocol's entire subject is claims about deliverables that nothing re-checks. That is the one lie a verification protocol cannot afford to be relaxed about — not the author's embarrassment at the number, which is not an argument. A count that drifts 45 → 69 → 82 → 84 across four releases is not a cosmetic slip. `CHANGELOG.md` is exempt by design: a historical entry records what was true at that release, so re-counting it would punish honest history. Only fenced code blocks are read — a number in a copy-pasteable command is a claim, a number in prose is commentary. | Update the number, or delete it. A count nobody re-checks is a liability. |
| `TEST_COUNT_UNVERIFIED` | WARN | — | The rule above reads its baseline by importing the test suite, so "I could not run my own check" is a reachable state. Reporting nothing in that state is PM-10 inverted: there a check weakened itself when a flag was forgotten, here a check switches itself off and returns "nothing to compare". This rule shipped with exactly that bug — `top_level_dir` made discovery refuse to import a non-package `tests/`, leaving the rule dead on this very repository until a test caught it. WARN because a broken suite is a problem to report, not a verdict on the README. | Fix the suite's imports, or the discovery call. Silence here means the check is off. |
| `UNMAPPED_CLAIM_SURFACE` | WARN | §8 | The claim surface is still listed in the v0.1.0 maps, so a "is it mapped anywhere" check would have stayed green the whole time the drift lasted: the file *was* mapped, just never by a round recent enough to be reading today's text. Round 3 and round 4 maps both omitted the READMEs, and three false claims shipped. The rule first compared against the **newest** id, on the reasoning that it was the only comparison catching the real gap. Round 013 falsified that reasoning: `current = ids[-1]` *demanded* the listing, so a ledger-only round that never touched the READMEs had to attest to them anyway, and the gate then retired `XJ-20260929-001`'s staleness on that fiction. Round 014 listed the same two files honestly, because 014 had actually edited them — the same rule produced opposite results depending on coincidence. The rule now asks who *holds* the claim instead: some round listing the file must hold a verdict that is **PASS** and signed **at or after the file's mtime**. FAIL holds nothing, and a PASS predating the text holds nothing. Where a project has no verdicts at all there is no signature to read, and the rule degrades to the old newest-id comparison rather than inventing a baseline; that fallback is what keeps the original drift case (`test_mapping_from_an_old_round_does_not_count`) meaningful. `--artifact-map` defaults to `./artifacts.json` when that file exists: a check that only runs when a flag is remembered is a check that will be forgotten, and the flagless invocation is exactly what a cold reader types. | Have a round that actually reads the file sign for it with a PASS verdict, and list it in that round's map. |
| `UNBLOCKS_MALFORMED` | ERROR | §6.3 R1/R2 | `unblocks` carries a resolution reference — the record that a fix discharged an earlier card's condition (`ADR-0002`). A malformed one is a broken pointer in the audit trail. Deliberately checks **shape and self-reference only**: condition ids are free-text prefixes in practice (`"C1: …"`, but also `"C1 (B1, from Q2): …"`), so verifying that the referenced condition *exists* would mean parsing prose. Existence is `ADR-0002`'s revisit-trigger item 2, not this rule. | Use `"<card-id>.<condition-id>"`, e.g. `"XJ-20261004-004.C1"`. Never reference your own id. |
| `SELF_SIGNED` | ERROR | §6.3 R3 | A verdict whose `verifier` is the author of the reviewed artifact carries `self_signed: true`. Lint has no `--allow-nonindependent` flag, so it is strict here by design; the gate can admit a *declared* self-sign, which is the point of the flag. The rule reports the contradiction (`self_signed: true` **and** `independent: true`) separately, because that combination is the one this field exists to make impossible. | Set `independent: false` alongside, or drop `self_signed` if the review really was independent. |
| `DUPLICATE_UNBLOCKS` | WARN | §6.3 | Two or more verdicts claiming the same resolution reference. `ADR-0002` §6.3 records this as a **known, unarbitrated hazard** — nothing says which claimant actually closed the condition, and two is not exotic: a fix card plus a re-check card is a normal shape. WARN deliberately, because raising it to ERROR before arbitration exists would block legitimate pairs. | Confirm which round closed the condition; the deferral is recorded in `ADR-0002` revisit-trigger item 3. |
| `UNBLOCKS_DANGLING` | WARN | §6.3 R1 | An `unblocks` reference names a condition that cannot be found: either the referenced card has no verdict on disk (existence *undecidable*, not disproved — that card may still be queued for review, a state `VERDICT_WITHOUT_REVIEW` already reports), or its conditions do not open with the referenced id. This is `ADR-0002` revisit-trigger item 2 made checkable: before this rule, an `unblocks` could point at a condition that never existed and only the *shape* was checked. WARN on three grounds: undecidable is not false; condition ids are a **convention** (`C1:`, but also `C1 (B1, from Q2):`, and sometimes no prefix at all — an empty prefix set reports "no id prefixes" rather than pretending to have checked); and §6.3 keeps everything awaiting arbitration at WARN. Verified against this repository's full verdict set: `XJ-20261004-005`'s two live references both resolve. | Point the reference at a condition id the target card's conditions actually open with, or record why the reference is undecidable. |

## Deliberate exemptions

| Pattern | Exempt from | Why |
|---|---|---|
| `REVIEW-REQUEST-*.md` | the review-card rules (`REVIEW_MISSING_VERDICT_LINE`, `REVIEW_MISSING_BLOCKERS`) | A request is a hand-over document: it asks someone to produce a verdict, so it has none by definition. Requiring one would make every well-formed request non-conformant. |
| `<NS>-REVIEW-REQUEST-<NS2>-<date>-<NNN>.md` | the namespace rule's leading-token requirement | The project-prefixed request, for use when a request travels through a mailbox shared by several agents. `REVIEW-REQUEST-<NS>-<date>-<NNN>.md` remains valid and preferred; this form additionally carries a project prefix so a request cannot be mistaken for another project's. Without it, `<NS>-REVIEW-REQUEST-…` matched neither N1 (namespace does not lead) nor `classify()`'s prefix check, so it was an ERROR with no type. Deliberately narrow: the leading token must be a namespace and the name must end in a date-number id, so `DSB-REVIEW-REQUEST-XJ.md` and `REVIEW-REQUEST-whatever.md` still fail. |
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
- **Whether the change already landed** — PROTOCOL.md §6.2 makes the push the merge
  boundary, but a linter only reads the working tree: it cannot see `origin/main`, and
  `git log` shows no remote state. `VERDICT_WITHOUT_REVIEW` therefore stays a WARN even
  though "merged without a verdict" is a real violation — the check has to be a pre-push
  hook or CI step, not this tool. Do not let the warning's severity drift into implying
  the gate would catch it.

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

## Owned-files quality (`OWNED_FILES_EMPTY`, `OWNED_FILES_TOO_BROAD`, `OWNED_FILES_NONPATH`)

`OWNED_FILES_CONFLICT` only fires when two active cards overlap. A card that
declares nothing, or declares `**`, therefore passed every other rule while
making the ownership model decorative: the claim surface existed on paper and
constrained nothing.

| Rule | Level | Why | Fix |
|---|---|---|---|
| `OWNED_FILES_EMPTY` | WARN | An active card with no claims cannot be violated, so "single write ownership" (R2) is asserted and never checked. | Declare the paths this card owns exclusively. |
| `OWNED_FILES_TOO_BROAD` | WARN | `**` and root-ish claims match everything, so a violation check against them is vacuous. | Declare concrete paths. |
| `OWNED_FILES_NONPATH` | WARN | The line sits in the Owned files section but is not shaped like a path, so it is not treated as a claim — and until this rule existed, it silently generated conflict noise instead. | Move constraints prose to the Constraints section, or put the path on its own line. |

### Why `OWNED_FILES_NONPATH` exists (the 96% noise finding)

`_owned_files()` returns whatever is on a line in the section. On the real corpus
that included prohibitions and commentary — a card reading

```
## Owned files
不要** `tools/lint_cards.py`、`tests/test_lint_cards.py`、`PROTOCOL.md`、
```

yielded a "claim" that is a sentence. Those pseudo-claims then collided with each
other through `_paths_overlap`, because the sentence happens to name files another
card also names. The measured result (EVO-20261010-002):

| | count |
|---|---|
| `OWNED_FILES_CONFLICT` before | **132** |
| Same rule, recomputed over path-shaped entries only | **5** |
| Noise | **~96%** |

That mattered beyond tidiness: `OWNED_FILES_CONFLICT` is the only ERROR-level
blocker under `--strict`, so 127 false findings were burying the 5 real ones — and
a reviewer had already read the inflated number as "the corpus is deteriorating,
clean the boards first".

The filter is deliberately permissive about *shape* and silent about *meaning*: a
well-formed path is accepted without asking whether it belongs to this card, because
guessing at intent would only relocate the false positives. Directory claims stay
legal here (`templates/TASK.md` states a directory claim owns its subtree); the
whitelist is where directory claims are refused.

Prose is **reported, never dropped**. Silently skipping it would recreate this
repository's most-repeated defect: a check that stopped looking while still
reporting success.

Both are WARN on purpose, and the reason is deployment: CI runs this linter with
`--strict`, where a WARN is an ERROR. Promoting them is a gate, and
EVO-20261007-001 forbids opening a gate before the current corpus is measured.
At the time of writing the corpus is **not** clean (11 findings on this
repository), so `--strict` cannot be used as evidence for these two rules yet.

**Directory claims stay legal here.** `templates/TASK.md` states that a directory
claim owns everything beneath it, so `tools/` is a valid entry. Only the
whitelist (`policy/owned-files-whitelist.yml`) refuses directory claims and
globs — see below.

## owned-files enforcement (dry-run shadow period)

`tools/check_owned_files.py` answers a question no rule asked before: *after the
fact, did this branch touch files that no card claimed?* Three design decisions
are load-bearing, and each one is a place where the obvious implementation is
wrong:

- **Authorization is per-diff, not per-agent.** "Whatever cards this assignee
  has open" was rejected because one forgotten `CLOSED` widens an agent's write
  surface forever. The author declares the cards a commit belongs to with a
  `Card-Id:` trailer, and the authorized surface is the union of *those* cards.
  A commit with no trailer is **unknown**, not violating — otherwise the check
  punishes the honest agent that forgot a convention instead of the one that
  broke a boundary.
- **The exit code is always 0.** Findings are data. A checker that can fail the
  build before its false-positive rate is known is not a measurement, it is an
  outage. `--strict` is deliberately absent from this tool.
- **The whitelist is an exception list, not a permission.** Exact paths only; a
  glob in a shared exception file is a universal escape hatch wearing a config
  file's clothes. High-impact files — this repository's CI, linter, gate, artifact
  map and the whitelist itself — are protected by `.github/CODEOWNERS` instead,
  because a human approval boundary is the only kind that survives a determined
  agent. CODEOWNERS binds on GitHub PRs only; it is an approval boundary, not an
  absolute one.

**Shadow period exit criteria** (EVO-20261007-001): run ≥1 week or ≥3 tasks,
then promote to a real gate only if the false-positive rate stays ≤10% and no
more than 3 human rescues were needed per week. Above that, fix the rules before
the gate. Until then the CI job runs with `continue-on-error: true` and uploads
its report as an artifact.

**Escape hatch, deliberately narrow**: fix the rules or ask a human — do not add
a whitelist entry to silence your own violation. Whitelist changes are
high-impact changes and need sir's sign-off.

## Review-card sections must be sections (`REVIEW_MISSING_BLOCKERS`)

A heading that *names* a section is not that section. The original test was
`any("blocker" in name for name in _sections(text))`, and `_sections` collects
every heading at every level — so a verdict heading reading
`### **PASS** (blockers=0)` satisfied the rule while the card carried no Blockers
section at all. Three review copies shipped that way and passed
(EVO-20261010-004).

Scanning the corpus showed the substring test admits three kinds of noise:

| heading actually seen | what it really is |
|---|---|
| `### **PASS** (blockers=0)` | verdict heading |
| `### P1 · 解析对齐 —— 阻断（2× 分母回归）` | finding heading |
| `### B1 reproduction (the blocker)` | evidence heading |

Enumerating those as exceptions would be whack-a-mole; matching the *structure*
is the fix. The rule now requires an H1/H2 heading whose text **is** the name:
`## Blockers`, `## Blocker` (singular — the corpus uses it once), `## 阻断`,
optionally bolded, optionally trailing a colon.

### The pattern behind three same-day defects

This was the third of three defects fixed in one day with a single root cause —
**approximating structure with a substring**:

| defect | the substring stood in for |
|---|---|
| `_owned_files()` read constraint prose as file claims | a path (EVO-20261010-002) |
| `check_evo_protected_assets()` read "不改 gate.py" as "will change gate.py" | an intent (EVO-20261010-003) |
| `_sections()` accepted a verdict heading as a Blockers section | a section (EVO-20261010-004) |

Each one *admitted noise while missing the real thing*: prose generated 127
phantom conflicts, a prohibition was read as a plan, and a verdict line passed a
structural requirement. The lesson worth keeping is narrower than "be careful":
when a check asks whether some structure exists, match the structure, and treat
"the word appears somewhere" as evidence of nothing.

## Declared vs mentioned: task-card sections (`TASK_MISSING_SECTION`)

`_has_section` asked "does this card declare a Constraints section?" by checking
whether the alias appeared **anywhere** in a heading. The Chinese alias `边界` is
two very common characters, so this satisfied it:

```
### ③ 5 条真冲突未处理 —— 边界划得对，应另开卡
```

Four sentences and a document H1 were being read as sections (EVO-20261010-005).

Two fixes were tried before one survived, and the rejected one is the interesting
part — **equality is too strict**:

| rule | `## Acceptance audit` | `### 边界划得对，应另开卡` |
|---|---|---|
| substring (original) | ✅ accepted | ❌ accepted (the bug) |
| equality | ❌ **rejected (a regression)** | ✅ rejected |
| **start-anchored** | ✅ accepted | ✅ rejected |

`## Acceptance audit` is a genuine acceptance section with a qualifier; a rule
that drops it trades one defect for another. Anchoring at the start keeps the
qualifier and drops the sentence. Measured across `.tasks/*.md`: of 12 cards where
the loose rule disagreed with a stricter one, this keeps the 8 real sections and
rejects the 4 sentences, with no card losing a section it actually declares.

**Why the other two same-shaped checks were left alone.** EVO-20261010-004's
review flagged all three (`_has_section`, `verdict_section`,
`REVIEW_Q_SECTIONS`) as the same anti-pattern, and they are — but they are not
equally exposed:

| check | second line of defence | output | action |
|---|---|---|---|
| `_has_section` | none | ERROR | **tightened** |
| `verdict_section` | `\b(PASS\|CONDITIONAL\|FAIL)\b` anchor | ERROR | left, comment added |
| `REVIEW_Q_SECTIONS` | none | WARN | left, note added |

Tightening a check that already has a backstop buys little and costs regression
surface. The grading is recorded here so a future audit does not have to re-derive
it — and so that removing the `verdict_section` anchor's `elif` branch is visibly
a mistake rather than a simplification.

## `ORPHAN_VERDICT`: a verdict with no card *anywhere*

The rule asks a narrower question than it looks: not "is this verdict
meaningful?" but "is its card missing from the places we look?". Cards were
collected from `.tasks/*.md` and `.tasks/legacy/*.md`, which meant the EVO rule
cards were invisible — they are `_handoffs/evo/EVO-*.json`, outside the card
directory entirely. Four of them (`EVO-20261010-001..004`), each holding a PASS
verdict and a review document, were reported as orphans.

So the fix is **one-sided on purpose**. EVO card ids are admitted for the orphan
direction only:

| direction | sees EVO ids? | why |
|---|---|---|
| orphan (verdict without card) | **yes** | the cards exist; we were simply not looking |
| card without verdict | **no** | whether EVO cards must carry a verdict is a question about the EVO state machine, not this rule |

Folding them into both would have been tidier and much worse: seven of the eleven
EVO cards have no in-repo verdict, so the reverse direction would have fired
seven times over — **four false positives traded for forty new ones**. Two tests
in `TestEvoVerdictPairing` exist purely to keep that asymmetry from being
"cleaned up" by a later reader.

Note the two directories already disagree on what counts as an id: the active
directory requires a strict `NAMESPACE_RE` full-name match (`XJ-...md`), while
`legacy/` uses the looser `ID_IN_NAME_RE`, which also extracts an id from
`REVIEW-XJ-....md`. That inconsistency is why an archived card's review file
keeps its verdict paired while the same file in the active directory would not.
Tracked as a review question on `XJ-20261013-002`, not fixed here.

Without `--evo-dir` the four findings return unchanged: the directory was not
named, so lint does not guess at it.

## EVO protected assets (`EVO_PROTECTED_ASSET_TOUCHED`)

A rule-evolution card must not quietly rewrite the system that judges it. Two
independent projects state the same principle — AgentDescent puts it plainly
(*"a self-modifying system must not be able to replace its own evaluator"*, with
its governance layer deliberately non-pluggable) and DarwinAgent encodes it as an
asset boundary that fails closed — and reef makes it structural: its commit record
admits only `training / rollback / promote`, where `rollback`/`promote` **must**
carry a target id and `training` **must not**. A rule about what may not change
belongs in a schema, not in a paragraph.

`EVO-20261010-003` gives this repository the same shape. Five assets are protected
(sir's list):

1. verdict 模板与字段语义
2. EVO 状态机定义
3. AgnesCode 评审员资格
4. sir 终裁权
5. `gate.py` 判定逻辑

A card that **targets** one of them is an ERROR unless it also carries both
`protected_assets_changes` (naming the asset and why) and `sir_approval` — that
pair is the legitimate escalation path, because a discipline-level change is sir's
call and never something a card can grant itself.

**Detection is by declaration, not by keyword.** The first draft scraped prose and
produced three false positives on the existing corpus, every one a card that was
*protecting* the asset:

```
"不改 gate.py（评审明确禁区）"
"高风险文件（gate.yml、lint_cards.py、gate.py…）不进白名单"
"状态机补旁路"
```

A keyword scan cannot distinguish *"I will change X"* from *"I will not change
X"*, so it fired hardest on the cards defending the boundary most explicitly. That
inversion is disqualifying: cards now declare `protected_assets_targeted`, and only
that list is judged. A card remains free to discuss, cite or forbid `gate.py` in
prose without being treated as touching it.

`EVO_PROTECTED_ASSET_UNKNOWN` (WARN) catches a typo'd asset name, so a
misspelling cannot silently opt a card out of the boundary.

Enable with `--evo-dir <path>`; without the flag the check is off, like every
other rule that needs an external file.

## Card self-listing in the artifact map (`CARD_SELF_IN_MAP`)

`artifacts.json` says it plainly: *"Keep this list equal to what the reviewer
actually read."* A round's own card is not something the reviewer read — it is
the record *of* the review. Listing it makes the round stale by construction:

1. The freshness rule compares every listed artifact's mtime against the round's
   verdict timestamp.
2. Closing a card edits the card file (`IN_REVIEW` → `CLOSED`, recording the
   verdict and the reviewed commit), and that edit necessarily happens *after*
   the verdict is written.
3. No later round revisits a closed card, so nothing ever supersedes the finding.

The result is a permanent, unactionable finding — worse than noise, because it
sits among real staleness and trains readers to ignore the list. `XJ-20261008-001`
demonstrated it end to end: closing the card produced
`[STALE_VERDICT] ... .tasks/XJ-20261008-001.md was modified after the verdict`,
with no verdict able to retire it afterwards.

**The rule is WARN, not ERROR.** Seven rounds carried the pattern and the
repository tolerates some of them living red for unrelated reasons; the point is
to stop the habit spreading, not to demand a sweep nobody scheduled. Only
`XJ-20261008-001` was corrected (EVO-20261010-001) — the rest were left alone
deliberately, because their staleness comes from later rounds touching shared
files, which is the mechanism working, not this defect.

Note what this rule is *not*: it is not a fix to `gate.py`. The freshness logic is
correct; the defect was in the data. `gate.py` stays untouched.

## The test-count anchor (`<!-- test-count -->N<!-- /test-count -->`)

`STALE_TEST_COUNT` is right and was still painful: the count lived as hand-written
prose in two READMEs, so one added test made both files wrong at once. It tripped
three times in a week (141 → 166 → 168). The rule stays; the *hand-typing* goes.

`tools/sync_test_count.py` writes the real count into both READMEs:

```
python tools/sync_test_count.py            # write the count
python tools/sync_test_count.py --check    # exit 1 when out of sync
```

**The anchor is not an exemption.** `TEST_COUNT_RES` lists the anchored form
first, so the checker reads the number back and a stale anchor fails exactly like
stale prose. If the anchor were skipped, the syntax would become a place to hide
a wrong claim — the exact inversion of why the rule exists.

Four decisions worth knowing, because each rejects an easier wrong answer:

- **The count comes from `unittest`, not `grep`.** The review suggested
  `grep -c "^def test_" tests/*.py`, which happens to agree with the suite today
  (168 == 168). It agrees by coincidence: this repository has no parameterised
  tests and no shared test-case base class. `lint_cards.py` already discovers the
  count properly, and a sync tool that disagreed with the checker would just be
  a new way to be wrong.
- **The sync runs locally, not in CI.** CI writing a README would leave an
  uncommitted diff in the PR flow, and `gate.yml` deliberately holds
  `contents: read`; a writer needs a permission widening the project avoids.
- **A missing anchor is an error, never a silent no-op.** A tool that reports
  success while changing nothing is the failure mode this whole exercise targets.
- **The self-referential test is intentional.** `test_check_mode_on_the_real_repo_is_clean`
  fails the moment a test is added without syncing, because that test *is* a
  test. That pressure is the point: the fix is one command, and the alternative
  is a number that rots quietly.
