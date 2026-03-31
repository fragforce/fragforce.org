"""
Management command to perform all new-year setup steps for Extra Life:

  1. Untrack teams/participants/events whose IDs are below the configured minimums
  2. Sync the new team from Extra Life (which auto-creates the new EventModel)
  3. Mark the new event as tracked so downstream donation/participant queries work
  4. Sync participants for the new team

Steps can be skipped individually with --skip-* flags.  Use --dry-run to
preview steps 1 and 3 without making any changes (syncs are always skipped in
dry-run mode).
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from ffdonations.management.commands.untrack_old_el_ids import Command as UntrackCommand
from ffdonations.models import EventModel, TeamModel


class Command(BaseCommand):
    help = "Run all Extra Life new-year setup steps in order."

    def add_arguments(self, parser):
        parser.add_argument(
            '--new-team-id',
            type=int,
            required=True,
            help="The new year's Extra Life team ID",
        )
        parser.add_argument(
            '--min-team-id',
            type=int,
            default=None,
            help="Untrack teams with id < this value (default: MIN_EL_TEAMID setting)",
        )
        parser.add_argument(
            '--min-participant-id',
            type=int,
            default=None,
            help="Untrack participants with id < this value (default: MIN_EL_PARTICIPANTID setting)",
        )
        parser.add_argument(
            '--min-event-id',
            type=int,
            default=None,
            help="Untrack events with id < this value (default: skipped)",
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Preview untrack and event-track steps without saving; skip all syncs",
        )
        parser.add_argument(
            '--skip-untrack',
            action='store_true',
            help="Skip step 1: untracking old IDs",
        )
        parser.add_argument(
            '--skip-team-sync',
            action='store_true',
            help="Skip step 2: syncing the new team from Extra Life",
        )
        parser.add_argument(
            '--skip-event-track',
            action='store_true',
            help="Skip step 3: marking the new event as tracked",
        )
        parser.add_argument(
            '--skip-participant-sync',
            action='store_true',
            help="Skip step 4: syncing participants for the new team",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        new_team_id = options['new_team_id']

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "DRY RUN — untrack/event-track steps will not save; syncs skipped"
            ))

        # ------------------------------------------------------------------ #
        # Step 1: Untrack stale records                                       #
        # ------------------------------------------------------------------ #
        self.stdout.write(self.style.MIGRATE_HEADING("Step 1: Untracking stale Extra Life IDs"))
        if not options['skip_untrack']:
            untrack = UntrackCommand(stdout=self.stdout, stderr=self.stderr)
            untrack.handle(
                min_team_id=options['min_team_id'],
                min_participant_id=options['min_participant_id'],
                min_event_id=options['min_event_id'],
                dry_run=dry_run,
            )
        else:
            self.stdout.write("  Skipped")

        # ------------------------------------------------------------------ #
        # Step 2: Sync the new team (creates new EventModel if needed)        #
        # ------------------------------------------------------------------ #
        self.stdout.write(self.style.MIGRATE_HEADING("Step 2: Syncing new team from Extra Life"))
        if not options['skip_team_sync'] and not dry_run:
            from ffdonations.tasks.teams import update_teams
            result = update_teams.apply(kwargs={'teams': [new_team_id]})
            guids = result.get()
            self.stdout.write(self.style.SUCCESS(f"  Team sync complete — {len(guids)} team(s) updated"))
        else:
            self.stdout.write("  Skipped")

        # ------------------------------------------------------------------ #
        # Step 3: Mark the new event as tracked                               #
        # ------------------------------------------------------------------ #
        self.stdout.write(self.style.MIGRATE_HEADING("Step 3: Marking new event as tracked"))
        if not options['skip_event_track']:
            try:
                team = TeamModel.objects.get(id=new_team_id)
            except TeamModel.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"  Team {new_team_id} not in DB — run step 2 first (or re-run without --skip-team-sync)"
                ))
            else:
                if team.event_id is None:
                    self.stdout.write(self.style.WARNING("  Team has no associated event yet"))
                else:
                    evt = team.event
                    if evt.tracked:
                        self.stdout.write(f"  Event {evt.id} ({evt.name!r}) already tracked")
                    else:
                        self.stdout.write(f"  Marking event {evt.id} ({evt.name!r}) as tracked")
                        if not dry_run:
                            EventModel.objects.filter(id=evt.id).update(tracked=True)
                            self.stdout.write(self.style.SUCCESS("  Done"))
        else:
            self.stdout.write("  Skipped")

        # ------------------------------------------------------------------ #
        # Step 4: Sync participants                                            #
        # ------------------------------------------------------------------ #
        self.stdout.write(self.style.MIGRATE_HEADING("Step 4: Syncing participants from Extra Life"))
        if not options['skip_participant_sync'] and not dry_run:
            if new_team_id != settings.EXTRALIFE_TEAMID:
                self.stdout.write(self.style.WARNING(
                    f"  Note: EXTRALIFE_TEAMID={settings.EXTRALIFE_TEAMID} but --new-team-id={new_team_id}. "
                    "Participant sync uses EXTRALIFE_TEAMID — update the env var to match."
                ))
            from ffdonations.tasks.participants import update_participants
            result = update_participants.apply()
            guids = result.get()
            self.stdout.write(self.style.SUCCESS(f"  Participant sync complete — {len(guids)} participant(s) updated"))
        else:
            self.stdout.write("  Skipped")

        self.stdout.write(self.style.SUCCESS("\nNew year setup complete."))
