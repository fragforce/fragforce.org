from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_safe

from ..models import ParticipantModel
from ..tasks.participants import update_participants_if_needed


@require_safe
@cache_page(settings.VIEW_PARTICIPANTS_CACHE)
def v_participants(request):
    update_participants_if_needed.delay()
    return JsonResponse(
        [d for d in ParticipantModel.objects.all().order_by('id')[:settings.MAX_API_ROWS].values()],
        safe=False,
    )


@require_safe
@cache_page(settings.VIEW_PARTICIPANTS_CACHE)
def v_tracked_participants(request):
    update_participants_if_needed.delay()
    return JsonResponse(
        [d for d in ParticipantModel.objects.filter(tracked=True)[:settings.MAX_API_ROWS].order_by('id').values()],
        safe=False,
    )
