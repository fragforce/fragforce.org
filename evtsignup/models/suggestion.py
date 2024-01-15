from django.contrib.postgres.fields import HStoreField
from django.db import models
from django_workflow_engine.executor import User


class StreamSuggestion(models.Model):
    """ A user would like to stream a game """
    event_interest = models.ForeignKey("EventInterest", on_delete=models.CASCADE, blank=False, null=False)
    game = models.ForeignKey("eventer.Game", on_delete=models.CASCADE, blank=False, null=False)
    suggested_players = models.ManyToManyField(User, blank=True)
    min_players = models.PositiveSmallIntegerField(default=1, blank=False, null=False)
    max_players = models.PositiveSmallIntegerField(default=1, blank=False, null=False)
    ideal_players = models.PositiveSmallIntegerField(default=1, blank=False, null=False)
    flags = HStoreField(default=dict, blank=False, null=False)
