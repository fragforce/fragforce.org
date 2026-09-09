""" Participants """
from collections import namedtuple

from .base import DonorDriveBase
from .log import root_logger

mod_logger = root_logger.getChild('participants')
Participant = namedtuple('Participant',
                         [
                             'avatarImageURL',
                             'campaignDate',
                             'campaignName',
                             'createdDateUTC',
                             'displayName',
                             'eventID',
                             'eventName',
                             'fundraisingGoal',
                             'isTeamCaptain',
                             'numDonations',
                             'participantID',
                             'sumPledges',
                             'sumDonations',
                             'teamID',
                             'teamName',
                             'raw',
                         ],
                         rename=True,
                         )


class Participants(DonorDriveBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def sub_base(self):
        return 'participants'

    def sub_by_pid(self, participant_id):
        return 'participants/%s' % participant_id

    def sub_by_eid(self, event_id):
        return 'events/%d/participants' % event_id

    def sub_by_tid(self, team_id):
        return 'teams/%d/participants' % team_id

    @classmethod
    def _p_to_p(cls, data):
        kws = {}
        for f in Participant._fields:
            if f == 'raw':
                kws[f] = data
            else:
                kws[f] = dict(data).get(f, None)
        return Participant(**kws)

    def participants(self):
        """ Get a list of ALL EL participants
        WARNING: This takes a LOT of requests! It's a ton of data...
        """
        fresp = self.fetch(sub_url=self.sub_base())
        for t in fresp:
            yield self._p_to_p(t)

    def participant(self, participant_id):
        """ Get a single EL participant
        """
        fresp = list(self.fetch(sub_url=self.sub_by_pid(participant_id)))[0]
        return self._p_to_p(fresp)

    def participants_for_event(self, event_id):
        """ Get all participants for the given event """
        fresp = self.fetch(sub_url=self.sub_by_eid(event_id))
        for t in fresp:
            yield self._p_to_p(t)

    def participants_for_team(self, team_id):
        """ Get all participants for the given team """
        fresp = self.fetch(sub_url=self.sub_by_tid(team_id))
        for t in fresp:
            yield self._p_to_p(t)
