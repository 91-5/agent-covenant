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
#
# Probe step 2 (XJ-20261021-002 followup, sir-reported): even a runnable
# interpreter can fail to IMPORT THIS REPO's test suite — a D:\python\python
# (3.14) collected only 275 tests with 2 failures + 3 errors (test module
# import errors), which makes lint's TEST_COUNT discovery raise and blocks
# every push with TEST_COUNT_UNVERIFIED. So a candidate that CAN import the
# suite is preferred (it keeps TEST_COUNT live).
#
# But the import is a PREFERENCE, not a hard requirement (regression lesson,
# same card): hook test fixtures and other repos have no tests/ directory, so
# a hard import gate made every nested hook call exit 2 (12 test failures).
# Fall back to the last runnable candidate instead — in a tests-less repo,
# lint's TEST_COUNT silently skips (its documented "off, not passing" state
# only matters where a suite exists).
# The import needs bash: tests/test_pre_push_hook.py resolves Git bash at
# module level, and a python spawned as a Git-bash child cannot see git via
# shutil.which (Windows PATH entries arrive POSIX-style). This bash knows its
# own path reliably — export it as the hint before probing (XJ-20261021-002).
if command -v cygpath >/dev/null 2>&1 && [ -n "${BASH:-}" ]; then
    COVENANT_BASH_HINT=$(cygpath -w "$BASH" 2>/dev/null) && export COVENANT_BASH_HINT
fi
PYTHON=""
for candidate in python3 python; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    "$candidate" -c '' >/dev/null 2>&1 || continue
    PYTHON=$candidate
    if "$candidate" -c "import unittest, sys; sys.path.insert(0, '.'); import tests.test_pre_push_hook" >/dev/null 2>&1; then
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "[pre-push] ERROR: no python interpreter that can run (tried: python3, python)" >&2
    echo "[pre-push]        hint: run 'python -m unittest discover -s tests' with the interpreter you trust, fix its env, or use --no-verify" >&2
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
# --allow-orphan-id (XJ-20261021-003, dp 大脑裁定): the two in-repo EVO verdicts
# whose cards live in _handoffs/evo are topology-accepted orphans — downgraded
# to NOTICE, still printed. Any NEW orphan id still warns and fails strict.
# (EVO_PROTECTED_ASSET_TOUCHED exemption unchanged: sir ruling (a), C1.)
LINT_OUT=$("$PYTHON" tools/lint_cards.py --dir .tasks --verdict-dir verdicts --artifact-map artifacts.json --evo-dir ../_handoffs/evo --allow-orphan-id EVO-20261019-001 --allow-orphan-id EVO-20261020-001 --strict 2>&1) && LINT_CODE=0 || LINT_CODE=$?
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
# Phase 4b (XJ-20261021-004, dp 大脑 conservative ruling): on gate FAIL, emit a
# structured disposition block — the violations (already printed by gate) plus
# a rollback GUIDE built from .freeze/state.json, IF deepfreeze is managing this
# tree. The guide is TEXT ONLY: per the phase-4 ruling, the hook never executes
# a restore itself — FAIL may be a stale verdict or an environment issue, and an
# automatic /MIR would delete uncommitted work irreversibly. The human decides.
if ! "$PYTHON" tools/gate.py --verdict-dir verdicts --artifact-map artifacts.json --require "$NEWEST_ID"; then
    echo "[pre-push] BLOCKED: gate violations for round $NEWEST_ID (see above)." >&2
    # --- disposition guidance (text only, never executed) ---
    echo "[pre-push] ---- gate FAIL disposition ----" >&2
    echo "[pre-push] common causes: verdict missing/stale/CONDITIONAL; artifact mtime outran the verdict ts (re-sign or re-review); link sha mismatch (re-run link_card.py)" >&2
    if [ -f ".freeze/state.json" ]; then
        SNAP_TS=$(python -c "import json,sys; d=json.load(open('.freeze/state.json')); print(d.get('latest_snapshot',''))" 2>/dev/null)
        if [ -n "$SNAP_TS" ]; then
            echo "[pre-push] rollback guide (MANUAL - the hook will NOT run this):" >&2
            echo "[pre-push]   deepfreeze.ps1 restore -Source \"\$PWD\" -Snapshot $SNAP_TS -AutoConfirm" >&2
            echo "[pre-push]   (quarantine preserves post-snapshot new files; verify the FAIL is real before rolling back)" >&2
        fi
    else
        echo "[pre-push] (no deepfreeze state in this tree - no snapshot rollback available)" >&2
    fi
    echo "[pre-push] --------------------------------" >&2
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
