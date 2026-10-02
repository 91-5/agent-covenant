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
import json
import re
import sys
import unittest
from datetime import datetime, timezone
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
TEST_COUNT_RES = (
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


def _has_section(sections, key):
    aliases = TASK_SECTION_ALIASES.get(key, (key,))
    return any(any(alias in name for alias in aliases) for name in sections)


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
    if not any("blocker" in name or "阻塞" in name for name in sections):
        out.append(_finding("REVIEW_MISSING_BLOCKERS", "ERROR", path,
                            "no '## Blockers' section (state the count, even if zero)"))
    return out


def _section_body(text, header_names):
    """Return the text under the first H2 whose header matches one of header_names.

    A status word lives in the body, not in the header line, so a single-line scan
    silently misses it.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
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


def check_verdict_pairs(card_ids, verdict_dir):
    out = []
    if not verdict_dir or not verdict_dir.is_dir():
        return out
    verdict_ids = {p.name[: -len(VERDICT_SUFFIX)] for p in verdict_dir.glob(f"*{VERDICT_SUFFIX}")}
    for vid in sorted(verdict_ids - card_ids):
        out.append(_finding("ORPHAN_VERDICT", "WARN", Path(f"{vid}{VERDICT_SUFFIX}"),
                            "verdict has no matching card in the card directory"))
    for vid in sorted(card_ids - verdict_ids):
        out.append(_finding("VERDICT_WITHOUT_REVIEW", "WARN", Path(f"{vid}.md"),
                            "card has no machine-readable verdict file"))
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


def _is_active(card_text):
    status = _section_body(card_text, ("status", "状态")).strip().upper()
    if not status:
        return True  # no status = still open
    for closed in ("CLOSED", "GATED", "已归档", "已完成", "已通过"):
        if closed in status:
            return False
    return True


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


def lint_card_dir(card_dir):
    findings = []
    card_ids = set()
    claims = []
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
        if not path.name.isascii():
            findings.append(_finding("NON_ASCII_FILENAME", "WARN", path,
                                    "non-ASCII filename — breaks tooling on some platforms"))
    findings += check_owned_files_conflicts(claims)
    return findings, card_ids


def build_parser():
    parser = argparse.ArgumentParser(
        prog="lint_cards.py",
        description="Lint collaboration cards against PROTOCOL.md §4 and §7.",
    )
    parser.add_argument("--dir", required=True, help="directory containing card markdown files")
    parser.add_argument("--verdict-dir", default=None,
                        help="verdict directory (default: <dir>/../verdicts)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument("--artifact-map", default=None,
                        help="artifacts.json to check the public claim surface against; "
                             "defaults to ./artifacts.json when that file exists "
                             "(neither flag nor file = check not enabled)")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON findings")
    parser.add_argument("--quiet", action="store_true", help="suppress output; use the exit code")
    return parser


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
    findings += check_verdict_pairs(card_ids | _legacy_card_ids(card_dir), verdict_dir)

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
    findings += check_unmapped_claim_surface(project_root, artifact_map, verdict_dir)

    errors = sum(1 for f in findings if f["level"] == "ERROR")
    warnings = sum(1 for f in findings if f["level"] == "WARN")
    failed = errors > 0 or (args.strict and warnings > 0)

    if args.as_json:
        print(json.dumps({"ok": not failed, "errors": errors, "warnings": warnings,
                          "findings": findings}, ensure_ascii=False, indent=2))
    elif not args.quiet:
        for item in findings:
            location = f"{item['file']}:{item['line']}" if item["line"] else item["file"]
            print(f"[{item['level']}] {item['rule']} {location}: {item['detail']}")
        if failed:
            print(f"LINT: FAIL ({errors} errors, {warnings} warnings)")
        else:
            print(f"LINT: PASS ({warnings} warnings)")
    return EXIT_ERROR if failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
