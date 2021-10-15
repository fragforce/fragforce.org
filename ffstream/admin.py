from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from .models import *


class ActiveBooleanDefault(SimpleListFilter):
    title = "Can be used for streaming"
    parameter_name = 'active'

    def lookups(self, request, model_admin):
        return (
            ('all', 'All'),
            (1, 'Yes'),
            (None, 'No')
        )

    def choices(self, changelist):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == (str(lookup) if lookup else lookup),
                'query_string': changelist.get_query_string({self.parameter_name: lookup}, []),
                'display': title,
            }

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == "all":
                return queryset
            else:
                return queryset.filter(**{self.parameter_name: self.value()})
        elif self.value() is None:
            return queryset.filter(**{self.parameter_name: False})


class KeyAdmin(admin.ModelAdmin):
    date_hierarchy = "modified"
    list_filter = (
        "is_live",
        #"active",
        ActiveBooleanDefault,
        "livestream",
        "pull",
    )
    orderin:g = ("-modified",)
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
