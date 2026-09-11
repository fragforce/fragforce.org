from django.contrib import admin

from evtsignup.models import EventAvailabilityHour, EventInterest, EventInterestNote, GameInterestUserEvent


class GameInterestInline(admin.TabularInline):
    model = GameInterestUserEvent
    extra = 0
    fields = ['game', 'role']
    autocomplete_fields = ['game']
    verbose_name = 'Game selection'
    verbose_name_plural = 'Game selections'


@admin.register(EventInterest)
class EventInterestAdmin(admin.ModelAdmin):
    list_display = [
        'display_name_or_user', 'event', 'roles_summary',
        'game_count', 'has_fundraising_url', 'acknowledged',
    ]
    list_filter = ['event', 'acknowledged']
    search_fields = ['display_name', 'user__username', 'eventinterestnote__notes']
    raw_id_fields = ['el_participant']
    readonly_fields = ['user', 'event']
    inlines = [GameInterestInline]
    change_form_template = 'admin/evtsignup/eventinterest/change_form.html'

    def get_queryset(self, request):
        return super().get_queryset(request).distinct()

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        from eventer.igdb import IGDBClient
        from eventer.models import EventRole
        extra_context = extra_context or {}
        extra_context['event_roles'] = EventRole.objects.order_by('name')
        extra_context['igdb_configured'] = IGDBClient.credentials_configured()
        return super().changeform_view(request, object_id, form_url, extra_context)

    @admin.display(description='Signup', ordering='display_name')
    def display_name_or_user(self, obj):
        return obj.display_name or obj.user.username

    @admin.display(description='Roles')
    def roles_summary(self, obj):
        slugs = obj.eventavailabilityhour_set.values_list('role__name', flat=True).distinct()
        names = sorted(set(slugs))
        return ', '.join(names) if names else '—'

    @admin.display(description='Games', ordering='gameinterestuserevent')
    def game_count(self, obj):
        count = obj.gameinterestuserevent_set.count()
        return count if count else '—'

    @admin.display(description='Fundraising', boolean=True)
    def has_fundraising_url(self, obj):
        return bool(obj.fundraising_url)


@admin.register(GameInterestUserEvent)
class GameInterestUserEventAdmin(admin.ModelAdmin):
    list_display = ['event_interest', 'game', 'role']
    list_filter = ['role', 'event_interest__event']
    search_fields = ['event_interest__display_name', 'event_interest__user__username', 'game__name']
    autocomplete_fields = ['game']


@admin.register(EventAvailabilityHour)
class EventAvailabilityHourAdmin(admin.ModelAdmin):
    list_display = ['event_interest', 'hour', 'role']
    list_filter = ['role', 'event_interest__event']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('role', 'event_interest')


@admin.register(EventInterestNote)
class EventInterestNoteAdmin(admin.ModelAdmin):
    list_display = ['event_interest', 'role', 'notes']
    list_filter = ['role', 'event_interest__event']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('role', 'event_interest')
