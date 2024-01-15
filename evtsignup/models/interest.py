from django.db import models
from django_workflow_engine.executor import User


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
