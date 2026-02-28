#!/usr/bin/env bash
# PostToolUse hook for Edit/Write — scope validation after code changes
# Asks if unnecessary code was written

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty')

# Only check code files
case "$FILE_PATH" in
  *.py|*.ts|*.tsx|*.js|*.jsx|*.go|*.rs|*.kt|*.java|*.rb)
    ;;
  *)
    exit 0
    ;;
esac

# Different questions for test vs production code
case "$FILE_PATH" in
  *test*|*spec*|*__tests__*)
    jq -n '{
      additionalContext: "You just edited a test file. Does this test assert exactly one behavior? Is it the simplest test that could fail next?"
    }'
    ;;
  *)
    jq -n '{
      additionalContext: "You just edited production code. Did you write only the minimum code needed to pass the failing test? Is there any code here that is not yet required by a test?"
    }'
    ;;
esac

exit 0
