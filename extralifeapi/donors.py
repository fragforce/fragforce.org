""" Donations """
from collections import namedtuple

from .base import DonorDriveBase
from .log import root_logger

mod_logger = root_logger.getChild('donors')
Donation = namedtuple('Donation',
                      [
                          'avatarImageURL',
                          'createdDateUTC',
                          'amount',
                          'displayName',
                          'donorID',
                          'donationID',
                          'participantID',
                          'teamID',
                          'message',
                          'raw',
                      ],
                      rename=True,
                      )


class Donations(DonorDriveBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def sub_by_pid(self, participant_id):
        return 'participants/%d/donations' % participant_id

    def sub_by_tid(self, team_id):
        return 'teams/%d/donations' % team_id

    @classmethod
    def _d_to_d(cls, data):
        kws = {}
        for f in Donation._fields:
            if f == 'raw':
                kws[f] = data
            else:
                kws[f] = data.get(f, None)
        return Donation(**kws)

    def donations_for_participants(self, participant_id):
        """ Get all donations for the given participant """
        fresp = self.fetch(sub_url=self.sub_by_pid(participant_id))
        for r in fresp:
            yield self._d_to_d(r)

    def donations_for_team(self, team_id):
        """ Get all donations for the given team """
        fresp = self.fetch(sub_url=self.sub_by_tid(team_id))
        for r in fresp:
            yield self._d_to_d(r)
