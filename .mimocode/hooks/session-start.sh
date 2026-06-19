#!/bin/bash
# session-start.sh — Inject .remember/ state into session context
#
# Reads now.md, today's log, recent.md, and archive.md.
# Also runs daily rollover if the date has changed.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
REMEMBER_DIR="$PROJECT_DIR/.remember"
TODAY=$(date '+%Y-%m-%d')

# --- Daily rollover check ---
YESTERDAY=$(date -v-1d '+%Y-%m-%d' 2>/dev/null || date -d "yesterday" '+%Y-%m-%d' 2>/dev/null)
STALE_FILE="$REMEMBER_DIR/today-${YESTERDAY}.md"
if [ -f "$STALE_FILE" ]; then
    DONE_FILE="$REMEMBER_DIR/today-${YESTERDAY}.done.md"
    if [ ! -f "$DONE_FILE" ]; then
        mv "$STAGING_FILE" "$DONE_FILE" 2>/dev/null || mv "$STALE_FILE" "$DONE_FILE"
        # Append one-liner to archive
        ENTRIES=$(grep -c '^## ' "$DONE_FILE" 2>/dev/null || echo 0)
        echo "| ${YESTERDAY} | ${ENTRIES} entries |" >> "$REMEMBER_DIR/archive.md"
    fi
fi

# --- Ensure today's file exists ---
TODAY_FILE="$REMEMBER_DIR/today-${TODAY}.md"
[ -f "$TODAY_FILE" ] || touch "$TODAY_FILE"

# --- Inject into context ---
echo "=== REMEMBER ==="

for LABEL in now today recent archive; do
    case "$LABEL" in
        now)     FILE="$REMEMBER_DIR/now.md" ;;
        today)   FILE="$TODAY_FILE" ;;
        recent)  FILE="$REMEMBER_DIR/recent.md" ;;
        archive) FILE="$REMEMBER_DIR/archive.md" ;;
    esac
    if [ -f "$FILE" ] && [ -s "$FILE" ]; then
        echo "--- $LABEL ---"
        cat "$FILE"
        echo ""
    fi
done

echo "=== END REMEMBER ==="
