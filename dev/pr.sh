#!/usr/bin/env bash
# Run the test suite, push the current branch, and open a PR with test results in the body.
#
# Usage:
#   dev/pr.sh "PR title"
#   dev/pr.sh "PR title" --base some-branch   # default base is dev
#   dev/pr.sh "PR title" --body "Description" # add a description above test results
#   dev/pr.sh "PR title" --skip-lint          # push and open PR without running lint
#   dev/pr.sh "PR title" --skip-tests         # push and open PR without running tests

cd "$(git rev-parse --show-toplevel)"

TITLE="${1}"
if [[ -z "$TITLE" ]]; then
    echo "Usage: dev/pr.sh \"PR title\" [--base <branch>] [--body \"description\"] [--skip-lint] [--skip-tests]"
    exit 1
fi
shift

BASE="dev"
SKIP_LINT=false
SKIP_TESTS=false
BODY=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --base) BASE="$2"; shift 2 ;;
        --body) BODY="$2"; shift 2 ;;
        --skip-lint) SKIP_LINT=true; shift ;;
        --skip-tests) SKIP_TESTS=true; shift ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [[ "$SKIP_LINT" = false ]]; then
    echo "Running lint..."
    LINT_OUTPUT=$(dev/lint.sh 2>/dev/null)
    LINT_EXIT=$?

    if [[ $TEST_EXIT -ne 0 ]]; then
        echo ""
        echo "Linting failed - aborting. Use --skip-lint to open a PR anyway."
        echo ""
        echo "$LINT_OUTPUT"
        echo $LINT_EXIT
    fi
fi

if [[ "$SKIP_TESTS" = false ]]; then
    echo "Running tests..."
    TEST_OUTPUT=$(dev/runtests.sh 2>/dev/null)
    TEST_EXIT=$?

    if [[ $TEST_EXIT -ne 0 ]]; then
        echo ""
        echo "Tests failed - aborting. Use --skip-tests to open a PR anyway."
        echo ""
        echo "$TEST_OUTPUT"
        exit $TEST_EXIT
    fi
fi

echo ""
echo "Pushing $BRANCH to origin..."
git push -u origin "$BRANCH"

echo ""
echo "Creating PR..."
gh pr create \
    --title "$TITLE" \
    --base "$BASE" \
    --body "$(cat <<EOF
${BODY:+${BODY}

---

}## Test Results

${TEST_OUTPUT:-"Tests skipped."}
${LINT_OUTPUT:-"Linting skipped"}
EOF
)"
