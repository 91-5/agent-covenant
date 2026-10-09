#!/usr/bin/env python3
"""Sync the test count declared in the READMEs with the suite's real count.

Why this exists (EVO-20261007-001, review point 4 / P2-2)
--------------------------------------------------------
`STALE_TEST_COUNT` tripped twice in one week (141 -> 166 -> 168) because the
number lived as hand-written prose in two READMEs, and every test added made
both files wrong at once. The rule is right -- a count in a copy-pasteable
command is a claim about the deliverable -- but the *maintenance* was manual,
so the honest fix is to stop hand-writing it.

Design choices, and the ones deliberately rejected
--------------------------------------------------
* **The number comes from `unittest`, not from grep.** The review suggested
  `grep -c "^def test_" tests/*.py`. On today's corpus that agrees with the
  suite (168 == 168), but it is a coincidence of this repository having no
  parameterised tests and no shared test-case base classes. `lint_cards.py`
  already discovers the count properly (`_discover_test_count`); a sync script
  that disagreed with the checker would just be a new way to be wrong.
* **This runs locally, not in CI.** CI writing READMEs would leave an
  uncommitted diff inside the PR flow, and `gate.yml` deliberately holds
  `contents: read` -- a writer would need a permission widening that the
  project's least-privilege design avoids on purpose.
* **The anchor is not an exemption.** `lint_cards.py` still validates the
  number between the markers, so a stale anchor fails exactly like stale prose.
  The anchor only removes the hand-typing.

Usage
-----
    python tools/sync_test_count.py            # write the real count into both READMEs
    python tools/sync_test_count.py --check    # exit 1 if either README is out of sync
    python tools/sync_test_count.py --json     # machine-readable result

Exit codes
----------
    0  in sync (or successfully written)
    1  out of sync under --check, or an anchor is missing/malformed
    2  usage error (suite could not be discovered)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_USAGE = 2

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The markers a README uses to declare its count. Deliberately picks up the
#: HTML-comment form so the number is attributable to exactly one construct.
ANCHOR_RE = re.compile(
    r"(?P<open><!--\s*test-count\s*-->)(?P<number>\d+)(?P<close><!--\s*/test-count\s*-->)"
)
ANCHORED_FILES = ("README.md", "README.zh-CN.md")


def _safe_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _load_linter():
    """Reuse the checker's own suite-discovery so the two cannot disagree."""
    spec = importlib.util.spec_from_file_location(
        "lint_cards", REPO_ROOT / "tools" / "lint_cards.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def real_test_count(linter=None):
    """Return the suite's actual test count, or None when undiscoverable."""
    lint = linter or _load_linter()
    count, failed = lint._discover_test_count(REPO_ROOT)
    if failed:
        return None
    return count


def sync_file(path, count, write=True):
    """Rewrite every anchor in `path` to `count`.

    Returns `(changed, error)` where error is a human-readable reason when the
    file declares no anchor at all. A README without an anchor is an error
    rather than a silent no-op: a script that reports success while changing
    nothing is precisely the failure mode this whole exercise is about.
    """
    if not path.is_file():
        return (False, f"missing file: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = list(ANCHOR_RE.finditer(text))
    if not matches:
        return (False, f"no '<!-- test-count -->' anchor found in {path.name}")
    changed = False
    # Replace right-to-left so earlier offsets stay valid.
    for match in reversed(matches):
        if match.group("number") != str(count):
            text = text[:match.start("number")] + str(count) + text[match.end("number"):]
            changed = True
    if changed and write:
        path.write_text(text, encoding="utf-8")
    return (changed, None)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Write the suite's real test count into the README anchors."
    )
    parser.add_argument("--check", action="store_true",
                        help="report drift and exit 1 instead of writing")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    return parser


def main(argv=None):
    _safe_utf8()
    args = build_parser().parse_args(argv)

    count = real_test_count()
    if count is None:
        print("[USAGE] could not discover the test suite; refusing to guess a count",
              file=sys.stderr)
        return EXIT_USAGE

    results = []
    problems = []
    for name in ANCHORED_FILES:
        changed, error = sync_file(REPO_ROOT / name, count, write=not args.check)
        if error:
            problems.append(error)
        results.append({"file": name, "changed": changed, "error": error})

    ok = not problems and not (args.check and any(r["changed"] for r in results))

    if args.json:
        print(json.dumps({"ok": ok, "count": count, "files": results},
                         ensure_ascii=False, indent=2))
    else:
        for item in results:
            if item["error"]:
                print(f"[ERROR] {item['file']}: {item['error']}")
            elif item["changed"]:
                verb = "out of sync" if args.check else "updated"
                print(f"[{'DRIFT' if args.check else ' OK '}] {item['file']}: {verb} -> {count}")
            else:
                print(f"[ OK ] {item['file']}: in sync at {count}")
    return EXIT_OK if ok else EXIT_DRIFT


if __name__ == "__main__":
    sys.exit(main())