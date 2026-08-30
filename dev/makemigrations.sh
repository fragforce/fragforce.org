#!/usr/bin/env bash
# Create new Django migrations inside the web container.
#
# Usage:
#   dev/makemigrations.sh              # detect changes across all apps
#   dev/makemigrations.sh ffdonations  # create migrations for a specific app

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

cd "$(git rev-parse --show-toplevel)"

require_engine

ensure_web_running

dc exec -T web python manage.py makemigrations "$@"
