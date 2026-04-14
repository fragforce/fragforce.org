from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from social_core.exceptions import AuthForbidden

from evtsignup.models import DiscordEventUser
from evtsignup.pipeline import require_discord_guild, save_discord_id


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


class SaveDiscordIdTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.backend = _make_backend()

    def test_creates_discord_event_user(self):
        save_discord_id(self.backend, self.user, {'id': '123456789'})
        deu = DiscordEventUser.objects.get(user=self.user)
        self.assertEqual(deu.discord_id, '123456789')

    def test_updates_existing_discord_event_user(self):
        DiscordEventUser.objects.create(user=self.user, discord_id='old_id')
        save_discord_id(self.backend, self.user, {'id': '999999'})
        deu = DiscordEventUser.objects.get(user=self.user)
        self.assertEqual(deu.discord_id, '999999')

    def test_skips_when_no_discord_id_in_response(self):
        save_discord_id(self.backend, self.user, {})
        self.assertFalse(DiscordEventUser.objects.filter(user=self.user).exists())

    def test_skips_non_discord_backends(self):
        backend = _make_backend(name='google-oauth2')
        save_discord_id(backend, self.user, {'id': '123'})
        self.assertFalse(DiscordEventUser.objects.filter(user=self.user).exists())

    def test_discord_id_as_integer_is_stringified(self):
        # Discord may return the id as an integer in some contexts
        save_discord_id(self.backend, self.user, {'id': 123456789})
        deu = DiscordEventUser.objects.get(user=self.user)
        self.assertEqual(deu.discord_id, '123456789')
        self.assertIsInstance(deu.discord_id, str)

    def test_skips_when_discord_id_is_empty_string_after_stringify(self):
        save_discord_id(self.backend, self.user, {'id': ''})
        self.assertFalse(DiscordEventUser.objects.filter(user=self.user).exists())

    def test_each_user_gets_own_discord_event_user(self):
        user2 = User.objects.create_user(username='testuser2')
        save_discord_id(self.backend, self.user, {'id': '111111111'})
        save_discord_id(self.backend, user2, {'id': '222222222'})
        self.assertEqual(DiscordEventUser.objects.get(user=self.user).discord_id, '111111111')
        self.assertEqual(DiscordEventUser.objects.get(user=user2).discord_id, '222222222')
