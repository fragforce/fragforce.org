import logging

import requests
from celery import shared_task

from extralifeapi.participants import Participants

log = logging.getLogger(__name__)


def _safe_log(value):
    """Sanitize a user-provided value for logging by stripping newlines (prevents log injection)."""
    return str(value).replace('\n', ' ').replace('\r', ' ')


@shared_task
def resolve_fundraising_url(event_interest_id):
    """
    Resolve a fundraising URL on an EventInterest to a canonical participant or team record.

    - If the URL is a participant page: find or create a ParticipantModel and link via el_participant.
    - If the URL is a team page: log for coordinator review (no automated action).
    - If the URL is unrecognised or empty: log and exit.
    """
    from django.conf import settings

    from evtsignup.models import EventInterest
    from evtsignup.utils import parse_fundraising_url
    max_attempts = getattr(settings, 'URL_RESOLUTION_MAX_ATTEMPTS', 3)

    try:
        interest = EventInterest.objects.get(pk=event_interest_id)
    except EventInterest.DoesNotExist:
        log.warning('resolve_fundraising_url: EventInterest %s not found', event_interest_id)
        return

    if not interest.fundraising_url:
        return

    if interest.url_resolution_attempts >= max_attempts:
        log.info(
            'resolve_fundraising_url: EventInterest %s has reached max attempts (%d), skipping',
            event_interest_id, max_attempts,
        )
        return

    interest.url_resolution_attempts += 1
    interest.save(update_fields=['url_resolution_attempts'])

    result = parse_fundraising_url(interest.fundraising_url)

    if result.is_participant:
        _resolve_participant(interest, result)
    elif result.is_team:
        log.info(
            'resolve_fundraising_url: EventInterest %s has a team URL - flagged for coordinator review',
            event_interest_id,
        )
    else:
        # Try following redirects - may be a vanity link pointing to Extra Life
        if _is_followable_url(interest.fundraising_url):
            resolved = _follow_redirect(interest.fundraising_url)
            if resolved and resolved != interest.fundraising_url:
                redirected_result = parse_fundraising_url(resolved)
                if redirected_result.is_participant:
                    log.info(
                        'resolve_fundraising_url: EventInterest %s resolved via redirect to participant',
                        event_interest_id,
                    )
                    _resolve_participant(interest, redirected_result)
                    return
                elif redirected_result.is_team:
                    log.info(
                        'resolve_fundraising_url: EventInterest %s redirect resolves to team URL - flagged for review',
                        event_interest_id,
                    )
                    return
        log.info(
            'resolve_fundraising_url: EventInterest %s has unrecognised URL',
            event_interest_id,
        )


def _is_followable_url(url):
    """Return True if the URL is a valid http/https URL worth attempting to follow."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url if '://' in url else f'https://{url}')
        return (
            parsed.scheme in ('http', 'https')
            and bool(parsed.netloc)
            and ' ' not in parsed.netloc
            and '.' in parsed.netloc
        )
    except Exception:
        return False


def _follow_redirect(url):
    """
    Follow HTTP redirects on a user-provided URL and return the final URL.
    Query params/fragments are stripped from the *outgoing* request only to reduce attack
    surface. The returned URL (resp.url) preserves whatever params the server redirected
    to — parse_fundraising_url() relies on this to extract participant IDs from query strings.
    Only called after _is_followable_url() validates the URL. The final URL is always
    re-parsed through parse_fundraising_url() before any action is taken.
    """
    from urllib.parse import urlparse, urlunparse
    try:
        raw = url if '://' in url else f'https://{url}'
        parsed = urlparse(raw)
        # Strip query, params, fragment, and credentials - only follow scheme/host/path
        clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
        resp = requests.get(
            clean_url,
            allow_redirects=True,
            timeout=10,
            headers={'User-Agent': 'Fragforce/1.0'},
        )
        return resp.url
    except Exception as e:
        log.debug('_follow_redirect: request failed: %s', e)
        return None


def _resolve_participant(interest, result):
    """Look up the participant by ID or slug and link to el_participant."""
    from ffdonations.models import ParticipantModel

    id_or_slug = result.id_or_slug
    safe_slug = _safe_log(id_or_slug)
    log.info(
        'resolve_fundraising_url: resolving participant %s for EventInterest %s',
        safe_slug, interest.pk,
    )

    try:
        api_participant = Participants().participant(id_or_slug)
    except Exception as e:
        log.warning(
            'resolve_fundraising_url: failed to fetch participant %s: %s',
            safe_slug, e,
        )
        return

    if not api_participant:
        log.warning(
            'resolve_fundraising_url: participant %s not found in Extra Life API',
            safe_slug,
        )
        return

    numeric_id = api_participant.get('participantID')
    if not numeric_id:
        log.warning('resolve_fundraising_url: no participantID in API response for %s', safe_slug)
        return

    participant, created = ParticipantModel.objects.get_or_create(
        id=numeric_id,
        defaults={'displayName': api_participant.get('displayName', ''), 'tracked': False},
    )

    interest.el_participant = participant
    interest.save(update_fields=['el_participant'])
    log.info(
        'resolve_fundraising_url: linked EventInterest %s to participant %s (%s)',
        interest.pk, numeric_id, 'created' if created else 'existing',
    )


@shared_task
def retry_pending_url_resolutions():
    """
    Re-queue resolve_fundraising_url for any EventInterest records where:
    - fundraising_url is set
    - el_participant is not yet resolved
    This catches cases where the signal fired but the task failed or Celery was down.
    """
    from django.conf import settings

    from evtsignup.models import EventInterest
    max_attempts = getattr(settings, 'URL_RESOLUTION_MAX_ATTEMPTS', 3)
    pending = EventInterest.objects.filter(
        fundraising_url__isnull=False,
        el_participant__isnull=True,
        url_resolution_attempts__lt=max_attempts,
    ).exclude(fundraising_url='')
    count = pending.count()
    if count == 0:
        log.info('retry_pending_url_resolutions: nothing to retry')
        return
    log.info('retry_pending_url_resolutions: re-queuing %d records', count)
    for interest in pending:
        resolve_fundraising_url.delay(interest.pk)
