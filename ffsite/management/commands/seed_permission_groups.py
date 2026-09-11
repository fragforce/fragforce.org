from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from fforg.permissions import GROUP_DEFINITIONS, _collect_permissions


class Command(BaseCommand):
    help = "Create or update all permission groups defined in fforg/permissions.py."

    def handle(self, *args, **options):
        for group_name, permission_list in GROUP_DEFINITIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            action = 'Created' if created else 'Updated'
            permissions, missing = _collect_permissions(permission_list)
            group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(
                f"{action} '{group_name}' with {len(permissions)} permission(s)."
            ))
            if missing:
                self.stdout.write(self.style.WARNING(
                    f"  Missing (run after all migrations): {', '.join(missing)}"
                ))
