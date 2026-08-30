# Shared helpers for the dev/ scripts.
#
# Source this near the top of each script (before any `cd`):
#   source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"
#
# It selects a compose backend (docker or podman) and exposes small wrappers:
#   dc <args>          run a compose command against the selected backend
#   engine <args>      run a raw engine command (image, info, ...) on the backend
#   require_engine     fail with a clear message if the engine isn't reachable
#   ensure_web_running start the dev stack if the web container isn't up

FF_DEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- compose backend selection -----------------------------------------
# COMPOSE_BACKEND=docker|podman forces a backend; otherwise auto-detect
# (prefer docker, fall back to podman).
if [[ -n "$COMPOSE_BACKEND" ]]; then
    case "$COMPOSE_BACKEND" in
        docker|podman) ;;
        *) echo "Error: COMPOSE_BACKEND must be 'docker' or 'podman' (got '$COMPOSE_BACKEND')." >&2; exit 1 ;;
    esac
elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    COMPOSE_BACKEND=docker
elif command -v podman >/dev/null 2>&1 && podman compose version >/dev/null 2>&1; then
    COMPOSE_BACKEND=podman
else
    echo "Error: no usable compose backend (need 'docker compose' or 'podman compose')." >&2
    exit 1
fi

# dc <args> — run a compose command against the selected backend.
dc() {
    if [[ "$COMPOSE_BACKEND" == "podman" ]]; then
        podman compose "$@"
    else
        docker compose "$@"
    fi
}

# engine <args> — run a raw engine command (image, info, ...) on the backend.
engine() {
    if [[ "$COMPOSE_BACKEND" == "podman" ]]; then
        podman "$@"
    else
        docker "$@"
    fi
}

# require_engine — fail with a clear message if the engine isn't reachable.
require_engine() {
    if ! engine info >/dev/null 2>&1; then
        echo "Error: ${COMPOSE_BACKEND} is not running or not accessible." >&2
        exit 1
    fi
}

# ensure_web_running — start the dev stack if the web container isn't up.
ensure_web_running() {
    if ! dc ps -q --status running web 2>/dev/null | grep -q .; then
        echo "Containers not running - starting dev stack..."
        "$FF_DEV_DIR/start.sh"
    fi
}
