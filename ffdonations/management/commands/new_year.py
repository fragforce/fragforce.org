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

SKIPPED_DRY = "Dry Run - Skipped"
SKIPPED_ARG = "Step Explicitly Skipped"

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

        self._step1_untrack(options, dry_run)
        self._step2_sync_team(new_team_id, dry_run, options['skip_team_sync'])
        self._step3_track_event(new_team_id, dry_run, options['skip_event_track'])
        self._step4_sync_participants(new_team_id, dry_run, options['skip_participant_sync'])

        self.stdout.write(self.style.SUCCESS("\nNew year setup complete."))

    def _step1_untrack(self, options, dry_run):
        self.stdout.write(self.style.MIGRATE_HEADING("Step 1: Untracking stale Extra Life IDs"))
        if options['skip_untrack']:
            self.stdout.write(SKIPPED_ARG)
            return
        untrack = UntrackCommand(stdout=self.stdout, stderr=self.stderr)
        untrack.handle(
            min_team_id=options['min_team_id'],
            min_participant_id=options['min_participant_id'],
            min_event_id=options['min_event_id'],
            dry_run=dry_run,
        )

    def _step2_sync_team(self, new_team_id, dry_run, skip):
        self.stdout.write(self.style.MIGRATE_HEADING("Step 2: Syncing new team from Extra Life"))
        if skip:
            self.stdout.write(SKIPPED_ARG)
            return
        elif dry_run:
            self.stdout.write(SKIPPED_DRY)
            return
        from ffdonations.tasks.teams import update_teams
        guids = update_teams.apply(kwargs={'teams': [new_team_id]}).get()
        self.stdout.write(self.style.SUCCESS(f"  Team sync complete - {len(guids)} team(s) updated"))

    def _step3_track_event(self, new_team_id, dry_run, skip):
        self.stdout.write(self.style.MIGRATE_HEADING("Step 3: Marking new event as tracked"))
        if skip:
            self.stdout.write(SKIPPED_ARG)
            return
        try:
            team = TeamModel.objects.get(id=new_team_id)
        except TeamModel.DoesNotExist:
            self.stdout.write(self.style.WARNING(
                f"  Team {new_team_id} not in DB - run step 2 first (or re-run without --skip-team-sync)"
            ))
            return
        if team.event_id is None:
            self.stdout.write(self.style.WARNING("  Team has no associated event yet"))
            return
        evt = team.event
        if evt.tracked:
            self.stdout.write(f"  Event {evt.id} ({evt.name!r}) already tracked")
            return
        self.stdout.write(f"  Marking event {evt.id} ({evt.name!r}) as tracked")
        if not dry_run:
            EventModel.objects.filter(id=evt.id).update(tracked=True)
            self.stdout.write(self.style.SUCCESS("  Done"))
        else:
            self.stdout.write(SKIPPED_DRY)

    def _step4_sync_participants(self, new_team_id, dry_run, skip):
        self.stdout.write(self.style.MIGRATE_HEADING("Step 4: Syncing participants from Extra Life"))
        if skip:
            self.stdout.write(SKIPPED_ARG)
            return
        elif dry_run:
            self.stdout.write(SKIPPED_DRY)
            return
        if new_team_id != settings.EXTRALIFE_TEAMID:
            self.stdout.write(self.style.WARNING(
                f"  Note: EXTRALIFE_TEAMID={settings.EXTRALIFE_TEAMID} but --new-team-id={new_team_id}. "
                "Participant sync uses EXTRALIFE_TEAMID - update the env var to match."
            ))
        from ffdonations.tasks.participants import update_participants
        guids = update_participants.apply().get()
        self.stdout.write(self.style.SUCCESS(f"  Participant sync complete - {len(guids)} participant(s) updated"))
