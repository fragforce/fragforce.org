import logging

import pytz
from celery import shared_task
from django.utils import timezone

from .donations import update_donations
from .helpers import *
from ...models import *

log = logging.getLogger('ffdonations.tasks.tiltify.campaigns')


@shared_task(bind=True)
def update_campaigns(self, team_id):
    team = TeamTiltifyModel.objects.get(id=team_id)

    tf = get_tiltify()

    updated = 0
    created = 0
    for c in tf.f_team_campaigns(team.id):
        log.warning("Working on team-campaign %r", c.parsed.get('id', None), extra=dict(c=c.parsed))
        try:
            o = CampaignTiltifyModel.objects.get(id=int(c.parsed.get('id')))

            n = {}
            for k in c.FIELDS_NORM:
                if c.parsed.get(k, None) is None:
                    continue
                if str(k) in ['startsAt', 'endsAt']:
                    setattr(o, k, datetime.datetime.fromtimestamp(int(c.parsed.get(k, None)) / 1000, tz=pytz.UTC))
                else:
                    setattr(o, k, str(c.parsed.get(k, None)))

            o.team_id = team.id
            o.raw = c.data
            o.subtype = c.__class__.__name__

            o.save()
            updated += 1
        except CampaignTiltifyModel.DoesNotExist as e:
            n = {}
            for k in c.FIELDS_NORM:
                if c.parsed.get(k, None) is None:
                    continue
                if str(k) in ['startsAt', 'endsAt']:
                    n[str(k)] = datetime.datetime.fromtimestamp(int(c.parsed.get(k)) / 1000, tz=pytz.UTC)
                else:
                    n[str(k)] = str(c.parsed.get(k))

            o = CampaignTiltifyModel(
                raw=c.data,
                subtype=c.__class__.__name__,
                team=team,
                **n,
            )

            o.save()
            created += 1

        # Get donations, if active
        if o.startsAt < timezone.now() < o.endsAt:
            update_donations.apply_async(args=(o.id,), ignore_results=True)

    return created, updated
