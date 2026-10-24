"""Control bank loader, harness self-test, and M3 observer probes.

The control bank is the harness's own lie detector (dp：负对照是底线).
Three kinds of control block live in ``tools/eval/tasks/controls/``:

* negative (负对照) -- fabricated evidence (fake command / fake exit code /
  missing ref / unrelated real evidence). The judge MUST refuse E4. If any
  negative control passes as E4, the metric suite is broken and the card
  fails: 抓不到 = 检测器坏了.
* positive (正对照) -- genuinely true, fully supported claims. The judge MUST
  return E4. Guards against "block everything" score inflation.
* blank (空白对照) -- plain assertions with no evidence line (must be E0) or
  format-compliant evidence about something unrelated (must be E3, i.e. NOT
  accepted as support). Guards against "evidence decoration".

File format: an HTML comment carrying metadata (id / kind / expected / note),
then the implant block -- exactly the markdown that gets judged directly in
the self-test and *implanted into task products* at study time. Metadata
never travels with an implant: products receive the block verbatim, nothing
else, so a product cannot recognise a control by its wrapper.

Hidden variants: two reworded negative controls live in
``tools/eval/tasks/controls-sealed/`` (gitignored, sir's custody). The
self-test loads that directory when present and folds the results into the
negative totals -- uniformly, with no marker distinguishing them (constraint
4: 运行报告不标注). A fresh clone without the sealed directory still meets
the acceptance bar of >=6/6 visible negatives.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import judge
from schema import LEVEL_NAMES

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VISIBLE_BANK_DIR = Path(__file__).resolve().parent / "tasks" / "controls"
SEALED_BANK_DIR = Path(__file__).resolve().parent / "tasks" / "controls-sealed"

KINDS = ("negative", "positive", "blank")

META_RE = re.compile(r"<!--\s*eval-control(.*?)-->", re.DOTALL)
_META_FIELD_RE = re.compile(r"^(\w+)\s*:\s*(.+?)\s*$", re.MULTILINE)


@dataclass
class ControlDef:
    """One control: metadata + the verbatim implant block."""

    cid: str
    kind: str  # negative | positive | blank
    expected: str  # exact frozen level the judge must return
    note: str
    block: str  # the markdown block (claim + evidence), metadata stripped
    source: str  # which file it came from (visible bank vs sealed)
    sealed: bool = False

    def to_dict(self, include_block: bool = False) -> Dict[str, object]:
        out: Dict[str, object] = {
            "id": self.cid,
            "kind": self.kind,
            "expected": self.expected,
            "source": self.source,
        }
        if include_block:
            out["block"] = self.block
        return out


@dataclass
class ControlResult:
    control: ControlDef
    judged_level: str
    ok: bool
    detail: str = ""


@dataclass
class SelftestResult:
    results: List[ControlResult] = field(default_factory=list)
    sealed_loaded: int = 0

    @property
    def ok(self) -> bool:
        return all(result.ok for result in self.results)

    def counts(self) -> Dict[str, Dict[str, int]]:
        """Aggregate per kind: total / passed. Hidden variants are folded in
        invisibly -- the aggregate never says which files were sealed."""
        out: Dict[str, Dict[str, int]] = {}
        for result in self.results:
            bucket = out.setdefault(result.control.kind, {"total": 0, "passed": 0})
            bucket["total"] += 1
            if result.ok:
                bucket["passed"] += 1
        return out


def _parse_control_file(path: Path, sealed: bool) -> Optional[ControlDef]:
    text = path.read_text(encoding="utf-8")
    meta_match = META_RE.search(text)
    if not meta_match:
        return None
    fields = dict(_META_FIELD_RE.findall(meta_match.group(1)))
    cid = fields.get("id", path.stem)
    kind = fields.get("kind", "")
    expected = fields.get("expected", "")
    if kind not in KINDS or expected not in LEVEL_NAMES:
        return None
    block = text[meta_match.end():].strip("\n")
    if not block.strip():
        return None
    return ControlDef(
        cid=cid, kind=kind, expected=expected,
        note=fields.get("note", ""), block=block,
        source=str(path), sealed=sealed,
    )


def load_bank(visible_dir: Path = VISIBLE_BANK_DIR, sealed_dir: Path = SEALED_BANK_DIR) -> Tuple[List[ControlDef], int]:
    """Load the full control bank: visible definitions plus the sealed
    directory when it exists on this machine. Returns (controls, sealed_count)."""
    controls: List[ControlDef] = []
    sealed_count = 0
    for path in sorted(visible_dir.glob("*.md")):
        control = _parse_control_file(path, sealed=False)
        if control is not None:
            controls.append(control)
    if sealed_dir.is_dir():
        for path in sorted(sealed_dir.glob("*.md")):
            control = _parse_control_file(path, sealed=True)
            if control is not None:
                controls.append(control)
                sealed_count += 1
    return controls, sealed_count


def check_control(control: ControlDef, root: Path, timeout: int = judge.DEFAULT_TIMEOUT_SECONDS) -> ControlResult:
    """Judge one control block and compare against its frozen expectation."""
    judgements = judge.judge_markdown(control.block, root, product=f"control:{control.cid}", timeout=timeout)
    if len(judgements) != 1:
        return ControlResult(
            control=control, judged_level="<none>", ok=False,
            detail=f"对照块必须恰好含 1 条断言，实际抽出 {len(judgements)} 条",
        )
    judgement = judgements[0]
    ok = judgement.level == control.expected
    detail = judgement.detail
    if control.kind == "negative" and ok:
        detail = "负对照已抓到（未按 E4 通过）: " + detail
    return ControlResult(control=control, judged_level=judgement.level, ok=ok, detail=detail)


def run_selftest(root: Path = REPO_ROOT, timeout: int = judge.DEFAULT_TIMEOUT_SECONDS) -> SelftestResult:
    """Run every control through the judge. This is the lie detector:
    one negative slipping through as E4 fails the whole harness."""
    controls, sealed_count = load_bank()
    result = SelftestResult(sealed_loaded=sealed_count)
    for control in controls:
        result.results.append(check_control(control, root, timeout=timeout))
    return result


def format_selftest(result: SelftestResult) -> str:
    """Render the self-test report. Per-ID lines are uniform: sealed variants
    appear under their ordinary ids with no hidden marker (constraint 4)."""
    lines = ["== eval harness selftest（对照组测谎仪）=="]
    counts = result.counts()
    order = [kind for kind in KINDS if kind in counts]
    for kind in order:
        bucket = counts[kind]
        lines.append(f"{kind}: {bucket['passed']}/{bucket['total']} 符合冻结预期")
    lines.append(f"sealed 目录已装载 {result.sealed_loaded} 个变体（报告中不做任何标注）")
    for item in result.results:
        mark = "ok  " if item.ok else "FAIL"
        lines.append(
            f"  [{mark}] {item.control.cid} ({item.control.kind}) "
            f"expected={item.control.expected} judged={item.judged_level}"
        )
        if not item.ok:
            lines.append(f"         detail: {item.detail}")
    lines.append("SELFTEST: " + ("PASS" if result.ok else "FAIL"))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# M3 probes -- the harness observing the gate, never modifying it.
# ---------------------------------------------------------------------------


def probe_lint_rejection(card_id: str, card_text: str, workdir: Optional[Path] = None) -> Tuple[bool, str]:
    """Run the REAL lint_cards.py against a candidate card in a throwaway
    directory. Returns (rejected, combined_output). The harness is an
    observer: it invokes the gate tools as subprocesses and touches nothing
    they own."""
    tmp: Optional[tempfile.TemporaryDirectory] = None
    if workdir is None:
        tmp = tempfile.TemporaryDirectory()
        workdir = Path(tmp.name)
    card_dir = workdir / ".tasks"
    verdict_dir = workdir / "verdicts"
    card_dir.mkdir(parents=True, exist_ok=True)
    verdict_dir.mkdir(parents=True, exist_ok=True)
    (card_dir / f"{card_id}.md").write_text(card_text, encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "lint_cards.py"),
             "--dir", str(card_dir), "--verdict-dir", str(verdict_dir),
             "--no-verdict-schema"],
            capture_output=True, timeout=120, cwd=str(workdir),
        )
        output = (completed.stdout or b"").decode("utf-8", errors="replace")
        errout = (completed.stderr or b"").decode("utf-8", errors="replace")
        combined = output + ("\n" + errout if errout else "")
        rejected = completed.returncode != 0 or "[ERROR]" in output
        return rejected, combined
    finally:
        if tmp is not None:
            tmp.cleanup()


def probe_gate_rejection(verdict_payload: dict, workdir: Optional[Path] = None) -> Tuple[bool, str]:
    """Run the REAL gate.py against a candidate verdict in a throwaway
    directory. Returns (rejected, combined_output); rejected = gate exit != 0."""
    tmp: Optional[tempfile.TemporaryDirectory] = None
    if workdir is None:
        tmp = tempfile.TemporaryDirectory()
        workdir = Path(tmp.name)
    verdict_dir = workdir / "verdicts"
    verdict_dir.mkdir(parents=True, exist_ok=True)
    vid = verdict_payload.get("id", "EVALPROBE-000000-001")
    (verdict_dir / f"{vid}.verdict.json").write_text(
        json.dumps(verdict_payload, ensure_ascii=False), encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "gate.py"),
             "--verdict-dir", str(verdict_dir), "--require", str(vid)],
            capture_output=True, timeout=120, cwd=str(workdir),
        )
        output = (completed.stdout or b"").decode("utf-8", errors="replace")
        errout = (completed.stderr or b"").decode("utf-8", errors="replace")
        combined = output + ("\n" + errout if errout else "")
        return completed.returncode != 0, combined
    finally:
        if tmp is not None:
            tmp.cleanup()
