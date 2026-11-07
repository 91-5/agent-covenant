import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent.parent
data = json.loads((ROOT / "dryrun" / "round6-armsplit.json").read_text(encoding="utf-8"))

# Sanity anchors vs blind-state full-group numbers (must match: 180/69/9, 94.2/5.8)
a = data["all"]
assert a["tri_split"]["E3a-fact-unsupported"] == 180
assert a["tri_split"]["E3b-anchor-miss"] == 69
assert a["tri_split"]["E3c-not-mechanical"] == 9
assert a["h1_should_be_E2"] == [94.2, 243]
assert a["h2_still_E3"] == [5.8, 15]
assert data["arm_A"]["n"] == 129 and data["arm_B"]["n"] == 129
print("anchors OK: full-group numbers reproduce; arms balanced 129/129")

# Q6 direction-conflict check (pre-registered in card review question 6):
# conflict = H1 concentrated in one arm AND H2 concentrated in the other.
h1a, h1b = data["arm_A"]["h1_should_be_E2"][0], data["arm_B"]["h1_should_be_E2"][0]
h2a, h2b = data["arm_A"]["h2_still_E3"][0], data["arm_B"]["h2_still_E3"][0]
conflict = (h1a > 50 < h1b) and (h2a > 50 or h2b > 50) and (h1a > 50) != (h2a > 50)
print(f"H1: A={h1a}% B={h1b}% | H2: A={h2a}% B={h2b}%")
print("direction conflict (Q6 precondition):", conflict)
