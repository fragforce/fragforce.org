import re

# Discord client ID is a snowflake: decimal digits, 17-20 chars
DISCORD_CLIENT_ID_RE = re.compile(r'^\d{17,20}$')

# Discord client secret: 32 chars, lowercase, uppercase, digits, underscore, dash
DISCORD_CLIENT_SECRET_RE = re.compile(r'^[a-zA-Z0-9_-]{32}$')

# Discord bot token: MN + 25 chars . 6 chars . 38 chars
DISCORD_BOT_TOKEN_RE = re.compile(r'^[MN][A-Za-z0-9]{25}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{38}$')


def discord_oauth_credentials_valid(client_id: str, client_secret: str) -> bool:
    return bool(
        DISCORD_CLIENT_ID_RE.match(client_id or '') and
        DISCORD_CLIENT_SECRET_RE.match(client_secret or '')
    )


def discord_bot_token_valid(token: str) -> bool:
    return bool(DISCORD_BOT_TOKEN_RE.match(token or ''))
