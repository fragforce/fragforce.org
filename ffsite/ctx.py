from ffsfdc.models import *
import datetime
from django.conf import settings

def common_org(request):
    """ Context processors for all ffsite pages """
    return dict(
        all_events=Event.objects.order_by('event_start_date').all()[:settings.MAX_ALL_EVENTS],
        upcoming_events=Event.objects.filter(event_start_date__gte=datetime.datetime.now()).order_by(
            'event_start_date').all()[:settings.MAX_UPCOMING_EVENTS],
        past_events=Event.objects.filter(event_start_date__lt=datetime.datetime.now()).order_by(
            '-event_start_date').all()[:settings.MAX_PAST_EVENTS],
        allsites=SiteAccount.objects.order_by('name').all(),
        now=datetime.datetime.utcnow(),
        gaid=settings.GOOGLE_ANALYTICS_ID,
    )