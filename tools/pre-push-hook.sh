#!/bin/sh
# pre-push-hook.sh — git pre-push hook: run lint + gate before allowing push.
#
# Installed by tools/install-hooks.sh.  Reads git's pre-push stdin:
#   <local ref> <local sha> <remote ref> <remote sha>   (one line per ref)
#
# Blocks the push if:
#   - lint_cards.py --strict returns non-zero, OR
#   - gate.py --require <newest_round_id> returns non-zero
#
# The newest round id is the last non-underscore key in artifacts.json.
# This matches the CI scope in .github/workflows/gate.yml.
#
# Escape hatch: git push --no-verify  (recorded in shell history).

set -eu

# --- locate repo root ---
# Use git to find the repo root, not the script location.  When the hook is
# installed via core.hooksPath the script may live outside the working tree,
# and when tests invoke it from a tempdir the script location is irrelevant.
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
    echo "[pre-push] ERROR: not inside a git work tree" >&2
    exit 2
fi
cd "$REPO_ROOT"

# --- find python ---
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    echo "[pre-push] ERROR: python3 or python not found in PATH" >&2
    exit 2
fi

# --- parse stdin: only branch pushes (skip tags, deletes) ---
# Read stdin directly in the loop; no intermediate variable needed.
# Use process substitution to avoid subshell variable scoping issues.
PUSH_BRANCH=0
while IFS= read -r line; do
    [ -z "$line" ] && continue
    LOCAL_REF=$(echo "$line" | awk '{print $1}')
    LOCAL_SHA=$(echo "$line" | awk '{print $2}')

    # Skip tag pushes
    case "$LOCAL_REF" in refs/tags/*) continue ;; esac

    # Skip delete (all-zero local sha)
    case "$LOCAL_SHA" in 0000000000000000000000000000000000000000) continue ;; esac

    PUSH_BRANCH=1
done

if [ "$PUSH_BRANCH" -eq 0 ]; then
    # Only tags or deletes, or empty stdin — no gate needed
    exit 0
fi

# --- get newest round id from artifacts.json ---
if [ ! -f artifacts.json ]; then
    echo "[pre-push] ERROR: artifacts.json not found in repo root" >&2
    exit 2
fi

NEWEST_ID=$("$PYTHON" -c "
import json, sys
with open('artifacts.json', encoding='utf-8') as f:
    m = json.load(f)
ids = [k for k in m if not k.startswith('_')]
if not ids:
    print('', end='')
else:
    print(ids[-1], end='')
")

if [ -z "$NEWEST_ID" ]; then
    echo "[pre-push] WARNING: no round ids found in artifacts.json — skipping gate"
    exit 0
fi

echo "[pre-push] Linting cards and gating round $NEWEST_ID ..."

# --- step 1: lint --strict ---
if ! "$PYTHON" tools/lint_cards.py --dir .tasks --verdict-dir verdicts --artifact-map artifacts.json --strict; then
    echo "[pre-push] BLOCKED: lint errors (see above). Fix them or use --no-verify to bypass." >&2
    exit 1
fi

# --- step 2: gate --require newest round ---
if ! "$PYTHON" tools/gate.py --verdict-dir verdicts --artifact-map artifacts.json --require "$NEWEST_ID"; then
    echo "[pre-push] BLOCKED: gate violations for round $NEWEST_ID (see above)." >&2
    exit 1
fi

echo "[pre-push] OK — lint and gate passed."
exit 0
