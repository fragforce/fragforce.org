#!/usr/bin/env bash
# Start the full dev stack.
# On first run (no built image), builds containers and runs first-time setup.
# On subsequent runs, just starts containers and waits for readiness.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

cd "$(git rev-parse --show-toplevel)"

if [[ ! -f .env ]]; then
    echo "Error: .env file not found."
    echo "Run: cp env.sample .env"
    exit 1
fi

require_engine

FIRST_RUN=false
if ! engine image inspect fragforceorg-web &>/dev/null; then
    FIRST_RUN=true
fi

if [[ "$FIRST_RUN" = true ]]; then
    echo "First run detected — building containers (this will take a few minutes)..."
    dc up --build -d
    echo ""
    echo "Waiting for migrations to finish..."
    dc wait init
    echo ""
    echo "Running collectstatic..."
    dc exec -T web uv run --frozen python manage.py collectstatic --no-input
else
    dc up -d
fi

#echo ""
#echo "Installing dev dependencies (pyflakes, etc.)..."
#dc exec -T web pip install --quiet --require-hashes --only-binary :all: --no-binary django-redis-cache,django-memoize -r requirements-dev.txt

echo ""
echo "Waiting for web server at http://localhost:8000/ ..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/ >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

echo ""
echo "Dev server ready: http://localhost:8000/"
echo ""
dc ps
