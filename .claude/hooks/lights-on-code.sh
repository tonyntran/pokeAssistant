#!/usr/bin/env bash
# PreToolUse hook for Edit/Write — TDD enforcement via questions
# Asks "is there a failing test?" before production code is written

set -euo pipefail

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty')

# Only check code files, not config/docs
case "$FILE_PATH" in
  *.py|*.ts|*.tsx|*.js|*.jsx|*.go|*.rs|*.kt|*.java|*.rb)
    ;;
  *)
    exit 0
    ;;
esac

# Skip test files themselves
case "$FILE_PATH" in
  *test*|*spec*|*__tests__*)
    exit 0
    ;;
esac

# Ask the question — don't give a directive
jq -n '{
  additionalContext: "Before writing this production code: Is there a failing test that requires this change? If not, should you write one first?"
}'

exit 0
