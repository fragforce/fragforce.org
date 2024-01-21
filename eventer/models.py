from django.contrib.postgres.fields import HStoreField
from django.db import models
from django_workflow_engine.executor import User


class Team(models.Model):
    """ A team or group of people who do events """
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    team_info = HStoreField(default=dict, null=False)
    role = models.ForeignKey('TeamRole', on_delete=models.CASCADE, blank=False, null=False)
    description = models.TextField(default='', blank=False, null=False)


class TeamRole(models.Model):
    """ A role a user can have in a team """
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)


class TeamMember(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, blank=False, null=False)
    role = models.ForeignKey(TeamRole, on_delete=models.CASCADE, blank=False, null=False)

    class Meta:
        unique_together = [
            ["user", "team"],  # Basic overlap check
        ]


class EventRole(models.Model):
    """ A role a user can have on an event """
    name = models.CharField(max_length=255, unique=True, db_index=True, null=False, blank=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)


class Game(models.Model):
    """ An IGDB backed game """

    name = models.CharField(max_length=255, unique=True, db_index=True, null=False, blank=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)
    igdb_id = models.SlugField(max_length=255, blank=False, null=False, unique=True)
    status = models.ForeignKey('GameStatus', on_delete=models.CASCADE, blank=False, null=False)
    flags = HStoreField(default=dict, blank=False, null=False)


class GameStatus(models.Model):
    """ Game's approval status """
    name = models.CharField(max_length=255, unique=True, db_index=True, null=False, blank=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)


class Event(models.Model):
    """ A gaming event """
    name = models.CharField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)

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

    @staticmethod
    def duration_f():
        """ Field value for duration (stop-start) """
        from django.db.models import F
        return F('stop') - F('start')
