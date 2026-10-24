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


def reproduce(evidence: EvidenceLine, root: Path, timeout: int) -> ReproResult:
    """Attempt to reproduce one evidence line's claimed observation.

    Ref-form: the observation is the referenced file's text, prefixed with the
    ref path itself (so a claim anchoring its own ref path is legitimately
    satisfiable -- frozen in §1.4). Cmd-form: the command runs in ``root``.
    """
    if evidence.has_ref_form:
        ref_path = root / evidence.ref
        if not ref_path.is_file():
            return ReproResult(
                reproduced=False,
                detail=f"ref 不存在: {evidence.ref}",
            )
        try:
            text = ref_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return ReproResult(reproduced=False, detail=f"ref 不可读: {exc}")
        return ReproResult(
            reproduced=True,
            observation=f"ref={evidence.ref}\n{text[:20000]}",
            detail=f"ref 存在且可读: {evidence.ref}",
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
    exit_code, output, error = run_command(evidence.command, root, timeout)
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


def judge_claim(claim: Claim, root: Path, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> ClaimJudgement:
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

    result = reproduce(claim.evidence, root, timeout)
    if result.refused:
        flags.append("refused_exec")
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
) -> List[ClaimJudgement]:
    """Extract then judge every claim in one product. The harness's front door."""
    judgements: List[ClaimJudgement] = []
    for claim in extract_claims(markdown_text, product=product):
        judgements.append(judge_claim(claim, root, timeout=timeout))
    return judgements


def judge_file(product_path: Path, root: Path, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> List[ClaimJudgement]:
    """Judge one product file on disk."""
    text = product_path.read_text(encoding="utf-8", errors="replace")
    return judge_markdown(text, root, product=str(product_path), timeout=timeout)
