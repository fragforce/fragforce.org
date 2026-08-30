import logging
import zoneinfo

from django import forms

log = logging.getLogger(__name__)
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path

from eventer.models import Event, EventPeriod, EventRole, EventSignupSlotConfig, EventSignupSlot, EventScheduleAssignment, EventScheduleMultiAssignment, EventSlotGroup, EventSlotGroupMembership, Game, Team, TeamMember, TeamRole, HOUR_SECONDS
from eventer.schedule import build_schedule_grid, LOCAL_TIME_FMT
from eventer.slot_generator import generate_slots

def _save_coordinator_assignment(event, slot, role, user):
    """Create EventInterest, availability rows, and schedule assignment for a coordinator-sourced signup."""
    from datetime import timedelta
    from evtsignup.models import EventInterest, EventAvailabilityHour

    interest, _ = EventInterest.objects.get_or_create(
        user=user, event=event,
        defaults={'acknowledged': True},
    )
    hour = slot.start.replace(minute=0, second=0, microsecond=0)
    while hour < slot.stop:
        EventAvailabilityHour.objects.get_or_create(
            event_interest=interest, hour=hour, role=role,
        )
        hour += timedelta(hours=1)
    EventScheduleAssignment.objects.filter(slot=slot, role=role).delete()
    EventScheduleAssignment.objects.create(event=event, slot=slot, role=role, user=user)





@admin.register(EventPeriod)
class EventPeriodAdmin(admin.ModelAdmin):
    pass


class ColorPickerWidget(forms.MultiWidget):
    """Color picker + hex text input side by side."""
    def __init__(self):
        widgets = [
            forms.TextInput(attrs={'type': 'color', 'style': 'width:3em;height:2em;padding:0;cursor:pointer;vertical-align:middle'}),
            forms.TextInput(attrs={'style': 'width:7em;font-family:monospace;vertical-align:middle', 'maxlength': '7', 'placeholder': '#417690'}),
        ]
        super().__init__(widgets)

    def decompress(self, value):
        return [value, value] if value else ['#417690', '#417690']

    def value_from_datadict(self, data, files, name):
        # Text input (hex) takes precedence; sync both to the same value
        values = super().value_from_datadict(data, files, name)
        return values[1] if values[1] else values[0]


class EventRoleAdminForm(forms.ModelForm):
    color = forms.CharField(widget=ColorPickerWidget(), max_length=7)

    class Meta:
        model = EventRole
        fields = [
            'name', 'slug', 'description',
            'color', 'display_order',
            'multi_assign',
            'has_game_selection', 'game_min_players',
            'show_notes', 'show_fundraising_url', 'show_stream_commands',
        ]


@admin.register(EventRole)
class EventRoleAdmin(admin.ModelAdmin):
    form = EventRoleAdminForm
    list_display = [
        'name', 'slug', 'color_swatch', 'display_order',
        'multi_assign',
        'has_game_selection', 'show_notes', 'show_fundraising_url', 'show_stream_commands',
    ]
    list_filter = [
        'multi_assign',
        'has_game_selection', 'show_notes', 'show_fundraising_url', 'show_stream_commands',
    ]
    ordering = ['display_order', 'name']
    search_fields = ['name', 'slug']

    @admin.display(description='Color')
    def color_swatch(self, obj):
        from django.utils.html import format_html
        return format_html(
            '<span style="display:inline-block;width:1.2em;height:1.2em;background:{};border:1px solid #ccc;vertical-align:middle;border-radius:2px;margin-right:4px"></span>{}',
            obj.color, obj.color
        )

    class Media:
        js = ('admin/js/eventrole_color_sync.js',)


class HasEventPeriodFilter(admin.SimpleListFilter):
    title = 'event period'
    parameter_name = 'has_period'

    def lookups(self, request, model_admin):
        return [
            ('yes', 'Scheduled (has period)'),
            ('no', 'Unscheduled (no period)'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(eventperiod__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(eventperiod__isnull=True)
        return queryset


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    change_form_template = 'admin/eventer/event/change_form.html'
    list_display = ['name', 'slug', 'event_start']
    list_filter = [HasEventPeriodFilter]
    prepopulated_fields = {'slug': ('name',)}

    def response_add(self, request, obj, post_url_continue=None):
        return HttpResponseRedirect(f'../../eventsignupslotconfig/add/?event={obj.pk}')

    @admin.display(description='Start', ordering='eventperiod__start')
    def event_start(self, obj):
        period = obj.eventperiod_set.order_by('start').first()
        if period is None:
            return '-'
        tz = zoneinfo.ZoneInfo(obj.timezone)
        return period.start.astimezone(tz).strftime('%Y-%m-%d %H:%M %Z')

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:event_id>/setup-superstream/',
                 self.admin_site.admin_view(self.setup_superstream_view),
                 name='eventer_event_setup_superstream'),
            path('<int:event_id>/generate-slots/',
                 self.admin_site.admin_view(self.generate_slots_view),
                 name='eventer_event_generate_slots'),
            path('<int:event_id>/availability/',
                 self.admin_site.admin_view(self.availability_summary_view),
                 name='eventer_event_availability_summary'),
            path('<int:event_id>/build-schedule/',
                 self.admin_site.admin_view(self.build_schedule_view),
                 name='eventer_event_build_schedule'),
            path('<int:event_id>/assign-slot/',
                 self.admin_site.admin_view(self.assign_slot_view),
                 name='eventer_event_assign_slot'),
            path('<int:event_id>/add-availability/',
                 self.admin_site.admin_view(self.add_availability_view),
                 name='eventer_event_add_availability'),
            path('<int:event_id>/assign-multi-slot/',
                 self.admin_site.admin_view(self.assign_multi_slot_view),
                 name='eventer_event_assign_multi_slot'),
            path('<int:event_id>/remove-multi-slot/',
                 self.admin_site.admin_view(self.remove_multi_slot_view),
                 name='eventer_event_remove_multi_slot'),
        ]
        return custom + urls

    def setup_superstream_view(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        existing_periods = list(event.eventperiod_set.all())
        errors = None

        if request.method == 'POST':
            start_str = request.POST.get('start', '').strip()
            duration_str = request.POST.get('duration', '40').strip()
            try:
                duration = int(duration_str)
                if duration < 1:
                    raise ValueError("Duration must be at least 1 hour")
                # Parse the datetime-local value (naive, in event's timezone)
                from datetime import datetime, timedelta
                naive_start = datetime.strptime(start_str, '%Y-%m-%dT%H:%M')
                tz = zoneinfo.ZoneInfo(event.timezone)
                local_start = naive_start.replace(tzinfo=tz)
                utc_start = local_start.astimezone(zoneinfo.ZoneInfo('UTC'))
                utc_stop = utc_start + timedelta(hours=duration)
                EventPeriod.objects.create(event=event, start=utc_start, stop=utc_stop)
                self.message_user(
                    request,
                    f"Added {duration}-hour period starting {local_start.strftime('%Y-%m-%d %H:%M %Z')}",
                    messages.SUCCESS,
                )
                return HttpResponseRedirect(f'../../{event_id}/generate-slots/')
            except (ValueError, KeyError) as e:
                errors = str(e)

        context = {
            **self.admin_site.each_context(request),
            'event': event,
            'existing_periods': existing_periods,
            'errors': errors,
            'form_start': '',
            'title': f'Add Superstream Period - {event.name}',
        }
        return render(request, 'admin/eventer/event/setup_superstream.html', context)

    def generate_slots_view(self, request, event_id):
        from evtsignup.models import EventInterest
        event = get_object_or_404(Event, pk=event_id)
        errors = None

        if request.method == 'POST':
            replace = request.POST.get('replace') == '1'
            signup_count = EventInterest.objects.filter(event=event).count()
            if replace and signup_count > 0 and request.POST.get('confirm_replace_with_signups') != '1':
                errors = (
                    f"This event has {signup_count} existing signup(s). Check the confirmation box to proceed with regeneration."
                )
            else:
                try:
                    result = generate_slots(event, replace=replace)
                    self.message_user(
                        request,
                        f"Generated slots: {result['created']} created, "
                        f"{result['skipped']} already existed, "
                        f"{result['deleted']} deleted.",
                        messages.SUCCESS,
                    )
                    if result.get('empty_groups'):
                        self.message_user(
                            request,
                            f"Warning: the following slot groups have no role memberships and were skipped: "
                            f"{', '.join(result['empty_groups'])}. Add roles to these groups to generate slots for them.",
                            messages.WARNING,
                        )
                    return HttpResponseRedirect(f'../../{event_id}/change/')
                except ValueError as e:
                    errors = str(e)

        existing_slots = list(event.signup_slots.prefetch_related('roles').order_by('start'))
        signup_count = EventInterest.objects.filter(event=event).count()
        context = {
            **self.admin_site.each_context(request),
            'event': event,
            'existing_slots': existing_slots,
            'existing_count': len(existing_slots),
            'signup_count': signup_count,
            'errors': errors,
            'title': f'Generate Signup Slots - {event.name}',
        }
        return render(request, 'admin/eventer/event/generate_slots.html', context)

    def availability_summary_view(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        grid = build_schedule_grid(event)
        approved_games = Game.objects.filter(status='approved').order_by('name')
        context = {
            **self.admin_site.each_context(request),
            'event': event,
            'rows': grid['rows'],
            'role_headers': grid['role_headers'],
            'multi_role_headers': grid['multi_role_headers'],
            'approved_games': approved_games,
            'title': f'Availability Summary - {event.name}',
        }
        return render(request, 'admin/eventer/event/availability_summary.html', context)

    def build_schedule_view(self, request, event_id):
        from django.db import transaction
        event = get_object_or_404(Event, pk=event_id)

        if request.method == 'POST':
            multi_slugs = set(EventRole.objects.filter(multi_assign=True).values_list('slug', flat=True))
            # Batch-load slots, roles, users, and games referenced in POST before the loop
            slot_ids = set()
            role_slugs = set()
            user_ids_post = set()
            game_ids_post = set()
            seen_keys = set()
            for key in request.POST:
                if not key.startswith('assign_') or key in seen_keys:
                    continue
                seen_keys.add(key)
                try:
                    _, slot_pk, role_slug = key.split('_', 2)
                    slot_ids.add(int(slot_pk))
                    role_slugs.add(role_slug)
                    for uid in request.POST.getlist(key):
                        if uid:
                            user_ids_post.add(int(uid))
                    gid = request.POST.get(f'game_{slot_pk}')
                    if gid:
                        game_ids_post.add(int(gid))
                except (ValueError, AttributeError):
                    continue

            slots_by_pk = {s.pk: s for s in EventSignupSlot.objects.filter(pk__in=slot_ids, event=event)}
            roles_by_slug = {r.slug: r for r in EventRole.objects.filter(slug__in=role_slugs)}
            users_by_pk = {u.pk: u for u in User.objects.filter(pk__in=user_ids_post)}
            games_by_pk = {g.pk: g for g in Game.objects.filter(pk__in=game_ids_post)}

            with transaction.atomic():
                EventScheduleAssignment.objects.filter(event=event).delete()
                EventScheduleMultiAssignment.objects.filter(event=event).delete()
                created = 0
                for key in seen_keys:
                    try:
                        _, slot_pk, role_slug = key.split('_', 2)
                    except (ValueError, AttributeError):
                        log.warning('build_schedule_view: malformed POST key %r, skipping', key)
                        continue
                    slot = slots_by_pk.get(int(slot_pk))
                    role = roles_by_slug.get(role_slug)
                    if not slot or not role:
                        continue
                    for user_id in request.POST.getlist(key):
                        if not user_id:
                            continue
                        user = users_by_pk.get(int(user_id))
                        if not user:
                            continue
                        if role_slug in multi_slugs:
                            EventScheduleMultiAssignment.objects.create(event=event, slot=slot, role=role, user=user)
                        else:
                            game_id = request.POST.get(f'game_{slot_pk}') or None
                            game = games_by_pk.get(int(game_id)) if game_id else None
                            EventScheduleAssignment.objects.create(event=event, slot=slot, role=role, user=user, game=game)
                        created += 1
            self.message_user(request, f"Schedule saved: {created} assignment(s).", messages.SUCCESS)
            return HttpResponseRedirect(f'../../{event_id}/build-schedule/')

        grid = build_schedule_grid(event)
        approved_games = Game.objects.filter(status='approved').order_by('name')
        context = {
            **self.admin_site.each_context(request),
            'event': event,
            'rows': grid['rows'],
            'role_headers': grid['role_headers'],
            'multi_role_headers': grid['multi_role_headers'],
            'approved_games': approved_games,
            'title': f'Build Schedule - {event.name}',
        }
        return render(request, 'admin/eventer/event/build_schedule.html', context)

    def assign_slot_view(self, request, event_id):
        """Assign or unassign a single slot/role - inline fine-tuning from availability grid."""
        if request.method != 'POST':
            return HttpResponseRedirect(f'../../{event_id}/availability/')
        event = get_object_or_404(Event, pk=event_id)
        slot_pk = request.POST.get('slot_pk')
        role_slug = request.POST.get('role_slug')
        user_id = request.POST.get('user_id', '').strip()
        game_id = request.POST.get('game_id', '').strip()
        try:
            slot = EventSignupSlot.objects.get(pk=int(slot_pk), event=event)
            role = EventRole.objects.get(slug=role_slug)
            game = Game.objects.get(pk=int(game_id)) if game_id else None
            EventScheduleAssignment.objects.filter(slot=slot, role=role).delete()
            if user_id:
                user = User.objects.get(pk=int(user_id))
                EventScheduleAssignment.objects.create(event=event, slot=slot, role=role, user=user, game=game)
                self.message_user(request, f"Assigned {user.username} to {slot.label} ({role.name}).", messages.SUCCESS)
            else:
                self.message_user(request, f"Cleared assignment for {slot.label} ({role.name}).", messages.INFO)
        except Exception as e:
            self.message_user(request, f"Error: {e}", messages.ERROR)
        return HttpResponseRedirect(f'../../{event_id}/availability/')

    def add_availability_view(self, request, event_id):
        """
        Dedicated page: coordinator assigns a user to a slot outside the normal signup flow.
        GET: show form with slot/role pre-filled and user select.
        POST: create EventInterest + EventAvailabilityInterest rows + EventScheduleAssignment.
        """
        from django import forms as django_forms

        event = get_object_or_404(Event, pk=event_id)
        slot_pk = request.POST.get('slot_pk') or request.GET.get('slot')
        role_slug = request.POST.get('role_slug') or request.GET.get('role')
        override = (request.POST.get('override') or request.GET.get('override')) == '1'
        slot = get_object_or_404(EventSignupSlot, pk=slot_pk, event=event)
        role = get_object_or_404(EventRole, slug=role_slug)

        class AddAvailabilityForm(django_forms.Form):
            user = django_forms.ModelChoiceField(
                queryset=User.objects.all().order_by('username'),
                widget=django_forms.Select(attrs={'style': 'width:100%'}),
                empty_label='-- Select user --',
            )

        errors = None
        if request.method == 'POST':
            form = AddAvailabilityForm(request.POST)
            if form.is_valid():
                try:
                    _save_coordinator_assignment(event, slot, role, form.cleaned_data['user'])
                    action = "Override assigned" if override else "Added signup and assigned"
                    self.message_user(
                        request,
                        f"{action} {form.cleaned_data['user'].username} to {slot.label} ({role.name}).",
                        messages.SUCCESS,
                    )
                    return HttpResponseRedirect(f'../../{event_id}/availability/')
                except Exception as e:
                    errors = str(e)
        else:
            form = AddAvailabilityForm()

        context = {
            **self.admin_site.each_context(request),
            'event': event, 'slot': slot, 'role': role,
            'override': override, 'form': form, 'errors': errors,
            'title': f'{"Override Assign" if override else "Add Signup & Assign"} - {slot.label} ({role.name})',
        }
        return render(request, 'admin/eventer/event/add_availability.html', context)

    def _multi_slot_view(self, request, event_id, action):
        """Add or remove a user from a multi-assignment slot. action: 'assign' or 'remove'."""
        if request.method != 'POST':
            return HttpResponseRedirect(f'../../{event_id}/availability/')
        event = get_object_or_404(Event, pk=event_id)
        slot_pk = request.POST.get('slot_pk')
        role_slug = request.POST.get('role_slug')
        user_id = request.POST.get('user_id', '').strip()
        try:
            slot = EventSignupSlot.objects.get(pk=int(slot_pk), event=event)
            role = EventRole.objects.get(slug=role_slug)
            user = User.objects.get(pk=int(user_id))
            if action == 'assign':
                EventScheduleMultiAssignment.objects.get_or_create(event=event, slot=slot, role=role, user=user)
                self.message_user(request, f"Added {user.username} to {slot.label} ({role.name}).", messages.SUCCESS)
            else:
                EventScheduleMultiAssignment.objects.filter(event=event, slot=slot, role=role, user=user).delete()
                self.message_user(request, f"Removed {user.username} from {slot.label} ({role.name}).", messages.INFO)
        except Exception as e:
            self.message_user(request, f"Error: {e}", messages.ERROR)
        return HttpResponseRedirect(f'../../{event_id}/availability/')

    def assign_multi_slot_view(self, request, event_id):
        return self._multi_slot_view(request, event_id, 'assign')

    def remove_multi_slot_view(self, request, event_id):
        return self._multi_slot_view(request, event_id, 'remove')

@admin.register(EventSignupSlotConfig)
class EventSignupSlotConfigAdmin(admin.ModelAdmin):
    change_form_template = 'admin/eventer/eventsignupslotconfig/change_form.html'

    def response_add(self, request, obj, post_url_continue=None):
        return HttpResponseRedirect(f'../../event/{obj.event_id}/setup-superstream/')

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        if object_id:
            try:
                config = EventSignupSlotConfig.objects.get(pk=object_id)
                groups = EventSlotGroup.objects.prefetch_related('memberships__role').all()
                group_summaries = []
                for group in groups:
                    memberships = list(group.memberships.all())
                    effective_block = group.block_hours if group.block_hours is not None else config.management_block_hours
                    group_summaries.append({
                        'group': group,
                        'effective_block_hours': effective_block if not group.use_prime_time else None,
                        'memberships': memberships,
                    })
                extra_context['group_summaries'] = group_summaries
            except EventSignupSlotConfig.DoesNotExist:
                pass
        return super().changeform_view(request, object_id, form_url, extra_context)


class EventSlotGroupMembershipInline(admin.TabularInline):
    model = EventSlotGroupMembership
    extra = 1
    fields = ['role', 'first_block_hours']
    autocomplete_fields = ['role']


@admin.register(EventSlotGroup)
class EventSlotGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'use_prime_time', 'block_hours', 'member_count']
    inlines = [EventSlotGroupMembershipInline]

    def get_queryset(self, request):
        from django.db.models import Count
        return super().get_queryset(request).annotate(_member_count=Count('memberships'))

    @admin.display(description='Members')
    def member_count(self, obj):
        return obj._member_count


@admin.register(EventSignupSlot)
class EventSignupSlotAdmin(admin.ModelAdmin):
    list_display = ['event', 'role_list', 'label', 'duration_hours', 'start_local', 'stop_local', 'start_utc', 'stop_utc']
    list_filter = ['event', 'roles']
    filter_horizontal = ['roles']

    @admin.display(description='Roles')
    def role_list(self, obj):
        return ', '.join(obj.roles.values_list('name', flat=True))

    @admin.display(description='Duration')
    def duration_hours(self, obj):
        return f'{int((obj.stop - obj.start).total_seconds() / HOUR_SECONDS)}h'

    @admin.display(description='Start (Local)', ordering='start')
    def start_local(self, obj):
        tz = zoneinfo.ZoneInfo(obj.event.timezone)
        return obj.start.astimezone(tz).strftime(LOCAL_TIME_FMT)

    @admin.display(description='Stop (Local)', ordering='stop')
    def stop_local(self, obj):
        tz = zoneinfo.ZoneInfo(obj.event.timezone)
        return obj.stop.astimezone(tz).strftime(LOCAL_TIME_FMT)

    @admin.display(description='Start (UTC)', ordering='start')
    def start_utc(self, obj):
        return obj.start

    @admin.display(description='Stop (UTC)', ordering='stop')
    def stop_utc(self, obj):
        return obj.stop


class _ScheduleAssignmentAdminBase(admin.ModelAdmin):
    list_display = ['event', 'role', 'slot_label', 'slot_start_local', 'user']
    list_filter = ['event', 'role']
    raw_id_fields = ['user']

    @admin.display(description='Slot', ordering='slot__start')
    def slot_label(self, obj):
        return obj.slot.label

    @admin.display(description='Start (Local)', ordering='slot__start')
    def slot_start_local(self, obj):
        tz = zoneinfo.ZoneInfo(obj.event.timezone)
        return obj.slot.start.astimezone(tz).strftime(LOCAL_TIME_FMT)


@admin.register(EventScheduleAssignment)
class EventScheduleAssignmentAdmin(_ScheduleAssignmentAdminBase):
    pass


@admin.register(EventScheduleMultiAssignment)
class EventScheduleMultiAssignmentAdmin(_ScheduleAssignmentAdminBase):
    pass


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['game_name', 'status_display', 'suggested', 'effective_players', 'igdb_link']
    actions = ['approve_games', 'mark_suggested']
    readonly_fields = [
        'igdb_id', 'igdb_slug', 'igdb_url', 'igdb_cover_hash',
        'summary', 'first_release_date', 'igdb_category', 'multiplayer_max',
    ]
    fields = [
        'name', 'status', 'suggested', 'coordinator_notes',
        'multiplayer_max_override',
        'igdb_id', 'igdb_slug', 'igdb_url', 'igdb_cover_hash',
        'summary', 'first_release_date', 'igdb_category', 'multiplayer_max',
    ]

    @admin.action(description='Approve selected games')
    def approve_games(self, request, queryset):
        updated = queryset.exclude(status='approved').update(status='approved')
        self.message_user(request, f'{updated} game{"s" if updated != 1 else ""} approved.', messages.SUCCESS)

    @admin.action(description='Mark selected games as suggested')
    def mark_suggested(self, request, queryset):
        updated = queryset.filter(suggested=False).update(suggested=True)
        self.message_user(request, f'{updated} game{"s" if updated != 1 else ""} marked as suggested.', messages.SUCCESS)

    @admin.display(description='Game', ordering='name')
    def game_name(self, obj):
        return str(obj)

    @admin.display(description='Status', ordering='status')
    def status_display(self, obj):
        from django.utils.html import format_html
        icons = {
            'approved': ('✅', 'var(--body-fg, #333)'),
            'pending':  ('⏳', 'var(--secondary, #888)'),
            'rejected': ('🚫', 'var(--error-fg, #ba2121)'),
        }
        icon, color = icons.get(obj.status, ('', 'inherit'))
        return format_html('<span style="color:{}">{} {}</span>', color, icon, obj.get_status_display())

    @admin.display(description='Max players', ordering='multiplayer_max')
    def effective_players(self, obj):
        val = obj.effective_multiplayer_max
        if val is None:
            return '—'
        if obj.multiplayer_max_override is not None:
            from django.utils.html import format_html
            return format_html('{} <span style="font-size:0.8em;color:var(--secondary,#888)">(override)</span>', val)
        return val

    @admin.display(description='IGDB')
    def igdb_link(self, obj):
        from django.utils.html import format_html
        if obj.igdb_url:
            return format_html('<a href="{}" target="_blank" rel="noopener">IGDB ↗</a>', obj.igdb_url)
        return '-'
    list_filter = ['status', 'suggested']
    search_fields = ['name', 'igdb_slug']
    change_list_template = 'admin/eventer/game/change_list.html'

    def get_urls(self):
        custom = [
            path('search-igdb/',
                 self.admin_site.admin_view(self.search_igdb_view),
                 name='eventer_game_search_igdb'),
            path('sync-and-link/',
                 self.admin_site.admin_view(self.sync_and_link_view),
                 name='eventer_game_sync_and_link'),
        ]
        return custom + super().get_urls()

    def search_igdb_view(self, request):
        if not request.user.has_perm('eventer.search_igdb'):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        from eventer.igdb import IGDBClient, IGDBError, sync_game_from_igdb
        from eventer.models import Game

        # POST: sync selected games
        if request.method == 'POST':
            igdb_ids = request.POST.getlist('igdb_id')
            created_names, updated_names, errors = [], [], []
            for igdb_id in igdb_ids:
                try:
                    game, created = sync_game_from_igdb(int(igdb_id))
                    (created_names if created else updated_names).append(game.name)
                except Exception as e:
                    errors.append(str(e))
            if created_names:
                self.message_user(request, f'Added: {", ".join(created_names)}', messages.SUCCESS)
            if updated_names:
                self.message_user(request, f'Updated: {", ".join(updated_names)}', messages.SUCCESS)
            for error in errors:
                self.message_user(request, f'Error: {error}', messages.ERROR)
            return HttpResponseRedirect('.' + (f'?q={request.POST.get("q", "")}' if request.POST.get('q') else ''))

        # GET: search
        query = request.GET.get('q', '').strip()
        results = []
        error = None

        if not IGDBClient.credentials_configured():
            error = 'IGDB credentials are not configured. Set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET.'
        elif query:
            try:
                client = IGDBClient()
                raw_results = client.search_games(query)
                existing_ids = set(
                    Game.objects.filter(
                        igdb_id__in=[r['id'] for r in raw_results]
                    ).values_list('igdb_id', flat=True)
                )
                for r in raw_results:
                    cover_hash = (r.get('cover') or {}).get('image_id')
                    release_year = None
                    if r.get('first_release_date'):
                        from datetime import datetime, timezone
                        release_year = datetime.fromtimestamp(
                            r['first_release_date'], tz=timezone.utc
                        ).year
                    results.append({
                        'igdb_id': r['id'],
                        'name': r['name'],
                        'cover_url_thumb': f'//images.igdb.com/igdb/image/upload/t_thumb/{cover_hash}.jpg' if cover_hash else None,
                        'release_year': release_year,
                        'category': r.get('category'),
                        'already_exists': r['id'] in existing_ids,
                    })
            except IGDBError as e:
                log.warning('IGDB search failed: %s', e)
                error = 'IGDB search failed. Check credentials and try again.'

        if request.GET.get('format') == 'json':
            from django.http import JsonResponse
            return JsonResponse({'results': results, 'error': error})

        context = {
            **self.admin_site.each_context(request),
            'title': 'Search IGDB',
            'query': query,
            'results': results,
            'error': error,
        }
        return render(request, 'admin/eventer/game/search_igdb.html', context)

    def sync_and_link_view(self, request):
        """
        POST-only endpoint: sync a game from IGDB and link it to an EventInterest.
        Used by the IGDB search panel on the EventInterest change form.
        Returns JSON.
        """
        from django.http import JsonResponse
        from django.core.exceptions import PermissionDenied
        if not request.user.has_perm('eventer.search_igdb'):
            raise PermissionDenied
        if request.method != 'POST':
            return JsonResponse({'error': 'POST required'}, status=405)

        from eventer.igdb import IGDBError, sync_game_from_igdb
        from evtsignup.models import EventInterest, GameInterestUserEvent
        from eventer.models import EventRole

        igdb_id = request.POST.get('igdb_id', '').strip()
        event_interest_id = request.POST.get('event_interest_id', '').strip()
        role_id = request.POST.get('role_id', '').strip()

        try:
            event_interest = EventInterest.objects.get(pk=int(event_interest_id))
            role = EventRole.objects.get(pk=int(role_id))
            game, created = sync_game_from_igdb(int(igdb_id))
            if game.status != 'approved':
                game.status = 'approved'
                game.save(update_fields=['status'])
            _, linked = GameInterestUserEvent.objects.get_or_create(
                event_interest=event_interest,
                game=game,
                role=role,
            )
            return JsonResponse({
                'status': 'ok',
                'game_id': game.pk,
                'game_name': str(game),
                'game_created': created,
                'linked': linked,
                'role_name': role.name,
            })
        except EventInterest.DoesNotExist:
            return JsonResponse({'error': 'EventInterest not found'}, status=404)
        except EventRole.DoesNotExist:
            return JsonResponse({'error': 'Role not found'}, status=404)
        except ValueError:
            return JsonResponse({'error': f'IGDB game {igdb_id} not found.'}, status=404)
        except IGDBError as e:
            log.warning('IGDB sync-and-link failed for igdb_id=%s: %s', igdb_id, e)
            return JsonResponse({'error': 'IGDB API error - check credentials and try again.'}, status=400)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    pass


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    pass


@admin.register(TeamRole)
class TeamRoleAdmin(admin.ModelAdmin):
    pass
