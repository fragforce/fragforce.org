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
