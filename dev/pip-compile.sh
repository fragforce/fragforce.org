#!/usr/bin/env bash
# Regenerate pip-tools lockfiles inside the dev container.
#
# Usage:
#   dev/pip-compile.sh                          # regenerate all three lockfiles
#   dev/pip-compile.sh prod                     # regenerate requirements.txt only
#   dev/pip-compile.sh ci                       # regenerate requirements-ci.txt only
#   dev/pip-compile.sh dev                      # regenerate requirements-dev.txt only
#   dev/pip-compile.sh --upgrade                # regenerate all and allow upgrades
#   dev/pip-compile.sh --upgrade-package <pkg>  # upgrade a single package across all files
#
# pip>=26 is ensured automatically before compiling.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

cd "$(git rev-parse --show-toplevel)"

require_engine

UPGRADE_FLAG=""
UPGRADE_PACKAGES=()
TARGET="all"

# Ensure pip>=26 - older pip fails on kombu's setup.py (use_2to3 removed in setuptools 58+)
dc run --rm compile pip install --quiet "pip>=26" 2>/dev/null || true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --upgrade) UPGRADE_FLAG="--upgrade"; shift ;;
        --upgrade-package) UPGRADE_PACKAGES+=("$2"); shift 2 ;;
        prod|ci|dev) TARGET="$1"; shift ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

if [[ ${#UPGRADE_PACKAGES[@]} -gt 0 ]]; then
    UPGRADE_OR_NO_UPGRADE=""
    for pkg in "${UPGRADE_PACKAGES[@]}"; do
        UPGRADE_OR_NO_UPGRADE="$UPGRADE_OR_NO_UPGRADE --upgrade-package $pkg"
    done
else
    UPGRADE_OR_NO_UPGRADE="${UPGRADE_FLAG:---no-upgrade}"
fi

compile_prod() {
    echo "Compiling requirements.txt..."
    dc run --rm compile pip-compile /code/pyproject.toml \
        -o /code/requirements.txt \
        --generate-hashes \
        $UPGRADE_OR_NO_UPGRADE
}

compile_ci() {
    echo "Compiling requirements-ci.txt..."
    dc run --rm compile pip-compile /code/pyproject.toml \
        --extra ci \
        -o /code/requirements-ci.txt \
        --generate-hashes \
        $UPGRADE_OR_NO_UPGRADE \
        --allow-unsafe
}

compile_dev() {
    echo "Compiling requirements-dev.txt..."
    dc run --rm compile pip-compile /code/pyproject.toml \
        --extra dev \
        -o /code/requirements-dev.txt \
        --generate-hashes \
        $UPGRADE_OR_NO_UPGRADE \
        --allow-unsafe
}

case "$TARGET" in
    prod) compile_prod ;;
    ci)   compile_ci ;;
    dev)  compile_dev ;;
    all)
        compile_prod
        compile_ci
        compile_dev
        ;;
esac

echo ""
echo "Done. Review changes then run dev/reset.sh --clean to rebuild containers."
