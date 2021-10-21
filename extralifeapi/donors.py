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

    def sub_by_pid(self, participantID):
        return 'participants/%d/donations' % participantID

    def sub_by_tid(self, teamID):
        return 'teams/%d/donations' % teamID

    @classmethod
    def _d_to_d(cls, data):
        kws = {}
        for f in Donation._fields:
            if f == 'raw':
                kws[f] = data
            else:
                kws[f] = data.get(f, None)
        return Donation(**kws)

    def donations_for_participants(self, participantID):
        """ Get all donations for the given participant """
        fresp = self.fetch(sub_url=self.sub_by_pid(participantID))
        for r in fresp:
            yield self._d_to_d(r)

    def donations_for_team(self, teamID):
        """ Get all donations for the given team """
        fresp = self.fetch(sub_url=self.sub_by_tid(teamID))
        for r in fresp:
            yield self._d_to_d(r)
