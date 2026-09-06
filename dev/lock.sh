#!/usr/bin/env bash
# Run uv sync to update the uv.lock file according to current constraints in pyproject.toml
#
# Usage:
#   dev/lock.sh             # run a fresh uv sync to update the uv.lock file

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

cd "$(git rev-parse --show-toplevel)"

require_engine

echo "updating uv lockfile"
dc run compile uv lock
