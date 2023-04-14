from django.conf import settings
from django.shortcuts import render
from django.views.decorators.cache import cache_page

from ffsfdc.models import *


@cache_page(settings.VIEW_SITE_EVENT_CACHE)
def events(request):
    """ Events page """
    return render(request, 'ff/events/index.html', {
        'events': Event.objects.order_by('-event_start_date').all(),
    })


@cache_page(settings.VIEW_SITE_EVENT_CACHE)
def events_upcoming(request):
    """ Events upcoming page """
    return render(request, 'ff/events/upcoming.html', {
        'events': Event.objects.filter(event_start_date__gte=timezone.now()).order_by(
            'event_start_date').all(),
    })


@cache_page(settings.VIEW_SITE_EVENT_CACHE)
def event(request, sfid):
    """ Event page """
    return render(request, 'ff/events/event.html', {
        'event': Event.objects.filter(sfid=sfid).first(),
    })
