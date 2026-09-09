"""
Central permission group definitions for Fragforce.

Groups and their permissions are defined here and seeded automatically
after every migration via a post_migrate signal in ffsite/apps.py.

To add a new permission to a group, add it to the relevant GROUP_PERMISSIONS
entry and it will be applied on next deploy.

To apply immediately in a running environment:
    pipenv run python manage.py seed_permission_groups
"""
import logging

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

log = logging.getLogger(__name__)


# (app_label, model_name, [actions])
COORDINATOR_PERMISSIONS = [
    # eventer - full access to event setup and schedule management
    ('eventer', 'event', ['add', 'change', 'delete', 'view', 'view_coordinator_schedule']),
    ('eventer', 'eventperiod', ['add', 'change', 'delete', 'view']),
    ('eventer', 'eventrole', ['add', 'change', 'delete', 'view']),
    ('eventer', 'eventsignupslotconfig', ['add', 'change', 'delete', 'view']),
    ('eventer', 'eventsignupslot', ['add', 'change', 'delete', 'view']),
    ('eventer', 'game', ['add', 'change', 'delete', 'view', 'search_igdb']),
    ('eventer', 'team', ['add', 'change', 'view']),
    ('eventer', 'teamrole', ['view']),
    ('eventer', 'teammember', ['view']),

    # evtsignup - view signups, no delete
    ('evtsignup', 'eventinterest', ['view']),
    ('evtsignup', 'eventavailabilityhour', ['view']),
    ('evtsignup', 'eventinterestnote', ['view']),
    ('evtsignup', 'gameinterestuserevent', ['view']),

    # auth - view users for autocomplete search in schedule tools
    ('auth', 'user', ['view']),
]

SUPERSTREAM_MODERATOR_PERMISSIONS = [
    ('eventer', 'event', ['view_coordinator_schedule']),
]

SUPERSTREAM_TECH_MANAGER_PERMISSIONS = [
    ('eventer', 'event', ['view_coordinator_schedule']),
]

SUPERSTREAM_KEY_MANAGER_PERMISSIONS = [
    ('ffstream', 'key', ['view', 'change']),
    ('ffstream', 'key', ['set_key_superstream']),
]

LIVESTREAM_KEY_MANAGER_PERMISSIONS = [
    ('ffstream', 'key', ['view', 'change']),
    ('ffstream', 'key', ['set_key_livestream']),
]

GROUP_DEFINITIONS = {
    'Coordinator': COORDINATOR_PERMISSIONS,
    'Superstream Moderator': SUPERSTREAM_MODERATOR_PERMISSIONS,
    'Superstream Tech Manager': SUPERSTREAM_TECH_MANAGER_PERMISSIONS,
    'Superstream Key Manager': SUPERSTREAM_KEY_MANAGER_PERMISSIONS,
    'Livestream Key Manager': LIVESTREAM_KEY_MANAGER_PERMISSIONS,
}


def _collect_permissions(permission_list):
    """
    Resolve (app_label, model_name, actions) tuples to Permission objects.

    For standard CRUD actions ('add', 'change', 'delete', 'view'), the codename
    is built as '{action}_{model_name}'. For custom permissions the codename is
    used as-is (e.g. 'set_key_superstream' stays 'set_key_superstream').
    """
    standard_actions = {'add', 'change', 'delete', 'view'}
    permissions = []
    missing = []
    for app_label, model_name, actions in permission_list:
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist:
            missing.append(f'{app_label}.{model_name}')
            continue
        for action in actions:
            codename = f'{action}_{model_name}' if action in standard_actions else action
            try:
                permissions.append(Permission.objects.get(content_type=ct, codename=codename))
            except Permission.DoesNotExist:
                missing.append(f'{app_label}.{codename}')
    return permissions, missing


def seed_permission_groups(**kwargs):
    """
    Idempotently create/update all permission groups.
    Safe to call multiple times - connected to post_migrate signal.
    """
    for group_name, permission_list in GROUP_DEFINITIONS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        permissions, missing = _collect_permissions(permission_list)
        group.permissions.set(permissions)
        log.debug("Seeded group '%s' with %d permission(s).", group_name, len(permissions))
        if missing:
            log.warning(
                "Group '%s': missing permissions (run after all migrations): %s",
                group_name, ', '.join(missing),
            )
