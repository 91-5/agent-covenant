#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XJ-20261113-002 D2: import-closure independence audit (ADV-4 phase0 hard gate).

Scans ``tools/eval`` with the AST (never imports/executes the scanned code),
builds the transitive local import closure of every frozen truth-source root
(``external_truth``, ``layer_sensitivity``, ``fp_overall``,
``independence_audit``), and fails hard when any module in that closure imports
a forbidden grader module, directly OR indirectly (prohibition 4 / C-4.1).

Modules outside the truth-source closure that import a grader module are
historical read-only callers: they are registered in ``unauditable_legacy_layers``
with their names and an explicit declaration (their layer-generating scripts are
not in this repository; per F6 the executable scan evidence is this audit), and
are NOT counted as violations. Rules are read back from the frozen
``R15-TRUTH`` block in docs/eval-prereg.md section 22 D22-E; this script does
not hard-code a threshold the frozen block already carries.

CI is py3.9: JSON is written through ``open(..., newline="")``, never
``Path.write_text(newline=)``.
"""

from __future__ import print_function

import argparse
import ast
import hashlib
import json
import os
import sys
from typing import Dict, List, Set, Tuple  # noqa: F401

TRUTH_BEGIN = "<!-- R15-TRUTH-BEGIN -->"
TRUTH_END = "<!-- R15-TRUTH-END -->"
DEFAULT_PREREG = "docs/eval-prereg.md"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_frozen_block(prereg_path):
    with open(prereg_path, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    start = text.find(TRUTH_BEGIN)
    end = text.find(TRUTH_END)
    if start < 0 or end < 0 or end < start:
        raise SystemExit("FATAL: frozen R15-TRUTH block not found in %s" % prereg_path)
    block = text[start + len(TRUTH_BEGIN):end]
    fence = block.find("```json")
    if fence >= 0:
        block = block[fence + len("```json"):]
        closing = block.rfind("```")
        if closing >= 0:
            block = block[:closing]
    return json.loads(block)


def parse_imports(path):
    """Return [(module_name, lineno), ...] for every import in the file."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        src = f.read()
    tree = ast.parse(src, filename=path)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.module, node.lineno))
    return found


def leaf(module_name):
    return module_name.split(".")[-1]


def forbidden_hits(imports, forbidden):
    out = []
    for module_name, lineno in imports:
        base = leaf(module_name)
        for bad in forbidden:
            if base == bad or module_name == bad:
                out.append({"import": module_name, "line": lineno, "forbidden": bad})
    return out


def discover_modules(scan_dir):
    """module stem -> {path, imports} for every .py directly under scan_dir."""
    mods = {}
    if not os.path.isdir(scan_dir):
        raise SystemExit("FATAL: scan dir not found: %s" % scan_dir)
    for name in sorted(os.listdir(scan_dir)):
        if not name.endswith(".py"):
            continue
        path = os.path.join(scan_dir, name)
        stem = name[:-3]
        mods[stem] = {"path": path, "imports": parse_imports(path)}
    return mods


def truth_closure(roots, mods, forbidden):
    """Transitive local closure of truth-source roots.

    Only modules that actually exist on disk enter the closure; a root that is
    not produced yet is reported separately as ``roots_pending``. Every module
    in the closure is then checked for forbidden imports, so an indirect hit
    (root -> helper -> judge) is detected exactly like a direct one.
    """
    seen = set()
    pending = list(roots)
    while pending:
        mod = pending.pop()
        if mod in seen:
            continue
        info = mods.get(mod)
        if info is None:
            continue
        seen.add(mod)
        for module_name, lineno in info["imports"]:
            base = leaf(module_name)
            if base in forbidden:
                continue  # recorded in the second pass below
            if base in mods and base not in seen:
                pending.append(base)
    violations = []
    for mod in sorted(seen):
        info = mods[mod]
        hits = forbidden_hits(info["imports"], forbidden)
        if hits:
            violations.append({
                "module": mod,
                "path": str(info.get("path", "<synthetic>")).replace("\\", "/"),
                "hits": hits,
                "kind": "direct_or_indirect_forbidden_import_in_truth_source_closure",
            })
    return sorted(seen), violations


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scan", default="tools/eval",
                    help="directory whose .py modules are scanned")
    ap.add_argument("--forbid", default="",
                    help="comma-separated forbidden grader module names")
    ap.add_argument("--out", default="", help="output JSON path")
    ap.add_argument("--prereg", default=DEFAULT_PREREG)
    ap.add_argument("--self-test", action="store_true",
                    help="verify the hard gate actually fires on a synthetic chain")
    args = ap.parse_args(argv)

    frozen = load_frozen_block(args.prereg)
    frozen_forbidden = list(frozen["forbidden_imports"])
    forbidden = [x.strip() for x in args.forbid.split(",") if x.strip()] or frozen_forbidden
    if sorted(forbidden) != sorted(frozen_forbidden):
        raise SystemExit("FATAL: --forbid %r diverges from frozen block %r" %
                         (forbidden, frozen_forbidden))

    if args.self_test:
        # Synthetic closure: root -> helper -> judge (indirect hit must fire).
        fake = {
            "t_root": {"imports": [("helper", 3)]},
            "helper": {"imports": [("judge", 7)]},
        }
        _, fake_v = truth_closure(["t_root"], fake, forbidden)
        ok = len(fake_v) >= 1 and any(v["module"] == "helper" for v in fake_v)
        print("SELFTEST: %s (synthetic indirect import detected: %s)" %
              ("PASS" if ok else "FAIL", json.dumps(fake_v, ensure_ascii=False)))
        return 0 if ok else 1

    mods = discover_modules(args.scan)
    roots = list(frozen["truth_source_roots"])
    closure, violations = truth_closure(roots, mods, forbidden)

    roots_present = [r for r in roots if r in mods]
    roots_pending = [r for r in roots if r not in mods]

    legacy = []
    for name in sorted(mods.keys()):
        info = mods[name]
        hits = forbidden_hits(info["imports"], forbidden)
        if not hits:
            continue
        if name in closure:
            continue  # already a violation, do not double count
        legacy.append({
            "name": name + ".py",
            "path": info["path"].replace("\\", "/"),
            "forbidden_hits": hits,
            "declaration": (
                "historical read-only grader caller outside the round-15 "
                "truth-source closure; its layer-generating script is not in "
                "this repository, so the independence of its historical layer "
                "labels is NOT auditable here (F6: executable AST scan evidence "
                "= this run). Not modified, red-zone discipline held."
            ),
        })

    audited_modules = []
    for name in sorted(mods.keys()):
        info = mods[name]
        audited_modules.append({
            "module": name + ".py",
            "sha256": sha256_file(info["path"]),
            "in_truth_source_closure": name in closure,
            "import_count": len(info["imports"]),
        })

    doc = {
        "schema": "r15-independence-audit-v1",
        "card": "XJ-20261113-002",
        "phase": "D2_ADV-4_phase0_hard_gate",
        "frozen_in": "section 22 D22-E",
        "frozen_block_sha256": hashlib.sha256(
            json.dumps(frozen, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "scan_dir": args.scan.replace("\\", "/"),
        "forbidden": forbidden,
        "truth_source_roots": roots,
        "roots_present": roots_present,
        "roots_pending": roots_pending,
        "truth_source_closure": closure,
        "audited_module_count": len(audited_modules),
        "audited_modules": audited_modules,
        "violations": violations,
        "unauditable_legacy_layers": legacy,
        "unauditable_legacy_layer_names": [x["name"] for x in legacy],
        "independence_I_4_3": frozen["independence"]["three_metrics_I_4_3"],
        "independence_satisfied": frozen["independence"]["satisfied"],
        "hard_gate": "PASS" if not violations else "FAIL",
        "scan_evidence": (
            "AST walk over every .py in %s; transitive local-import closure "
            "from the frozen roots; direct and indirect forbidden imports fail "
            "the gate" % args.scan.replace("\\", "/")
        ),
    }

    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        with open(args.out, "w", encoding="utf-8", newline="") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    print("AUDIT: %s | audited_modules=%d | violations=%d | "
          "unauditable_legacy_layers=%d | closure=%s | roots_pending=%s" %
          (doc["hard_gate"], len(audited_modules), len(violations),
           len(legacy), ",".join(closure) or "(none)",
           ",".join(roots_pending) or "(none)"))
    for item in legacy:
        print("  LEGACY %s -> %s" % (item["name"], item["declaration"]))
    for item in violations:
        print("  VIOLATION %s %s" % (item["module"], item["hits"]))
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
