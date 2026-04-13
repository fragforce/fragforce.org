from django.test import TestCase

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
