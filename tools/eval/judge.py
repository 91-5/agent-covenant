"""Five-level deterministic judge: E0 无证据行 / E1 缺字段 / E2 不可复现 /
E3 不支持 / E4 支持.

Frozen decision order (docs/eval-prereg.md §1 -- restate, never re-derive):

1. **E0** -- claim exists, no evidence line bound to it. (无依据主张)
2. **E1** -- evidence line present but incomplete: neither the command form
   (``cmd`` + ``exit`` or ``out``) nor the independent-review ref form. (无依据主张)
3. **E2** -- evidence structurally complete, but the observation does not
   reproduce: the ref path does not exist; or the command cannot start / is
   refused by the denylist / times out; or the actual exit code differs from
   the claimed one; or the claimed ``out`` substring is absent from the actual
   output. The evidence evaporates on contact with reality. (无依据主张)
4. **E3** -- the observation reproduces exactly as claimed, but does not
   support the assertion: not every claim anchor appears in the observation
   text. 矛盾 and 无关 deliberately collapse into this single mechanical rule
   -- both mean "the cited evidence fails to carry the claim", which is what
   M1 counts; telling them apart is adjudication-layer work, not judge work.
5. **E4** -- observation reproduces and every anchor is present. An
   *unanchored* claim (no integers, no backticked tokens) passes
   mechanically when its evidence reproduces, and is flagged ``unanchored``
   in every downstream surface: a mechanical pass must never masquerade as a
   semantic one.

Determinism contract: same input text + same filesystem state + same command
outputs => same levels, same flags, same detail strings. No LLM, no network,
no randomness at this layer (dp 纪律：判定器确定性).

Execution safety: commands arrive from product markdown, i.e. from the
environment under test. Every command passes a frozen denylist before
executing (recursive deletes, disk format, shutdown, remote-execution pipes
...). A refused command is judged E2 with flag ``refused_exec`` -- refusal can
never manufacture an E4, so the denylist cannot be gamed upward. The residual
risk of running measured products' commands locally is stated in the prereg
limitations, not hidden.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from extract import extract_claims
from schema import Claim, ClaimJudgement, EvidenceLine

DEFAULT_TIMEOUT_SECONDS = 120

#: Frozen denylist (docs/eval-prereg.md §1.6). Matched case-insensitively as
#: substrings; a longer list adds refusals, never approvals.
COMMAND_DENYLIST = (
    "rm -rf", "rm -fr", "rmdir /s", "rd /s", "del /s", "del /f", "erase /s",
    "format ", "mkfs", "diskpart", "cipher /w",
    "shutdown", "restart-computer", "stop-computer",
    "reg delete", "reg add", "remove-item -recurse", "remove-item -force",
    "curl ", "wget ", "invoke-webrequest", "invoke-expression", "iex ",
    "| sh", "| bash", "|sh", "|bash", "git push --force", "git push -f",
    "git reset --hard", "git clean -fd", "> /dev/sd", "dd if=",
)


@dataclass
class ReproResult:
    """Outcome of attempting to reproduce one evidence line's observation."""

    reproduced: bool
    observation: str = ""
    detail: str = ""
    refused: bool = False
    #: v1.5 C11 track flags (pwsh_exit_level_only / pwsh_unavailable /
    #: command_too_long) and C10 ref flags (ref_missing_both). Empty on the
    #: legacy single-root path, so pre-v1.5 behaviour carries zero new flags.
    track_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "reproduced": self.reproduced,
            "observation": self.observation,
            "detail": self.detail,
            "refused": self.refused,
        }


def command_refused(command: str) -> Optional[str]:
    """Return the matched denylist pattern, or None if the command may run."""
    lowered = command.lower()
    for pattern in COMMAND_DENYLIST:
        if pattern in lowered:
            return pattern
    return None


#: v1.5 C11 frozen PowerShell-flavor lexicon — copied verbatim from
#: docs/eval-prereg.md §11 (C11, frozen at a1b5ec2); no token may be added or
#: removed here without a prereg revision. Matched case-insensitively as
#: substrings of the command line.
POWERSHELL_FLAVOR_TOKENS = (
    "get-content", "test-path", "select-string", "get-childitem", "get-item",
    "get-date", "measure-object", "set-content", "copy-item", "write-output",
    "out-string", "format-table", "get-random", "get-process", "sort-object",
)

#: pwsh track refuses to execute absurdly long commands (the -EncodedCommand
#: wrapper inflates UTF-16LE by ~2.7x; 8000 raw chars stays far below every
#: Windows command-line limit). Over-limit commands are flagged, not run —
#: the flag keeps the refusal auditable instead of silently biased.
MAX_PWSH_COMMAND_CHARS = 8000

_PWSH_PROBE_CACHE: Optional[Dict[str, object]] = None


def is_powershell_flavor(command: str) -> bool:
    """C11 flavor dispatch: True only when a frozen lexicon token appears."""
    lowered = (command or "").lower()
    return any(token in lowered for token in POWERSHELL_FLAVOR_TOKENS)


def lexicon_sha256() -> str:
    """Stable hash of the frozen lexicon; recorded into packaging metadata so
    any drift between judge.py and v1.5 §11 is detectable."""
    import hashlib

    payload = "\n".join(POWERSHELL_FLAVOR_TOKENS)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def powershell_track_info() -> Dict[str, object]:
    """Probe Windows PowerShell once and cache the result: availability,
    version, execution policy. Recorded into packaging metadata (C11 blind-spot
    seal); a missing powershell.exe is an explicit fact, never a silent
    fallback to cmd."""
    global _PWSH_PROBE_CACHE
    if _PWSH_PROBE_CACHE is not None:
        return dict(_PWSH_PROBE_CACHE)
    probe = ("powershell -NoProfile -NonInteractive -Command "
             "\"[Console]::Out.Write('v=' + $PSVersionTable.PSVersion.ToString() "
             "+ ';ep=' + (Get-ExecutionPolicy))\"")
    exit_code, output, _error = run_command(probe, Path.cwd(), 30)
    info: Dict[str, object] = {"available": False, "version": None,
                               "execution_policy": None,
                               "engine": "powershell.exe (Windows PowerShell)"}
    if exit_code == 0 and "v=" in output and ";ep=" in output:
        body = output.strip()
        try:
            kv = body.split("v=", 1)[1].split(";", 1)
            info["version"] = kv[0].strip() or None
            ep = body.split(";ep=", 1)[1].strip()
            info["execution_policy"] = ep or None
            info["available"] = True
        except (IndexError, ValueError):
            info["available"] = False
    _PWSH_PROBE_CACHE = dict(info)
    return dict(_PWSH_PROBE_CACHE)


def _pwsh_wrapper(command: str) -> str:
    """C11 pwsh track invocation — same encoding as the round-4 attribution
    instrument: UTF-16LE base64 via -EncodedCommand (no quoting ambiguity)."""
    import base64

    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
    return f"powershell -NoProfile -NonInteractive -EncodedCommand {encoded}"


def _reproduce_pwsh(evidence: EvidenceLine, cwd: Path,
                    timeout: int) -> ReproResult:
    """C11 pwsh track. Reproduction = exit match AND claimed out= hit (the
    ADV-1 output-semantic check: PowerShell cmdlets return exit 0 on logical
    no-match, so exit alone never counts as reproduction)."""
    if len(evidence.command) > MAX_PWSH_COMMAND_CHARS:
        return ReproResult(
            reproduced=False,
            detail=(f"命令超长（{len(evidence.command)} > {MAX_PWSH_COMMAND_CHARS}），"
                    f"pwsh 轨不予执行: {evidence.command}"),
            track_flags=["command_too_long"],
        )
    track = powershell_track_info()
    if not track["available"]:
        return ReproResult(
            reproduced=False,
            detail=f"命令无法完成观察: powershell 不可用，pwsh 轨拒绝执行: {evidence.command}",
            track_flags=["pwsh_unavailable"],
        )
    exit_code, output, error = run_command(
        _pwsh_wrapper(evidence.command), cwd, timeout)
    if error:
        return ReproResult(
            reproduced=False,
            detail=f"命令无法完成观察: {evidence.command} ({error})")
    if evidence.exit_code is not None and exit_code != evidence.exit_code:
        return ReproResult(
            reproduced=False,
            observation=output,
            detail=f"退出码不符: 证据声称 exit={evidence.exit_code}, 实际 exit={exit_code}")
    if evidence.out is not None and evidence.out not in output:
        return ReproResult(
            reproduced=False,
            observation=output,
            detail=f"声称输出未复现: out={evidence.out!r} 不在实际输出中")
    detail_bits = [f"pwsh 轨已复现: {evidence.command}", f"exit={exit_code}"]
    flags: List[str] = []
    if evidence.out is not None:
        detail_bits.append(f"out={evidence.out!r} 已命中")
    else:
        # ADV-1: exit-only match on the pwsh track is exit-level reproduction,
        # never semantic reproduction — carried as an explicit flag.
        detail_bits.append("证据无 out=，仅 exit 级复现")
        flags.append("pwsh_exit_level_only")
    return ReproResult(reproduced=True, observation=output,
                       detail="; ".join(detail_bits), track_flags=flags)


def run_command(command: str, cwd: Path, timeout: int) -> Tuple[Optional[int], str, str]:
    """Run a command in ``cwd``; returns (exit_code, combined_output, error).

    exit_code is None when the process could not be started at all. Output is
    stdout+stderr, decoded with replacement -- judge outputs must never crash
    on exotic bytes (same console discipline as the repo's other tools).
    """
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            timeout=timeout,
            capture_output=True,
        )
    except subprocess.TimeoutExpired:
        return None, "", f"timeout after {timeout}s"
    except OSError as exc:
        return None, "", f"could not start: {exc}"
    output = (completed.stdout or b"").decode("utf-8", errors="replace")
    errout = (completed.stderr or b"").decode("utf-8", errors="replace")
    return completed.returncode, output + ("\n" + errout if errout else ""), ""


def reproduce(evidence: EvidenceLine, root: Path, timeout: int,
              workspace: Optional[Path] = None) -> ReproResult:
    """Attempt to reproduce one evidence line's claimed observation.

    Ref-form: the observation is the referenced file's text, prefixed with the
    ref path itself (so a claim anchoring its own ref path is legitimately
    satisfiable -- frozen in §1.4). Cmd-form: the command runs in ``root``.

    v1.5 C10/C11 (round-5 instrument, card XJ-20261106-002): when ``workspace``
    is given (packaging-time judging against a rebuilt execution workspace),
    command evidence reruns with cwd=workspace and ref evidence resolves
    workspace first, then root (``ref_missing_both`` flag when neither has the
    file). PowerShell-flavor commands dispatch to the C11 pwsh track. Without
    ``workspace`` every path behaves exactly as before the v1.5 revision --
    legacy callers (run.py --judge, --dry-run, selftest bank) are pinned to
    byte-identical behaviour by tests.
    """
    if evidence.has_ref_form:
        surfaces: List[Tuple[str, Path]] = []
        if workspace is not None:
            surfaces.append(("workspace", workspace / evidence.ref))
        surfaces.append(("root", root / evidence.ref))
        for _surface_name, ref_path in surfaces:
            if ref_path.is_file():
                try:
                    text = ref_path.read_text(encoding="utf-8", errors="replace")
                except OSError as exc:
                    return ReproResult(reproduced=False, detail=f"ref 不可读: {exc}")
                return ReproResult(
                    reproduced=True,
                    observation=f"ref={evidence.ref}\n{text[:20000]}",
                    detail=f"ref 存在且可读: {evidence.ref}",
                )
        missing_flags = ["ref_missing_both"] if workspace is not None else []
        return ReproResult(
            reproduced=False,
            detail=f"ref 不存在: {evidence.ref}",
            track_flags=missing_flags,
        )

    # Command form.
    assert evidence.command is not None  # completeness was checked upstream
    matched = command_refused(evidence.command)
    if matched is not None:
        return ReproResult(
            reproduced=False,
            refused=True,
            detail=f"命令命中拒绝清单({matched!r})，不予执行: {evidence.command}",
        )
    cwd = workspace if workspace is not None else root
    if is_powershell_flavor(evidence.command):
        return _reproduce_pwsh(evidence, cwd, timeout)
    exit_code, output, error = run_command(evidence.command, cwd, timeout)
    if error:
        return ReproResult(
            reproduced=False,
            detail=f"命令无法完成观察: {evidence.command} ({error})",
        )
    if evidence.exit_code is not None and exit_code != evidence.exit_code:
        return ReproResult(
            reproduced=False,
            observation=output,
            detail=f"退出码不符: 证据声称 exit={evidence.exit_code}, 实际 exit={exit_code}",
        )
    if evidence.out is not None and evidence.out not in output:
        return ReproResult(
            reproduced=False,
            observation=output,
            detail=f"声称输出未复现: out={evidence.out!r} 不在实际输出中",
        )
    detail_bits = [f"命令已复现: {evidence.command}", f"exit={exit_code}"]
    if evidence.out is not None:
        detail_bits.append(f"out={evidence.out!r} 已命中")
    return ReproResult(reproduced=True, observation=output, detail="; ".join(detail_bits))


def _all_anchors_present(claim: Claim, observation: str) -> bool:
    return all(anchor in observation for anchor in claim.anchors)


def judge_claim(claim: Claim, root: Path, timeout: int = DEFAULT_TIMEOUT_SECONDS,
                workspace: Optional[Path] = None) -> ClaimJudgement:
    """Judge one claim. See module docstring for the frozen decision order."""
    if claim.evidence is None:
        return ClaimJudgement(
            claim=claim,
            level="E0",
            detail="断言存在但无证据行",
        )
    if not claim.evidence.is_complete:
        missing = []
        if claim.evidence.command is None and claim.evidence.ref is None:
            missing.append("缺命令与 ref")
        elif claim.evidence.command is not None:
            missing.append("命令缺 exit/out 字段")
        else:
            missing.append("ref 形式不完整")
        return ClaimJudgement(
            claim=claim,
            level="E1",
            detail=f"证据行存在但字段不完整（{'; '.join(missing)}）: {claim.evidence.raw}",
        )

    flags: List[str] = []
    if claim.unanchored:
        flags.append("unanchored")

    result = reproduce(claim.evidence, root, timeout, workspace=workspace)
    if result.refused:
        flags.append("refused_exec")
    flags.extend(result.track_flags)
    if not result.reproduced:
        return ClaimJudgement(
            claim=claim,
            level="E2",
            flags=flags,
            detail=result.detail,
            observation=result.observation,
        )

    if claim.unanchored:
        return ClaimJudgement(
            claim=claim,
            level="E4",
            flags=flags,
            detail=result.detail + "（无语义锚，仅机械复核通过）",
            observation=result.observation,
        )
    if _all_anchors_present(claim, result.observation):
        return ClaimJudgement(
            claim=claim,
            level="E4",
            flags=flags,
            detail=result.detail,
            observation=result.observation,
        )
    missing_anchors = [anchor for anchor in claim.anchors if anchor not in result.observation]
    return ClaimJudgement(
        claim=claim,
        level="E3",
        flags=flags,
        detail=(
            f"观察已复现但不支持断言（锚未命中: {missing_anchors}）——"
            f"证据与断言矛盾或无关"
        ),
        observation=result.observation,
    )


def judge_markdown(
    markdown_text: str,
    root: Path,
    product: str = "<memory>",
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    workspace: Optional[Path] = None,
) -> List[ClaimJudgement]:
    """Extract then judge every claim in one product. The harness's front door.

    ``workspace`` (v1.5 C10): the rebuilt execution workspace for packaging-time
    judging; None keeps the legacy single-root behaviour."""
    judgements: List[ClaimJudgement] = []
    for claim in extract_claims(markdown_text, product=product):
        judgements.append(judge_claim(claim, root, timeout=timeout,
                                      workspace=workspace))
    return judgements


def judge_file(product_path: Path, root: Path, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> List[ClaimJudgement]:
    """Judge one product file on disk."""
    text = product_path.read_text(encoding="utf-8", errors="replace")
    return judge_markdown(text, root, product=str(product_path), timeout=timeout)
