#!/usr/bin/env bash
# Run pyflakes across the entire codebase (not just staged files).
# Useful for a full check before opening a PR.
#
# Usage:
#   dev/lint.sh             # lint all Python files
#   dev/lint.sh ffdonations # lint a specific app directory

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

cd "$(git rev-parse --show-toplevel)"

require_engine

ensure_web_running

TARGET="${1:-.}"
FILES=$(find "$TARGET" -name "*.py" | grep -v '\.git' | grep -v '\.venv' | grep -v migrations | tr '\n' ' ')

if [[ -z "$FILES" ]]; then
    echo "No Python files found in: $TARGET"
    exit 0
fi

echo "Running pyflakes on $(echo $FILES | wc -w | tr -d ' ') Python files..."
dc exec -T web uv run --frozen python -m pyflakes $FILES
