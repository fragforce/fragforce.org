import logging

from django.contrib.auth.models import User
from django.utils.text import slugify
from social_django.models import UserSocialAuth

from ffstream.models import Key
from ffstream.wordlist import generate_stream_key

log = logging.getLogger(__name__)


def get_or_create_stream_key(user: User) -> Key:
    """Get or create a stream key for a user."""
    key = Key.objects.filter(owner=user).first()
    if key:
        return key

    safe_name = slugify(user.username.replace('.', '-'))
    name = safe_name
    suffix = 1
    while Key.objects.filter(name=name).exists():
        name = f"{safe_name}-{suffix}"
        suffix += 1

    candidate = generate_stream_key()
    while Key.objects.filter(stream_key=candidate).exists():
        candidate = generate_stream_key()

    return Key.objects.create(
        name=name,
        stream_key=candidate,
        owner=user,
        superstream=False,
        livestream=False,
    )


def get_or_register_user(discord_id: str, discord_username: str) -> User:
    """Get or create a Django User for a Discord user.

    If the user already exists (via previous bot interaction or web OAuth),
    return them. Otherwise create a new account and link it to the Discord ID
    so that a future web OAuth login will associate the same account.
    """
    # Already linked via social auth
    try:
        return UserSocialAuth.objects.get(provider='discord', uid=discord_id).user
    except UserSocialAuth.DoesNotExist:
        pass

    # New user - create account
    base_username = slugify(discord_username.replace('.', '-'))
    username = base_username
    suffix = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}-{suffix}"
        suffix += 1

    user = User.objects.create_user(username=username, email='')
    UserSocialAuth.objects.create(user=user, provider='discord', uid=discord_id, extra_data={})

    log.info("Registered new user %s from Discord ID %s", username, discord_id)
    return user
