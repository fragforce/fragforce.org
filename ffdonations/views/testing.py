from functools import wraps

from django.http import JsonResponse
from django.shortcuts import Http404

from ..tasks import *


def _onlydebug(f):
    """ Decorator: Only run the view if we're in debug mode """

    @wraps(f)
    def wrapped(*args, **kwargs):
        if not settings.DEBUG:
            raise Http404("DEBUG=False")

        return f(*args, **kwargs)

    return wrapped


@_onlydebug
def v_testView(request):
    ret = [
        ('pct',),
        ('team',),
    ]

    return JsonResponse([repr(r) for r in ret], safe=False)


@_onlydebug
def v_forceUpdate(request):
    ret = [
        update_donations_existing.delay(),
        update_participants.delay(),
        update_teams.delay(),
    ]

    for team in TeamModel.objects.filter(tracked=True).all():
        ret.append(update_donations_team.delay(team.id))

    for p in ParticipantModel.objects.filter(tracked=True).all():
        ret.append(update_donations_participant.delay(p.id))

    return JsonResponse([repr(r) for r in ret], safe=False)
