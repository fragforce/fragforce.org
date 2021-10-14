from django.contrib import admin

from .models import *


class KeyAdmin(admin.ModelAdmin):
    date_hierarchy = "modified"
    list_filter = (
        "is_live",
        "active",
        "livestream",
        "pull",
    )
    ordering = ("-modified",)
    sortable_by = (
        "name",
        "id",
        "created",
        "modified",
        "is_live",
        "active",
        "livestream",
        "pull",
    )
    list_display = (
        "name",
        "id",
        "created",
        "modified",
        "is_live",
        "active",
        "livestream",
        "pull",
    )
    search_fields = (
        "name",
        "id",
        )


# Register your models here.
admin.site.register(Key, KeyAdmin)
admin.site.register(Stream)
