from __future__ import absolute_import, unicode_literals

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from requests.exceptions import HTTPError

from extralifeapi.teams import Teams

from ..models import EventModel, TeamModel
from ..utils import current_el_events


def _make_team(*args, **kwargs):
    """ Make a safe team object """
    from fforg.rdbs import r_http_cache

    from ..helpers import el_request_sleeper
    kwargs.setdefault('request_sleeper', el_request_sleeper)
    kwargs.setdefault('http_cache', r_http_cache)
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


def _upsert_team(team, tracked_events=None):
    """ Upsert a TeamModel from an extralifeapi Team namedtuple and queue donation sync if tracked. """
    from .donations import update_donations_if_needed_team

    if team.eventID:
        try:
            evt = EventModel.objects.get(id=team.eventID)
        except EventModel.DoesNotExist:
            evt = EventModel(tracked=False, id=team.eventID, name=team.eventName)
            evt.save()
    else:
        evt = None

    try:
        tm = TeamModel.objects.get(id=team.teamID)
    except TeamModel.DoesNotExist:
        tm = TeamModel(
            tracked=False,
            id=team.teamID,
        )
    tm.name = team.name
    tm.team_group_name = team.teamGroupName
    tm.created = team.createdDateUTC
    tm.fundraising_goal = team.fundraisingGoal
    tm.num_donations = team.numDonations
    tm.sum_donations = team.sumDonations
    tm.event = evt
    tm.raw = team.raw

    if settings.EXTRALIFE_TEAMID >= 0 and tm.id == settings.EXTRALIFE_TEAMID:
        tm.tracked = True
    elif (
        not tm.tracked
        and getattr(settings, 'EXTRALIFE_TEAMGROUP_NAME', '')
        and team.teamGroupName == settings.EXTRALIFE_TEAMGROUP_NAME
        and tm.id >= settings.MIN_EL_TEAMID
    ):
        if tracked_events is None:
            tracked_events = current_el_events()
        if evt is not None and (evt.tracked or evt.id in tracked_events):
            tm.tracked = True

    tm.save()

    # Hook in donations update
    if tm.tracked:
        update_donations_if_needed_team.delay(team_id=tm.id)

    return tm


@shared_task(bind=True)
def update_teams(self, teams=None):
    """ Update data in the team model from online data.
    WARNING: Listing teams causes an api call per team given
    WARNING: If teams is None then will fetch all tracked teams and unresolved stubs
    """
    el_api = _make_team()
    ret = []
    if teams is None:
        team_ids = set(TeamModel.objects.filter(tracked=True).values_list('id', flat=True))
        # Also resolve newly created untracked stubs (e.g. from participant/donation sync)
        # so teams matching EXTRALIFE_TEAMGROUP_NAME are promoted automatically.
        team_ids.update(
            TeamModel.objects.filter(
                tracked=False,
                num_donations__isnull=True,
                id__gte=settings.MIN_EL_TEAMID,
            ).values_list('id', flat=True)
        )
        if settings.EXTRALIFE_TEAMID >= 0:
            team_ids.add(settings.EXTRALIFE_TEAMID)
        teams = sorted(team_ids)

    el_teams = []
    for tid in teams:
        try:
            el_teams.append(el_api.team(team_id=int(tid)))
        except (HTTPError, IndexError) as e:
            if isinstance(e, IndexError) or (e.response is not None and e.response.status_code == 404):
                try:
                    tm = TeamModel.objects.get(id=int(tid))
                    tm.tracked = False
                    tm.save()
                except TeamModel.DoesNotExist:
                    pass
            else:
                raise
    tracked_events = current_el_events()
    for team in el_teams:
        tm = _upsert_team(team, tracked_events=tracked_events)
        ret.append(tm.guid)
    return ret


@shared_task(bind=True)
def discover_teamgroup_teams(self):
    """ Scan current tracked events for teams matching EXTRALIFE_TEAMGROUP_NAME and track them. """
    group_name = getattr(settings, 'EXTRALIFE_TEAMGROUP_NAME', '')
    if not group_name:
        return []

    el_api = _make_team()
    tracked_events = current_el_events()
    ret = []
    for event_id in tracked_events:
        for team in el_api.event_teams(event_id):
            if team.teamGroupName == group_name and team.teamID >= settings.MIN_EL_TEAMID:
                tm = _upsert_team(team, tracked_events=tracked_events)
                ret.append(tm.guid)
    return ret
