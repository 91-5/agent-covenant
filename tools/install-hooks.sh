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
#
# Target repository: the work tree this is *run from*, resolved with
# `git rev-parse --show-toplevel` on $PWD — deliberately NOT derived from the
# installer's own location. This installer can legitimately live outside the repo
# it installs into: the test suite runs it with $PWD set to a throwaway repo, and
# a maintainer may invoke it by absolute path. Resolving from $SCRIPT_DIR instead
# would silently write into the installer's own repository, which is how an early
# version of this script came to litter the real .git/hooks/ with three files and
# two .bak copies during a test run.

set -eu

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
HOOK_SRC="$SCRIPT_DIR/pre-push-hook.sh"

if [ ! -f "$HOOK_SRC" ]; then
    echo "[install-hooks] ERROR: pre-push-hook.sh not found next to this installer" >&2
    exit 2
fi

# --- target repo: the work tree we are standing in ---
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$REPO_ROOT" ]; then
    echo "[install-hooks] ERROR: not inside a git work tree; cd into the target repo first" >&2
    exit 2
fi

# --- find hooks dir ---
HOOKS_PATH_CFG=$(git -C "$REPO_ROOT" config --get core.hooksPath || true)
if [ -z "$HOOKS_PATH_CFG" ]; then
    HOOKS_DIR="$REPO_ROOT/.git/hooks"
else
    # A relative core.hooksPath resolves against the work tree root. Absolute
    # means POSIX-absolute or a Windows drive path -- matching only on a leading
    # slash would re-prefix "C:/repo/.githooks" onto the repo root and produce
    # "C:/repo/C:/repo/.githooks".
    case "$HOOKS_PATH_CFG" in
        /*|[A-Za-z]:[/\\]*) HOOKS_DIR="$HOOKS_PATH_CFG" ;;
        *)                  HOOKS_DIR="$REPO_ROOT/$HOOKS_PATH_CFG" ;;
    esac
fi

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
