#!/usr/bin/env python3
"""agent-covenant lint-cards — schema and naming linter for collaboration cards.

Stdlib only. See PROTOCOL.md §4 (schemas) and §7 (naming rules N1/N2), and
docs/lint-rules.md for the rationale behind each rule.

Usage
-----
    python tools/lint_cards.py --dir .tasks
    python tools/lint_cards.py --dir .tasks --verdict-dir verdicts --strict
    python tools/lint_cards.py --dir .tasks --artifact-map artifacts.json
    python tools/lint_cards.py --dir .tasks --json

Exit codes
----------
    0  no ERROR-level findings (WARN allowed unless --strict)
    1  at least one ERROR
    2  usage error
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2

NAMESPACE_RE = re.compile(r"^([A-Z]{2,6})-\d{8}-\d{3}\.md$")

# Directory documentation is not a card, so N1's hijack rationale does not reach it.
# N1 exists because a bare name like TASK-002 gets resolved against another agent's
# context and the review lands on the wrong artifact (postmortems PM-1); a README
# describes the card directory, and no second agent will mint a card called
# "README". Localized variants (README.zh-CN.md) are the same artifact.
#
# Observed 2026-10-02 in the deepseek-brain review run: its own `.tasks/README.md`
# was reported NAMESPACE_MISSING, and the only way to silence that was to rename the
# file to something that lied about what it was — which then got parsed as a task
# card and produced four TASK_MISSING_SECTION warnings instead. A rule that can only
# be satisfied by misnaming a file is a rule with no valid compliance path.
#
# Deliberately narrow: `README.md` and `README.<locale>.md` only. A card directory
# is not the place for general prose notes, and widening this to "any unnamespaced
# .md" would exempt exactly the bare names N1 was written to catch.
DIRECTORY_DOC_RE = re.compile(r"^README(\.[A-Za-z-]+)?\.md$")

# A review request that carries a project prefix. The canonical hand-over name here is
# `REVIEW-REQUEST-<NS>-<date>-<NNN>.md`, which satisfies N1 through the `REVIEW-` prefix
# exemption and carries no project prefix. That form remains both valid and preferred.
#
# This pattern exists because a mailbox shared by several agents invites project-prefixed
# names, and `<NS>-REVIEW-REQUEST-...` matches neither the N1 pattern (the namespace does
# not lead) nor `classify()`'s literal-prefix check (the name does not start with
# `REVIEW-REQUEST-`), so it was an ERROR with no recognised type. The same mailbox
# already held `REVIEW-BRIEF-XJRC-20261002-001.md`, a third type prefix invented
# independently, so this is an emerging convention rather than a hypothetical.
#
# Observed 2026-10-02 in the deepseek-brain review run. Worth recording how that run
# actually failed: its orchestrator invented a `DSB-` project prefix, and the resulting
# names broke N1. The rule was working as designed -- the naming was the defect. An
# earlier draft of this comment claimed N1 admitted no conformant namespaced request,
# which the repository's own conventions disprove; corrected rather than left standing.
#
# Narrow on purpose: the leading token must be a namespace and the name must end in a
# date-number id, so `REVIEW-REQUEST-whatever.md` and other bare names stay rejected.
NAMESPACED_REQUEST_RE = re.compile(
    r"^([A-Z]{2,6})-REVIEW-REQUEST-(?:[A-Z]{2,6}-)?\d{8}-\d{3}\.md$"
)
ID_IN_NAME_RE = re.compile(r"([A-Z]{2,6}-\d{8}-\d{3})")
BARE_TASK_RE = re.compile(r"TASK-\d+")
ABS_PATH_RE = re.compile(r"[A-Za-z]:\\|/")
VERDICT_SUFFIX = ".verdict.json"
# The snapshot-link facility the traceability contract writes into. `link_card.py`
# owns the prefix/suffix; kept local so lint does not import a writer tool just to
# name a file (the shape is a data contract, not logic).
FREEZE_DIRNAME = ".freeze"
LINK_PREFIX = "link-"

# Must mirror gate.py's default --max-clock-skew (300s) so the future-ts
# plausibility check cannot drift between lint and gate. Single source of
# truth on purpose: the dead shadow VALID_VERDICTS tuple in
# check_verdict_schema was exactly this kind of trap - a local copy of a
# gate constant that looked like a check but changed nothing.
LINT_MAX_CLOCK_SKEW = 300

TASK_SECTIONS = ("context", "deliverables", "constraints", "acceptance", "status")
TASK_SECTION_ALIASES = {
    "context": ("context", "上下文", "背景"),
    "deliverables": ("deliverables", "deliverable", "产出", "交付"),
    "constraints": ("constraints", "constraint", "约束", "边界"),
    "acceptance": ("acceptance", "验收"),
    "status": ("status", "状态"),
}
REVIEW_Q_SECTIONS = ("review questions", "review handoff",
                     "review_questions", "review handoff", "审查问题", "审查")

# The public claim surface: the files a reader trusts without running anything.
CLAIM_SURFACE_FILES = ("README.md", "README.zh-CN.md", "CHANGELOG.md")
# CHANGELOG is deliberately absent. A changelog entry records what was true at
# that release, so a historical "45 tests" is correct history, not a stale claim.
COUNTED_CLAIM_FILES = ("README.md", "README.zh-CN.md")
# The anchored form is listed FIRST on purpose. `tools/sync_test_count.py`
# writes `<!-- test-count -->N<!-- /test-count -->`, and that marker is a
# convenience for the writer, not an exemption from this check: a stale anchor
# must fail exactly like stale prose. Ordering it first means the anchor (when
# present on a line) is the number reported, so the reader is told about the
# claim the sync script is responsible for.
TEST_COUNT_RES = (
    re.compile(r"<!--\s*test-count\s*-->(\d+)<!--\s*/test-count\s*-->"),
    re.compile(r"#\s*(\d+)\s+tests?\b"),
    re.compile(r"(\d+)\s*个(?:单测|单元测试|测试)"),
)


def _safe_utf8():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _sections(text):
    """Return the set of normalised H2 section names present in a markdown body."""
    found = set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            body = stripped.lstrip("#").strip().lower().replace("：", ":")
            found.add(body)
    return found


def _norm_heading(name):
    """A heading reduced to comparable form: no markers, no bold, no trailing colon."""
    return name.strip().strip("*").strip(" :：").strip().lower()


def _section_name_matches(sections, aliases):
    """True when some heading *is* one of `aliases`, allowing a qualifier after it.

    The intent is "does this card declare a Constraints section?", and the answer
    has to survive both a shorter and a longer spelling: `## Acceptance audit` is
    an acceptance section, `## 中文验收` is one, but
    `## ③ 5 条真冲突未处理 —— 边界划得对，应另开卡` is a sentence that happens to
    contain `边界`.

    Two rules were rejected on corpus evidence before this one (EVO-20261010-005):

      * substring (`alias in name`) -- the original. Measured over the corpus it
        accepted four sentences and one document H1 as sections, because the
        Chinese alias `边界` is two very common characters.
      * equality (`name == alias`) -- too strict. It drops `## Acceptance audit`,
        which is a real acceptance section with a qualifier.

    Anchoring at the START keeps the qualifier and drops the sentence. Verified
    against all `.tasks/*.md`: of 12 cards where the loose rule disagreed with a
    stricter one, this keeps the 8 genuine sections and rejects the 4 sentences,
    with no card losing a section it actually declares.
    """
    wanted = [_norm_heading(a) for a in aliases if a and a.strip()]
    for name in sections:
        core = _norm_heading(name)
        if any(core.startswith(a) for a in wanted):
            return True
    return False


def _has_section(sections, key):
    return _section_name_matches(sections, TASK_SECTION_ALIASES.get(key, (key,)))


def classify(path):
    name = path.name
    if NAMESPACED_REQUEST_RE.match(name):
        return "request"  # namespaced hand-over; see NAMESPACED_REQUEST_RE
    if name.startswith("REVIEW-REQUEST-"):
        return "request"  # a hand-over document; it never carries a verdict by definition
    if name.startswith("REVIEW-"):
        return "review"
    if name.startswith("HANDOFF-") or name.startswith("ADR-"):
        return "exempt"
    if BARE_TASK_RE.match(name):
        return "bare_task"
    if NAMESPACE_RE.match(name):
        return "task"
    return "other"


def _finding(rule, level, path, detail, line=None):
    return {"rule": rule, "level": level, "file": path.name, "line": line, "detail": detail}


def check_namespace(path, _text):
    if DIRECTORY_DOC_RE.match(path.name):
        return []
    if (not NAMESPACE_RE.match(path.name)
            and not path.name.startswith(("REVIEW-", "HANDOFF-", "ADR-"))
            and not NAMESPACED_REQUEST_RE.match(path.name)):
        return [_finding("NAMESPACE_MISSING", "ERROR", path,
                         "filename must be <NS>-YYYYMMDD-NNN.md (PROTOCOL.md N1); "
                         f"got {path.name!r} — a bare name can be hijacked by another agent")]
    return []


HANDOVER_HEADERS = ("review handoff", "review questions", "审查", "trigger", "触发",
                    "next single action")


def _handover_line_numbers(text):
    """Line numbers that live inside a handover section.

    N2 exists to stop a bare task id being used *as a handover instruction*.
    Quoting an incident in Context ("the TASK-002 collision", postmortems PM-1)
    is not a handover, so scanning the whole body produced false positives that
    trained people to ignore the linter. Only sections that instruct a reader to
    go and do something are in scope.
    """
    lines = text.splitlines()
    in_scope = set()
    active = False
    for number, line in enumerate(lines, start=1):
        if line.strip().startswith("#"):
            header = line.strip().lstrip("#").strip().lower()
            active = any(alias in header for alias in HANDOVER_HEADERS)
            continue
        if active:
            in_scope.add(number)
    return in_scope


def check_bare_task_refs(path, text):
    out = []
    scoped = _handover_line_numbers(text)
    for number, line in enumerate(text.splitlines(), start=1):
        if scoped and number not in scoped:
            continue
        for match in BARE_TASK_RE.finditer(line):
            if ABS_PATH_RE.search(line):
                continue  # referenced together with an absolute path: conformant
            out.append(_finding("BARE_TASK_NAME", "ERROR", path,
                                f"bare {match.group(0)} reference - hand over the absolute "
                                "path instead (PROTOCOL.md N2)", number))
    return out


#: A Blockers declaration is a *section heading*, not any line that mentions the
#: word. H1/H2 only, and the heading text must BE the name (optionally bolded,
#: optionally trailing a colon) rather than merely contain it.
#:
#: `阻塞` is kept alongside `阻断` for a specific reason: the pre-fix rule tested
#: `"阻塞" in name`, so dropping it here would narrow the accepted vocabulary
#: while fixing the over-acceptance. No card currently writes either as a heading
#: (reviewed: 19x `## Blockers`, 1x `## Blocker`, zero Chinese headings), so the
#: two spellings are behaviourally invisible today -- keeping both costs nothing
#: and avoids failing a future author who writes one of them. Reviewer T-1 caught
#: the dropped word; the docstring above it previously over-claimed that the
#: corpus uses `## 阻断`, which it does not.
BLOCKERS_SECTION_RE = re.compile(
    r"^\s{0,3}#{1,2}\s+(?:\*\*)?\s*(?:blockers?|阻断|阻塞)\s*(?:\*\*)?\s*[:：]?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _has_blockers_section(text):
    """True when the card declares a Blockers section, not merely names one.

    The previous test was `any("blocker" in name for name in _sections(text))`,
    and `_sections` collects every heading at every level. So a verdict heading
    reading `### **PASS** (blockers=0)` satisfied the rule while the card had no
    Blockers section at all -- three review copies shipped that way and passed
    (EVO-20261010-004).

    Scanning the corpus showed the substring test admits three kinds of noise:
    verdict headings (`### **PASS** (blockers=0)`), finding headings
    (`### P1 - blocked (2x regression)`), and evidence headings
    (`### B1 reproduction (the blocker)`). Trying to enumerate those as
    exceptions would be whack-a-mole; matching the structure is the fix.

    Accepted forms, checked against the corpus rather than assumed: 19 cards use
    `## Blockers`, one uses `## Blocker` (singular). No card uses a Chinese
    heading, but `阻断` and `阻塞` stay accepted because the pre-fix rule matched
    `阻塞` and narrowing the vocabulary is not part of this fix.
    """
    return bool(BLOCKERS_SECTION_RE.search(text))


def check_review_card(path, text):
    out = []
    sections = _sections(text)
    verdict_section = any("verdict" in name or "结论" in name or "总评" in name for name in sections)
    if not verdict_section:
        out.append(_finding("REVIEW_MISSING_VERDICT_LINE", "ERROR", path,
                            "no '## Verdict' section (PASS / CONDITIONAL / FAIL)"))
    elif not re.search(r"\b(PASS|CONDITIONAL|FAIL)\b", text, re.IGNORECASE):
        out.append(_finding("REVIEW_MISSING_VERDICT_LINE", "ERROR", path,
                            "'## Verdict' section contains no PASS / CONDITIONAL / FAIL"))
    if not _has_blockers_section(text):
        out.append(_finding("REVIEW_MISSING_BLOCKERS", "ERROR", path,
                            "no '## Blockers' section (state the count, even if zero)"))
    return out


# A fence opens with three or more backticks or tildes, optionally indented, and
# closes with the same character. Markdown lets a document carry a section header
# inside a fence as *documentation of that section*, so a heading scan that ignores
# fences reads the illustration as the real thing. Track the marker instead of
# matching a fixed string: ``` and ~~~ both count, and a longer run still closes a
# shorter opening.
_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


def _fenced_line_indices(lines):
    """Indices of every line that belongs to a fenced code block, fences included.

    Returns a set so callers can skip with one membership test per line.
    """
    inside = set()
    marker = None
    for index, line in enumerate(lines):
        match = _FENCE_RE.match(line)
        if marker is None:
            if match:
                marker = match.group(1)[0]
                inside.add(index)
            continue
        inside.add(index)
        if match and match.group(1)[0] == marker:
            marker = None
    return inside


def _section_body(text, header_names):
    """Return the text under the first H2 whose header matches one of header_names.

    A status word lives in the body, not in the header line, so a single-line scan
    silently misses it.

    Headings inside fenced code blocks are skipped. A card that documents the
    status section it is expected to carry would otherwise have that illustration
    read as the card's own status (XJ-20261013-006 did exactly this, and the rule
    it documents came back to fire on it).
    """
    lines = text.splitlines()
    fenced = _fenced_line_indices(lines)
    for index, line in enumerate(lines):
        if index in fenced:
            continue
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        header = stripped.lstrip("#").strip().lower()
        header = header.split("：")[0].split(":")[0].strip()
        if header in header_names:
            body = []
            for follower in lines[index + 1:]:
                if follower.strip().startswith("#"):
                    break
                body.append(follower)
            return "\n".join(body)
    return ""


def check_task_card(path, text):
    out = []
    sections = _sections(text)
    for key in TASK_SECTIONS:
        if not _has_section(sections, key):
            out.append(_finding("TASK_MISSING_SECTION", "WARN", path,
                                f"missing section for '{key}'"))
    if not any(any(alias in name for alias in REVIEW_Q_SECTIONS) for name in sections):
        out.append(_finding("TASK_MISSING_REVIEW_QUESTIONS", "WARN", path,
                            "no 'Review questions' / 'Review handoff' section — the reviewer "
                            "has no adversarial brief"))
    status_body = _section_body(text, ("status", "状态"))
    closed_now = re.search(r"\b(CLOSED|GATED)\b", status_body, re.IGNORECASE) or \
        re.search(r"(已归档|已完成|已通过)", status_body)
    if closed_now:
        out.append(_finding("CLOSED_NOT_ARCHIVED", "WARN", path,
                            "card is CLOSED/GATED but still present — archive or delete it "
                            "within one working day (PROTOCOL.md §8)"))
    return out


CONDITION_PREFIX_RE = re.compile(r"^\s*([A-Za-z]+\d+)")


def _condition_prefixes(conditions):
    """Best-effort condition ids from a verdict's free-text conditions.

    Condition ids are a convention, not a schema field: in practice every
    condition in this repository opens with 'C1', 'C2', ... -- sometimes
    annotated as 'C1 (B1, from Q2): ...'. Extracting the leading token is
    therefore reliable on this data set, but it is a *prefix*, not a field:
    conditions without such a token contribute nothing, and callers must
    treat an empty set as 'cannot verify', never as 'no conditions'.
    """
    out = set()
    if not isinstance(conditions, list):
        return out
    for cond in conditions:
        if not isinstance(cond, str):
            continue
        m = CONDITION_PREFIX_RE.match(cond)
        if m:
            out.add(m.group(1))
    return out


def _check_unblocks_dangling(verdict_dir):
    """WARN when an unblocks reference names a condition that may not exist.

    This is ADR-0002's revisit-trigger item 2 made checkable: an unblocks
    value claiming to discharge XJ-....C9 when that card's conditions open
    with C1/C2 can now be seen, where before only the shape was checked.

    Deliberately WARN, on three grounds. A referenced card with no verdict
    file yet (still queued for review) makes existence *undecidable*, and
    erroring would fail closed on a state another rule already reports
    (VERDICT_WITHOUT_REVIEW). The prefix is a convention, not a field: a
    card whose conditions carry no leading token has an empty prefix set,
    and an error would turn every reference to it into a false positive.
    And per 6.3, anything awaiting arbitration warns rather than blocks.

    Reads verdicts directly rather than through gate.load_verdict for the
    same reason _check_duplicate_unblocks does: malformed files are already
    the schema check's finding.
    """
    out = []
    verdicts = {}
    for path in sorted(verdict_dir.glob(f"*{VERDICT_SUFFIX}")):
        vid = path.name[: -len(VERDICT_SUFFIX)]
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001 - reported by the schema check
            continue
        if isinstance(data, dict):
            verdicts[vid] = data

    # Claimant pass: every unblocks reference, resolved against the
    # referenced card's own conditions.
    for vid, data in verdicts.items():
        value = data.get("unblocks")
        if isinstance(value, str):
            refs = [value]
        elif isinstance(value, list):
            refs = [i for i in value if isinstance(i, str)]
        else:
            continue
        for ref in refs:
            if not UNBLOCKS_RE.match(ref):
                continue  # UNBLOCKS_MALFORMED already covers the shape
            target_card, _, cond_id = ref.partition(".")
            target = verdicts.get(target_card)
            if target is None:
                out.append(_finding(
                    "UNBLOCKS_DANGLING", "WARN",
                    Path(f"{vid}{VERDICT_SUFFIX}"),
                    f"{ref}: referenced card has no verdict on disk, so the "
                    "condition cannot be verified",
                ))
                continue
            prefixes = _condition_prefixes(target.get("conditions"))
            if cond_id not in prefixes:
                detail = (f"{ref}: referenced card's conditions do not open "
                          f"with {cond_id} (found: "
                          f"{sorted(prefixes) if prefixes else 'no id prefixes'})")
                out.append(_finding(
                    "UNBLOCKS_DANGLING", "WARN",
                    Path(f"{vid}{VERDICT_SUFFIX}"), detail,
                ))
    return out


def check_verdict_pairs(card_ids, verdict_dir, extra_known_ids=None, allow_orphan_ids=None):
    """Pair verdicts against cards, in both directions.

    `extra_known_ids` are ids that count as "a card exists" for the orphan
    direction only. EVO rule cards live outside the card directory as
    `_handoffs/evo/EVO-*.json`, so their in-repo verdicts used to be reported
    as ORPHAN_VERDICT -- four false positives (EVO-20261010-001..004), each of
    which had both a PASS verdict and a review document.

    `allow_orphan_ids` (XJ-20261021-003, dp 大脑裁定) are ids whose orphan
    finding is DOWNGRADED to NOTICE — still printed, still in the JSON, but
    not counted as a failure under --strict. This is the constrained green:
    the topology-accepted orphans stay visible, and any NEW orphan id (a
    verdict nobody expected) still warns and fails strict. Purely removing
    the finding would swallow future unknowns; permanent red would kill the
    CI's signal value.

    Deliberately one-sided. Folding these ids into `card_ids` proper would make
    the reverse direction fire for the seven EVO cards with no in-repo verdict,
    turning four false positives into forty real-looking ones -- a second defect
    traded for the first. Whether EVO cards must carry a verdict is a separate
    question about the EVO state machine, not something to decide here.
    """
    out = []
    if not verdict_dir or not verdict_dir.is_dir():
        return out
    verdict_ids = {p.name[: -len(VERDICT_SUFFIX)] for p in verdict_dir.glob(f"*{VERDICT_SUFFIX}")}
    known_ids = card_ids | set(extra_known_ids or ())
    allowed = set(allow_orphan_ids or ())
    for vid in sorted(verdict_ids - known_ids):
        if vid in allowed:
            out.append(_finding("ORPHAN_VERDICT", "NOTICE", Path(f"{vid}{VERDICT_SUFFIX}"),
                                "verdict has no matching card in the card directory "
                                "(allow-listed topology orphan; still visible, not a failure)"))
        else:
            out.append(_finding("ORPHAN_VERDICT", "WARN", Path(f"{vid}{VERDICT_SUFFIX}"),
                                "verdict has no matching card in the card directory"))
    for vid in sorted(card_ids - verdict_ids):
        out.append(_finding("VERDICT_WITHOUT_REVIEW", "WARN", Path(f"{vid}.md"),
                            "card has no machine-readable verdict file"))
    out.extend(_check_duplicate_unblocks(verdict_dir))
    out.extend(_check_unblocks_dangling(verdict_dir))
    return out


def _check_duplicate_unblocks(verdict_dir):
    """WARN when two or more verdicts claim the same resolution reference.

    ADR-0002 section 6.3 records duplicate closure as a *known, unarbitrated
    hazard*: nothing says which of two claimants actually closed the condition,
    and two is not an exotic count - a fix card plus a re-check card is a normal
    shape. Arbitration is deferred to the machine check, so this warns and does
    not block. Raising it to an error before that arbitration exists would block
    legitimate pairs.

    The verdict files are read directly rather than through gate.load_verdict:
    this check needs only one optional field, and a malformed verdict is already
    reported by check_verdict_schema.
    """
    out = []
    claims = {}
    for path in sorted(verdict_dir.glob(f"*{VERDICT_SUFFIX}")):
        vid = path.name[: -len(VERDICT_SUFFIX)]
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001 - reported by the schema check
            continue
        if not isinstance(data, dict):
            continue
        value = data.get("unblocks")
        if isinstance(value, str):
            items = [value]
        elif isinstance(value, list):
            items = [i for i in value if isinstance(i, str)]
        else:
            continue
        for item in items:
            claims.setdefault(item, []).append(vid)
    for ref in sorted(claims):
        claimants = sorted(claims[ref])
        if len(claimants) > 1:
            out.append(_finding(
                "DUPLICATE_UNBLOCKS", "WARN",
                Path(f"{claimants[0]}{VERDICT_SUFFIX}"),
                f"{ref} is claimed by {len(claimants)} verdicts "
                f"({', '.join(claimants)}); which of them closed the condition is "
                "unarbitrated (ADR-0002 6.3)",
            ))
    return out


def _project_root(card_dir):
    """The project the cards belong to: `<project>/.tasks` -> `<project>`.

    Rules that inspect the claim surface read the *linted* project, not the
    repository the linter happens to ship in, so running the linter against a
    scratch directory does not drag that directory's README into scope.
    """
    return card_dir.resolve().parent


def _suite_has_import_failure(suite):
    """True if discovery produced placeholder tests for modules it could not import.

    `unittest` does not raise on a broken import: it substitutes a `_FailedTest`
    and carries on. The resulting `countTestCases()` is therefore a *count of a
    suite that cannot run* — comparing a declared number against it would report
    a confident mismatch against a meaningless baseline, which is worse than
    reporting nothing. Checked by class name so no private symbol is imported.
    """
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            if _suite_has_import_failure(item):
                return True
        elif type(item).__name__ == "_FailedTest":
            return True
    return False


def _discover_test_count(project_root):
    """Count the suite in-process. Returns `(count, failed)`.

    The `failed` flag is the whole point. A project with no `tests/` directory is
    legitimately nothing to compare against, but a suite that cannot be imported
    is a check that switched itself off and reported success — the inverse of
    PM-10, where a check weakened itself when a flag was forgotten. That silent
    path already hid a bug during this rule's own implementation:
    `top_level_dir` made discovery refuse to import a non-package `tests/`, so the
    rule was dead on this repository until a test caught it. Silence is not an
    acceptable answer to "I could not run my own check".

    Discovery mirrors the documented run command (`python -m unittest discover -s
    tests`), so top_level_dir is deliberately left at its default: tests/ is not a
    package, and forcing repo root as the top level makes discovery refuse to
    import it.
    """
    tests_dir = project_root / "tests"
    if not tests_dir.is_dir():
        return None, False
    try:
        suite = unittest.TestLoader().discover(str(tests_dir))
    except Exception:
        return None, True  # a broken test tree must not crash the lint run
    if _suite_has_import_failure(suite):
        return None, True
    return suite.countTestCases(), False


def _declared_counts(text):
    """Yield `(line_no, number)` for counts declared in copy-pasteable blocks only.

    Restricting to fenced code blocks is what keeps the rule honest: a number in
    a command a reader can run is a claim that must stay true, while a number in
    an explanation ("the README used to claim 45 tests") is commentary about the
    past and re-checking it would flag the very correction this project wants to
    make. A rule that cries wolf on its own documentation trains people to ignore
    it, which is the PM this project exists to prevent.
    """
    in_block = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_block = not in_block
            continue
        if not in_block:
            continue
        for pattern in TEST_COUNT_RES:
            match = pattern.search(line)
            if match:
                yield number, int(match.group(1))
                break


def check_stale_test_count(project_root):
    """A test count written in prose rots silently; nothing else would notice.

    This repository shipped a README claiming 45 tests while the suite held 69,
    and no rule read prose. The defect class this project exists to prevent
    happened to the project itself, so the linter now reads the number back.
    """
    out = []
    actual, failed = _discover_test_count(project_root)
    if failed:
        out.append(_finding("TEST_COUNT_UNVERIFIED", "WARN", project_root,
                            "test suite discovery raised, so no declared count was checked - "
                            "the rule is off, not passing"))
        return out
    if actual is None:
        return out
    for name in COUNTED_CLAIM_FILES:
        path = project_root / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for number, claimed in _declared_counts(text):
            if claimed != actual:
                out.append(_finding("STALE_TEST_COUNT", "ERROR", path,
                                    f"declares {claimed} tests but the suite holds "
                                    f"{actual} - a number in prose goes stale on the next "
                                    "test added", number))
    return out


def load_artifact_map(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot read artifact map {path}: {exc}")
    if not isinstance(data, dict):
        raise ValueError(f"artifact map {path} must be a JSON object")
    return data


def _verdict_index(verdict_dir):
    """`{id: record}` for every readable verdict file; unreadable ones stay absent."""
    records = {}
    if not verdict_dir or not Path(verdict_dir).is_dir():
        return records
    for path in sorted(Path(verdict_dir).glob(f"*{VERDICT_SUFFIX}")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(record, dict):
            records[path.name[: -len(VERDICT_SUFFIX)]] = record
    return records


def _signed_at(record):
    """A verdict's signature instant, or None when it carries no usable `ts`."""
    raw = record.get("ts")
    if not isinstance(raw, str):
        return None
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def _listed_files(entry):
    """The file paths one artifact-map entry claims, normalised."""
    if not isinstance(entry, list):
        return set()
    return {item.strip().replace("\\", "/").lstrip("./")
            for item in entry if isinstance(item, str)}


def _claim_state(name, path, artifact_map, ids, verdicts):
    """Who, if anyone, stands behind `name`'s current text.

    Returns `(holder, listed_by, blockers)`. `holder` is the id of a round that
    lists the file and holds a PASS verdict signed at or after its mtime, or None
    with the reason each listing round failed to qualify.
    """
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    listed_by = [vid for vid in ids if name in _listed_files(artifact_map.get(vid))]
    blockers = []
    for vid in listed_by:
        record = verdicts.get(vid)
        if record is None:
            blockers.append(f"{vid} lists it but has no verdict file")
            continue
        state = str(record.get("verdict", "")).strip().upper()
        if state != "PASS":
            blockers.append(f"{vid} lists it but its verdict is "
                            f"{state or 'missing the verdict field'}")
            continue
        stamp = _signed_at(record)
        if stamp is None:
            blockers.append(f"{vid} lists it and is PASS but carries no usable ts")
        elif stamp < mtime:
            blockers.append(f"{vid} is PASS but signed {stamp.isoformat()}, before this "
                            f"text's mtime {mtime.isoformat()}")
        else:
            return vid, listed_by, []
    return None, listed_by, blockers


def check_evo_protected_assets(evo_dir):
    """A rule-evolution card must not quietly rewrite the system that judges it.

    Adopted from two independent sources (EVO-20261010-003): AgentDescent states
    the principle outright -- "a self-modifying system must not be able to replace
    its own evaluator" -- and DarwinAgent encodes it as an "asset boundary" that
    fails closed. reef does it with a field: its commit record only admits
    `training / rollback / promote`, and rollback/promote must carry a target id
    while training must not. The common form is **structural, not aspirational**:
    the rule about what may not change lives in a schema, not in a paragraph.

    Detection is by DECLARATION, not by keyword-scraping prose. The first draft
    matched protected names as substrings across `owned_files` and the json-dumped
    `proposed_change`, and it produced three false positives on the existing
    corpus, every one of them a card that was *protecting* the asset:

        "高风险文件（gate.yml、lint_cards.py、gate.py...）不进白名单"
        "不改 gate.py（评审明确禁区）"
        "状态机补旁路"

    A keyword scan cannot tell "I will change X" from "I will not change X", so it
    punished the stronger a card's protection language, the harder it fired. That
    inversion is disqualifying: the check must read what a card DECLARES it will
    touch. So a card lists `protected_assets_targeted` explicitly, and only that
    list is judged.

    A card that targets any protected asset is an ERROR unless it also carries
    both `protected_assets_changes` (naming the asset and the reason) and
    `sir_approval`. That pair is the legitimate escalation path -- discipline-level
    changes are sir's call, not something a card can grant itself.

    Deliberately not checked: prose in `proposed_change`. A card is free to
    discuss, cite or forbid gate.py without declaring that it intends to modify
    it; only the declaration is load-bearing.
    """
    out = []
    if not evo_dir or not Path(evo_dir).is_dir():
        return out

    # The five assets sir approved (EVO-20261010-003). A card names them in
    # `protected_assets_targeted`; anything else is not this rule's business.
    PROTECTED = (
        "verdict 模板与字段语义",
        "EVO 状态机定义",
        "AgnesCode 评审员资格",
        "sir 终裁权",
        "gate.py 判定逻辑",
    )

    for path in sorted(Path(evo_dir).glob("EVO-*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            out.append(_finding("EVO_UNREADABLE", "ERROR", path, f"cannot read EVO card: {exc}"))
            continue
        if not isinstance(data, dict):
            continue

        targeted = data.get("protected_assets_targeted") or []
        if isinstance(targeted, str):
            targeted = [targeted]
        # Only names that are actually on the list count; an unknown string is a
        # typo, not a boundary crossing, and is reported as such.
        unknown = [t for t in targeted if t not in PROTECTED]
        hit = [t for t in targeted if t in PROTECTED]
        if unknown:
            out.append(_finding(
                "EVO_PROTECTED_ASSET_UNKNOWN", "WARN", path,
                f"protected_assets_targeted names {unknown}, which is not one of the "
                f"protected assets {list(PROTECTED)} -- check for a typo"))
        if not hit:
            continue

        changes = data.get("protected_assets_changes")
        approval = data.get("sir_approval")
        if changes and approval:
            out.append(_finding(
                "EVO_PROTECTED_ASSET_TOUCHED", "WARN", path,
                f"targets protected asset(s) {hit} but declares "
                "protected_assets_changes + sir_approval -- allowed as an explicit "
                "discipline-level change, recorded for audit"))
        else:
            out.append(_finding(
                "EVO_PROTECTED_ASSET_TOUCHED", "ERROR", path,
                f"targets protected asset(s) {hit} without both "
                "protected_assets_changes and sir_approval. A rule-evolution card "
                "may not rewrite the system that judges it: escalate explicitly "
                "(discipline-level change is sir's call), do not self-grant."))
    return out


def check_card_self_in_map(artifact_map, card_dir=None):
    """A round must not list its own card as a judged artifact (EVO-20261010-001).

    The freshness rule compares each listed artifact's mtime against the round's
    verdict timestamp. A card's own file is edited as part of *closing it*
    (IN_REVIEW -> CLOSED, recording the verdict and the reviewed commit), and
    that edit necessarily happens after the verdict. So listing the card makes
    the round stale by definition the moment the round finishes -- and since no
    later round revisits a closed card, nothing ever supersedes it. The finding
    is permanent and useless, which is worse than noise: it hides real staleness
    among findings nobody can act on.

    The list should equal what the reviewer read. A reviewer reads the code, the
    docs and the evidence; the card is the record *of* the review, not an input
    to it.

    WARN, not ERROR: seven existing rounds carry this pattern and the repository
    gate already tolerates some of them living red. This rule is here to stop the
    habit spreading, not to demand a sweep nobody scheduled.
    """
    out = []
    for vid in sorted(artifact_map):
        if vid.startswith("_"):
            continue
        # Archived cards are historical records; their self-listing is a
        # consequence of being captured at creation time, not a live defect.
        if card_dir is not None and (card_dir / "legacy" / f"{vid}.md").exists():
            continue
        # `_listed_files` already normalises (strip + backslashes + leading "./"),
        # and `lstrip("./")` eats the leading dot of ".tasks/..." too -- so the
        # comparison string is normalised the same way rather than re-stripped.
        self_path = _listed_files([f".tasks/{vid}.md"]).pop()
        if self_path in _listed_files(artifact_map.get(vid)):
            out.append(_finding(
                "CARD_SELF_IN_MAP", "WARN", Path("artifacts.json"),
                f"{vid} lists its own card '.tasks/{vid}.md' as a judged artifact - "
                "closing the card then makes its own verdict stale, permanently "
                "(no later round revisits a closed card). List what the reviewer "
                "read, not the card that records the review (EVO-20261010-001)."))
    return out


def check_unmapped_claim_surface(project_root, artifact_map, verdict_dir=None):
    """The claim surface needs a *current PASS signature*, or freshness skips it.

    README.md is still listed in the v0.1.0 maps, so a "is it mapped anywhere"
    check would have stayed green for the entire drift: the file was mapped, just
    not by any round recent enough to be reviewing today's text.

    This rule used to approximate "recent enough" with *round identity* — the
    newest id has to list the file — and round 013 is what proved the
    approximation wrong. A listing is not a signature. 013 listed both READMEs
    without ever editing them (`0aec1f9` is CHANGELOG.md alone; `39d3229` is the
    card plus CHANGELOG.md), and the gate retired `XJ-20260929-001`'s staleness on
    both, so the fiction retired a real finding. Nothing forced that round to be
    dishonest: `current = ids[-1]` demanded the listing, so a ledger-only round
    either attested to files it never read or took the WARN. The same rule let 014
    list those two files honestly, because 014 had actually edited them —
    compliance was a function of coincidence, which is not a check.

    So coverage asks about signatures instead of ids: does any round that lists
    this file hold a verdict that is PASS *and* signed at or after the file's
    current mtime? FAIL holds nothing, and neither does a PASS that predates the
    text it would be vouching for. Where a project has no verdicts at all there
    is no signature to read, and the rule degrades to the old newest-id
    comparison rather than inventing a baseline.
    """
    out = []
    if artifact_map is None:
        return out
    ids = [key for key in artifact_map if not key.startswith("_")]
    if not ids:
        return out
    # The map is append-ordered by convention (oldest id first); the last id is
    # the round whose reading is supposed to be current.
    current = ids[-1]
    verdicts = _verdict_index(verdict_dir)
    for name in CLAIM_SURFACE_FILES:
        path = project_root / name
        if not path.is_file():
            continue
        if verdicts:
            holder, listed_by, blockers = _claim_state(name, path, artifact_map, ids, verdicts)
            if holder is not None:
                continue
            claimed = ", ".join(listed_by) if listed_by else "no round in the map lists it"
            out.append(_finding("UNMAPPED_CLAIM_SURFACE", "WARN", path,
                                f"no current PASS signature covers it — {claimed}, and "
                                f"{'; '.join(blockers) if blockers else 'nothing has signed for it'}. "
                                "A listing retires a staleness only once a PASS verdict signed "
                                "at or after the file's mtime stands behind it"))
            continue
        if name not in _listed_files(artifact_map.get(current)):
            out.append(_finding("UNMAPPED_CLAIM_SURFACE", "WARN", path,
                                f"not listed in {current}, the newest id in artifacts.json, so "
                                "no freshness check covers it - list it under that id. No verdict "
                                "files exist, so this is the degraded newest-id comparison, not "
                                "a signature check"))
    return out


def _owned_files(text):
    """Extract declared file ownership from the card's 'Owned files' section.

    A card declares what it owns exclusively; two active cards claiming the same
    path is the planning-stage form of the lost-update hazard that no runtime lock
    can retroactively fix (PROTOCOL.md R2, postmortems PM-5).
    """
    body = _section_body(text, ("owned files", "归属文件", "负责文件"))
    if not body.strip():
        return []
    owned = []
    for line in body.splitlines():
        entry = line.strip().lstrip("-*+").strip()
        entry = entry.lstrip("[]").lstrip("xX ").strip()
        if not entry or entry.startswith(("<", "{")):
            continue  # template placeholder, not a real claim
        owned.append(entry)
    return owned


def _looks_like_path(entry):
    """Is this Owned-files line actually a path, or prose that drifted in?

    `_owned_files` returns whatever sits on a line in the section, and on the
    real corpus that includes constraint sentences: a card whose section reads
    "不要** `tools/lint_cards.py`、`tests/test_lint_cards.py`、`PROTOCOL.md`、"
    yields a "claim" that is a prohibition, not an ownership declaration. Those
    pseudo-claims then collide with each other through `_paths_overlap`, because
    the sentence happens to name files another card also names.

    The measurable consequence (EVO-20261010-002): `OWNED_FILES_CONFLICT`
    reported 132 findings where same-rule recomputation over path-shaped entries
    finds 5 real ones -- about 96% noise, and it is the only ERROR-level blocker
    under `--strict`, so the noise was hiding real conflicts.

    Accepted shapes:
      * a file: one token containing a dot and a short alphanumeric extension
        (``tools/gate.py``, ``README.md``, ``verdicts/X.verdict.json``)
      * a directory claim: a token ending in ``/`` (templates/TASK.md states a
        directory claim owns everything beneath it, so this MUST stay legal)
      * any token containing a path separator, once backticks/quotes/backslashes
        are stripped (``agent-os/**``, ``docs/lint-rules.md``)

    Rejected: sentences, prose with spaces, prohibitions, bullet text. The test
    is deliberately permissive about *shape* and silent about *meaning* -- it
    cannot know whether a well-formed path belongs to the card, and pretending
    otherwise would just move the false positives.
    """
    token = entry.strip().strip("`'\"").strip()
    if not token or " " in token or "\t" in token:
        return False  # a sentence, not a token
    if token.endswith("/"):
        return True  # directory claim -- explicitly legal here
    if "/" in token or "\\" in token:
        return True
    # A bare filename needs an extension; "CHANGELOG.md" yes, "本卡" no.
    return bool(re.match(r"^[^/\\]+\.[A-Za-z0-9]{1,8}$", token))


def _owned_paths(text):
    """The subset of `_owned_files(text)` that is shaped like a path."""
    return [entry for entry in _owned_files(text) if _looks_like_path(entry)]


def check_owned_files_nonpath(claims):
    """Report Owned-files lines that are not paths, instead of silently dropping.

    Silently filtering them would repeat the defect class this repository keeps
    post-morteming: a check that stops looking while still reporting success. If
    a card's Owned files section contains prose, the author (or a later reader)
    should be told, because the section is machine-read and the prose is doing
    nothing but generating collision noise.

    `claims` is a list of ``(filename, [raw entries])`` for active cards.
    """
    out = []
    for name, entries in claims:
        for entry in entries:
            if not _looks_like_path(entry):
                out.append(_finding(
                    "OWNED_FILES_NONPATH", "WARN", Path(name),
                    f"line {entry!r} sits in the Owned files section but is not a "
                    "path -- it will not be treated as a claim (it was generating "
                    "false OWNED_FILES_CONFLICT noise). Move constraints prose to "
                    "the Constraints section, or write the path on its own line."))
    return out


def _is_active(card_text):
    status = _section_body(card_text, ("status", "状态")).strip().upper()
    if not status:
        return True  # no status = still open
    for closed in ("CLOSED", "GATED", "已归档", "已完成", "已通过"):
        if closed in status:
            return False
    return True


def check_status_drift(card_dir, verdict_dir):
    """WARN when a card advertises an open state it has already grown out of.

    Drift means: `## Status` carries no closed marker (CLOSED / GATED / etc.)
    while `verdicts/<id>.verdict.json` records PASS. This is not cosmetic.
    `_is_active` decides whether a card's owned-files claims take part in
    conflict detection, so a drifted card holds its files forever -- and every
    later card touching the same file collides with it. That is how the three
    OWNED_FILES_CONFLICT findings of XJ-20261013-002 pointed at the innocent new
    card while XJ-20261004-006, PASS since 2026-10-05, quietly kept the claim.

    Seven cards drifted this way and none of them were written that way on
    purpose: two wrote prose ("Awaiting independent review.") with no state
    token at all. A fix that only matched the enum values would have found five
    of the seven, so this rule deliberately reuses `_is_active` -- an open state
    is whatever `_is_active` considers open, which already covers prose.

    WARN, not ERROR: a wrong status does not itself damage the evidence chain,
    and ERROR would trap a repo mid-correction. AgnesCode ruled the level on
    XJ-20261013-003: earn ERROR after a clean WARN record.
    """
    out = []
    if not card_dir or not card_dir.is_dir():
        return out
    verdicts = {}
    if verdict_dir and verdict_dir.is_dir():
        for path in verdict_dir.glob(f"*{VERDICT_SUFFIX}"):
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
            except Exception:  # noqa: BLE001 - schema check reports unreadable verdicts
                continue
            verdicts[path.name[:-len(VERDICT_SUFFIX)]] = data
    for path in sorted(card_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if not _is_active(text):
            continue
        verdict = verdicts.get(path.stem)
        if not verdict:
            continue
        if str(verdict.get("verdict", "")).upper() != "PASS":
            continue
        ts = verdict.get("ts") or "unknown date"
        out.append(_finding("STATUS_DRIFT", "WARN", path,
                            f"Status still reads as open but verdicts/{path.stem}"
                            f"{VERDICT_SUFFIX} is PASS (signed {ts}). A drifted card "
                            "stays active and keeps holding its owned files; "
                            "realign it or archive it."))
    return out


def check_link_not_stamped(project_root, verdict_dir):
    """WARN when a verdict exists on disk but its snapshot link was never stamped.

    Phase 1+2 built the link contract: `deepfreeze protect --card` writes a snap
    link, and `link_card.py` stamps the verdict group (`verdict_sha256`,
    `verdict_ts`) back into it. `gate.check_links` reads a link with *no* verdict
    group as "snapshot taken, verdict not written yet" and passes silently -- the
    right reading while the review is pending, and the wrong one once
    `verdicts/<id>.verdict.json` is sitting right there with nobody having run
    link_card. The chain then looks intact while it is severed, and the gate
    cannot tell the difference (AgnesCode RQ2, EVO-20261020-001).

    The gate deliberately does not warn here (a gate has no link-directory
    semantics it is willing to make default-on); the linter is where a "smells
    wrong" signal belongs. WARN, not ERROR: an unstamped link blocks nothing
    today, it just leaves a signed verdict unlinked.

    Scoped to the *linted* project (`<card-dir>/..`), like the other rules that
    read a project's own files: running the linter against a scratch tree must
    not consult this repository's `.freeze/`. When the project has no `.freeze/`
    the whole rule is off -- zero cost, and the gate's own opt-in posture mirrored.
    """
    out = []
    if not verdict_dir or not verdict_dir.is_dir():
        return out
    freeze_dir = project_root / FREEZE_DIRNAME
    if not freeze_dir.is_dir():
        return out  # no snapshot facility in this project: rule not enabled
    for path in sorted(verdict_dir.glob(f"*{VERDICT_SUFFIX}")):
        vid = path.name[: -len(VERDICT_SUFFIX)]
        link_path = freeze_dir / f"{LINK_PREFIX}{vid}.json"
        if not link_path.is_file():
            continue
        try:
            link = json.loads(link_path.read_text(encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001 - a bad link is gate's LINK_UNREADABLE, not ours
            continue
        if not isinstance(link, dict):
            continue
        if "verdict_sha256" in link:
            continue  # stamped: the link points at this verdict's bytes
        out.append(_finding(
            "LINK_NOT_STAMPED", "WARN", Path(f"{vid}{VERDICT_SUFFIX}"),
            f"{freeze_dir.name}/{link_path.name} exists but carries no "
            f"verdict_sha256: the verdict was signed but never linked, so the "
            f"traceability chain reads intact while it is severed. Stamp it: "
            f"python tools/link_card.py --card {vid} --verdict "
            f"{verdict_dir.name}/{path.name}"))
    return out


def _paths_overlap(left, right):
    """Heuristic overlap test: equality, directory containment, or glob prefix."""
    a = left.strip().strip("/\\").replace("\\", "/")
    b = right.strip().strip("/\\").replace("\\", "/")
    if not a or not b:
        return False
    if a == b:
        return True
    a_star, b_star = "*" in a, "*" in b
    if a_star or b_star:
        literal = (a if a_star else b).split("*")[0]
        other = (b if b_star else a)
        return bool(literal) and other.startswith(literal)
    # A bare directory claim ("tools") owns everything under it.
    return a.startswith(b + "/") or b.startswith(a + "/")


def check_owned_files_quality(path, text):
    """A claim surface that cannot constrain anything is not a claim.

    `OWNED_FILES_CONFLICT` only fires when two active cards overlap; a card that
    claims nothing, or claims `**`, passes every other rule while making the
    whole ownership model decorative. These two rules close that hole at
    planning time, which is the only place cheap enough to fix it.

    Both are WARN on purpose: CI runs this linter with `--strict`, so promoting
    them to ERROR is a gate, and a gate should not be opened before the current
    corpus is measured (EVO-20261007-001 shadow period). Note the asymmetry with
    the whitelist: a *directory* claim is legitimate here — templates/TASK.md
    states a directory claim owns everything beneath it — so only `**` and
    root-ish declarations are too broad for a card.
    """
    out = []
    owned = _owned_files(text)
    if not owned:
        out.append(_finding(
            "OWNED_FILES_EMPTY", "WARN", path,
            "active card declares no owned files, so ownership enforcement has "
            "nothing to check (PROTOCOL.md R2)"))
        return out
    for entry in owned:
        candidate = entry.strip().strip("/\\").replace("\\", "/")
        if "**" in entry or candidate in ("", ".", "/", "*"):
            out.append(_finding(
                "OWNED_FILES_TOO_BROAD", "WARN", path,
                f"owned-files entry {entry!r} is too broad to constrain anything; "
                "declare concrete paths (a directory claim is allowed, `**` is not)"))
    return out


def check_owned_files_conflicts(claims):
    """claims: list of (filename, [owned paths]) for active cards only."""
    out = []
    for i, (name_a, paths_a) in enumerate(claims):
        for name_b, paths_b in claims[i + 1:]:
            for path_a in paths_a:
                for path_b in paths_b:
                    if _paths_overlap(path_a, path_b):
                        out.append(_finding(
                            "OWNED_FILES_CONFLICT", "WARN", Path(name_a),
                            f"'{path_a}' is also claimed by {name_b} as '{path_b}' — two active "
                            "cards must not own the same file (PROTOCOL.md R2)"))
    return out


def _legacy_card_ids(card_dir):
    """Card ids parked in <dir>/legacy - evidence, not linted, but still paired.

    Any namespaced id found in a legacy filename counts, including review cards
    (`REVIEW-XJ-20260930-004.md`) - a verdict's counterpart is the review card as
    often as the task card.
    """
    legacy_dir = card_dir / "legacy"
    if not legacy_dir.is_dir():
        return set()
    ids = set()
    for path in legacy_dir.glob("*.md"):
        match = ID_IN_NAME_RE.search(path.name)
        if match:
            ids.add(match.group(1))
    return ids


def _evo_card_ids(evo_dir):
    """Ids of EVO rule cards, which live outside the card directory.

    These are `_handoffs/evo/EVO-*.json` rather than Markdown cards under
    `.tasks/`, so pairing never saw them. Only used to stop their verdicts being
    reported as orphans -- see check_verdict_pairs for why it stops there.
    """
    if not evo_dir:
        return set()
    directory = Path(evo_dir)
    if not directory.is_dir():
        return set()
    return {path.stem for path in directory.glob("EVO-*.json")}


def lint_card_dir(card_dir):
    findings = []
    card_ids = set()
    claims = []
    # Path-shaped claims only: the overlap rule compares paths, and feeding it
    # constraint prose produced ~96% false positives (EVO-20261010-002).
    path_claims = []
    for path in sorted(card_dir.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            findings.append(_finding("UNREADABLE_CARD", "ERROR", path, f"cannot read: {exc}"))
            continue
        kind = classify(path)
        if NAMESPACE_RE.match(path.name):
            card_ids.add(path.stem)
        findings += check_namespace(path, text)
        findings += check_bare_task_refs(path, text)
        if kind == "review":
            findings += check_review_card(path, text)
        elif kind == "task":
            findings += check_task_card(path, text)
        if _is_active(text):
            owned = _owned_files(text)
            if owned:
                claims.append((path.name, owned))
                # Only path-shaped entries take part in the overlap check; every
                # non-path entry is reported regardless of whether the card also
                # has valid paths, so prose cannot hide behind a well-formed line
                # (EVO-20261010-002: such prose was ~96% of the conflict noise).
                paths = _owned_paths(text)
                if paths:
                    path_claims.append((path.name, paths))
                rejected = [entry for entry in owned if not _looks_like_path(entry)]
                if rejected:
                    findings += check_owned_files_nonpath([(path.name, rejected)])
            if kind == "task":
                findings += check_owned_files_quality(path, text)
        if not path.name.isascii():
            findings.append(_finding("NON_ASCII_FILENAME", "WARN", path,
                                    "non-ASCII filename — breaks tooling on some platforms"))
    findings += check_owned_files_conflicts(path_claims)
    return findings, card_ids


UNBLOCKS_RE = re.compile(r"^[A-Z]+-\d{8}-\d{3}\.[A-Za-z]\d+$")


def _unblocks_problems(vid, value):
    """Shape checks for a verdict's `unblocks` field (ADR-0002 R1/R2).

    Returns a list of human-readable problem strings, [] when well-formed.
    Deliberately does NOT verify that the referenced condition exists: condition
    ids are free-text prefixes in practice (XJ-20261003-001's is "C1: PROTOCOL.md
    ...", XJ-20261004-004's is "C1 (B1, from Q2): ..."), so existence cannot be
    established without parsing prose. Shape and self-reference are checkable;
    existence is ADR-0002's Revisit-trigger item 2.
    """
    problems = []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        return [f"unblocks: must be a string or list of strings (got {type(value).__name__})"]
    if not items:
        return ["unblocks: must not be empty"]
    for item in items:
        if not isinstance(item, str) or not item.strip():
            problems.append(f"unblocks: every entry must be a non-empty string (got {item!r})")
            continue
        if not UNBLOCKS_RE.match(item):
            problems.append(
                f"unblocks: {item!r} is not of the form <NS>-YYYYMMDD-NNN.<condition> "
                "(e.g. XJ-20261004-004.C1)"
            )
            continue
        if item.split(".", 1)[0] == vid:
            problems.append(
                f"unblocks: {item!r} references its own id; a verdict cannot discharge "
                "a condition of the card it judges (ADR-0002 R1)"
            )
    return problems


def check_verdict_schema(verdict_dir, skipped=False):
    """Validate every verdict file against gate.py's schema contract.

    A legal verdict JSON may still violate gate.py's required fields (id,
    verdict, blockers, independent, verifier, ts, evidence). This check
    reuses gate.py's load_verdict and per-field validators so lint and
    gate never drift. Findings are ERROR level - a verdict the gate can't
    read is not a verdict at all.

    Added per DFB-20261003-007 (deepfreeze) after two rounds of cards
    shipped with schema-violating verdicts; the legacy_schema branch only
    hid the drift from lint, not from gate.

    Converged in the XJ-20261003-002 review of b754ae4:
    * the shadow VALID_VERDICTS tuple was dead code - verdict values were
      already validated by gate._check_verdict_value against gate's single
      source, so the local copy "looked like a check" but editing it changed
      nothing. Removed, with a regression test that fails on reintroduction.
    * ts was only checked for parseability while gate.py rejects future-dated
      timestamps; the "lint and gate never drift" claim was already broken.
      Now reuses gate._check_timestamp_plausibility, so a future ts is
      rejected by lint too. LINT_MAX_CLOCK_SKEW mirrors gate's default.
    """
    out = []
    if skipped:
        # Kept pure on purpose: main() emits the visible NOTICE and the
        # JSON payload carries one too. A check that can be switched off and
        # leave no trace is not a check.
        return out
    if verdict_dir is None or not Path(verdict_dir).is_dir():
        return out
    try:
        import importlib.util as _ilu
        _gate_path = Path(__file__).resolve().parent / "gate.py"
        _spec = _ilu.spec_from_file_location("_gate_module", _gate_path)
        _gate = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_gate)
        load_verdict = _gate.load_verdict
        _check_fields = _gate._check_fields
        _check_verdict_value = _gate._check_verdict_value
        _check_blockers = _gate._check_blockers
        _check_evidence = _gate._check_evidence
        parse_ts = _gate.parse_ts
        _check_ts_plausibility = _gate._check_timestamp_plausibility
    except Exception as exc:  # noqa: BLE001 - reported as a finding below
        out.append(_finding("VERDICT_SCHEMA_GATE_IMPORT", "ERROR",
                            Path(verdict_dir),
                            f"could not import gate.py helpers ({exc}); "
                            "verdict schema check skipped"))
        return out
    for path in sorted(Path(verdict_dir).glob(f"*{VERDICT_SUFFIX}")):
        vid = path.name[: -len(VERDICT_SUFFIX)]
        data, err_code, err_detail = load_verdict(Path(verdict_dir), vid)
        if err_code:
            out.append(_finding("VERDICT_SCHEMA_NONCOMPLIANT", "ERROR",
                                path, f"{err_code}: {err_detail}"))
            continue
        # Reuse gate's per-field validators; accumulate all violations so
        # one bad verdict does not hide another.
        problems = []
        for code, msg in _check_fields(vid, data):
            problems.append(f"field: {msg}")
        norm_v, v_problems = _check_verdict_value(data)
        problems.extend(f"verdict: {m}" for _, m in v_problems)
        if norm_v is not None:
            b_problems = _check_blockers(data, norm_v)
            problems.extend(f"blockers: {m}" for _, m in b_problems)
        # _check_evidence returns a list of (code, msg); only flag negatives
        e_problems = _check_evidence(data)
        if e_problems:
            problems.extend(f"evidence: {m}" for _, m in e_problems)
        # ts must be present, non-empty, and ISO-8601 parseable
        ts_raw = data.get("ts")
        if not ts_raw or not isinstance(ts_raw, str):
            problems.append(f"ts: missing or not a string (got {ts_raw!r})")
        else:
            try:
                parse_ts(ts_raw)
            except Exception:  # noqa: BLE001 - report as a finding
                problems.append(f"ts: not ISO-8601 parseable (got {ts_raw!r})")
        # A future-dated ts can never go stale, so it silently defeats the
        # gate's freshness rule. gate.py has this check; reusing it is what
        # actually keeps "lint and gate never drift" true (XJ-20261003-002 fix).
        # Lint has no --max-clock-skew flag; LINT_MAX_CLOCK_SKEW mirrors
        # gate's default so the two cannot diverge.
        problems.extend(
            f"ts: {msg}" for _code, msg in _check_ts_plausibility(data, LINT_MAX_CLOCK_SKEW)
        )
        # independent should be true (no --allow-nonindependent in lint)
        if data.get("independent") is not True:
            problems.append(f"independent: must be true (got {data.get('independent')!r})")
        # ADR-0002 R3: a self-signed verdict is not an independent authority.
        # Lint has no --allow-nonindependent flag, so it is strict by design.
        if data.get("self_signed") is True:
            if data.get("independent") is True:
                problems.append(
                    "self_signed: true together with independent: true is a "
                    "contradiction (ADR-0002 R3)"
                )
            else:
                problems.append(
                    "self_signed: true; a self-signed verdict is not an "
                    "independent authority (ADR-0002 R3)"
                )
        # ADR-0002 R1/R2: `unblocks` carries a resolution reference and must be
        # well-formed. Lint cannot verify that the referenced condition exists -
        # condition ids are free-text prefixes in practice ("C1", but also
        # "C1 (B1, from Q2)") - so this checks shape and self-reference only.
        if "unblocks" in data:
            problems.extend(_unblocks_problems(vid, data.get("unblocks")))
        if problems:
            out.append(_finding("VERDICT_SCHEMA_NONCOMPLIANT", "ERROR",
                                path,
                                f"{vid}: " + "; ".join(problems)))
    return out


def build_parser():
    parser = argparse.ArgumentParser(
        prog="lint_cards.py",
        description="Lint collaboration cards against PROTOCOL.md §4 and §7.",
    )
    parser.add_argument("--dir", required=True, help="directory containing card markdown files")
    parser.add_argument("--verdict-dir", default=None,
                        help="verdict directory (default: <dir>/../verdicts)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument("--no-verdict-schema", action="store_true",
                        help="skip the verdict schema check (only useful for "
                             "tests that intentionally use empty verdict stubs). "
                             "Always prints a NOTICE that the check was bypassed, so a "
                             "skipped run cannot masquerade as a full one.")
    parser.add_argument("--artifact-map", default=None,
                        help="artifacts.json to check the public claim surface against; "
                             "defaults to ./artifacts.json when that file exists "
                             "(neither flag nor file = check not enabled)")
    parser.add_argument("--evo-dir", default=None,
                        help="directory of EVO rule-evolution cards (EVO-*.json) to "
                             "check the protected-asset boundary against; neither "
                             "flag nor directory = check not enabled")
    parser.add_argument("--allow-orphan-id", action="append", default=[], metavar="ID",
                        help="orphan verdicts for these ids downgrade to NOTICE (visible, "
                             "not a failure); unknown orphan ids still warn and fail --strict")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON findings")
    parser.add_argument("--quiet", action="store_true", help="suppress output; use the exit code")
    return parser


def check_subprocess_text_no_encoding(project_root):
    """ERROR when a tools/ call decodes subprocess output with the ambient locale.

    ``subprocess.run(..., text=True)`` without ``encoding=`` decodes the child's
    bytes with the *caller's* preferred locale. On a cp936/GBK console that
    mangles (or, for strict codecs, kills) any non-ASCII output -- and this repo
    prints CJK violation text from both gate.py and lint_cards.py.

    Measured (XJ-20261024-003): ``tools/eval/m3_probe.py`` did exactly this and
    died with ``UnicodeDecodeError`` before it could parse ``--json``, so the
    whole probe returned nothing on a GBK machine while passing on a UTF-8 one.
    AgnesCode isolated the root cause and scanned every subprocess call site in
    tools/**; this rule is the guard so the class cannot come back.

    ERROR, not WARN: the failure is silent on the developer's machine (their
    locale hides it) and loud only for whoever reproduces the work -- precisely
    the kind of defect that needs to fail at the door.

    Exempt with a trailing ``# noqa: SUBPROCESS_TEXT_NO_ENCODING`` when the
    decode genuinely happens elsewhere (caller passes bytes on purpose).

    Scope: ``<project>/tools/**/*.py`` only. Not a general codebase policy --
    the argument is about this repo's own tooling, and widening the scope is how
    a guard turns into noise.
    """
    out = []
    tools_dir = project_root / "tools"
    if not tools_dir.is_dir():
        return out  # project without a tools/ tree: rule not enabled

    subprocess_callees = {"run", "call", "check_call", "check_output", "Popen", "popen"}
    for path in sorted(tools_dir.rglob("*.py")):
        try:
            # utf-8-sig, not utf-8: a BOM is legal in Python source but makes
            # ast.parse raise, and a skipped file is a silently unguarded file
            # (measured while testing this rule -- the first injected sample was
            # written by PowerShell, which prepends a BOM).
            source = path.read_text(encoding="utf-8-sig", errors="replace")
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue  # a file that does not parse is somebody else's finding
        lines = source.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            callee = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if callee not in subprocess_callees:
                continue
            keywords = {kw.arg for kw in node.keywords if kw.arg}
            text_mode = "text" in keywords or "universal_newlines" in keywords
            if not text_mode or "encoding" in keywords:
                continue
            start = getattr(node, "lineno", 1)
            end = getattr(node, "end_lineno", start) or start
            # Exemption window: the call's own lines plus the line immediately
            # above it. A multi-line call naturally carries its noqa on the
            # preceding comment line (measured: without the lookback the
            # documented exemption did not work).
            span = "\n".join(lines[max(0, start - 2): end])
            if "SUBPROCESS_TEXT_NO_ENCODING" in span:
                continue  # explicit # noqa
            out.append(_finding(
                "SUBPROCESS_TEXT_NO_ENCODING", "ERROR", path, 
                f"{callee}(...) uses text=True without encoding=: the child's bytes "
                f"are decoded with the caller's locale, so non-ASCII output either "
                f"mangles or raises UnicodeDecodeError depending on the machine. Pass "
                f'encoding="utf-8", errors="replace" (or add '
                f"`# noqa: SUBPROCESS_TEXT_NO_ENCODING` if bytes are intended)", line=start))
    return out


def main(argv=None):
    _safe_utf8()
    args = build_parser().parse_args(argv)
    card_dir = Path(args.dir)
    if not card_dir.is_dir():
        print(f"[USAGE] card directory not found: {card_dir}", file=sys.stderr)
        return EXIT_USAGE
    verdict_dir = Path(args.verdict_dir) if args.verdict_dir else card_dir.parent / "verdicts"

    findings, card_ids = lint_card_dir(card_dir)
    # Cards parked in legacy/ are evidence, not linted - but they still exist, so
    # their verdicts are neither orphaned nor missing.
    findings += check_verdict_pairs(card_ids | _legacy_card_ids(card_dir), verdict_dir,
                                    extra_known_ids=_evo_card_ids(args.evo_dir),
                                    allow_orphan_ids=getattr(args, "allow_orphan_id", []))
    findings += check_status_drift(card_dir, verdict_dir)
    if not getattr(args, "no_verdict_schema", False):
        findings += check_verdict_schema(verdict_dir, skipped=args.no_verdict_schema)

    # Prose is part of the deliverable too: a README can lie, and a README nobody
    # re-checks lies forever. Both rules read the project the cards belong to.
    project_root = _project_root(card_dir)
    # A check that only runs when a flag is remembered is a check that will be
    # forgotten (PM-10). When the map is simply sitting there, use it. Only a
    # project that has no map at all is genuinely out of scope.
    map_path = args.artifact_map
    if map_path is None and (project_root / "artifacts.json").is_file():
        map_path = str(project_root / "artifacts.json")
    artifact_map = None
    if map_path:
        try:
            artifact_map = load_artifact_map(map_path)
        except ValueError as exc:
            print(f"[USAGE] {exc}", file=sys.stderr)
            return EXIT_USAGE
    findings += check_stale_test_count(project_root)
    findings += check_subprocess_text_no_encoding(project_root)
    findings += check_evo_protected_assets(args.evo_dir)
    findings += check_link_not_stamped(project_root, verdict_dir)
    findings += check_unmapped_claim_surface(project_root, artifact_map, verdict_dir)
    if artifact_map is not None:
        findings += check_card_self_in_map(artifact_map, card_dir)

    errors = sum(1 for f in findings if f["level"] == "ERROR")
    warnings = sum(1 for f in findings if f["level"] == "WARN")
    failed = errors > 0 or (args.strict and warnings > 0)

    if args.as_json:
        payload = {"ok": not failed, "errors": errors, "warnings": warnings,
                  "findings": findings}
        if args.no_verdict_schema and verdict_dir.is_dir():
            payload["notices"] = [
                "verdict schema check SKIPPED (--no-verdict-schema); verdicts NOT "
                "validated against gate.py's contract; lint and gate may disagree"]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif not args.quiet:
        for item in findings:
            location = f"{item['file']}:{item['line']}" if item["line"] else item["file"]
            print(f"[{item['level']}] {item['rule']} {location}: {item['detail']}")
        if args.no_verdict_schema and verdict_dir.is_dir():
            # A check that can be turned off must leave a visible trace, or a
            # forgotten flag silently downgrades the run and still reports PASS.
            n = len(list(verdict_dir.glob("*" + VERDICT_SUFFIX)))
            print("[NOTICE] verdict schema check SKIPPED (--no-verdict-schema): " +
                  str(n) + " verdict file(s) NOT validated against gate.py's contract;"
                  " lint and gate may disagree")
        if failed:
            print(f"LINT: FAIL ({errors} errors, {warnings} warnings)")
        else:
            print(f"LINT: PASS ({warnings} warnings)")
    return EXIT_ERROR if failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
