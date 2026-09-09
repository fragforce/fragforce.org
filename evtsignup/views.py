import logging
import zoneinfo
from collections import defaultdict

from django.contrib import messages

log = logging.getLogger(__name__)
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from eventer.models import Event, EventRole, EventSignupSlot, Game
from eventer.slot_generator import _expand_to_hours
from evtsignup.models import EventAvailabilityHour, EventInterest, EventInterestNote, GameInterestUserEvent

SIGNUP_TEMPLATE = 'evtsignup/signup.html'


def _group_slots_by_day(slots_qs, tz):
    """Return an ordered list of (day_label, [slot, ...]) grouped by slot start day in tz."""
    groups = defaultdict(list)
    order = []
    for slot in slots_qs:
        local_start = slot.start.astimezone(tz)
        day_key = local_start.date()
        if day_key not in groups:
            order.append(day_key)
        groups[day_key].append(slot)
    return [(day.strftime('%A, %B %-d'), groups[day]) for day in order]


def _game_qs_for_role(role):
    """Return the approved/suggested game queryset for a role, filtered by game_min_players.
    Uses multiplayer_max_override when set (same logic as Game.effective_multiplayer_max)."""
    from django.db.models.functions import Coalesce
    qs = Game.objects.filter(status='approved', suggested=True)
    if role.game_min_players is not None:
        # Annotate with effective max (override takes precedence over IGDB value)
        # then exclude games where effective max is known and below the threshold
        qs = qs.annotate(
            effective_max=Coalesce('multiplayer_max_override', 'multiplayer_max')
        ).exclude(
            Q(effective_max__isnull=False) & Q(effective_max__lt=role.game_min_players)
        )
    return qs


def _build_hour_role_set(event, roles_with_slots, post_data):
    """Build a set of (hour, role) tuples from POST data. Field per role is '{slug}_slots'."""
    result = set()
    slot_cache = {s.pk: s for s in EventSignupSlot.objects.filter(event=event)}
    for role in roles_with_slots:
        for slot_id_str in post_data.getlist(f'{role.slug}_slots'):
            if not slot_id_str.isdigit():
                continue
            slot = slot_cache.get(int(slot_id_str))
            if slot is None:
                continue
            for hour in _expand_to_hours(slot):
                result.add((hour, role))
    return result


def _save_signup(request, event, roles_with_slots, game_qs_by_slug):
    """
    Validate and save a POST submission.
    Returns (interest, created, errors). On errors, interest/created are None.
    """
    display_name = request.POST.get('display_name', '').strip()
    preferences = request.POST.get('preferences', '').strip()
    acknowledged = bool(request.POST.get('acknowledged'))
    fundraising_url = request.POST.get('fundraising_url', '').strip() or None

    if not acknowledged:
        return None, None, ["You must acknowledge the Fragforce rules to sign up."]

    interest, created = EventInterest.objects.update_or_create(
        user=request.user,
        event=event,
        defaults={
            'display_name': display_name,
            'preferences': preferences,
            'acknowledged': acknowledged,
            'fundraising_url': fundraising_url,
        },
    )

    # Rebuild hourly availability
    interest.eventavailabilityhour_set.all().delete()
    hour_role_pairs = _build_hour_role_set(event, roles_with_slots, request.POST)
    EventAvailabilityHour.objects.bulk_create([
        EventAvailabilityHour(event_interest=interest, hour=hour, role=role)
        for hour, role in sorted(hour_role_pairs, key=lambda x: (x[0], x[1].slug))
    ])

    # Sync game selections - one row per (game, role)
    roles_by_slug = {r.slug: r for r in roles_with_slots}
    GameInterestUserEvent.objects.filter(event_interest=interest).delete()
    game_rows = []
    for slug, games_qs in game_qs_by_slug.items():
        role = roles_by_slug.get(slug)
        if role:
            for gid in games_qs.filter(pk__in=request.POST.getlist(f'{slug}_games')).values_list('pk', flat=True):
                game_rows.append(GameInterestUserEvent(event_interest=interest, game_id=gid, role=role))
    GameInterestUserEvent.objects.bulk_create(game_rows, ignore_conflicts=True)

    # Sync notes for roles with show_notes=True
    for role in roles_with_slots:
        if not role.show_notes:
            continue
        text = request.POST.get(f'{role.slug}_notes', '').strip()
        if text:
            EventInterestNote.objects.update_or_create(
                event_interest=interest, role=role,
                defaults={'notes': text},
            )
        else:
            EventInterestNote.objects.filter(event_interest=interest, role=role).delete()

    return interest, created, []


def _prefill_from_post(request, roles_with_slots, game_qs_by_slug):
    """Build prefill and selected dicts from a POST request (used after validation failure)."""
    prefill = {
        'display_name': request.POST.get('display_name', ''),
        'preferences': request.POST.get('preferences', ''),
        'acknowledged': bool(request.POST.get('acknowledged')),
        'fundraising_url': request.POST.get('fundraising_url', ''),
    }
    notes_by_slug = {
        role.slug: request.POST.get(f'{role.slug}_notes', '')
        for role in roles_with_slots if role.show_notes
    }
    selected_slot_ids = {
        role.slug: {int(x) for x in request.POST.getlist(f'{role.slug}_slots') if x.isdigit()}
        for role in roles_with_slots
    }
    selected_game_ids = {
        slug: {int(x) for x in request.POST.getlist(f'{slug}_games') if x.isdigit()}
        for slug in game_qs_by_slug
    }
    return prefill, selected_slot_ids, selected_game_ids, notes_by_slug


def _prefill_from_existing(existing, slots_by_slug, game_qs_by_slug):
    """Build prefill and selected dicts from a saved EventInterest."""
    prefill = {
        'display_name': existing.display_name,
        'preferences': existing.preferences,
        'acknowledged': existing.acknowledged,
        'fundraising_url': existing.fundraising_url or '',
    }

    notes_by_slug = {
        n.role.slug: n.notes
        for n in existing.eventinterestnote_set.select_related('role').all()
    }

    hours_by_slug = defaultdict(set)
    for hour, slug in existing.eventavailabilityhour_set.values_list('hour', 'role__slug'):
        hours_by_slug[slug].add(hour)

    inactive_role_slugs = set(hours_by_slug.keys()) - set(slots_by_slug.keys())
    if inactive_role_slugs:
        log.warning(
            'signup prefill: user %s has saved availability for roles with no active slots: %s',
            existing.user_id, sorted(inactive_role_slugs),
        )

    selected_slot_ids = {
        slug: {
            slot.pk for slot in slots
            if all(h in hours_by_slug.get(slug, set()) for h in _expand_to_hours(slot))
        }
        for slug, slots in slots_by_slug.items()
    }

    # Fetch all game selections in one query then partition by slug
    game_selections_by_slug = defaultdict(set)
    for slug, game_id in existing.gameinterestuserevent_set.filter(
        role__slug__in=list(game_qs_by_slug.keys())
    ).values_list('role__slug', 'game_id'):
        game_selections_by_slug[slug].add(game_id)
    selected_game_ids = {
        slug: game_selections_by_slug[slug] & set(games_qs.values_list('pk', flat=True))
        for slug, games_qs in game_qs_by_slug.items()
    }

    return prefill, selected_slot_ids, selected_game_ids, notes_by_slug, inactive_role_slugs


@login_required
@require_http_methods(["GET", "POST"])
def signup_view(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)

    is_locked = event.locked
    existing = EventInterest.objects.filter(user=request.user, event=event).first()
    can_signup = event.signups_open and not is_locked
    can_edit = event.edits_open and not is_locked

    if existing and (is_locked or not can_edit):
        if request.method == 'POST':
            existing.display_name = request.POST.get('display_name', '').strip()
            existing.fundraising_url = request.POST.get('fundraising_url', '').strip() or None
            existing.save(update_fields=['display_name', 'fundraising_url'])
            messages.success(request, "Your profile has been updated.")
            return redirect('evtsignup-signup', event_slug=event_slug)
        return render(request, SIGNUP_TEMPLATE, {
            'event': event,
            'locked': is_locked,
            'profile_only': True,
            'existing': existing,
            'prefill': {
                'display_name': existing.display_name,
                'fundraising_url': existing.fundraising_url or '',
            },
        })

    if not existing and is_locked:
        return render(request, SIGNUP_TEMPLATE, {'event': event, 'locked': True})

    slots = EventSignupSlot.objects.filter(event=event).prefetch_related('roles').order_by('start')
    if not slots.exists():
        can_signup = False

    if not existing and not can_signup:
        return render(request, SIGNUP_TEMPLATE, {
            'event': event, 'locked': False, 'signups_closed': True,
        })

    tz = zoneinfo.ZoneInfo(event.timezone)

    # Only include roles that have slots on this event, preserving display_order
    all_roles = list(EventRole.objects.all())
    slot_role_ids = set(slots.values_list('roles', flat=True))
    roles_with_slots = [r for r in all_roles if r.pk in slot_role_ids]
    slots_by_slug = {r.slug: slots.filter(roles=r) for r in roles_with_slots}

    # Game querysets for roles that have game selection enabled
    game_qs_by_slug = {}
    for role in roles_with_slots:
        if not role.has_game_selection:
            continue
        qs = _game_qs_for_role(role)
        if existing:
            linked_ids = existing.gameinterestuserevent_set.filter(role=role).values_list('game_id', flat=True)
            qs = (qs | Game.objects.filter(pk__in=linked_ids).exclude(status='rejected')).distinct()
        game_qs_by_slug[role.slug] = qs.order_by('name')

    errors = []

    if request.method == 'POST':
        _, created, errors = _save_signup(request, event, roles_with_slots, game_qs_by_slug)
        if not errors:
            if created:
                messages.success(request, "Your signup has been received!")
            else:
                messages.success(request, "Your signup has been updated.")
            return redirect('evtsignup-signup', event_slug=event_slug)

    if errors:
        prefill, selected_slot_ids, selected_game_ids, notes_by_slug = _prefill_from_post(request, roles_with_slots, game_qs_by_slug)
    elif existing:
        prefill, selected_slot_ids, selected_game_ids, notes_by_slug, inactive_role_slugs = _prefill_from_existing(existing, slots_by_slug, game_qs_by_slug)
        if inactive_role_slugs:
            messages.warning(
                request,
                "Some of your previously saved availability could not be loaded because those roles "
                "no longer have slots for this event. Please review your availability before saving.",
            )
    else:
        prefill = {}
        selected_slot_ids = {r.slug: set() for r in roles_with_slots}
        selected_game_ids = {slug: set() for slug in game_qs_by_slug}
        notes_by_slug = {}

    # Build per-role context list for template, preserving display_order
    role_tracks = []
    for role in roles_with_slots:
        slug = role.slug
        role_tracks.append({
            'role': role,
            'slug': slug,
            'slot_days': _group_slots_by_day(slots_by_slug[slug], tz),
            'slots': slots_by_slug[slug],
            'selected_slot_ids': selected_slot_ids.get(slug, set()),
            'games': game_qs_by_slug.get(slug),
            'selected_game_ids': selected_game_ids.get(slug, set()),
            'notes_prefill': notes_by_slug.get(slug, ''),
            'is_active': bool(
                selected_slot_ids.get(slug) or
                selected_game_ids.get(slug) or
                (role.show_fundraising_url and prefill.get('fundraising_url'))
            ),
        })

    context = {
        'event': event,
        'existing': existing,
        'errors': errors,
        'prefill': prefill,
        'role_tracks': role_tracks,
    }
    return render(request, SIGNUP_TEMPLATE, context)
