from django.contrib.auth.models import User
from django.test import TestCase

from evtsignup.models import DiscordEventUser
from ffbot.utils import get_or_create_stream_key, get_or_register_user
from ffstream.models import Key
from social_django.models import UserSocialAuth


class GetOrRegisterUserTest(TestCase):
    def test_returns_existing_user_via_discord_event_user(self):
        user = User.objects.create_user(username='existing')
        DiscordEventUser.objects.create(user=user, discord_id='111111111111111111')
        result = get_or_register_user('111111111111111111', 'existing')
        self.assertEqual(result, user)
        self.assertEqual(User.objects.count(), 1)

    def test_returns_existing_user_via_social_auth(self):
        user = User.objects.create_user(username='webuser')
        UserSocialAuth.objects.create(user=user, provider='discord', uid='222222222222222222', extra_data={})
        result = get_or_register_user('222222222222222222', 'webuser')
        self.assertEqual(result, user)
        self.assertEqual(User.objects.count(), 1)

    def test_creates_new_user_with_correct_records(self):
        result = get_or_register_user('333333333333333333', 'newuser')
        self.assertEqual(result.username, 'newuser')
        self.assertTrue(DiscordEventUser.objects.filter(user=result, discord_id='333333333333333333').exists())
        self.assertTrue(UserSocialAuth.objects.filter(user=result, provider='discord', uid='333333333333333333').exists())

    def test_handles_username_collision(self):
        User.objects.create_user(username='streamer')
        result = get_or_register_user('444444444444444444', 'streamer')
        self.assertNotEqual(result.username, 'streamer')
        self.assertIn('streamer', result.username)

    def test_slugifies_username_with_periods(self):
        result = get_or_register_user('555555555555555555', 'aevum.decessus')
        self.assertEqual(result.username, 'aevum-decessus')

    def test_creates_user_with_empty_email(self):
        result = get_or_register_user('666666666666666666', 'nomail')
        self.assertEqual(result.email, '')


class GetOrCreateStreamKeyTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='streamer')

    def test_returns_existing_key(self):
        key = Key.objects.create(name='streamer', owner=self.user)
        result = get_or_create_stream_key(self.user)
        self.assertEqual(result.pk, key.pk)
        self.assertEqual(Key.objects.filter(owner=self.user).count(), 1)

    def test_creates_new_key_for_user(self):
        result = get_or_create_stream_key(self.user)
        self.assertEqual(result.owner, self.user)

    def test_new_key_has_superstream_false(self):
        result = get_or_create_stream_key(self.user)
        self.assertFalse(result.superstream)

    def test_new_key_has_livestream_false(self):
        result = get_or_create_stream_key(self.user)
        self.assertFalse(result.livestream)

    def test_handles_name_collision(self):
        other = User.objects.create_user(username='other')
        Key.objects.create(name='streamer', owner=other)
        result = get_or_create_stream_key(self.user)
        self.assertNotEqual(result.name, 'streamer')
        self.assertEqual(result.owner, self.user)

    def test_handles_stream_key_collision(self):
        from unittest.mock import patch
        from ffstream.wordlist import generate_stream_key as real_gen
        existing = Key.objects.create(name='collision', stream_key='CollisionKey')
        call_count = {'n': 0}

        def patched():
            call_count['n'] += 1
            if call_count['n'] == 1:
                return existing.stream_key
            return real_gen()

        with patch('ffbot.utils.generate_stream_key', patched):
            result = get_or_create_stream_key(self.user)
        self.assertNotEqual(result.stream_key, existing.stream_key)
        self.assertGreaterEqual(call_count['n'], 2)
