"""Assertion extractor: product markdown -> Claim objects.

The grammar below is the frozen claim surface (docs/eval-prereg.md §1). It is
deliberately small and regex-checkable so that judging stays deterministic:

    - [已验证] <claim text>
      证据：cmd=`<command>` exit=<int> out=`<expected substring>`

    - [已验证] <claim text>
      证据：ref=<path>（独立复核）

Extraction rules, all mechanical:

1. A *claim unit* is a list item (``-``/``*``/numbered, any indent) whose text
   contains the literal marker ``[已验证]``. No marker, no claim -- ordinary
   prose is never judged (the harness measures assertions that *claim* to be
   verified, not everything an agent writes).
2. The *evidence line* is the first non-empty line after the claim line that
   starts with ``证据：`` (after optional list indentation), OR a ``证据：``
   segment on the same line after the claim text. An evidence line binds to
   exactly the claim it follows; the next claim terminates the search window
   (a claim can never inherit a later claim's evidence).
3. Fields are parsed order-independently: ``cmd=`` `...` `` `` (backticked, may
   contain spaces), ``exit=`` digits, ``out=`` `...` `` ``, ``ref=`` backticked
   or single token. Unrecognised trailing text is ignored, not an error -- E1
   is decided by *absence* of complete fields, which keeps the rule monotone:
   more decoration can only help, never reclassify.

Known boundary (review question 4, frozen): wording variants of the markers
(``[验证过]``, ``依据：`` ...) are NOT recognised. A miss hides a claim from
judging entirely, which removes it from the M2 denominator -- optimistic
(under-reports 无依据主张). This bias is stated in the report's limitations,
not patched ad hoc in code.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from schema import Claim, EvidenceLine

CLAIM_MARKER = "[已验证]"
EVIDENCE_PREFIX = "证据："

#: Standalone integers only: not inside identifiers (XJ-20261024-001) and not
#: fragments of decimals or hyphenated dates. Frozen anchor rule, §1.
INTEGER_ANCHOR_RE = re.compile(r"(?<![\w.\-])\d+(?![\w.\-])")

BACKTICK_RE = re.compile(r"`([^`]+)`")

LIST_ITEM_RE = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")

EVIDENCE_LINE_RE = re.compile(r"^\s*证据[:：]\s*(.*)$")

_FIELD_CMD = re.compile(r"cmd\s*=\s*`([^`]+)`|cmd\s*=\s*(\S+)")
_FIELD_EXIT = re.compile(r"exit\s*=\s*(\d+)")
_FIELD_OUT = re.compile(r"out\s*=\s*`([^`]+)`")
_FIELD_REF = re.compile(r"ref\s*=\s*`([^`]+)`|ref\s*=\s*(\S+)")


def extract_anchors(claim_text: str) -> List[str]:
    """Frozen anchor rule: standalone integers plus backticked tokens.

    Anchors are the *only* semantic handle the deterministic judge has (§1):
    E4 requires every anchor to appear in the reproduced observation. Claims
    with no anchor at all are marked unanchored -- they are still judged
    mechanically (exit/out/ref), and the unanchored flag is carried into every
    report so nobody mistakes a mechanical pass for a semantic one.
    """
    anchors: List[str] = []
    for match in BACKTICK_RE.finditer(claim_text):
        token = match.group(1).strip()
        if token:
            anchors.append(token)
    for match in INTEGER_ANCHOR_RE.finditer(BACKTICK_RE.sub(" ", claim_text)):
        anchors.append(match.group(0))
    # De-duplicate, keep first-occurrence order (dicts are ordered, 3.7+).
    return list(dict.fromkeys(anchors))


def _parse_evidence_fields(payload: str) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[str]]:
    command = exit_code = out = ref = None
    match = _FIELD_CMD.search(payload)
    if match:
        command = (match.group(1) or match.group(2) or "").strip() or None
    match = _FIELD_EXIT.search(payload)
    if match:
        exit_code = int(match.group(1))
    match = _FIELD_OUT.search(payload)
    if match:
        out = match.group(1)
    match = _FIELD_REF.search(payload)
    if match:
        ref = (match.group(1) or match.group(2) or "").strip().strip("`") or None
    return command, exit_code, out, ref


def _find_evidence_line(lines: List[str], claim_index: int) -> Optional[EvidenceLine]:
    """Bind the evidence line that follows a claim, per frozen rule 2."""
    item_text = lines[claim_index]
    inline_match = re.search(re.escape(EVIDENCE_PREFIX) + r"\s*(.*)$", item_text)
    if inline_match:
        payload = inline_match.group(1).strip()
        if payload:
            command, exit_code, out, ref = _parse_evidence_fields(payload)
            return EvidenceLine(
                raw=payload, source_line=claim_index + 1,
                command=command, exit_code=exit_code, out=out, ref=ref,
            )
    for index in range(claim_index + 1, len(lines)):
        line = lines[index]
        if not line.strip():
            continue
        # A new list item at the same or shallower indent ends the window:
        # this is the next claim's territory, not ours.
        list_match = LIST_ITEM_RE.match(line)
        if list_match and index != claim_index:
            window_indent = len(LIST_ITEM_RE.match(item_text).group(1)) if LIST_ITEM_RE.match(item_text) else 0
            if len(list_match.group(1)) <= window_indent:
                break
            # Deeper-nested item that is not an evidence line: still within
            # this claim's block; keep scanning for the evidence line.
        evidence_match = EVIDENCE_LINE_RE.match(line)
        if evidence_match:
            payload = evidence_match.group(1).strip()
            command, exit_code, out, ref = _parse_evidence_fields(payload)
            return EvidenceLine(
                raw=payload, source_line=index + 1,
                command=command, exit_code=exit_code, out=out, ref=ref,
            )
        if list_match:
            continue  # deeper list content: keep scanning inside the block
        # Plain prose continuation lines do not terminate the window but are
        # not evidence either; only a 证据： line can be.
        continue
    return None


def extract_claims(markdown_text: str, product: str = "<memory>") -> List[Claim]:
    """Extract every claim unit from a product markdown. Deterministic:
    same text, same product name, same output list."""
    lines = markdown_text.splitlines()
    claims: List[Claim] = []
    for index, line in enumerate(lines):
        list_match = LIST_ITEM_RE.match(line)
        body = list_match.group(2) if list_match else line
        marker_at = body.find(CLAIM_MARKER)
        if marker_at < 0:
            continue
        text = body.replace(CLAIM_MARKER, "", 1)
        # Same-line evidence (rule 2) is split off before anchor extraction.
        text = re.split(re.escape(EVIDENCE_PREFIX), text)[0]
        text = text.strip().strip("*").strip()
        if not text:
            continue  # a bare marker with no assertion is not a claim
        evidence = _find_evidence_line(lines, index)
        anchors = extract_anchors(text)
        claims.append(
            Claim(
                text=text,
                source_line=index + 1,
                product=product,
                evidence=evidence,
                anchors=anchors,
                unanchored=(len(anchors) == 0),
            )
        )
    return claims
