#!/usr/bin/env bash
# Tail logs for a dev stack service.
#
# Usage:
#   dev/logs.sh             # web (default)
#   dev/logs.sh worker
#   dev/logs.sh beat
#   dev/logs.sh db
#   dev/logs.sh redis

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

cd "$(git rev-parse --show-toplevel)"

require_engine

ensure_web_running

SERVICE="${1:-web}"
dc logs -f "$SERVICE"
