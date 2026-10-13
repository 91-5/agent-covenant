#!/bin/sh
# install-hooks.sh — install the pre-push hook into .git/hooks/ or core.hooksPath
#
# Usage:  bash tools/install-hooks.sh
# Idempotent: re-running is safe; backs up existing non-identical hooks.
#
# Behavior:
#   1. Locate the hooks directory (core.hooksPath if set, else .git/hooks).
#   2. If .hooks/pre-push already exists and is identical to our hook, no-op.
#   3. If .hooks/pre-existing (non-identical), back it up as pre-push.bak.<timestamp>.
#   4. Copy pre-push-hook.sh → hooks/pre-push, chmod +x.

set -eu

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
HOOK_SRC="$SCRIPT_DIR/pre-push-hook.sh"

# --- find hooks dir ---
HOOKS_DIR=$(git -C "$REPO_ROOT" config --get core.hooksPath || true)
if [ -z "$HOOKS_DIR" ]; then
    HOOKS_DIR="$REPO_ROOT/.git/hooks"
fi
# Resolve relative hooksPath against repo root
case "$HOOKS_DIR" in
    /*) ;;  # absolute
    *)  HOOKS_DIR="$REPO_ROOT/$HOOKS_DIR" ;;
esac

mkdir -p "$HOOKS_DIR"

HOOK_DST="$HOOKS_DIR/pre-push"

# --- idempotent check ---
if [ -f "$HOOK_DST" ]; then
    if diff -q "$HOOK_SRC" "$HOOK_DST" >/dev/null 2>&1; then
        echo "[install-hooks] pre-push hook already up-to-date — nothing to do."
        exit 0
    fi
    # Different content: back up
    BACKUP="$HOOK_DST.bak.$(date +%Y%m%d%H%M%S)"
    cp "$HOOK_DST" "$BACKUP"
    echo "[install-hooks] Backed up existing pre-push hook to $BACKUP"
fi

cp "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_DST"
echo "[install-hooks] Installed pre-push hook to $HOOK_DST"
