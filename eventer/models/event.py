from django.db import models


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
