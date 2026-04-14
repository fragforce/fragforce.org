import re

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from ffstream.models import Key, Stream
from ffstream.wordlist import WORDS, generate_stream_key

# Test credentials - not real secrets
TEST_PASSWORD = 'pass'


class MyKeysViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='streamer', password=TEST_PASSWORD)
        self.other_user = User.objects.create_user(username='other', password=TEST_PASSWORD)
        self.key = Key.objects.create(stream_key='secret-key-1', name='streamer', owner=self.user)
        self.other_key = Key.objects.create(stream_key='secret-key-2', name='other', owner=self.other_user)

    def test_redirects_unauthenticated_users(self):
        response = self.client.get(reverse('my-keys'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/discord/', response['Location'])

    def test_shows_own_keys(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        response = self.client.get(reverse('my-keys'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'secret-key-1')

    def test_does_not_show_other_users_keys(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        response = self.client.get(reverse('my-keys'))
        self.assertNotContains(response, 'secret-key-2')

    def test_shows_empty_state_when_no_keys(self):
        User.objects.create_user(username='nokeys', password=TEST_PASSWORD)
        self.client.login(username='nokeys', password=TEST_PASSWORD)
        response = self.client.get(reverse('my-keys'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "don't have a stream key yet")


class LogoutViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='streamer', password=TEST_PASSWORD)

    def test_logout_redirects_to_home(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, '/')

    def test_logout_ends_session(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        self.client.post(reverse('logout'))
        response = self.client.get(reverse('my-keys'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/discord/', response['Location'])

    def test_logout_rejects_get(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)


class GenerateKeyViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='streamer', password=TEST_PASSWORD)

    def test_generates_key_for_user(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        self.client.post(reverse('generate-key'))
        key = Key.objects.get(owner=self.user)
        self.assertIsNotNone(key)

    def test_generated_key_has_superstream_false(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        self.client.post(reverse('generate-key'))
        key = Key.objects.get(owner=self.user)
        self.assertFalse(key.superstream)

    def test_generated_key_has_livestream_false(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        self.client.post(reverse('generate-key'))
        key = Key.objects.get(owner=self.user)
        self.assertFalse(key.livestream)

    def test_does_not_generate_second_key(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        self.client.post(reverse('generate-key'))
        self.client.post(reverse('generate-key'))
        self.assertEqual(Key.objects.filter(owner=self.user).count(), 1)

    def test_redirects_to_my_keys(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        response = self.client.post(reverse('generate-key'))
        self.assertRedirects(response, reverse('my-keys'))

    def test_rejects_get(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        response = self.client.get(reverse('generate-key'))
        self.assertEqual(response.status_code, 405)

    def test_requires_login(self):
        response = self.client.post(reverse('generate-key'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/discord/', response['Location'])

    def test_claims_existing_unowned_key_with_matching_name(self):
        # Pre-existing key with the user's username but no owner (legacy data)
        existing = Key.objects.create(name='streamer', stream_key='OldLegacyKeyValue')
        self.client.login(username='streamer', password=TEST_PASSWORD)
        self.client.post(reverse('generate-key'))
        existing.refresh_from_db()
        self.assertEqual(existing.owner, self.user)
        self.assertEqual(Key.objects.filter(owner=self.user).count(), 1)

    def test_avoids_name_collision_with_owned_key(self):
        # Key with user's username already owned by someone else
        other = User.objects.create_user(username='other', password=TEST_PASSWORD)
        Key.objects.create(name='streamer', owner=other)
        self.client.login(username='streamer', password=TEST_PASSWORD)
        self.client.post(reverse('generate-key'))
        key = Key.objects.get(owner=self.user)
        self.assertNotEqual(key.name, 'streamer')

    def test_username_with_period_produces_valid_slug_name(self):
        # Discord usernames can contain periods which are not valid in SlugField
        user = User.objects.create_user(username='aevum.decessus', password=TEST_PASSWORD)
        self.client.login(username='aevum.decessus', password=TEST_PASSWORD)
        self.client.post(reverse('generate-key'))
        key = Key.objects.get(owner=user)
        self.assertNotIn('.', key.name)

    def test_username_with_period_claims_dotted_legacy_key(self):
        # A key may already exist with the dotted username from before slugification
        user = User.objects.create_user(username='aevum.decessus', password=TEST_PASSWORD)
        existing = Key.objects.create(name='aevum.decessus', stream_key='LegacyDottedKey')
        self.client.login(username='aevum.decessus', password=TEST_PASSWORD)
        self.client.post(reverse('generate-key'))
        key = Key.objects.get(owner=user)
        self.assertEqual(key.pk, existing.pk)
        self.assertNotIn('.', key.name)


class RegenerateKeyViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='streamer', password=TEST_PASSWORD)
        self.key = Key.objects.create(name='streamer', owner=self.user, superstream=False, livestream=False)

    def test_regenerates_key(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        old_stream_key = self.key.stream_key
        self.client.post(reverse('regenerate-key'))
        new_key = Key.objects.get(owner=self.user)
        self.assertNotEqual(new_key.stream_key, old_stream_key)

    def test_does_not_change_superstream_or_livestream(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        self.client.post(reverse('regenerate-key'))
        new_key = Key.objects.get(owner=self.user)
        self.assertFalse(new_key.superstream)
        self.assertFalse(new_key.livestream)

    def test_redirects_to_my_keys(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        response = self.client.post(reverse('regenerate-key'))
        self.assertRedirects(response, reverse('my-keys'))

    def test_rejects_get(self):
        self.client.login(username='streamer', password=TEST_PASSWORD)
        response = self.client.get(reverse('regenerate-key'))
        self.assertEqual(response.status_code, 405)

    def test_requires_login(self):
        response = self.client.post(reverse('regenerate-key'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/discord/', response['Location'])


class StreamKeyGeneratorTest(TestCase):
    def test_generates_four_words(self):
        key = generate_stream_key()
        words = re.findall(r'[A-Z][a-z]+', key)
        self.assertEqual(len(words), 4)

    def test_each_word_is_in_wordlist(self):
        for _ in range(20):
            key = generate_stream_key()
            words = re.findall(r'[A-Z][a-z]+', key)
            for word in words:
                self.assertIn(word, WORDS)

    def test_words_are_capitalized(self):
        key = generate_stream_key()
        words = re.findall(r'[A-Z][a-z]+', key)
        for word in words:
            self.assertTrue(word[0].isupper())
            self.assertTrue(word[1:].islower())

    def test_wordlist_has_minimum_size(self):
        # Ensure the wordlist has enough words for good randomness
        self.assertGreaterEqual(len(WORDS), 50)

    def test_generated_key_is_unique(self):
        from unittest.mock import patch
        # Force a collision on the first attempt
        existing = Key.objects.create(name='collision-test', stream_key='CollisionKeyValue')
        call_count = {'n': 0}
        original = __import__('ffstream.wordlist', fromlist=['generate_stream_key']).generate_stream_key

        def patched():
            call_count['n'] += 1
            if call_count['n'] == 1:
                return existing.stream_key  # collide first
            return original()

        with patch('ffstream.models.generate_stream_key', patched):
            key = Key(name='new-key')
            key.save()
        self.assertNotEqual(key.stream_key, existing.stream_key)
        self.assertGreaterEqual(call_count['n'], 2)

    def test_stream_key_auto_generated_on_save(self):
        key = Key(name='auto-gen-test')
        key.save()
        self.assertIsNotNone(key.stream_key)
        self.assertNotEqual(key.stream_key, '')
        words = re.findall(r'[A-Z][a-z]+', key.stream_key)
        self.assertEqual(len(words), 4)

    def test_existing_stream_key_not_overwritten_on_save(self):
        key = Key(name='manual-key', stream_key='ManualKeyValue')
        key.save()
        self.assertEqual(key.stream_key, 'ManualKeyValue')


class KeyOwnerConstraintTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='streamer', password=TEST_PASSWORD)
        self.key1 = Key.objects.create(name='key1', owner=self.user)
        self.key2 = Key.objects.create(name='key2')

    def test_one_key_per_user(self):
        self.key2.owner = self.user
        with self.assertRaises(IntegrityError):
            self.key2.save()

    def test_multiple_unowned_keys_allowed(self):
        key3 = Key.objects.create(name='key3')
        self.assertIsNone(key3.owner)


class StreamingViewOwnerCheckTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='streamer', password=TEST_PASSWORD)
        self.owned_key = Key.objects.create(name='owned', owner=self.user, superstream=True, livestream=True)
        self.unowned_key = Key.objects.create(name='unowned', superstream=True, livestream=True)

    def test_start_blocks_ownerless_key(self):
        response = self.client.post(reverse('pub-start'), {'name': self.unowned_key.stream_key})
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'no owner', response.content)

    def test_start_srt_blocks_ownerless_key(self):
        response = self.client.post(reverse('pub-start-srt'), {'name': self.unowned_key.stream_key})
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'no owner', response.content)

    def test_start_livestream_blocks_ownerless_key(self):
        response = self.client.post(reverse('pub-start-livestream'), {'name': self.unowned_key.stream_key})
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'no owner', response.content)

    def test_start_blocks_non_superstream_key(self):
        self.owned_key.superstream = False
        self.owned_key.save()
        response = self.client.post(reverse('pub-start'), {'name': self.owned_key.stream_key})
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'Super Stream', response.content)

    def test_start_livestream_does_not_check_superstream(self):
        self.owned_key.superstream = False
        self.owned_key.save()
        response = self.client.post(reverse('pub-start-livestream'), {'name': self.owned_key.stream_key})
        # Should not be blocked by superstream - proceeds past that check
        self.assertNotIn(b'Super Stream', response.content)

    def test_start_livestream_blocks_non_livestream_key(self):
        self.owned_key.livestream = False
        self.owned_key.save()
        response = self.client.post(reverse('pub-start-livestream'), {'name': self.owned_key.stream_key})
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'not allowed to livestream', response.content)


class StopViewTest(TestCase):
    def setUp(self):
        from django.utils import timezone as tz
        self.user = User.objects.create_user(username='streamer', password=TEST_PASSWORD)
        self.key = Key.objects.create(name='streamer', owner=self.user, superstream=True, is_live=True)
        self.stream1 = Stream.objects.create(key=self.key, is_live=True, started=tz.now())
        self.stream2 = Stream.objects.create(key=self.key, is_live=True, started=tz.now())

    def test_sets_key_is_live_false(self):
        self.client.post(reverse('pub-stop'), {'name': self.key.stream_key})
        self.key.refresh_from_db()
        self.assertFalse(self.key.is_live)

    def test_ends_all_active_streams(self):
        self.client.post(reverse('pub-stop'), {'name': self.key.stream_key})
        self.stream1.refresh_from_db()
        self.stream2.refresh_from_db()
        self.assertFalse(self.stream1.is_live)
        self.assertFalse(self.stream2.is_live)
        self.assertIsNotNone(self.stream1.ended)
        self.assertIsNotNone(self.stream2.ended)

    def test_only_ends_streams_where_ended_is_none(self):
        from django.utils import timezone as tz
        already_ended = Stream.objects.create(
            key=self.key, is_live=False, started=tz.now(), ended=tz.now()
        )
        self.client.post(reverse('pub-stop'), {'name': self.key.stream_key})
        already_ended.refresh_from_db()
        self.assertFalse(already_ended.is_live)  # unchanged

    def test_nonexistent_key_returns_404(self):
        response = self.client.post(reverse('pub-stop'), {'name': 'NonExistentKey'})
        self.assertEqual(response.status_code, 404)

    def test_returns_ok(self):
        response = self.client.post(reverse('pub-stop'), {'name': self.key.stream_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'OK')


class PlayViewTest(TestCase):
    def setUp(self):
        from django.utils import timezone as tz
        pull_key_owner = User.objects.create_user(username='pull-key-owner', password=TEST_PASSWORD)
        stream_owner = User.objects.create_user(username='stream-owner', password=TEST_PASSWORD)
        self.pull_key = Key.objects.create(name='pull', owner=pull_key_owner, pull=True)
        self.stream_key = Key.objects.create(name='streamer', owner=stream_owner, superstream=True)
        self.stream = Stream.objects.create(key=self.stream_key, is_live=True, started=tz.now())

    def test_missing_key_param_returns_403(self):
        response = self.client.post(reverse('pub-play'), {'name': 'streamer'})
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'no key given', response.content)

    def test_non_pull_key_returns_403(self):
        non_pull_owner = User.objects.create_user(username='non-pull-owner', password=TEST_PASSWORD)
        non_pull = Key.objects.create(name='nonpull', owner=non_pull_owner, pull=False)
        response = self.client.post(reverse('pub-play'), {
            'name': 'streamer',
            'key': non_pull.stream_key,
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'not a pull key', response.content)

    def test_no_active_stream_returns_403(self):
        self.stream.is_live = False
        self.stream.save()
        response = self.client.post(reverse('pub-play'), {
            'name': 'streamer',
            'key': self.pull_key.stream_key,
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'inactive stream', response.content)

    def test_self_pull_superstream_redirects(self):
        # self-pull: use the stream key as both pull key and stream key
        response = self.client.post(reverse('pub-play'), {
            'name': self.stream_key.name,
            'key': self.stream_key.stream_key,
        })
        self.assertEqual(response.status_code, 302)

    def test_pull_key_redirects_to_active_stream(self):
        response = self.client.post(reverse('pub-play'), {
            'name': 'streamer',
            'key': self.pull_key.stream_key,
        })
        self.assertEqual(response.status_code, 302)


class ViewEndpointTest(TestCase):
    def setUp(self):
        pull_key_owner = User.objects.create_user(username='pull-key-owner', password=TEST_PASSWORD)
        no_pull_key_owner = User.objects.create_user(username='no-pull-key-owner', password=TEST_PASSWORD)
        self.pull_key = Key.objects.create(name='pull', owner=pull_key_owner, pull=True)
        self.no_pull_key = Key.objects.create(name='nopull', owner=no_pull_key_owner, pull=False)

    def test_require_safe_rejects_post(self):
        response = self.client.post(reverse('view', args=[self.pull_key.stream_key]))
        self.assertEqual(response.status_code, 405)

    def test_non_pull_key_returns_403(self):
        response = self.client.get(reverse('view', args=[self.no_pull_key.stream_key]))
        self.assertEqual(response.status_code, 403)

    def test_nonexistent_key_returns_404(self):
        response = self.client.get(reverse('view', args=['NonExistentKey']))
        self.assertEqual(response.status_code, 404)

    def test_valid_pull_key_renders_template(self):
        response = self.client.get(reverse('view', args=[self.pull_key.stream_key]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ffstream/view.html')


class GotoViewTest(TestCase):
    def setUp(self):
        from django.utils import timezone as tz
        pull_key_owner = User.objects.create_user(username='pull-key-owner', password=TEST_PASSWORD)
        no_pull_key_owner = User.objects.create_user(username='no-pull-key-owner', password=TEST_PASSWORD)
        stream_owner = User.objects.create_user(username='stream-owner', password=TEST_PASSWORD)
        self.pull_key = Key.objects.create(name='pull', owner=pull_key_owner, pull=True)
        self.no_pull_key = Key.objects.create(name='nopull', owner=no_pull_key_owner, pull=False)
        self.stream_key = Key.objects.create(name='streamer', owner=stream_owner)
        self.stream = Stream.objects.create(key=self.stream_key, is_live=True, started=tz.now())

    def test_require_safe_rejects_post(self):
        response = self.client.post(
            reverse('goto', args=[self.pull_key.stream_key, 'streamer'])
        )
        self.assertEqual(response.status_code, 405)

    def test_non_pull_key_returns_403(self):
        response = self.client.get(
            reverse('goto', args=[self.no_pull_key.stream_key, 'streamer'])
        )
        self.assertEqual(response.status_code, 403)

    def test_nonexistent_pull_key_returns_404(self):
        response = self.client.get(
            reverse('goto', args=['NonExistentKey', 'streamer'])
        )
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_stream_name_returns_404(self):
        response = self.client.get(
            reverse('goto', args=[self.pull_key.stream_key, 'nonexistent'])
        )
        self.assertEqual(response.status_code, 404)

    def test_active_stream_redirects_to_url(self):
        response = self.client.get(
            reverse('goto', args=[self.pull_key.stream_key, 'streamer'])
        )
        self.assertEqual(response.status_code, 302)
