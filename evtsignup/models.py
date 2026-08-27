from django.contrib.auth.models import User
from django.db import models


class EventInterest(models.Model):
    """ A user's signup for an event """
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    event = models.ForeignKey("eventer.Event", on_delete=models.CASCADE, blank=False, null=False)

    # Display info from signup form
    display_name = models.CharField(max_length=255, blank=True)
    preferences = models.TextField(blank=True)  # pronouns, other info
    acknowledged = models.BooleanField(default=False)

    # Fundraising - for streamers
    fundraising_url = models.URLField(null=True, blank=True)
    el_participant = models.ForeignKey(
        'ffdonations.ParticipantModel', null=True, blank=True, on_delete=models.SET_NULL
    )

    # URL resolution tracking
    url_resolution_attempts = models.PositiveSmallIntegerField(
        default=0,
        help_text='Number of times fundraising URL resolution has been attempted'
    )

    def __str__(self):
        name = self.display_name or str(self.user)
        return f'{name} - {self.event}'

    class Meta:
        unique_together = [["user", "event"]]


class GameInterestUserEvent(models.Model):
    """ User's pre-selected game checkbox for a particular event and role track """
    event_interest = models.ForeignKey("EventInterest", on_delete=models.CASCADE, blank=False, null=False)
    game = models.ForeignKey('eventer.Game', on_delete=models.CASCADE, blank=False, null=False)
    role = models.ForeignKey('eventer.EventRole', on_delete=models.CASCADE, blank=False, null=False)

    def __str__(self):
        return f'{self.event_interest} - {self.game} ({self.role})'

    class Meta:
        unique_together = [["event_interest", "game", "role"]]


class EventInterestNote(models.Model):
    """ Free-text game preference notes per role per signup. One row per (event_interest, role). """
    event_interest = models.ForeignKey("EventInterest", on_delete=models.CASCADE, blank=False, null=False)
    role = models.ForeignKey('eventer.EventRole', on_delete=models.CASCADE, blank=False, null=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'{self.event_interest} [{self.role.slug}]'

    class Meta:
        unique_together = [["event_interest", "role"]]


class EventAvailabilityHour(models.Model):
    """ One record per available hour per role per user per event.
    Form checkboxes (e.g. 'Friday 8pm-11pm') expand to one row per hour per role on save. """
    event_interest = models.ForeignKey("EventInterest", on_delete=models.CASCADE, blank=False, null=False)
    hour = models.DateTimeField(null=False, blank=False)  # UTC, start of the hour
    role = models.ForeignKey("eventer.EventRole", on_delete=models.CASCADE, blank=False, null=False)

    def __str__(self):
        return f'{self.event_interest} @ {self.hour:%Y-%m-%d %H:%M} UTC [{self.role.slug}]'

    class Meta:
        unique_together = [["event_interest", "hour", "role"]]
