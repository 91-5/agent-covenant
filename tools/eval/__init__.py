"""agent-covenant process-integrity eval harness (XJ-20261024-001).

This package is an OBSERVER. It measures the covenant process; it never
modifies it. The red line is load-bearing, not stylistic:

    gate.py / lint_cards.py / pre-push-hook.sh / verdicts/ / .tasks/ existing
    cards are read at most, written never. A harness that edits the system
    under test has contaminated its own evidence.

Everything here is stdlib-only and Python 3.9 compatible (CI constraint).
Judging E0-E4 is deterministic pure rules -- the same input always yields the
same output, and no LLM participates at this layer. LLM judgement belongs to
the (blinded) adjudication layer, which is a human process, not this package.

Wording discipline (EVO-20261024-001): conclusions from this harness may only
be stated as "evidence under pre-registered conditions" (预注册条件下的对照
证据). The word 证明 is banned for outcome claims -- see docs/eval-prereg.md.
"""
from __future__ import annotations

HARNESS_VERSION = "1.0.0"

#: Cards this package was built under; recorded for provenance, not policy.
PROVENANCE = {
    "card": "XJ-20261024-001",
    "upstream_discipline": "EVO-20261024-001",
    "base_commit": "bebfb64",
}
