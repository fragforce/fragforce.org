from django.db import models


class Event(models.Model):
    """ A gaming event """
    name = models.CharField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)


class EventPeriod(models.Model):
    """ A start/stop time period for an event """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=False, null=False)
    start = models.DateTimeField(null=False, blank=False)
    stop = models.DateTimeField(null=False, blank=False)
