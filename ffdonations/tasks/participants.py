from __future__ import absolute_import, unicode_literals

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from extralifeapi.participants import Participants
from ffsfdc.models import *
from ..models import *


def _make_p(*args, **kwargs):
    """ Make a safe participant object """
    from ..helpers import el_request_sleeper
    kwargs.setdefault('request_sleeper', el_request_sleeper)
    return Participants(*args, **kwargs)


@shared_task(bind=True)
def update_participants_if_needed(self):
    """ Update the participants db if required """

    def doupdate():
        return update_participants()

    minc = timezone.now() - settings.EL_PTCP_UPDATE_FREQUENCY_MIN
    maxc = timezone.now() - settings.EL_PTCP_UPDATE_FREQUENCY_MAX

    if ParticipantModel.objects.all().count() <= 0:
        return doupdate()

    bq = ParticipantModel.objects.filter(tracked=True)

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
def update_participants(self, participants=None):
    """ Update data in the participants model from online data.
    WARNING: Listing participants causes an api call per participant given
    WARNING: If participants is None then will fetch a list of ALL participants
     Will take a TON of requests!!!
    """
    from .donations import update_donations_if_needed_participant, update_donations_if_needed_team
    p = _make_p()
    ret = []

    # Fetch data from EL
    if participants is None:
        if settings.EL_EVENT_ID >= 0:
            tr = p.participants_for_event(settings.EL_EVENT_ID)
        else:
            raise ValueError("Invalid settings.EL_EVENT_ID value")
    else:
        tr = [p.participant(int(participantID)) for participantID in participants]

    for participant in tr:
        if participant.eventID:
            try:
                evt = EventModel.objects.get(id=participant.eventID)
            except EventModel.DoesNotExist as e:
                evt = EventModel(tracked=False, id=participant.eventID)
                evt.save()
        else:
            evt = None

        if participant.teamID:
            try:
                team = TeamModel.objects.get(id=participant.teamID)
            except TeamModel.DoesNotExist as e:
                team = TeamModel(
                    tracked=False,
                    id=participant.teamID,
                    name=participant.teamName,
                )
                team.save()
        else:
            team = None

        # Get/create
        try:
            tm = ParticipantModel.objects.get(id=participant.participantID)
        except ParticipantModel.DoesNotExist as e:
            tm = ParticipantModel(
                tracked=False,
                id=participant.participantID,
            )
        tm.sumPledges = participant.sumPledges
        tm.displayName = participant.displayName
        tm.numDonations = participant.numDonations
        tm.sumDonations = participant.sumDonations
        # Handle nulls
        if participant.isTeamCaptain:
            tm.isTeamCaptain = True
        else:
            tm.isTeamCaptain = False
        tm.fundraisingGoal = participant.fundraisingGoal
        tm.avatarImage = participant.avatarImageURL
        tm.created = participant.createdDateUTC
        tm.event = evt
        tm.team = team
        tm.raw = participant.raw
        # Update tracked from org
        try:
            c = Contact.objects.get(extra_life_id=participant.participantID)
            tm.tracked = True
        except Contact.DoesNotExist as e:
            pass
        # Update tracked from parents
        if not tm.tracked and ((evt and evt.tracked) or (team and team.tracked)):
            tm.tracked = True
        # Save it
        tm.save()

        # Hook in donations update
        if tm.tracked:
            update_donations_if_needed_participant.delay(participantID=tm.id)
            if tm.team:
                update_donations_if_needed_team.delay(teamID=tm.team.id)

        ret.append(tm.guid)

    return ret
