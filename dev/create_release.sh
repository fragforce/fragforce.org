#!/usr/bin/env bash
# Run all release validation checks (mirroring validate-release.yaml), run the
# full test suite, and if everything passes create a PR to the target branch
# using the extracted CHANGELOG section as the PR body.
#
# Usage:
#   dev/create_release.sh              # target branch: dev (default)
#   dev/create_release.sh master       # target branch: master
#   dev/create_release.sh --base dev   # same as default, explicit

set -eo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

cd "$(git rev-parse --show-toplevel)"

# --- argument parsing -------------------------------------------------------
BASE="dev"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --base) BASE="$2"; shift 2 ;;
        dev|master) BASE="$1"; shift ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

# --- helpers ----------------------------------------------------------------
pass() { echo "  ✅ $*"; }
fail() { echo "  ❌ $*" >&2; FAILED=1; }

# version_gt A B — true (0) if A is strictly greater than B (semver MAJOR.MINOR.PATCH).
# Uses pure bash arithmetic so it works on macOS without GNU coreutils.
version_gt() {
    local IFS=.
    local -a a=($1) b=($2)
    for i in 0 1 2; do
        local ai=${a[$i]:-0} bi=${b[$i]:-0}
        if (( ai > bi )); then return 0; fi
        if (( ai < bi )); then return 1; fi
    done
    return 1  # equal is not greater
}

FAILED=0
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "==> Release validation (targeting: $BASE)"
echo ""

# --- Check 1: version bump --------------------------------------------------
echo "--- Version check"

git fetch origin "$BASE" --quiet

BASE_VERSION=$(git show "origin/$BASE:pyproject.toml" | grep '^version = ' | cut -d'"' -f2)
PR_VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)

if [[ "$BASE_VERSION" = "$PR_VERSION" ]]; then
    fail "Version not bumped (still $BASE_VERSION)"
elif version_gt "$PR_VERSION" "$BASE_VERSION"; then
    pass "Version bumped: $BASE_VERSION -> $PR_VERSION"
else
    fail "Version downgraded: $BASE_VERSION -> $PR_VERSION (must increase)"
fi

# --- Check 2: CHANGELOG.md updated ------------------------------------------
echo "--- CHANGELOG check"

if ! git diff --name-only "origin/$BASE...HEAD" | grep -q '^CHANGELOG.md$'; then
    fail "CHANGELOG.md not updated relative to $BASE"
else
    pass "CHANGELOG.md updated"

    # Check 3: version section present
    if [[ "$BASE_VERSION" != "$PR_VERSION" ]]; then
        if ! grep -q "^## \[$PR_VERSION\]" CHANGELOG.md; then
            fail "Version $PR_VERSION not found in CHANGELOG.md (expected: ## [$PR_VERSION] - YYYY-MM-DD)"
        else
            pass "Version $PR_VERSION found in CHANGELOG.md"
        fi
    fi
fi

# --- Check 4: tag does not already exist ------------------------------------
echo "--- Tag check"

git fetch --tags --quiet
TAG="v$PR_VERSION"
if git rev-parse "$TAG" >/dev/null 2>&1; then
    fail "Tag $TAG already exists - release already created?"
else
    pass "Tag $TAG does not exist yet"
fi

# --- Bail out if any validation failed ---------------------------------------
if [[ $FAILED -ne 0 ]]; then
    echo ""
    echo "Release validation failed - fix the issues above before creating a release PR." >&2
    exit 1
fi

# --- Extract changelog section ----------------------------------------------
echo ""
echo "==> Extracting CHANGELOG section for $PR_VERSION"

CHANGELOG_SECTION=$(awk "/^## \[$PR_VERSION\]/{flag=1; next} /^## \[/{flag=0} flag" CHANGELOG.md)

if [[ -z "$CHANGELOG_SECTION" ]]; then
    echo "CHANGELOG.md section for $PR_VERSION is empty - add release notes first." >&2
    exit 1
fi

# Grab the full header line including the date
CHANGELOG_HEADER=$(grep "^## \[$PR_VERSION\]" CHANGELOG.md)
echo "  Found: $CHANGELOG_HEADER"

# --- Run test suite ---------------------------------------------------------
echo ""
echo "==> Running test suite"
echo ""

require_engine
ensure_web_running

TEST_OUTPUT=$(dev/runtests.sh 2>/dev/null)
TEST_EXIT=$?

echo "$TEST_OUTPUT"

if [[ $TEST_EXIT -ne 0 ]]; then
    echo ""
    echo "Tests failed - aborting." >&2
    exit $TEST_EXIT
fi

# --- Push branch and create PR ----------------------------------------------
echo ""
echo "==> Pushing $CURRENT_BRANCH to origin"
git push -u origin "$CURRENT_BRANCH"

echo ""
echo "==> Creating release PR: $PR_VERSION -> $BASE"

gh pr create \
    --title "Release $PR_VERSION" \
    --base "$BASE" \
    --body "$(cat <<EOF
## Release $PR_VERSION

$CHANGELOG_HEADER

$CHANGELOG_SECTION

---

## Test Results

$TEST_OUTPUT
EOF
)"
