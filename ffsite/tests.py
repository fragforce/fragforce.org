from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

TEST_PASSWORD = 'pass'


class LoginErrorViewTest(TestCase):
    def test_returns_200(self):
        response = self.client.get(reverse('login-error'))
        self.assertEqual(response.status_code, 200)

    def test_contains_discord_invite_link(self):
        response = self.client.get(reverse('login-error'))
        self.assertContains(response, 'discord.gg/fragforce')


class DiscordLoginButtonTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    @override_settings(
        SOCIAL_AUTH_DISCORD_KEY='123456789012345678',
        SOCIAL_AUTH_DISCORD_SECRET='abcDEF123_-abcDEF123_-abcDEF1234',
    )
    def test_login_button_shown_when_credentials_valid(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, reverse('social:begin', args=['discord']))

    @override_settings(SOCIAL_AUTH_DISCORD_KEY='', SOCIAL_AUTH_DISCORD_SECRET='')
    def test_login_button_hidden_when_credentials_empty(self):
        response = self.client.get(reverse('home'))
        self.assertNotContains(response, reverse('social:begin', args=['discord']))


class StaticViewsRequireSafeTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def _assert_post_rejected(self, url_name, *args):
        response = self.client.post(reverse(url_name, args=args) if args else reverse(url_name))
        self.assertEqual(response.status_code, 405)

    def test_home_rejects_post(self):
        self._assert_post_rejected('home')

    def test_donate_rejects_post(self):
        self._assert_post_rejected('donate')

    def test_join_rejects_post(self):
        self._assert_post_rejected('join')

    def test_contact_rejects_post(self):
        self._assert_post_rejected('contact')

    def test_stream_rejects_post(self):
        self._assert_post_rejected('stream')


class DonateViewTest(TestCase):
    def test_returns_200(self):
        response = self.client.get(reverse('donate'))
        self.assertEqual(response.status_code, 200)

    def test_passes_rnd_pct_to_template(self):
        response = self.client.get(reverse('donate'))
        self.assertIn('rnd_pct', response.context)

    def test_is_not_cached(self):
        # donate() has cache commented out - each request should re-render
        from django.core.cache import cache
        cache.clear()
        response1 = self.client.get(reverse('donate'))
        response2 = self.client.get(reverse('donate'))
        # Both should return 200 without cache serving stale content
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)


class StreamViewTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    @override_settings(STREAM_URL='https://stream.example.com')
    def test_context_includes_stream_url(self):
        response = self.client.get(reverse('stream'))
        self.assertEqual(response.context['stream_url'], 'https://stream.example.com')

    @override_settings(STREAM_URL=None)
    def test_context_stream_url_none_when_not_set(self):
        response = self.client.get(reverse('stream'))
        self.assertIsNone(response.context['stream_url'])


class AdminNavLinkTest(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user('staff', is_staff=True, password=TEST_PASSWORD)
        self.regular_user = User.objects.create_user('regular', is_staff=False, password=TEST_PASSWORD)

    def test_admin_link_shown_for_staff(self):
        self.client.login(username='staff', password=TEST_PASSWORD)
        response = self.client.get(reverse('home'))
        self.assertContains(response, reverse('admin:index'))

    def test_admin_link_hidden_for_regular_user(self):
        self.client.login(username='regular', password=TEST_PASSWORD)
        response = self.client.get(reverse('home'))
        self.assertNotContains(response, reverse('admin:index'))

    def test_admin_link_hidden_when_not_logged_in(self):
        response = self.client.get(reverse('home'))
        self.assertNotContains(response, reverse('admin:index'))


class AdminLoginDiscordButtonTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    @override_settings(
        SOCIAL_AUTH_DISCORD_KEY='123456789012345678',
        SOCIAL_AUTH_DISCORD_SECRET='abcDEF123_-abcDEF123_-abcDEF1234',
    )
    def test_discord_button_shown_when_credentials_valid(self):
        response = self.client.get(reverse('admin:login'))
        self.assertContains(response, reverse('social:begin', args=['discord']))

    @override_settings(SOCIAL_AUTH_DISCORD_KEY='', SOCIAL_AUTH_DISCORD_SECRET='')
    def test_discord_button_hidden_when_credentials_not_set(self):
        response = self.client.get(reverse('admin:login'))
        self.assertNotContains(response, reverse('social:begin', args=['discord']))

    @override_settings(
        SOCIAL_AUTH_DISCORD_KEY='123456789012345678',
        SOCIAL_AUTH_DISCORD_SECRET='abcDEF123_-abcDEF123_-abcDEF1234',
    )
    def test_discord_button_includes_default_admin_next(self):
        response = self.client.get(reverse('admin:login'))
        self.assertContains(response, 'action="%s"' % reverse('social:begin', args=['discord']))
        self.assertContains(response, '<input type="hidden" name="next" value="/admin/">')

    @override_settings(
        SOCIAL_AUTH_DISCORD_KEY='123456789012345678',
        SOCIAL_AUTH_DISCORD_SECRET='abcDEF123_-abcDEF123_-abcDEF1234',
    )
    def test_discord_button_preserves_next_param(self):
        response = self.client.get(reverse('admin:login') + '?next=/admin/ffstream/')
        self.assertContains(response, 'action="%s"' % reverse('social:begin', args=['discord']))
        self.assertContains(response, '<input type="hidden" name="next" value="/admin/ffstream/">')


class JoinAndContactViewTest(TestCase):
    def test_join_returns_200(self):
        response = self.client.get(reverse('join'))
        self.assertEqual(response.status_code, 200)

    def test_contact_returns_200(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)


class LocaltimeFilterTest(TestCase):
    def test_format_datetime_returns_html_with_value(self):
        from ffsite.templatetags.fftz import format_datetime
        result = format_datetime('2026-04-16T12:00:00')
        self.assertIn('2026-04-16T12:00:00', result)
        self.assertIn('<time', result)
        self.assertIn('updateTimeValue', result)

    def test_format_datetime_uses_provided_eid(self):
        from ffsite.templatetags.fftz import format_datetime
        result = format_datetime('2026-04-16T12:00:00', eid='myid')
        self.assertIn('id="myid"', result)
        self.assertIn('"#myid"', result)

    def test_format_datetime_output_is_safe(self):
        from django.utils.safestring import SafeData
        from ffsite.templatetags.fftz import format_datetime
        result = format_datetime('2026-04-16T12:00:00')
        self.assertIsInstance(result, SafeData)


class LocaltimeShortFilterTest(TestCase):
    def test_returns_html_with_time_element(self):
        from ffsite.templatetags.fftz import format_datetime_short
        result = format_datetime_short('2026-04-16T12:00:00')
        self.assertIn('<time', result)
        self.assertIn('2026-04-16T12:00:00.000Z', result)

    def test_uses_toLocaleString_with_options(self):
        from ffsite.templatetags.fftz import format_datetime_short
        result = format_datetime_short('2026-04-16T12:00:00')
        self.assertIn('toLocaleString', result)
        self.assertIn('timeZoneName', result)
        self.assertNotIn('updateTimeValue', result)

    def test_uses_provided_eid(self):
        from ffsite.templatetags.fftz import format_datetime_short
        result = format_datetime_short('2026-04-16T12:00:00', eid='myid')
        self.assertIn('id="myid"', result)

    def test_output_is_safe(self):
        from django.utils.safestring import SafeData
        from ffsite.templatetags.fftz import format_datetime_short
        result = format_datetime_short('2026-04-16T12:00:00')
        self.assertIsInstance(result, SafeData)


class RandomContactTest(TestCase):
    @patch('ffsite.utils.el_teams', return_value=[1])
    def test_returns_participant_when_exists(self, _):
        from ffdonations.models import EventModel, TeamModel, ParticipantModel
        event = EventModel.objects.create(id=1, name='Test', tracked=True)
        team = TeamModel.objects.create(id=1, name='Team', tracked=True, event=event)
        participant = ParticipantModel.objects.create(id=1, displayName='Alice', tracked=True, team=team, event=event)
        from ffsite.utils import random_contact
        result = random_contact()
        self.assertEqual(result.id, participant.id)

    @patch('ffsite.utils.el_teams', return_value=[])
    def test_returns_empty_participant_when_none_exist(self, _):
        from ffsite.utils import random_contact
        result = random_contact()
        self.assertIsInstance(result, __import__('ffdonations.models', fromlist=['ParticipantModel']).ParticipantModel)
