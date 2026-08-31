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

echo "updating uv lockfile"
dc run compile uv lock
