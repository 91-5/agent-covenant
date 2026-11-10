#!/usr/bin/env python3
"""v1.8 R1 off-line replay (docs/eval-prereg.md §16; card XJ-20261110-001 D2).

WHAT THIS TOOL DOES
-------------------
Replays the sealed mismatch samples of an earlier round on the **R1-aligned
observation surface** and reports how far the pre-registered expectation
actually holds.

Three independent things are checked, all read-only:

1. **Pre-R1 reproduction** — the aligner is re-run over the whole sealed
   dataset with the *old* surface (observation root only) and compared, claim
   by claim, with the frozen alignment split. This closes the round-8
   ADV-1 finding: the frozen `shadow_align` result was never independently
   replayed because the replay script was never tracked. This file is
   tracked, so the check is now reproducible on another machine.

2. **Per-item R1 replay** — every claim listed in the §16 expected-resolution
   mapping table is re-executed twice: once at the observation root (pre-R1)
   and once at the C10 rebuilt execution workspace (post-R1). The measured
   outcome is compared with the **frozen** prediction.

3. **Coverage report** — how many of the mapped items the alignment actually
   resolves, and where the measurement departs from the pre-registration.

PRE-REGISTRATION DISCIPLINE
---------------------------
The §16 design is **read-only** here: this script opens the preregistration
for reading only and never writes to it. The replay result must not be
written back into the §16 design — a departure is reported as a measurement,
and belongs to a later §17 appendix, never to §16 itself.

The C10 execution workspace is rebuilt from the sealed run directory with the
frozen `blind.rebuild_workspace` helper (dual-placement registry + canonical
`products/T##/` tree, every file hash-verified), so the replay is
self-contained: it needs the custody tree and the sealed package, nothing
else.

CLI
---
    python tools/eval/replay_r1.py --round7-custody DIR [--round6-custody DIR]
        [--pkg7 DIR] [--pkg6 DIR] [--prereg FILE] [--root DIR]
        [--out FILE]

Exit codes: 0 = ok; 1 = operational error; 2 = usage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import blind  # noqa: E402
import dsl_compiler  # noqa: E402
import shadow_align  # noqa: E402

#: repository root — the workspace must be rebuilt INSIDE it (see
#: rebuild_workspace): a criterion that is observable inside the repository
#: (git) is not observable outside it.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

#: §16 mapping-table row. The basis column may contain escaped pipes, so the
#: row is matched field by field instead of being split on "|".
_MAPPING_ROW_RE = re.compile(
    r"^\|\s*`(?P<cid>P\d{3}-c\d{2})`\s*"
    r"\|\s*(?P<arm>[AB])\s*"
    r"\|\s*(?P<own>[^|]+?)\s*"
    r"\|\s*`(?P<pred>[^`]+)`\s*"
    r"\|\s*(?P<sens>[^|]+?)\s*"
    r"\|\s*(?P<before>通过|不通过)\s*"
    r"\|\s*\*\*(?P<after>通过|不通过)\*\*\s*"
    r"\|\s*(?P<main>E\d)\s*"
    r"\|\s*(?P<verdict>\*\*不消解\*\*|消解)\s*\|",
    re.M)

_ROW_OWNERS = ("I2 命令观测面", "I3 产物面", "轮六-I2 命令观测面")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_prereg_mapping(prereg: Path) -> Tuple[Dict[str, dict], str]:
    """Read the §16 expected-resolution mapping table (READ ONLY).

    Returns (mapping, section_sha256). The preregistration is never written
    to by this tool -- the freeze discipline depends on it."""
    text = prereg.read_text(encoding="utf-8")
    index = text.find("## §16 变更记录")
    if index < 0:
        raise ValueError("§16 section not found in the preregistration")
    section = text[index:]
    mapping: Dict[str, dict] = {}
    for match in _MAPPING_ROW_RE.finditer(section):
        row = match.groupdict()
        mapping[row["cid"]] = {
            "claim_id": row["cid"],
            "arm": row["arm"],
            "owner": row["own"],
            "predicate": row["pred"],
            "sensitivity": row["sens"],
            "predicted_before": row["before"],
            "predicted_after": row["after"],
            "predicted_main": row["main"],
            "predicted_verdict": row["verdict"].replace("*", ""),
        }
    return mapping, hashlib.sha256(section.encode("utf-8")).hexdigest()


def load_records(path: Path) -> List[dict]:
    """Load a records JSONL file, skipping the `_meta` header line."""
    out: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if "_meta" in rec:
            continue
        out.append(rec)
    return out


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def claim_index(claims_by_code: Dict[str, list], claim_id: str) -> Optional[int]:
    """Index (0-based) of the claim a `<code>-c<NN>` id refers to."""
    code, _, num = claim_id.rpartition("-c")
    if code not in claims_by_code:
        return None
    try:
        return int(num) - 1
    except ValueError:
        return None


def main_level_for(levels_by_code: Dict[str, list], claim_id: str) -> Optional[str]:
    index = claim_index(_LEVELS_CACHE["claims"], claim_id)
    if index is None:
        return None
    code = claim_id.rpartition("-c")[0]
    judgements = _LEVELS_CACHE["levels"].get(code, [])
    if index >= len(judgements):
        return None
    return judgements[index].get("level")


#: module-level cache so main_level_for() can stay a one-liner
_LEVELS_CACHE: Dict[str, dict] = {"claims": {}, "levels": {}}


def rebuild_workspace(run_dir: Path, work_dir: Path) -> Dict[str, object]:
    """Rebuild the C10 execution workspace from a sealed run directory.

    ``work_dir`` MUST sit on the same surface class as the workspace the main
    track judged against — inside the repository. That is not cosmetic: a
    ``git log``-style criterion is observable inside the repository and fails
    outside it, so a workspace in a temp directory would measure a different
    face than the run does. R1's whole claim is "both instruments read the
    same face", so the replay has to be on that face too."""
    package_dir = work_dir / "pkg"
    package_dir.mkdir(parents=True, exist_ok=True)
    meta = blind.rebuild_workspace(run_dir, package_dir)
    return {
        "workspace": str(package_dir / blind.WORKSPACE_DIR_NAME),
        "file_count": meta.get("file_count"),
        "manifest_sha256": meta.get("manifest_sha256"),
        "registry_missing": meta.get("registry_missing"),
        "registry_present": meta.get("registry_present"),
        "in_repository": _is_inside_repo(package_dir),
    }


def _is_inside_repo(path: Path) -> bool:
    try:
        Path(path).resolve().relative_to(REPO_ROOT)
        return True
    except (ValueError, OSError):
        return False


def replay_record(record: dict, root: Path, workspace: Optional[Path]
                  ) -> Tuple[bool, dict]:
    """Execute one record on a given surface. Returns (predicate_ok, result)."""
    result = dsl_compiler.execute_record(record, root, 30, workspace=workspace)
    return bool(result.get("predicate_ok")), result


def consistency(predicate_ok: bool, main_level: Optional[str]) -> Optional[bool]:
    """§12 D4 rule: consistent = bool(predicate_ok) == (level == 'E4').

    Returns None when the main level is unavailable (no comparable pair)."""
    if main_level is None:
        return None
    return predicate_ok == (main_level == "E4")


def replay_round(round_id: str, custody: Path, pkg: Path, run_dir_name: str,
                 shadow_dir_name: str, mapping: Dict[str, dict], root: Path,
                 work_dir: Path, arms: Tuple[str, ...] = ("A",)) -> dict:
    """Replay one round's sealed mismatch samples on both surfaces."""
    claims_by_code = load_json(pkg / "claims.json")
    levels_by_code = load_json(pkg / "judgements-blind.json")
    _LEVELS_CACHE["claims"] = claims_by_code
    _LEVELS_CACHE["levels"] = levels_by_code

    run_dir = custody / run_dir_name
    shadow_dir = custody / shadow_dir_name
    surface = rebuild_workspace(run_dir, work_dir / round_id)
    workspace = Path(surface["workspace"])

    records_by_arm: Dict[str, Dict[str, dict]] = {}
    for arm in arms:
        records_path = shadow_dir / "primary" / arm / f"records-{arm}.jsonl"
        records_by_arm[arm] = {r["claim_id"]: r
                               for r in load_records(records_path)}

    items: List[dict] = []
    for claim_id, expected in sorted(mapping.items()):
        arm = expected["arm"]
        record = records_by_arm.get(arm, {}).get(claim_id)
        main_level = main_level_for(levels_by_code, claim_id)
        row = {
            "claim_id": claim_id,
            "owner": expected["owner"],
            "arm": arm,
            "predicate": expected["predicate"],
            "predicted_before": expected["predicted_before"],
            "predicted_after": expected["predicted_after"],
            "predicted_main": expected["predicted_main"],
            "predicted_verdict": expected["predicted_verdict"],
            "main_level": main_level,
        }
        if record is None:
            row["error"] = "no sealed record for this claim id in this round"
            items.append(row)
            continue
        before_ok, before_res = replay_record(record, root, None)
        after_ok, after_res = replay_record(record, root, workspace)
        row["actual_before"] = "通过" if before_ok else "不通过"
        row["actual_after"] = "通过" if after_ok else "不通过"
        row["consistent_before"] = consistency(before_ok, main_level)
        row["consistent_after"] = consistency(after_ok, main_level)
        # §16 table semantics: 消解 = the item is consistent AFTER the fix;
        # 不消解 = it is still inconsistent. The transition is reported
        # separately so a broken-consistency case can never hide inside the
        # "still inconsistent" bucket.
        row["actual_verdict"] = ("消解" if row["consistent_after"]
                                 else "不消解")
        if row["consistent_before"] is False and row["consistent_after"] is False:
            row["transition"] = "仍不一致"
        elif row["consistent_before"] is False and row["consistent_after"] is True:
            row["transition"] = "消解"
        elif row["consistent_before"] is True and row["consistent_after"] is True:
            row["transition"] = "保持一致"
        else:
            row["transition"] = "一致被破坏"
        row["matches_prediction"] = (
            row["actual_before"] == expected["predicted_before"]
            and row["actual_after"] == expected["predicted_after"]
            and row["actual_verdict"] == expected["predicted_verdict"])
        row["cwd_before"] = before_res.get("cwd")
        row["cwd_after"] = after_res.get("cwd")
        row["artifact_surface_after"] = after_res.get("artifact_surface")
        items.append(row)

    measured = [i for i in items if "error" not in i]
    resolved = [i for i in measured if i["actual_verdict"] == "消解"]
    predicted_resolved = [i for i in measured
                          if i["predicted_verdict"] == "消解"]
    return {
        "round": round_id,
        "custody": str(custody),
        "package": str(pkg),
        "workspace_rebuild": surface,
        "mapped_items": len(items),
        "measured_items": len(measured),
        "errors": [i["claim_id"] for i in items if "error" in i],
        "predicted_resolved": len(predicted_resolved),
        "measured_resolved": len(resolved),
        "prediction_matches": sum(1 for i in measured if i["matches_prediction"]),
        "prediction_departures": [
            {"claim_id": i["claim_id"], "owner": i["owner"],
             "predicted": {"before": i["predicted_before"],
                           "after": i["predicted_after"],
                           "verdict": i["predicted_verdict"],
                           "main": i["predicted_main"]},
             "measured": {"before": i.get("actual_before"),
                          "after": i.get("actual_after"),
                          "verdict": i.get("actual_verdict"),
                          "transition": i.get("transition"),
                          "main": i["main_level"]}}
            for i in measured if not i["matches_prediction"]],
        "items": items,
    }


def reproduce_pre_r1(custody: Path, pkg: Path, shadow_dir_name: str,
                      root: Path) -> dict:
    """Re-run the aligner on the OLD surface and compare with the frozen
    alignment split, claim by claim (round-8 ADV-1 closure)."""
    claims_by_code = load_json(pkg / "claims.json")
    levels_by_code = load_json(pkg / "judgements-blind.json")

    main_by_code: Dict[str, List[dict]] = {}
    for code, claims in claims_by_code.items():
        rows = []
        for idx, claim in enumerate(claims):
            judgements = levels_by_code.get(code, [])
            level = judgements[idx].get("level") if idx < len(judgements) else None
            rows.append({**claim, "_level": level})
        main_by_code[code] = rows

    records_by_code: Dict[str, List[dict]] = {}
    for arm in ("A", "B"):
        path = custody / shadow_dir_name / "primary" / arm / f"records-{arm}.jsonl"
        per_arm: Dict[str, List[dict]] = {}
        for rec in load_records(path):
            code = rec["claim_id"].rpartition("-c")[0]
            per_arm.setdefault(code, []).append(rec)
        records_by_code[f"{arm}"] = per_arm

    frozen_path = custody / shadow_dir_name / "alignment-split.json"
    frozen = load_json(frozen_path)
    report = {"frozen_alignment": str(frozen_path), "per_arm": {}}
    total_same = total_diff = 0
    for arm in ("A", "B"):
        result = shadow_align.align(main_by_code, records_by_code[arm], root)
        frozen_arm = frozen.get("per_arm", {}).get(arm, {})
        same = diff = 0
        examples = []
        for code, product in frozen_arm.get("per_product", {}).items():
            frozen_flags = product.get("consistent_flags") or {}
            replay_flags = (result["per_product"].get(code, {})
                            .get("consistent_flags") or {})
            for claim_id, flag in frozen_flags.items():
                if claim_id not in replay_flags:
                    diff += 1
                    if len(examples) < 5:
                        examples.append({"claim_id": claim_id, "frozen": flag,
                                         "replay": None})
                elif bool(replay_flags[claim_id]) == bool(flag):
                    same += 1
                else:
                    diff += 1
                    if len(examples) < 5:
                        examples.append({"claim_id": claim_id, "frozen": flag,
                                         "replay": replay_flags[claim_id]})
        total_same += same
        total_diff += diff
        report["per_arm"][arm] = {
            "frozen_comparable": frozen_arm.get("totals", {}).get("comparable_pairs"),
            "replay_comparable": result["totals"]["comparable_pairs"],
            "frozen_agreement_rate": frozen_arm.get("totals", {}).get("agreement_rate"),
            "replay_agreement_rate": result["totals"]["agreement_rate"],
            "flags_equal": same,
            "flags_differ": diff,
            "difference_examples": examples,
        }
    report["total_flags_equal"] = total_same
    report["total_flags_differ"] = total_diff
    report["verdict"] = ("reproduced" if total_diff == 0
                          else "NOT reproduced -- see difference_examples")
    return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="v1.8 R1 off-line replay (§16; card XJ-20261110-001 D2)")
    ap.add_argument("--round7-custody", metavar="DIR", required=True,
                    help="round-7 custody root (holds run-dir-r7/ and shadow-r7/)")
    ap.add_argument("--round6-custody", metavar="DIR", default=None,
                    help="round-6 custody root (holds the 24 round-6 mapped items)")
    ap.add_argument("--pkg7", metavar="DIR", default=None,
                    help="sealed round-7 package (claims.json + judgements-blind.json)")
    ap.add_argument("--pkg6", metavar="DIR", default=None,
                    help="sealed round-6 package")
    ap.add_argument("--prereg", default="docs/eval-prereg.md",
                    help="preregistration carrying the §16 mapping table (READ ONLY)")
    ap.add_argument("--root", default=".",
                    help="observation root (the pre-R1 surface)")
    ap.add_argument("--workspace-parent", metavar="DIR", default=None,
                    help="where the C10 workspace is rebuilt — must be inside "
                         "the repository so the replay reads the same face as "
                         "the run (default: <repo>/.eval-sealed/)")
    ap.add_argument("--out", metavar="FILE", default=None,
                    help="write the machine-readable replay report")
    ap.add_argument("--keep-workspace", action="store_true",
                    help="keep the rebuilt workspace directory for inspection")
    args = ap.parse_args(argv)

    repo = Path(__file__).resolve().parent.parent.parent
    prereg = Path(args.prereg)
    if not prereg.is_absolute():
        prereg = repo / prereg
    root = Path(args.root)
    if not root.is_absolute():
        root = repo / root

    try:
        mapping, section_sha = parse_prereg_mapping(prereg)
    except (OSError, ValueError) as exc:
        print(f"[ERROR] preregistration mapping table unreadable: {exc}",
              file=sys.stderr)
        return 2
    if not mapping:
        print("[ERROR] §16 mapping table is empty", file=sys.stderr)
        return 2

    sealed = repo / ".eval-sealed"
    pkg7 = Path(args.pkg7) if args.pkg7 else sealed / "pkg-r7-shadow"
    pkg6 = Path(args.pkg6) if args.pkg6 else sealed / "pkg-r6-shadow"
    r7 = Path(args.round7_custody)
    r6 = Path(args.round6_custody) if args.round6_custody else None

    work_parent = Path(args.workspace_parent) if args.workspace_parent else (
        repo / ".eval-sealed")
    work_parent.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="replay-r1-", dir=str(work_parent)))
    try:
        report: Dict[str, object] = {
            "schema": "agent-covenant/replay-r1/v1",
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": ("off-line replay of the sealed mismatch samples on the "
                     "R1-aligned observation surface; the §16 design is READ "
                     "ONLY here -- the replay result must not be written back "
                     "into it"),
            "prereg": {
                "path": str(prereg),
                "section": "§16",
                "section_sha256": section_sha,
                "mapped_rows": len(mapping),
            },
            "instrument": {
                "dsl_compiler_sha256": sha256_file(
                    Path(__file__).resolve().parent / "dsl_compiler.py"),
                "shadow_align_sha256": sha256_file(
                    Path(__file__).resolve().parent / "shadow_align.py"),
                "replay_r1_sha256": sha256_file(Path(__file__).resolve()),
            },
            "observation_root": str(root),
            "rounds": {},
        }

        # --- round 7: pre-R1 reproduction + per-item replay -------------------
        r7_mapping = {cid: row for cid, row in mapping.items()
                      if row["owner"] != "轮六-I2 命令观测面"}
        report["rounds"]["7"] = replay_round(
            "7", r7, pkg7, "run-dir-r7", "shadow-r7", r7_mapping, root,
            work_dir / "round7")
        report["rounds"]["7"]["pre_r1_reproduction"] = reproduce_pre_r1(
            r7, pkg7, "shadow-r7", root)

        # --- round 6: the 24 round-6 mapped items ---------------------------
        if r6 is not None:
            r6_mapping = {cid: row for cid, row in mapping.items()
                          if row["owner"] == "轮六-I2 命令观测面"}
            if r6_mapping:
                report["rounds"]["6"] = replay_round(
                    "6", r6, pkg6, "run-dir-r6", "shadow-r6", r6_mapping, root,
                    work_dir / "round6")

        measured = []
        predicted_resolved = 0
        for round_report in report["rounds"].values():
            measured.append(round_report["measured_items"])
            predicted_resolved += round_report["predicted_resolved"]
        report["summary"] = {
            "rounds_replayed": sorted(report["rounds"].keys()),
            "mapped_rows_in_prereg": len(mapping),
            "mapped_items_measured": sum(measured),
            "predicted_resolved_total": predicted_resolved,
            "measured_resolved_total": sum(
                r["measured_resolved"] for r in report["rounds"].values()),
            "prediction_matches_total": sum(
                r["prediction_matches"] for r in report["rounds"].values()),
            "pre_r1_reproduction_verdict": report["rounds"]["7"]
            ["pre_r1_reproduction"]["verdict"],
        }
        payload = json.dumps(report, ensure_ascii=False, indent=2)
        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8", newline="") as fh:
                fh.write(payload + "\n")
            print(f"replay report -> {out_path}")
            print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
        else:
            print(payload)
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"[ERROR] replay failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if not args.keep_workspace:
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
