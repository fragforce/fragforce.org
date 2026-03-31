# Management Commands

Management commands are one-off commands that are run by hand generally, and not in automated tasks.


## Untrack old EL Ids

Extra Life resets all IDs every year, this management command lets us clean up old IDs so they are no longer tracked.

Works in conjunction with `MIN_EL_TEAMID` and `MIN_EL_PARTICIPANTID` settings

Preview what would be untracked (using MIN_EL_TEAMID / MIN_EL_PARTICIPANTID from settings)
`python manage.py untrack_old_el_ids --dry-run`

Run using the settings defaults (`MIN_EL_TEAMID` and `MIN_EL_PARTICIPANTID`)
`python manage.py untrack_old_el_ids`

Override with explicit values
`python manage.py untrack_old_el_ids --min-team-id 70000 --min-participant-id 600000`

Also untrack old events (skipped by default since event IDs aren't in settings)
`python manage.py untrack_old_el_ids --min-event-id 5000`

## new_year Command

Runs four steps in sequence to transition the app to a new Extra Life year.

### Usage
```bash
python manage.py new_year --new-team-id <id> [options]
```

### Steps

1. **Untrack stale records** - delegates to `untrack_old_el_ids` to set `tracked=False` on any `TeamModel`, `ParticipantModel`, and optionally `EventModel` records whose IDs fall below the configured minimums (`MIN_EL_TEAMID` / `MIN_EL_PARTICIPANTID` settings, overridable via flags).

2. **Sync the new team** - calls `update_teams` synchronously for `--new-team-id`, which fetches the team from Extra Life and auto-creates the new `EventModel` if it doesn't exist yet.

3. **Mark the new event as tracked** - sets `tracked=True` on the event associated with the new team, which is required for donation and participant syncs to recognise it as a valid current event.

4. **Sync participants** - calls `update_participants` synchronously to pull the new year's participants. Warns if `EXTRALIFE_TEAMID` in settings doesn't match `--new-team-id`, since that task reads the setting directly.

### Arguments

| Flag | Required | Description |
|------|----------|-------------|
| `--new-team-id` | Yes | The new year's Extra Life team ID |
| `--dry-run` | No | Preview steps 1 and 3; skip all syncs |
| `--min-team-id` | No | Override ID floor for team untracking (default: `MIN_EL_TEAMID`) |
| `--min-participant-id` | No | Override ID floor for participant untracking (default: `MIN_EL_PARTICIPANTID`) |
| `--min-event-id` | No | Untrack events below this ID (skipped if not specified) |
| `--skip-untrack` | No | Skip step 1 |
| `--skip-team-sync` | No | Skip step 2 |
| `--skip-event-track` | No | Skip step 3 |
| `--skip-participant-sync` | No | Skip step 4 |
