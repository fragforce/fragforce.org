#!/usr/bin/env bash
# Run the full test suite (or a subset) via Docker and format output as a GitHub comment.
#
# Usage:
#   dev/runtests.sh               # run all tests (reuses existing test DB)
#   dev/runtests.sh ffdonations   # run a single app
#   dev/runtests.sh ffdonations.tests.SomeTestClass.test_method
#   dev/runtests.sh --fresh       # drop and recreate the test DB first, then run all tests
#   dev/runtests.sh --fresh ffdonations  # drop and recreate, then run a single app

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

cd "$(git rev-parse --show-toplevel)"

require_engine

ensure_web_running

COMMIT=$(git rev-parse --short HEAD)
DATE=$(date +%Y-%m-%d)
FENCE='```'

# Handle --fresh flag
KEEPDB="--keepdb"
if [[ "${1:-}" == "--fresh" ]]; then
    shift
    KEEPDB=""
fi

# Run tests, capturing all output (Django test runner writes to stderr)
OUTPUT=$(dc exec -T web uv run --frozen python manage.py test $KEEPDB "$@" 2>&1)
EXIT_CODE=$?

# Extract summary lines
SUMMARY=$(echo "$OUTPUT" | grep -E '^(Ran [0-9]+ test|OK$|FAILED \()')
RAN_LINE=$(echo "$SUMMARY" | grep '^Ran ')
STATUS_LINE=$(echo "$SUMMARY" | grep -E '^(OK|FAILED)')

# Extract failure details if any
if [[ $EXIT_CODE -ne 0 ]]; then
    FAILURES=$(echo "$OUTPUT" | grep -E '^(FAIL|ERROR): ' | sed 's/^/- /')
fi

# Build markdown
echo "## Test Run - \`${1:-all}\` @ \`$COMMIT\`"
echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "**:white_check_mark: $RAN_LINE** - $DATE"
else
    echo "**:x: $RAN_LINE** - $DATE"
fi
echo ""
echo "$FENCE"
echo "$RAN_LINE"
echo ""
echo "$STATUS_LINE"
echo "$FENCE"

if [[ $EXIT_CODE -ne 0 && -n "$FAILURES" ]]; then
    echo ""
    echo "### Failures"
    echo "$FAILURES"
    echo ""
    echo "<details><summary>Full output</summary>"
    echo ""
    echo "$FENCE"
    echo "$OUTPUT" | grep -v '^Loading .env'
    echo "$FENCE"
    echo ""
    echo "</details>"
fi

exit $EXIT_CODE
