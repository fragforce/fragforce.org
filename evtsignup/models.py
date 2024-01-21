from django.contrib.postgres.fields import HStoreField
from django.db import models
from django_workflow_engine.executor import User


class DiscordEventUser(models.Model):
    """ Created if a User maps to a discord ID """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    discord_id = models.CharField(max_length=255, blank=False, db_index=True, null=False, unique=True)


class SalesforceEventUser(models.Model):
    """ Created if a user maps to a SFID """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    salesforce_id = models.CharField(max_length=64, blank=False, db_index=True, null=False, unique=True)


class ExtraLifeEventUser(models.Model):
    """ Created if a user maps to an extra life user """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    el_participant_id = models.PositiveBigIntegerField(blank=False, db_index=True, null=False, unique=True)
    # el_participant_url = models.URLField(max_length=8192, blank=False, null=False) # calc'ed


class StreamSuggestion(models.Model):
    """ A user would like to stream a game """
    event_interest = models.ForeignKey("EventInterest", on_delete=models.CASCADE, blank=False, null=False)
    game = models.ForeignKey("eventer.Game", on_delete=models.CASCADE, blank=False, null=False)
    suggested_players = models.ManyToManyField(User, blank=True)
    min_players = models.PositiveSmallIntegerField(default=1, blank=False, null=False)
    max_players = models.PositiveSmallIntegerField(default=1, blank=False, null=False)
    ideal_players = models.PositiveSmallIntegerField(default=1, blank=False, null=False)
    flags = HStoreField(default=dict, blank=False, null=False)


class EventInterest(models.Model):
    """ A user has expressed interest in an event """
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    event = models.ForeignKey("eventer.Event", on_delete=models.CASCADE, blank=False, null=False)
    interest_level = models.ForeignKey("evtsignup.InterestLevel", on_delete=models.CASCADE, blank=False, null=False)

    class Meta:
        unique_together = [
            ["user", "event"],
        ]


class InterestLevel(models.Model):
    """ Different levels/types of interest """
    name = models.CharField(max_length=255, unique=True, db_index=True, null=False, blank=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)
    rank = models.SmallIntegerField(default=0, blank=False, null=False)  # Above zero = good, below zero = never


class EventRoleInterest(models.Model):
    """ A User's interest level in a given role for a given event they're interested in """
    event_interest = models.ForeignKey("EventInterest", on_delete=models.CASCADE, blank=False, null=False)
    event_role = models.ForeignKey("eventer.EventRole", on_delete=models.CASCADE, blank=False, null=False)
    interest_level = models.ForeignKey("InterestLevel", on_delete=models.CASCADE, blank=False, null=False)

    class Meta:
        unique_together = [
            ["event_interest", "event_role"],
        ]


class GameInterestUser(models.Model):
    """ User's interest in a game overall """
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    game = models.ForeignKey('eventer.Game', on_delete=models.CASCADE, blank=False, null=False)
    interest_level = models.ForeignKey('InterestLevel', on_delete=models.CASCADE, blank=False, null=False)

    class Meta:
        unique_together = [
            ["user", "game"],
        ]


class GameInterestUserEvent(models.Model):
    """ User's interest in a game for a particular event """
    event_interest = models.ForeignKey("EventInterest", on_delete=models.CASCADE, blank=False, null=False)
    game = models.ForeignKey('eventer.Game', on_delete=models.CASCADE, blank=False, null=False)
    interest_level = models.ForeignKey('InterestLevel', on_delete=models.CASCADE, blank=False, null=False)

    class Meta:
        unique_together = [
            ["event_interest", "game"],
        ]


class EventAvailabilityInterest(models.Model):
    """ Used by users to show their availability for a given time period for an event they've expressed interest in """
    event_interest = models.ForeignKey("EventInterest", on_delete=models.CASCADE, blank=False, null=False)
    interest_level = models.ForeignKey("InterestLevel", on_delete=models.CASCADE, blank=False, null=False)
    period_start = models.DateTimeField(null=False, blank=False)
    period_end = models.DateTimeField(null=False, blank=False)

    class Meta:
        unique_together = [
            ["event_interest", "period_start", "period_end"],  # Basic overlap check
        ]
