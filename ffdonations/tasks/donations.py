from __future__ import absolute_import, unicode_literals

import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from requests.exceptions import HTTPError

from extralifeapi.donors import Donations

from ..models import DonationModel, ParticipantModel, TeamModel
from ..utils import current_el_events
from .sender import note_new_donation

log = logging.getLogger("donations")


def _make_d(*args, **kwargs):
    """ Make a safe Donations object """
    from fforg.rdbs import r_http_cache

    from ..helpers import el_request_sleeper
    kwargs.setdefault('request_sleeper', el_request_sleeper)
    kwargs.setdefault('http_cache', r_http_cache)
    return Donations(*args, **kwargs)


@shared_task(bind=True)
def update_donations_if_needed(self):
    """ Update the donations db if required - This updates all EXISTING donations!
    May not capture ones if we don't have donations for that team/participant already.
    See update_donations_if_needed_team and update_donations_if_needed_participant.
    """
    log.debug("update_donations_if_needed: n/a")

    def doupdate():
        return update_donations_existing()

    minc = timezone.now() - settings.EL_DON_UPDATE_FREQUENCY_MIN
    maxc = timezone.now() - settings.EL_DON_UPDATE_FREQUENCY_MAX

    if DonationModel.objects.all().count() <= 0:
        return doupdate()

    bq = DonationModel.objects

    # Force an update if it's been more than EL_TEAM_UPDATE_FREQUENCY_MAX since last
    # update for any record
    if bq.filter(last_updated__lte=maxc).count() > 0:
        return doupdate()

    # Skip updating if it's been less than EL_TEAM_UPDATE_FREQUENCY_MIN since last update
    # for any record
    if bq.filter(last_updated__gte=minc).count() > 0:
        return None

    # Guess we'll do an update!
    return doupdate()


@shared_task(bind=True)
def update_donations_existing(self):
    """ Update donations based on all existing participants and teams that are known based
    on the donations DB
    """
    evts = current_el_events()
    team_ids = DonationModel.objects.filter(
        team__isnull=False,
        team__event__id__in=evts).values('team').distinct('team')
    participant_ids = DonationModel.objects.filter(participant__isnull=False, participant__event__id__in=evts).values(
        'participant').distinct('participant')

    ret = []
    for team_id in team_ids:
        ret.append(update_donations_if_needed_team.delay(team_id=team_id['team']).id)
    for participant_id in participant_ids:
        ret.append(update_donations_if_needed_participant.delay(participant_id=participant_id['participant']).id)
    return ret


@shared_task(bind=True)
def update_donations_if_needed_team(self, team_id):
    log.debug("update_donations_if_needed_team: %r", team_id)

    def doupdate():
        return update_donations_team(team_id=team_id)

    try:
        team = TeamModel.objects.get(id=team_id)
    except TeamModel.DoesNotExist:
        # Silently exit for now - It might not have been committed yet - will get next time ;)
        # TODO: Log this
        return None

    # Gotta be in a tracked (or should be tracked) event
    if team.event_id not in current_el_events():
        return None

    minc = timezone.now() - settings.EL_DON_TEAM_UPDATE_FREQUENCY_MIN
    maxc = timezone.now() - settings.EL_DON_TEAM_UPDATE_FREQUENCY_MAX
    min_team_id = settings.MIN_EL_TEAMID
    # Don't query any team with an id < MIN_EL_TEAMID, as those are from prior years
    if team_id < min_team_id:
        team.tracked = False
        team.save()
        return None

    assert team.tracked, f"Expected a tracked team - Got {team}"
    if DonationModel.objects.all().count() <= 0:
        return doupdate()

    # Match on team and event id
    bfilter = DonationModel.objects.filter(team=team)
    # Skip updating if it's been less than EL_DON_TEAM_UPDATE_FREQUENCY_MIN since last update
    # for any record - do this first. The MIN_FREQUENCY is to avoid hammering the API, the MAX_FREQUENCY tells us
    # when data is stale and should be refreshed. Even if we don't check anywhere near the MIN_FREQUENCY, it is an
    # absolute minimum time between requests so that we don't hammer the donor drive API.
    if bfilter.filter(last_updated__gte=minc).count() > 0:
        return None

    # No donation records yet - throttle via the team record itself to avoid hammering the API
    if bfilter.count() == 0 and team.last_updated >= minc:
        return None

    # Only force this if there are known donations but none in DB
    # Don't simplify to != as this could cause thrashing if team update is behind the donations
    # update
    # if team.numDonations > 0 and bfilter.count() <= 0:
    if team.num_donations is None:
        return None

    if team.num_donations > 0 and bfilter.count() < team.num_donations:
        return doupdate()

    # Force an update if it's been more than EL_DON_TEAM_UPDATE_FREQUENCY_MAX since last
    # update for any record
    if bfilter.filter(last_updated__lte=maxc).count() > 0:
        return doupdate()

    # if all else fails
    return doupdate()


@shared_task(bind=True)
def update_donations_team(self, team_id):
    """ """
    d = _make_d()
    ret = []

    if team_id is None:
        return ret

    try:
        team = TeamModel.objects.get(id=team_id)
    except TeamModel.DoesNotExist:
        team = TeamModel(id=team_id, tracked=False)
        team.save()

    # Team has to be tracked
    if not team.tracked:
        return None

    # Gotta be in a tracked (or should be tracked) event
    if team.event_id not in current_el_events():
        return None

    try:
        donations_list = list(d.donations_for_team(team_id=team_id))
    except HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            team.tracked = False
            team.save()
        else:
            raise
        return ret

    for donation in donations_list:
        # Get/create participant if it's set...
        if donation.participantID:
            try:
                participant = ParticipantModel.objects.get(id=donation.participantID)
            except ParticipantModel.DoesNotExist:
                participant = ParticipantModel(id=donation.participantID, tracked=False)
                participant.save()
        else:
            participant = None

        try:
            tm = DonationModel.objects.get(id=donation.donationID)
        except DonationModel.DoesNotExist:
            tm = DonationModel(id=donation.donationID)
        tm.team = team
        tm.participant = participant
        tm.raw = donation.raw
        tm.avatar_image = donation.avatarImageURL
        if donation.displayName:
            tm.display_name = donation.displayName
        else:
            tm.display_name = ''
        tm.created = donation.createdDateUTC
        tm.amount = donation.amount
        if donation.message:
            tm.message = donation.message
        else:
            tm.message = ''
        tm.save()

        note_new_donation.apply_async((tm.id,), queue='alerts')


@shared_task(bind=True)
def update_donations_if_needed_participant(self, participant_id):
    log.debug("update_donations_if_needed_participant: %r", participant_id)

    def doupdate():
        return update_donations_participant(participant_id=participant_id)

    try:
        participant = ParticipantModel.objects.get(id=participant_id)
    except ParticipantModel.DoesNotExist:
        # Silently exit for now - It might not have been committed yet - will get next time ;)
        # TODO: Log this
        return None

    minc = timezone.now() - settings.EL_DON_PTCP_UPDATE_FREQUENCY_MIN
    maxc = timezone.now() - settings.EL_DON_PTCP_UPDATE_FREQUENCY_MAX
    min_participant_id = settings.MIN_EL_PARTICIPANTID

    # Do not poll the api for participant IDs that are less than our min value
    # These correspond to participant ids from previous years, and are not valid anymore
    if participant_id < min_participant_id:
        participant.tracked = False
        participant.last_updated = timezone.now()
        participant.save()
        return None

    # Participant not tracked
    if not participant.tracked:
        log.debug(f"Expected a tracked participant - Got {participant}")
        return None

    if participant.event_id not in current_el_events():
        log.debug(f"Expected a participant in a tracked event - Got {participant}")
        return None

    if DonationModel.objects.all().count() <= 0:
        return doupdate()

    bfilter = DonationModel.objects.filter(participant=participant)

    # Skip updating if it's been less than EL_DON_PTCP_UPDATE_FREQUENCY_MIN since last update
    # for any record
    if bfilter.filter(last_updated__gte=minc).count() > 0:
        return None

    # No donation records yet - throttle via the participant record itself to avoid hammering the API
    if bfilter.count() == 0 and participant.last_updated >= minc:
        return None

    # Only force this if there are known donations but none in DB
    # Don't simplify to != as this could cause trashing if team update is behind the donations
    # update
    # if participant.numDonations > 0 and bfilter.count() <= 0:
    if participant.num_donations > 0 and bfilter.count() < participant.num_donations:
        return doupdate()

    # Force an update if it's been more than EL_DON_PTCP_UPDATE_FREQUENCY_MAX since last
    # update for any record
    if bfilter.filter(last_updated__lte=maxc).count() > 0:
        return doupdate()

    # if all else fails
    return doupdate()


@shared_task(bind=True)
def update_donations_participant(self, participant_id):
    """ """
    d = _make_d()
    ret = []

    if participant_id is None:
        return ret

    try:
        participant = ParticipantModel.objects.get(id=participant_id)
    except ParticipantModel.DoesNotExist:
        participant = ParticipantModel(id=participant_id, tracked=False)
        participant.save()

    # Participant not tracked
    if not participant.tracked:
        log.debug(f"Expected a tracked participant - Got {participant}")
        return ret

    if participant.event_id not in current_el_events():
        log.debug(f"Expected a participant in a tracked event - Got {participant}")
        return ret

    try:
        donations = list(d.donations_for_participants(participant_id=participant_id))
    except HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            participant.tracked = False
            participant.last_updated = timezone.now()
            participant.save()
            return None
        raise

    for donation in donations:
        # Get/create participant if it's set...
        if donation.teamID:
            try:
                team = TeamModel.objects.get(id=donation.teamID)
            except TeamModel.DoesNotExist:
                team = TeamModel(id=donation.teamID, tracked=False)
                team.save()
        else:
            team = None

        try:
            tm = DonationModel.objects.get(id=donation.donationID)
        except DonationModel.DoesNotExist:
            tm = DonationModel(id=donation.donationID)
        tm.team = team
        tm.participant = participant
        tm.raw = donation.raw
        tm.avatar_image = donation.avatarImageURL
        if donation.displayName:
            tm.display_name = donation.displayName
        else:
            tm.display_name = ''
        tm.created = donation.createdDateUTC
        tm.amount = donation.amount
        if donation.message:
            tm.message = donation.message
        else:
            tm.message = ''
        tm.save()

        note_new_donation.apply_async((tm.id,), queue='alerts')

        ret.append(tm.guid)
    return ret
