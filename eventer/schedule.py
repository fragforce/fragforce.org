"""
Shared schedule grid building utilities used by both admin views and public/coordinator views.
"""
import logging
import zoneinfo
from datetime import timedelta

from eventer.models import EventRole, EventScheduleAssignment, EventScheduleMultiAssignment
from eventer.slot_generator import _expand_to_hours

log = logging.getLogger(__name__)

LOCAL_TIME_FMT = '%a %b %-d %-I%p %Z'


def _event_all_hours(event_start, event_end):
    hours = []
    cur = event_start.replace(minute=0, second=0, microsecond=0)
    while cur < event_end:
        hours.append(cur)
        cur += timedelta(hours=1)
    return hours


def _build_hour_role_users(event, all_hours, all_roles):
    from evtsignup.models import EventInterest
    all_slugs = [r.slug for r in all_roles]
    hour_role_users = {h: {slug: set() for slug in all_slugs} for h in all_hours}
    interests = (
        EventInterest.objects
        .filter(event=event)
        .select_related('user')
        .prefetch_related('eventavailabilityhour_set__role')
    )
    for interest in interests:
        for avail in interest.eventavailabilityhour_set.all():
            if avail.hour not in hour_role_users:
                continue
            if avail.role.slug not in hour_role_users[avail.hour]:
                log.warning(
                    'schedule: skipping availability for user %s at hour %s — role %r has no active slots for event %s',
                    interest.user_id, avail.hour, avail.role.slug, event.pk,
                )
                continue
            hour_role_users[avail.hour][avail.role.slug].add(interest.user)
    return hour_role_users


def _build_role_hour_slot(event, all_roles):
    all_slugs = {r.slug for r in all_roles}
    role_hour_slot = {slug: {} for slug in all_slugs}
    for slot in event.signup_slots.prefetch_related('roles').order_by('start'):
        for role in slot.roles.all():
            if role.slug in role_hour_slot:
                for hour in _expand_to_hours(slot):
                    role_hour_slot[role.slug][hour] = slot
    return role_hour_slot


def _build_slot_role_data(all_hours, single_roles, role_hour_slot, hour_role_users, role_objects):
    slot_role_available = {}
    slot_role_assigned = {}
    seen = set()
    for role in single_roles:
        slug = role.slug
        for hour in all_hours:
            slot = role_hour_slot[slug].get(hour)
            if not slot or (slot.pk, slug) in seen:
                continue
            seen.add((slot.pk, slug))
            available = None
            for sh in _expand_to_hours(slot):
                users = hour_role_users.get(sh, {}).get(slug, set())
                available = users if available is None else available & users
            role_obj = role_objects.get(slug)
            assigned = EventScheduleAssignment.objects.filter(
                slot=slot, role=role_obj
            ).select_related('user').first() if role_obj else None
            slot_role_available[(slot.pk, slug)] = sorted(available or [], key=lambda u: u.username)
            slot_role_assigned[(slot.pk, slug)] = assigned
    return slot_role_available, slot_role_assigned


def _build_grid_rows(
        all_hours,
        tz,
        single_roles,
        role_hour_slot,
        role_objects,
        slot_role_available,
        slot_role_assigned
        ):
    role_next_hour = {r.slug: None for r in single_roles}
    role_alt = {r.slug: False for r in single_roles}
    rows = []
    for hour in all_hours:
        local_hour = hour.astimezone(tz)
        is_day_start = hour == all_hours[0] or local_hour.hour == 0
        cells = []
        for role in single_roles:
            slug = role.slug
            slot = role_hour_slot[slug].get(hour)
            if slot is None:
                cells.append({'type': 'empty', 'show_stream_commands': role.show_stream_commands})
            elif role_next_hour[slug] is not None and hour < role_next_hour[slug]:
                cells.append({'type': 'skip', 'show_stream_commands': role.show_stream_commands})
            else:
                slot_hours = list(_expand_to_hours(slot))
                role_next_hour[slug] = slot_hours[-1] + timedelta(hours=1) if slot_hours else hour + timedelta(hours=1)
                role_obj = role_objects.get(slug)
                role_alt[slug] = not role_alt[slug]
                cells.append({
                    'type': 'slot', 'rowspan': len(slot_hours),
                    'slot': slot, 'role_slug': slug,
                    'role_color': role_obj.color if role_obj else '#417690',
                    'show_stream_commands': role_obj.show_stream_commands if role_obj else False,
                    'alt': role_alt[slug],
                    'available': slot_role_available.get((slot.pk, slug), []),
                    'assigned': slot_role_assigned.get((slot.pk, slug)),
                })
        rows.append({
            'hour': hour,
            'local': local_hour.strftime('%-I%p'),
            'day': local_hour.strftime('%a %b %-d'),
            'is_day_start': is_day_start,
            'cells': cells,
        })
    return rows


def _build_multi_slot_data(event, all_hours, multi_roles, role_hour_slot, hour_role_users, role_objects):
    """Build available/assigned data for multi-assignment roles (e.g. Participant)."""
    data = {}
    seen = set()
    for role in multi_roles:
        slug = role.slug
        for hour in all_hours:
            slot = role_hour_slot.get(slug, {}).get(hour)
            if not slot or (slot.pk, slug) in seen:
                continue
            seen.add((slot.pk, slug))
            available = None
            for sh in _expand_to_hours(slot):
                users = hour_role_users.get(sh, {}).get(slug, set())
                available = users if available is None else available & users
            role_obj = role_objects.get(slug)
            assigned = list(EventScheduleMultiAssignment.objects.filter(
                slot=slot, role=role_obj
            ).select_related('user')) if role_obj else []
            data[(slot.pk, slug)] = {
                'available': sorted(available or [], key=lambda u: u.username),
                'assigned': assigned,
            }
    return data


def slot_hour_range(event_start, slot):
    """Return (start_hour, end_hour) 1-indexed relative to event start."""
    start_hour = int((slot.start - event_start).total_seconds() // 3600) + 1
    end_hour = int((slot.stop - event_start).total_seconds() // 3600)
    return start_hour, end_hour


def generate_twitch_commands(event, slot, streamer_display_name, game_name):
    """Generate the three Twitch bot command strings for a streamer slot."""
    if event.start:
        h_start, h_end = slot_hour_range(event.start, slot)
        hour_str = f'Hours {h_start}-{h_end}'
    else:
        hour_str = slot.label

    title_cmd = f'!settitle {event.name} | {hour_str}'
    game_cmd = f'!setgame {game_name}' if game_name else ''
    donate_cmd = f'!setteam {streamer_display_name}' if streamer_display_name else ''
    return title_cmd, game_cmd, donate_cmd


def build_schedule_grid(event):
    """
    Build hourly grid data structure for schedule views.
    Used by admin (availability summary, build schedule) and public coordinator view.
    """
    tz = zoneinfo.ZoneInfo(event.timezone)
    all_roles = list(EventRole.objects.all())  # ordered by display_order, name
    single_roles = [r for r in all_roles if not r.multi_assign]
    multi_roles = [r for r in all_roles if r.multi_assign]

    if not event.start or not event.end:
        return {
            'rows': [],
            'role_headers': [{
                'label': r.name,
                'color': r.color,
                'slug': r.slug,
                'show_stream_commands': r.show_stream_commands
                } for r in single_roles],
            'multi_role_headers': [{'label': r.name, 'color': r.color, 'slug': r.slug} for r in multi_roles],
            'slot_role_available': {}, 'slot_role_assigned': {},
            'multi_slot_data': {}, 'role_objects': {},
        }

    all_hours = _event_all_hours(event.start, event.end)
    role_objects = {r.slug: r for r in all_roles}
    hour_role_users = _build_hour_role_users(event, all_hours, all_roles)
    role_hour_slot = _build_role_hour_slot(event, all_roles)
    slot_role_available, slot_role_assigned = _build_slot_role_data(
        all_hours, single_roles, role_hour_slot, hour_role_users, role_objects
    )
    multi_slot_data = _build_multi_slot_data(
        event, all_hours, multi_roles, role_hour_slot, hour_role_users, role_objects
    )
    rows = _build_grid_rows(
        all_hours,
        tz,
        single_roles,
        role_hour_slot,
        role_objects,
        slot_role_available,
        slot_role_assigned
        )
    role_headers = [
        {'label': r.name, 'color': r.color, 'slug': r.slug, 'show_stream_commands': r.show_stream_commands}
        for r in single_roles
    ]
    multi_role_headers = [
        {'label': r.name, 'color': r.color, 'slug': r.slug}
        for r in multi_roles
    ]
    # Attach multi-assignment data and compute rowspan in a single pass
    multi_next_hour = {r.slug: None for r in multi_roles}
    multi_alt = {r.slug: False for r in multi_roles}
    for row in rows:
        multi_cells = {}
        for role in multi_roles:
            slug = role.slug
            slot = role_hour_slot.get(slug, {}).get(row['hour'])
            if slot is None:
                multi_cells[slug] = {'type': 'empty'}
            elif multi_next_hour[slug] is not None and row['hour'] < multi_next_hour[slug]:
                multi_cells[slug] = {'type': 'skip'}
            else:
                key = (slot.pk, slug)
                slot_hours = list(_expand_to_hours(slot))
                multi_next_hour[slug] = (
                    slot_hours[-1] + timedelta(hours=1) if slot_hours
                    else row['hour'] + timedelta(hours=1)
                    )
                multi_alt[slug] = not multi_alt[slug]
                multi_cells[slug] = {
                    'type': 'slot',
                    'slot': slot,
                    'role_slug': slug,
                    'role_color': role.color,
                    'rowspan': len(slot_hours),
                    'alt': multi_alt[slug],
                    'available': multi_slot_data.get(key, {}).get('available', []),
                    'assigned': multi_slot_data.get(key, {}).get('assigned', []),
                }
        row['multi_cells_list'] = [multi_cells.get(r.slug, {'type': 'empty'}) for r in multi_roles]

    return {
        'rows': rows, 'role_headers': role_headers,
        'multi_role_headers': multi_role_headers,
        'slot_role_available': slot_role_available,
        'slot_role_assigned': slot_role_assigned,
        'multi_slot_data': multi_slot_data,
        'role_objects': role_objects,
    }
