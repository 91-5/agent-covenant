"""Task-list schema and claim/evidence dataclasses for the eval harness.

Two record types meet here:

* **TaskDef** -- one entry of the 30-task list (``tools/eval/tasks/*.json``).
  Frozen shape: id / layer / title / prompt / product / acceptance. The
  acceptance field is what makes task completion *checkable* without an LLM:
  either a fixed answer string the product must contain verbatim on an
  ``答案：`` line, or a command whose exit code decides coverage.

* **Claim / EvidenceLine / ClaimJudgement** -- the analysis unit is the claim
  (断言), never the task card (dp principle #1). Extractors produce Claims,
  the judge attaches a ClaimJudgement to each.

Validation is deliberately boring: every failure is a string a human can act
on, and nothing raises on schema drift -- a broken task list must be
*reported*, not crashed over (the harness measures processes; it should not
reproduce their failure modes).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

LAYERS = ("fact", "code", "process")

LAYER_COUNTS = {"fact": 10, "code": 10, "process": 10}  # frozen: 10/10/10

TOTAL_TASKS = 30

TASK_ID_RE = re.compile(r"^T\d{2}$")

ANSWER_LINE_RE = re.compile(r"^\s*答案[:：]\s*(.+?)\s*$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Task definitions
# ---------------------------------------------------------------------------


@dataclass
class Acceptance:
    """How task completion is decided, without judgement calls.

    type="answer": the product must contain ``答案：<value>`` matching
    ``value`` exactly after whitespace normalisation. type="command": the
    command runs in the run workspace; exit 0 (or ``expect_exit``) = covered.
    """

    type: str  # "answer" | "command"
    value: Optional[str] = None      # answer text (type="answer")
    command: Optional[str] = None    # shell command (type="command")
    expect_exit: int = 0             # expected exit (type="command")

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"type": self.type}
        if self.type == "answer":
            out["value"] = self.value
        else:
            out["command"] = self.command
            out["expect_exit"] = self.expect_exit
        return out


@dataclass
class TaskDef:
    """One task of the 30-task list. See docs/eval-prereg.md §3 for the
    frozen sampling rules (10 fact / 10 code / 10 process, 3 reps each)."""

    id: str
    layer: str
    title: str
    prompt: str
    product: str
    acceptance: Acceptance
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "layer": self.layer,
            "title": self.title,
            "prompt": self.prompt,
            "product": self.product,
            "acceptance": self.acceptance.to_dict(),
            "notes": self.notes,
        }


def validate_task(raw: Dict[str, Any], source: str = "") -> Tuple[Optional[TaskDef], List[str]]:
    """Validate one raw task dict. Returns (task, errors); task is None when
    the errors are fatal (bad id/layer/acceptance). Non-fatal findings stay in
    errors and the task is still returned, so a report can show everything."""
    errors: List[str] = []
    where = source or raw.get("id", "<unnamed>")

    tid = raw.get("id")
    if not isinstance(tid, str) or not TASK_ID_RE.match(tid):
        errors.append(f"{where}: id must match T\\d{{2}}, got {tid!r}")

    layer = raw.get("layer")
    if layer not in LAYERS:
        errors.append(f"{where}: layer must be one of {LAYERS}, got {layer!r}")

    title = raw.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append(f"{where}: title must be a non-empty string")

    prompt = raw.get("prompt")
    if not isinstance(prompt, str) or len(prompt.strip()) < 10:
        errors.append(f"{where}: prompt must be a non-trivial string (>=10 chars)")

    product = raw.get("product")
    if not isinstance(product, str) or not product.strip():
        errors.append(f"{where}: product must name the produced file")

    acc_raw = raw.get("acceptance")
    acceptance: Optional[Acceptance] = None
    if not isinstance(acc_raw, dict):
        errors.append(f"{where}: acceptance must be an object")
    else:
        atype = acc_raw.get("type")
        if atype == "answer":
            value = acc_raw.get("value")
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{where}: acceptance.type=answer needs a non-empty value")
            else:
                acceptance = Acceptance(type="answer", value=value)
        elif atype == "command":
            command = acc_raw.get("command")
            if not isinstance(command, str) or not command.strip():
                errors.append(f"{where}: acceptance.type=command needs a non-empty command")
            else:
                expect = acc_raw.get("expect_exit", 0)
                if not isinstance(expect, int) or isinstance(expect, bool):
                    errors.append(f"{where}: acceptance.expect_exit must be an int")
                    expect = 0
                acceptance = Acceptance(type="command", command=command, expect_exit=expect)
        else:
            errors.append(f"{where}: acceptance.type must be 'answer' or 'command', got {atype!r}")

    notes = raw.get("notes", "")
    if not isinstance(notes, str):
        errors.append(f"{where}: notes must be a string when present")
        notes = ""

    if errors and (acceptance is None or not isinstance(tid, str)):
        return None, errors

    task = TaskDef(
        id=tid,  # type: ignore[arg-type]
        layer=layer,  # type: ignore[arg-type]
        title=title,  # type: ignore[arg-type]
        prompt=prompt,  # type: ignore[arg-type]
        product=product,  # type: ignore[arg-type]
        acceptance=acceptance,  # type: ignore[arg-type]
        notes=notes,
    )
    return task, errors


def load_task_file(path: Any) -> Tuple[Optional[TaskDef], List[str]]:
    """Load and validate one task JSON file."""
    text = path.read_text(encoding="utf-8")
    try:
        raw = json.loads(text)
    except ValueError as exc:
        return None, [f"{path}: invalid JSON: {exc}"]
    if not isinstance(raw, dict):
        return None, [f"{path}: top level must be a JSON object"]
    return validate_task(raw, source=str(path))


def load_task_dir(task_dir: Any) -> Tuple[List[TaskDef], List[str]]:
    """Load every T*.json in a task directory. Returns (tasks, errors) with
    errors carrying every schema finding, so --dry-run can print the full list
    instead of stopping at the first bad file."""
    tasks: List[TaskDef] = []
    errors: List[str] = []
    files = sorted(path for path in task_dir.glob("T*.json"))
    if not files:
        errors.append(f"{task_dir}: no T*.json task files found")
    for path in files:
        task, task_errors = load_task_file(path)
        errors.extend(task_errors)
        if task is not None:
            tasks.append(task)
    ids = [task.id for task in tasks]
    if len(set(ids)) != len(ids):
        errors.append(f"{task_dir}: duplicate task ids present")
    for layer, want in LAYER_COUNTS.items():
        got = sum(1 for task in tasks if task.layer == layer)
        if got != want:
            errors.append(
                f"{task_dir}: layer {layer} has {got} tasks, frozen design requires {want}"
            )
    return tasks, errors


# ---------------------------------------------------------------------------
# Claims and judgements
# ---------------------------------------------------------------------------


@dataclass
class EvidenceLine:
    """One parsed ``证据：`` line. A line is *complete* when it carries either
    the command form (cmd + exit or out) or the independent-review ref form.
    Anything else is structurally E1 (frozen in docs/eval-prereg.md §1)."""

    raw: str
    source_line: int
    command: Optional[str] = None
    exit_code: Optional[int] = None
    out: Optional[str] = None
    ref: Optional[str] = None

    @property
    def has_command_form(self) -> bool:
        return self.command is not None and (self.exit_code is not None or self.out is not None)

    @property
    def has_ref_form(self) -> bool:
        return self.ref is not None

    @property
    def is_complete(self) -> bool:
        return self.has_command_form or self.has_ref_form

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw,
            "source_line": self.source_line,
            "command": self.command,
            "exit_code": self.exit_code,
            "out": self.out,
            "ref": self.ref,
            "complete": self.is_complete,
        }


@dataclass
class Claim:
    """One ``[已验证]`` assertion extracted from a product markdown."""

    text: str
    source_line: int
    product: str
    evidence: Optional[EvidenceLine] = None
    anchors: List[str] = field(default_factory=list)
    unanchored: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source_line": self.source_line,
            "product": self.product,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "anchors": list(self.anchors),
            "unanchored": self.unanchored,
        }


@dataclass
class ClaimJudgement:
    """The five-level verdict for one claim, plus the audit trail.

    ``detail`` is a human-readable sentence recording *what the judge actually
    did* (ran which command, saw which output) -- failure samples are assets
    (纪律提醒 3), and a level without its evidence trail is just a number.
    """

    claim: Claim
    level: str  # E0 | E1 | E2 | E3 | E4
    flags: List[str] = field(default_factory=list)
    detail: str = ""
    observation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "flags": list(self.flags),
            "detail": self.detail,
            "observation": self.observation,
            "claim": self.claim.to_dict(),
        }


LEVEL_NAMES = {
    "E0": "无证据行",
    "E1": "缺字段",
    "E2": "不可复现",
    "E3": "不支持",
    "E4": "支持",
}
