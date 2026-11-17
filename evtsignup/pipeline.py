import logging

import requests
from django.conf import settings
from social_core.exceptions import AuthPolicyError

log = logging.getLogger(__name__)


def require_discord_guild(backend, response, *args, **kwargs):
    """Deny login if the user is not a member of the required Discord guild."""
    if backend.name != 'discord':
        return
    required_guild_id = settings.DISCORD_REQUIRED_GUILD_ID
    if not required_guild_id:
        return
    access_token = kwargs.get('access_token') or (response or {}).get('access_token', '')
    guilds = requests.get(
        'https://discord.com/api/users/@me/guilds',
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=10,
    ).json()
    if not isinstance(guilds, list):
        log.warning("Discord guilds API returned unexpected response: %r", guilds)
        raise AuthPolicyError(backend, code="membership_required", stage="pipeline")
    guild_ids = {str(g['id']) for g in guilds}
    if str(required_guild_id) not in guild_ids:
        log.warning("User not in required guild %s", required_guild_id)
        raise AuthPolicyError(backend, code="membership_required", stage="pipeline")
