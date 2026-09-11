from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_safe

from ..models import TeamModel
from ..tasks.teams import update_teams_if_needed


@require_safe
@cache_page(settings.VIEW_TEAMS_CACHE)
def v_teams(request):
    update_teams_if_needed.delay()
    return JsonResponse(
        [d for d in TeamModel.objects.all().order_by('id')[:settings.MAX_API_ROWS].values()],
        safe=False,
    )


@require_safe
@cache_page(settings.VIEW_TEAMS_CACHE)
def v_tracked_teams(request):
    update_teams_if_needed.delay()
    return JsonResponse(
        [d for d in TeamModel.objects.filter(tracked=True).order_by('id')[:settings.MAX_API_ROWS].values()],
        safe=False,
    )
