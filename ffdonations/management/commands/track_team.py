"""
Management command to add a new Extra Life team and mark it as tracked.

Fetches the team from the Extra Life API (creating or updating the local
TeamModel and its EventModel), then sets tracked=True on the team.
"""
from django.core.management.base import BaseCommand

from ffdonations.models import TeamModel


class Command(BaseCommand):
    help = "Fetch an Extra Life team from the API and mark it as tracked."

    def add_arguments(self, parser):
        parser.add_argument(
            '--team-id',
            type=int,
            required=True,
            help="The Extra Life team ID to track",
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Fetch and display team info without marking it as tracked",
        )

    def handle(self, *args, **options):
        team_id = options['team_id']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - team will not be marked as tracked"))

        self.stdout.write(f"Fetching team {team_id} from Extra Life...")
        from ffdonations.tasks.teams import update_teams
        update_teams.apply(kwargs={'teams': [team_id]}).get()

        try:
            team = TeamModel.objects.get(id=team_id)
        except TeamModel.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Team {team_id} not found after sync - check the team ID is valid"))
            return

        self.stdout.write(f"  Name:  {team.name}")
        self.stdout.write(f"  Event: {team.event_id} ({getattr(team.event, 'name', 'unknown')})")
        self.stdout.write(f"  Donations: {team.numDonations} totalling ${team.sumDonations}")

        if team.tracked:
            self.stdout.write(self.style.SUCCESS(f"Team {team_id} is already tracked"))
            return

        if not dry_run:
            TeamModel.objects.filter(id=team_id).update(tracked=True)
            self.stdout.write(self.style.SUCCESS(f"Team {team_id} is now tracked"))
