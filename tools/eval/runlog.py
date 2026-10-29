#!/usr/bin/env python3
"""run-log v2: the execution recorder for the tool-enabled executor (D1 of
XJ-20261030-001).

Round four introduces a tool-enabled executor (prereg v1.3, C7), and the first
extra execution constraint of v1.3 turns "the executor must leave execution
traces" from a promise into a file: every command that really runs is recorded
-- the command, its working directory, its exit code, stdout/stderr summaries
(truncated to a fixed length) and a UTC ISO-8601 timestamp. Arm B's "wrote
evidence from knowledge alone" is then checkable the mechanical way: a B-arm
run-log holds zero execution records, exactly as round 3's run-log-r3.json
showed (B: 0 records, A: 126).

Format contract (self-described, backward compatible):

* File shape: ``{runlog_version, generated_utc, workspace, note, records[]}``.
  ``runlog_version = 2`` (the ``FORMAT_VERSION`` constant of this module) is
  the self-description; readers of the round-3 format (v1) read ``records[]``
  unchanged.
* Every record is a strict superset of the v1 record written by
  ``study_runner.RunLog``: all v1 fields (key / task_id / condition / kind /
  command / executed / exit_code / refused / error / utc) keep their names and
  their meaning; v2 adds cwd / stdout_summary / stderr_summary plus the two
  truncation flags. A v1 reader that iterates records keeps working; a v1
  writer's files load fine through :func:`RunLog.load`.
* v1 semantics stay reachable: ``records_for("B")`` comes back empty for a
  B-arm run, and a refused command is recorded without being executed.

Discipline this module keeps on purpose:

* stdlib-only, Python 3.9 compatible (package constraint), no printing --
  recording returns data, the CLI decides what to show.
* The summaries are an *audit* context, not the frozen evidence grammar: they
  are raw prefixes of the captured streams, not ``out=`` spans, and never feed
  judging. Judging stays in judge.py; refusing stays the caller's decision
  (``run.py --exec`` consults ``judge.command_refused`` so the frozen
  denylist text is imported, never copied -- protocol §8).
* An existing log file that cannot be parsed raises instead of being silently
  overwritten: a recorder that clobbers an audit trail it cannot read is the
  failure mode this card exists to close.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

#: Self-described format version, mirrored into every written file as
#: ``runlog_version``. v1 = the round-3 ``run-log.json`` shape written by
#: ``study_runner.RunLog``; v2 = strict superset of v1.
FORMAT_VERSION = 2

#: Fields a run-log-r3.json (v1) reader may rely on, kept verbatim.
V1_RECORD_FIELDS = ("key", "task_id", "condition", "kind", "command",
                    "executed", "exit_code", "refused", "error", "utc")

#: Fixed cap for each captured-stream summary. Deliberately the same bound as
#: the evidence-snippet grammar (study_runner.SNIPPET_MAX_CHARS) so no single
#: record can silently outweigh the product text it audits.
SUMMARY_MAX_CHARS = 500

#: v1 kinds are "evidence" | "acceptance" (runner-side). The executor wrapper
#: records kind="exec" so runner-side and executor-side entries stay
#: distinguishable without breaking v1 readers (the field is free-form there).
DEFAULT_KIND = "exec"


def _utc_iso() -> str:
    """UTC ISO-8601, second precision (same shape as study_runner.now_iso)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _decode(data: Optional[bytes]) -> str:
    if data is None:
        return ""
    return data.decode("utf-8", errors="replace")


def _summary(text: Optional[str]) -> Tuple[Optional[str], bool]:
    """(prefix, was_truncated) under the fixed cap; None stays None so a
    missing observation keeps being missing."""
    if text is None:
        return None, False
    text = str(text)
    if len(text) > SUMMARY_MAX_CHARS:
        return text[:SUMMARY_MAX_CHARS], True
    return text, False


def record(command: str, *, cwd: Any = None, exit_code: Optional[int] = None,
           stdout: Optional[str] = None, stderr: Optional[str] = None,
           executed: Optional[bool] = None, error: str = "",
           refused: Optional[str] = None, kind: str = DEFAULT_KIND,
           key: str = "", task_id: str = "", condition: str = "",
           utc: Optional[str] = None) -> Dict[str, Any]:
    """Build one v2 record dict. Pure: appends nothing, prints nothing.

    ``cwd`` defaults to the recording process's working directory at call
    time, so the field is always a concrete path. ``executed`` defaults to
    "an exit code exists" -- a timeout or a failed spawn therefore records
    ``executed=false`` exactly like v1. All v1 fields are always present.
    """
    if isinstance(exit_code, bool) or not (
            exit_code is None or isinstance(exit_code, int)):
        raise TypeError(f"exit_code must be None or int, got {exit_code!r}")
    if executed is None:
        executed = exit_code is not None
    out_summary, out_truncated = _summary(stdout)
    err_summary, err_truncated = _summary(stderr)
    entry: Dict[str, Any] = {
        # v1 fields (run-log-r3.json readers depend on these names).
        "key": key,
        "task_id": task_id,
        "condition": condition,
        "kind": kind,
        "command": command,
        "executed": executed,
        "exit_code": exit_code,
        "refused": refused,
        "error": error,
        "utc": utc or _utc_iso(),
        # v2 fields.
        "cwd": str(Path(cwd)) if cwd is not None else str(Path.cwd()),
        "stdout_summary": out_summary,
        "stderr_summary": err_summary,
        "stdout_truncated": out_truncated,
        "stderr_truncated": err_truncated,
    }
    return entry


def execute(command: str, *, cwd: Any = None, timeout: Optional[int] = None,
            log: Optional["RunLog"] = None,
            **context: Any) -> Tuple[Dict[str, Any], str, str]:
    """Run ``command`` in a subprocess, record it, and return
    ``(record, full_stdout, full_stderr)``.

    The record carries the truncated summaries; the caller decides what to do
    with the full streams (``run.py --exec`` echoes them). ``timeout=None``
    means no limit -- callers that wrap executor commands should always pass
    one (``run.py --exec`` passes its ``--timeout``, default 120s). A refused
    command is NOT this function's concern: check ``judge.command_refused``
    first and record it with ``executed=False, refused=...`` so the refusal
    itself stays in the trace (protocol §3.4: missing observations stay
    missing, refusals stay visible).
    """
    workdir = Path(cwd) if cwd is not None else Path.cwd()
    try:
        completed = subprocess.run(command, shell=True, cwd=str(workdir),
                                   timeout=timeout, capture_output=True)
    except subprocess.TimeoutExpired as exc:
        entry = record(command, cwd=workdir, exit_code=None,
                       stdout=_decode(exc.stdout), stderr=_decode(exc.stderr),
                       error=f"timeout after {timeout}s", **context)
        full_out, full_err = _decode(exc.stdout), _decode(exc.stderr)
    except OSError as exc:
        entry = record(command, cwd=workdir, exit_code=None,
                       error=f"could not start: {exc}", **context)
        full_out = full_err = ""
    else:
        full_out, full_err = _decode(completed.stdout), _decode(completed.stderr)
        entry = record(command, cwd=workdir, exit_code=completed.returncode,
                       stdout=full_out, stderr=full_err, **context)
    if log is not None:
        log.records.append(entry)
    return entry, full_out, full_err


class RunLog:
    """In-memory run-log v2: an append-only list of records plus the file
    (de)serialization. The workspace attribute keeps v1 file shape parity."""

    def __init__(self, workspace: Any = None,
                 records: Optional[List[Dict[str, Any]]] = None) -> None:
        self.workspace = Path(workspace) if workspace is not None else Path.cwd()
        self.records: List[Dict[str, Any]] = list(records or [])

    def record(self, command: str, **kwargs: Any) -> Dict[str, Any]:
        entry = record(command, **kwargs)
        self.records.append(entry)
        return entry

    def execute(self, command: str, *, cwd: Any = None,
                timeout: Optional[int] = None,
                **context: Any) -> Dict[str, Any]:
        entry, _out, _err = execute(command, cwd=cwd, timeout=timeout,
                                    log=self, **context)
        return entry

    def records_for(self, condition: str) -> List[Dict[str, Any]]:
        """v1 parity: the arm filter the B-arm-zero assertion reads."""
        return [r for r in self.records if r.get("condition") == condition]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runlog_version": FORMAT_VERSION,
            "generated_utc": _utc_iso(),
            "workspace": str(self.workspace),
            "note": "every command run through the execution wrapper is "
                    "recorded here; a condition-B run must hold zero records "
                    "(v1.3 constraint 1; round-3 run-log-r3.json precedent: "
                    "B 0 / A 126)",
            "records": self.records,
        }

    def save(self, path: Any) -> Path:
        """Write the whole log (create or overwrite). Appending across wrapper
        invocations is load() -> record -> save(), never a partial write."""
        path = Path(path)
        if str(path.parent):
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
                        encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Any, workspace: Any = None) -> "RunLog":
        """Read an existing log (v1 or v2) for append-resume. A missing file
        starts an empty log; a file that exists but cannot be parsed raises
        ValueError -- never silently overwritten."""
        path = Path(path)
        records: List[Dict[str, Any]] = []
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except ValueError as exc:
                raise ValueError(
                    f"{path}: existing run-log is not parseable JSON ({exc}); "
                    "refusing to overwrite an unreadable audit trail") from exc
            if isinstance(data, dict) and isinstance(data.get("records"), list):
                records = [r for r in data["records"] if isinstance(r, dict)]
        return cls(workspace=workspace, records=records)
