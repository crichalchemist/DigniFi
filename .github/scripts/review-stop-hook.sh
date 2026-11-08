#!/usr/bin/env bash
# Stop hook for the PR review (claude-code-review.yml). In headless mode any reply with no tool
# call ends the session. The reviews of #34 and #35 ended on their own partway through, with no
# error and nothing posted; a rerun of #34's change read every file, so the stop comes and goes.
# While no "## Claude review" comment by github-actions[bot] has been posted or edited since the
# review started, this sends the review back to work, at most three times; the workflow's
# fallback step still covers a review that stops a fourth time.
set -u
# Every run counts itself, so the workflow can show the hook was loaded even when it never blocks.
checks_file="${RUNNER_TEMP:?}/review-stop-checks"
echo $(($(cat "$checks_file" 2>/dev/null || echo 0) + 1)) > "$checks_file"
blocks_file="${RUNNER_TEMP:?}/review-stop-blocks"
blocks=$(cat "$blocks_file" 2>/dev/null || echo 0)
# TEMPORARY, test branch only: block the first stop whatever was posted, to prove in CI that a
# block from this hook keeps the run going.
if [ ! -f "$RUNNER_TEMP/review-forced-block" ]; then
  touch "$RUNNER_TEMP/review-forced-block"
  echo $((blocks + 1)) > "$blocks_file"
  jq -n '{decision: "block", reason: "This is a test of the review workflow. Before you stop, run `git diff --stat HEAD^1 HEAD` once more, then end your reply."}'
  exit 0
fi
if [ "$blocks" -ge 3 ]; then
  exit 0
fi
pr=$(jq -r '.pull_request.number' "${GITHUB_EVENT_PATH:?}")
posted=$(gh api --paginate "repos/${GITHUB_REPOSITORY:?}/issues/$pr/comments" \
  --jq '.[] | select((.body | startswith("## Claude review")) and .user.login == "github-actions[bot]" and .updated_at >= env.REVIEW_STARTED_AT) | .id' 2>/dev/null)
if [ -n "${REVIEW_STARTED_AT:-}" ] && [ -n "$posted" ]; then
  exit 0
fi
echo $((blocks + 1)) > "$blocks_file"
jq -n --arg reason "You haven't posted the review's summary, so don't stop yet. If any changed file is still unread, review it next: \`git diff --stat HEAD^1 HEAD\` lists them and \`git diff HEAD^1 HEAD -- <path>\` shows one. Then write the summary to review-summary.md and post it as your instructions say. If you can't finish, post it now: list what you found and name every file you didn't reach." \
  '{decision: "block", reason: $reason}'
