#!/usr/bin/env bash
# PreToolUse hook for Bash — hard-block irreversible destructive commands
# Exits with code 2 to block execution

set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Force push to main/master
if echo "$COMMAND" | grep -qE 'git\s+push\s+.*--force.*\s+(main|master)'; then
  echo "BLOCKED: Force push to main/master is not allowed." >&2
  exit 2
fi

# Skip git hooks
if echo "$COMMAND" | grep -qE '--no-verify'; then
  echo "BLOCKED: Bypassing git hooks with --no-verify is not allowed." >&2
  exit 2
fi

# Dangerous rm commands
if echo "$COMMAND" | grep -qE 'rm\s+(-rf|-fr)\s+(/|~|\$HOME|\.\.)'; then
  echo "BLOCKED: Dangerous rm command targeting root, home, or parent directories." >&2
  exit 2
fi

exit 0
