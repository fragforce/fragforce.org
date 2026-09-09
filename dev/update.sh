#!/usr/bin/env bash
# Pull the latest changes and update the dev environment.
# Rebuilds the Docker image if requirements.txt changed, then runs migrations.
#
# Usage:
#   dev/update.sh

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

cd "$(git rev-parse --show-toplevel)"

require_engine

ensure_web_running

# Track whether any lockfile changes after the pull
LOCKFILE_BEFORE=$(git rev-parse HEAD:uv.lock 2>/dev/null)

echo "Pulling latest changes..."
git pull --ff-only

LOCKFILE_AFTER=$(git rev-parse HEAD:uv.lock 2>/dev/null)

if [[ "$LOCKFILE_BEFORE" != "$LOCKFILE_AFTER" ]]; then
    echo ""
    echo "Requirements changed - rebuilding image..."
    dc build web init
    dc up -d web
fi

echo ""
echo "Running migrations..."
"$FF_DEV_DIR/migrate.sh"
