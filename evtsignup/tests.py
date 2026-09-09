from datetime import datetime
from datetime import timezone as dt_timezone
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from social_core.exceptions import AuthForbidden

from eventer.models import Event, EventPeriod, EventRole, EventSignupSlot
from evtsignup.models import EventAvailabilityHour, EventInterest
from evtsignup.pipeline import require_discord_guild
from evtsignup.utils import parse_fundraising_url


def _dt(year, month, day, hour=0):
    return datetime(year, month, day, hour, tzinfo=dt_timezone.utc)


def _seed_roles():
    for slug, name in [
        ('participant', 'Participant'),
        ('streamer', 'Streamer'),
        ('moderator', 'Moderator'),
        ('tech-manager', 'Tech Manager'),
    ]:
        EventRole.objects.get_or_create(slug=slug, defaults={'name': name, 'description': ''})


def _make_event(signups_open=True, edits_open=True, locked=False, with_slots=True):
    event = Event.objects.create(
        name='Test Superstream', slug='test-superstream', description='A test event',
        timezone='America/New_York',
        signups_open=signups_open, edits_open=edits_open, locked=locked,
    )
    EventPeriod.objects.create(
        event=event,
        start=_dt(2025, 4, 4, 12),
        stop=_dt(2025, 4, 5, 4),
    )
    if with_slots:
        _seed_roles()
        participant_role = EventRole.objects.get(slug='participant')
        streamer_role = EventRole.objects.get(slug='streamer')
        slot = EventSignupSlot.objects.create(
            event=event,
            start=_dt(2025, 4, 4, 12),
            stop=_dt(2025, 4, 4, 15),
            label='Friday 8am - 11am',
        )
        slot.roles.set([participant_role, streamer_role])
    return event


class SignupViewGetTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tester', 'tester@example.com', 'pass')
        self.client.login(username='tester', password='pass')

    def test_unauthenticated_redirects_to_login(self):
        self.client.logout()
        event = _make_event()
        response = self.client.get(f'/signup/{event.slug}/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/signup/test-superstream/', response['Location'])

    def test_locked_shows_locked_message(self):
        event = _make_event(locked=True)
        response = self.client.get(f'/signup/{event.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'locked')
        self.assertTrue(response.context['locked'])

    def test_no_slots_shows_signups_closed(self):
        event = _make_event(with_slots=False)
        response = self.client.get(f'/signup/{event.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['signups_closed'])

    def test_signups_not_open_shows_signups_closed(self):
        event = _make_event(signups_open=False)
        response = self.client.get(f'/signup/{event.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['signups_closed'])

    def test_existing_signup_edits_not_open_shows_profile_only(self):
        event = _make_event(signups_open=False, edits_open=False)
        EventInterest.objects.create(user=self.user, event=event, acknowledged=True)
        response = self.client.get(f'/signup/{event.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['profile_only'])

    def test_open_event_renders_form(self):
        event = _make_event()
        response = self.client.get(f'/signup/{event.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign Up')
        self.assertFalse(response.context.get('locked'))
        self.assertFalse(response.context.get('signups_closed'))

    def test_existing_signup_prepopulates_display_name(self):
        event = _make_event()
        EventInterest.objects.create(
            user=self.user, event=event, acknowledged=True,
            display_name='My Name', preferences='they/them',
        )
        response = self.client.get(f'/signup/{event.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Name')
        self.assertContains(response, 'they/them')


class SignupViewPostTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tester', 'tester@example.com', 'pass')
        self.client.login(username='tester', password='pass')
        self.event = _make_event()
        self.slot = EventSignupSlot.objects.filter(event=self.event).first()

    def _url(self):
        return f'/signup/{self.event.slug}/'

    def _post(self, extra=None):
        data = {
            'display_name': 'Test User',
            'preferences': '',
            'acknowledged': '1',
            'participant_slots': [str(self.slot.pk)],
        }
        if extra:
            data.update(extra)
        return self.client.post(self._url(), data)

    def test_no_acknowledgement_returns_error(self):
        response = self.client.post(self._url(), {
            'display_name': 'Test User',
            'preferences': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['errors'])
        self.assertContains(response, 'acknowledge')

    def test_no_acknowledgement_preserves_display_name(self):
        response = self.client.post(self._url(), {
            'display_name': 'My Name',
            'preferences': 'they/them',
        })
        self.assertContains(response, 'My Name')
        self.assertContains(response, 'they/them')

    def test_valid_post_creates_event_interest(self):
        self._post()
        self.assertTrue(EventInterest.objects.filter(user=self.user, event=self.event).exists())

    def test_valid_post_redirects(self):
        response = self._post()
        self.assertRedirects(response, self._url(), fetch_redirect_response=False)

    def test_valid_post_shows_received_message(self):
        self._post()
        response = self.client.get(self._url())
        msgs = list(response.context['messages'])
        self.assertEqual(len(msgs), 1)
        self.assertIn('received', str(msgs[0]))

    def test_update_post_shows_updated_message(self):
        self._post()
        self.client.get(self._url())  # consume the first message
        self._post()  # update
        response = self.client.get(self._url())
        msgs = list(response.context['messages'])
        self.assertEqual(len(msgs), 1)
        self.assertIn('updated', str(msgs[0]))

    def test_valid_post_expands_slot_to_hourly_rows(self):
        self._post()
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        # slot is 12:00-15:00 UTC = 3 hours, participant (multi-assign) role only
        hours = EventAvailabilityHour.objects.filter(event_interest=interest)
        self.assertEqual(hours.count(), 3)
        self.assertTrue(all(h.role.multi_assign for h in hours))

    def test_valid_post_single_assign_role_creates_hourly_rows(self):
        single_role = EventRole.objects.filter(multi_assign=False, eventsignupslot__event=self.event).first()
        self._post({f'{single_role.slug}_slots': [str(self.slot.pk)], 'participant_slots': []})
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        hours = EventAvailabilityHour.objects.filter(event_interest=interest)
        self.assertTrue(all(not h.role.multi_assign for h in hours))

    def test_valid_post_same_slot_both_role_types_creates_rows_for_each(self):
        single_role = EventRole.objects.filter(multi_assign=False, eventsignupslot__event=self.event).first()
        self._post({'participant_slots': [str(self.slot.pk)], f'{single_role.slug}_slots': [str(self.slot.pk)]})
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        # 3 hours x 2 roles = 6 rows
        self.assertEqual(EventAvailabilityHour.objects.filter(event_interest=interest).count(), 6)
        multi_assign_values = set(EventAvailabilityHour.objects.filter(event_interest=interest).values_list('role__multi_assign', flat=True))
        self.assertEqual(multi_assign_values, {True, False})

    def test_resubmit_replaces_hourly_rows(self):
        self._post()
        self._post({'participant_slots': []})
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        self.assertEqual(EventAvailabilityHour.objects.filter(event_interest=interest).count(), 0)

    def test_invalid_slot_id_ignored(self):
        self.client.post(self._url(), {
            'display_name': 'Test',
            'acknowledged': '1',
            'participant_slots': ['99999'],
        })
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        self.assertEqual(EventAvailabilityHour.objects.filter(event_interest=interest).count(), 0)

    def test_slot_from_different_event_ignored(self):
        other_event = Event.objects.create(
            name='Other Event', slug='other-event', description='',
            signups_open=True, edits_open=True,
        )
        other_slot = EventSignupSlot.objects.create(
            event=other_event, start=_dt(2025, 4, 4, 12), stop=_dt(2025, 4, 4, 15),
            label='Friday 8am - 11am',
        )
        self.client.post(self._url(), {
            'display_name': 'Test',
            'acknowledged': '1',
            'participant_slots': [str(other_slot.pk)],
        })
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        self.assertEqual(EventAvailabilityHour.objects.filter(event_interest=interest).count(), 0)


class SignupViewGameSelectionTest(TestCase):
    def setUp(self):
        from eventer.models import Game
        self.user = User.objects.create_user('tester', 'tester@example.com', 'pass')
        self.client.login(username='tester', password='pass')
        self.event = _make_event()
        self.slot = EventSignupSlot.objects.filter(event=self.event).first()
        self.game = Game.objects.create(
            name='Test Game', status='approved', suggested=True,
            igdb_id=12345,
        )

    def _url(self):
        return f'/signup/{self.event.slug}/'

    def test_game_selection_creates_game_interest_rows(self):
        from evtsignup.models import GameInterestUserEvent
        self.client.post(self._url(), {
            'acknowledged': '1',
            'participant_games': [str(self.game.pk)],
        })
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        self.assertTrue(GameInterestUserEvent.objects.filter(event_interest=interest, game=self.game).exists())

    def test_resubmit_replaces_game_selections(self):
        from evtsignup.models import GameInterestUserEvent
        self.client.post(self._url(), {
            'acknowledged': '1',
            'participant_games': [str(self.game.pk)],
        })
        self.client.post(self._url(), {'acknowledged': '1'})
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        self.assertEqual(GameInterestUserEvent.objects.filter(event_interest=interest).count(), 0)

    def test_fundraising_url_saved(self):
        self.client.post(self._url(), {
            'acknowledged': '1',
            'fundraising_url': 'https://www.extra-life.org/participants/511438',
        })
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        self.assertEqual(interest.fundraising_url, 'https://www.extra-life.org/participants/511438')

    def test_fundraising_url_blank_stored_as_null(self):
        self.client.post(self._url(), {'acknowledged': '1', 'fundraising_url': ''})
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        self.assertIsNone(interest.fundraising_url)


class SignupViewPrefillTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tester', 'tester@example.com', 'pass')
        self.client.login(username='tester', password='pass')
        self.event = _make_event()
        self.slot = EventSignupSlot.objects.filter(event=self.event).first()

    def _url(self):
        return f'/signup/{self.event.slug}/'

    def _selected_ids_for_slug(self, response, slug):
        for track in response.context['role_tracks']:
            if track['slug'] == slug:
                return track['selected_slot_ids']
        return set()

    def test_reedit_preselects_previously_chosen_slots(self):
        multi_role = EventRole.objects.filter(multi_assign=True).first()
        self.client.post(self._url(), {
            'acknowledged': '1',
            f'{multi_role.slug}_slots': [str(self.slot.pk)],
        })
        response = self.client.get(self._url())
        self.assertIn(self.slot.pk, self._selected_ids_for_slug(response, multi_role.slug))

    def test_reedit_does_not_preselect_unselected_slots(self):
        multi_role = EventRole.objects.filter(multi_assign=True).first()
        self.client.post(self._url(), {'acknowledged': '1'})
        response = self.client.get(self._url())
        self.assertNotIn(self.slot.pk, self._selected_ids_for_slug(response, multi_role.slug))


class GroupSlotsByDayTest(TestCase):
    def setUp(self):
        import zoneinfo
        self.tz = zoneinfo.ZoneInfo('America/New_York')
        self.event = Event.objects.create(
            name='Day Test', slug='day-test', description='',
            timezone='America/New_York',
        )

    def test_slots_on_same_day_grouped_together(self):
        from evtsignup.views import _group_slots_by_day
        # Both slots start on Friday Apr 4 in ET (12 UTC and 15 UTC = 8am and 11am EDT)
        EventSignupSlot.objects.create(event=self.event, start=_dt(2025, 4, 4, 12), stop=_dt(2025, 4, 4, 15), label='8am')
        EventSignupSlot.objects.create(event=self.event, start=_dt(2025, 4, 4, 15), stop=_dt(2025, 4, 4, 18), label='11am')
        groups = _group_slots_by_day(EventSignupSlot.objects.filter(event=self.event).order_by('start'), self.tz)
        self.assertEqual(len(groups), 1)
        _, slots = groups[0]
        self.assertEqual(len(slots), 2)

    def test_slots_crossing_midnight_split_into_two_days(self):
        from evtsignup.views import _group_slots_by_day
        # Friday 11pm EDT = Saturday 03:00 UTC; Saturday 2am EDT = Saturday 06:00 UTC
        EventSignupSlot.objects.create(event=self.event, start=_dt(2025, 4, 4, 23), stop=_dt(2025, 4, 5, 2), label='Fri late')
        EventSignupSlot.objects.create(event=self.event, start=_dt(2025, 4, 5, 6), stop=_dt(2025, 4, 5, 9), label='Sat early')
        groups = _group_slots_by_day(EventSignupSlot.objects.filter(event=self.event).order_by('start'), self.tz)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0][0], 'Friday, April 4')
        self.assertEqual(groups[1][0], 'Saturday, April 5')

    def test_day_label_format(self):
        from evtsignup.views import _group_slots_by_day
        EventSignupSlot.objects.create(event=self.event, start=_dt(2025, 4, 4, 12), stop=_dt(2025, 4, 4, 15), label='8am')
        groups = _group_slots_by_day(EventSignupSlot.objects.filter(event=self.event), self.tz)
        self.assertEqual(groups[0][0], 'Friday, April 4')

    def test_empty_queryset_returns_empty_list(self):
        from evtsignup.views import _group_slots_by_day
        groups = _group_slots_by_day(EventSignupSlot.objects.none(), self.tz)
        self.assertEqual(groups, [])


def _make_backend(name='discord'):
    backend = MagicMock()
    backend.name = name
    return backend


class RequireDiscordGuildTest(TestCase):
    @override_settings(DISCORD_REQUIRED_GUILD_ID='164136635762606081')
    def test_passes_when_user_in_guild(self):
        backend = _make_backend()
        guilds = [{'id': '164136635762606081'}, {'id': '999'}]
        with patch('evtsignup.pipeline.requests.get') as mock_get:
            mock_get.return_value.json.return_value = guilds
            result = require_discord_guild(backend, {'access_token': 'token'})
        self.assertIsNone(result)

    @override_settings(DISCORD_REQUIRED_GUILD_ID='164136635762606081')
    def test_raises_when_user_not_in_guild(self):
        backend = _make_backend()
        guilds = [{'id': '999'}]
        with patch('evtsignup.pipeline.requests.get') as mock_get:
            mock_get.return_value.json.return_value = guilds
            with self.assertRaises(AuthForbidden):
                require_discord_guild(backend, {'access_token': 'token'})

    def test_passes_when_no_guild_id_configured(self):
        backend = _make_backend()
        with self.settings(DISCORD_REQUIRED_GUILD_ID=''):
            result = require_discord_guild(backend, {'access_token': 'token'})
        self.assertIsNone(result)

    def test_skips_non_discord_backends(self):
        backend = _make_backend(name='google-oauth2')
        result = require_discord_guild(backend, {'access_token': 'token'})
        self.assertIsNone(result)

    @override_settings(DISCORD_REQUIRED_GUILD_ID='164136635762606081')
    def test_raises_when_guilds_response_is_not_a_list(self):
        backend = _make_backend()
        with patch('evtsignup.pipeline.requests.get') as mock_get:
            mock_get.return_value.json.return_value = {'error': 'unauthorized'}
            with self.assertRaises(AuthForbidden):
                require_discord_guild(backend, {'access_token': 'token'})


class ParseFundraisingUrlTest(TestCase):
    # --- Empty cases ---

    def test_empty_string(self):
        r = parse_fundraising_url('')
        self.assertEqual(r.type, 'empty')
        self.assertEqual(r.id_or_slug, '')

    def test_none(self):
        r = parse_fundraising_url(None)
        self.assertEqual(r.type, 'empty')

    def test_whitespace_only(self):
        r = parse_fundraising_url('   ')
        self.assertEqual(r.type, 'empty')

    # --- Modern participant URLs ---

    def test_numeric_participant_id(self):
        r = parse_fundraising_url('https://www.extra-life.org/participants/511438')
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, '511438')
        self.assertTrue(r.is_participant)
        self.assertTrue(r.is_extralife)

    def test_vanity_participant_slug(self):
        r = parse_fundraising_url('https://www.extra-life.org/participants/aevumdecessus')
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, 'aevumdecessus')

    def test_participant_url_without_www(self):
        r = parse_fundraising_url('https://extra-life.org/participants/511438')
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, '511438')

    def test_participant_url_with_trailing_slash(self):
        r = parse_fundraising_url('https://www.extra-life.org/participants/511438/')
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, '511438')

    def test_participant_url_with_fragment(self):
        r = parse_fundraising_url('https://www.extra-life.org/participants/511438#donate')
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, '511438')

    # --- Modern team URLs ---

    def test_team_vanity_slug(self):
        r = parse_fundraising_url('https://www.extra-life.org/teams/fragforce-dcm')
        self.assertEqual(r.type, 'team')
        self.assertEqual(r.id_or_slug, 'fragforce-dcm')
        self.assertTrue(r.is_team)
        self.assertTrue(r.is_extralife)

    def test_team_numeric_id(self):
        r = parse_fundraising_url('https://www.extra-life.org/teams/68980')
        self.assertEqual(r.type, 'team')
        self.assertEqual(r.id_or_slug, '68980')

    # --- Legacy cfm URLs ---

    def test_legacy_participant_cfm(self):
        r = parse_fundraising_url(
            'https://www.extra-life.org/index.cfm?fuseaction=donorDrive.participant&participantID=511438'
        )
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, '511438')

    def test_legacy_participant_cfm_portal_home_fuseaction(self):
        # Seen in practice - fuseaction=portal.home but participantID present
        r = parse_fundraising_url(
            'https://www.extra-life.org/index.cfm?fuseaction=portal.home&participantID=514130'
        )
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, '514130')

    def test_legacy_team_cfm(self):
        r = parse_fundraising_url(
            'https://www.extra-life.org/index.cfm?fuseaction=donorDrive.team&teamID=68980'
        )
        self.assertEqual(r.type, 'team')
        self.assertEqual(r.id_or_slug, '68980')

    def test_legacy_donordrive_domain(self):
        r = parse_fundraising_url(
            'https://www.donordrive.com/index.cfm?fuseaction=donorDrive.participant&participantID=533595'
        )
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, '533595')

    # --- Non-EL / other URLs ---

    def test_tiltify_url(self):
        r = parse_fundraising_url('https://tiltify.com/+fragforce/')
        self.assertEqual(r.type, 'other')
        self.assertFalse(r.is_extralife)

    def test_hospital_charity_url(self):
        r = parse_fundraising_url('http://chfou.convio.net/goto/Montscot832')
        self.assertEqual(r.type, 'other')

    def test_shortlink_url(self):
        r = parse_fundraising_url('https://el.pvcp.co')
        self.assertEqual(r.type, 'other')

    def test_not_yet_signed_up_text(self):
        r = parse_fundraising_url('I have not signed up yet')
        self.assertEqual(r.type, 'other')

    def test_bare_text(self):
        r = parse_fundraising_url('some random text')
        self.assertEqual(r.type, 'other')

    # --- raw_url always preserved ---

    def test_raw_url_preserved_for_participant(self):
        url = 'https://www.extra-life.org/participants/511438'
        r = parse_fundraising_url(url)
        self.assertEqual(r.raw_url, url)

    def test_raw_url_preserved_for_other(self):
        url = 'https://tiltify.com/+fragforce/'
        r = parse_fundraising_url(url)
        self.assertEqual(r.raw_url, url)


class EventInterestAdminTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Group

        from eventer.models import Event
        from fforg.permissions import seed_permission_groups
        seed_permission_groups()
        self.coordinator = User.objects.create_user('coord_ei', 'c@example.com', 'pass', is_staff=True)
        self.coordinator.groups.add(Group.objects.get(name='Coordinator'))
        self.client.login(username='coord_ei', password='pass')
        self.event = Event.objects.create(name='Admin Test Event', slug='admin-test-event', description='')
        from evtsignup.models import EventAvailabilityHour, EventInterest
        self.ei = EventInterest.objects.create(
            user=self.coordinator, event=self.event,
            display_name='Test Coord', acknowledged=True,
            fundraising_url='https://extra-life.org/participant/123'
        )
        from datetime import datetime, timezone
        _seed_roles()
        hour = datetime(2025, 4, 4, 8, tzinfo=timezone.utc)
        self.role = EventRole.objects.filter(show_fundraising_url=True).first()
        EventAvailabilityHour.objects.create(event_interest=self.ei, hour=hour, role=self.role)

    def test_list_view_renders(self):
        response = self.client.get('/admin/evtsignup/eventinterest/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Coord')

    def test_list_shows_roles_summary(self):
        response = self.client.get('/admin/evtsignup/eventinterest/')
        self.assertContains(response, self.role.name)

    def test_list_shows_fundraising_boolean(self):
        response = self.client.get('/admin/evtsignup/eventinterest/')
        self.assertEqual(response.status_code, 200)

    def test_change_form_renders_with_igdb_context(self):
        response = self.client.get(f'/admin/evtsignup/eventinterest/{self.ei.pk}/change/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Game selections')

    def test_roles_summary_no_availability(self):
        from eventer.models import Event
        from evtsignup.models import EventInterest
        event2 = Event.objects.create(name='Admin Test 2', slug='admin-test-2', description='')
        ei2 = EventInterest.objects.create(user=self.coordinator, event=event2, acknowledged=True)
        from django.contrib.admin.sites import AdminSite

        from evtsignup.admin import EventInterestAdmin
        admin = EventInterestAdmin(EventInterest, AdminSite())
        self.assertEqual(admin.roles_summary(ei2), '—')

    def test_game_count_zero_shows_dash(self):
        from django.contrib.admin.sites import AdminSite

        from evtsignup.admin import EventInterestAdmin
        from evtsignup.models import EventInterest
        admin = EventInterestAdmin(EventInterest, AdminSite())
        self.assertEqual(admin.game_count(self.ei), '—')


class IsFollowableUrlTest(TestCase):
    def test_https_url_is_followable(self):
        from evtsignup.tasks import _is_followable_url
        self.assertTrue(_is_followable_url('https://el.0n5.us'))

    def test_http_url_is_followable(self):
        from evtsignup.tasks import _is_followable_url
        self.assertTrue(_is_followable_url('http://example.com/path'))

    def test_freetext_is_not_followable(self):
        from evtsignup.tasks import _is_followable_url
        self.assertFalse(_is_followable_url('I have not signed up yet'))

    def test_empty_string_is_not_followable(self):
        from evtsignup.tasks import _is_followable_url
        self.assertFalse(_is_followable_url(''))

    def test_no_dot_in_netloc_is_not_followable(self):
        from evtsignup.tasks import _is_followable_url
        self.assertFalse(_is_followable_url('https://localhost'))

    def test_ftp_is_not_followable(self):
        from evtsignup.tasks import _is_followable_url
        self.assertFalse(_is_followable_url('ftp://example.com'))


class FollowRedirectTest(TestCase):
    def test_returns_final_url_on_success(self):
        from unittest.mock import MagicMock, patch

        from evtsignup.tasks import _follow_redirect
        mock_resp = MagicMock()
        mock_resp.url = 'https://www.extra-life.org/participants/511438'
        with patch('evtsignup.tasks.requests.get', return_value=mock_resp) as mock_get:
            result = _follow_redirect('https://el.0n5.us')
        self.assertEqual(result, 'https://www.extra-life.org/participants/511438')
        mock_get.assert_called_once()

    def test_returns_none_on_network_error(self):
        from unittest.mock import patch

        import requests

        from evtsignup.tasks import _follow_redirect
        with patch('evtsignup.tasks.requests.get', side_effect=requests.exceptions.ConnectionError):
            result = _follow_redirect('https://el.0n5.us')
        self.assertIsNone(result)


class ResolveFundraisingUrlTaskTest(TestCase):
    def setUp(self):
        from eventer.models import Event
        self.user = User.objects.create_user('taskuser', 'tu@example.com', 'pass')
        self.event = Event.objects.create(name='Task Test Event', slug='task-test-event', description='')

    def _make_interest(self, url):
        from evtsignup.models import EventInterest
        return EventInterest.objects.create(
            user=self.user, event=self.event, acknowledged=True, fundraising_url=url
        )

    def test_resolves_participant_url(self):
        from unittest.mock import patch

        from evtsignup.tasks import resolve_fundraising_url
        interest = self._make_interest('https://www.extra-life.org/participants/511438')
        mock_api = {'participantID': 511438, 'displayName': 'AevumDecessus'}
        with patch('evtsignup.tasks.Participants.participant', return_value=mock_api):
            resolve_fundraising_url(interest.pk)
        interest.refresh_from_db()
        self.assertIsNotNone(interest.el_participant)
        self.assertEqual(interest.el_participant.id, 511438)

    def test_skips_if_no_url(self):
        from evtsignup.models import EventInterest
        from evtsignup.tasks import resolve_fundraising_url
        interest = EventInterest.objects.create(
            user=self.user, event=self.event, acknowledged=True
        )
        resolve_fundraising_url(interest.pk)  # should not raise

    def test_logs_team_url(self):
        from evtsignup.tasks import resolve_fundraising_url
        interest = self._make_interest('https://www.extra-life.org/teams/fragforce')
        resolve_fundraising_url(interest.pk)  # should not raise or create participant
        interest.refresh_from_db()
        self.assertIsNone(interest.el_participant)

    def test_follows_redirect_for_vanity_url(self):
        from unittest.mock import patch

        from evtsignup.tasks import resolve_fundraising_url
        interest = self._make_interest('https://el.0n5.us')
        mock_api = {'participantID': 511438, 'displayName': 'AevumDecessus'}
        with patch('evtsignup.tasks._follow_redirect',
                   return_value='https://www.extra-life.org/participants/511438'), \
             patch('evtsignup.tasks.Participants.participant', return_value=mock_api):
            resolve_fundraising_url(interest.pk)
        interest.refresh_from_db()
        self.assertIsNotNone(interest.el_participant)

    def test_skips_redirect_for_freetext(self):
        from unittest.mock import patch

        from evtsignup.tasks import resolve_fundraising_url
        interest = self._make_interest('I have not signed up yet')
        with patch('evtsignup.tasks._follow_redirect') as mock_follow:
            resolve_fundraising_url(interest.pk)
        mock_follow.assert_not_called()

    def test_handles_missing_interest(self):
        from evtsignup.tasks import resolve_fundraising_url
        resolve_fundraising_url(99999)  # should not raise


class SignalQueueTest(TestCase):
    def setUp(self):
        from eventer.models import Event
        self.user = User.objects.create_user('siguser', 'sig@example.com', 'pass')
        self.event = Event.objects.create(name='Signal Test', slug='signal-test', description='')

    def test_queues_task_when_url_set_on_create(self):
        from unittest.mock import patch

        from evtsignup.models import EventInterest
        with patch('evtsignup.tasks.resolve_fundraising_url') as mock_task:
            mock_task.delay = mock_task
            EventInterest.objects.create(
                user=self.user, event=self.event, acknowledged=True,
                fundraising_url='https://www.extra-life.org/participants/511438'
            )
        mock_task.assert_called_once()

    def test_does_not_queue_when_no_url(self):
        from unittest.mock import patch

        from evtsignup.models import EventInterest
        with patch('evtsignup.tasks.resolve_fundraising_url') as mock_task:
            EventInterest.objects.create(
                user=self.user, event=self.event, acknowledged=True
            )
        mock_task.assert_not_called()

    def test_skips_requeue_when_url_unchanged_and_resolved(self):
        from unittest.mock import patch

        from evtsignup.models import EventInterest
        from ffdonations.models import ParticipantModel
        participant = ParticipantModel.objects.create(
            id=511438, displayName='Test', tracked=False
        )
        interest = EventInterest.objects.create(
            user=self.user, event=self.event, acknowledged=True,
            fundraising_url='https://www.extra-life.org/participants/511438',
            el_participant=participant,
        )
        with patch('evtsignup.tasks.resolve_fundraising_url') as mock_task:
            interest.display_name = 'Updated'
            interest.save()
        mock_task.assert_not_called()

    def test_requeues_when_url_changes(self):
        from unittest.mock import patch

        from evtsignup.models import EventInterest
        from ffdonations.models import ParticipantModel
        participant = ParticipantModel.objects.create(
            id=511438, displayName='Test', tracked=False
        )
        interest = EventInterest.objects.create(
            user=self.user, event=self.event, acknowledged=True,
            fundraising_url='https://www.extra-life.org/participants/511438',
            el_participant=participant,
        )
        with patch('evtsignup.tasks.resolve_fundraising_url') as mock_task:
            mock_task.delay = mock_task
            interest.fundraising_url = 'https://www.extra-life.org/participants/999999'
            interest.save()
        mock_task.assert_called_once()


class FundraisingUrlSignalTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('sigtest', 'sig@example.com', 'pass')
        self.event = Event.objects.create(
            name='Signal Test', slug='signal-test', description='',
            signups_open=True, edits_open=True,
        )

    def test_create_with_url_queues_task(self):
        from unittest.mock import patch
        with patch('evtsignup.tasks.resolve_fundraising_url') as mock_task:
            EventInterest.objects.create(
                user=self.user, event=self.event, acknowledged=True,
                fundraising_url='https://extra-life.org/participants/123',
            )
        mock_task.delay.assert_called_once()

    def test_create_without_url_does_not_queue(self):
        from unittest.mock import patch
        with patch('evtsignup.tasks.resolve_fundraising_url') as mock_task:
            EventInterest.objects.create(
                user=self.user, event=self.event, acknowledged=True,
            )
        mock_task.delay.assert_not_called()

    def test_update_url_queues_task(self):
        from unittest.mock import patch
        interest = EventInterest.objects.create(
            user=self.user, event=self.event, acknowledged=True,
            fundraising_url='https://extra-life.org/participants/123',
        )
        with patch('evtsignup.tasks.resolve_fundraising_url') as mock_task:
            interest.fundraising_url = 'https://extra-life.org/participants/456'
            interest.save()
        mock_task.delay.assert_called_once()

    def test_update_other_field_does_not_queue(self):
        from unittest.mock import patch
        interest = EventInterest.objects.create(
            user=self.user, event=self.event, acknowledged=True,
            fundraising_url='https://extra-life.org/participants/123',
        )
        with patch('evtsignup.tasks.resolve_fundraising_url') as mock_task:
            interest.display_name = 'New Name'
            interest.save(update_fields=['display_name'])
        mock_task.delay.assert_not_called()

    def test_update_unchanged_url_without_el_participant_queues(self):
        from unittest.mock import patch
        interest = EventInterest.objects.create(
            user=self.user, event=self.event, acknowledged=True,
            fundraising_url='https://extra-life.org/participants/123',
        )
        with patch('evtsignup.tasks.resolve_fundraising_url') as mock_task:
            interest.save()
        mock_task.delay.assert_called_once()

    def test_update_unchanged_url_with_el_participant_does_not_queue(self):
        from unittest.mock import patch

        from ffdonations.models import ParticipantModel
        participant = ParticipantModel.objects.create(
            id=99991, displayName='Test', sumDonations=0,
            numDonations=0, fundraisingGoal=0,
        )
        interest = EventInterest.objects.create(
            user=self.user, event=self.event, acknowledged=True,
            fundraising_url='https://extra-life.org/participants/99991',
            el_participant=participant,
        )
        with patch('evtsignup.tasks.resolve_fundraising_url') as mock_task:
            interest.display_name = 'Changed Name'
            interest.save()
        mock_task.delay.assert_not_called()

    def test_url_resolution_attempts_reset_on_url_change(self):
        interest = EventInterest.objects.create(
            user=self.user, event=self.event, acknowledged=True,
            fundraising_url='https://extra-life.org/participants/123',
            url_resolution_attempts=3,
        )
        from unittest.mock import patch
        with patch('evtsignup.tasks.resolve_fundraising_url'):
            interest.fundraising_url = 'https://extra-life.org/participants/456'
            interest.save()
        interest.refresh_from_db()
        self.assertEqual(interest.url_resolution_attempts, 0)
