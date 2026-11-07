"""Round-6 unblind follow-up: arm-split of E3 attribution (advisory Q6 precondition).

Joins the sealed key (sir custody, sir authorized unblind 2026-11-07) with the
blind attribution rows from round5-e3-attribution.md AUTO:TABLE span.
No re-judging, no judge.py invocation, no drift concern: judgement levels and
attribution labels are untouched; this is a pure group-by over already-frozen
per-claim rows.

Outputs:
  dryrun/round6-armsplit.json          — machine-readable crosstab
  docs/round5-e3-attribution.md §8     — human-readable addendum (appended,
                                         clearly marked 解盲后追加, 解读层)
"""
import io
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent.parent
DOC = ROOT / "docs" / "round5-e3-attribution.md"
KEY = ROOT / ".eval-sealed" / "key-20261107T023933Z.json"
OUT = ROOT / "dryrun" / "round6-armsplit.json"

text = DOC.read_text(encoding="utf-8")
i = text.find("<!-- AUTO:TABLE -->")
j = text.find("<!-- /AUTO:TABLE -->")
assert i >= 0 and j > i, "AUTO:TABLE span not found"
span = text[i:j]

rows = []
for m in re.finditer(
    r"^\| (P\d+) \| `([^`]+)` \| (应-E2|仍-E3) \| (\d+) \| (.+?) \| ([^|]+) \|", span, re.M
):
    code, label, cf, nanchors, claim, sec = m.groups()
    rows.append(
        {"code": code, "label": label, "counterfactual": cf, "secondary": sec.strip()}
    )
assert len(rows) == 258, f"expected 258 rows, got {len(rows)}"

key = json.loads(KEY.read_text(encoding="utf-8"))
mapping = {r["code"]: r["condition"] for r in key["mapping"]}
assert len(mapping) == 180

for r in rows:
    assert r["code"] in mapping, f"code {r['code']} not in key"
    r["condition"] = mapping[r["code"]]


def share(rs, cf):
    n = len(rs)
    if n == 0:
        return None, 0
    c = sum(1 for r in rs if r["counterfactual"] == cf)
    return round(100 * c / n, 1), c


def crosstab(cond=None):
    rs = rows if cond is None else [r for r in rows if r["condition"] == cond]
    out = {
        "n": len(rs),
        "tri_split": dict(Counter(r["label"] for r in rs)),
        "h1_should_be_E2": share(rs, "应-E2"),
        "h2_still_E3": share(rs, "仍-E3"),
    }
    return out


result = {
    "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "key": KEY.name,
    "note": "key-join only over frozen blind attribution rows; no re-judging; 解读层",
    "all": crosstab(None),
    "arm_A": crosstab("A"),
    "arm_B": crosstab("B"),
}

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
