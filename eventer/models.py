from datetime import time

from django.contrib.auth.models import User
from django.db import models

HOUR_SECONDS = 3600

SUPERSTREAM_TIMEZONES = [
    ('US/Canada', [
        ('America/New_York', 'Eastern (ET)'),
        ('America/Chicago', 'Central (CT)'),
        ('America/Denver', 'Mountain (MT)'),
        ('America/Los_Angeles', 'Pacific (PT)'),
        ('America/Anchorage', 'Alaska (AKT)'),
        ('Pacific/Honolulu', 'Hawaii (HT)'),
    ]),
    ('Australia/NZ', [
        ('Australia/Sydney', 'Sydney/Melbourne (AEST)'),
        ('Australia/Brisbane', 'Brisbane (AEST no DST)'),
        ('Australia/Perth', 'Perth (AWST)'),
        ('Pacific/Auckland', 'Auckland (NZST)'),
    ]),
    ('Europe/UK', [
        ('Europe/London', 'London (GMT/BST)'),
        ('Europe/Paris', 'Central Europe (CET/CEST)'),
        ('Europe/Helsinki', 'Eastern Europe (EET/EEST)'),
    ]),
    ('Other', [
        ('UTC', 'UTC'),
        ('Asia/Singapore', 'Singapore (SGT)'),
        ('Asia/Tokyo', 'Japan (JST)'),
    ]),
]


class Team(models.Model):
    """ A team or group of people who do events """
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    role = models.ForeignKey('TeamRole', on_delete=models.CASCADE, blank=False, null=False)
    description = models.TextField(default='', blank=False, null=False)

    def __str__(self):
        return self.name


class TeamRole(models.Model):
    """ A role a user can have in a team """
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)

    def __str__(self):
        return self.name


class TeamMember(models.Model):
    """ Connect a User to a Role in a Team """
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, blank=False, null=False)
    role = models.ForeignKey(TeamRole, on_delete=models.CASCADE, blank=False, null=False)

    def __str__(self):
        return f'{self.user} - {self.team} ({self.role})'

    class Meta:
        unique_together = [
            ["user", "team"],  # Basic overlap check
        ]


class EventRole(models.Model):
    """ A role a user can have on an event """
    name = models.CharField(max_length=255, unique=True, db_index=True, null=False, blank=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)
    color = models.CharField(max_length=7, default='#417690', blank=False, null=False,
                             help_text="Hex color code for UI display (e.g. #417690)")
    multi_assign = models.BooleanField(default=False,
                                       help_text="Allow multiple users assigned per slot (e.g. Participant). Single-assign roles enforce one user per slot.")
    display_order = models.PositiveSmallIntegerField(default=100,
                                                     help_text="Display order — lower numbers appear first. Roles with the same value are sorted alphabetically.")
    has_game_selection = models.BooleanField(default=False,
                                             help_text="Show a game preference picker for this role on the signup form.")
    game_min_players = models.PositiveSmallIntegerField(null=True, blank=True,
                                                        help_text="Exclude games where max players is less than this value. Leave blank to show all games.")
    show_fundraising_url = models.BooleanField(default=False,
                                               help_text="Show the fundraising URL field for this role on the signup form.")
    show_stream_commands = models.BooleanField(default=False,
                                               help_text="Show Twitch stream commands (title, game, donate) in the coordinator schedule for this role. Also pins this role's column first.")
    show_notes = models.BooleanField(default=False,
                                     help_text="Show an 'Other game preferences' notes textarea for this role on the signup form.")

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class Game(models.Model):
    """ An IGDB backed game """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected - not allowed on stream (e.g. banned on Twitch)'

    name = models.CharField(max_length=255, db_index=True, null=False, blank=False, verbose_name="Game name")
    coordinator_notes = models.TextField(blank=True, verbose_name="Coordinator notes", help_text="Internal notes for coordinators, e.g. hardware requirements or known issues")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True, verbose_name="Status", help_text="Moderation status - rejected games cannot be selected on signup forms")
    suggested = models.BooleanField(default=False, db_index=True, verbose_name="Suggested game", help_text="Show this game on the signup form game selection list (only applies when status=approved)")
    igdb_id = models.PositiveIntegerField(unique=True, null=False, blank=False, verbose_name="IGDB ID", help_text="Numeric IGDB game ID, e.g. 115555")
    igdb_slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, db_index=True, verbose_name="IGDB slug", help_text="IGDB URL slug, e.g. 'going-medieval'")
    igdb_url = models.URLField(null=True, blank=True, verbose_name="IGDB URL", help_text="Full IGDB game page URL")
    igdb_cover_hash = models.CharField(max_length=255, null=True, blank=True, verbose_name="IGDB cover hash", help_text="IGDB image hash - use //images.igdb.com/igdb/image/upload/t_{size}/{hash}.jpg")
    summary = models.TextField(blank=True, verbose_name="IGDB summary", help_text="Short game description from IGDB")
    multiplayer_max = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Max players (IGDB)", help_text="Maximum co-op party size from IGDB; null=unknown or single player")
    multiplayer_max_override = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Max players (override)", help_text="Manual override for max players; takes precedence over IGDB value when set")
    first_release_date = models.DateField(null=True, blank=True, verbose_name="First release date", help_text="Initial release date from IGDB")
    igdb_category = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="IGDB category", help_text="IGDB game category: 0=main game, 1=DLC, 2=expansion, 3=bundle, 4=standalone expansion")

    @property
    def cover_url(self):
        if not self.igdb_cover_hash:
            return None
        return f'//images.igdb.com/igdb/image/upload/t_cover_big/{self.igdb_cover_hash}.jpg'

    @property
    def cover_url_thumb(self):
        if not self.igdb_cover_hash:
            return None
        return f'//images.igdb.com/igdb/image/upload/t_thumb/{self.igdb_cover_hash}.jpg'

    @property
    def effective_multiplayer_max(self):
        """Returns the override if set, otherwise the IGDB value."""
        if self.multiplayer_max_override is not None:
            return self.multiplayer_max_override
        return self.multiplayer_max

    def __str__(self):
        if self.first_release_date:
            return f'{self.name} ({self.first_release_date.year})'
        return self.name

    class Meta:
        permissions = [
            ('search_igdb', 'Can search IGDB and sync games'),
        ]


class Event(models.Model):
    """ A gaming event """
    name = models.CharField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)
    timezone = models.CharField(max_length=64, default='America/New_York', blank=False, null=False,
                                choices=SUPERSTREAM_TIMEZONES,
                                help_text="Timezone for coordinator-facing display. Public schedule uses browser local time via the |localtime template filter.")
    public = models.BooleanField(default=False,
                               help_text="Show this event on the public events listing.")
    signups_open = models.BooleanField(default=False,
                                       help_text="Allow new signups. Has no effect when locked.")
    edits_open = models.BooleanField(default=False,
                                     help_text="Allow existing signups to be edited. Has no effect when locked.")
    locked = models.BooleanField(default=False,
                                 help_text="Lock the event - disables all signups and edits regardless of other flags.")
    schedule_published = models.BooleanField(default=False,
                                             help_text="Publish the finalized schedule - enables the public schedule view.")

    @property
    def start(self):
        """ Earliest period start - the event's effective start time """
        period = self.eventperiod_set.order_by('start').first()
        return period.start if period else None

    @property
    def end(self):
        """ Latest period stop - the event's effective end time """
        period = self.eventperiod_set.order_by('stop').last()
        return period.stop if period else None

    class Meta:
        permissions = [
            ('view_coordinator_schedule', 'Can view the coordinator schedule for events'),
        ]

    def __str__(self):
        return self.name

    @classmethod
    def add_details(cls, fq=None):
        from django.db.models import Sum, F

        if fq is None:
            fq = cls.objects

        return fq.annotate(duration=Sum(F("event_period__stop") - F("event_period__start")))


class EventPeriod(models.Model):
    """ A start/stop time period for an event """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=False, null=False)
    start = models.DateTimeField(null=False, blank=False)
    stop = models.DateTimeField(null=False, blank=False)

    def __str__(self):
        return f'{self.event} - {self.start} to {self.stop}'

    @staticmethod
    def duration_f():
        """ Field value for duration (stop-start) """
        from django.db.models import F
        return F('stop') - F('start')


class EventSignupSlotConfig(models.Model):
    """ Generator configuration for slot templates for an event """
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='slot_config')

    # Player/Streamer block sizes
    standard_block_hours = models.PositiveSmallIntegerField(
        default=3,
        help_text="Default slot block size in hours for participant/streamer grid",
    )
    prime_block_hours = models.PositiveSmallIntegerField(
        default=2,
        help_text="Slot block size during prime time hours",
    )
    prime_time_start = models.TimeField(
        default=time(14, 0),
        help_text="Start of prime time (in event timezone) - shorter blocks begin here",
    )
    prime_time_end = models.TimeField(
        default=time(21, 0),
        help_text="End of prime time (in event timezone) - shorter blocks end here",
    )

    # Management block sizes (used by groups with use_prime_time=False that don't set their own block_hours)
    management_block_hours = models.PositiveSmallIntegerField(
        default=6,
        help_text="Default block size in hours for management-style role groups. Individual groups can override this.",
    )

    def __str__(self):
        return f'Slot config for {self.event}'


class EventSlotGroup(models.Model):
    """ A named grouping of roles that share slot generation settings. Global and reusable across events. """
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    use_prime_time = models.BooleanField(
        default=False,
        help_text="If true, use variable prime-time block sizing. If false, use this group's block_hours (or the event's management_block_hours if not set).",
    )
    block_hours = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Block size in hours for this group. Null falls back to the event's management_block_hours. Ignored when use_prime_time is true.",
    )
    roles = models.ManyToManyField(
        'EventRole',
        through='EventSlotGroupMembership',
        related_name='slot_groups',
        blank=True,
    )

    def __str__(self):
        return self.name


class EventSlotGroupMembership(models.Model):
    """ Membership of a role in a slot group, with an optional first-block offset. """
    group = models.ForeignKey(EventSlotGroup, on_delete=models.CASCADE, related_name='memberships')
    role = models.ForeignKey('EventRole', on_delete=models.CASCADE, related_name='slot_group_memberships')
    first_block_hours = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Override the first slot's block size for this role to stagger changeovers. Null uses the group's standard block size.",
    )

    class Meta:
        unique_together = [['group', 'role']]

    def __str__(self):
        offset = f' (first={self.first_block_hours}h)' if self.first_block_hours is not None else ''
        return f'{self.role.name} in {self.group.name}{offset}'


class EventSignupSlot(models.Model):
    """ A single slot on the signup form, linked to one or more roles """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='signup_slots')
    roles = models.ManyToManyField(EventRole, blank=True, help_text="Roles this slot applies to")
    start = models.DateTimeField(help_text="Slot start time (UTC)")
    stop = models.DateTimeField(help_text="Slot end time (UTC)")
    label = models.CharField(max_length=255, help_text="Human-readable label shown on signup form")

    class Meta:
        ordering = ['start']
        unique_together = [['event', 'start', 'stop']]

    def __str__(self):
        return f'{self.event} - {self.label}'


class EventScheduleAssignment(models.Model):
    """ A confirmed schedule assignment - one user per role per signup slot (singular roles only) """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='schedule_assignments')
    slot = models.ForeignKey(EventSignupSlot, on_delete=models.CASCADE, related_name='schedule_slot_assignments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(EventRole, on_delete=models.CASCADE)
    game = models.ForeignKey('Game', on_delete=models.SET_NULL, null=True, blank=True,
                             help_text="Game being played this slot (streamer slots only)")

    class Meta:
        unique_together = [['slot', 'role']]
        ordering = ['slot__start', 'role__name']

    def __str__(self):
        return f'{self.event} - {self.slot.label} - {self.role} - {self.user}'


class EventScheduleMultiAssignment(models.Model):
    """ A confirmed multi-user assignment for roles that allow multiple assignees per slot (e.g. Participant) """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='schedule_multi_assignments')
    slot = models.ForeignKey(EventSignupSlot, on_delete=models.CASCADE, related_name='multi_assignments')
    role = models.ForeignKey(EventRole, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = [['slot', 'role', 'user']]
        ordering = ['slot__start', 'role__name']

    def __str__(self):
        return f'{self.event} - {self.slot.label} - {self.role} - {self.user}'
