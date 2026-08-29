#!/usr/bin/env bash
# Open a shell inside the web container.
#
# Usage:
#   dev/shell.sh            # bash shell
#   dev/shell.sh django     # Django manage.py shell
#   dev/shell.sh db         # Django dbshell (postgres)

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

cd "$(git rev-parse --show-toplevel)"

require_engine

ensure_web_running

case "${1:-bash}" in
    django|dj)
        dc exec web uv run --frozen python manage.py shell
        ;;
    db)
        dc exec web uv run --frozen python manage.py dbshell
        ;;
    bash|"")
        dc exec web bash
        ;;
    *)
        echo "Usage: dev/shell.sh [bash|django|db]"
        exit 1
        ;;
esac
