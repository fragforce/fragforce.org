from __future__ import absolute_import, unicode_literals

import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from requests.exceptions import HTTPError

from extralifeapi.donors import Donations
from ..models import *
from .sender import note_new_donation

log = logging.getLogger("donations")


def _make_d(*args, **kwargs):
    """ Make a safe Donations object """
    from ..helpers import el_request_sleeper
    kwargs.setdefault('request_sleeper', el_request_sleeper)
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
    teamIDs = DonationModel.objects.filter(team__isnull=False).values('team').distinct('team')
    participantIDs = DonationModel.objects.filter(participant__isnull=False).values('participant').distinct(
        'participant')

    ret = []
    for teamID in teamIDs:
        ret.append(update_donations_if_needed_team.delay(teamID=teamID['team']).id)
    for participantID in participantIDs:
        ret.append(update_donations_if_needed_participant.delay(participantID=participantID['participant']).id)
    return ret


@shared_task(bind=True)
def update_donations_if_needed_team(self, teamID):
    log.debug("update_donations_if_needed_team: %r", teamID)

    def doupdate():
        return update_donations_team(teamID=teamID)

    try:
        team = TeamModel.objects.get(id=teamID)
    except TeamModel.DoesNotExist as e:
        # Silently exit for now - It might not have been committed yet - will get next time ;)
        # TODO: Log this
        return None

    minc = timezone.now() - settings.EL_DON_TEAM_UPDATE_FREQUENCY_MIN
    maxc = timezone.now() - settings.EL_DON_TEAM_UPDATE_FREQUENCY_MAX
    minTeamID = settings.MIN_EL_TEAMID
    # Don't query any team with an id < MIN_EL_TEAMID, as those are from prior years
    if teamID < minTeamID:
        team.tracked = False
        team.save()
        return None

    assert team.tracked, f"Expected a tracked team - Got {team}"
    if DonationModel.objects.all().count() <= 0:
        return doupdate()

    bfilter = DonationModel.objects.filter(team=team)
    # Skip updating if it's been less than EL_DON_TEAM_UPDATE_FREQUENCY_MIN since last update
    # for any record - do this first
    if bfilter.filter(last_updated__gte=minc).count() > 0:
        return None

    # Only force this if there are known donations but none in DB
    # Don't simplify to != as this could cause trashing if team update is behind the donations
    # update
    #if team.numDonations > 0 and bfilter.count() <= 0:
    if team.numDonations >0 and bfilter.count() < team.numDonations:
        return doupdate()

    # Force an update if it's been more than EL_DON_TEAM_UPDATE_FREQUENCY_MAX since last
    # update for any record
    if bfilter.filter(last_updated__lte=maxc).count() > 0:
        return doupdate()

    # if all else fails
    return doupdate()

@shared_task(bind=True)
def update_donations_team(self, teamID):
    """ """
    d = _make_d()
    ret = []

    if teamID is None:
        return ret

    try:
        team = TeamModel.objects.get(id=teamID)
    except TeamModel.DoesNotExist as e:
        team = TeamModel(id=teamID, tracked=False)
        team.save()

    if not team.tracked:
        return None

    for donation in d.donations_for_team(teamID=teamID):
        # Get/create participant if it's set...
        if donation.participantID:
            try:
                participant = ParticipantModel.objects.get(id=donation.participantID)
            except ParticipantModel.DoesNotExist as e:
                participant = ParticipantModel(id=donation.participantID, tracked=False)
                participant.save()
        else:
            participant = None

        try:
            tm = DonationModel.objects.get(id=donation.donationID)
        except DonationModel.DoesNotExist as e:
            tm = DonationModel(id=donation.donationID)
        tm.team = team
        tm.participant = participant
        tm.raw = donation.raw
        tm.avatarImage = donation.avatarImageURL
        if donation.displayName:
            tm.displayName = donation.displayName
        else:
            tm.displayName = ''
        tm.created = donation.createdDateUTC
        tm.amount = donation.amount
        if donation.message:
            tm.message = donation.message
        else:
            tm.message = ''
        tm.save()

        note_new_donation.s()(tm.id)

@shared_task(bind=True)
def update_donations_if_needed_participant(self, participantID):
    log.debug("update_donations_if_needed_participant: %r", participantID)

    def doupdate():
        return update_donations_participant(participantID=participantID)

    try:
        participant = ParticipantModel.objects.get(id=participantID)
    except ParticipantModel.DoesNotExist as e:
        # Silently exit for now - It might not have been committed yet - will get next time ;)
        # TODO: Log this
        return None

    minc = timezone.now() - settings.EL_DON_PTCP_UPDATE_FREQUENCY_MIN
    maxc = timezone.now() - settings.EL_DON_PTCP_UPDATE_FREQUENCY_MAX
    minParticipantID = settings.MIN_EL_PARTICIPANTID

    # Do not poll the api for participant IDs that are less than our min value
    # These correspond to participant ids from previous years, and are not valid anymore
    if participantID < minParticipantID:
        participant.tracked = False
        participant.last_updated = timezone.now()
        participant.save()
        return None

    # Participant not tracked
    if not participant.tracked:
        log.debug(f"Expected a tracked participant - Got {participant}")
        return None

    if DonationModel.objects.all().count() <= 0:
        return doupdate()

    bfilter = DonationModel.objects.filter(participant=participant)

    # Skip updating if it's been less than EL_DON_PTCP_UPDATE_FREQUENCY_MIN since last update
    # for any record
    if bfilter.filter(last_updated__gte=minc).count() > 0:
        return None
    
    # Only force this if there are known donations but none in DB
    # Don't simplify to != as this could cause trashing if team update is behind the donations
    # update
    #if participant.numDonations > 0 and bfilter.count() <= 0:
    if participant.numDonations > 0 and bfilter.count() < participant.numDonations:
        return doupdate()

    # Force an update if it's been more than EL_DON_PTCP_UPDATE_FREQUENCY_MAX since last
    # update for any record
    if bfilter.filter(last_updated__lte=maxc).count() > 0:
        return doupdate()

    # if all else fails
    return doupdate()


@shared_task(bind=True)
def update_donations_participant(self, participantID):
    """ """
    d = _make_d()
    ret = []

    if participantID is None:
        return ret

    try:
        participant = ParticipantModel.objects.get(id=participantID)
    except ParticipantModel.DoesNotExist as e:
        participant = ParticipantModel(id=participantID, tracked=False)
        participant.save()

    # Participant not tracked
    if not participant.tracked:
        log.debug(f"Expected a tracked participant - Got {participant}")
        return ret

    try:
        donations = list(d.donations_for_participants(participantID=participantID))
    except HTTPError:
        participant.tracked = False
        participant.last_updated = timezone.now()
        participant.save()
        return None

    for donation in donations:
        # Get/create participant if it's set...
        if donation.teamID:
            try:
                team = TeamModel.objects.get(id=donation.teamID)
            except TeamModel.DoesNotExist as e:
                team = TeamModel(id=donation.teamID, tracked=False)
                team.save()
        else:
            team = None

        try:
            tm = DonationModel.objects.get(id=donation.donationID)
        except DonationModel.DoesNotExist as e:
            tm = DonationModel(id=donation.donationID)
        tm.team = team
        tm.participant = participant
        tm.raw = donation.raw
        tm.avatarImage = donation.avatarImageURL
        if donation.displayName:
            tm.displayName = donation.displayName
        else:
            tm.displayName = ''
        tm.created = donation.createdDateUTC
        tm.amount = donation.amount
        if donation.message:
            tm.message = donation.message
        else:
            tm.message = ''
        tm.save()

        note_new_donation.s()(tm.id)

        ret.append(tm.guid)
    return ret
