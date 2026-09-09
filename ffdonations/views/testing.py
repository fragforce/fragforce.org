from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import Http404
from django.views.decorators.http import require_safe

from ..models import ParticipantModel, TeamModel
from ..tasks.donations import update_donations_existing, update_donations_participant, update_donations_team
from ..tasks.participants import update_participants
from ..tasks.teams import update_teams


def _onlydebug(f):
    """ Decorator: Only run the view if we're in debug mode """

    @wraps(f)
    def wrapped(*args, **kwargs):
        if not settings.DEBUG:
            raise Http404("DEBUG=False")

        return f(*args, **kwargs)

    return wrapped


@require_safe
@_onlydebug
def v_test_view(request):
    ret = [
        ('pct',),
        ('team',),
    ]

    return JsonResponse([repr(r) for r in ret], safe=False)


@require_safe
@_onlydebug
def v_force_update(request):
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
