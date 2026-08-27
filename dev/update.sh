#!/usr/bin/env bash
# Pull the latest changes and update the dev environment.
# Rebuilds the Docker image if requirements.txt changed, then runs migrations.
#
# Usage:
#   dev/update.sh

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

cd "$(git rev-parse --show-toplevel)"

require_engine

# Ensure containers are running
if ! dc ps -q --status running web 2>/dev/null | grep -q .; then
    echo "Containers not running - starting dev stack..."
    "$FF_DEV_DIR/start.sh"
    exit $?
fi

# Track whether any lockfile changes after the pull
LOCKFILE_BEFORE=$(git rev-parse HEAD:requirements.txt HEAD:requirements-dev.txt HEAD:requirements-ci.txt 2>/dev/null)

echo "Pulling latest changes..."
git pull --ff-only

LOCKFILE_AFTER=$(git rev-parse HEAD:requirements.txt HEAD:requirements-dev.txt HEAD:requirements-ci.txt 2>/dev/null)

if [[ "$LOCKFILE_BEFORE" != "$LOCKFILE_AFTER" ]]; then
    echo ""
    echo "Requirements changed - rebuilding image..."
    dc build web
    dc up -d web
fi

echo ""
echo "Running migrations..."
dev/migrate.sh
