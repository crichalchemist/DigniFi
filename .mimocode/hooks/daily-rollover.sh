#!/bin/bash
# daily-rollover.sh — Rename yesterday's log to .done.md, update archive + recent
#
# Safe to run multiple times (idempotent).

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
REMEMBER_DIR="$PROJECT_DIR/.remember"

YESTERDAY=$(date -v-1d '+%Y-%m-%d' 2>/dev/null || date -d "yesterday" '+%Y-%m-%d' 2>/dev/null)
STAGING="$REMEMBER_DIR/today-${YESTERDAY}.md"
DONE="$REMEMBER_DIR/today-${YESTERDAY}.done.md"

if [ ! -f "$STAGING" ]; then
    echo "No staging file for ${YESTERDAY}, nothing to roll."
    exit 0
fi

if [ -f "$DONE" ]; then
    echo "Already rolled: ${YESTERDAY}"
    exit 0
fi

mv "$STAGING" "$DONE"

# Append one-liner to archive
ENTRIES=$(grep -c '^## ' "$DONE" 2>/dev/null || echo 0)
echo "| ${YESTERDAY} | ${ENTRIES} entries |" >> "$REMEMBER_DIR/archive.md"

# Update recent.md: keep last 7 days of .done.md content
RECENT="$REMEMBER_DIR/recent.md"
{
    echo "# Recent"
    echo ""
    for f in $(ls -t "$REMEMBER_DIR"/today-*.done.md 2>/dev/null | head -7); do
        DATE=$(basename "$f" .done.md | sed 's/today-//')
        echo "## ${DATE}"
        # Include first entry or summary line
        grep '^## ' "$f" | head -3 | sed 's/^## /  /'
        echo ""
    done
} > "$RECENT"

echo "Rolled ${YESTERDAY} → .done.md (${ENTRIES} entries)"
