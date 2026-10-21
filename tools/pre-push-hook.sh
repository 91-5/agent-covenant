#!/bin/sh
# pre-push-hook.sh — git pre-push hook: run lint + gate before allowing push.
#
# Installed by tools/install-hooks.sh.  Reads git's pre-push stdin:
#   <local ref> <local sha> <remote ref> <remote sha>   (one line per ref)
#
# Blocks the push if:
#   - lint_cards.py --strict returns non-zero, OR
#   - gate.py --require <newest_round_id> returns non-zero, OR
#   - gate.py --check-all-links returns non-zero (a link's verdict_sha256,
#     timing or manifest no longer matches the files on disk)
#
# The newest round id is the last non-underscore key in artifacts.json.
# This matches the CI scope in .github/workflows/gate.yml.
#
# Escape hatch: git push --no-verify  (recorded in shell history).
# Skip only the link sweep: DEEPFREEZE_SKIP_LINK_CHECK=1 git push  (lint and
# gate still run -- use it when the link is a known work-in-progress, never to
# ship a verdict whose link you have not refreshed).

set -eu

# --- locate repo root ---
# Use git to find the repo root, not the script location.  When the hook is
# installed via core.hooksPath the script may live outside the working tree,
# and when tests invoke it from a tempdir the script location is irrelevant.
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$REPO_ROOT" ]; then
    echo "[pre-push] ERROR: not inside a git work tree" >&2
    exit 2
fi
cd "$REPO_ROOT"

# --- find a usable python ---
# `command -v` only proves a name resolves, not that the name runs. On Windows
# Git Bash, `python3` resolves to the Microsoft Store stub in
# %LOCALAPPDATA%\Microsoft\WindowsApps\python3, which exists, exits non-zero, and
# prints nothing. Preferring it on name alone made this hook die with that
# stub's exit code and no diagnostics. Probe each candidate instead.
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c '' >/dev/null 2>&1; then
        PYTHON=$candidate
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "[pre-push] ERROR: no usable python interpreter (tried: python3, python)" >&2
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
# --evo-dir: EVO cards live outside the repo (_handoffs/evo) — passing the dir
# lets the orphan check pair EVO verdicts with their cards instead of warning
# forever. Absent dir → the is_dir() guard skips it, zero cost (XJ-20261021-002).
#
# EVO_PROTECTED_ASSET_TOUCHED exemption (sir ruling 2026-10-21, option (a) of
# XJ-20261021-002 C1): that WARN is the by-design audit record of the EVO
# legitimate-escalation channel — it only fires when protected_assets_changes
# AND sir_approval are BOTH present (the un-backed variant is an ERROR, which
# still blocks below). Under --strict it would otherwise block every push
# while an EVO targeted card is the current round. ERRORs and every other
# WARN still block: the exemption is exactly one rule code, nothing else.
LINT_OUT=$("$PYTHON" tools/lint_cards.py --dir .tasks --verdict-dir verdicts --artifact-map artifacts.json --evo-dir ../_handoffs/evo --strict 2>&1) && LINT_CODE=0 || LINT_CODE=$?
NON_EXEMPT=$(printf '%s\n' "$LINT_OUT" | grep -E '^\[(ERROR|WARN)\]' | grep -vE '^\[WARN\] EVO_PROTECTED_ASSET_TOUCHED' || true)
if [ "$LINT_CODE" -eq 2 ]; then
    printf '%s\n' "$LINT_OUT"
    echo "[pre-push] BLOCKED: lint usage error (exit 2 is not a pass)." >&2
    exit 1
fi
if [ "$LINT_CODE" -ne 0 ] && [ -n "$NON_EXEMPT" ]; then
    printf '%s\n' "$LINT_OUT"
    echo "[pre-push] BLOCKED: lint findings (see above). Fix them or use --no-verify to bypass." >&2
    exit 1
fi
printf '%s\n' "$LINT_OUT"
if [ "$LINT_CODE" -ne 0 ]; then
    echo "[pre-push] lint: only the EVO escalation-channel WARN present - exempted (XJ-20261021-002 C1, sir ruling (a)), continuing"
fi

# --- step 2: gate --require newest round ---
if ! "$PYTHON" tools/gate.py --verdict-dir verdicts --artifact-map artifacts.json --require "$NEWEST_ID"; then
    echo "[pre-push] BLOCKED: gate violations for round $NEWEST_ID (see above)." >&2
    exit 1
fi

# --- step 3: link sweep (verdict sha / timing / manifest) ---
# Step 2 only re-reads links for the ids it gates, i.e. the newest round. A
# verdict that was re-signed after its link was written leaves a stale
# verdict_sha256 on an *older* round, and nothing would notice until that round
# is gated again -- in practice, never. This sweep runs the same check_links()
# over every link that bound a verdict, so the fix (re-run link_card.py) happens
# before the push instead of after a reviewer finds the trace inconsistent.
#
# The logic stays in gate.py on purpose: one implementation, two entry points.
# A shell copy would be a second rule that can drift from the one CI enforces.
case "${DEEPFREEZE_SKIP_LINK_CHECK:-0}" in
    1|true|yes|TRUE|YES)
        echo "[pre-push] SKIP link sweep (DEEPFREEZE_SKIP_LINK_CHECK=$DEEPFREEZE_SKIP_LINK_CHECK)"
        ;;
    *)
        if [ ! -d "${LINK_DIR:-.freeze}" ]; then
            echo "[pre-push] no ${LINK_DIR:-.freeze} directory - link sweep skipped"
        elif ! "$PYTHON" tools/gate.py --check-all-links --link-dir "${LINK_DIR:-.freeze}" --verdict-dir verdicts; then
            echo "[pre-push] BLOCKED: link trace violations (see above)." >&2
            echo "[pre-push] fix: python tools/link_card.py --card <id> --verdict verdicts/<id>.verdict.json" >&2
            echo "[pre-push]      (or DEEPFREEZE_SKIP_LINK_CHECK=1 git push to skip only this step)" >&2
            exit 1
        fi
        ;;
esac

echo "[pre-push] OK — lint, gate and link sweep passed."
exit 0
