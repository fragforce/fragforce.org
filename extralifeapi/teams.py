""" Teams """
from collections import namedtuple

from .base import DonorDriveBase
from .log import root_logger

Team = namedtuple('Team',
                  [
                      'teamID',
                      'name',
                      'avatarImageURL',
                      'createdDateUTC',
                      'eventID',
                      'eventName',
                      'fundraisingGoal',
                      'numDonations',
                      'sumDonations',
                      'raw',
                  ],
                  rename=True,
                  )
mod_logger = root_logger.getChild('teams')


class Teams(DonorDriveBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def sub_team(self):
        return 'teams'

    def sub_team_by_tid(self, team_id):
        return 'teams/%s' % team_id

    def sub_team_by_eid(self, event_id):
        return 'events/%d/teams' % event_id

    @classmethod
    def _team_to_team(cls, data):
        kws = {}
        for f in Team._fields:
            if f == 'raw':
                kws[f] = data
            else:
                kws[f] = dict(data).get(f, None)
        return Team(**kws)

    def teams(self):
        """ Return a generator of all teams as Team named tuples """
        fresp = self.fetch(sub_url=self.sub_team())
        for t in fresp:
            yield self._team_to_team(t)

    def team(self,team_id):
        """ Get a team """
        results = list(self.fetch(sub_url=self.sub_team_by_tid(team_id)))
        if not results:
            raise IndexError(f"No team found for teamID={team_id}")
        fresp = results[0]
        self.log.info("fresp=", extra=dict(fresp=fresp))
        return self._team_to_team(fresp)

    def event_teams(self, event_id):
        """ Return a generator of all teams as Team named tuples for the given event """
        fresp = self.fetch(sub_url=self.sub_team_by_eid(event_id))
        for t in fresp:
            yield self._team_to_team(t)
