#!/usr/bin/env python3
"""v1.6 structured-assertion compiler (docs/eval-prereg.md §12 D1-D3; card
XJ-20261108-001 D1).

 WHAT THIS TOOL IS
 -----------------
 A parser + validator + mechanical predicate executor for the frozen v1.6
 structured-assertion schema. It takes the JSON block of structured records a
 product carries, validates each record against §12, executes the record's
 predicate against its observation surface, and emits a per-record result
 ``{claim_id, observed, expected, predicate_ok, detail, flags}`` with every
 failure kept as evidence.

 WHAT THIS TOOL IS NOT
 ---------------------
 **Zero discretion by design** (card constraint: 禁 LLM 主判定 / 禁语义等价):
 there is no natural-language understanding and no semantic-comparison surface,
 no model call anywhere in this file. The ``编译`` step — free-text assertion
 to structured record — is the executor's work under test; this tool only
 validates and mechanically executes what the executor declared. In particular
 ``exact_answer`` compares the verification command's output to the expected
 answer text EXACTLY (trailing-line-ending normalization only); any
 "these two texts mean the same thing" path is forbidden by §12 and absent
 here by construction.

 OBSERVATION SURFACES (implementation semantics, disclosed in the card record)
 ------------------------------------------------------------------------
 * command form (``verification_command``): the command runs via the frozen
   judge executor (``judge.run_command``, shell discipline unchanged), 30s
   timeout; observation = (exit_code, combined output).
 * artifact form (``artifact_path``): the file is read under the given root
   (UTF-8, errors replaced); observation = (exists, text).
 * predicate -> surface rules (validation-level, mechanical):
     - ``exists`` / ``not_exists``: artifact form only (file existence);
     - ``exit_equals`` / ``exact_answer``: command form only (exit code /
       output text);
     - ``equals`` / ``contains`` / ``matches_regex`` / ``json_path_equals`` /
       ``line_count_equals``: either form (observed text = output or file
       text).
   These couplings are implementation definitions of the frozen predicates,
   not new predicates; a coverage gap goes through the §12 closed-set route
   (披露 → 追记 → 向前生效), never an ad-hoc predicate.

 CLI
 ---
    python tools/eval/dsl_compiler.py --records FILE [--root DIR] [--out FILE]
    python tools/eval/dsl_compiler.py --selftest

 Exit codes: 0 = ok (selftest passed / records processed); 1 = selftest
 failed or operational error; 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from schema import (DSL_CLAIM_TYPES, DSL_EVALUATIVE_TYPE, DSL_EXISTENCE_PREDICATES,  # noqa: E402
                    DSL_EXIT_PREDICATES, DSL_FIELDS, DSL_PREDICATES,
                    validate_dsl_record)

#: Judge-timeout discipline: every observation execution (command or regex
#: guard subprocess) runs under this cap (§12 D3 matches_regex 超时罩口径).
DEFAULT_TIMEOUT_SECONDS = 30

#: Regex guard timeout — a distinct constant so the pilot report can cite it.
REGEX_GUARD_SECONDS = 30

#: Predicate-equality strings compare with trailing line endings stripped
#: (exact-byte comparison otherwise). This is NOT semantic normalization.
_EXACT_STRIP_RE = re.compile(r"[\r\n]+\Z")

#: Recorded observation is capped to keep result JSON auditable.
OBSERVED_CAP_CHARS = 2000

#: §13 ⑨ frozen B-arm mechanical marker (fixed-prefix convention).
B_ARM_PREFIX = "B-ARM-NOT-EXECUTED::"

_EVALUATIVE_NO_PREDICATE = "evaluative record: no predicate to execute (构念外)"


def _strip_trailing_newlines(text: str) -> str:
    return _EXACT_STRIP_RE.sub("", text)


def _cap(text: str) -> str:
    if text is None:
        return None
    if len(text) > OBSERVED_CAP_CHARS:
        return text[:OBSERVED_CAP_CHARS] + f"…[capped {len(text)} chars]"
    return text


def command_refused(command: str) -> Optional[str]:
    """Reuse the frozen judge denylist — same refusal discipline as judging.
    Local copy is NOT acceptable (drift risk); import lazily so schema-only
    consumers stay light."""
    from judge import command_refused as _refused
    return _refused(command)


def run_verification_command(command: str, root: Path,
                             timeout: int = DEFAULT_TIMEOUT_SECONDS
                             ) -> Tuple[Optional[int], str, str]:
    """Execute one verification command via the frozen judge executor.

    §13 ⑪ frozen caliber: judge.run_command + C11 flavor dispatch —
    PowerShell-flavor commands rerun through pwsh -EncodedCommand exactly as
    the main judge does, so the shadow measurement shares the main track's
    execution semantics."""
    from judge import is_powershell_flavor, run_command as _run
    if is_powershell_flavor(command):
        import base64

        encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
        wrapped = f"powershell -NoProfile -NonInteractive -EncodedCommand {encoded}"
        return _run(wrapped, root, timeout)
    return _run(command, root, timeout)


def regex_search_guarded(pattern: str, text: str,
                         timeout: int = REGEX_GUARD_SECONDS
                         ) -> Tuple[Optional[bool], List[str]]:
    """re.search under a hard timeout guard (§12 D3: 超时按观察失败留痕并旗标).

    The search runs in a short-lived subprocess (true kill on timeout — a
    runaway backtracking regex cannot outlive its guard), communicating via a
    temp JSON file. Returns (found, flags): found True/False/None(=failure),
    flags may contain ``regex_timeout`` / ``regex_error``."""
    flags: List[str] = []
    payload_file = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8", newline="") as fh:
            json.dump({"pattern": pattern, "text": text}, fh)
            payload_file = fh.name
        snippet = (
            "import json,re,sys\n"
            f"d=json.load(open(r'{payload_file}',encoding='utf-8'))\n"
            "try:\n"
            "    m=re.search(d['pattern'],d['text'])\n"
            "    print(json.dumps({'found': bool(m), 'error': None}))\n"
            "except re.error as e:\n"
            "    print(json.dumps({'found': None, 'error': str(e)}))\n"
        )
        done = subprocess.run([sys.executable, "-c", snippet],
                              capture_output=True, timeout=timeout)
        if done.returncode != 0:
            flags.append("regex_error")
            return None, flags
        out = json.loads(done.stdout.decode("utf-8", errors="replace"))
        if out.get("error"):
            flags.append("regex_error")
            return None, flags
        return bool(out.get("found")), flags
    except subprocess.TimeoutExpired:
        flags.append("regex_timeout")
        return None, flags
    except (OSError, ValueError):
        flags.append("regex_error")
        return None, flags
    finally:
        if payload_file:
            try:
                Path(payload_file).unlink()
            except OSError:
                pass


def _json_path_get(doc: object, dotted: str) -> Tuple[bool, object]:
    """§12 D3: json_path_equals supports dotted paths ONLY (no jq dependency)."""
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def execute_record(record: Dict[str, object], root: Path,
                   timeout: int = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, object]:
    """Validate + execute one structured record. Never raises for a bad
    record — every failure becomes evidence in the result (现行纪律)."""
    claim_id = str(record.get("claim_id", "<no-claim-id>"))
    errors = validate_dsl_record(record)
    base = {"claim_id": claim_id, "observed": None,
            "expected": _cap(str(record.get("expected"))) if record.get("expected") is not None else None,
            "predicate_ok": False, "detail": "", "flags": []}
    if errors:
        return {**base, "detail": "schema invalid: " + "; ".join(errors),
                "flags": ["schema_invalid"]}

    claim_type = record["claim_type"]
    predicate = record.get("predicate")
    if claim_type == DSL_EVALUATIVE_TYPE:
        return {**base, "predicate_ok": False,
                "detail": _EVALUATIVE_NO_PREDICATE, "flags": ["evaluative_face"]}

    expected = record["expected"]
    command = (record.get("verification_command") or "").strip()
    artifact = (record.get("artifact_path") or "").strip()
    flags: List[str] = []

    # §13 ⑨ B-arm mechanical marker (fixed prefix, frozen): provenance only —
    # the evaluator strips the prefix and executes the remainder at the same
    # caliber as arm A; the flag keeps the provenance auditable.
    if command and command.startswith(B_ARM_PREFIX):
        command = command[len(B_ARM_PREFIX):].strip()
        flags.append("b_arm_not_executed")

    refused = command_refused(command) if command else None
    if refused:
        return {**base, "detail": f"命令命中拒绝清单({refused!r})，不予执行: {command}",
                "flags": ["refused_exec"]}

    observed_text = None
    exit_code = None
    artifact_exists = None
    if command:
        exit_code, output, error = run_verification_command(command, root, timeout)
        if error:
            return {**base, "detail": f"命令无法完成观察: {command} ({error})",
                    "flags": ["observation_failed"]}
        observed_text = output
    if artifact:
        rel = artifact.replace("\\", "/")
        if ".." in rel.split("/"):
            return {**base, "detail": f"artifact_path 越界，不予读取: {artifact}",
                    "flags": ["artifact_path_out_of_bounds"]}
        path = root / rel
        artifact_exists = path.is_file()
        if artifact_exists:
            observed_text = path.read_text(encoding="utf-8", errors="replace")

    ok = False
    detail = ""
    if predicate in DSL_EXISTENCE_PREDICATES:
        observed = artifact_exists
        ok = (observed is True) if predicate == "exists" else (observed is False)
        detail = f"artifact {artifact!r} exists={observed}; predicate={predicate}"
        return {**base, "observed": _cap(json.dumps(observed)), "predicate_ok": ok,
                "detail": detail, "flags": flags}

    if predicate == "exit_equals":
        observed = exit_code
        ok = (observed is not None and observed == int(expected))
        detail = f"command exit={observed}; expected={expected}"
        return {**base, "observed": _cap(json.dumps(observed)), "predicate_ok": ok,
                "detail": detail, "flags": flags}

    text = observed_text or ""
    if predicate == "exact_answer":
        observed_cmp = _strip_trailing_newlines(text)
        expected_cmp = _strip_trailing_newlines(str(expected))
        ok = observed_cmp == expected_cmp
        detail = ("exact_answer: 精确比对（仅尾随换行归一，语义等价路径不存在）"
                  f"; match={ok}")
        return {**base, "observed": _cap(text), "predicate_ok": ok,
                "detail": detail, "flags": flags}

    if predicate == "equals":
        observed_cmp = _strip_trailing_newlines(text)
        ok = observed_cmp == str(expected)
        detail = f"equals: exact text compare; match={ok}"
        return {**base, "observed": _cap(text), "predicate_ok": ok,
                "detail": detail, "flags": flags}

    if predicate == "contains":
        ok = str(expected) in text
        detail = f"contains: exact substring; match={ok}"
        return {**base, "observed": _cap(text), "predicate_ok": ok,
                "detail": detail, "flags": flags}

    if predicate == "matches_regex":
        # observed text: trailing line endings stripped first (same caliber as
        # equals/exact_answer) - a CRLF tail must not sink an anchored pattern
        found, guard_flags = regex_search_guarded(str(expected),
                                                  _strip_trailing_newlines(text),
                                                  timeout)
        flags.extend(guard_flags)
        if found is None:
            detail = ("matches_regex: 观察失败" +
                      ("（超时罩触发，按观察失败留痕）" if "regex_timeout" in guard_flags
                       else "（正则错误）"))
            return {**base, "observed": _cap(text), "predicate_ok": False,
                    "detail": detail, "flags": flags}
        ok = found
        detail = f"matches_regex: search under {REGEX_GUARD_SECONDS}s guard; match={ok}"
        return {**base, "observed": _cap(text), "predicate_ok": ok,
                "detail": detail, "flags": flags}

    if predicate == "json_path_equals":
        # §12 D3: dotted paths ONLY (no jq). The frozen schema carries a single
        # `expected` string; the compiler's frozen convention is
        # `expected = "<dotted.path>-><value>"` — anything else is a flagged
        # convention error, never guessed.
        raw = str(expected)
        if "->" not in raw:
            return {**base, "observed": _cap(text), "predicate_ok": False,
                    "detail": 'json_path_equals: expected 须为 "<dotted.path>-><value>"（编译器冻结约定）',
                    "flags": ["json_path_convention_missing"]}
        dotted, value = raw.split("->", 1)
        dotted, value = dotted.strip(), value.strip()
        try:
            doc = json.loads(text)
        except ValueError:
            return {**base, "observed": _cap(text), "predicate_ok": False,
                    "detail": "json_path_equals: 观察不是合法 JSON",
                    "flags": ["json_parse_error"]}
        found, extracted = _json_path_get(doc, dotted)
        if not found:
            return {**base, "observed": _cap(text), "predicate_ok": False,
                    "detail": f"json_path_equals: 路径 {dotted!r} 未命中",
                    "flags": ["json_path_miss"]}
        ok = str(extracted) == value
        detail = (f"json_path_equals: path={dotted!r} extracted={extracted!r} "
                  f"expected={value!r}; match={ok}")
        return {**base, "observed": _cap(text), "predicate_ok": ok,
                "detail": detail, "flags": flags}

    if predicate == "line_count_equals":
        # line count convention: number of newline-terminated lines; a
        # trailing partial line (text not ending in a newline) counts too
        lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        ok = lines == int(expected)
        detail = f"line_count_equals: observed={lines}; expected={expected}"
        return {**base, "observed": _cap(text), "predicate_ok": ok,
                "detail": detail, "flags": flags}

    return {**base, "detail": f"未知 predicate（不应到达此处）: {predicate!r}",
            "flags": flags + ["unknown_predicate"]}


def compile_records(records: List[Dict[str, object]], root: Path,
                    timeout: int = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, object]:
    """Compile a structured-records JSON block: validate + execute every
    record, keep every failure as evidence. Returns the machine-readable
    result (no E0-E4 numbers anywhere — the shadow track stays isolated)."""
    results = [execute_record(rec, root, timeout) for rec in records]
    invalid = sum(1 for r in results if "schema_invalid" in r["flags"])
    return {
        "record_count": len(records),
        "schema_invalid_count": invalid,
        "predicate_ok_count": sum(1 for r in results if r["predicate_ok"]),
        "results": results,
    }


def _selftest() -> int:
    """Embedded self-check: 9 predicates x >=1 positive + >=1 negative, plus
    schema-validation and convention-error cases. Exit 0 = all green."""
    import tempfile
    checks: List[Tuple[str, bool, str]] = []

    def check(name: str, cond: bool):
        checks.append((name, bool(cond), "" if cond else "selftest mismatch"))

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        with open(root / "answer.txt", "w", encoding="utf-8", newline="") as fh:
            fh.write("MIT\n")
        with open(root / "doc.md", "w", encoding="utf-8", newline="") as fh:
            fh.write("# head\nbody line\n")
        with open(root / "data.json", "w", encoding="utf-8", newline="") as fh:
            fh.write('{"a": {"b": "yes"}}')
        with open(root / "three.txt", "w", encoding="utf-8", newline="") as fh:
            fh.write("1\n2\n3\n")
        with open(root / "gone.txt", "w", encoding="utf-8", newline="") as fh:
            fh.write("temp")
        (root / "gone.txt").unlink()

        def rec(cid, ctype, pred, expected, command=None, artifact=None):
            r = {"claim_id": cid, "claim_type": ctype, "statement": "s " + cid,
                 "verification_command": command, "artifact_path": artifact,
                 "evidence_span": [1, 2], "predicate": pred, "expected": expected}
            return r

        # exists / not_exists (artifact form)
        r = execute_record(rec("st-exists", "fact_existence", "exists", "any", artifact="answer.txt"), root)
        check("exists-pos", r["predicate_ok"] and not r["flags"])
        r = execute_record(rec("st-notexists", "fact_existence", "not_exists", "any", artifact="gone.txt"), root)
        check("not_exists-pos", r["predicate_ok"] and not r["flags"])
        r = execute_record(rec("st-exists-neg", "fact_existence", "exists", "any", artifact="gone.txt"), root)
        check("exists-neg", r["predicate_ok"] is False and not r["flags"])
        r = execute_record(rec("st-notexists-neg", "fact_existence", "not_exists", "any", artifact="answer.txt"), root)
        check("not_exists-neg", r["predicate_ok"] is False)

        # equals (command form)
        r = execute_record(rec("st-equals", "command_output", "equals", "1", command="python -c \"print(1)\""), root)
        check("equals-pos", r["predicate_ok"] and not r["flags"])
        r = execute_record(rec("st-equals-neg", "command_output", "equals", "2", command="python -c \"print(1)\""), root)
        check("equals-neg", r["predicate_ok"] is False)

        # contains (artifact form)
        r = execute_record(rec("st-contains", "fact_value", "contains", "body line", artifact="doc.md"), root)
        check("contains-pos", r["predicate_ok"])
        r = execute_record(rec("st-contains-neg", "fact_value", "contains", "absent line", artifact="doc.md"), root)
        check("contains-neg", r["predicate_ok"] is False)

        # matches_regex (command form, guarded)
        r = execute_record(rec("st-regex", "command_output", "matches_regex", r"^\[1\]$",
                                    command="python -c \"print('[1]')\""), root)
        check("regex-pos", r["predicate_ok"] and "regex_error" not in r["flags"])
        r = execute_record(rec("st-regex-neg", "command_output", "matches_regex", r"^\[9\]$",
                                    command="python -c \"print('[1]')\""), root)
        check("regex-neg", r["predicate_ok"] is False)

        # json_path_equals (artifact form, dotted path -> value convention)
        r = execute_record(rec("st-json", "fact_value", "json_path_equals", "a.b->yes", artifact="data.json"), root)
        check("json-pos", r["predicate_ok"] and "json_value_mismatch" not in r["flags"])
        r = execute_record(rec("st-json-neg", "fact_value", "json_path_equals", "a.b->no", artifact="data.json"), root)
        check("json-neg", r["predicate_ok"] is False)
        r = execute_record(rec("st-json-conv", "fact_value", "json_path_equals", "a.b", artifact="data.json"), root)
        check("json-convention-flag", "json_path_convention_missing" in r["flags"])

        # line_count_equals (artifact form)
        r = execute_record(rec("st-lines", "fact_value", "line_count_equals", 3, artifact="three.txt"), root)
        check("lines-pos", r["predicate_ok"])
        r = execute_record(rec("st-lines-neg", "fact_value", "line_count_equals", 9, artifact="three.txt"), root)
        check("lines-neg", r["predicate_ok"] is False)

        # exit_equals (command form)
        r = execute_record(rec("st-exit", "process_state", "exit_equals", 0, command="python -c \"pass\""), root)
        check("exit-pos", r["predicate_ok"])
        r = execute_record(rec("st-exit-neg", "process_state", "exit_equals", 0,
                                    command="python -c \"import sys;sys.exit(3)\""), root)
        check("exit-neg", r["predicate_ok"] is False)

        # exact_answer: EXACT compare; semantic equivalence must NOT pass
        r = execute_record(rec("st-exact", "fact_value", "exact_answer", "MIT",
                                    command="python -c \"print('MIT')\""), root)
        check("exact-pos", r["predicate_ok"] and not r["flags"])
        r = execute_record(rec("st-exact-trailing", "fact_value", "exact_answer", "MIT",
                                    artifact="answer.txt"), root)
        # artifact form forbidden for exact_answer -> schema invalid
        check("exact-artifact-invalid", "schema_invalid" in r["flags"])
        r = execute_record(rec("st-exact-equiv", "fact_value", "exact_answer", "MIT License",
                                    command="python -c \"print('MIT')\""), root)
        check("exact-semantic-equivalence-rejected",
              r["predicate_ok"] is False and "MIT License" != "MIT")

        # schema validation: evaluative must not carry a predicate
        bad = {"claim_id": "st-eval", "claim_type": "evaluative", "statement": "s",
               "verification_command": "", "artifact_path": "", "evidence_span": [1, 1],
               "predicate": "equals", "expected": "x"}
        r = execute_record(bad, root)
        check("evaluative-no-predicate", "schema_invalid" in r["flags"]
              and any("evaluative" in e for e in r["detail"].split("; ")))

        # timeout guard: catastrophic backtracking flagged, not crashed
        evil = "(a+)+$"
        r = execute_record(rec("st-regex-timeout", "command_output", "matches_regex",
                                    evil, command="python -c \"print('a'*40+'x')\""), root)
        check("regex-timeout-flagged", "regex_timeout" in r["flags"] and r["predicate_ok"] is False)

    failed = [name for name, ok, _ in checks if not ok]
    for name, ok, msg in checks:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {name}")
    print(f"DSL-COMPILER SELFTEST: {'PASS' if not failed else 'FAIL'} "
          f"({len(checks)} checks, {len(failed)} failed)")
    return 0 if not failed else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="v1.6 structured-assertion compiler (§12)")
    ap.add_argument("--records", metavar="FILE",
                    help="JSON file: list of structured assertion records")
    ap.add_argument("--root", default=".", help="observation root (repo/canonical)")
    ap.add_argument("--out", metavar="FILE", help="write machine-readable result JSON")
    ap.add_argument("--selftest", action="store_true",
                    help="embedded 9-predicate positive/negative self-check")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()
    if not args.records:
        ap.print_help()
        return 2
    records = json.loads(Path(args.records).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        print("[ERROR] --records file must hold a JSON list", file=sys.stderr)
        return 2
    result = compile_records(records, Path(args.root))
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"compiled {result['record_count']} records -> {args.out} "
              f"(ok {result['predicate_ok_count']}, schema-invalid {result['schema_invalid_count']})")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
