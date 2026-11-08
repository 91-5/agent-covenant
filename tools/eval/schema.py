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


# ---------------------------------------------------------------------------
# v1.5 C10/C11 packaging metadata (card XJ-20261106-002)
# ---------------------------------------------------------------------------

#: Keys build_package adds to a package manifest when it seals judgements
#: against a rebuilt execution workspace. Older manifests (pre-v1.5) lack
#: both keys; readers must tolerate their absence, never raise over it.
PACKAGING_METADATA_KEYS = ("workspace_rebuild", "shell_track")


def packaging_metadata(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Backward-compatible read of the C10/C11 metadata block.

    Returns only the keys actually present, so a pre-v1.5 manifest yields
    ``{}`` and every caller can feature-test instead of version-guessing."""
    return {key: manifest[key] for key in PACKAGING_METADATA_KEYS if key in manifest}


def validate_packaging_metadata(meta: Dict[str, Any]) -> List[str]:
    """Structural checks on the metadata block (drift findings, never raises).

    An absent block is valid (pre-v1.5 package). A present block must carry
    the fields downstream surfaces read: workspace_rebuild.registry_missing /
    .files / .manifest_sha256 and shell_track.available / .lexicon_sha256."""
    findings: List[str] = []
    if not meta:
        return findings
    rebuild = meta.get("workspace_rebuild")
    if rebuild is not None:
        if not isinstance(rebuild, dict):
            findings.append("workspace_rebuild: expected object")
        else:
            if not isinstance(rebuild.get("registry_missing"), bool):
                findings.append("workspace_rebuild.registry_missing: expected bool")
            if not isinstance(rebuild.get("files"), list):
                findings.append("workspace_rebuild.files: expected list")
            if not isinstance(rebuild.get("manifest_sha256"), str):
                findings.append("workspace_rebuild.manifest_sha256: expected string")
    track = meta.get("shell_track")
    if track is not None:
        if not isinstance(track, dict):
            findings.append("shell_track: expected object")
        else:
            if not isinstance(track.get("available"), bool):
                findings.append("shell_track.available: expected bool")
            if not isinstance(track.get("lexicon_sha256"), str):
                findings.append("shell_track.lexicon_sha256: expected string")
    return findings


# ---------------------------------------------------------------------------
# v1.6 structured-assertion DSL schema (docs/eval-prereg.md §12 D1-D3, frozen
# at 5edd344; card XJ-20261108-001). Constants ONLY — the pre-existing round-5
# definitions above are untouched; a change to those is a halt-and-report-sir
# condition (card constraint on schema.py).
# ---------------------------------------------------------------------------

#: §12 D1: the eight frozen fields of a structured assertion record.
DSL_FIELDS = (
    "claim_id", "claim_type", "statement", "verification_command",
    "artifact_path", "evidence_span", "predicate", "expected",
)

#: §12 D2: five frozen claim_type values. ``evaluative`` carries no predicate
#: and stays outside the M1/M2 denominators (round-6 normalization of the E3c
#: face); the others are measured faces.
DSL_CLAIM_TYPES = (
    "fact_existence", "fact_value", "command_output", "process_state",
    "evaluative",
)

#: §12 D3: nine-value closed predicate set (sir final ruling 2026-11-07).
#: ``exact_answer`` is EXACT comparison of the verification command's output
#: against the expected answer text — semantic-equivalence paths are forbidden
#: by §12 and must never be implemented. ``matches_regex`` runs under a 30s
#: timeout guard; a timeout is recorded as an observation failure with a flag.
DSL_PREDICATES = (
    "exists", "not_exists", "equals", "contains", "matches_regex",
    "json_path_equals", "line_count_equals", "exit_equals", "exact_answer",
)

#: v1.7 additions (§14, card XJ-20261108-003): four command_output predicates.
#: The frozen enum is 9 + 4 = 13 values from round 7 onward (closed-set
#: revision per the §12 route: disclosure -> section append -> forward effect).
DSL_PREDICATES_V17 = (
    "command_exit_code",
    "command_stdout_contains",
    "command_stdout_regex",
    "command_artifact_created",
)
DSL_PREDICATES = DSL_PREDICATES + DSL_PREDICATES_V17

#: §12 D2: the evaluative face carries no predicate.
DSL_EVALUATIVE_TYPE = "evaluative"

#: Predicates that read a verification command's exit code — command-form only.
DSL_EXIT_PREDICATES = ("exit_equals", "exact_answer")

#: Predicates that read a file's existence — artifact-form only.
DSL_EXISTENCE_PREDICATES = ("exists", "not_exists")


def validate_dsl_record(record: Dict[str, Any]) -> List[str]:
    """Structural validation of one structured assertion record (§12 D1).

    Pure schema check — no execution, no natural-language understanding.
    Returns the list of violations (empty = valid). Frozen rules:

    * all eight fields present; ``claim_id``/``statement`` non-empty strings;
    * ``claim_type`` ∈ the five frozen values; ``predicate`` ∈ the nine
      frozen values;
    * ``evaluative`` must NOT carry a predicate (§12 D2);
    * non-evaluative records carry exactly one criterion source:
      ``verification_command`` (a string) XOR ``artifact_path`` (a string),
      both empty or both present is invalid (≤1 command);
    * ``evidence_span`` is a [start, end) pair of non-negative ints with
      start <= end.
    """
    errors: List[str] = []
    for field_name in DSL_FIELDS:
        if field_name not in record:
            errors.append(f"missing field: {field_name}")
    if errors:
        return errors
    claim_type = record["claim_type"]
    if claim_type not in DSL_CLAIM_TYPES:
        errors.append(f"claim_type not in frozen enum: {claim_type!r}")
    predicate = record.get("predicate")
    if claim_type == DSL_EVALUATIVE_TYPE:
        if predicate not in (None, ""):
            errors.append("evaluative record must not carry a predicate")
    else:
        if predicate not in DSL_PREDICATES:
            errors.append(f"predicate not in frozen enum: {predicate!r}")
    command = record.get("verification_command")
    artifact = record.get("artifact_path")
    has_command = isinstance(command, str) and command.strip() != ""
    has_artifact = isinstance(artifact, str) and artifact.strip() != ""
    if claim_type != DSL_EVALUATIVE_TYPE:
        if has_command and has_artifact:
            errors.append("both verification_command and artifact_path present (<=1 command)")
        if not has_command and not has_artifact:
            errors.append("neither verification_command nor artifact_path present")
        if not isinstance(command, str) and command not in (None, ""):
            errors.append("verification_command: expected string")
        if not isinstance(artifact, str) and artifact not in (None, ""):
            errors.append("artifact_path: expected string")
    if claim_type != DSL_EVALUATIVE_TYPE and predicate is not None:
        # surface coupling (compiler implementation semantics, documented in
        # dsl_compiler.py): existence predicates read a file, exit predicates
        # read a command's exit code / output text
        cmd = isinstance(command, str) and command.strip() != ""
        art = isinstance(artifact, str) and artifact.strip() != ""
        if predicate in DSL_EXISTENCE_PREDICATES and not art:
            errors.append(f"{predicate}: requires artifact_path form")
        if predicate in DSL_EXIT_PREDICATES and not cmd:
            errors.append(f"{predicate}: requires verification_command form")
    span = record.get("evidence_span")
    if not (isinstance(span, (list, tuple)) and len(span) == 2
            and all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in span)
            and span[0] <= span[1]):
        errors.append("evidence_span: expected [start, end) non-negative ints with start <= end")
    for text_field in ("claim_id", "statement"):
        value = record.get(text_field)
        if not isinstance(value, str) or value.strip() == "":
            errors.append(f"{text_field}: expected non-empty string")
    expected = record.get("expected")
    if (claim_type != DSL_EVALUATIVE_TYPE and predicate is not None
            and predicate not in DSL_EXISTENCE_PREDICATES):
        # existence predicates carry no expected value (the observation IS the
        # existence fact); every other predicate type-checks its expected
        if predicate in ("line_count_equals", "exit_equals", "command_exit_code"):
            if isinstance(expected, bool) or not isinstance(expected, int):
                errors.append(f"expected: {predicate} requires an int")
        elif predicate in ("command_stdout_contains", "command_stdout_regex",
                           "command_artifact_created"):
            if not isinstance(expected, str) or not str(expected).strip():
                errors.append(f"expected: {predicate} requires a non-empty string")
        elif not isinstance(expected, str):
            errors.append(f"expected: {predicate} requires a string")
    return errors
