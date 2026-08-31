# Development Guide

## Requirements

- [Docker](https://docker.com)
- [Docker Compose](https://docs.docker.com/compose/) or [Podman Compose](https://docs.podman.io/en/v5.6.2/markdown/podman-compose.1.html)
- [GitHub CLI (`gh`)](https://cli.github.com/) — required for `dev/pr.sh`

## Initial Setup

```bash
cp env.sample .env
```

Generate a secret key and add it to `.env`:

```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(50))" >> .env
```

Then start the dev stack - on first run this will build the containers, run migrations, load the HC schema, and collect static files:

```bash
dev/start.sh
```

## Dev Scripts

All developer scripts live in `dev/` and can be run from the repo root.

| Script | Description |
| -------- | ------------- |
| `dev/lib.sh` | Library script to autodetech compose engine, make sure the engine is running, and check if the web stack is running. |
| `dev/start.sh` | Start the dev stack. Detects first run and handles setup automatically. |
| `dev/update.sh` | Pull latest changes, rebuild image if dependencies changed, and run migrations. |
| `dev/pip-compile.sh [prod\|ci\|dev] [--upgrade] [--upgrade-package pkg]` | Regenerate pip-tools lockfiles inside the dev container. Defaults to all three. `--upgrade` upgrades all packages; `--upgrade-package pkg` upgrades a single package across all files. |
| `dev/check-requirements.sh [--quiet\|--exclusive]` | Check for version differences between the three lockfiles (`--quiet` for exit-code only). `--exclusive` shows which packages are dev-only, ci+dev-only, or shared across all files - useful for evaluating Dependabot PR scope. |
| `dev/reset.sh [--clean] [--force]` | Tear down volumes and restart. `--clean` also removes built images forcing a full Docker rebuild. `--force` skips the confirmation prompt. |
| `dev/shell.sh [bash\|django\|db]` | Open a shell in the web container: `bash` (default), `django` (Django shell), `db` (dbshell). |
| `dev/lint.sh [dir]` | Run pyflakes across all Python files (or a specific app directory). |
| `dev/logs.sh [service]` | Tail logs for a service (`web` default; also `worker`, `beat`, `db`, `redis`). |
| `dev/migrate.sh [app]` | Run pending migrations (all apps, or a specific one). |
| `dev/makemigrations.sh [app]` | Create migrations for model changes (all apps, or a specific one). Passes through any extra Django args (e.g. `--check`). |
| `dev/runtests.sh [--fresh] [target]` | Run tests and format output as a GitHub-ready markdown comment. `--fresh` drops and recreates the test DB first. |
| `dev/coverage.sh [app]` | Run tests with coverage and print a full coverage report sorted by worst coverage first. |
| `dev/pr.sh "Title" [--base branch] [--body "desc"] [--skip-tests]` | Run tests, push branch, and open a PR with test results embedded in the body. Aborts if tests fail. Requires `gh`. Defaults to `dev` as the base branch. |

## Running Tests

```bash
# Run all tests
dev/runtests.sh

# Run a single app's tests
dev/runtests.sh ffdonations

# Run a specific test class or method
dev/runtests.sh ffdonations.tests.TeamAdminSyncDonationsTest
dev/runtests.sh ffdonations.tests.TeamAdminSyncDonationsTest.test_queues_task_for_each_selected_team
```

Or use Django directly:

```bash
docker compose exec web python manage.py test
```

```bash
podman compose exec web python manage.py test
```

## Useful Commands

Inside the container (`dev/shell.sh`):

```bash
python manage.py shell       # Django shell
python manage.py dbshell     # Postgres shell
python manage.py migrate     # Run migrations
python manage.py collectstatic --no-input
```

## Environment Variables

Copy `env.sample` to `.env` to get started. All optional variables have sensible defaults — only set them if you need to override.

### Required

| Variable | Description |
| ---------- | ------------- |
| `SECRET_KEY` | Django secret key (generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`) |

### Redis

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `REDIS_URL` | `redis://localhost` | Single Redis instance (split across DB indexes 0-4) |
| `REDIS0_URL`-`REDIS4_URL` | - | Override individual Redis DB URLs (default, tasks, tombs, timers, cache) |

### Discord OAuth2

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `DISCORD_CLIENT_ID` | - | OAuth2 app client ID |
| `DISCORD_CLIENT_SECRET` | - | OAuth2 app client secret |
| `DISCORD_GUILD_ID` | `164136635762606081` | Required guild; users not in this guild are denied login |

### Discord Bot

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `DISCORD_BOT_TOKEN` | - | Bot token for role sync and slash commands |
| `ADD_DISCORD_COMMANDS` | `true` | Set to `false` to start the bot without registering slash commands |
| `DISCORD_ROLE_SYNC_HOURS` | `1` | How often to sync Discord roles (hours) |
| `DISCORD_MEMBER_SYNC_MINUTES` | `15` | How often to sync guild member roles (minutes) |

### Extra Life / DonorDrive

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `EXTRALIFE_TEAMID` | `73149` | Extra Life team ID to sync |
| `MIN_EL_TEAMID` | `73127` | Minimum valid team ID |
| `MIN_EL_PARTICIPANTID` | `565075` | Minimum valid participant ID |
| `EL_EVENT_ID` | `-1` | Extra Life event ID filter (-1 = all) |
| `EL_REQUEST_MIN_TIME_SECONDS` | `15` | Minimum time between API requests |
| `EL_REQUEST_MIN_TIME_URL_SECONDS` | `15` | Minimum time between requests to the same URL |
| `EL_RETRY_AFTER_SECONDS` | `60` | Delay after a rate-limit response |
| `EL_MAX_RETRIES` | `3` | Max retries on rate-limit |
| `EL_SERVER_RETRY_AFTER_SECONDS` | `600` | Delay after a server error |
| `EL_SERVER_MAX_RETRIES` | `6` | Max retries on server error |
| `REQUEST_MIN_TIME_HOST_SECONDS` | `15` | Minimum time between requests to the same host |

### Tiltify

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `TILTIFY_TOKEN` | - | Tiltify API token |
| `TILTIFY_TEAMS` | `fragforce` | Comma-separated team slugs |
| `TILTIFY_TIMEOUT` | `60` | API request timeout (seconds) |
| `TILTIFY_APP_OWNER` | - | Tiltify app owner slug |

### IGDB

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `IGDB_CLIENT_ID` | - | Twitch app client ID create at [twitch](https://dev.twitch.tv/console/apps) |
| `IGDB_CLIENT_SECRET` | - | Twitch app client secret |
| `IGDB_RATE_LIMIT_RETRIES` | `3` | Max retries on IGDB 429 rate limit response |
| `IGDB_RATE_LIMIT_RETRY_AFTER` | `1.0` | Default wait (seconds) between retries if no Retry-After header |

### Twitch Bot Integration

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `FRAG_BOT_API` | `https://bot.fragforce.org/dbquery` | Twitch bot API endpoint |
| `FRAG_BOT_KEY` | - | API key |
| `FRAG_BOT_BOT` | `misterfragbot` | Bot username |

### Donations

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `SINGAPORE_DONATIONS` | `0.0` | Manual donation adjustment (SGD region) |
| `OTHER_DONATIONS` | `0.0` | Manual donation adjustment (other) |
| `TARGET_DONATIONS` | `1.0` | Donation goal override |
| `SEND_MISSED_DONATIONS` | `10` | Minutes of missed donations to re-announce |

### Streaming

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `STREAM_URL` | - | Stream URL |
| `STREAM_DASH_BASE` | `https://stream.fragforce.org` | DASH stream server base URL |

### Django / Performance

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `DEBUG` | `True` | Django debug mode |
| `DJANGO_LOG_LEVEL` | `INFO` | Log level |
| `MAX_API_ROWS` | `1024` | Max rows returned by API endpoints |
| `GOOGLE_ANALYTICS_ID` | - | GA tracking ID |
| `MAX_UPCOMING_EVENTS` | `20` | Max upcoming events shown |
| `MAX_PAST_EVENTS` | `20` | Max past events shown |
| `DOCKER` | `False` | Use Docker database config |
| `DOCKER_PROD` | `False` | Use Docker production database config |

### View Cache Timeouts (seconds)

| Variable | Default |
| ---------- | --------- |
| `VIEW_TEAMS_CACHE` | `20` |
| `VIEW_PARTICIPANTS_CACHE` | `20` |
| `VIEW_DONATIONS_CACHE` | `20` |
| `VIEW_DONATIONS_STATS_CACHE` | `20` |
| `VIEW_SITE_EVENT_CACHE` | `60` |
| `VIEW_SITE_SITE_CACHE` | `60` |
| `VIEW_SITE_STATIC_CACHE` | `300` |

See `env.sample` for a commented template of all variables.

## Managing Dependencies

Dependencies are declared in `pyproject.toml` and locked in three files:

| File | Used by |
| ------ | --------- |
| `requirements.txt` | Production Docker images |
| `requirements-ci.txt` | CI (GitHub Actions coverage workflow) |
| `requirements-dev.txt` | Local dev container |

To regenerate lockfiles after editing `pyproject.toml`:

```bash
dev/pip-compile.sh                        # regenerate all three
dev/pip-compile.sh prod                   # production only
dev/pip-compile.sh ci                     # CI only
dev/pip-compile.sh dev                    # dev only
dev/pip-compile.sh --upgrade              # upgrade all packages
dev/pip-compile.sh --upgrade-package django  # upgrade a single package across all files
```

To check for version skew between lockfiles (e.g. after a Dependabot PR):

```bash
dev/check-requirements.sh             # check for diffs, exits 1 if found
dev/check-requirements.sh --exclusive # show which packages are dev/ci-only vs shared
```

After regenerating, rebuild containers to pick up changes:

```bash
dev/reset.sh --clean
```
