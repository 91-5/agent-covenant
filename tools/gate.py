#!/usr/bin/env python3
"""agent-covenant gate — verdict gate for multi-agent deliverables.

Reads machine-readable verdict files (`verdicts/<id>.verdict.json`) and decides
whether a delivery is allowed to proceed. Stdlib only, no runtime deps.

Usage
-----
    python tools/gate.py --verdict-dir verdicts --require AC-20260929-001
    python tools/gate.py --verdict-dir verdicts --artifact-map artifacts.json --json

Exit codes
----------
    0  every required id satisfied the policy
    1  gate violation(s); reasons printed (or emitted as JSON with --json)
    2  usage / input error (bad directory, unreadable verdict, bad args)

Policy (normative in PROTOCOL.md §6)
------------------------------------
  * verdict file exists and parses
  * verdict in {PASS, CONDITIONAL, FAIL}
  * blockers == 0 for PASS
  * CONDITIONAL needs --allow-conditional AND a non-empty acknowledged_by,
    and non-empty conditions[] when blockers > 0
  * independent == true unless --allow-nonindependent
  * evidence is a non-empty list of strings
  * freshness: when --artifact-map is given, the artifact's mtime must not be
    newer than the verdict's `ts` (1s grace for clock granularity). A verdict
    older than the thing it judges is stale and blocks.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_VIOLATION = 1
EXIT_USAGE = 2

VALID_VERDICTS = ("PASS", "CONDITIONAL", "FAIL")
REQUIRED_FIELDS = ("id", "verdict", "blockers", "independent", "verifier", "ts")
VERDICT_SUFFIX = ".verdict.json"
STALE_GRACE_SECONDS = 1.0


def _safe_utf8() -> None:
    """Windows consoles default to a legacy codepage; never let output crash."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def parse_ts(raw):
    """Parse an ISO-8601 timestamp into an aware UTC datetime.

    Accepts a trailing 'Z' (3.10+ fromisoformat does, 3.9 does not) and treats a
    naive timestamp as UTC.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("ts must be a non-empty ISO-8601 string")
    text = raw.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_verdict(verdict_dir, vid):
    """Return (data, error_code, error_detail). data is None on error."""
    path = verdict_dir / f"{vid}{VERDICT_SUFFIX}"
    if not path.is_file():
        return None, "MISSING_VERDICT", f"no verdict file at {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - any parse failure is a violation
        return None, "UNREADABLE_VERDICT", f"cannot parse {path.name}: {exc}"
    if not isinstance(data, dict):
        return None, "UNREADABLE_VERDICT", "verdict file must contain a JSON object"
    return data, None, None


def _check_fields(vid, data):
    out = []
    for field in REQUIRED_FIELDS:
        if field not in data:
            out.append(("MISSING_FIELD", f"required field '{field}' is absent"))
    if "id" in data and data["id"] != vid:
        out.append(("ID_MISMATCH", f"id field {data['id']!r} does not match filename id {vid!r}"))
    return out


def _check_verdict_value(data):
    raw = data.get("verdict")
    if raw is None:
        return None, []
    if not isinstance(raw, str) or raw.strip().upper() not in VALID_VERDICTS:
        return None, [("BAD_VERDICT_VALUE", f"verdict {raw!r} is not one of {VALID_VERDICTS}")]
    return raw.strip().upper(), []


def _check_blockers(data, verdict):
    if "blockers" not in data:
        return []
    blockers = data["blockers"]
    if isinstance(blockers, bool) or not isinstance(blockers, int):
        return [("BAD_VERDICT_VALUE", "blockers must be an integer")]
    if verdict == "PASS" and blockers != 0:
        return [("BLOCKERS_PRESENT", f"PASS verdict carries blockers={blockers}")]
    return []


def _check_conditional(data, verdict, allow_conditional):
    if verdict != "CONDITIONAL":
        return []
    out = []
    if not allow_conditional:
        out.append(("CONDITIONAL_NOT_ALLOWED", "CONDITIONAL requires --allow-conditional"))
    if not str(data.get("acknowledged_by") or "").strip():
        out.append(("CONDITIONAL_UNACKNOWLEDGED", "CONDITIONAL has no acknowledged_by"))
    blockers = data.get("blockers")
    if not data.get("conditions") and isinstance(blockers, int) and blockers > 0:
        out.append(("CONDITIONAL_NO_CONDITIONS", "CONDITIONAL with blockers>0 needs a non-empty conditions[]"))
    return out


def _check_independence(data, allow_nonindependent):
    if data.get("independent") is True:
        return []
    if allow_nonindependent:
        return []
    return [("NOT_INDEPENDENT", f"independent={data.get('independent')!r}; the author may not review itself")]


def _check_evidence(data):
    evidence = data.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return [("NO_EVIDENCE", "evidence must be a non-empty list")]
    if not all(isinstance(item, str) and item.strip() for item in evidence):
        return [("NO_EVIDENCE", "every evidence entry must be a non-empty string")]
    return []


def _check_freshness(data, artifact_paths):
    if "ts" not in data:
        return []
    try:
        judged_at = parse_ts(data["ts"])
    except Exception as exc:  # noqa: BLE001
        return [("BAD_TIMESTAMP", f"ts is not a valid ISO-8601 timestamp: {exc}")]
    out = []
    for rel in artifact_paths:
        path = Path(rel)
        if not path.exists():
            out.append(("ARTIFACT_MISSING", f"gated artifact does not exist: {rel}"))
            continue
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if (modified - judged_at).total_seconds() > STALE_GRACE_SECONDS:
            out.append((
                "STALE_VERDICT",
                f"artifact {rel} was modified after the verdict was issued "
                f"({modified.isoformat()} > {judged_at.isoformat()})",
            ))
    return out


def evaluate(vid, data, verdict_dir, args, artifact_map):
    """Return a list of (code, detail) violations for one verdict."""
    violations = []
    violations += _check_fields(vid, data)
    verdict, value_errors = _check_verdict_value(data)
    violations += value_errors
    violations += _check_blockers(data, verdict)
    if verdict == "FAIL":
        violations.append(("VERDICT_FAIL", "reviewer returned FAIL"))
    violations += _check_conditional(data, verdict, args.allow_conditional)
    violations += _check_independence(data, args.allow_nonindependent)
    violations += _check_evidence(data)
    violations += _check_freshness(data, (artifact_map or {}).get(vid, []))
    return violations


def build_parser():
    parser = argparse.ArgumentParser(
        prog="gate.py",
        description="Verdict gate for multi-agent deliverables (see PROTOCOL.md §6).",
    )
    parser.add_argument("--verdict-dir", default="verdicts", help="directory of <id>.verdict.json files")
    parser.add_argument("--require", action="append", default=[], metavar="ID",
                        help="verdict id that must pass; repeatable. Default: every verdict in the dir")
    parser.add_argument("--artifact-map", metavar="FILE",
                        help='JSON {"<id>": ["<path>", ...]} used for the staleness check')
    parser.add_argument("--allow-conditional", action="store_true",
                        help="treat CONDITIONAL as passing (acknowledged_by still required)")
    parser.add_argument("--allow-nonindependent", action="store_true",
                        help="accept verdicts not produced independently of the author")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit machine-readable JSON")
    parser.add_argument("--quiet", action="store_true", help="suppress output; use the exit code")
    return parser


def _read_artifact_map(path):
    if not path:
        return {}
    map_path = Path(path)
    if not map_path.is_file():
        raise ValueError(f"artifact map not found: {path}")
    try:
        data = json.loads(map_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"cannot parse artifact map {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("artifact map must be a JSON object of {id: [paths]}")
    return data


def main(argv=None):
    _safe_utf8()
    args = build_parser().parse_args(argv)

    verdict_dir = Path(args.verdict_dir)
    if not verdict_dir.is_dir():
        print(f"[USAGE] verdict directory not found: {verdict_dir}", file=sys.stderr)
        return EXIT_USAGE
    try:
        artifact_map = _read_artifact_map(args.artifact_map)
    except ValueError as exc:
        print(f"[USAGE] {exc}", file=sys.stderr)
        return EXIT_USAGE

    if args.require:
        ids = list(args.require)
    else:
        ids = sorted(p.name[: -len(VERDICT_SUFFIX)] for p in verdict_dir.glob(f"*{VERDICT_SUFFIX}"))

    findings = []
    for vid in ids:
        data, code, detail = load_verdict(verdict_dir, vid)
        if code:
            findings.append({"id": vid, "code": code, "detail": detail})
            continue
        for vcode, vdetail in evaluate(vid, data, verdict_dir, args, artifact_map):
            findings.append({"id": vid, "code": vcode, "detail": vdetail})

    ok = not findings
    if args.as_json:
        print(json.dumps({"ok": ok, "checked": len(ids), "violations": findings},
                         ensure_ascii=False, indent=2))
    elif not args.quiet:
        for item in findings:
            print(f"[{item['code']}] {item['id']}: {item['detail']}")
        if ok:
            print(f"GATE: PASS ({len(ids)} checked)")
        else:
            print(f"GATE: FAIL ({len(findings)} violations across {len(ids)} checked)")
    return EXIT_OK if ok else EXIT_VIOLATION


if __name__ == "__main__":
    sys.exit(main())
