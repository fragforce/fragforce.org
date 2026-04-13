from django.contrib.auth.models import Group, User
from django.test import TestCase

from ffdiscord.models import DiscordRole, DiscordRoleMapping
from ffdiscord.utils import sync_guild_roles, sync_user_roles
from ffdiscord.validators import (
    discord_bot_token_valid,
    discord_oauth_credentials_valid,
)

VALID_CLIENT_ID = '123456789012345678'  # 18-digit snowflake  # NOSONAR
VALID_CLIENT_SECRET = 'abcDEF123_-abcDEF123_-abcDEF1234'  # 32 chars  # NOSONAR
VALID_BOT_TOKEN = 'MTestToken1234567890123456.AAAAAA.BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB'  # NOSONAR


class DiscordOAuthCredentialsValidTest(TestCase):
    def test_valid_credentials(self):
        self.assertTrue(discord_oauth_credentials_valid(VALID_CLIENT_ID, VALID_CLIENT_SECRET))

    def test_empty_client_id(self):
        self.assertFalse(discord_oauth_credentials_valid('', VALID_CLIENT_SECRET))

    def test_none_client_id(self):
        self.assertFalse(discord_oauth_credentials_valid(None, VALID_CLIENT_SECRET))

    def test_non_numeric_client_id(self):
        self.assertFalse(discord_oauth_credentials_valid('abc123abc123abc123', VALID_CLIENT_SECRET))

    def test_client_id_too_short(self):
        self.assertFalse(discord_oauth_credentials_valid('1234567890123456', VALID_CLIENT_SECRET))

    def test_client_id_too_long(self):
        self.assertFalse(discord_oauth_credentials_valid('123456789012345678901', VALID_CLIENT_SECRET))

    def test_empty_client_secret(self):
        self.assertFalse(discord_oauth_credentials_valid(VALID_CLIENT_ID, ''))

    def test_none_client_secret(self):
        self.assertFalse(discord_oauth_credentials_valid(VALID_CLIENT_ID, None))

    def test_client_secret_wrong_length(self):
        self.assertFalse(discord_oauth_credentials_valid(VALID_CLIENT_ID, 'tooshort'))

    def test_client_secret_invalid_chars(self):
        self.assertFalse(discord_oauth_credentials_valid(VALID_CLIENT_ID, 'abcDEF123!@abcDEF123!@abcDEF12'))


class DiscordBotTokenValidTest(TestCase):
    def test_valid_token_starts_with_M(self):
        token = 'M' + 'A' * 25 + '.' + 'B' * 6 + '.' + 'C' * 38
        self.assertTrue(discord_bot_token_valid(token))

    def test_valid_token_starts_with_N(self):
        token = 'N' + 'A' * 25 + '.' + 'B' * 6 + '.' + 'C' * 38
        self.assertTrue(discord_bot_token_valid(token))

    def test_empty_token(self):
        self.assertFalse(discord_bot_token_valid(''))

    def test_none_token(self):
        self.assertFalse(discord_bot_token_valid(None))

    def test_wrong_starting_char(self):
        token = 'X' + 'A' * 25 + '.' + 'B' * 6 + '.' + 'C' * 38
        self.assertFalse(discord_bot_token_valid(token))

    def test_wrong_part1_length(self):
        token = 'M' + 'A' * 24 + '.' + 'B' * 6 + '.' + 'C' * 38
        self.assertFalse(discord_bot_token_valid(token))

    def test_wrong_part2_length(self):
        token = 'M' + 'A' * 25 + '.' + 'B' * 5 + '.' + 'C' * 38
        self.assertFalse(discord_bot_token_valid(token))

    def test_wrong_part3_length(self):
        token = 'M' + 'A' * 25 + '.' + 'B' * 6 + '.' + 'C' * 37
        self.assertFalse(discord_bot_token_valid(token))

    def test_missing_dots(self):
        self.assertFalse(discord_bot_token_valid('M' + 'A' * 70))


class SyncGuildRolesTest(TestCase):
    def test_creates_new_roles(self):
        sync_guild_roles([('111', 'Admin'), ('222', 'Streamer')])
        self.assertEqual(DiscordRole.objects.count(), 2)
        self.assertTrue(DiscordRole.objects.filter(discord_role_id='111', name='Admin').exists())

    def test_updates_existing_role_name(self):
        DiscordRole.objects.create(discord_role_id='111', name='OldName')
        sync_guild_roles([('111', 'NewName')])
        self.assertEqual(DiscordRole.objects.get(discord_role_id='111').name, 'NewName')

    def test_handles_empty_list(self):
        sync_guild_roles([])
        self.assertEqual(DiscordRole.objects.count(), 0)

    def test_upserts_multiple_roles(self):
        DiscordRole.objects.create(discord_role_id='111', name='Existing')
        sync_guild_roles([('111', 'Updated'), ('222', 'New')])
        self.assertEqual(DiscordRole.objects.count(), 2)
        self.assertEqual(DiscordRole.objects.get(discord_role_id='111').name, 'Updated')


class SyncUserRolesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='streamer')
        self.role = DiscordRole.objects.create(discord_role_id='111', name='Streamer')
        self.group = Group.objects.create(name='streamers')
        self.mapping = DiscordRoleMapping.objects.create(role=self.role, group=self.group)

    def test_adds_entitled_group(self):
        sync_user_roles(self.user, ['111'])
        self.assertIn(self.group, self.user.groups.all())

    def test_removes_unentitled_group(self):
        self.user.groups.add(self.group)
        sync_user_roles(self.user, [])
        self.assertNotIn(self.group, self.user.groups.all())

    def test_no_change_when_correct(self):
        self.user.groups.add(self.group)
        sync_user_roles(self.user, ['111'])
        self.assertIn(self.group, self.user.groups.all())

    def test_early_return_when_no_mappings(self):
        DiscordRoleMapping.objects.all().delete()
        self.user.groups.add(self.group)
        sync_user_roles(self.user, [])
        # Should not remove group since there are no mappings to manage
        self.assertIn(self.group, self.user.groups.all())

    def test_grants_staff_access(self):
        self.mapping.grants_staff_access = True
        self.mapping.save()
        sync_user_roles(self.user, ['111'])
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_staff)

    def test_revokes_staff_access(self):
        self.mapping.grants_staff_access = True
        self.mapping.save()
        self.user.is_staff = True
        self.user.save()
        self.user.groups.add(self.group)
        sync_user_roles(self.user, [])
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)

    def test_staff_not_set_without_grants_staff_access(self):
        sync_user_roles(self.user, ['111'])
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
