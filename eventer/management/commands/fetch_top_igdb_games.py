from django.core.management.base import BaseCommand, CommandError

from eventer.igdb import IGDBClient


class Command(BaseCommand):
    help = 'Fetch top IGDB games by hypes and/or rating and add to library as pending (not suggested)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--by', choices=['hypes', 'rating', 'both'], default='both',
            help='Sort metric: hypes (anticipation), rating (total_rating), or both (default)'
        )
        parser.add_argument('--limit', type=int, default=100, help='Number of games to fetch per metric (default: 100)')
        parser.add_argument('--min-rating-count', type=int, default=50,
                            help='Minimum rating count for --by rating (default: 50)')

    def handle(self, *args, **options):
        if not IGDBClient.credentials_configured():
            raise CommandError('IGDB credentials are not configured. Set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET.')

        client = IGDBClient()
        if not client.credentials_valid():
            raise CommandError('IGDB credentials are invalid. Check IGDB_CLIENT_ID and IGDB_CLIENT_SECRET.')

        by = options['by']
        limit = options['limit']
        min_rating_count = options['min_rating_count']

        from django.conf import settings

        from eventer.tasks import _sync_game_list
        delay = getattr(settings, 'IGDB_BULK_SYNC_DELAY', 0.5)

        if by in ('hypes', 'both'):
            self.stdout.write(f'Fetching top {limit} games by hypes...')
            results = client.top_games_by_hypes(limit=limit)
            added, updated, errors = _sync_game_list(results, delay, 'fetch_top_igdb_games[hypes]')
            self.stdout.write(self.style.SUCCESS(
                f'Hypes: {added} added, {updated} updated, {errors} errors'
            ))

        if by in ('rating', 'both'):
            self.stdout.write(f'Fetching top {limit} games by rating (min {min_rating_count} ratings)...')
            results = client.top_games_by_rating(limit=limit, min_rating_count=min_rating_count)
            added, updated, errors = _sync_game_list(results, delay, 'fetch_top_igdb_games[rating]')
            self.stdout.write(self.style.SUCCESS(
                f'Rating: {added} added, {updated} updated, {errors} errors'
            ))
