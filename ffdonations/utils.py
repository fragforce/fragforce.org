from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from memoize import memoize

from .models import EventModel, TeamModel


@memoize(timeout=120)
def event_name_maker(year=timezone.now().year):
    return 'Extra Life %d' % year


@memoize(timeout=120)
def el_teams(year=timezone.now().year):
    """ Returns a list of team IDs that we're tracking for the given year """
    ret = set()
    # Always include the EXTRALIFE_TEAMID team
    if settings.EXTRALIFE_TEAMID > 0:
        ret.add(settings.EXTRALIFE_TEAMID)
    # Append all tracked teams in the current event
    tracked_teams = TeamModel.objects.filter(tracked=True, event__id__in=current_el_events())
    for tm in tracked_teams:
        ret.add(tm.id)
    return ret

@memoize(timeout=120)
def el_num_donations(year=timezone.now().year):
    """ For current year """
    teams = TeamModel.objects.filter(id__in=el_teams(year=year))
    tsum = teams.aggregate(ttl=Sum('numDonations')).get('ttl', 0)
    if tsum is None:
        tsum = 0
    return dict(
        countDonations=float(tsum),
    )


@memoize(timeout=120)
def el_donation_stats(year=timezone.now().year):
    """ For current year """
    teams = TeamModel.objects.filter(id__in=el_teams(year=year))
    tsum = teams.aggregate(ttl=Sum('sumDonations')).get('ttl', 0)
    if tsum is None:
        tsum = 0
    return dict(
        sumDonations=float(tsum),
    )


@memoize(timeout=3600)
def current_el_events():
    """ Gets a list of valid events """
    ret = set([e.id for e in EventModel.objects.filter(tracked=True).all()])

    if settings.EXTRALIFE_TEAMID >= 0:
        try:
            ret.add(TeamModel.objects.get(id=settings.EXTRALIFE_TEAMID).event_id)
        except TeamModel.DoesNotExist:
            pass

    return list(ret)
