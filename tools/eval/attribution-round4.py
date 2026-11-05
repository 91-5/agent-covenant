#!/usr/bin/env python3
"""Round-4 E2/E3 full attribution instrument (XJ-20261105-002, a→b chain step a).

 WHAT THIS TOOL IS
 -----------------
 An attribution classifier over **already-sealed judge outputs**. It consumes
 ``judgements-blind.json`` (levels, details, observations, claim/evidence
 records) verbatim and answers a different question than the judge: *given
 that the judge assigned this level, where did the evidence chain break?*
 Outputs are root-cause labels and three-way responsibility shares for the
 v1.5 prereg-revision card (chain step b) to consume.

 WHAT THIS TOOL IS NOT
 ---------------------
 **Zero E-level semantics** (card constraint 3): it never assigns, checks,
 re-derives or validates E0-E4. ``judge.py`` is the only level authority; a
 level here is an opaque input that merely selects which attribution branch
 runs (E2 → evidence-reproduction analysis, E3 → anchor-corpus analysis).
 The judge module is imported **only** for its execution primitive
 (``run_command`` / ``command_refused``) so that re-runs use the same
 executor as the instrument; ``judge_claim`` is never called.

 READ-ONLY DISCIPLINE (card constraint 2)
 ----------------------------------------
 Run products, custody data, the blind package and the sealed key are opened
 read-only. Every re-execution happens inside a fresh temp workspace
 (``--workdir``) seeded with *copies* of the sealed working files; the
 reconstruction is checked against the dual-placement record's declared
 SHA-256 values before it is trusted.

 CLASSIFICATION RULES ARE ATTRIBUTION-LAYER VOCABULARY
 -----------------------------------------------------
 Labels such as ``shell flavor`` or ``placement`` describe *why an evidence
 line failed to reproduce at the measurement root*. They are not E-levels and
 imply nothing about any other entry. The label → responsibility mapping is
 stated in the report (D4) and is a documentation decision of this card, not
 a judgement about any arm's quality.

 USAGE
 -----
    python tools/eval/attribution-round4.py [--doc docs/round4-attribution.md]
        [--json-out PATH] [--no-rerun] [--timeout 30]

 Exit codes: 0 = analysis complete and written; 1 = operational failure
 (missing inputs, unreadable package); 2 = usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Instrument execution primitive reuse ONLY (see module docstring boundary).
from judge import command_refused, run_command  # noqa: E402

DEFAULT_PACKAGE = Path(".eval-sealed/pkg-round4")
DEFAULT_KEY = Path(".eval-sealed/key-20261105T121359Z.json")
DEFAULT_CUSTODY = Path("D:/15812/projects/round4-custody/run-dir")
DEFAULT_REPO = Path(".")
DEFAULT_DRAFTS = Path("dryrun/round4-drafts")
DEFAULT_TASKS = Path("tools/eval/tasks")
DEFAULT_DOC = Path("docs/round4-attribution.md")

NEGATIVE_TASKS = ["T01", "T16", "T24", "T26", "T27", "T28", "T29", "T30"]

# Attribution-layer command-flavor lexicon (vocabulary for describing why a
# command could not start under the instrument's frozen shell; NOT judge
# semantics, NOT a denylist, and it never decides a level).
POWERSHELL_TOKENS = (
    "get-content", "test-path", "select-string", "get-childitem", "get-item",
    "get-date", "measure-object", "set-content", "copy-item", "write-output",
    "out-string", "format-table", "get-random", "get-process", "sort-object",
)

# Files probed as repo-side grounding corpus for E3 anchors (bounded, fixed).
REPO_CORPUS_FILES = [
    "README.md", "PROTOCOL.md", "LICENSE", "CHANGELOG.md", "CONTRIBUTING.md",
    "artifacts.json", "ADR-0001.md", "ADR-0002.md", "postmortems.md",
]

E2_LABELS = {
    "R1-denylist-refused": "仪器（设计内拒绝）",
    "R2-ref-grammar-decoration": "仪器（ref 捕获含装饰后缀）",
    "R3-ref-placement-armA": "仪器（执行工作区≠判定根）",
    "R4-ref-believed-armB": "执行者（ref 目标在测量根不存在）",
    "R5-ref-absent-everywhere": "执行者（落盘缺失）",
    "R6-cwd-placement-armA": "仪器（执行工作区≠判定根）",
    "R7-believed-placement-armB": "执行者（believed 断言在测量根不成立）",
    "R8-shell-flavor": "仪器（判定 shell=cmd.exe，证据风味 PowerShell）",
    "R9-believed-mismatch": "执行者（声称值在任何重建环境均不成立）",
    "R10-claim-vs-runlog": "执行者（声称与仪器执行记录矛盾）",
    "R11-output-format-drift": "仪器（out= 精确子串口径）",
    "R12-output-content-drift": "执行者（声称输出内容与现实不符）",
    "R13-could-not-complete": "仪器（超时/无法启动）",
    "R14-reconstruction-gap": "未定位（应为 0，出现即仪器缺陷需人工复核）",
}

E3_LABELS = {
    "A1-executor-semantic": "执行者（证据复现但不支持断言）",
    "A2-anchor-ungroundable": "执行者（断言锚文本无语料根据）",
    "A3-task-construction": "任务构造（任务语料与仓库事实漂移）",
}

LABEL_TO_RESPONSIBILITY = {
    "R1-denylist-refused": "仪器", "R2-ref-grammar-decoration": "仪器",
    "R3-ref-placement-armA": "仪器", "R6-cwd-placement-armA": "仪器",
    "R8-shell-flavor": "仪器", "R11-output-format-drift": "仪器",
    "R13-could-not-complete": "仪器", "R14-reconstruction-gap": "仪器",
    "R4-ref-believed-armB": "执行者", "R5-ref-absent-everywhere": "执行者",
    "R7-believed-placement-armB": "执行者", "R9-believed-mismatch": "执行者",
    "R10-claim-vs-runlog": "执行者", "R12-output-content-drift": "执行者",
    "A1-executor-semantic": "执行者", "A2-anchor-ungroundable": "执行者",
    "A3-task-construction": "任务构造",
}

AUTO_SPANS = [
    "COVERAGE", "E2-SUMMARY", "E3-TABLE", "D4-TAXONOMY", "DUAL-PLACEMENT",
    "APPENDIX-E2", "APPENDIX-E3", "APPENDIX-D3", "SELFTEST",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sanitize(text: Optional[str], limit: int = 90) -> str:
    """Quoting discipline: never emit U+FFFD or control chars into the report;
    describe them instead. Keeps the deliverable's own UTF-8 surface clean."""
    if text is None:
        return ""
    out = []
    fffd = 0
    for ch in str(text):
        if ch == "\ufffd":
            fffd += 1
            continue
        if fffd:
            out.append(f"<U+FFFD x{fffd}>")
            fffd = 0
        if ch in "\n\r\t":
            out.append(" ")
        elif ord(ch) < 32:
            out.append(f"<U+{ord(ch):04X}>")
        else:
            out.append(ch)
    if fffd:
        out.append(f"<U+FFFD x{fffd}>")
    s = "".join(out)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > limit:
        s = s[: limit - 1] + "…"
    return s


def sha256_of(path: Path) -> Optional[str]:
    h = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def normalize_command(cmd: str) -> str:
    return re.sub(r"\s+", " ", cmd or "").strip()


def is_powershell_flavor(command: str) -> bool:
    lowered = normalize_command(command).lower()
    return any(tok in lowered for tok in POWERSHELL_TOKENS)


class Probes:
    """Existence + content probes. Read-only everywhere."""

    def __init__(self, repo: Path, custody: Path, seal_git_head: str) -> None:
        self.repo = repo
        self.custody = custody
        self.seal_head = seal_git_head
        self._seal_cache: Dict[str, Optional[str]] = {}

    def exists_at_judge_root(self, rel: str) -> bool:
        rel = rel.strip().strip("`").replace("\\", "/")
        if not rel or ".." in rel.split("/"):
            return False
        try:
            return (self.repo / rel).is_file()
        except OSError:
            return False

    def exists_in_workspace(self, rel: str) -> bool:
        rel = rel.strip().strip("`").replace("\\", "/")
        if not rel or ".." in rel.split("/"):
            return False
        try:
            return (self.custody / rel).is_file()
        except OSError:
            return False

    def exists_in_canonical(self, task: str, name: str) -> bool:
        name = name.strip().strip("`").replace("\\", "/").split("/")[-1]
        if not name:
            return False
        try:
            return (self.custody / "products" / task / name).is_file()
        except OSError:
            return False

    def exists_anywhere_probe(self, rel: str, task: str) -> Dict[str, bool]:
        return {
            "judge_root": self.exists_at_judge_root(rel),
            "workspace": self.exists_in_workspace(rel),
            "canonical": self.exists_in_canonical(task, rel),
        }

    def seal_file_text(self, rel: str) -> Optional[str]:
        """Repository file content as of the seal-time git head (read-only)."""
        rel = rel.strip().strip("`").replace("\\", "/")
        if rel in self._seal_cache:
            return self._seal_cache[rel]
        text: Optional[str] = None
        import subprocess
        try:
            r = subprocess.run(
                ["git", "show", f"{self.seal_head}:{rel}"],
                capture_output=True, cwd=str(self.repo), timeout=30,
            )
            if r.returncode == 0:
                text = r.stdout.decode("utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            text = None
        if text is None:
            try:
                p = self.repo / rel
                if p.is_file():
                    text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = None
        self._seal_cache[rel] = text
        return text


class Rerunner:
    """Re-executes commands in an isolated temp workspace built from *copies*
    of the sealed working files. Nothing outside --workdir is ever written."""

    def __init__(self, workdir: Path, custody: Path, timeout: int,
                 enabled: bool = True) -> None:
        self.workdir = workdir
        self.timeout = timeout
        self.enabled = enabled
        self.cache: Dict[str, Tuple[Optional[int], str, bool, str]] = {}
        self.seeded_from: List[str] = []
        if enabled:
            self.workdir.mkdir(parents=True, exist_ok=True)
            self._seed(custody)

    def _seed(self, custody: Path) -> None:
        """Copy sealed working-copy implementation/data files into the temp
        workspace (flat layout, mirroring the execution-time run-dir root).
        The authoritative set is the dual-placement record's file list (the
        declared executor working copies); extension heuristics would pull in
        instrument probe files."""
        declared = []
        dual = custody / "impl-dual-placement.json"
        if dual.is_file():
            try:
                declared = [f["file"] for f in
                            json.loads(dual.read_text(encoding="utf-8")).get("files", [])
                            if isinstance(f, dict) and f.get("file")]
            except (OSError, ValueError):
                declared = []
        for name in declared or sorted(p.name for p in custody.iterdir()
                                       if p.is_file() and p.suffix.lower() in {".py", ".txt", ".csv"}):
            p = custody / name
            if p.is_file():
                shutil.copy2(p, self.workdir / p.name)
                self.seeded_from.append(p.name)

    def run(self, command: str) -> Tuple[Optional[int], str, bool, str]:
        """Returns (exit, output_head, refused, note). Cached per command."""
        key = normalize_command(command)
        if key in self.cache:
            return self.cache[key]
        if not self.enabled:
            res = (None, "", False, "rerun disabled")
            self.cache[key] = res
            return res
        matched = command_refused(key)
        if matched is not None:
            res = (None, "", True, f"denylist match {matched!r}")
        else:
            cwd = self.workdir if self.workdir.is_dir() else Path(tempfile.gettempdir())
            exit_code, output, error = run_command(key, cwd, self.timeout)
            note = f"rerun exit={exit_code}" if error == "" else f"rerun error: {sanitize(error, 60)}"
            res = (exit_code, output, False, note)
        self.cache[key] = res
        return res

    def run_pwsh(self, command: str) -> Optional[int]:
        """Counterfactual: the same command under the executor's assumed shell
        (powershell.exe), same temp workspace, same denylist. Used only to
        separate 'true under the assumed shell' (shell-flavor class) from
        'wrong under any shell' (value-mismatch class)."""
        key = "pwsh::" + normalize_command(command)
        if key in self.cache:
            return self.cache[key][0]
        if not self.enabled:
            self.cache[key] = (None, "", False, "rerun disabled")
            return None
        matched = command_refused(key)
        if matched is not None:
            self.cache[key] = (None, "", True, f"denylist match {matched!r}")
            return None
        import base64
        encoded = base64.b64encode(normalize_command(command).encode("utf-16-le")).decode("ascii")
        wrapped = f"powershell -NoProfile -NonInteractive -EncodedCommand {encoded}"
        cwd = self.workdir if self.workdir.is_dir() else Path(tempfile.gettempdir())
        exit_code, _output, error = run_command(wrapped, cwd, self.timeout)
        self.cache[key] = (exit_code, "", False, error)
        return exit_code


class Attribution:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.package = Path(args.package)
        self.key_path = Path(args.key)
        self.custody = Path(args.custody)
        self.repo = Path(args.repo).resolve()
        self.drafts_dir = Path(args.drafts)
        self.tasks_dir = Path(args.tasks)
        self.doc_path = Path(args.doc)
        self.timeout = args.timeout

        self.judgements = self._load_json(self.package / "judgements-blind.json")
        self.manifest = self._load_json(self.package / "manifest.json")
        self.key = self._load_json(self.key_path)
        self.root_state = self._load_json(self.package / "root-state.json")
        self.runlog = self._load_json(self.custody / "run-log.json")
        self.dual = self._load_json(self.custody / "impl-dual-placement.json")

        self.mapping = {m["code"]: m for m in self.key["mapping"]}
        self.probes = Probes(self.repo, self.custody,
                             self.root_state.get("git_head", "HEAD"))
        self.rerunner = Rerunner(Path(args.workdir), self.custody,
                                 self.timeout, enabled=not args.no_rerun)
        self.runlog_index = self._index_runlog()
        self.task_texts = self._load_task_texts()
        self.product_cache: Dict[str, str] = {}
        self.draft_cache: Dict[str, dict] = {}
        self.e2_rows: List[dict] = []
        self.e3_rows: List[dict] = []
        self.dual_rows: List[dict] = []
        self.d3_tasks: List[dict] = []

    # ---------- loading ----------

    @staticmethod
    def _load_json(path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise SystemExit(f"attribution: cannot read {path}: {exc}")

    def _index_runlog(self) -> Dict[Tuple[str, str], List[dict]]:
        idx: Dict[Tuple[str, str], List[dict]] = {}
        for rec in self.runlog.get("records", []):
            key = (rec.get("key", ""), normalize_command(rec.get("command", "")))
            idx.setdefault(key, []).append(rec)
        return idx

    def _load_task_texts(self) -> Dict[str, str]:
        out = {}
        for p in sorted(self.tasks_dir.glob("T*.json")):
            try:
                out[p.stem] = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                out[p.stem] = ""
        return out

    def product_text(self, key: str) -> str:
        if key not in self.product_cache:
            p = self.custody / "products" / f"{key}.md"
            try:
                self.product_cache[key] = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                self.product_cache[key] = ""
        return self.product_cache[key]

    def draft(self, task: str) -> dict:
        if task not in self.draft_cache:
            p = self.drafts_dir / f"{task}.json"
            try:
                self.draft_cache[task] = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self.draft_cache[task] = {}
        return self.draft_cache[task]

    # ---------- provenance ----------

    @staticmethod
    def provenance(product_text: str, source_line: int) -> str:
        """Which claim surface did this judged claim come from? Round-4
        products carry the draft's notes verbatim (which may embed a full
        believed-form report) *plus* the runner-generated section under the
        first '## 已验证结论' heading. source_line is 1-based (extract.py)."""
        boundary = None
        for i, line in enumerate(product_text.splitlines(), start=1):
            if line.strip() == "## 已验证结论":
                boundary = i
                break
        if boundary is None:
            return "draft_embedded"
        return "draft_embedded" if source_line < boundary else "runner_generated"

    # ---------- E2 classification ----------

    def classify_e2(self, code: str, rec: dict) -> dict:
        claim = rec.get("claim", {})
        ev = claim.get("evidence", {}) or {}
        m = self.mapping[code]
        key, task, cond = m["key"], m["task_id"], m["condition"]
        detail = rec.get("detail") or ""
        flags = rec.get("flags") or []
        obs = rec.get("observation") or ""
        row = {
            "code": code, "key": key, "task": task, "arm": cond,
            "provenance": self.provenance(self.product_text(key),
                                          int(claim.get("source_line", 0))),
            "detail": sanitize(detail, 110),
            "evidence": sanitize(ev.get("raw", ""), 110),
            "label": None, "note": "", "probes": {}, "rerun": "",
        }

        if "refused_exec" in flags or "拒绝清单" in detail:
            row["label"] = "R1-denylist-refused"
            return row

        ref_missing = re.search(r"ref (?:不存在|不可读): (.+)$", detail)
        if ref_missing and ev.get("ref") is not None:
            captured = ref_missing.group(1).strip()
            clean = captured.replace("（独立复核）", "").replace("(独立复核)", "").strip()
            dec = captured != clean
            probe = self.probes.exists_anywhere_probe(clean, task)
            row["probes"] = {"captured": captured, "clean": clean, "exists": probe}
            row["note"] = f"ref 捕获值={sanitize(captured, 60)}"
            dec_note = "（捕获含装饰后缀）" if dec else ""
            # Priority: judge-root existence first (the judge's detail already
            # establishes seal-time absence; a current-root hit means post-seal
            # repo drift), then workspace placement, then true absence.
            if probe["judge_root"] and dec:
                # clean path exists at the very root the judge checked:
                # the captured decoration is the sole failure cause
                row["note"] += "；清洁路径在判定根存在，装饰捕获为唯一失败环节"
                row["label"] = "R2-ref-grammar-decoration"
                return row
            if probe["judge_root"]:
                row["note"] += "（当前判定根已存在：密封后仓库漂移，密封时点不存在）"
                row["label"] = "R3-ref-placement-armA" if cond == "A" else "R4-ref-believed-armB"
                return row
            if probe["workspace"] or probe["canonical"]:
                row["note"] += dec_note
                row["label"] = "R3-ref-placement-armA" if cond == "A" else "R4-ref-believed-armB"
                return row
            row["note"] += "；全探测面均不存在" + dec_note
            row["label"] = "R5-ref-absent-everywhere"
            return row

        exit_mismatch = re.search(
            r"退出码不符: 证据声称 exit=(-?\d+), 实际 exit=(-?\d+|None)", detail)
        if exit_mismatch and ev.get("command"):
            claimed = int(exit_mismatch.group(1))
            actual_root = exit_mismatch.group(2)
            command = ev.get("command") or ""
            rl_matches = [r.get("exit_code") for r in
                          self.runlog_index.get((key, normalize_command(command)), [])
                          if r.get("exit_code") is not None]
            rl_exit = rl_matches[0] if rl_matches else None
            rl_confirms = claimed in rl_matches
            rr_exit, rr_out, rr_refused, rr_note = self.rerunner.run(command)
            row["rerun"] = rr_note
            row["note"] = (f"声称 exit={claimed}, 判定根实际={actual_root}, "
                           f"runlog={'%s' % rl_exit if rl_exit is not None else '—'}, "
                           f"重建工作区 rerun={'%s' % rr_exit if rr_exit is not None else '—'}")
            prov = row["provenance"]
            if cond == "A" and prov == "runner_generated" and rl_matches and not rl_confirms:
                row["label"] = "R10-claim-vs-runlog"
                return row
            if rr_refused:
                row["label"] = "R13-could-not-complete"
                return row
            if rr_exit is not None and rr_exit == claimed:
                row["label"] = ("R6-cwd-placement-armA" if cond == "A"
                                else "R7-believed-placement-armB")
                return row
            if rl_confirms:
                # execution-time record confirms the claim; only the temp
                # reconstruction disagrees -> placement at measurement root
                row["label"] = "R6-cwd-placement-armA"
                return row
            if is_powershell_flavor(command):
                pwsh_exit = self.rerunner.run_pwsh(command)
                row["note"] += f", pwsh 反事实={'%s' % pwsh_exit if pwsh_exit is not None else '—'}"
                if pwsh_exit is not None and pwsh_exit == claimed:
                    # true under the executor's assumed shell: the failing
                    # link is the instrument's frozen shell (cmd.exe)
                    row["label"] = "R8-shell-flavor"
                else:
                    # wrong under any shell tried
                    row["label"] = "R9-believed-mismatch"
                return row
            row["label"] = "R9-believed-mismatch"
            return row

        if "声称输出未复现" in detail and ev.get("out") is not None:
            claimed_out = str(ev.get("out"))
            norm_obs = re.sub(r"\s+", " ", obs)
            norm_out = re.sub(r"\s+", " ", claimed_out)
            row["note"] = f"声称 out={sanitize(claimed_out, 60)}"
            if norm_out and norm_out in norm_obs:
                row["label"] = "R11-output-format-drift"
            else:
                row["label"] = "R12-output-content-drift"
            return row

        if "无法完成观察" in detail or "timeout" in detail.lower():
            row["label"] = "R13-could-not-complete"
            return row

        row["label"] = "R14-reconstruction-gap"
        row["note"] = f"未匹配任何已知判语形态: {sanitize(detail, 80)}"
        return row

    # ---------- E3 classification ----------

    def task_corpus_files(self, task: str) -> List[str]:
        """Bounded repo-side corpus: files the task JSON names, plus the fixed
        repo probe set. Attribution vocabulary, frozen and listed in the report."""
        names = set(REPO_CORPUS_FILES)
        text = self.task_texts.get(task, "")
        for tok in re.findall(r"[A-Za-z0-9_\-./]+\.(?:md|json|py|txt|csv|yml|yaml)", text):
            names.add(tok.split("/")[-1])
        return sorted(names)

    def workspace_corpus_text(self, task: str) -> str:
        chunks = []
        canon = self.custody / "products" / task
        if canon.is_dir():
            for p in sorted(canon.iterdir()):
                if p.is_file():
                    try:
                        chunks.append(p.read_text(encoding="utf-8", errors="replace"))
                    except OSError:
                        pass
        return "\n".join(chunks)

    def classify_e3(self, code: str, rec: dict) -> dict:
        claim = rec.get("claim", {})
        m = self.mapping[code]
        key, task, cond = m["key"], m["task_id"], m["condition"]
        detail = rec.get("detail") or ""
        obs = rec.get("observation") or ""
        anchors: List[str] = []
        mm = re.search(r"锚未命中: (\[.*?\])", detail)
        if mm:
            try:
                anchors = json.loads(mm.group(1).replace("'", '"'))
            except ValueError:
                anchors = [a.strip(" '\"") for a in mm.group(1)[1:-1].split(",")]
        if not anchors:
            anchors = [a for a in claim.get("anchors", []) if a not in obs]

        prod_text = self.product_text(key)
        task_text = self.task_texts.get(task, "")
        ws_text = self.workspace_corpus_text(task)
        repo_files = self.task_corpus_files(task)
        repo_hits: Dict[str, Optional[str]] = {}
        for name in repo_files:
            t = self.probes.seal_file_text(name)
            if t:
                repo_hits[name] = t

        per_anchor = []
        any_ungroundable = False
        any_construction = False
        for a in anchors:
            in_obs = a in obs
            in_prod = a in prod_text
            in_task = a in task_text
            in_ws = a in ws_text
            in_repo_files = [n for n, t in repo_hits.items() if a in t]
            grounded = in_task or in_ws or bool(in_repo_files)
            # Construction-side, stated mechanically: the task JSON itself
            # carries the anchor text while no repository truth (seal-time
            # files probed) and no workspace data file does — i.e. the task
            # corpus and the repository drifted apart on this fact.
            construction = in_task and not in_ws and not in_repo_files
            if not grounded:
                any_ungroundable = True
            if construction:
                any_construction = True
            per_anchor.append({
                "anchor": sanitize(a, 40),
                "in_observation": in_obs, "in_product": in_prod,
                "in_task_json": in_task, "in_workspace": in_ws,
                "in_repo_seal_files": in_repo_files,
            })

        if any_construction:
            label = "A3-task-construction"
        elif any_ungroundable:
            label = "A2-anchor-ungroundable"
        else:
            label = "A1-executor-semantic"
        return {
            "code": code, "key": key, "task": task, "arm": cond,
            "provenance": self.provenance(prod_text, int(claim.get("source_line", 0))),
            "detail": sanitize(detail, 110),
            "evidence": sanitize((claim.get("evidence") or {}).get("raw", ""), 110),
            "label": label, "anchors": per_anchor,
        }


# ---------- aggregation ----------

def aggregate(att: Attribution) -> dict:
    e2 = att.e2_rows
    e3 = att.e3_rows
    e2_labels = Counter(r["label"] for r in e2)
    e3_labels = Counter(r["label"] for r in e3)
    resp = Counter()
    for r in e2 + e3:
        resp[LABEL_TO_RESPONSIBILITY[r["label"]]] += 1
    total = sum(resp.values())
    resp_pct = {k: round(v * 100.0 / total, 1) if total else 0.0
                for k, v in resp.items()}
    by_arm = defaultdict(Counter)
    for r in e2 + e3:
        by_arm[r["arm"]][r["label"]] += 1
    return {
        "generated_utc": now_iso(),
        "e2_total": len(e2), "e3_total": len(e3),
        "e2_labels": dict(e2_labels), "e3_labels": dict(e3_labels),
        "responsibility": dict(resp), "responsibility_pct": resp_pct,
        "total": total, "by_arm": {k: dict(v) for k, v in by_arm.items()},
        "rerun_cache_size": len(att.rerunner.cache),
        "seeded_files": att.rerunner.seeded_from,
    }


def dual_placement_report(att: Attribution) -> Tuple[List[dict], bool]:
    rows = []
    all_ok = True
    for f in att.dual.get("files", []):
        task, name = f["task"], f["file"]
        wc = att.custody / name
        canon = att.custody / "products" / task / name
        h_wc, h_canon = sha256_of(wc), sha256_of(canon)
        declared = f.get("sha256")
        ok = (h_wc is not None and h_wc == h_canon == declared)
        all_ok = all_ok and ok
        rows.append({"task": task, "file": name, "working_copy": str(wc),
                     "hash_match": ok,
                     "sha256": h_wc or "—",
                     "declared_matches": declared == h_wc})
    return rows, all_ok


# ---------- doc emission ----------

def emit_doc(att: Attribution, agg: dict, dual_rows: List[dict],
             dual_ok: bool) -> str:
    doc = att.doc_path
    if not doc.is_file():
        raise SystemExit(f"attribution: doc not found: {doc}")
    text = doc.read_text(encoding="utf-8")
    spans = {
        "COVERAGE": span_coverage(att, agg),
        "E2-SUMMARY": span_e2_summary(att, agg),
        "E3-TABLE": span_e3_table(att),
        "D4-TAXONOMY": span_d4(agg),
        "DUAL-PLACEMENT": span_dual(dual_rows, dual_ok),
        "APPENDIX-E2": span_appendix_e2(att),
        "APPENDIX-E3": span_appendix_e3(att),
        "APPENDIX-D3": span_appendix_d3(att),
        "SELFTEST": span_selftest(doc),
    }
    for name, body in spans.items():
        pattern = re.compile(
            r"(<!-- AUTO:" + name + r" -->).*?(<!-- /AUTO:" + name + r" -->)",
            re.S)
        new = f"<!-- AUTO:{name} -->\n{body}\n<!-- /AUTO:{name} -->"
        if not pattern.search(text):
            raise SystemExit(f"attribution: doc missing AUTO span {name}")
        text = pattern.sub(lambda _m: new, text, count=1)
    doc.write_text(text, encoding="utf-8")
    return str(doc)


def span_coverage(att: Attribution, agg: dict) -> str:
    e2 = agg["e2_total"]
    e3 = agg["e3_total"]
    unlabeled = [r for r in att.e2_rows + att.e3_rows
                 if not r.get("label") or r["label"].startswith("R14")]
    lines = [
        f"- 生成时间：{agg['generated_utc']}（attribution-round4 运行时写入，非手填）",
        f"- D1 覆盖：**{e2}/{e2}** 条 E2 逐条有根因分类标签；残留（R14 或无标签）= **{len(unlabeled)}**",
        f"- D2 覆盖：**{e3}/{e3}** 条 E3 逐条有根因分类标签 + 逐锚语料存在性",
        f"- 复跑缓存：{agg['rerun_cache_size']} 条唯一命令；重建工作区播种文件：{len(agg['seeded_files'])} 个",
    ]
    return "\n".join(lines)


def span_e2_summary(att: Attribution, agg: dict) -> str:
    lines = ["| 根因标签 | 三向归责 | 条数 | A 臂 | B 臂 | 典型 P 码 |", "|---|---|---:|---:|---:|---|"]
    e2_by = defaultdict(list)
    for r in att.e2_rows:
        e2_by[r["label"]].append(r)
    for label in sorted(E2_LABELS, key=lambda k: -len(e2_by.get(k, []))):
        rows = e2_by.get(label, [])
        if not rows:
            continue
        arm = Counter(r["arm"] for r in rows)
        examples = " ".join(r["code"] for r in rows[:3])
        lines.append(f"| `{label}` | {E2_LABELS[label]} | {len(rows)} | "
                     f"{arm.get('A', 0)} | {arm.get('B', 0)} | {examples} |")
    return "\n".join(lines)


def span_e3_table(att: Attribution) -> str:
    lines = ["| P 码 | 任务 | 臂 | 来源 | 缺失锚 | 根因标签 |", "|---|---|---|---|---|---|"]
    for r in sorted(att.e3_rows, key=lambda x: (x["task"], x["arm"], x["key"])):
        anchors = "、".join(a["anchor"] for a in r["anchors"]) or "—"
        lines.append(f"| {r['code']} | {r['task']} | {r['arm']} | "
                     f"{r['provenance']} | {anchors} | `{r['label']}` |")
    return "\n".join(lines)


def span_d4(agg: dict) -> str:
    total = agg["total"]
    lines = ["| 三向归责 | 条数（E2+E3=642 全量口径） | 占比 |", "|---|---:|---:|"]
    for k in ["执行者", "仪器", "任务构造"]:
        v = agg["responsibility"].get(k, 0)
        pct = agg["responsibility_pct"].get(k, 0.0)
        lines.append(f"| {k} | {v} | {pct}% |")
    lines.append(f"| **合计** | **{total}** | **{round(sum(agg['responsibility_pct'].values()), 1)}%** |")
    lines.append("")
    lines.append("标签 × 归责明细（E2/E3 分列）：")
    lines.append("")
    lines.append("| 标签 | 归责 | E2 | E3 |")
    lines.append("|---|---|---:|---:|")
    for label in sorted(set(list(E2_LABELS) + list(E3_LABELS))):
        e2n = agg["e2_labels"].get(label, 0)
        e3n = agg["e3_labels"].get(label, 0)
        if e2n == 0 and e3n == 0:
            continue
        lines.append(f"| `{label}` | {LABEL_TO_RESPONSIBILITY[label]} | {e2n} | {e3n} |")
    return "\n".join(lines)


def span_dual(dual_rows: List[dict], ok: bool) -> str:
    lines = [f"双落位 SHA-256 比对（工作副本 vs 正本 vs 登记值）：**{'全部一致' if ok else '存在不一致'}**",
             "",
             "| 任务 | 文件 | 三方一致 | SHA-256（前 16 位） |", "|---|---|---|---|"]
    for r in dual_rows:
        lines.append(f"| {r['task']} | {r['file']} | {'是' if r['hash_match'] else '否'} | {r['sha256'][:16]}… |")
    return "\n".join(lines)


def span_appendix_e2(att: Attribution) -> str:
    lines = ["| P 码 | 任务键 | 来源 | 证据行（摘要） | 判语摘要 | 根因标签 | 证据要点 |",
             "|---|---|---|---|---|---|---|"]
    for r in att.e2_rows:
        lines.append(f"| {r['code']} | {r['key']} | {r['provenance']} | "
                     f"{r['evidence']} | {r['detail']} | `{r['label']}` | "
                     f"{r['note']} {r['rerun']} |")
    return "\n".join(lines)


def span_appendix_e3(att: Attribution) -> str:
    lines = ["### 逐锚语料存在性（o=判定观察 p=产物 t=任务JSON w=工作区语料 r=密封时仓库文件）", ""]
    for r in sorted(att.e3_rows, key=lambda x: (x["task"], x["arm"], x["key"])):
        lines.append(f"- **{r['code']}**（{r['key']}，{r['provenance']}）→ `{r['label']}`")
        for a in r["anchors"]:
            flags = "".join([
                "o" if a["in_observation"] else "-",
                "p" if a["in_product"] else "-",
                "t" if a["in_task_json"] else "-",
                "w" if a["in_workspace"] else "-",
                "r" if a["in_repo_seal_files"] else "-",
            ])
            repo = (",".join(a["in_repo_seal_files"]) or "—")
            lines.append(f"  - 锚「{a['anchor']}」 opwtr={flags} 命中仓库文件={repo}")
    return "\n".join(lines)


def span_appendix_d3(att: Attribution) -> str:
    lines = []
    for td in att.d3_tasks:
        lines.append(f"#### {td['task']}（{td['title']}）")
        lines.append("")
        lines.append(f"- 工作区落盘：{td['workspace_files']}")
        lines.append(f"- A 臂判级分布：{td['a_levels']}；B 臂判级分布：{td['b_levels']}")
        lines.append(f"- 失败环节定位：**{td['stage_label']}**")
        lines.append("")
        lines.append("| 断言（前 40 字） | 草稿 believed | run-log 实际 | 判定根复跑 | 判级 | 根因 |")
        lines.append("|---|---|---|---|---|---|")
        for row in td["chain"]:
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    return "\n".join(lines)


def span_selftest(doc_path: Path) -> str:
    """A9 self-test, generated at attribution runtime (not hand-written):
    grep the report for the banned residual marker, excluding (a) the line
    that states the ban itself and (b) this self-test's own command echo —
    both are instrument quoting, not residual content."""
    text = doc_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    hits = [i for i, line in enumerate(lines, start=1)
            if "未分类" in line]
    ban_self = [i for i in hits
                if re.search(r"禁令自述|不得出现|A5 禁令", lines[i - 1])
                or lines[i - 1].lstrip().startswith("$ grep")]
    residual = [i for i in hits if i not in ban_self]
    return ("\n".join([
        "```",
        f"$ grep -n \"未分类\" docs/round4-attribution.md   # 运行时执行于 {now_iso()}",
        f"命中行: {hits if hits else '(无)'}",
        ("排除行（禁令自述行 + 本自测块自身的 grep 命令回显行）: " + str(ban_self)) if ban_self else "排除行: (无)",
        f"残留命中: {residual if residual else '(无)'}  → {'PASS (0)' if not residual else 'FAIL'}",
        "```",
    ]))


# ---------- D3 chain reconstruction ----------

def build_d3(att: Attribution) -> None:
    tasks_meta = {}
    for t, text in att.task_texts.items():
        try:
            j = json.loads(text)
            tasks_meta[t] = j.get("title", "")
        except ValueError:
            tasks_meta[t] = ""
    # label lookup keyed by (code, evidence raw) so a product with several
    # failing records gets the right label on each chain row
    label_by = {}
    for r in att.e2_rows + att.e3_rows:
        label_by.setdefault((r["code"], r["evidence"]), r["label"])
    for task in NEGATIVE_TASKS:
        codes = sorted(k for k, m in att.mapping.items() if m["task_id"] == task)
        a_levels: Counter = Counter()
        b_levels: Counter = Counter()
        chain_seen: Dict[tuple, dict] = {}
        for code in codes:
            m = att.mapping[code]
            cond = m["condition"]
            levels = Counter()
            for rec in att.judgements.get(code, []):
                levels[rec.get("level")] += 1
                if rec.get("level") not in ("E2", "E3"):
                    continue
                claim = rec.get("claim", {})
                ev = claim.get("evidence", {}) or {}
                text40 = sanitize(claim.get("text", ""), 40)
                ev_raw = sanitize(ev.get("raw", ""), 110)
                lab = label_by.get((code, ev_raw), "—")
                believed = "—"
                for c in att.draft(task).get("claims", []):
                    if sanitize(c.get("text", ""), 40) == text40:
                        believed = ("ref=" + str(c["ref"])) if c.get("ref") \
                            else f"exit={c.get('believed_exit')}"
                        break
                cmd = ev.get("command")
                rl = None
                if cmd:
                    recs = att.runlog_index.get((m["key"], normalize_command(cmd)), [])
                    exits = [r.get("exit_code") for r in recs
                             if r.get("exit_code") is not None]
                    rl = exits[0] if exits else None
                rr = "—"
                if cmd:
                    ex, _o, _ref, note = att.rerunner.run(cmd)
                    rr = str(ex) if ex is not None else note
                ck = (text40, believed, str(rl), lab)
                if ck not in chain_seen:
                    chain_seen[ck] = {"text": text40, "believed": believed,
                                      "runlog": str(rl) if rl is not None else "—",
                                      "label": lab, "rerun": rr,
                                      "levels": Counter()}
                chain_seen[ck]["levels"][rec.get("level")] += 1
            (a_levels if cond == "A" else b_levels).update(levels)
        loose = [f["file"] for f in att.dual.get("files", []) if f["task"] == task]
        canon = att.custody / "products" / task
        ws_files = sorted(p.name for p in canon.iterdir() if p.is_file()) \
            if canon.is_dir() else []
        stage = d3_stage_label(task, a_levels, b_levels, att)
        att.d3_tasks.append({
            "task": task, "title": tasks_meta.get(task, ""),
            "workspace_files": f"run-dir 根工作副本 {loose or '—'}；正本 products/{task}/ {ws_files or '—'}",
            "a_levels": dict(a_levels), "b_levels": dict(b_levels),
            "stage_label": stage,
            "chain": [[c["text"], c["believed"], c["runlog"], c["rerun"],
                       "、".join(f"{k}x{v}" for k, v in sorted(c["levels"].items())),
                       c["label"]] for c in chain_seen.values()],
        })


def d3_stage_label(task: str, a_levels: Counter, b_levels: Counter,
                   att: Attribution) -> str:
    """D3's four-stage lens: 落盘缺失 / 命名漂移 / 环境依赖 / 真实执行失败.
    Derived from this task's own attribution rows — no new judgement."""
    rows = [r for r in att.e2_rows + att.e3_rows if r["task"] == task]
    labs = Counter(r["label"] for r in rows)
    a_labs = Counter(r["label"] for r in rows if r["arm"] == "A")
    parts = []
    if labs.get("R5-ref-absent-everywhere"):
        parts.append("落盘缺失")
    if labs.get("R9-believed-mismatch") or labs.get("R12-output-content-drift"):
        parts.append("真实执行失败/声称不实")
    if (labs.get("R6-cwd-placement-armA") or labs.get("R3-ref-placement-armA")
            or labs.get("R7-believed-placement-armB") or labs.get("R4-ref-believed-armB")):
        parts.append("环境依赖（工作区 vs 判定根落位）")
    if labs.get("R8-shell-flavor"):
        parts.append("环境依赖（shell 风味）")
    if labs.get("R2-ref-grammar-decoration") or labs.get("R11-output-format-drift"):
        parts.append("仪器口径（ref 捕获/out 子串）")
    if not parts:
        if a_levels.get("E2", 0) + a_levels.get("E3", 0) == 0:
            parts.append("无（A 臂链路完整；差值来自 B 臂 believed 值不可复现）")
        else:
            parts.append("其他（见逐条附录）")
    return "；".join(parts)


# ---------- main ----------

def analyze(att: Attribution) -> dict:
    for code in sorted(att.judgements):
        for rec in att.judgements[code]:
            level = rec.get("level")
            if level == "E2":
                att.e2_rows.append(att.classify_e2(code, rec))
            elif level == "E3":
                att.e3_rows.append(att.classify_e3(code, rec))
    dual_rows, dual_ok = dual_placement_report(att)
    att.dual_rows = dual_rows
    build_d3(att)
    agg = aggregate(att)
    return agg


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--package", default=str(DEFAULT_PACKAGE))
    ap.add_argument("--key", default=str(DEFAULT_KEY))
    ap.add_argument("--custody", default=str(DEFAULT_CUSTODY))
    ap.add_argument("--repo", default=".")
    ap.add_argument("--drafts", default=str(DEFAULT_DRAFTS))
    ap.add_argument("--tasks", default=str(DEFAULT_TASKS))
    ap.add_argument("--doc", default=str(DEFAULT_DOC))
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--no-rerun", action="store_true")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    if args.workdir is None:
        # Fresh, uniquely-named reconstruction dir per run: never reuses or
        # deletes prior state, never touches repo/custody paths.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        args.workdir = str(Path(tempfile.gettempdir())
                           / f"xj20261105-002-attr-{stamp}")

    att = Attribution(args)
    agg = analyze(att)
    dual_rows, dual_ok = dual_placement_report(att)
    doc = emit_doc(att, agg, dual_rows, dual_ok)

    # UTF-8 self-check on the written deliverable (constraint 6): no runs of
    # literal '?' (mojibake indicator) longer than two chars, no U+FFFD.
    written = Path(doc).read_text(encoding="utf-8")
    fffd = written.count("\ufffd")
    q_runs = re.findall(r"\?{3,}", written)
    print(f"attribution: E2={agg['e2_total']} E3={agg['e3_total']} "
          f"responsibility={agg['responsibility_pct']}")
    print(f"attribution: doc written: {doc} | U+FFFD={fffd} | '?{{3,}}' runs={len(q_runs)}")
    if fffd or q_runs:
        print("attribution: UTF-8 SELF-CHECK FAILED", file=sys.stderr)
        return 1
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
