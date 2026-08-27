# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## Changed
- Upgrade all dev scripts to autodetect and support `podman compose` or `docker compose`

### Removed
- Remove `django-workflow-engine` (unused scaffolding; `simple_workflow` was a Hello World demo, `onboard_contractor`/`onboard_perm` were never registered)

## [2.6.0] - 2026-08-19

### Security
- Whitelist `orderBy` query parameter in donation views to prevent injection
- Use cryptographic PRNG and expand wordlist for stream key generation
- Add `CSRF_TRUSTED_ORIGINS` setting required by Django 5.2
- Pin `actions/checkout` to a commit SHA in sync workflow
- Upgrade pyjwt 2.12.1 to 2.13.0: fixes GHSA-xgmm-8j9v-c9wx (algorithm confusion via JWK-as-HMAC-secret), GHSA-jq35-7prp-9v3f (PyJWK algorithm allow-list bypass), GHSA-w7vc-732c-9m39 (DoS via b64=false payload), GHSA-993g-76c3-p5m4 (PyJWKClient accepts non-HTTP URIs), GHSA-fhv5-28vv-h8m8 (PyJWKClient cache wiped on fetch error)
- Upgrade django 5.2.15 to 5.2.17: fixes CVE-2026-15920 (URL validation bypass in display_for_field) and CVE-2026-15830 (DoS via nested geometry collections)
- Upgrade sqlparse 0.5.5 to 0.6.0: fixes CVE-2026-59893 (ReDoS via dollar-quoted literals, GHSA-prg7-hcfm-mfcr), CVE-2026-54284 (ReDoS via multiline comments, GHSA-cfqr-cjx5-5jcm), CVE-2026-71491 (ReDoS via comment-only statements)
- Upgrade social-auth-core 5.0.2 to 5.1.0: OpenID Connect backends now validate ID tokens on refresh and reject identity changes
- Upgrade wheel 0.47.0 to 0.48.0: fixes GHSA-vgq5-9859-3mmw (path traversal / arbitrary file write via crafted project name)

### Added
- `validate-release.yaml`: PR check that enforces version bump in `pyproject.toml` and matching entry in `CHANGELOG.md` on every merge to `master`
- `create-release.yaml`: automatically creates a GitHub release and tag on push to `master`, using the matching `CHANGELOG.md` section as release notes; idempotent if tag already exists

### Removed
- Remove `django-oauth-toolkit` (unused OAuth2 provider)

### Changed
- Upgrade redis client 7.4.0 to 8.1.0
- Dependency updates (certifi, idna, aiohappyeyeballs, coverage, click)
- All Login with discord flows are now using POST instead of GET, per [Changelog](https://github.com/python-social-auth/social-app-django/releases/tag/6.0.0)

### Fixed
- Fix SonarCloud JRE provisioning 403 by adding explicit Java setup step

## [2.5.2] - 2026-05-20

### Security
- Upgrade lxml 6.1.0 to 6.1.1: fixes CVE-2025-7424 and CVE-2025-11731 in bundled libxslt (GHSA-4jhm-jv67-739f)

### Changed
- Dependency updates (py-cord, yarl, decorator, django-markdownify, click)

## [2.5.1] - 2026-05-15

### Fixed
- Data migration reliability: add `batch_size=1000` to `bulk_create`, assert update counts, raise on missing roles/slugs
- Schedule view no longer swallows DB errors from narrow exception handlers
- Slot generator surfaces empty groups instead of silently skipping them
- Require confirmation before regenerating slots when signups already exist
- Warn when saved availability references roles with no active slots

## [2.5.0] - 2026-05-05

### Changed
- Replaced `django-redis-cache` with `django-redis`; upgraded redis client 3.5.3 → 7.4.0
- Upgraded Celery 5.2.7 → 5.6.3 and billiard 3.6.4 → 4.2.4
- Replaced pipenv / `Pipfile` with pip-tools / `pyproject.toml` and `requirements*.txt`

### Added
- `dev/pip-compile.sh` wrapper for reproducible lockfile generation
- `dev/check-requirements.sh` to detect version skew between lockfiles
- `requirements-ci.txt` for a minimal CI install surface

## [2.4.0] - 2026-05-01

### Added
- Public schedule display showing the game being played in each slot
- Coordinator schedule preview before the schedule is published
- Multi-slot assignments: Participant role tracked as `EventScheduleMultiAssignment`
- IGDB search panel in the `EventInterest` admin; coordinators can search, sync, and link games directly; game is auto-approved on sync
- Coordinator-linked games shown on the signup form even before they are suggested
- `sync_all_igdb_games` and `sync_single_igdb_game` rate-limited Celery tasks (2/s)
- `fetch_top_games_by_hypes` and `fetch_top_games_by_rating` beat tasks; `fetch_top_igdb_games` management command
- `resolve_fundraising_url` Celery task: follows redirects and vanity URLs, queued on `EventInterest` save
- `close_signups_for_started_events` and `retry_pending_url_resolutions` beat tasks
- `URL_RESOLUTION_MAX_ATTEMPTS` setting; resolution skipped and retried separately after exhaustion

### Fixed
- Fundraising URL resolution skips re-queuing when URL is unchanged and already resolved
- Redirect following strips query params and fragments; only scheme/host/path are followed
- CodeQL: sanitize user-provided values in log statements
- `Participants.participant()` called as classmethod instead of instance method

## [2.3.0] - 2026-04-24

### Added
- IGDB game metadata fields on `Game`: cover hash, summary, URL, multiplayer capacity, IGDB slug
- `Game.multiplayer_max_override` for capacity overrides on top of IGDB data
- `Game.status` choices field with coordinator notes; `suggested` flag for coordinators
- Slot template generator: `EventSignupSlot` and `EventSignupSlotConfig` models with a Generate Slots button in the Event admin
- Fundraising URL parser with validation
- Central permission groups (`Coordinator`, etc.) seeded automatically via `post_migrate`; `seed_permission_groups` management command
- Events link in the site navigation header
- Grouped timezone choices on the `Event` model

### Changed
- Signup form: mobile-responsive 2×2 grid for role buttons, pill-style slot buttons with consistent column widths
- `EventSlotConfig`/`EventSlotTemplate` renamed to `EventSignupSlotConfig`/`EventSignupSlot`

### Removed
- `InterestLevel` model (unused in the signup flow)
- `SalesforceEventUser` model
- Unused `team_info` HStoreField from `TeamModel`
- Unused `flags` HStoreField from `Game`

### Fixed
- Extra Life team API `IndexError` on empty response
- Invalid `<li>` elements outside `<ul>` in admin templates

## [2.2.0] - 2026-04-17

### Added
- Superstream signup form (`evtsignup`): hourly availability model, role selection, slot sign-up
- CodeQL Advanced Setup workflow for Actions and Python
- SonarCloud integration: quality gate check run via GitHub App token, PR analysis, JUnit test reporting
- Discord login button on the admin login page
- Admin nav link visible to staff users

### Changed
- `DiscordEventUser` model removed; signups now reference `UserSocialAuth` directly
- Tiltify CELERY_IMPORTS entry removed alongside v3 model removal

### Removed
- Tiltify v3 models, tasks, and settings

### Fixed
- ReDoS-vulnerable regex in Link header parser (S2631)
- Various SonarCloud-flagged code quality issues: commented-out code, wildcard imports, deprecated `datetime.utcnow()`, snake_case renames, redundant branches

## [2.1.0] - 2026-04-13

### Added
- Discord bot (`ffbot`) with `/stream-key` slash command; `ADD_DISCORD_COMMANDS` setting gates registration
- `clear_discord_commands` management command
- Discord role sync: separate role-list and member-sync tasks; `grants_staff_access` flag on `DiscordRoleMapping`
- `DISCORD_ROLE_SYNC_HOURS` and `DISCORD_MEMBER_SYNC_MINUTES` env vars for sync schedule

### Fixed
- Stream key admin display: string lookup values, `BooleanField` comparison, stream count in deletion summary
- Key display name slugification for Discord usernames containing periods
- Bot lifecycle: use `asyncio.Event` instead of `on_ready` to prevent reconnect after intentional close

## [2.0.0] - 2026-04-10

### Added
- Discord OAuth2 login: users authenticate with Discord; access denied if not in the configured guild
- Stream key management page with click-to-copy buttons for OBS setup
- OBS setup instructions for Super Stream and Direct Livestream keys
- Deferred FK constraint handling for stream key regeneration when stream history exists

### Changed
- Stream key wordlist expanded to 310 three-syllable words; uniqueness enforced at the database level
- `Key` model: primary key separated from `stream_key` field

### Removed
- Heroku Connect SQL fixture from dev setup

### Fixed
- Stream key regeneration FK constraint error when stream history exists
- Stream key name collision for users with pre-existing keys

## [1.2.0] - 2026-04-02

### Added
- `new_year` management command for yearly team/participant reset
- `untrack` and `track_team` management commands
- Admin actions to trigger on-demand donation sync for teams and participants
- ETag / `Last-Modified` conditional GET support in the DonorDrive API client (`HttpCacheDB`)
- Retry and backoff for transient Extra Life API errors
- `DEVELOPMENT.md` documenting local setup, dev scripts, and workflows
- `dev/start.sh`, `dev/runtests.sh`, `dev/reset.sh`, `dev/shell.sh`, `dev/lint.sh`, `dev/logs.sh`, `dev/pr.sh`
- sync-dev-to-master GitHub Actions workflow

### Fixed
- Untrack teams, participants, and events automatically on 404 from Extra Life API
- `TimersDB.time_until` using stale import-time timestamp
- Redis timer keys not refreshing after use

## [1.1.0] - 2025-10-24

### Added
- Set `User-Agent: fragforce.org` header on all Extra Life API requests

### Fixed
- `note_new_donations` returning early before posting missed donations to the Twitch bot

## [1.0.1] - 2024-04-13

### Changed
- Updated GitHub Actions workflows to Node.js 20
- Removed old Salesforce integration code

### Fixed
- Contact page Discord URL
- Stream schedule display
- `python3-dev` package install in Dockerfiles

### Removed
- Google Calendar embed from stream schedule page

## [1.0.0] - 2023-05-08

Initial public release.

---

[unreleased]: https://github.com/fragforce/fragforce.org/compare/v2.6.0...HEAD
[2.6.0]: https://github.com/fragforce/fragforce.org/compare/v2.5.2...v2.6.0
[2.5.2]: https://github.com/fragforce/fragforce.org/compare/v2.5.1...v2.5.2
[2.5.1]: https://github.com/fragforce/fragforce.org/compare/v2.5.0...v2.5.1
[2.5.0]: https://github.com/fragforce/fragforce.org/compare/v2.4.0...v2.5.0
[2.4.0]: https://github.com/fragforce/fragforce.org/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/fragforce/fragforce.org/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/fragforce/fragforce.org/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/fragforce/fragforce.org/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/fragforce/fragforce.org/compare/v1.2.0...v2.0.0
[1.2.0]: https://github.com/fragforce/fragforce.org/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/fragforce/fragforce.org/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/fragforce/fragforce.org/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/fragforce/fragforce.org/releases/tag/v1.0.0
