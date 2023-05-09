from __future__ import absolute_import, unicode_literals

from celery import shared_task
from django.conf import settings

from extralifeapi.teams import Teams
from ffsfdc.models import *
from ..models import *


def _make_team(*args, **kwargs):
    """ Make a safe team object """
    from ..helpers import el_request_sleeper
    kwargs.setdefault('request_sleeper', el_request_sleeper)
    return Teams(*args, **kwargs)


@shared_task(bind=True)
def update_teams_if_needed(self):
    """ Update the team db if required """

    def doupdate():
        return update_teams()

    if TeamModel.objects.all().count() <= 0:
        return doupdate()

    minc = timezone.now() - settings.EL_TEAM_UPDATE_FREQUENCY_MIN
    maxc = timezone.now() - settings.EL_TEAM_UPDATE_FREQUENCY_MAX

    bq = TeamModel.objects.filter(tracked=True)

    # Skip updating if it's been less than EL_TEAM_UPDATE_FREQUENCY_MIN since last update
    # for any record
    if bq.filter(last_updated__gte=minc).count() > 0:
        return None

    # Force an update if it's been more than EL_TEAM_UPDATE_FREQUENCY_MAX since last
    # update for any record
    if bq.filter(last_updated__lte=maxc).count() > 0:
        return doupdate()

    # Guess we'll do an update!
    return doupdate()


@shared_task(bind=True)
def update_teams(self, teams=None):
    """ Update data in the team model from online data.
    WARNING: Listing teams causes an api call per team given
    WARNING: If teams is None then will fetch a list of ALL teams - May make many requests
    """
    from .donations import update_donations_if_needed_team
    el_api = _make_team()
    ret = []
    if teams is None:
        teams = []
        if settings.EXTRALIFE_TEAMID >= 0:
            teams.append(settings.EXTRALIFE_TEAMID)
        for sa in SiteAccount.objects.filter(el_id__isnull=False):
            if int(sa.el_id) >= settings.MIN_EL_TEAMID:
                teams.append(int(sa.el_id))

    el_teams = [el_api.team(teamID=int(tid)) for tid in teams]
    for team in el_teams:
        if team.eventID:
            try:
                evt = EventModel.objects.get(id=team.eventID)
            except EventModel.DoesNotExist as e:
                evt = EventModel(tracked=False, id=team.eventID, name=team.eventName)
                evt.save()
        else:
            evt = None

        try:
            tm = TeamModel.objects.get(id=team.teamID)

        except TeamModel.DoesNotExist as e:
            tm = TeamModel(
                tracked=False,
                id=team.teamID,
            )
        tm.name = team.name
        tm.created = team.createdDateUTC
        tm.fundraisingGoal = team.fundraisingGoal
        tm.numDonations = team.numDonations
        tm.sumDonations = team.sumDonations
        tm.event = evt

        # Update tracked from org
        try:
            if SiteAccount.objects.filter(el_id=team.teamID).order_by('-createddate').count() > 0:
                tm.tracked = True
        except SiteAccount.DoesNotExist as e:
            pass
        except IndexError as e:
            pass

        tm.raw = team.raw
        if settings.EXTRALIFE_TEAMID >= 0:
            if tm.id == settings.EXTRALIFE_TEAMID:
                tm.tracked = True
        tm.save()

        # Hook in donations update
        if tm.tracked:
            update_donations_if_needed_team.delay(teamID=tm.id)

        ret.append(tm.guid)
    return ret
