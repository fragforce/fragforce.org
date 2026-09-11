from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_safe

from .models import Key, Stream
from .wordlist import generate_stream_key

NO_OWNER = "no owner assigned"


@csrf_exempt
@require_POST
def start_srt(request):
    skey = request.POST['name']
    key = get_object_or_404(Key, stream_key=skey)
    if not key.owner:
        return HttpResponseForbidden(NO_OWNER)
    if not key.superstream:
        return HttpResponseForbidden("key not enabled for Super Stream events")
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
    key = get_object_or_404(Key, stream_key=skey)
    if not key.owner:
        return HttpResponseForbidden(NO_OWNER)
    if not key.livestream:
        return HttpResponseForbidden("Key not allowed to livestream")
    key.is_live = True
    key.save()

    stream = Stream(key=key, is_live=True, started=timezone.now(), ended=None)
    stream.save()
    stream.set_stream_key()

    return HttpResponse("OK")


@csrf_exempt
@require_POST
def start(request):
    skey = request.POST['name']
    key = get_object_or_404(Key, stream_key=skey)
    if not key.owner:
        return HttpResponseForbidden(NO_OWNER)
    if not key.superstream:
        return HttpResponseForbidden("key not enabled for Super Stream events")
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
    key = get_object_or_404(Key, stream_key=skey)
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

    pull_key = get_object_or_404(Key, stream_key=request.POST['key'])
    strean_key = get_object_or_404(Key, name=request.POST['name'])

    # Allow users to pull their own stream if they want
    if pull_key.pk == strean_key.pk and strean_key.superstream:
        for stream in strean_key.stream_set.filter(is_live=True, ended=None).order_by("-started"):
            return HttpResponseRedirect(stream.stream_key())

    if not pull_key.pull:
        # print("not a pull key")
        return HttpResponseForbidden("not a pull key")

    for stream in strean_key.stream_set.filter(is_live=True, ended=None).order_by("-started")[:1]:
        # print("Found " + stream.stream_key())
        return HttpResponseRedirect(stream.stream_key())

    # print("inactive stream")
    return HttpResponseForbidden("inactive stream")


@require_safe
def view(request, key=None):
    pull_key = get_object_or_404(Key, stream_key=key)
    if not pull_key.pull:
        return HttpResponseForbidden("bad key")

    return render(request, 'ffstream/view.html', dict(
        pull_key=pull_key,
        streams=Stream.objects.filter(is_live=True).order_by("-created").all(),
        liveKeys=Key.objects.filter(is_live=True, superstream=True).order_by("-created").all(),
    ))


@require_safe
@login_required
def my_keys(request):
    key = Key.objects.filter(owner=request.user).first()
    return render(request, 'ffstream/my_keys.html', {'key': key})


@require_POST
@login_required
def generate_key(request):
    if not Key.objects.filter(owner=request.user).exists():
        safe_name = slugify(request.user.username.replace('.', '-'))
        # Claim an existing unowned key with the user's name if one exists
        claimed = Key.objects.filter(name__in=[request.user.username, safe_name], owner=None).first()
        if claimed:
            claimed.owner = request.user
            claimed.name = safe_name
            claimed.save()
        else:
            name = safe_name
            # Avoid name collision with a key owned by someone else
            while Key.objects.filter(name=name).exists():
                name = f"{safe_name}-{generate_stream_key()[:8]}"
            Key.objects.create(
                name=name,
                owner=request.user,
                superstream=False,
                livestream=False,
            )
    return redirect('my-keys')


@require_POST
@login_required
def regenerate_key(request):
    candidate = generate_stream_key()
    while Key.objects.filter(stream_key=candidate).exists():
        candidate = generate_stream_key()
    Key.objects.filter(owner=request.user).update(stream_key=candidate)
    return redirect('my-keys')


@require_safe
def goto(request, key, name):
    pull_key = get_object_or_404(Key, stream_key=key)
    if not pull_key.pull:
        return HttpResponseForbidden("bad key")

    strean_key = get_object_or_404(Key, name=name)
    for stream in strean_key.stream_set.filter(is_live=True, ended=None).order_by("-started"):
        return HttpResponseRedirect(stream.url())

    return Http404("No active stream")
