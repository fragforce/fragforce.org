import logging
import time

from celery import shared_task

log = logging.getLogger(__name__)

@shared_task(rate_limit='2/s')  # stays under IGDB's 4 req/sec, leaves headroom for interactive searches
def sync_single_igdb_game(igdb_id):
    """
    Sync a single game from IGDB by ID.
    Rate-limited at 2/s across all workers.
    """
    from eventer.igdb import IGDBError, sync_game_from_igdb
    try:
        game, created = sync_game_from_igdb(igdb_id)
        return {'igdb_id': igdb_id, 'name': game.name, 'created': created}
    except (IGDBError, ValueError) as e:
        log.warning('sync_single_igdb_game: failed igdb_id=%s: %s', igdb_id, e)
        raise


@shared_task
def sync_all_igdb_games():
    """Re-fetch all existing Game records from IGDB by dispatching rate-limited per-game tasks."""
    from eventer.igdb import IGDBClient
    from eventer.models import Game

    if not IGDBClient.credentials_configured():
        log.info('sync_all_igdb_games: IGDB credentials not configured, skipping')
        return

    igdb_ids = list(Game.objects.values_list('igdb_id', flat=True))
    log.info('sync_all_igdb_games: dispatching %d tasks', len(igdb_ids))
    for igdb_id in igdb_ids:
        sync_single_igdb_game.delay(igdb_id)


@shared_task
def fetch_top_games_by_hypes(limit=100):
    """Fetch top games by hypes from IGDB and add to library as pending. Dispatches rate-limited per-game tasks."""
    from eventer.igdb import IGDBClient, IGDBError

    if not IGDBClient.credentials_configured():
        log.info('fetch_top_games_by_hypes: IGDB credentials not configured, skipping')
        return

    client = IGDBClient()
    try:
        results = client.top_games_by_hypes(limit=limit)
    except IGDBError as e:
        log.error('fetch_top_games_by_hypes: failed to fetch from IGDB: %s', e)
        return

    log.info('fetch_top_games_by_hypes: dispatching %d tasks', len(results))
    for r in results:
        if r.get('id'):
            sync_single_igdb_game.delay(r['id'])


@shared_task
def fetch_top_games_by_rating(limit=100, min_rating_count=50):
    """Fetch top-rated games from IGDB and add to library as pending. Dispatches rate-limited per-game tasks."""
    from eventer.igdb import IGDBClient, IGDBError

    if not IGDBClient.credentials_configured():
        log.info('fetch_top_games_by_rating: IGDB credentials not configured, skipping')
        return

    client = IGDBClient()
    try:
        results = client.top_games_by_rating(limit=limit, min_rating_count=min_rating_count)
    except IGDBError as e:
        log.error('fetch_top_games_by_rating: failed to fetch from IGDB: %s', e)
        return

    log.info('fetch_top_games_by_rating: dispatching %d tasks', len(results))
    for r in results:
        if r.get('id'):
            sync_single_igdb_game.delay(r['id'])


def _sync_game_list(results, delay, source_label):
    """
    Sync a list of IGDB game dicts synchronously without auto-suggesting.
    Used by management commands for immediate execution without task dispatch.
    Returns (added, updated, errors).
    """
    from eventer.igdb import IGDBError, sync_game_from_igdb

    added, updated, errors = 0, 0, 0
    for r in results:
        igdb_id = r.get('id')
        if not igdb_id:
            continue
        try:
            _, created = sync_game_from_igdb(igdb_id)
            if created:
                added += 1
            else:
                updated += 1
        except IGDBError as e:
            log.warning('%s: failed to sync igdb_id=%s: %s', source_label, igdb_id, e)
            errors += 1
        except ValueError as e:
            log.warning('%s: igdb_id=%s not found: %s', source_label, igdb_id, e)
            errors += 1
        if delay > 0:
            time.sleep(delay)
    return added, updated, errors


@shared_task
def close_signups_for_started_events():
    """
    Auto-close signups for events that have started.
    Sets signups_open=False on any Event where the earliest period has started
    and signups_open is still True. Uses a single annotated UPDATE to avoid N+1 saves.
    """
    from django.db.models import Min
    from django.utils import timezone

    from eventer.models import Event

    now = timezone.now()
    closed = (
        Event.objects
        .filter(signups_open=True)
        .annotate(first_start=Min('eventperiod__start'))
        .filter(first_start__lte=now)
        .update(signups_open=False)
    )
    log.info('close_signups_for_started_events: closed %d events', closed)
