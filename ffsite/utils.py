from random import choice

from ffdonations.models import ParticipantModel
from ffdonations.utils import el_teams


def random_contact():
    """ Returns a randomly selected Contact """
    # Limit all queries to these
    participants = ParticipantModel.objects.filter(team__id__in=el_teams())
    if len(participants) > 0:
        pk = choice(participants)
    else:
        pk = ParticipantModel()
    if pk:
        return pk
    else:
        # Retry if the contact doesn't exist
        return random_contact()
