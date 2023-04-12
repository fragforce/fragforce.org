from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.cache import cache_page

from ..tasks import *
from ..utils import event_name_maker


@cache_page(settings.VIEW_DONATIONS_CACHE)
def v_donations(request):
    orderByVar = request.GET.get('orderBy', 'id')
    filterByVar = request.GET.get('filterBy', 'none')
    recordCountVar = request.GET.get('recordCount', '0')
    recordCountInt = int(recordCountVar)
    update_donations_if_needed.delay()
    listedDonos = DonationModel.objects.order_by(orderByVar).filter(participant__event__id__in=current_el_events())
    if filterByVar != 'none':
        listedDonos = listedDonos.filter(participant_id=filterByVar, amount__isnull=False)
    else:
        listedDonos = listedDonos.filter(amount__isnull=False)
    if recordCountInt > 0 and recordCountInt <= settings.MAX_API_ROWS:
        listedDonos = listedDonos[:recordCountInt]
    else:
        listedDonos = listedDonos[:settings.MAX_API_ROWS]
    return JsonResponse(
        [d for d in listedDonos.values()],
        safe=False,
    )


@cache_page(settings.VIEW_DONATIONS_CACHE)
def v_tracked_donations(request):
    orderByVar = request.GET.get('orderBy', 'id')
    update_donations_if_needed.delay()
    return JsonResponse(
        [d for d in
         DonationModel.objects.filter(DonationModel.tracked_q()).order_by(orderByVar)[:settings.MAX_API_ROWS].values()],
        safe=False,
    )
