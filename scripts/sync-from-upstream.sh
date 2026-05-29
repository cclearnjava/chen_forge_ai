#!/bin/bash
# sync-from-upstream.sh — Sync hook files from Towow (upstream) to wow-harness.
#
# Purpose: Towow is the development/incubation repo where hooks are written
# and tested. This script copies updated hooks to wow-harness and reports
# any discrepancies in settings.json hook registrations.
#
# What it does:
#   1. Copy shared hook scripts from Towow → wow-harness (skip Towow-only files)
#   2. Replace find-towow-root.sh references → find-project-root.sh in copied files
#   3. Compare settings.json hook registrations and report differences
#   4. Sync shared scripts (guard-feedback.py, deploy-guard.py, context_router.py, guard_router.py)
#   5. Sync context-fragments/ directory
#
# Usage:
#   ./scripts/sync-from-upstream.sh                     # default Towow path
#   ./scripts/sync-from-upstream.sh /path/to/Towow      # explicit upstream path
#   ./scripts/sync-from-upstream.sh --dry-run            # show what would change

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HARNESS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
UPSTREAM_DEFAULT="$(cd "$HARNESS_ROOT/../Towow" 2>/dev/null && pwd || echo "")"

# Parse args
DRY_RUN=false
UPSTREAM=""

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        *) UPSTREAM="$arg" ;;
    esac
done

if [ -z "$UPSTREAM" ]; then
    UPSTREAM="$UPSTREAM_DEFAULT"
fi

if [ -z "$UPSTREAM" ] || [ ! -d "$UPSTREAM/scripts/hooks" ]; then
    echo "ERROR: Cannot find upstream Towow repo."
    echo "Usage: $0 [--dry-run] [/path/to/Towow]"
    exit 1
fi

echo "=== wow-harness sync-from-upstream ==="
echo "Upstream: $UPSTREAM"
echo "Target:   $HARNESS_ROOT"
echo "Dry run:  $DRY_RUN"
echo ""

# ─── Files that exist only in Towow (not synced) ───
TOWOW_ONLY=(
    "find-towow-root.sh"  # Towow-specific root finder
)

# ─── Files that exist only in wow-harness (not overwritten) ───
HARNESS_ONLY=(
    "find-project-root.sh"  # Generic root finder
    "sanitize-on-read.py"   # WP-11 addition
)

# ─── Step 1: Copy shared hooks ───
echo "── Step 1: Sync hook scripts ──"
COPIED=0
SKIPPED=0
UNCHANGED=0

for src_file in "$UPSTREAM/scripts/hooks/"*; do
    filename="$(basename "$src_file")"

    # Skip Towow-only files
    skip=false
    for excl in "${TOWOW_ONLY[@]}"; do
        if [ "$filename" = "$excl" ]; then
            skip=true
            break
        fi
    done
    if $skip; then
        echo "  SKIP (Towow-only): $filename"
        ((SKIPPED++))
        continue
    fi

    # Skip harness-only files (don't overwrite)
    for excl in "${HARNESS_ONLY[@]}"; do
        if [ "$filename" = "$excl" ]; then
            skip=true
            break
        fi
    done
    if $skip; then
        echo "  SKIP (harness-only): $filename"
        ((SKIPPED++))
        continue
    fi

    dst_file="$HARNESS_ROOT/scripts/hooks/$filename"

    # Check if content differs
    if [ -f "$dst_file" ]; then
        if diff -q "$src_file" "$dst_file" > /dev/null 2>&1; then
            ((UNCHANGED++))
            continue
        fi
    fi

    if $DRY_RUN; then
        echo "  WOULD COPY: $filename"
    else
        cp "$src_file" "$dst_file"
        echo "  COPIED: $filename"
    fi
    ((COPIED++))
done

echo ""
echo "  Results: $COPIED copied, $SKIPPED skipped, $UNCHANGED unchanged"

# ─── Step 2: Replace find-towow-root.sh references ───
echo ""
echo "── Step 2: Path references ──"
PATCHED=0

for hook_file in "$HARNESS_ROOT/scripts/hooks/"*.py "$HARNESS_ROOT/scripts/hooks/"*.sh; do
    [ -f "$hook_file" ] || continue
    filename="$(basename "$hook_file")"

    # Skip harness-only files
    skip=false
    for excl in "${HARNESS_ONLY[@]}"; do
        if [ "$filename" = "$excl" ]; then
            skip=true
            break
        fi
    done
    if $skip; then continue; fi

    if grep -q "find-towow-root.sh" "$hook_file" 2>/dev/null; then
        if $DRY_RUN; then
            echo "  WOULD PATCH: $filename (find-towow-root.sh → find-project-root.sh)"
        else
            # Use perl for reliable in-place replace (macOS sed -i differs from GNU)
            perl -pi -e 's/find-towow-root\.sh/find-project-root.sh/g' "$hook_file"
            echo "  PATCHED: $filename"
        fi
        ((PATCHED++))
    fi
done

if [ "$PATCHED" -eq 0 ]; then
    echo "  No path references to patch"
fi

# ─── Step 3: Compare settings.json hook registrations ───
echo ""
echo "── Step 3: Hook registration diff ──"

# Extract hook script names from settings.json
extract_hooks() {
    python3 -c "
import json, sys
with open('$1') as f:
    d = json.load(f)
hooks = []
for stage, entries in d.get('hooks', {}).items():
    for entry in entries:
        matcher = entry.get('matcher', '*')
        for h in entry.get('hooks', []):
            cmd = h.get('command', '')
            # Extract script name
            for part in reversed(cmd.split()):
                if part.endswith(('.py', '.sh')):
                    hooks.append(f'{stage}|{matcher}|{part.split(\"/\")[-1]}')
                    break
for h in sorted(set(hooks)): print(h)
" 2>/dev/null
}

UPSTREAM_HOOKS=$(extract_hooks "$UPSTREAM/.claude/settings.json")
HARNESS_HOOKS=$(extract_hooks "$HARNESS_ROOT/.claude/settings.json")

# Find hooks only in upstream
ONLY_UPSTREAM=$(comm -23 <(echo "$UPSTREAM_HOOKS") <(echo "$HARNESS_HOOKS"))
ONLY_HARNESS=$(comm -13 <(echo "$UPSTREAM_HOOKS") <(echo "$HARNESS_HOOKS"))

if [ -n "$ONLY_UPSTREAM" ]; then
    echo "  ⚠ Only in Towow (missing from wow-harness):"
    echo "$ONLY_UPSTREAM" | while IFS='|' read -r stage matcher script; do
        echo "    $stage $matcher: $script"
    done
fi

if [ -n "$ONLY_HARNESS" ]; then
    echo "  ℹ Only in wow-harness (expected for harness-specific hooks):"
    echo "$ONLY_HARNESS" | while IFS='|' read -r stage matcher script; do
        echo "    $stage $matcher: $script"
    done
fi

if [ -z "$ONLY_UPSTREAM" ] && [ -z "$ONLY_HARNESS" ]; then
    echo "  ✓ Hook registrations in sync"
fi

# ─── Step 4: Check for other synced files ───
echo ""
echo "── Step 4: Other shared files ──"

# Scripts in scripts/ root that are shared with Towow
for shared_file in "guard-feedback.py" "deploy-guard.py" "context_router.py" "guard_router.py"; do
    src="$UPSTREAM/scripts/$shared_file"
    dst="$HARNESS_ROOT/scripts/$shared_file"
    if [ -f "$src" ] && [ -f "$dst" ]; then
        if ! diff -q "$src" "$dst" > /dev/null 2>&1; then
            if $DRY_RUN; then
                echo "  WOULD COPY: scripts/$shared_file"
            else
                cp "$src" "$dst"
                echo "  COPIED: scripts/$shared_file"
            fi
        fi
    elif [ -f "$src" ] && [ ! -f "$dst" ]; then
        echo "  ⚠ MISSING in harness: scripts/$shared_file"
    fi
done

# ─── Step 5: Sync context-fragments/ directory ───
echo ""
echo "── Step 5: Context fragments ──"
FRAG_COPIED=0
FRAG_UNCHANGED=0

src_frag_dir="$UPSTREAM/scripts/context-fragments"
dst_frag_dir="$HARNESS_ROOT/scripts/context-fragments"

if [ -d "$src_frag_dir" ]; then
    if [ ! -d "$dst_frag_dir" ]; then
        if $DRY_RUN; then
            echo "  WOULD CREATE: scripts/context-fragments/"
        else
            mkdir -p "$dst_frag_dir"
            echo "  CREATED: scripts/context-fragments/"
        fi
    fi

    for src_frag in "$src_frag_dir/"*; do
        [ -f "$src_frag" ] || continue
        frag_name="$(basename "$src_frag")"
        dst_frag="$dst_frag_dir/$frag_name"

        if [ -f "$dst_frag" ]; then
            if diff -q "$src_frag" "$dst_frag" > /dev/null 2>&1; then
                ((FRAG_UNCHANGED++))
                continue
            fi
        fi

        if $DRY_RUN; then
            echo "  WOULD COPY: context-fragments/$frag_name"
        else
            cp "$src_frag" "$dst_frag"
            echo "  COPIED: context-fragments/$frag_name"
        fi
        ((FRAG_COPIED++))
    done

    echo "  Results: $FRAG_COPIED copied, $FRAG_UNCHANGED unchanged"
else
    echo "  ⚠ Upstream context-fragments/ not found"
fi

echo ""
echo "=== Sync complete ==="
