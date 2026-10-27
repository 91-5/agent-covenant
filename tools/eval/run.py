"""CLI front door for the eval harness.

Modes (composable flags, stdlib argparse only):

    python tools/eval/run.py --selftest
        The lie detector: every control (visible + sealed, if present) through
        the judge. Negative controls must not pass, positive must pass, blank
        must be distinguished. Exit 1 on any failure.

    python tools/eval/run.py --dry-run
        Parse the 30-task list against the frozen schema and grade the
        fixture products; E0-E4 must each hit at least once. No study data.

    python tools/eval/run.py --judge <file-or-dir> [--root DIR]
        Judge product markdown deterministically; prints per-claim results
        and pooled level counts as JSON.

    python tools/eval/run.py --package <run-dir> --out <dir>
        Build the blinded adjudication package + the sealed key. The key is
        written next to the package (inside the gitignored sealed area) and
        must be handed to sir immediately -- the printed instruction says so.

    python tools/eval/run.py --report <package-dir>
        Stage-1 blind report (no condition information exists in it).

    python tools/eval/run.py --unblind <package-dir> --key <key.json>
        Stage-2 paired analysis. Sir-only; wrong key is a hard stop.

This script runs from a checkout (like the repo's other tools): it puts its
own directory on sys.path so plain imports work under
``python tools/eval/run.py`` as well as under unittest discovery.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import blind  # noqa: E402  (path shim above)
import controls  # noqa: E402
import judge  # noqa: E402
import report  # noqa: E402
import stats  # noqa: E402
from schema import (  # noqa: E402
    LAYER_COUNTS,
    TOTAL_TASKS,
    load_task_dir,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TASK_DIR = Path(__file__).resolve().parent / "tasks"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2


def _safe_utf8() -> None:
    """Windows consoles default to a legacy codepage; never let output crash."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="agent-covenant process-integrity eval harness (observer).",
    )
    parser.add_argument("--selftest", action="store_true",
                        help="run the control bank through the judge (lie detector)")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate the task list and grade fixture products")
    parser.add_argument("--judge", metavar="PATH",
                        help="judge a product markdown file or a directory of them")
    parser.add_argument("--tasks", action="store_true",
                        help="list the parsed task inventory and exit")
    parser.add_argument("--package", metavar="RUN_DIR",
                        help="build the blinded package + sealed key from a run dir")
    parser.add_argument("--out", metavar="DIR", default=None,
                        help="output dir for --package (default: .eval-sealed/pkg-<ts>)")
    parser.add_argument("--report", metavar="PACKAGE_DIR",
                        help="generate the stage-1 blind report from a package")
    parser.add_argument("--allow-drift", action="store_true",
                        help="report/unblind even though the repository state differs "
                             "from the one the package's judgements were sealed against; "
                             "the drift is printed and must be cited alongside the numbers")
    parser.add_argument("--unblind", nargs=2, metavar=("PACKAGE_DIR", "KEY"),
                        help="sir-only: paired analysis from package + sealed key")
    parser.add_argument("--root", metavar="DIR", default=str(REPO_ROOT),
                        help="workspace root for ref-form paths and command cwd")
    parser.add_argument("--timeout", type=int, default=judge.DEFAULT_TIMEOUT_SECONDS,
                        help=f"per-command timeout in seconds (default {judge.DEFAULT_TIMEOUT_SECONDS})")
    return parser


def cmd_selftest(root: Path, timeout: int) -> int:
    result = controls.run_selftest(root=root, timeout=timeout)
    print(controls.format_selftest(result))
    return EXIT_OK if result.ok else EXIT_FAIL


def cmd_dry_run(root: Path, timeout: int) -> int:
    ok = True
    print("== eval harness dry-run ==")

    tasks, task_errors = load_task_dir(TASK_DIR)
    layer_counts = {layer: 0 for layer in LAYER_COUNTS}
    for task in tasks:
        layer_counts[task.layer] = layer_counts.get(task.layer, 0) + 1
    print(f"tasks: {len(tasks)}/{TOTAL_TASKS} parsed from {TASK_DIR}")
    for layer, count in layer_counts.items():
        print(f"  layer {layer}: {count}/{LAYER_COUNTS[layer]}")
    if task_errors:
        ok = False
        for error in task_errors:
            print(f"  [ERROR] {error}")
    else:
        print("  schema: ok")

    level_hits = {"E0": 0, "E1": 0, "E2": 0, "E3": 0, "E4": 0}
    fixtures = sorted(FIXTURE_DIR.glob("*.md"))
    if not fixtures:
        ok = False
        print(f"  [ERROR] no fixture products found in {FIXTURE_DIR}")
    for fixture in fixtures:
        judgements = judge.judge_file(fixture, root, timeout=timeout)
        if not judgements:
            ok = False
            print(f"  [ERROR] {fixture.name}: no claims extracted")
            continue
        for j in judgements:
            level_hits[j.level] = level_hits.get(j.level, 0) + 1
        summary = ", ".join(f"{j.level}" for j in judgements)
        print(f"  fixture {fixture.name}: {len(judgements)} claim(s) -> {summary}")
    print(f"fixture level hits: {level_hits}")
    missing = [level for level, hits in level_hits.items() if hits < 1]
    if missing:
        ok = False
        print(f"  [ERROR] levels without a fixture hit: {missing}")
    else:
        print("  every level E0-E4 hit at least once: ok")

    print("DRY-RUN: " + ("PASS" if ok else "FAIL"))
    return EXIT_OK if ok else EXIT_FAIL


def cmd_tasks() -> int:
    tasks, task_errors = load_task_dir(TASK_DIR)
    for task in sorted(tasks, key=lambda item: item.id):
        print(f"{task.id} [{task.layer}] {task.title}")
    for error in task_errors:
        print(f"[ERROR] {error}")
    return EXIT_OK if not task_errors else EXIT_FAIL


def cmd_judge(path: Path, root: Path, timeout: int) -> int:
    files: List[Path]
    if path.is_dir():
        files = sorted(path.glob("*.md"))
    elif path.is_file():
        files = [path]
    else:
        print(f"[ERROR] no such file or directory: {path}", file=sys.stderr)
        return EXIT_USAGE

    payload = {"root": str(root), "products": []}
    pooled = {"E0": 0, "E1": 0, "E2": 0, "E3": 0, "E4": 0}
    for file in files:
        judgements = judge.judge_file(file, root, timeout=timeout)
        for j in judgements:
            pooled[j.level] = pooled.get(j.level, 0) + 1
        payload["products"].append({
            "file": str(file),
            "judgements": [j.to_dict() for j in judgements],
        })
    payload["pooled_counts"] = pooled
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return EXIT_OK


def cmd_package(run_dir: Path, out_dir: Optional[Path], root: Path,
                timeout: int) -> int:
    seed = blind.generate_seed()
    if out_dir is None:
        sealed_root = REPO_ROOT / blind.SEALED_DIR_NAME
        out_dir = sealed_root / f"pkg-{seed[:8]}"
    try:
        package_dir, key_path, _mapping = blind.build_package(
            run_dir, out_dir, seed, root=root, timeout=timeout)
    except (OSError, ValueError) as exc:
        print(f"[ERROR] --package refused: {exc}", file=sys.stderr)
        print("        run 目录须含 run-data.json（runner 产出）与 products/。", file=sys.stderr)
        return EXIT_USAGE
    print(f"package: {package_dir}")
    print(f"sealed key: {key_path}")
    print("custody: 将 key 文件立即移交 sir 保管——ZCode 与 adjudicator 均不得持有完整对应表；")
    print("报告定稿前禁止任何解盲操作；key 含 seed，持有 seed 即可重导全部对应关系。")
    return EXIT_OK


def cmd_report(package_dir: Path, root: Path, timeout: int,
               allow_drift: bool = False) -> int:
    print(report.blind_report(package_dir, root, timeout=timeout,
                              allow_drift=allow_drift))
    return EXIT_OK


def cmd_unblind(package_dir: Path, key_path: Path, root: Path, timeout: int,
                allow_drift: bool = False) -> int:
    try:
        fragment = report.unblind_fragment(package_dir, key_path, root, timeout=timeout,
                                          allow_drift=allow_drift)
    except (ValueError, OSError, KeyError) as exc:
        print(f"[ERROR] unblind refused: {exc}", file=sys.stderr)
        return EXIT_USAGE
    print(fragment)
    return EXIT_OK


def main(argv: Optional[List[str]] = None) -> int:
    _safe_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    timeout = args.timeout

    any_mode = (args.selftest or args.dry_run or args.judge or args.tasks
                or args.package or args.report or args.unblind)
    if not any_mode:
        parser.print_help()
        return EXIT_USAGE

    if args.selftest:
        return cmd_selftest(root, timeout)
    if args.dry_run:
        return cmd_dry_run(root, timeout)
    if args.tasks:
        return cmd_tasks()
    if args.judge:
        return cmd_judge(Path(args.judge), root, timeout)
    if args.package:
        return cmd_package(Path(args.package), Path(args.out) if args.out else None,
                           root, timeout)
    if args.report:
        return cmd_report(Path(args.report), root, timeout, args.allow_drift)
    if args.unblind:
        package_dir, key_path = Path(args.unblind[0]), Path(args.unblind[1])
        return cmd_unblind(package_dir, key_path, root, timeout, args.allow_drift)
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
