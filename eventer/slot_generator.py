"""
Slot template generator for Superstream events.

Generates EventSignupSlot records from an event's EventPeriod and EventSignupSlotConfig.
Slot groupings and per-role first-block offsets are defined via EventSlotGroup and
EventSlotGroupMembership - no role slugs are hardcoded here.
"""
import logging
import zoneinfo
from datetime import timedelta

from eventer.models import Event, EventSignupSlot, EventSignupSlotConfig, EventSlotGroup

log = logging.getLogger(__name__)


def _expand_to_hours(slot):
    """Yield each UTC hour datetime from slot.start up to (not including) slot.stop."""
    current = slot.start.replace(minute=0, second=0, microsecond=0)
    while current < slot.stop:
        yield current
        current += timedelta(hours=1)


def _format_label(start_local, stop_local):
    """Format a human-readable slot label, e.g. 'Friday 8pm - 11pm'."""
    def fmt_time(dt):
        return dt.strftime('%-I%p').lower()

    start_day = start_local.strftime('%A')
    stop_day = stop_local.strftime('%A')
    if start_day == stop_day:
        return f"{start_day} {fmt_time(start_local)} - {fmt_time(stop_local)}"
    return f"{start_day} {fmt_time(start_local)} - {stop_day} {fmt_time(stop_local)}"


def _variable_block_hours(local_dt, config):
    """Return block size based on whether local_dt falls in prime time."""
    t = local_dt.time()
    if config.prime_time_start <= t < config.prime_time_end:
        return config.prime_block_hours
    return config.standard_block_hours


def _generate_grid(event, tz, start, stop, config, group, roles):
    """
    Generate slots for one group, one role at a time.

    Roles with first_block_hours=None share slots with the first role in the group
    (same start/stop, just additional M2M entries). Roles with a first_block_hours
    value get their own grid sequence, naturally staggering their changeovers.

    Returns (created, skipped) counts.
    """
    block_hours = group.block_hours or config.management_block_hours

    created = skipped = 0

    # Separate roles into: shared (no offset) and staggered (have an offset)
    shared_roles = [m.role for m in roles if m.first_block_hours is None]
    staggered = [(m.role, m.first_block_hours) for m in roles if m.first_block_hours is not None]

    def _run_grid(role_list, first_override):
        nonlocal created, skipped
        current = start
        is_first = True
        while current < stop:
            local = current.astimezone(tz)
            if is_first and first_override is not None:
                hours = first_override
            elif group.use_prime_time:
                hours = _variable_block_hours(local, config)
            else:
                hours = block_hours
            is_first = False

            slot_stop = min(current + timedelta(hours=hours), stop)

            # Absorb a too-short trailing stub into this slot
            min_slot_hours = max(config.prime_block_hours, 2) if group.use_prime_time else 2
            remaining = stop - slot_stop
            if timedelta(0) < remaining < timedelta(hours=min_slot_hours):
                slot_stop = stop

            label = _format_label(local, slot_stop.astimezone(tz))
            slot, was_created = EventSignupSlot.objects.get_or_create(
                event=event, start=current, stop=slot_stop,
                defaults={'label': label},
            )
            if was_created:
                slot.roles.set(role_list)
                created += 1
            else:
                slot.roles.add(*role_list)
                skipped += 1

            current = slot_stop

    if shared_roles:
        _run_grid(shared_roles, None)

    for role, first_hours in staggered:
        _run_grid([role], first_hours)

    return created, skipped


def generate_slots(event: Event, replace: bool = False) -> dict:
    """
    Generate EventSignupSlot records for an event based on EventSlotGroup configuration.

    Args:
        event: The Event to generate slots for
        replace: If True, delete existing slot templates before generating

    Returns:
        dict with keys 'created', 'skipped', 'deleted'

    Raises:
        ValueError: if event has no periods or no slot groups are configured
    """
    if not event.eventperiod_set.exists():
        raise ValueError("Event has no periods. Add a period first.")

    groups = list(
        EventSlotGroup.objects.prefetch_related('memberships__role').all()
    )
    if not groups:
        raise ValueError("No EventSlotGroups configured. Create slot groups and assign roles first.")

    config, _ = EventSignupSlotConfig.objects.get_or_create(event=event)
    tz = zoneinfo.ZoneInfo(event.timezone)
    event_start = event.start
    event_stop = event.end

    deleted = 0
    if replace:
        deleted, _ = EventSignupSlot.objects.filter(event=event).delete()

    total_created = total_skipped = 0
    empty_groups = []

    for group in groups:
        memberships = list(group.memberships.select_related('role').all())
        if not memberships:
            log.warning('generate_slots: slot group %r has no role memberships, skipping', group.name)
            empty_groups.append(group.name)
            continue
        c, s = _generate_grid(event, tz, event_start, event_stop, config, group, memberships)
        total_created += c
        total_skipped += s

    result = {'created': total_created, 'skipped': total_skipped, 'deleted': deleted}
    if empty_groups:
        result['empty_groups'] = empty_groups
    return result
