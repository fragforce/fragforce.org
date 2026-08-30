#!/usr/bin/env bash
# Run Django migrations inside the web container.
#
# Usage:
#   dev/migrate.sh              # run all pending migrations
#   dev/migrate.sh ffdonations  # migrate a specific app

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

cd "$(git rev-parse --show-toplevel)"

require_engine

ensure_web_running

dc exec -T web python manage.py migrate "$@"
