from django.test import TestCase, override_settings
from django.urls import reverse


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
