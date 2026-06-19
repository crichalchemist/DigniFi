#!/bin/bash
# post-save.sh — Append an entry to today's .remember/ log
#
# Usage: post-save.sh "branch-name" "Description of what was done"
#
# Appends to .remember/today-YYYY-MM-DD.md in the standard format:
#   ## HH:MM | branch-name
#   Description...

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
REMEMBER_DIR="$PROJECT_DIR/.remember"
TODAY=$(date '+%Y-%m-%d')
TODAY_FILE="$REMEMBER_DIR/today-${TODAY}.md"

BRANCH="${1:?Usage: post-save.sh <branch> <description>}"
DESCRIPTION="${2:?Usage: post-save.sh <branch> <description>}"
TIMESTAMP=$(date '+%H:%M')

[ -f "$TODAY_FILE" ] || touch "$TODAY_FILE"

{
    echo ""
    echo "## ${TIMESTAMP} | ${BRANCH}"
    echo "${DESCRIPTION}"
} >> "$TODAY_FILE"
