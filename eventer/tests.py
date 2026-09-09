import zoneinfo
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.contrib.auth.models import User
from django.test import TestCase

from eventer.models import (
    HOUR_SECONDS,
    Event,
    EventPeriod,
    EventRole,
    EventSignupSlot,
    EventSignupSlotConfig,
    EventSlotGroup,
    EventSlotGroupMembership,
)
from eventer.schedule import (
    _event_all_hours,
    build_schedule_grid,
    generate_twitch_commands,
    slot_hour_range,
)
from eventer.slot_generator import _expand_to_hours, _format_label, _variable_block_hours, generate_slots


def dt(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=dt_timezone.utc)


class EventStartEndTest(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name='Test Event', slug='test-event', description='')

    def test_start_returns_none_with_no_periods(self):
        self.assertIsNone(self.event.start)

    def test_end_returns_none_with_no_periods(self):
        self.assertIsNone(self.event.end)

    def test_start_returns_period_start_for_single_period(self):
        start = dt(2025, 4, 4, 8)
        stop = dt(2025, 4, 6)
        EventPeriod.objects.create(event=self.event, start=start, stop=stop)

        self.assertEqual(self.event.start, start)

    def test_end_returns_period_stop_for_single_period(self):
        start = dt(2025, 4, 4, 8)
        stop = dt(2025, 4, 6)
        EventPeriod.objects.create(event=self.event, start=start, stop=stop)

        self.assertEqual(self.event.end, stop)

    def test_start_returns_earliest_with_multiple_periods(self):
        early = dt(2025, 4, 4, 8)
        late = dt(2025, 4, 5, 8)
        EventPeriod.objects.create(event=self.event, start=late, stop=dt(2025, 4, 5, 20))
        EventPeriod.objects.create(event=self.event, start=early, stop=dt(2025, 4, 4, 20))

        self.assertEqual(self.event.start, early)

    def test_end_returns_latest_with_multiple_periods(self):
        early_stop = dt(2025, 4, 4, 20)
        late_stop = dt(2025, 4, 6)
        EventPeriod.objects.create(event=self.event, start=dt(2025, 4, 4, 8), stop=early_stop)
        EventPeriod.objects.create(event=self.event, start=dt(2025, 4, 5, 8), stop=late_stop)

        self.assertEqual(self.event.end, late_stop)



class SetupSuperstreamViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')
        self.event = Event.objects.create(name='Test Event', slug='test-event', description='')

    def _url(self):
        return f'/admin/eventer/event/{self.event.pk}/setup-superstream/'

    def test_get_renders_form(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Superstream Period')

    def test_post_creates_event_period_edt(self):
        # April 4 2025 is in EDT (UTC-4) - 8am EDT = 12:00 UTC
        response = self.client.post(self._url(), {
            'start': '2025-04-04T08:00',
            'duration': '40',
        })
        self.assertRedirects(
            response,
            f'/admin/eventer/event/{self.event.pk}/generate-slots/',
            fetch_redirect_response=False
            )
        self.assertEqual(EventPeriod.objects.filter(event=self.event).count(), 1)
        period = EventPeriod.objects.get(event=self.event)
        self.assertEqual(period.start.hour, 12)  # 8am EDT (UTC-4) = 12:00 UTC

    def test_post_creates_event_period_est(self):
        # January 10 2025 is in EST (UTC-5) - 8am EST = 13:00 UTC
        response = self.client.post(self._url(), {
            'start': '2025-01-10T08:00',
            'duration': '40',
        })
        self.assertRedirects(
            response,
            f'/admin/eventer/event/{self.event.pk}/generate-slots/',
            fetch_redirect_response=False
            )
        period = EventPeriod.objects.get(event=self.event)
        self.assertEqual(period.start.hour, 13)  # 8am EST (UTC-5) = 13:00 UTC

    def test_post_creates_event_period_pacific_timezone(self):
        # Event in Pacific time - April 4 2025 is PDT (UTC-7) - 8am PDT = 15:00 UTC
        pacific_event = Event.objects.create(
            name='Pacific Event', slug='pacific-event', description='',
            timezone='America/Los_Angeles'
        )
        response = self.client.post(
            f'/admin/eventer/event/{pacific_event.pk}/setup-superstream/',
            {'start': '2025-04-04T08:00', 'duration': '40'},
        )
        self.assertRedirects(
            response,
            f'/admin/eventer/event/{pacific_event.pk}/generate-slots/',
            fetch_redirect_response=False
            )
        period = EventPeriod.objects.get(event=pacific_event)
        self.assertEqual(period.start.hour, 15)  # 8am PDT (UTC-7) = 15:00 UTC

    def test_post_creates_event_period_utc_timezone(self):
        # Event in UTC - 8am UTC = 8:00 UTC, no DST
        utc_event = Event.objects.create(
            name='UTC Event', slug='utc-event', description='',
            timezone='UTC'
        )
        response = self.client.post(
            f'/admin/eventer/event/{utc_event.pk}/setup-superstream/',
            {'start': '2025-04-04T08:00', 'duration': '40'},
        )
        self.assertRedirects(
            response,
            f'/admin/eventer/event/{utc_event.pk}/generate-slots/',
            fetch_redirect_response=False
            )
        period = EventPeriod.objects.get(event=utc_event)
        self.assertEqual(period.start.hour, 8)  # 8am UTC = 8:00 UTC

    def test_post_with_invalid_duration_shows_error(self):
        response = self.client.post(self._url(), {
            'start': '2025-04-04T08:00',
            'duration': '-1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Duration must be at least 1 hour')
        self.assertEqual(EventPeriod.objects.filter(event=self.event).count(), 0)

    def test_get_shows_existing_periods(self):
        start = datetime(2025, 4, 4, 12, 0, tzinfo=dt_timezone.utc)
        EventPeriod.objects.create(event=self.event, start=start, stop=start + timedelta(hours=40))
        response = self.client.get(self._url())
        self.assertContains(response, 'already has 1 period')


def _local(year, month, day, hour, tz_name='America/New_York'):
    tz = zoneinfo.ZoneInfo(tz_name)
    return datetime(year, month, day, hour, tzinfo=dt_timezone.utc).astimezone(tz)


def _seed_roles():
    for slug, name in [
        ('participant', 'Participant'),
        ('streamer', 'Streamer'),
        ('moderator', 'Moderator'),
        ('tech-manager', 'Tech Manager'),
    ]:
        EventRole.objects.get_or_create(slug=slug, defaults={'name': name, 'description': ''})


class FormatLabelTest(TestCase):
    def test_same_day(self):
        # Fri Apr 4 2025: 12 UTC = 8am EDT, 15 UTC = 11am EDT
        self.assertEqual(_format_label(_local(2025, 4, 4, 12), _local(2025, 4, 4, 15)), 'Friday 8am - 11am')

    def test_crosses_midnight(self):
        # Fri 11pm EDT = Sat 3 UTC, Sat 2am EDT = Sat 6 UTC
        self.assertEqual(
            _format_label(_local(2025, 4, 5, 3), _local(2025, 4, 5, 6)),
            'Friday 11pm - Saturday 2am'
        )


class VariableBlockHoursTest(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name='Test', slug='test', description='')
        self.config = EventSignupSlotConfig.objects.create(event=self.event)

    def test_standard_block_outside_prime(self):
        # 8am EDT = 12 UTC - outside prime time (2pm-9pm ET)
        local = _local(2025, 4, 4, 12)
        self.assertEqual(_variable_block_hours(local, self.config), self.config.standard_block_hours)

    def test_prime_block_during_prime(self):
        # 3pm EDT = 19 UTC - inside prime time
        local = _local(2025, 4, 4, 19)
        self.assertEqual(_variable_block_hours(local, self.config), self.config.prime_block_hours)

    def test_prime_start_boundary(self):
        # 2pm EDT = 18 UTC - at prime_time_start, should be prime
        local = _local(2025, 4, 4, 18)
        self.assertEqual(_variable_block_hours(local, self.config), self.config.prime_block_hours)

    def test_prime_end_boundary(self):
        # 9pm EDT = 01 UTC next day - at prime_time_end, should be standard
        local = _local(2025, 4, 5, 1)
        self.assertEqual(_variable_block_hours(local, self.config), self.config.standard_block_hours)


class GenerateSlotsTest(TestCase):
    def setUp(self):
        _seed_roles()
        self.event = Event.objects.create(
            name='Test Superstream', slug='test-superstream', description='',
            timezone='America/New_York',
        )
        # 40hr event: Fri Apr 4 8am EDT (12 UTC) → Sun Apr 6 12am EDT (04 UTC)
        EventPeriod.objects.create(
            event=self.event,
            start=datetime(2025, 4, 4, 12, 0, tzinfo=dt_timezone.utc),
            stop=datetime(2025, 4, 6, 4, 0, tzinfo=dt_timezone.utc),
        )

    def _config(self):
        config, _ = EventSignupSlotConfig.objects.get_or_create(event=self.event)
        return config

    def test_raises_without_periods(self):
        event = Event.objects.create(name='No Period', slug='no-period', description='')
        with self.assertRaises(ValueError):
            generate_slots(event)

    def test_raises_without_groups(self):
        from eventer.models import EventSlotGroup
        EventSlotGroup.objects.all().delete()
        with self.assertRaises(ValueError):
            generate_slots(self.event)

    def test_creates_slots(self):
        result = generate_slots(self.event)
        self.assertGreater(result['created'], 0)
        self.assertEqual(result['deleted'], 0)
        self.assertGreaterEqual(result['skipped'], 0)

    def test_roles_without_offset_in_same_group_share_slots(self):
        from eventer.models import EventSlotGroup
        generate_slots(self.event)
        # All roles in the prime-time group with no first_block_hours should share identical slot sets
        prime_group = EventSlotGroup.objects.get(use_prime_time=True)
        shared_roles = [m.role for m in prime_group.memberships.filter(first_block_hours__isnull=True)]
        if len(shared_roles) < 2:
            return
        first_slots = set(EventSignupSlot.objects.filter(
            event=self.event,
            roles=shared_roles[0]).values_list(
                'id',
                flat=True
                )
            )
        for role in shared_roles[1:]:
            role_slots = set(EventSignupSlot.objects.filter(event=self.event, roles=role).values_list('id', flat=True))
            self.assertEqual(first_slots, role_slots)

    def test_management_group_uses_uniform_block_size(self):
        from eventer.models import EventSlotGroup
        generate_slots(self.event)
        config = self._config()
        # Any management group with no block_hours override should use config.management_block_hours
        mgmt_groups = EventSlotGroup.objects.filter(use_prime_time=False, block_hours__isnull=True)
        for group in mgmt_groups:
            for membership in group.memberships.filter(first_block_hours__isnull=True).select_related('role'):
                slots = list(EventSignupSlot.objects.filter(event=self.event, roles=membership.role).order_by('start'))
                for slot in slots[:-1]:
                    duration_hrs = (slot.stop - slot.start).total_seconds() / HOUR_SECONDS
                    self.assertEqual(duration_hrs, config.management_block_hours)

    def test_role_with_first_block_offset_uses_that_value(self):
        from eventer.models import EventSlotGroupMembership
        generate_slots(self.event)
        # Any membership with first_block_hours set should have that as the first slot's duration
        for membership in EventSlotGroupMembership.objects.filter(
            first_block_hours__isnull=False
            ).select_related('role'):
            first_slot = EventSignupSlot.objects.filter(
                event=self.event,
                roles=membership.role).order_by('start').first()
            if first_slot:
                duration_hrs = (first_slot.stop - first_slot.start).total_seconds() / HOUR_SECONDS
                self.assertEqual(duration_hrs, membership.first_block_hours)

    def test_prime_time_slots_use_prime_block_hours(self):
        generate_slots(self.event)
        config = self._config()
        tz = zoneinfo.ZoneInfo(self.event.timezone)
        participant = EventRole.objects.get(slug='participant')
        for slot in EventSignupSlot.objects.filter(event=self.event, roles=participant):
            local_start = slot.start.astimezone(tz)
            t = local_start.time()
            if config.prime_time_start <= t < config.prime_time_end:
                duration_hrs = (slot.stop - slot.start).total_seconds() / HOUR_SECONDS
                self.assertEqual(
                    duration_hrs,
                    config.prime_block_hours,
                    f"Prime-time slot {slot.label} should be {config.prime_block_hours}hr"
                    )

    def test_non_prime_slots_use_standard_block_hours(self):
        generate_slots(self.event)
        config = self._config()
        tz = zoneinfo.ZoneInfo(self.event.timezone)
        participant = EventRole.objects.get(slug='participant')
        slots = list(EventSignupSlot.objects.filter(event=self.event, roles=participant).order_by('start'))
        for slot in slots[:-1]:  # skip last slot (may be absorbed)
            local_start = slot.start.astimezone(tz)
            t = local_start.time()
            if not (config.prime_time_start <= t < config.prime_time_end):
                duration_hrs = (slot.stop - slot.start).total_seconds() / HOUR_SECONDS
                self.assertEqual(
                    duration_hrs,
                    config.standard_block_hours,
                    f"Non-prime slot {slot.label} should be {config.standard_block_hours}hr"
                    )

    def test_no_stub_slots_shorter_than_min(self):
        generate_slots(self.event)
        config = self._config()
        min_hours = max(config.prime_block_hours, 2)
        for slot in EventSignupSlot.objects.filter(event=self.event):
            duration_hrs = (slot.stop - slot.start).total_seconds() / HOUR_SECONDS
            self.assertGreaterEqual(duration_hrs, min_hours, f"Slot {slot.label} is too short: {duration_hrs}hr")

    def test_replace_deletes_existing_and_regenerates(self):
        generate_slots(self.event)
        first_count = EventSignupSlot.objects.filter(event=self.event).count()
        result = generate_slots(self.event, replace=True)
        self.assertGreater(result['deleted'], 0)
        self.assertEqual(EventSignupSlot.objects.filter(event=self.event).count(), first_count)

    def test_idempotent_without_replace(self):
        generate_slots(self.event)
        first_count = EventSignupSlot.objects.filter(event=self.event).count()
        result = generate_slots(self.event, replace=False)
        self.assertEqual(result['created'], 0)
        self.assertEqual(EventSignupSlot.objects.filter(event=self.event).count(), first_count)


class EventAdminListTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')
        self.event_with_period = Event.objects.create(
            name='Scheduled Event', slug='scheduled-event', description='',
            timezone='America/New_York',
        )
        EventPeriod.objects.create(
            event=self.event_with_period,
            start=datetime(2025, 4, 4, 12, 0, tzinfo=dt_timezone.utc),
            stop=datetime(2025, 4, 6, 4, 0, tzinfo=dt_timezone.utc),
        )
        self.event_no_period = Event.objects.create(
            name='Unscheduled Event', slug='unscheduled-event', description='',
        )

    def _url(self):
        return '/admin/eventer/event/'

    def test_has_period_filter_returns_scheduled_events(self):
        response = self.client.get(self._url(), {'has_period': 'yes'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Scheduled Event')
        self.assertNotContains(response, 'Unscheduled Event')

    def test_no_period_filter_returns_unscheduled_events(self):
        response = self.client.get(self._url(), {'has_period': 'no'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Unscheduled Event')
        self.assertNotContains(response, 'Scheduled Event')

    def test_event_start_shows_dash_when_no_period(self):
        response = self.client.get(self._url())
        self.assertContains(response, 'Unscheduled Event')
        # The event_start column should show '-' for events with no period
        self.assertContains(response, '<td class="field-event_start">-</td>')

    def test_event_start_shows_local_time_when_period_exists(self):
        response = self.client.get(self._url())
        # 12:00 UTC on April 4 2025 = 8am EDT
        self.assertContains(response, '2025-04-04 08:00 EDT')


class EventAdminCreateFlowTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')

    def test_create_event_redirects_to_slot_config_add(self):
        response = self.client.post('/admin/eventer/event/add/', {
            'name': 'New Event',
            'slug': 'new-event',
            'description': 'A new event',
            'timezone': 'America/New_York',
            'signups_open': False,
            'edits_open': False,
            'locked': False,
            '_save': '1',
        })
        self.assertEqual(response.status_code, 302)
        event = Event.objects.get(slug='new-event')
        self.assertIn(f'eventsignupslotconfig/add/?event={event.pk}', response['Location'])

    def test_create_slot_config_redirects_to_setup_superstream(self):
        event = Event.objects.create(name='Flow Event', slug='flow-event', description='')
        response = self.client.post('/admin/eventer/eventsignupslotconfig/add/', {
            'event': event.pk,
            'standard_block_hours': 3,
            'prime_block_hours': 2,
            'prime_time_start': '14:00:00',
            'prime_time_end': '21:00:00',
            'management_block_hours': 6,
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'event/{event.pk}/setup-superstream/', response['Location'])

    def test_setup_superstream_redirects_to_generate_slots(self):
        event = Event.objects.create(name='Flow Event 2', slug='flow-event-2', description='')
        response = self.client.post(
            f'/admin/eventer/event/{event.pk}/setup-superstream/',
            {'start': '2025-04-04T08:00', 'duration': '40'},
        )
        self.assertRedirects(
            response,
            f'/admin/eventer/event/{event.pk}/generate-slots/',
            fetch_redirect_response=False,
        )


class EventListViewTest(TestCase):
    def setUp(self):
        self.now = datetime(2025, 4, 4, 12, 0, tzinfo=dt_timezone.utc)

    def _make_event(self, name, slug, public=True, stop_offset_hours=48):
        event = Event.objects.create(name=name, slug=slug, description='A test event', public=public)
        EventPeriod.objects.create(
            event=event,
            start=self.now,
            stop=self.now + timedelta(hours=stop_offset_hours),
        )
        return event

    def test_lists_public_upcoming_events(self):
        from unittest.mock import patch
        self._make_event('Public Event', 'public-event')
        with patch('django.utils.timezone.now', return_value=self.now):
            response = self.client.get('/events/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Event')

    def test_excludes_non_public_events(self):
        from unittest.mock import patch
        self._make_event('Private Event', 'private-event', public=False)
        with patch('django.utils.timezone.now', return_value=self.now):
            response = self.client.get('/events/')
        self.assertNotContains(response, 'Private Event')

    def test_excludes_past_events(self):
        from unittest.mock import patch
        self._make_event('Past Event', 'past-event', stop_offset_hours=-1)
        future = self.now + timedelta(hours=2)
        with patch('django.utils.timezone.now', return_value=future):
            response = self.client.get('/events/')
        self.assertNotContains(response, 'Past Event')

    def test_empty_state_shown_when_no_events(self):
        from unittest.mock import patch
        with patch('django.utils.timezone.now', return_value=self.now):
            response = self.client.get('/events/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No upcoming events')


class EventDetailViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tester', 'tester@example.com', 'pass')
        self.event = Event.objects.create(
            name='Detail Event', slug='detail-event', description='An event',
            public=True, signups_open=True, edits_open=True,
        )
        EventPeriod.objects.create(
            event=self.event,
            start=datetime(2025, 4, 4, 12, tzinfo=dt_timezone.utc),
            stop=datetime(2025, 4, 6, 4, tzinfo=dt_timezone.utc),
        )

    def test_detail_returns_200(self):
        response = self.client.get(f'/events/{self.event.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detail Event')

    def test_non_public_event_detail_still_accessible(self):
        self.event.public = False
        self.event.save()
        response = self.client.get(f'/events/{self.event.slug}/')
        self.assertEqual(response.status_code, 200)

    def test_404_for_unknown_slug(self):
        response = self.client.get('/events/does-not-exist/')
        self.assertEqual(response.status_code, 404)

    def test_signup_link_shown_when_signups_open_and_no_existing_signup(self):
        self.client.login(username='tester', password='pass')
        response = self.client.get(f'/events/{self.event.slug}/')
        self.assertTrue(response.context['show_signup_link'])
        self.assertFalse(response.context['show_edit_link'])

    def test_edit_link_shown_when_edits_open_and_existing_signup(self):
        from evtsignup.models import EventInterest
        self.client.login(username='tester', password='pass')
        EventInterest.objects.create(user=self.user, event=self.event, acknowledged=True)
        response = self.client.get(f'/events/{self.event.slug}/')
        self.assertFalse(response.context['show_signup_link'])
        self.assertTrue(response.context['show_edit_link'])

    def test_no_links_when_locked(self):
        self.event.locked = True
        self.event.save()
        self.client.login(username='tester', password='pass')
        response = self.client.get(f'/events/{self.event.slug}/')
        self.assertFalse(response.context['show_signup_link'])
        self.assertFalse(response.context['show_edit_link'])

    def test_no_signup_link_when_signups_closed(self):
        self.event.signups_open = False
        self.event.save()
        self.client.login(username='tester', password='pass')
        response = self.client.get(f'/events/{self.event.slug}/')
        self.assertFalse(response.context['show_signup_link'])


def _make_schedule_event():
    """
    Create a test event with periods, roles, and signup slots for schedule tests.
    Returns (event, slot, single_assign_role) - uses the first single-assign role
    as the primary test role since multi-assign roles use EventScheduleMultiAssignment.
    """
    event = Event.objects.create(
        name='Schedule Test', slug='schedule-test', description='',
        timezone='America/New_York',
    )
    EventPeriod.objects.create(
        event=event,
        start=dt(2025, 4, 4, 12),
        stop=dt(2025, 4, 4, 18),
    )
    for slug, name, multi in [('participant', 'Participant', True), ('streamer', 'Streamer', False),
                               ('moderator', 'Moderator', False), ('tech-manager', 'Tech Manager', False)]:
        EventRole.objects.get_or_create(slug=slug, defaults={'name': name, 'description': '', 'multi_assign': multi})
    single_role = EventRole.objects.filter(multi_assign=False).order_by('display_order', 'name').first()
    multi_role = EventRole.objects.filter(multi_assign=True).first()
    slot = EventSignupSlot.objects.create(
        event=event,
        start=dt(2025, 4, 4, 12),
        stop=dt(2025, 4, 4, 15),
        label='Friday 8am - 11am',
    )
    slot.roles.set([single_role, multi_role])
    return event, slot, single_role


class AvailabilitySummaryViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')
        self.event, self.slot, self.role = _make_schedule_event()

    def _url(self):
        return f'/admin/eventer/event/{self.event.pk}/availability/'

    def test_returns_200(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)

    def test_shows_no_data_message_when_no_periods(self):
        event = Event.objects.create(name='No Period', slug='no-period', description='')
        response = self.client.get(f'/admin/eventer/event/{event.pk}/availability/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['rows'], [])

    def test_grid_has_correct_number_of_rows(self):
        response = self.client.get(self._url())
        # 6 hours (12:00-18:00 UTC)
        self.assertEqual(len(response.context['rows']), 6)

    def test_role_headers_present(self):
        from eventer.models import EventRole
        response = self.client.get(self._url())
        labels = [h['label'] for h in response.context['role_headers']]
        for role in EventRole.objects.filter(multi_assign=False):
            self.assertIn(role.name, labels)
        for role in EventRole.objects.filter(multi_assign=True):
            self.assertNotIn(role.name, labels)


class BuildScheduleViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')
        self.event, self.slot, self.role = _make_schedule_event()

    def _url(self):
        return f'/admin/eventer/event/{self.event.pk}/build-schedule/'

    def test_get_returns_200(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)

    def test_post_creates_schedule_slots(self):
        from eventer.models import EventScheduleAssignment
        streamer_role = EventRole.objects.get(slug='streamer')
        user = User.objects.create_user('streamer', 'streamer@example.com', 'pass')
        response = self.client.post(self._url(), {
            f'assign_{self.slot.pk}_streamer': str(user.pk),
        })
        self.assertRedirects(response, self._url(), fetch_redirect_response=False)
        self.assertTrue(EventScheduleAssignment.objects.filter(
            event=self.event, slot=self.slot, role=streamer_role, user=user
        ).exists())

    def test_post_creates_multi_assignments(self):
        from eventer.models import EventScheduleMultiAssignment
        participant_role = EventRole.objects.get(slug='participant')
        user1 = User.objects.create_user('p1', 'p1@example.com', 'pass')
        user2 = User.objects.create_user('p2', 'p2@example.com', 'pass')
        self.client.post(self._url(), {
            f'assign_{self.slot.pk}_participant': [str(user1.pk), str(user2.pk)],
        })
        self.assertEqual(
            EventScheduleMultiAssignment.objects.filter(
                event=self.event,
                slot=self.slot,
                role=participant_role).count(), 2
        )

    def test_post_replaces_existing_assignments(self):
        from eventer.models import EventScheduleAssignment
        streamer_role = EventRole.objects.get(slug='streamer')
        user1 = User.objects.create_user('user1', 'u1@example.com', 'pass')
        user2 = User.objects.create_user('user2', 'u2@example.com', 'pass')
        EventScheduleAssignment.objects.create(event=self.event, slot=self.slot, role=streamer_role, user=user1)
        self.client.post(self._url(), {
            f'assign_{self.slot.pk}_streamer': str(user2.pk),
        })
        assignment = EventScheduleAssignment.objects.get(event=self.event, slot=self.slot, role=streamer_role)
        self.assertEqual(assignment.user, user2)

    def test_post_clears_unsubmitted_slots(self):
        from eventer.models import EventScheduleAssignment
        streamer_role = EventRole.objects.get(slug='streamer')
        user = User.objects.create_user('user1', 'u1@example.com', 'pass')
        EventScheduleAssignment.objects.create(event=self.event, slot=self.slot, role=streamer_role, user=user)
        # POST with no assignments - should clear all
        self.client.post(self._url(), {})
        self.assertEqual(EventScheduleAssignment.objects.filter(event=self.event).count(), 0)


class AssignSlotViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')
        self.event, self.slot, self.role = _make_schedule_event()
        self.user = User.objects.create_user('streamer', 'streamer@example.com', 'pass')

    def _url(self):
        return f'/admin/eventer/event/{self.event.pk}/assign-slot/'

    def test_assigns_user_to_slot(self):
        from eventer.models import EventScheduleAssignment
        self.client.post(self._url(), {
            'slot_pk': self.slot.pk,
            'role_slug': 'streamer',
            'user_id': self.user.pk,
        })
        self.assertTrue(EventScheduleAssignment.objects.filter(
            slot=self.slot, role=self.role, user=self.user
        ).exists())

    def test_clears_assignment_when_no_user(self):
        from eventer.models import EventScheduleAssignment
        EventScheduleAssignment.objects.create(event=self.event, slot=self.slot, role=self.role, user=self.user)
        self.client.post(self._url(), {
            'slot_pk': self.slot.pk,
            'role_slug': 'streamer',
            'user_id': '',
        })
        self.assertFalse(EventScheduleAssignment.objects.filter(slot=self.slot, role=self.role).exists())

    def test_get_redirects_to_availability(self):
        response = self.client.get(self._url())
        self.assertRedirects(response,
            f'/admin/eventer/event/{self.event.pk}/availability/',
            fetch_redirect_response=False)


class AddAvailabilityViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')
        self.event, self.slot, self.role = _make_schedule_event()
        self.user = User.objects.create_user('newcomer', 'newcomer@example.com', 'pass')

    def _url(self):
        return f'/admin/eventer/event/{self.event.pk}/add-availability/'

    def test_get_renders_form(self):
        response = self.client.get(
            self._url(), {'slot': self.slot.pk, 'role': self.role.slug}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Friday 8am - 11am')

    def test_post_creates_event_interest(self):
        from evtsignup.models import EventInterest
        self.client.post(self._url(), {
            'slot_pk': self.slot.pk,
            'role_slug': 'streamer',
            'user': self.user.pk,
        })
        self.assertTrue(EventInterest.objects.filter(user=self.user, event=self.event).exists())

    def test_post_creates_availability_rows(self):
        from evtsignup.models import EventAvailabilityHour, EventInterest
        self.client.post(self._url(), {
            'slot_pk': self.slot.pk,
            'role_slug': self.role.slug,
            'user': self.user.pk,
        })
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        hours = EventAvailabilityHour.objects.filter(event_interest=interest, role=self.role)
        self.assertEqual(hours.count(), 3)  # 12:00, 13:00, 14:00 UTC

    def test_post_creates_schedule_slot(self):
        from eventer.models import EventScheduleAssignment
        self.client.post(self._url(), {
            'slot_pk': self.slot.pk,
            'role_slug': self.role.slug,
            'user': self.user.pk,
        })
        self.assertTrue(EventScheduleAssignment.objects.filter(
            event=self.event, slot=self.slot, role=self.role, user=self.user
        ).exists())

    def test_post_redirects_to_availability(self):
        response = self.client.post(self._url(), {
            'slot_pk': self.slot.pk,
            'role_slug': 'streamer',
            'user': self.user.pk,
        })
        self.assertRedirects(response,
            f'/admin/eventer/event/{self.event.pk}/availability/',
            fetch_redirect_response=False)


class GameCoverUrlTest(TestCase):
    def test_cover_url_returns_big_url(self):
        from eventer.models import Game
        game = Game(name='Test', igdb_id=1, igdb_cover_hash='abc123')
        self.assertEqual(game.cover_url, '//images.igdb.com/igdb/image/upload/t_cover_big/abc123.jpg')

    def test_cover_url_thumb_returns_thumb_url(self):
        from eventer.models import Game
        game = Game(name='Test', igdb_id=1, igdb_cover_hash='abc123')
        self.assertEqual(game.cover_url_thumb, '//images.igdb.com/igdb/image/upload/t_thumb/abc123.jpg')

    def test_cover_url_none_when_no_hash(self):
        from eventer.models import Game
        game = Game(name='Test', igdb_id=1, igdb_cover_hash=None)
        self.assertIsNone(game.cover_url)
        self.assertIsNone(game.cover_url_thumb)


class ParseIgdbGameTest(TestCase):
    def test_parses_basic_fields(self):
        from eventer.igdb import parse_igdb_game
        data = {
            'id': 1234,
            'name': 'Going Medieval',
            'slug': 'going-medieval',
            'url': 'https://www.igdb.com/games/going-medieval',
            'summary': 'A colony builder.',
            'cover': {'image_id': 'hash001'},
            'category': 0,
        }
        result = parse_igdb_game(data)
        self.assertEqual(result['name'], 'Going Medieval')
        self.assertEqual(result['igdb_slug'], 'going-medieval')
        self.assertEqual(result['igdb_url'], 'https://www.igdb.com/games/going-medieval')
        self.assertEqual(result['igdb_cover_hash'], 'hash001')
        self.assertEqual(result['summary'], 'A colony builder.')
        self.assertEqual(result['igdb_category'], 0)
        self.assertIsNone(result['first_release_date'])
        self.assertIsNone(result['multiplayer_max'])

    def test_parses_release_date(self):
        from eventer.igdb import parse_igdb_game
        data = {'id': 1, 'name': 'X', 'first_release_date': 1609459200}  # 2021-01-01 UTC
        result = parse_igdb_game(data)
        from datetime import date
        self.assertEqual(result['first_release_date'], date(2021, 1, 1))

    def test_handles_missing_cover(self):
        from eventer.igdb import parse_igdb_game
        data = {'id': 1, 'name': 'X'}
        result = parse_igdb_game(data)
        self.assertIsNone(result['igdb_cover_hash'])

    def test_handles_empty_slug(self):
        from eventer.igdb import parse_igdb_game
        data = {'id': 1, 'name': 'X', 'slug': ''}
        result = parse_igdb_game(data)
        self.assertIsNone(result['igdb_slug'])


class IGDBClientTest(TestCase):
    def test_credentials_configured_true_when_set(self):
        from eventer.igdb import IGDBClient
        with self.settings(IGDB_CLIENT_ID='abc', IGDB_CLIENT_SECRET='def'):
            self.assertTrue(IGDBClient.credentials_configured())

    def test_credentials_configured_false_when_empty(self):
        from eventer.igdb import IGDBClient
        with self.settings(IGDB_CLIENT_ID='', IGDB_CLIENT_SECRET=''):
            self.assertFalse(IGDBClient.credentials_configured())

    def test_credentials_configured_false_when_partial(self):
        from eventer.igdb import IGDBClient
        with self.settings(IGDB_CLIENT_ID='abc', IGDB_CLIENT_SECRET=''):
            self.assertFalse(IGDBClient.credentials_configured())

    def test_credentials_valid_returns_true_on_success(self):
        from unittest.mock import patch

        from eventer.igdb import IGDBClient
        client = IGDBClient()
        with patch.object(client, '_get_token', return_value='token'):
            self.assertTrue(client.credentials_valid())

    def test_credentials_valid_returns_false_on_401(self):
        from unittest.mock import patch

        from eventer.igdb import IGDBClient, IGDBError
        client = IGDBClient()
        with patch.object(client, '_get_token', side_effect=IGDBError('bad', status_code=401)):
            self.assertFalse(client.credentials_valid())

    def test_credentials_valid_returns_false_on_403(self):
        from unittest.mock import patch

        from eventer.igdb import IGDBClient, IGDBError
        client = IGDBClient()
        with patch.object(client, '_get_token', side_effect=IGDBError('forbidden', status_code=403)):
            self.assertFalse(client.credentials_valid())

    def test_credentials_valid_reraises_non_auth_errors(self):
        from unittest.mock import patch

        from eventer.igdb import IGDBClient, IGDBError
        client = IGDBClient()
        with patch.object(client, '_get_token', side_effect=IGDBError('timeout')):
            with self.assertRaises(IGDBError):
                client.credentials_valid()

    def test_rate_limit_retries_and_succeeds(self):
        from unittest.mock import MagicMock, patch

        from eventer.igdb import IGDBClient
        client = IGDBClient()
        rate_limited = MagicMock()
        rate_limited.status_code = 429
        rate_limited.headers = {'Retry-After': '0'}
        success = MagicMock()
        success.status_code = 200
        success.ok = True
        success.json.return_value = [{'id': 1, 'name': 'X'}]
        with patch.object(client, '_get_token', return_value='token'), \
             patch.object(client, '_do_request', side_effect=[rate_limited, success]), \
             patch('eventer.igdb.time.sleep') as mock_sleep, \
             self.settings(IGDB_RATE_LIMIT_RETRIES=3, IGDB_RATE_LIMIT_RETRY_AFTER=1.0):
            result = client._request('games', 'fields id,name;')
        self.assertEqual(result, [{'id': 1, 'name': 'X'}])
        mock_sleep.assert_called_once_with(0.0)

    def test_rate_limit_raises_after_max_retries(self):
        from unittest.mock import MagicMock, patch

        from eventer.igdb import IGDBClient, IGDBError
        client = IGDBClient()
        rate_limited = MagicMock()
        rate_limited.status_code = 429
        rate_limited.ok = False
        rate_limited.headers = {'Retry-After': '0'}
        rate_limited.text = 'Too Many Requests'
        with patch.object(client, '_get_token', return_value='token'), \
             patch.object(client, '_do_request', return_value=rate_limited), \
             patch('eventer.igdb.time.sleep'), \
             self.settings(IGDB_RATE_LIMIT_RETRIES=2, IGDB_RATE_LIMIT_RETRY_AFTER=0):
            with self.assertRaises(IGDBError) as cm:
                client._request('games', 'fields id;')
        self.assertEqual(cm.exception.status_code, 429)


class SyncGameFromIgdbTest(TestCase):
    def _mock_data(self):
        return {
            'id': 9999,
            'name': 'Mock Game',
            'slug': 'mock-game',
            'url': 'https://www.igdb.com/games/mock-game',
            'summary': 'A mock game.',
            'cover': {'image_id': 'mockhash'},
            'category': 0,
            'first_release_date': 1609459200,
        }

    def test_creates_game(self):
        from unittest.mock import MagicMock, patch

        from eventer.igdb import IGDBClient, sync_game_from_igdb
        mock_client = MagicMock(spec=IGDBClient)
        mock_client.fetch_game.return_value = self._mock_data()
        with patch('eventer.igdb.IGDBClient', return_value=mock_client):
            game, created = sync_game_from_igdb(9999)
        self.assertTrue(created)
        self.assertEqual(game.name, 'Mock Game')
        self.assertEqual(game.igdb_id, 9999)
        self.assertEqual(game.igdb_cover_hash, 'mockhash')

    def test_updates_existing_game(self):
        from unittest.mock import MagicMock, patch

        from eventer.igdb import IGDBClient, sync_game_from_igdb
        from eventer.models import Game
        Game.objects.create(name='Old Name', igdb_id=9999)
        mock_client = MagicMock(spec=IGDBClient)
        mock_client.fetch_game.return_value = {**self._mock_data(), 'name': 'Updated Name'}
        with patch('eventer.igdb.IGDBClient', return_value=mock_client):
            game, created = sync_game_from_igdb(9999)
        self.assertFalse(created)
        self.assertEqual(game.name, 'Updated Name')

    def test_raises_on_not_found(self):
        from unittest.mock import MagicMock, patch

        from eventer.igdb import IGDBClient, sync_game_from_igdb
        mock_client = MagicMock(spec=IGDBClient)
        mock_client.fetch_game.return_value = None
        with patch('eventer.igdb.IGDBClient', return_value=mock_client):
            with self.assertRaises(ValueError):
                sync_game_from_igdb(9999)


class IGDBClientGetTokenTest(TestCase):
    def _make_client(self):
        from eventer.igdb import IGDBClient
        with self.settings(IGDB_CLIENT_ID='test_id', IGDB_CLIENT_SECRET='test_secret'):
            return IGDBClient()

    def test_returns_cached_token(self):
        from unittest.mock import patch
        client = self._make_client()
        with patch('eventer.igdb.cache') as mock_cache:
            mock_cache.get.return_value = 'cached_token'
            token = client._get_token()
        self.assertEqual(token, 'cached_token')

    def test_fetches_and_caches_token(self):
        from unittest.mock import MagicMock, patch
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {'access_token': 'new_token', 'expires_in': 3600}
        with patch('eventer.igdb.cache') as mock_cache, \
             patch('eventer.igdb.requests.post', return_value=mock_resp):
            mock_cache.get.return_value = None
            token = client._get_token()
        self.assertEqual(token, 'new_token')
        mock_cache.set.assert_called_once()
        _, args, _ = mock_cache.set.mock_calls[0]
        self.assertEqual(args[1], 'new_token')
        self.assertEqual(args[2], 3600 - 60)  # TOKEN_EXPIRY_BUFFER

    def test_raises_on_timeout(self):
        from unittest.mock import patch

        import requests as req

        from eventer.igdb import IGDBError
        client = self._make_client()
        with patch('eventer.igdb.cache') as mock_cache, \
             patch('eventer.igdb.requests.post', side_effect=req.exceptions.Timeout):
            mock_cache.get.return_value = None
            with self.assertRaises(IGDBError) as cm:
                client._get_token()
        self.assertIn('Timed out', str(cm.exception))

    def test_raises_on_network_error(self):
        from unittest.mock import patch

        import requests as req

        from eventer.igdb import IGDBError
        client = self._make_client()
        with patch('eventer.igdb.cache') as mock_cache, \
             patch('eventer.igdb.requests.post', side_effect=req.exceptions.ConnectionError('refused')):
            mock_cache.get.return_value = None
            with self.assertRaises(IGDBError) as cm:
                client._get_token()
        self.assertIn('Network error', str(cm.exception))

    def test_raises_on_bad_response(self):
        from unittest.mock import MagicMock, patch

        from eventer.igdb import IGDBError
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 403
        mock_resp.text = 'Forbidden'
        with patch('eventer.igdb.cache') as mock_cache, \
             patch('eventer.igdb.requests.post', return_value=mock_resp):
            mock_cache.get.return_value = None
            with self.assertRaises(IGDBError) as cm:
                client._get_token()
        self.assertEqual(cm.exception.status_code, 403)


class IGDBClientDoRequestTest(TestCase):
    def _make_client(self):
        from eventer.igdb import IGDBClient
        with self.settings(IGDB_CLIENT_ID='test_id', IGDB_CLIENT_SECRET='test_secret'):
            return IGDBClient()

    def test_raises_on_timeout(self):
        from unittest.mock import patch

        import requests as req

        from eventer.igdb import IGDBError
        client = self._make_client()
        with patch('eventer.igdb.requests.post', side_effect=req.exceptions.Timeout):
            with self.assertRaises(IGDBError) as cm:
                client._do_request('games', 'fields id;', 'token')
        self.assertIn('Timed out', str(cm.exception))

    def test_raises_on_network_error(self):
        from unittest.mock import patch

        import requests as req

        from eventer.igdb import IGDBError
        client = self._make_client()
        with patch('eventer.igdb.requests.post', side_effect=req.exceptions.ConnectionError('refused')):
            with self.assertRaises(IGDBError) as cm:
                client._do_request('games', 'fields id;', 'token')
        self.assertIn('Network error', str(cm.exception))


class IGDBClientRequestTest(TestCase):
    def _make_client(self):
        from eventer.igdb import IGDBClient
        with self.settings(IGDB_CLIENT_ID='test_id', IGDB_CLIENT_SECRET='test_secret'):
            return IGDBClient()

    def _ok_resp(self, data):
        from unittest.mock import MagicMock
        resp = MagicMock()
        resp.status_code = 200
        resp.ok = True
        resp.json.return_value = data
        return resp

    def test_401_clears_cache_and_retries(self):
        from unittest.mock import MagicMock, patch
        client = self._make_client()
        unauth = MagicMock()
        unauth.status_code = 401
        unauth.ok = False
        unauth.text = 'Unauthorized'
        success = self._ok_resp([{'id': 1}])
        with patch.object(client, '_get_token', side_effect=['old_token', 'new_token']), \
             patch.object(client, '_do_request', side_effect=[unauth, success]) as mock_do, \
             patch('eventer.igdb.cache') as mock_cache:
            result = client._request('games', 'fields id;')
        self.assertEqual(result, [{'id': 1}])
        mock_cache.delete.assert_called_once_with(client._token_cache_key)
        self.assertEqual(mock_do.call_count, 2)


class IGDBClientFetchGameTest(TestCase):
    def _make_client(self):
        from eventer.igdb import IGDBClient
        with self.settings(IGDB_CLIENT_ID='test_id', IGDB_CLIENT_SECRET='test_secret'):
            return IGDBClient()

    def test_returns_first_result(self):
        from unittest.mock import patch
        client = self._make_client()
        with patch.object(client, '_request', return_value=[{'id': 1, 'name': 'X'}]):
            result = client.fetch_game(1)
        self.assertEqual(result, {'id': 1, 'name': 'X'})

    def test_returns_none_when_not_found(self):
        from unittest.mock import patch
        client = self._make_client()
        with patch.object(client, '_request', return_value=[]):
            result = client.fetch_game(1)
        self.assertIsNone(result)


class IGDBClientSearchGamesTest(TestCase):
    def _make_client(self):
        from eventer.igdb import IGDBClient
        with self.settings(IGDB_CLIENT_ID='test_id', IGDB_CLIENT_SECRET='test_secret'):
            return IGDBClient()

    def test_returns_results(self):
        from unittest.mock import patch
        client = self._make_client()
        games = [{'id': 1, 'name': 'Stardew Valley'}]
        with patch.object(client, '_request', return_value=games):
            result = client.search_games('stardew')
        self.assertEqual(result, games)

    def test_escapes_double_quotes_in_query(self):
        from unittest.mock import patch
        client = self._make_client()
        with patch.object(client, '_request', return_value=[]) as mock_req:
            client.search_games('test "game"')
        body = mock_req.call_args[0][1]
        self.assertIn(r'test \"game\"', body)

    def test_escapes_backslashes_in_query(self):
        from unittest.mock import patch
        client = self._make_client()
        with patch.object(client, '_request', return_value=[]) as mock_req:
            client.search_games('test\\game')
        body = mock_req.call_args[0][1]
        self.assertIn('test\\\\game', body)


class ParseIgdbGameMultiplayerTest(TestCase):
    def test_derives_multiplayer_max_from_onlinecoopmax(self):
        from eventer.igdb import parse_igdb_game
        data = {'id': 1, 'name': 'X', 'multiplayer_modes': [
            {'onlinecoop': True, 'onlinecoopmax': 4},
        ]}
        result = parse_igdb_game(data)
        self.assertEqual(result['multiplayer_max'], 4)

    def test_uses_default_2_when_onlinecoopmax_missing(self):
        from eventer.igdb import parse_igdb_game
        data = {'id': 1, 'name': 'X', 'multiplayer_modes': [
            {'onlinecoop': True},
        ]}
        result = parse_igdb_game(data)
        self.assertEqual(result['multiplayer_max'], 2)

    def test_skips_non_coop_modes(self):
        from eventer.igdb import parse_igdb_game
        data = {'id': 1, 'name': 'X', 'multiplayer_modes': [
            {'onlinecoop': False, 'onlinecoopmax': 4},
        ]}
        result = parse_igdb_game(data)
        self.assertIsNone(result['multiplayer_max'])

    def test_takes_max_across_multiple_modes(self):
        from eventer.igdb import parse_igdb_game
        data = {'id': 1, 'name': 'X', 'multiplayer_modes': [
            {'onlinecoop': True, 'onlinecoopmax': 2},
            {'onlinecoop': True, 'onlinecoopmax': 8},
        ]}
        result = parse_igdb_game(data)
        self.assertEqual(result['multiplayer_max'], 8)

    def test_multiplayer_max_zero_treated_as_none(self):
        from eventer.igdb import parse_igdb_game
        data = {'id': 1, 'name': 'X', 'multiplayer_modes': [
            {'onlinecoop': True, 'onlinecoopmax': 0},
        ]}
        result = parse_igdb_game(data)
        self.assertIsNone(result['multiplayer_max'])


class SyncIgdbGameCommandTest(TestCase):
    def _call_command(self, *args, **kwargs):
        from io import StringIO

        from django.core.management import call_command
        out = StringIO()
        call_command('sync_igdb_game', *args, stdout=out, **kwargs)
        return out.getvalue()

    def test_errors_when_not_configured(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        with self.settings(IGDB_CLIENT_ID='', IGDB_CLIENT_SECRET=''):
            with self.assertRaises(CommandError) as cm:
                call_command('sync_igdb_game', 1)
        self.assertIn('not configured', str(cm.exception))

    def test_errors_when_credentials_invalid(self):
        from unittest.mock import patch

        from django.core.management.base import CommandError

        from eventer.igdb import IGDBClient
        with self.settings(IGDB_CLIENT_ID='bad', IGDB_CLIENT_SECRET='bad'):
            with patch.object(IGDBClient, 'credentials_valid', return_value=False):
                with self.assertRaises(CommandError) as cm:
                    self._call_command(1)
        self.assertIn('invalid', str(cm.exception))

    def _patch_credentials(self):
        """Context manager that patches credential checks to pass."""
        from unittest.mock import MagicMock, patch

        from eventer.igdb import IGDBClient
        mock_client = MagicMock(spec=IGDBClient)
        mock_client.credentials_valid.return_value = True
        return patch('eventer.management.commands.sync_igdb_game.IGDBClient',
                     credentials_configured=MagicMock(return_value=True),
                     return_value=mock_client)

    def test_prints_created_on_success(self):
        from unittest.mock import MagicMock, patch
        mock_game = MagicMock()
        mock_game.name = 'Test Game'
        with self.settings(IGDB_CLIENT_ID='x', IGDB_CLIENT_SECRET='y'), \
             self._patch_credentials(), \
             patch('eventer.management.commands.sync_igdb_game.sync_game_from_igdb',
                   return_value=(mock_game, True)):
            out = self._call_command(1)
        self.assertIn('Created', out)

    def test_prints_updated_on_existing(self):
        from unittest.mock import MagicMock, patch
        mock_game = MagicMock()
        mock_game.name = 'Test Game'
        with self.settings(IGDB_CLIENT_ID='x', IGDB_CLIENT_SECRET='y'), \
             self._patch_credentials(), \
             patch('eventer.management.commands.sync_igdb_game.sync_game_from_igdb',
                   return_value=(mock_game, False)):
            out = self._call_command(1)
        self.assertIn('Updated', out)

    def test_raises_command_error_on_igdb_error(self):
        from unittest.mock import patch

        from django.core.management.base import CommandError

        from eventer.igdb import IGDBError
        with self.settings(IGDB_CLIENT_ID='x', IGDB_CLIENT_SECRET='y'), \
             self._patch_credentials(), \
             patch('eventer.management.commands.sync_igdb_game.sync_game_from_igdb',
                   side_effect=IGDBError('API error')):
            with self.assertRaises(CommandError) as cm:
                self._call_command(1)
        self.assertIn('IGDB API error', str(cm.exception))

    def test_raises_command_error_on_not_found(self):
        from unittest.mock import patch

        from django.core.management.base import CommandError
        with self.settings(IGDB_CLIENT_ID='x', IGDB_CLIENT_SECRET='y'), \
             self._patch_credentials(), \
             patch('eventer.management.commands.sync_igdb_game.sync_game_from_igdb',
                   side_effect=ValueError('not found')):
            with self.assertRaises(CommandError) as cm:
                self._call_command(1)
        self.assertIn('not found', str(cm.exception))


def _make_coordinator(username='coord'):
    """Create a staff user with the Coordinator group and return them."""
    from django.contrib.auth.models import Group

    from fforg.permissions import seed_permission_groups
    seed_permission_groups()
    user = User.objects.create_user(username, f'{username}@example.com', 'pass', is_staff=True)
    user.groups.add(Group.objects.get(name='Coordinator'))
    return user


class SearchIgdbViewTest(TestCase):
    def setUp(self):
        self.coordinator = _make_coordinator('coord_igdb')
        self.client.login(username='coord_igdb', password='pass')

    def _url(self):
        return '/admin/eventer/game/search-igdb/'

    def test_get_no_query_renders_form(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Search IGDB')

    def test_get_no_credentials_shows_error(self):
        with self.settings(IGDB_CLIENT_ID='', IGDB_CLIENT_SECRET=''):
            response = self.client.get(self._url() + '?q=fortnite')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'not configured')

    def test_get_with_query_returns_results(self):
        from unittest.mock import patch

        from eventer.igdb import IGDBClient
        mock_results = [{'id': 1905, 'name': 'Fortnite', 'slug': 'fortnite',
                         'cover': {'image_id': 'hash'}, 'first_release_date': 1498780800, 'category': 0}]
        with patch.object(IGDBClient, 'credentials_configured', return_value=True), \
             patch.object(IGDBClient, 'search_games', return_value=mock_results), \
             self.settings(IGDB_CLIENT_ID='x', IGDB_CLIENT_SECRET='y'):
            response = self.client.get(self._url() + '?q=fortnite')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fortnite')

    def test_get_json_format_returns_json(self):
        from unittest.mock import patch

        from eventer.igdb import IGDBClient
        with patch.object(IGDBClient, 'credentials_configured', return_value=True), \
             patch.object(IGDBClient, 'search_games', return_value=[]), \
             self.settings(IGDB_CLIENT_ID='x', IGDB_CLIENT_SECRET='y'):
            response = self.client.get(self._url() + '?q=test&format=json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertIn('results', data)

    def test_post_syncs_games(self):
        from unittest.mock import MagicMock, patch
        mock_game = MagicMock()
        mock_game.name = 'Fortnite'
        with patch('eventer.igdb.sync_game_from_igdb', return_value=(mock_game, True)):
            response = self.client.post(self._url(), {'igdb_id': ['1905'], 'q': 'fortnite'})
        self.assertRedirects(response, self._url() + '?q=fortnite', fetch_redirect_response=False)

    def test_requires_search_igdb_permission(self):
        User.objects.create_user('nocoord', 'nc@example.com', 'pass', is_staff=True)
        self.client.login(username='nocoord', password='pass')
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 403)


class SyncAndLinkViewTest(TestCase):
    def setUp(self):
        from evtsignup.models import EventInterest
        self.coordinator = _make_coordinator('coord_link')
        self.client.login(username='coord_link', password='pass')
        self.event = Event.objects.create(name='Link Test Event', slug='link-test-event', description='')
        self.interest = EventInterest.objects.create(
            user=self.coordinator, event=self.event, acknowledged=True
        )
        self.role = EventRole.objects.get_or_create(
            slug='streamer', defaults={'name': 'Streamer', 'description': ''}
        )[0]

    def _url(self):
        return '/admin/eventer/game/sync-and-link/'

    def _post(self, igdb_id=1905):
        return self.client.post(self._url(), {
            'igdb_id': str(igdb_id),
            'event_interest_id': str(self.interest.pk),
            'role_id': str(self.role.pk),
        })

    def test_requires_post(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 405)

    def test_syncs_and_links_game(self):
        from unittest.mock import patch

        from eventer.models import Game
        from evtsignup.models import GameInterestUserEvent
        game = Game.objects.create(name='Fortnite', igdb_id=1905, status='approved')
        with patch('eventer.igdb.sync_game_from_igdb', return_value=(game, False)):
            response = self._post()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(GameInterestUserEvent.objects.filter(
            event_interest=self.interest, game=game, role=self.role
        ).exists())

    def test_auto_approves_pending_game(self):
        from unittest.mock import patch

        from eventer.models import Game
        game = Game.objects.create(name='Fortnite Pending', igdb_id=19051, status='pending')
        with patch('eventer.igdb.sync_game_from_igdb', return_value=(game, False)):
            self._post(igdb_id=19051)
        game.refresh_from_db()
        self.assertEqual(game.status, 'approved')

    def test_returns_404_for_missing_interest(self):
        response = self.client.post(self._url(), {
            'igdb_id': '1905',
            'event_interest_id': '99999',
            'role_id': str(self.role.pk),
        })
        self.assertEqual(response.status_code, 404)

    def test_returns_404_for_not_found_game(self):
        from unittest.mock import patch
        with patch('eventer.igdb.sync_game_from_igdb', side_effect=ValueError('not found')):
            response = self._post()
        self.assertEqual(response.status_code, 404)
        self.assertIn('not found', response.json()['error'])

    def test_requires_search_igdb_permission(self):
        User.objects.create_user('nocoord2', 'nc2@example.com', 'pass', is_staff=True)
        self.client.login(username='nocoord2', password='pass')
        response = self.client.post(self._url(), {})
        self.assertEqual(response.status_code, 403)


class SyncSingleIgdbGameTaskTest(TestCase):
    def test_syncs_game(self):
        from unittest.mock import patch

        from eventer.models import Game
        from eventer.tasks import sync_single_igdb_game
        game = Game.objects.create(name='Test Game', igdb_id=1234)
        with patch('eventer.igdb.sync_game_from_igdb', return_value=(game, False)):
            result = sync_single_igdb_game(1234)
        self.assertEqual(result['igdb_id'], 1234)

    def test_raises_on_igdb_error(self):
        from unittest.mock import patch

        from eventer.igdb import IGDBError
        from eventer.tasks import sync_single_igdb_game
        with patch('eventer.igdb.sync_game_from_igdb', side_effect=IGDBError('fail')):
            with self.assertRaises(IGDBError):
                sync_single_igdb_game(1234)


class SyncAllIgdbGamesTaskTest(TestCase):
    def test_dispatches_tasks_for_each_game(self):
        from unittest.mock import patch

        from eventer.igdb import IGDBClient
        from eventer.models import Game
        from eventer.tasks import sync_all_igdb_games
        Game.objects.create(name='Game A', igdb_id=1)
        Game.objects.create(name='Game B', igdb_id=2)
        with patch.object(IGDBClient, 'credentials_configured', return_value=True), \
             patch('eventer.tasks.sync_single_igdb_game') as mock_task:
            mock_task.delay = mock_task
            sync_all_igdb_games()
        self.assertEqual(mock_task.call_count, 2)

    def test_skips_when_not_configured(self):
        from unittest.mock import patch

        from eventer.igdb import IGDBClient
        from eventer.tasks import sync_all_igdb_games
        with patch.object(IGDBClient, 'credentials_configured', return_value=False), \
             patch('eventer.tasks.sync_single_igdb_game') as mock_task:
            sync_all_igdb_games()
        mock_task.assert_not_called()


class FetchTopGamesByHypesTaskTest(TestCase):
    def test_dispatches_tasks_for_results(self):
        from unittest.mock import patch

        from eventer.igdb import IGDBClient
        from eventer.tasks import fetch_top_games_by_hypes
        mock_results = [{'id': 1877, 'name': 'Cyberpunk 2077'}, {'id': 52189, 'name': 'GTA VI'}]
        with patch.object(IGDBClient, 'credentials_configured', return_value=True), \
             patch.object(IGDBClient, 'top_games_by_hypes', return_value=mock_results), \
             patch('eventer.tasks.sync_single_igdb_game') as mock_task, \
             self.settings(IGDB_CLIENT_ID='x', IGDB_CLIENT_SECRET='y'):
            mock_task.delay = mock_task
            fetch_top_games_by_hypes(limit=2)
        self.assertEqual(mock_task.call_count, 2)

    def test_skips_when_not_configured(self):
        from unittest.mock import patch

        from eventer.igdb import IGDBClient
        from eventer.tasks import fetch_top_games_by_hypes
        with patch.object(IGDBClient, 'credentials_configured', return_value=False), \
             patch('eventer.tasks.sync_single_igdb_game') as mock_task:
            fetch_top_games_by_hypes()
        mock_task.assert_not_called()


class FetchTopGamesByRatingTaskTest(TestCase):
    def test_dispatches_tasks_for_results(self):
        from unittest.mock import patch

        from eventer.igdb import IGDBClient
        from eventer.tasks import fetch_top_games_by_rating
        mock_results = [{'id': 1103, 'name': 'Super Metroid'}]
        with patch.object(IGDBClient, 'credentials_configured', return_value=True), \
             patch.object(IGDBClient, 'top_games_by_rating', return_value=mock_results), \
             patch('eventer.tasks.sync_single_igdb_game') as mock_task, \
             self.settings(IGDB_CLIENT_ID='x', IGDB_CLIENT_SECRET='y'):
            mock_task.delay = mock_task
            fetch_top_games_by_rating(limit=1)
        mock_task.assert_called_once_with(1103)

    def test_skips_when_not_configured(self):
        from unittest.mock import patch

        from eventer.igdb import IGDBClient
        from eventer.tasks import fetch_top_games_by_rating
        with patch.object(IGDBClient, 'credentials_configured', return_value=False), \
             patch('eventer.tasks.sync_single_igdb_game') as mock_task:
            fetch_top_games_by_rating()
        mock_task.assert_not_called()


# --- schedule.py ---

class EventAllHoursTest(TestCase):
    def test_single_hour(self):
        start = dt(2025, 4, 4, 12)
        end = dt(2025, 4, 4, 13)
        hours = _event_all_hours(start, end)
        self.assertEqual(hours, [dt(2025, 4, 4, 12)])

    def test_multiple_hours(self):
        start = dt(2025, 4, 4, 12)
        end = dt(2025, 4, 4, 15)
        hours = _event_all_hours(start, end)
        self.assertEqual(len(hours), 3)
        self.assertEqual(hours[0], dt(2025, 4, 4, 12))
        self.assertEqual(hours[-1], dt(2025, 4, 4, 14))

    def test_truncates_to_hour(self):
        start = datetime(2025, 4, 4, 12, 30, tzinfo=dt_timezone.utc)
        end = datetime(2025, 4, 4, 14, 30, tzinfo=dt_timezone.utc)
        hours = _event_all_hours(start, end)
        self.assertEqual(hours[0].minute, 0)
        self.assertEqual(hours[0].second, 0)


class SlotHourRangeTest(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name='HR Test', slug='hr-test', description='')
        EventPeriod.objects.create(event=self.event, start=dt(2025, 4, 4, 12), stop=dt(2025, 4, 6, 4))
        self.slot = EventSignupSlot.objects.create(
            event=self.event, start=dt(2025, 4, 4, 15), stop=dt(2025, 4, 4, 18), label='Test Slot'
        )

    def test_start_hour_1_indexed(self):
        h_start, h_end = slot_hour_range(dt(2025, 4, 4, 12), self.slot)
        self.assertEqual(h_start, 4)  # 15:00 - 12:00 = 3h + 1 = 4
        self.assertEqual(h_end, 6)    # 18:00 - 12:00 = 6h

    def test_slot_at_event_start(self):
        slot = EventSignupSlot.objects.create(
            event=self.event, start=dt(2025, 4, 4, 12), stop=dt(2025, 4, 4, 15), label='First Slot'
        )
        h_start, h_end = slot_hour_range(dt(2025, 4, 4, 12), slot)
        self.assertEqual(h_start, 1)
        self.assertEqual(h_end, 3)


class GenerateTwitchCommandsTest(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name='Stream Test', slug='stream-test', description='')
        EventPeriod.objects.create(event=self.event, start=dt(2025, 4, 4, 12), stop=dt(2025, 4, 6, 4))
        self.slot = EventSignupSlot.objects.create(
            event=self.event, start=dt(2025, 4, 4, 12), stop=dt(2025, 4, 4, 15), label='Friday 8am - 11am'
        )

    def test_commands_with_game_and_streamer(self):
        title, game, donate = generate_twitch_commands(self.event, self.slot, 'JohnDoe', 'Celeste')
        self.assertIn('Stream Test', title)
        self.assertIn('Hours 1-3', title)
        self.assertEqual(game, '!setgame Celeste')
        self.assertEqual(donate, '!setteam JohnDoe')

    def test_no_game_empty_game_cmd(self):
        _, game, _ = generate_twitch_commands(self.event, self.slot, 'JohnDoe', '')
        self.assertEqual(game, '')

    def test_no_streamer_empty_donate_cmd(self):
        _, _, donate = generate_twitch_commands(self.event, self.slot, '', 'Celeste')
        self.assertEqual(donate, '')

    def test_no_event_start_uses_slot_label(self):
        event = Event.objects.create(name='No Period', slug='no-period-tw', description='')
        title, _, _ = generate_twitch_commands(event, self.slot, 'JohnDoe', 'Celeste')
        self.assertIn('Friday 8am - 11am', title)


class BuildScheduleGridEmptyTest(TestCase):
    def test_no_periods_returns_empty_rows(self):
        event = Event.objects.create(name='Empty Grid', slug='empty-grid', description='')
        grid = build_schedule_grid(event)
        self.assertEqual(grid['rows'], [])
        self.assertEqual(grid['slot_role_available'], {})
        self.assertEqual(grid['slot_role_assigned'], {})


class BuildScheduleGridFullTest(TestCase):
    def setUp(self):
        self.event, self.slot, self.role = _make_schedule_event()
        self.user = User.objects.create_user('griduser', 'g@example.com', 'pass')

    def test_role_headers_contain_single_assign_roles(self):
        grid = build_schedule_grid(self.event)
        labels = [h['label'] for h in grid['role_headers']]
        for role in EventRole.objects.filter(multi_assign=False):
            self.assertIn(role.name, labels)

    def test_multi_role_headers_contain_multi_assign_roles(self):
        grid = build_schedule_grid(self.event)
        labels = [h['label'] for h in grid['multi_role_headers']]
        for role in EventRole.objects.filter(multi_assign=True):
            self.assertIn(role.name, labels)

    def test_rows_count_matches_event_hours(self):
        grid = build_schedule_grid(self.event)
        expected_hours = int((self.event.end - self.event.start).total_seconds() // 3600)
        self.assertEqual(len(grid['rows']), expected_hours)

    def test_show_stream_commands_in_role_headers(self):
        grid = build_schedule_grid(self.event)
        for header in grid['role_headers']:
            self.assertIn('show_stream_commands', header)

    def test_availability_shows_in_grid(self):
        from eventer.slot_generator import _expand_to_hours
        from evtsignup.models import EventAvailabilityHour, EventInterest
        interest, _ = EventInterest.objects.get_or_create(
            user=self.user, event=self.event, defaults={'acknowledged': True}
        )
        # Must cover ALL hours of the slot for the user to appear as available
        for hour in _expand_to_hours(self.slot):
            EventAvailabilityHour.objects.create(event_interest=interest, hour=hour, role=self.role)
        grid = build_schedule_grid(self.event)
        found = False
        first_hour = self.slot.start.replace(minute=0, second=0, microsecond=0)
        for row in grid['rows']:
            if row['hour'] == first_hour:
                for cell in row['cells']:
                    if cell['type'] == 'slot' and cell['role_slug'] == self.role.slug:
                        self.assertIn(self.user, cell['available'])
                        found = True
        self.assertTrue(found)

    def test_day_start_flag_set_at_midnight(self):
        grid = build_schedule_grid(self.event)
        for row in grid['rows']:
            if row['hour'].hour == 0:
                self.assertTrue(row['is_day_start'])

    def test_multi_cells_list_length_matches_multi_role_headers(self):
        grid = build_schedule_grid(self.event)
        for row in grid['rows']:
            self.assertEqual(len(row['multi_cells_list']), len(grid['multi_role_headers']))


# --- slot_generator.py ---

class ExpandToHoursTest(TestCase):
    def test_single_hour_slot(self):
        slot = EventSignupSlot(
            start=dt(2025, 4, 4, 12), stop=dt(2025, 4, 4, 13), label='1h'
        )
        hours = list(_expand_to_hours(slot))
        self.assertEqual(hours, [dt(2025, 4, 4, 12)])

    def test_three_hour_slot(self):
        slot = EventSignupSlot(
            start=dt(2025, 4, 4, 12), stop=dt(2025, 4, 4, 15), label='3h'
        )
        hours = list(_expand_to_hours(slot))
        self.assertEqual(len(hours), 3)
        self.assertEqual(hours[-1], dt(2025, 4, 4, 14))

    def test_truncates_to_hour(self):
        slot = EventSignupSlot(
            start=datetime(2025, 4, 4, 12, 30, tzinfo=dt_timezone.utc),
            stop=datetime(2025, 4, 4, 15, 30, tzinfo=dt_timezone.utc),
            label='test'
        )
        hours = list(_expand_to_hours(slot))
        self.assertEqual(hours[0], dt(2025, 4, 4, 12))


class GenerateSlotsGroupTest(TestCase):
    def setUp(self):
        self.event = Event.objects.create(
            name='Group Slot Test', slug='group-slot-test', description='',
            timezone='America/New_York',
        )
        EventPeriod.objects.create(
            event=self.event,
            start=dt(2025, 4, 4, 12),
            stop=dt(2025, 4, 6, 4),
        )
        for slug, name, multi in [
            (
                'participant',
                'Participant',
                True
            ), (
                'streamer',
                'Streamer',
                False
            ), (
                'moderator',
                'Moderator',
                False
            ), (
                'tech-manager',
                'Tech Manager',
                False
            )
        ]:
            EventRole.objects.get_or_create(slug=slug, defaults={
                'name': name,
                'description': '',
                'multi_assign': multi
                }
            )

    def test_replace_deletes_existing_slots(self):
        generate_slots(self.event)
        first_count = EventSignupSlot.objects.filter(event=self.event).count()
        self.assertGreater(first_count, 0)
        result = generate_slots(self.event, replace=True)
        self.assertGreater(result['deleted'], 0)
        second_count = EventSignupSlot.objects.filter(event=self.event).count()
        self.assertEqual(first_count, second_count)

    def test_group_with_block_hours_override(self):
        group = EventSlotGroup.objects.create(name='Custom Block', use_prime_time=False, block_hours=4)
        role = EventRole.objects.get(slug='moderator')
        EventSlotGroupMembership.objects.filter(role=role).delete()
        EventSlotGroupMembership.objects.create(group=group, role=role, first_block_hours=None)
        generate_slots(self.event, replace=True)
        slots = list(EventSignupSlot.objects.filter(event=self.event, roles=role).order_by('start'))
        for slot in slots[:-1]:
            duration = (slot.stop - slot.start).total_seconds() / 3600
            self.assertEqual(duration, 4)

    def test_shared_roles_in_group_get_same_slots(self):
        generate_slots(self.event)
        participant = EventRole.objects.get(slug='participant')
        streamer = EventRole.objects.get(slug='streamer')
        p_slots = set(EventSignupSlot.objects.filter(event=self.event, roles=participant).values_list('id', flat=True))
        s_slots = set(EventSignupSlot.objects.filter(event=self.event, roles=streamer).values_list('id', flat=True))
        self.assertEqual(p_slots, s_slots)

    def test_staggered_role_gets_different_first_slot(self):
        generate_slots(self.event)
        moderator = EventRole.objects.get(slug='moderator')
        tech = EventRole.objects.get(slug='tech-manager')
        mod_membership = EventSlotGroupMembership.objects.filter(role=moderator).first()
        if mod_membership and mod_membership.first_block_hours:
            mod_first = EventSignupSlot.objects.filter(event=self.event, roles=moderator).order_by('start').first()
            tech_first = EventSignupSlot.objects.filter(event=self.event, roles=tech).order_by('start').first()
            mod_duration = (mod_first.stop - mod_first.start).total_seconds() / 3600
            tech_duration = (tech_first.stop - tech_first.start).total_seconds() / 3600
            self.assertNotEqual(mod_duration, tech_duration)
