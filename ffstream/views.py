from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import *


@csrf_exempt
@require_POST
def start_srt(request):
    skey = request.POST['name']
    key = get_object_or_404(Key, id=skey)
    if not key.active:
        return HttpResponseForbidden("inactive key")
    # if key.is_live:
    # What to do if already live?

    key.is_live = True
    key.save()

    stream = Stream(key=key, is_live=True, started=timezone.now(), ended=None)
    stream.save()
    stream.set_stream_key()  # No save needed

    # Change key to GUID
    return HttpResponse("OK")

@csrf_exempt
@require_POST
def start_livestream(request):
    skey = request.POST['name']
    key = get_object_or_404(Key, id=skey)
    if not key.active:
        return HttpResponseForbidden("inactive key")
    if not key.livestream:
        return HttpResponseForbidden("Key not allowed to livestream")
    key.is_live = True
    key.save

    stream = Stream(key=key, is_live=True, strated=timezone.now(), ended=None)
    stream.save
    stream.set_stream_key()

    return HttpResponse("OK")


@csrf_exempt
@require_POST
def start(request):
    skey = request.POST['name']
    key = get_object_or_404(Key, id=skey)
    if not key.active:
        return HttpResponseForbidden("inactive key")
    # if key.is_live:
    # What to do if already live?

    key.is_live = True
    key.save()

    stream = Stream(key=key, is_live=True, started=timezone.now(), ended=None)
    stream.save()
    stream.set_stream_key()  # No save needed

    # Change key to GUID
    return HttpResponseRedirect(stream.stream_key())


@csrf_exempt
@require_POST
def stop(request):
    skey = request.POST['name']
    key = get_object_or_404(Key, id=skey)
    key.is_live = False
    key.save()
    # End them all, just in case
    for stream in key.stream_set.filter(is_live=True, ended=None).all():
        stream.ended = timezone.now()
        stream.is_live = False
        stream.save()

    return HttpResponse("OK")


@csrf_exempt
@require_POST
def play(request):
    # Handle loopback for ffmpeg
    if "__" in request.POST['name']:
        kname, sname = request.POST['name'].split("__")
        key = get_object_or_404(Key, name=kname)
        stream = key.stream_set.filter(guid=sname).get()
        return HttpResponseRedirect(stream.stream_key())

    if not request.POST.get('key', None):
        # print("no key")
        return HttpResponseForbidden("no key given")

    pullKey = get_object_or_404(Key, id=request.POST['key'])
    streamKey = get_object_or_404(Key, name=request.POST['name'])

    # Allow users to pull their own stream if they want
    if pullKey.pk == streamKey.pk and streamKey.active:
        for stream in streamKey.stream_set.filter(is_live=True, ended=None).order_by("-started"):
            return HttpResponseRedirect(stream.stream_key())

    if not pullKey.pull:
        # print("not a pull key")
        return HttpResponseForbidden("not a pull key")

    for stream in streamKey.stream_set.filter(is_live=True, ended=None).order_by("-started")[:1]:
        # print("Found " + stream.stream_key())
        return HttpResponseRedirect(stream.stream_key())

    # print("inactive stream")
    return HttpResponseForbidden("inactive stream")


def view(request, key=None):
    pullKey = get_object_or_404(Key, id=key)
    if not pullKey.pull:
        return HttpResponseForbidden("bad key")

    return render(request, 'ffstream/view.html', dict(
        pullKey=pullKey,
        streams=Stream.objects.filter(is_live=True).order_by("-created").all(),
        liveKeys=Key.objects.filter(is_live=True, active=True).order_by("-created").all(),
    ))


def goto(request, key, name):
    pullKey = get_object_or_404(Key, id=key)
    if not pullKey.pull:
        return HttpResponseForbidden("bad key")

    streamKey = get_object_or_404(Key, name=name)
    for stream in streamKey.stream_set.filter(is_live=True, ended=None).order_by("-started"):
        return HttpResponseRedirect(stream.url())

    return Http404("No active stream")
