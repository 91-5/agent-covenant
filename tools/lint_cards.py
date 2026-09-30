#!/usr/bin/env python3
"""agent-covenant lint-cards — schema and naming linter for collaboration cards.

Stdlib only. See PROTOCOL.md §4 (schemas) and §7 (naming rules N1/N2), and
docs/lint-rules.md for the rationale behind each rule.

Usage
-----
    python tools/lint_cards.py --dir .tasks
    python tools/lint_cards.py --dir .tasks --verdict-dir verdicts --strict
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
from pathlib import Path

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2

NAMESPACE_RE = re.compile(r"^([A-Z]{2,6})-\d{8}-\d{3}\.md$")
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
    if not NAMESPACE_RE.match(path.name) and not path.name.startswith(("REVIEW-", "HANDOFF-", "ADR-")):
        return [_finding("NAMESPACE_MISSING", "ERROR", path,
                         "filename must be <NS>-YYYYMMDD-NNN.md (PROTOCOL.md N1); "
                         f"got {path.name!r} — a bare name can be hijacked by another agent")]
    return []


def check_bare_task_refs(path, text):
    out = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in BARE_TASK_RE.finditer(line):
            if ABS_PATH_RE.search(line):
                continue  # referenced together with an absolute path: conformant
            out.append(_finding("BARE_TASK_NAME", "ERROR", path,
                                f"bare {match.group(0)} reference — hand over the absolute "
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
    findings += check_verdict_pairs(card_ids, verdict_dir)

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
