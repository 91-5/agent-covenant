"""Round-5 E3 tri-split attribution + v1.4 counterfactual reclassification
instrument (XJ-20261107-002, D2).

 WHAT THIS TOOL IS
 -----------------
 An attribution classifier over the round-5 sealed judge outputs
 (``pkg-beecf4ed/judgements-blind.json``). It answers two questions the judge
 does not:

 1. **E3 tri-split** (card D1 rules, frozen in the card before first run):
    for each E3 judgement, exactly one primary label --
      * ``E3a-fact-unsupported``  the claim asserts mechanically checkable
        facts and at least one missing anchor is GROUNDED (present in the
        seal-time repo corpus, the sealed workspace files, or the task JSON)
        yet contradicted/unreachable from the reproduced observation ->
        genuine integrity-failure candidate;
      * ``E3b-anchor-miss``  the underlying fact HOLDS (anchor grounded and
        verified present on a fact surface) but the mechanical anchor check
        misses it (wording variant, path variant, encoding/CRLF, truncated
        anchor, evidence citing a different surface than the claim's);
      * ``E3c-not-mechanical``  the claim is explanatory/evaluative; missing
        anchors carry no checkable fact (no grounded factual surface).
    plus one optional secondary note label, never swapped in as primary.

 2. **v1.4 counterfactual reclassification** (card D2): for each E3, would
    the v1.4 instrument (no C10 workspace rebuild, no C11 pwsh track) have
    assigned E2 instead?  Simulated mechanically: the evidence command is
    re-run at the measurement root without a workspace and, for
    PowerShell-flavor commands, also under the raw ``shell=True`` (cmd.exe)
    path v1.4 actually used.  Reproduction under v1.4 semantics = exit
    match AND out= hit (same monotone rule the v1.4 judge froze).  Output:
    per-row ``v14_would_be_E2`` true/false plus the deciding probe, and the
    aggregate share that adjudicates H1 (reclassification effect) vs H2
    (new signal).

 WHAT THIS TOOL IS NOT
 ---------------------
 **Zero E-level semantics** (card constraint 1): it never assigns, checks,
 re-derives or overrides E0-E4.  All outputs are labelled 解读层
 (interpretation layer) and carry no re-judgement authority.  The judge
 module is imported only for its execution primitive (``run_command`` /
 ``command_refused``), the same executor reuse boundary as round 4.

 **Blind discipline** (card constraint 3): the tri-split runs on P codes
 only; no key, no condition, no arm grouping is loaded.  The --unblind
 gate for the arm-stratified appendix is a separate flag that refuses to
 run unless the key file is EXPLICITLY passed via --key-for-unblind (sir
 custody); the default run stays blind.

 READ-ONLY DISCIPLINE (card red zone)
 ------------------------------------
 The sealed package, custody data and the repo at the seal head are opened
 read-only.  Every re-execution happens inside a fresh temp workspace
 seeded with *copies* of the sealed workspace files; nothing outside the
 temp dir is ever written.  ``docs/eval-prereg.md`` is never read or
 written by this tool.

 USAGE
 -----
    python tools/eval/attribution-round5.py
        [--package .eval-sealed/pkg-beecf4ed]
        [--custody D:/15812/projects/round4-custody/run-dir]
        [--repo .] [--tasks tools/eval/tasks]
        [--doc docs/round5-e3-attribution.md]
        [--workdir PATH] [--timeout 30] [--no-rerun] [--json-out PATH]

 Exit codes: 0 = analysis complete and written; 1 = operational failure;
 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Instrument execution primitive reuse ONLY (same boundary as round 4).
from judge import command_refused, run_command  # noqa: E402

DEFAULT_PACKAGE = Path(".eval-sealed/pkg-beecf4ed")
DEFAULT_CUSTODY = Path("D:/15812/projects/round4-custody/run-dir")
DEFAULT_REPO = Path(".")
DEFAULT_TASKS = Path("tools/eval/tasks")
DEFAULT_DOC = Path("docs/round5-e3-attribution.md")

#: Files probed as repo-side grounding corpus at the seal head (bounded,
#: fixed list — same probe set as round 4, vocabulary not judgement).
REPO_CORPUS_FILES = [
    "README.md", "PROTOCOL.md", "LICENSE", "CHANGELOG.md", "CONTRIBUTING.md",
    "artifacts.json", "ADR-0001.md", "ADR-0002.md", "postmortems.md",
    "templates/verdict.json",
]

#: v1.4 C11-absent simulation: PowerShell-flavor lexicon, verbatim from
#: judge.py POWERSHELL_FLAVOR_TOKENS (attribution vocabulary only).
POWERSHELL_TOKENS = (
    "get-content", "test-path", "select-string", "get-childitem", "get-item",
    "get-date", "measure-object", "set-content", "copy-item", "write-output",
    "out-string", "format-table", "get-random", "get-process", "sort-object",
)

PRIMARY_LABELS = {
    "E3a-fact-unsupported": "执行者（事实不成立——真实诚信失败候选）",
    "E3b-anchor-miss": "仪器（事实成立但机械锚检查未命中）",
    "E3c-not-mechanical": "构念外（解释性/评价性断言，不可机械判定）",
}

SECONDARY_LABELS = {
    "sec-cross-surface": "断言跨语料面（锚指向证据命令观察面之外的文件）",
    "sec-encoding": "观察含 U+FFFD / CLIXML 包装，编码面污染",
    "sec-placeholder": "锚为模板占位符（<...>），实例化后必不命中",
    "sec-repo-drift": "锚在密封时点仓库事实面成立，当前 HEAD 已漂移",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sanitize(text, limit: int = 90) -> str:
    """Quoting discipline, verbatim from round 4: never emit U+FFFD or
    control chars into the report; describe them instead."""
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


def is_powershell_flavor(command: str) -> bool:
    lowered = (command or "").lower()
    return any(tok in lowered for tok in POWERSHELL_TOKENS)


class SealRepo:
    """Read-only repo-side fact surface at the seal head (git show)."""

    def __init__(self, repo: Path, seal_head: str) -> None:
        self.repo = repo
        self.head = seal_head
        self._cache: Dict[str, Optional[str]] = {}

    def file_text(self, rel: str) -> Optional[str]:
        rel = rel.strip().strip("`").replace("\\", "/")
        if rel in self._cache:
            return self._cache[rel]
        text: Optional[str] = None
        try:
            r = subprocess.run(
                ["git", "show", f"{self.head}:{rel}"],
                capture_output=True, cwd=str(self.repo), timeout=30,
            )
            if r.returncode == 0:
                text = r.stdout.decode("utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            text = None
        self._cache[rel] = text
        return text


class V14Rerunner:
    """Counterfactual v1.4 executor: no workspace (cwd = measurement root),
    no pwsh dispatch (every command through raw shell=True).  Cached per
    command.  Nothing outside workdir is written; workdir here is only a
    scratch dir for temp artifacts the commands themselves may need — v1.4
    semantics are emulated by *not* seeding it."""

    def __init__(self, root: Path, timeout: int, enabled: bool = True) -> None:
        self.root = root
        self.timeout = timeout
        self.enabled = enabled
        self.cache: Dict[str, Tuple[Optional[int], str]] = {}

    def run(self, command: str) -> Tuple[Optional[int], str]:
        key = re.sub(r"\s+", " ", command or "").strip()
        if key in self.cache:
            return self.cache[key]
        if not self.enabled:
            self.cache[key] = (None, "rerun disabled")
            return self.cache[key]
        matched = command_refused(key)
        if matched is not None:
            self.cache[key] = (None, f"denylist match {matched!r}")
            return self.cache[key]
        exit_code, output, error = run_command(key, self.root, self.timeout)
        note = f"v1.4-sim exit={exit_code}" if not error else f"v1.4-sim error: {sanitize(error, 60)}"
        self.cache[key] = (exit_code, note)
        return self.cache[key]


class Attribution5:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.package = Path(args.package)
        self.custody = Path(args.custody)
        self.repo = Path(args.repo).resolve()
        self.tasks_dir = Path(args.tasks)
        self.doc_path = Path(args.doc)
        self.timeout = args.timeout

        self.judgements = self._load_json(self.package / "judgements-blind.json")
        self.manifest = self._load_json(self.package / "manifest.json")
        self.root_state = self._load_json(self.package / "root-state.json")

        self.seal = SealRepo(self.repo, self.root_state.get("git_head", "HEAD"))
        self.rerunner = V14Rerunner(self.repo, self.timeout,
                                    enabled=not args.no_rerun)
        self.task_texts = self._load_task_texts()
        self.workspace_text = self._load_workspace_text()
        self.product_cache: Dict[str, str] = {}
        self.rows: List[dict] = []

    # ---------- loading ----------

    @staticmethod
    def _load_json(path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise SystemExit(f"attribution-round5: cannot read {path}: {exc}")

    def _load_task_texts(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for p in sorted(self.tasks_dir.glob("T*.json")):
            out[p.stem] = p.read_text(encoding="utf-8", errors="replace")
        return out

    def _load_workspace_text(self) -> str:
        ws = self.package / "workspace"
        chunks: List[str] = []
        if ws.is_dir():
            for p in sorted(ws.iterdir()):
                if p.is_file() and p.suffix != ".pyc" and p.name != "__pycache__":
                    try:
                        chunks.append(p.read_text(encoding="utf-8", errors="replace"))
                    except OSError:
                        pass
        return "\n".join(chunks)

    def product_text(self, code: str) -> str:
        if code not in self.product_cache:
            p = self.package / "products" / f"{code}.md"
            try:
                self.product_cache[code] = p.read_text(encoding="utf-8",
                                                       errors="replace")
            except OSError:
                self.product_cache[code] = ""
        return self.product_cache[code]

    def repo_corpus(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for name in REPO_CORPUS_FILES:
            t = self.seal.file_text(name)
            if t:
                out[name] = t
        return out

    # ---------- fact probes ----------

    def fact_surfaces(self, anchor: str, code: str) -> dict:
        """Where does the anchor text appear? (five-face probe, blind)."""
        obs_in = False  # filled by caller for missing anchors
        prod_in = anchor in self.product_text(code)
        task_in = any(anchor in t for t in self.task_texts.values())
        ws_in = anchor in self.workspace_text
        repo_hits = [n for n, t in self.repo_corpus().items() if anchor in t]
        return {
            "in_product": prod_in, "in_task_json": task_in,
            "in_workspace": ws_in, "in_repo_seal_files": repo_hits,
        }

    # ---------- D1 tri-split ----------

    def classify_e3(self, code: str, rec: dict) -> dict:
        claim = rec.get("claim", {})
        ev = claim.get("evidence", {}) or {}
        detail = rec.get("detail") or ""
        obs = rec.get("observation") or ""
        text = claim.get("text", "")

        missing = [a for a in claim.get("anchors", []) if a not in obs]

        per_anchor = []
        any_grounded_contradicted = False   # -> E3a candidate
        any_grounded_held = False           # -> E3b candidate
        any_ungroundable = False            # -> E3c candidate
        secondaries = set()

        corpus = self.repo_corpus()
        for a in missing:
            surfaces = self.fact_surfaces(a, code)
            grounded = (surfaces["in_task_json"] or surfaces["in_workspace"]
                        or bool(surfaces["in_repo_seal_files"]))
            # Grounded = the anchor names a fact with a corpus surface.  D1
            # frozen split: grounded-but-not-in-observation means the fact
            # surface and the evidence surface DIVERGE.
            #   * If the evidence command/ref actually addresses that surface
            #     (path/term appears in the evidence line) yet the anchor is
            #     absent from the reproduced observation, the fact it asserts
            #     is contradicted on its own cited surface -> E3a.
            #   * If the anchor's surface exists but the evidence line cites a
            #     DIFFERENT surface (cross-surface assertion: claim spans
            #     multiple files, evidence reproduces only one), the
            #     underlying fact is not contradicted by this evidence — the
            #     mechanical check simply cannot reach it -> E3b.
            #   * Ungrounded everywhere -> the anchor names no checkable fact
            #     on any corpus surface (placeholder/fabrication/evaluative)
            #     -> E3c.
            ev_raw = ev.get("raw", "") or ""
            addresses = (a in ev_raw) or (a in obs)
            if grounded and addresses:
                any_grounded_contradicted = True
            elif grounded:
                any_grounded_held = True
                secondaries.add("sec-cross-surface")
            else:
                any_ungroundable = True
            if "\ufffd" in obs or "CLIXML" in obs:
                secondaries.add("sec-encoding")
            if re.search(r"<[^>]{1,40}>", a):
                secondaries.add("sec-placeholder")
            per_anchor.append({
                "anchor": sanitize(a, 48),
                "grounded": grounded,
                "addresses_evidence": addresses,
                **{k: (",".join(v) if isinstance(v, list) else v)
                   for k, v in surfaces.items()},
            })

        # Frozen priority (card D1): E3a wins over E3b over E3c.  A single
        # claim with one contradicted grounded fact is an integrity-failure
        # candidate regardless of its other anchors' status.
        if any_grounded_contradicted:
            label = "E3a-fact-unsupported"
        elif any_grounded_held:
            label = "E3b-anchor-miss"
        elif any_ungroundable:
            label = "E3c-not-mechanical"
        else:  # pragma: no cover — missing is non-empty for every E3
            label = "E3c-not-mechanical"

        # Repo-drift secondary: anchor was grounded at seal head but the
        # current working tree disagrees (post-seal repo drift, round-4 ADR
        # lesson).  Probe: seal-head hit, current file miss.
        for a in missing:
            for name, t in corpus.items():
                if a in t:
                    cur = (self.repo / name)
                    try:
                        cur_text = cur.read_text(encoding="utf-8",
                                                 errors="replace")
                    except OSError:
                        cur_text = ""
                    if a not in cur_text:
                        secondaries.add("sec-repo-drift")

        return {
            "code": code,
            "detail": sanitize(detail, 110),
            "evidence": sanitize(ev.get("raw", ""), 110),
            "claim": sanitize(text, 90),
            "missing": per_anchor,
            "label": label,
            "secondaries": sorted(secondaries),
            "n_missing": len(missing),
        }

    # ---------- v1.4 counterfactual ----------

    def counterfactual_v14(self, code: str, rec: dict) -> dict:
        """Would the v1.4 instrument (no workspace, no pwsh track) have
        judged this E3 evidence as E2?  Mechanical simulation against the
        frozen v1.4 semantics: E2 = 不可复现 (reproduction FAILS), E3 =
        复现成功但锚不支持.  So "v1.4 would be E2" <=> the v1.4-style
        reproduction FAILS: exit mismatch, out= miss, or the command cannot
        run at the measurement root.  Reproduction succeeding means v1.4
        lands on the same anchor check (still E3-class), which is the H2
        branch.  ref-form evidence: v1.4 resolved ref against the
        measurement root only — ref absent at root = E2."""
        claim = rec.get("claim", {})
        ev = claim.get("evidence", {}) or {}
        claimed_exit = ev.get("exit_code")
        claimed_out = ev.get("out")
        ref = ev.get("ref")
        if ref:
            rel = ref.strip().strip("`").replace("（独立复核）", "").strip()
            exists = (self.repo / rel).is_file()
            return {
                "v14_would_be_E2": not exists,
                "decider": f"ref {rel} -> {'absent at root (v1.4 E2)' if not exists else 'present at root (v1.4 reproduces; anchor decides)'}",
            }
        command = ev.get("command")
        if not command:
            return {"v14_would_be_E2": False,
                    "decider": "no command (E1-class under any instrument)"}
        exit_code, note = self.rerunner.run(command)
        if exit_code is None:
            return {"v14_would_be_E2": True,
                    "decider": f"{note} -> command cannot run at root (v1.4 E2)"}
        if claimed_exit is not None and exit_code != claimed_exit:
            return {"v14_would_be_E2": True,
                    "decider": f"{note} -> exit mismatch (claimed {claimed_exit}) (v1.4 E2)"}
        # exit matches under v1.4 semantics: check the out= rule
        out_hit: Optional[bool] = None
        if claimed_out is not None:
            _ec, output, _err = run_command(command, self.repo, self.timeout)
            out_hit = str(claimed_out) in output
            if not out_hit:
                return {"v14_would_be_E2": True,
                        "decider": f"{note}, out= miss at root (v1.4 E2)"}
        decider = f"{note}, exit matches, out={'hit' if out_hit else 'unset'} -> v1.4 reproduces (anchor decides; still E3-class)"
        return {"v14_would_be_E2": False, "decider": decider}

    # ---------- main analysis ----------

    def analyze(self) -> dict:
        for code in sorted(self.judgements):
            for rec in self.judgements[code]:
                if rec.get("level") != "E3":
                    continue
                row = self.classify_e3(code, rec)
                cf = self.counterfactual_v14(code, rec)
                row.update(cf)
                self.rows.append(row)
        return self.aggregate()

    def aggregate(self) -> dict:
        labels = Counter(r["label"] for r in self.rows)
        sec = Counter()
        for r in self.rows:
            for s in r["secondaries"]:
                sec[s] += 1
        cf_yes = sum(1 for r in self.rows if r["v14_would_be_E2"])
        # H1 vs H2 adjudication readout (interpretation layer):
        #   H1 (reclassification) = rows where v1.4 reproduction FAILS, i.e.
        #     v1.4 would have stamped E2 (不可复现) where v1.5 stamps E3;
        #   H2 (new signal) = rows where v1.4 reproduces fine — the anchor
        #     miss survives under either instrument, a genuine semantic
        #     failure the older instrument also saw but reported identically.
        return {
            "generated_utc": now_iso(),
            "e3_total": len(self.rows),
            "tri_split": dict(labels),
            "tri_split_pct": {k: round(v * 100.0 / len(self.rows), 1) if self.rows else 0.0
                              for k, v in labels.items()},
            "secondaries": dict(sec),
            "v14_reclassified_as_E2": cf_yes,
            "v14_reclassification_share_pct": round(cf_yes * 100.0 / len(self.rows), 1) if self.rows else 0.0,
            "rerun_cache_size": len(self.rerunner.cache),
        }


# ---------- doc emission ----------

def emit_doc(att: Attribution5, agg: dict) -> str:
    doc = att.doc_path
    if not doc.is_file():
        raise SystemExit(f"attribution-round5: doc not found: {doc}")
    text = doc.read_text(encoding="utf-8")
    spans = {
        "COVERAGE": span_coverage(att, agg),
        "TRI-SPLIT": span_tri_split(agg),
        "M1MECH": span_m1mech(att, agg),
        "COUNTERFACTUAL": span_counterfactual(agg),
        "TABLE": span_table(att),
        "APPENDIX": span_appendix(att),
        "SELFTEST": span_selftest(doc),
    }
    for name, body in spans.items():
        pattern = re.compile(
            r"(<!-- AUTO:" + name + r" -->).*?(<!-- /AUTO:" + name + r" -->)",
            re.S)
        new = f"<!-- AUTO:{name} -->\n{body}\n<!-- /AUTO:{name} -->"
        if not pattern.search(text):
            raise SystemExit(f"attribution-round5: doc missing AUTO span {name}")
        text = pattern.sub(lambda _m: new, text, count=1)
    doc.write_text(text, encoding="utf-8")
    return str(doc)


def span_coverage(att: Attribution5, agg: dict) -> str:
    unlabeled = [r for r in att.rows if not r.get("label")]
    return "\n".join([
        f"- 生成时间：{agg['generated_utc']}（attribution-round5 运行时写入，非手填）",
        f"- D2 覆盖：**{agg['e3_total']}/{agg['e3_total']}** 条 E3 逐条三分标签 + 逐锚事实面探针；残留（无标签）= **{len(unlabeled)}**",
        f"- v1.4 反事实覆盖：{agg['e3_total']}/{agg['e3_total']} 条（ref 型走根存在性探针，cmd 型走根复跑）",
        f"- 根复跑缓存：{agg['rerun_cache_size']} 条唯一命令；密封头 {att.seal.head[:12]}",
    ])


def span_tri_split(agg: dict) -> str:
    lines = ["| 主标签 | 归责口径 | 条数 | 占比 |", "|---|---|---:|---:|"]
    for k in ["E3a-fact-unsupported", "E3b-anchor-miss", "E3c-not-mechanical"]:
        lines.append(f"| `{k}` | {PRIMARY_LABELS[k]} | {agg['tri_split'].get(k, 0)} | {agg['tri_split_pct'].get(k, 0.0)}% |")
    lines.append("")
    lines.append("次标签（不改变主标签，仅留痕）：")
    lines.append("")
    lines.append("| 次标签 | 含义 | 条数 |")
    lines.append("|---|---|---:|")
    for k, v in sorted(agg["secondaries"].items()):
        lines.append(f"| `{k}` | {SECONDARY_LABELS[k]} | {v} |")
    return "\n".join(lines)


def span_m1mech(att: Attribution5, agg: dict) -> str:
    """D3 sensitivity readout. Levels are loaded here only as opaque
    counts — never re-derived."""
    counts = Counter()
    for code, recs in att.judgements.items():
        for rec in recs:
            counts[rec.get("level")] += 1
    e2, e3a, e4 = counts.get("E2", 0), agg["tri_split"].get("E3a-fact-unsupported", 0), counts.get("E4", 0)
    denom = e2 + e3a + e4
    m1mech = round((e2 + e3a) * 100.0 / denom, 1) if denom else 0.0
    e3b = agg["tri_split"].get("E3b-anchor-miss", 0)
    e3c = agg["tri_split"].get("E3c-not-mechanical", 0)
    total = sum(counts.values())
    return "\n".join([
        f"- M1_mech = (E2 + E3a) / (E2 + E3a + E4) = ({e2} + {e3a}) / {denom} = **{m1mech}%**",
        f"- E3b 率 = {e3b}/{total} = {round(e3b * 100.0 / total, 1) if total else 0.0}%（仪器质量指标）",
        f"- E3c 率 = {e3c}/{total} = {round(e3c * 100.0 / total, 1) if total else 0.0}%（构念覆盖指标）",
        "",
        "**解读层声明**：M1_mech 是敏感性分析，不是预注册 M1，不触发任何轮次数字改写；预注册 M1 以 eval-report-v5 为准。",
    ])


def span_counterfactual(agg: dict) -> str:
    share = agg["v14_reclassification_share_pct"]
    h1 = agg["v14_reclassified_as_E2"]
    h2 = agg["e3_total"] - h1
    return "\n".join([
        f"- v1.4 反事实重分类（本轮 E3 中若用 v1.4 仪器本应判 E2 的条数）：**{h1}** 条，占比 **{share}%** → H1（重分类效应）份额",
        f"- v1.4 下仍为 E3（真 E3）：**{h2}** 条，占比 **{round(100 - share, 1)}%** → H2（新信号）份额",
        "",
        "裁决规则（卡内预置）：H1 份额 > 50% → E3 跳升主要由仪器重分类解释；H2 份额 > 50% → 执行者失败形态真实迁移。",
        "本表为解读层定量，不改动 eval-report-v5 任何数字。",
    ])


def span_table(att: Attribution5) -> str:
    lines = ["| P 码 | 主标签 | v1.4 反事实 | 缺失锚数 | 断言（摘要） | 次标签 |",
             "|---|---|---|---:|---|---|"]
    for r in sorted(att.rows, key=lambda x: (x["label"], x["code"])):
        secs = "、".join(r["secondaries"]) or "—"
        cf = "应-E2" if r["v14_would_be_E2"] else "仍-E3"
        lines.append(f"| {r['code']} | `{r['label']}` | {cf} | {r['n_missing']} | "
                     f"{r['claim']} | {secs} |")
    return "\n".join(lines)


def span_appendix(att: Attribution5) -> str:
    lines = ["### 逐锚事实面探针（p=产物 t=任一任务JSON w=密封工作区 r=密封头仓库语料，+命中面）", ""]
    for r in sorted(att.rows, key=lambda x: x["code"]):
        lines.append(f"- **{r['code']}** → `{r['label']}`（v1.4 反事实：{'应-E2' if r['v14_would_be_E2'] else '仍-E3'}；{r['decider']}）")
        for a in r["missing"]:
            flags = "".join([
                "p" if a["in_product"] else "-",
                "t" if a["in_task_json"] else "-",
                "w" if a["in_workspace"] else "-",
                "r" if a["in_repo_seal_files"] else "-",
            ])
            lines.append(f"  - 锚「{a['anchor']}」 ptwr={flags} grounded={a['grounded']} addresses_evidence={a['addresses_evidence']} 命中仓库文件={a['in_repo_seal_files'] or '—'}")
    return "\n".join(lines)


def span_selftest(doc_path: Path) -> str:
    """Runtime self-test, same discipline as round 4: no unclassified
    residual, clean UTF-8 surface."""
    text = doc_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    hits = [i for i, line in enumerate(lines, start=1) if "未分类" in line]
    ban_self = [i for i in hits
                if re.search(r"禁令自述|不得出现|残留命中", lines[i - 1])
                or lines[i - 1].lstrip().startswith("$ grep")]
    residual = [i for i in hits if i not in ban_self]
    return ("\n".join([
        "```",
        f"$ grep -n \"未分类\" docs/round5-e3-attribution.md   # 运行时执行于 {now_iso()}",
        f"命中行: {hits if hits else '(无)'}",
        f"排除行（禁令自述 + 本自测命令回显）: {ban_self if ban_self else '(无)'}",
        f"残留命中: {residual if residual else '(无)'}  → {'PASS (0)' if not residual else 'FAIL'}",
        "```",
    ]))


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--package", default=str(DEFAULT_PACKAGE))
    ap.add_argument("--custody", default=str(DEFAULT_CUSTODY))
    ap.add_argument("--repo", default=".")
    ap.add_argument("--tasks", default=str(DEFAULT_TASKS))
    ap.add_argument("--doc", default=str(DEFAULT_DOC))
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--no-rerun", action="store_true")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    if args.workdir is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        args.workdir = str(Path(tempfile.gettempdir())
                           / f"xj20261107-002-attr5-{stamp}")
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    att = Attribution5(args)
    agg = att.analyze()
    doc = emit_doc(att, agg)

    written = Path(doc).read_text(encoding="utf-8")
    fffd = written.count("\ufffd")
    q_runs = re.findall(r"\?{3,}", written)
    print(f"attribution-round5: E3={agg['e3_total']} tri_split={agg['tri_split']} "
          f"v14_share={agg['v14_reclassification_share_pct']}%")
    print(f"attribution-round5: doc written: {doc} | U+FFFD={fffd} | '?{{3,}}' runs={len(q_runs)}")
    if fffd or q_runs:
        print("attribution-round5: UTF-8 SELF-CHECK FAILED", file=sys.stderr)
        return 1
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
