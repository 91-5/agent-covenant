#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""XJ-20261113-003 D2: mechanical compliance lint for evaluation reports.

Rules are NOT hard-coded in this file. Every threshold, forbidden phrase,
scope-tag literal and continuity requirement is read back from the frozen
``R16-ERRATUM`` block in section 23 of docs/eval-prereg.md (clause D23-G),
so the lint cannot silently diverge from what was pre-registered.

Checks (clause D2 / D23-B / D23-F):
  1. coverage < 0.70 -> forbid an FP_overall point-estimate label, require
     ``FP_overall = not_estimable (truth_coverage_gap, ...)``.
  2. forbid total-domain discrimination wording (frozen phrase list).
  3. require the frozen scope-tag literal FP[anchor_miss] with a scope line.
  4. require a PROVISIONAL downgrade marker.
  5. require the erratum table plus >= 2 inline erratum markers.

Historical originals are preserved by design: a line carrying a struck-out
label (``~~`` / 作废 / 【原文) OR whose immediately following line carries the
inline 【勘误 marker is a *guarded historical line*, not an active claim.

``--self-test`` runs both a compliant synthetic sample (must pass) and several
constructed violating samples (each MUST fail), so an empty-tool no-op fails.

Standard library only; never imports judge / rubric_v4 / independent_judge.
Python 3.9 compatible: no Path.write_text(newline=), no | unions, no match.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

DEFAULT_PREREG = "docs/eval-prereg.md"
BEGIN = "<!-- R16-ERRATUM-BEGIN -->"
END = "<!-- R16-ERRATUM-END -->"
POINT_LABEL_RE = re.compile(r"FP_overall\s*=\s*[0-9]")
NOT_ESTIMABLE_RE = re.compile(r"FP_overall\s*=\s*not_estimable")
COVERAGE_RE = re.compile(r"coverage\s*=\s*(0?\.\d+|1\.0+)")
SCOPE_LINE_RE = re.compile(r"scope-tag", re.I)
INLINE_MARKER_RE = re.compile(r"【勘误[^】]*见\s*§0\s*勘误表第\s*\d+\s*条】")


def load_frozen_block(prereg_path: str = DEFAULT_PREREG) -> Dict[str, Any]:
    """Read back the R16-ERRATUM JSON block; fail hard if it is absent."""
    if not os.path.isfile(prereg_path):
        raise SystemExit("FATAL: frozen pre-registration not found: %s" % prereg_path)
    with open(prereg_path, "rb") as f:
        text = f.read().decode("utf-8").replace("\r\n", "\n")
    if BEGIN not in text or END not in text:
        raise SystemExit("FATAL: R16-ERRATUM frozen block markers absent in %s" % prereg_path)
    m = re.search(re.escape(BEGIN) + r"\s*```json\s*(.*?)```\s*" + re.escape(END), text, re.S)
    if m is None:
        raise SystemExit("FATAL: cannot parse R16-ERRATUM JSON block")
    try:
        block = json.loads(m.group(1))
    except ValueError as exc:
        raise SystemExit("FATAL: frozen block is not valid JSON: %s" % exc)
    if block.get("schema") != "r16-erratum-frozen-v1":
        raise SystemExit("FATAL: unexpected frozen block schema: %r" % block.get("schema"))
    return block


def lines_of(text: str) -> List[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def is_guarded_historical(line: str, next_line: str) -> bool:
    """Original text kept verbatim but explicitly superseded is not an active claim."""
    if any(tok in line for tok in ("~~", "作废", "【原文", "历史原文", "struck")):
        return True
    return "【勘误" in next_line


def lint_report(text: str, rules: Dict[str, Any], opts: argparse.Namespace) -> List[Dict[str, Any]]:
    """Return a list of violations; empty list means the report is compliant."""
    v: List[Dict[str, Any]] = []
    ls = lines_of(text)
    fp_rule = rules["fp_label_rule"]
    neg_rule = rules["negative_discrimination_rule"]
    cont = rules["erratum_continuity"]
    threshold = float(fp_rule["coverage_threshold"])

    def add(rule: str, lineno: int, detail: str) -> None:
        v.append({"rule": rule, "line": lineno, "detail": detail})

    # --- check 1: coverage-dependent FP_overall label -----------------------
    coverage_hits = [float(x) for x in COVERAGE_RE.findall(text)]
    if not coverage_hits:
        add("coverage_not_declared", 0, "no 'coverage = <float>' literal found")
        coverage = None
    else:
        coverage = min(coverage_hits)
    if coverage is not None and coverage < threshold:
        if not NOT_ESTIMABLE_RE.search(text):
            add("FP_overall_when_coverage_lt_0.70", 0,
                "coverage %.3f < %.2f but no 'FP_overall = not_estimable' declaration" % (coverage, threshold))
        else:
            for i, line in enumerate(ls):
                if NOT_ESTIMABLE_RE.search(line) and "truth_coverage_gap" not in line:
                    add("FP_overall_when_coverage_lt_0.70", i + 1,
                        "not_estimable declaration must carry truth_coverage_gap")
        if "truth_coverage_gap" not in text:
            add("FP_overall_when_coverage_lt_0.70", 0, "truth_coverage_gap literal missing")
        for i, line in enumerate(ls):
            if not POINT_LABEL_RE.search(line):
                continue
            if NOT_ESTIMABLE_RE.search(line):
                continue
            nxt = ls[i + 1] if i + 1 < len(ls) else ""
            if is_guarded_historical(line, nxt):
                continue
            add("FP_overall_when_coverage_lt_0.70", i + 1,
                "unstruck FP_overall point-estimate label with no inline erratum guard: %s" % line.strip()[:120])

    # --- check 2: total-domain discrimination wording ----------------------
    forbidden = list(neg_rule["forbidden_total_discrimination_phrases"])
    for phrase in forbidden:
        for i, line in enumerate(ls):
            if phrase in line:
                add("forbid_total_discrimination", i + 1,
                    "frozen forbidden phrase %r present (D-5.1)" % phrase)
    # a downgrade statement must remain, otherwise deleting the whole topic is a bypass
    allowed_present = any(p in text for p in neg_rule["allowed_phrases"]) or ("不构成总体判别力估计" in text)
    if not allowed_present:
        add("forbid_total_discrimination", 0,
            "no permitted D-5.1 downgrade wording retained; topic may have been silently removed")

    # --- check 3: scope-tag -------------------------------------------------
    literal = fp_rule["when_coverage_lt_threshold"]["layer_label_literal"]
    scope_lit = literal.split("=")[0].strip()  # FP[anchor_miss]
    if scope_lit not in text:
        add("require_scope_tag", 0, "frozen scope-tag literal %r missing" % scope_lit)
    scope_lines = [i + 1 for i, line in enumerate(ls)
                   if SCOPE_LINE_RE.search(line) and (scope_lit in line or opts.scope_tag in line)]
    if not scope_lines:
        add("require_scope_tag", 0,
            "no scope-tag declaration line carrying %r / %r" % (opts.scope_tag, scope_lit))

    # --- check 4: PROVISIONAL downgrade -------------------------------------
    if not re.search(r"\bPROVISIONAL\b", text):
        add("require_provisional", 0, "PROVISIONAL downgrade marker missing")

    # --- check 5: erratum continuity ----------------------------------------
    if opts.require_erratum:
        if "勘误表" not in text:
            add("require_erratum", 0, "erratum table section missing")
        n_markers = text.count("【勘误")
        if n_markers < int(cont["min_inline_markers"]):
            add("require_erratum", 0,
                "inline erratum markers %d < %d" % (n_markers, int(cont["min_inline_markers"])))
        if not INLINE_MARKER_RE.search(text):
            add("require_erratum", 0,
                "no inline marker of the frozen form 【勘误 ... 见 §0 勘误表第 N 条】")
        if "Erratum" not in text:
            add("require_erratum", 0, "erratum table must be labelled (Erratum)")

    # --- CLI spec validation: never let a caller silently redefine a rule --
    m = re.match(r"^FP_overall_when_coverage_lt_(0?\.\d+)$", opts.forbid_label or "")
    if opts.forbid_label:
        if m is None:
            add("forbid_label_spec", 0, "unrecognised --forbid-label spec %r" % opts.forbid_label)
        elif abs(float(m.group(1)) - threshold) > 1e-9:
            add("forbid_label_spec", 0,
                "--forbid-label threshold %s differs from frozen %s" % (m.group(1), threshold))
    if opts.scope_tag and opts.scope_tag not in ("FP_anchor_miss", scope_lit):
        add("require_scope_tag_spec", 0,
            "--require-scope-tag %r is not the frozen FP_anchor_miss" % opts.scope_tag)
    return v


# ---------------------------------------------------------------------------
# self-test: one compliant synthetic sample + several constructed violations
# ---------------------------------------------------------------------------
COMPLIANT = """# synthetic compliant report
coverage = 0.415
truth_coverage_gap = true (0.415 < 0.70)
## §0 勘误表（Erratum，2026-11-13）
| 位置 | 原文 | 更正 | 依据条款 | 认定方 |
|---|---|---|---|---|
| §1 | ~~`FP_overall = 1.0`~~（历史标签，已划注，作废） | `FP[anchor_miss]` 层内读数 | P-4.5'' | dp + sir |
| §2 | 预审 N1 的全域缺席断言（转述，逐字见上游） | 层构成伪影 | D-5.1 | dp + sir |
scope-tag: FP_anchor_miss -> `FP[anchor_miss]`（层内条件率，禁止外推）
`FP[anchor_miss] = 1.000 (48/48, Wilson 95% [0.9259, 1.0])`
`FP_overall = not_estimable (truth_coverage_gap, coverage = 0.415 < 0.70)`
M1 = +6.153846 pp, PROVISIONAL, 显式降级。
在 T\\* 可判子集上，主轨 E4 判定与 T\\* 真值呈负向关联；该关联由层构成解释，不构成总体判别力估计。
【勘误 2026-11-13：见 §0 勘误表第 1 条】原句保留，更正句紧随其后。
【勘误 2026-11-13：见 §0 勘误表第 2 条】原句保留，更正句紧随其后。
"""


def synthetic_opts() -> argparse.Namespace:
    return argparse.Namespace(
        require_erratum=True,
        forbid_label="FP_overall_when_coverage_lt_0.70",
        scope_tag="FP_anchor_miss",
        forbid_total_discrimination=True,
    )


def self_test(rules: Dict[str, Any]) -> int:
    opts = synthetic_opts()
    cases: List[Dict[str, Any]] = []

    base = lint_report(COMPLIANT, rules, opts)
    cases.append({"name": "compliant_synthetic_must_pass", "must_fail": False,
                  "violations": len(base), "ok": len(base) == 0})

    # NEGATIVE CASE 1: an unstruck point-estimate label with no not_estimable
    neg1 = COMPLIANT.replace("`FP_overall = not_estimable (truth_coverage_gap, coverage = 0.415 < 0.70)`", "")
    neg1 = neg1.replace("~~`FP_overall = 1.0`~~（历史标签，已划注，作废）", "`FP_overall = 1.0`（现行结论）")
    r1 = lint_report(neg1, rules, opts)
    cases.append({"name": "NEGATIVE_unstruck_FP_overall_point_estimate_must_fail",
                  "must_fail": True, "violations": len(r1), "ok": len(r1) > 0})

    # NEGATIVE CASE 2: a frozen forbidden phrase reintroduced
    phrase = rules["negative_discrimination_rule"]["forbidden_total_discrimination_phrases"][0]
    neg2 = COMPLIANT.replace("层构成伪影", "%s（越界断言）" % phrase)
    r2 = lint_report(neg2, rules, opts)
    cases.append({"name": "NEGATIVE_frozen_forbidden_phrase_must_fail",
                  "must_fail": True, "violations": len(r2), "ok": len(r2) > 0})

    # NEGATIVE CASE 3: erratum table + inline markers stripped
    neg3 = "\n".join(l for l in COMPLIANT.split("\n")
                     if "勘误表" not in l and "【勘误" not in l and "Erratum" not in l)
    r3 = lint_report(neg3, rules, opts)
    cases.append({"name": "NEGATIVE_missing_erratum_must_fail",
                  "must_fail": True, "violations": len(r3), "ok": len(r3) > 0})

    # NEGATIVE CASE 4: scope-tag removed
    neg4 = "\n".join(l for l in COMPLIANT.split("\n") if "scope-tag" not in l)
    r4 = lint_report(neg4, rules, opts)
    cases.append({"name": "NEGATIVE_missing_scope_tag_must_fail",
                  "must_fail": True, "violations": len(r4), "ok": len(r4) > 0})

    # NEGATIVE CASE 5: PROVISIONAL removed
    neg5 = COMPLIANT.replace("PROVISIONAL", "FINAL")
    r5 = lint_report(neg5, rules, opts)
    cases.append({"name": "NEGATIVE_missing_PROVISIONAL_must_fail",
                  "must_fail": True, "violations": len(r5), "ok": len(r5) > 0})

    all_ok = all(c["ok"] for c in cases)
    for c in cases:
        verdict = "PASS" if c["ok"] else "FAIL"
        if c["must_fail"]:
            print("SELFTEST %s: %s (constructed violating sample correctly rejected, violations=%d)"
                  % (verdict, c["name"], c["violations"]))
        else:
            print("SELFTEST %s: %s (compliant sample accepted, violations=%d)"
                  % (verdict, c["name"], c["violations"]))
    print("SELFTEST_NEGATIVE_CASES=%d" % sum(1 for c in cases if c["must_fail"]))
    print("SELFTEST: %s" % ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Mechanical report compliance lint (XJ-20261113-003 D2)")
    ap.add_argument("--report", default="", help="report markdown to lint")
    ap.add_argument("--prereg", default=DEFAULT_PREREG, help="frozen pre-registration path")
    ap.add_argument("--require-erratum", action="store_true", help="require erratum table + inline markers")
    ap.add_argument("--forbid-label", default="", help="e.g. FP_overall_when_coverage_lt_0.70")
    ap.add_argument("--require-scope-tag", dest="scope_tag", default="", help="e.g. FP_anchor_miss")
    ap.add_argument("--forbid-total-discrimination", action="store_true")
    ap.add_argument("--self-test", action="store_true", help="run synthetic positive + negative cases")
    ap.add_argument("--out", default="", help="optional JSON evidence file")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    rules = load_frozen_block(args.prereg)

    if args.self_test:
        return self_test(rules)

    if not args.report:
        print("FATAL: --report is required unless --self-test is used")
        return 2
    if not os.path.isfile(args.report):
        print("FATAL: report not found: %s" % args.report)
        return 2
    with open(args.report, "rb") as f:
        text = f.read().decode("utf-8")

    violations = lint_report(text, rules, args)
    result = {
        "schema": "r16-report-lint-v1",
        "card": "XJ-20261113-003",
        "report": args.report.replace("\\", "/"),
        "prereg": args.prereg.replace("\\", "/"),
        "rules_source": "section 23 D23-G R16-ERRATUM frozen block (read back, not hard-coded)",
        "checks": {
            "require_erratum": bool(args.require_erratum),
            "forbid_label": args.forbid_label or None,
            "require_scope_tag": args.scope_tag or None,
            "forbid_total_discrimination": bool(args.forbid_total_discrimination),
            "require_provisional": True,
        },
        "coverage_literals": COVERAGE_RE.findall(text),
        "inline_erratum_markers": text.count("【勘误"),
        "report_lf_chars": len(text.replace("\r\n", "\n")),
        "violations": violations,
        "status": "PASS" if not violations else "FAIL",
    }
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    if violations:
        print("LINT: FAIL | violations=%d | report=%s" % (len(violations), args.report))
        for item in violations:
            print("  [%s] line %d: %s" % (item["rule"], item["line"], item["detail"]))
        return 1
    print("LINT: PASS | checks=5 | coverage_gap_guard=OK | erratum_markers=%d | lf_chars=%d | rules=R16-ERRATUM-frozen-block"
          % (result["inline_erratum_markers"], result["report_lf_chars"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
