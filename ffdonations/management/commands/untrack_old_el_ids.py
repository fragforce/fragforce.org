"""
Management command to untrack Extra Life records whose IDs fall below a
specified minimum.  Extra Life resets all IDs every calendar year, so any
record with an ID below the new year's minimum is stale.
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from ffdonations.models import EventModel, TeamModel, ParticipantModel


class Command(BaseCommand):
    help = (
        "Set tracked=False for Extra Life Events, Teams, and Participants "
        "whose IDs are below the given minimums.  Defaults to the "
        "MIN_EL_TEAMID / MIN_EL_PARTICIPANTID settings."
    )

    def add_arguments(self, parser):
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
            help="Untrack events with id < this value (default: none, skipped unless specified)",
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Show what would be untracked without making any changes",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        min_team_id = options['min_team_id'] if options['min_team_id'] is not None else settings.MIN_EL_TEAMID
        min_participant_id = options['min_participant_id'] if options['min_participant_id'] is not None else settings.MIN_EL_PARTICIPANTID
        min_event_id = options['min_event_id']

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made"))

        self._untrack(
            model=TeamModel,
            label="Teams",
            min_id=min_team_id,
            dry_run=dry_run,
        )
        self._untrack(
            model=ParticipantModel,
            label="Participants",
            min_id=min_participant_id,
            dry_run=dry_run,
        )
        if min_event_id is not None:
            self._untrack(
                model=EventModel,
                label="Events",
                min_id=min_event_id,
                dry_run=dry_run,
            )
        else:
            self.stdout.write("Events: skipped (pass --min-event-id to include)")

    def _untrack(self, model, label, min_id, dry_run):
        qs = model.objects.filter(tracked=True, id__lt=min_id)
        count = qs.count()
        if count == 0:
            self.stdout.write(f"{label}: nothing to untrack below id={min_id}")
            return
        self.stdout.write(f"{label}: {count} record(s) with id < {min_id} currently tracked")
        if not dry_run:
            updated = qs.update(tracked=False)
            self.stdout.write(self.style.SUCCESS(f"{label}: untracked {updated} record(s)"))
