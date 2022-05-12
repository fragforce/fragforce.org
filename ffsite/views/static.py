from django.conf import settings
from django.shortcuts import render
from django.views.decorators.cache import cache_page


@cache_page(settings.VIEW_SITE_STATIC_CACHE)
def home(request):
    """ Home page """
    return render(request, 'ff/root/home.html', {})


# @cache_page(settings.VIEW_SITE_STATIC_CACHE)
def donate(request):
    """ How to donate page """
    from ..utils import random_contact
    return render(request, 'ff/root/donate.html', {
        'rnd_pct': random_contact(),
    })


@cache_page(settings.VIEW_SITE_STATIC_CACHE)
def join(request):
    """ How to join ff page """
    return render(request, 'ff/root/join.html', {})


@cache_page(settings.VIEW_SITE_STATIC_CACHE)
def contact(request):
    """ Contact page """
    return render(request, 'ff/root/contact.html', {})


@cache_page(settings.VIEW_SITE_STATIC_CACHE)
def stream(request):
    """ Stream page """
    return render(request, 'ff/root/stream.html', {
        "stream_url": settings.STREAM_URL,
    })
