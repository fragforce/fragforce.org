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
