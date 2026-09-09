from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_safe

from ..models import DonationModel
from ..tasks.donations import update_donations_if_needed
from ..utils import el_teams

VALID_ORDER_FIELDS = {'id', '-id', 'amount', '-amount', 'created', '-created'}


@require_safe
@cache_page(settings.VIEW_DONATIONS_CACHE)
def v_donations(request):
    order_by_var = request.GET.get('orderBy', 'id')
    if order_by_var not in VALID_ORDER_FIELDS:
        order_by_var = 'id'
    filter_by_var = request.GET.get('filterBy', 'none')
    record_count_var = request.GET.get('recordCount', '0')
    try:
        record_count_int = int(record_count_var)
    except ValueError:
        record_count_int = 0
    update_donations_if_needed.delay()
    listed_donations = DonationModel.objects.order_by(order_by_var).filter(team__id__in=el_teams())
    if filter_by_var != 'none' and filter_by_var.isdigit():
        listed_donations = listed_donations.filter(participant_id=filter_by_var, amount__isnull=False)
    else:
        listed_donations = listed_donations.filter(amount__isnull=False)
    if record_count_int > 0 and record_count_int <= settings.MAX_API_ROWS:
        listed_donations = listed_donations[:record_count_int]
    else:
        listed_donations = listed_donations[:settings.MAX_API_ROWS]
    return JsonResponse(
        [d for d in listed_donations.values()],
        safe=False,
    )


@require_safe
@cache_page(settings.VIEW_DONATIONS_CACHE)
def v_tracked_donations(request):
    order_by_var = request.GET.get('orderBy', 'id')
    if order_by_var not in VALID_ORDER_FIELDS:
        order_by_var = 'id'
    update_donations_if_needed.delay()
    return JsonResponse(
        [d for d in
         DonationModel.objects.filter(DonationModel.tracked_q()).order_by(order_by_var)[:settings.MAX_API_ROWS].values()],
        safe=False,
    )
