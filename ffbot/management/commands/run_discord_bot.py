import logging

import discord
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand

from ffbot.utils import get_or_create_stream_key, get_or_register_user
from ffdiscord.utils import sync_user_roles
from ffdiscord.validators import discord_bot_token_valid

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run the Fragforce Discord bot'

    def handle(self, *args, **options):
        if not discord_bot_token_valid(settings.DISCORD_BOT_TOKEN):
            raise SystemExit("DISCORD_BOT_TOKEN is missing or invalid - bot cannot start.")

        intents = discord.Intents.default()
        bot = discord.Bot(intents=intents)

        guild_ids = [int(settings.DISCORD_REQUIRED_GUILD_ID)] if settings.DISCORD_REQUIRED_GUILD_ID else None

        @bot.event
        async def on_ready():
            log.info("Fragforce bot logged in as %s (ID: %s)", bot.user, bot.user.id)

        @bot.slash_command(
            name="stream-key",
            description="Fetch your stream key",
            guild_ids=guild_ids,
        )
        async def stream_key(ctx):
            discord_id = str(ctx.author.id)
            discord_username = ctx.author.name

            role_ids = [str(r.id) for r in ctx.author.roles]

            def get_key():
                user = get_or_register_user(discord_id, discord_username)
                sync_user_roles(user, role_ids)
                return get_or_create_stream_key(user)

            key = await sync_to_async(get_key)()

            await ctx.respond(
                f"**Your Stream Key:** `{key.stream_key}`\n"
                f"Super Stream: {'Yes' if key.superstream else 'No'} | "
                f"Direct Livestream: {'Yes' if key.livestream else 'No'}",
                ephemeral=True,
            )

        bot.run(settings.DISCORD_BOT_TOKEN)
