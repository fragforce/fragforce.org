import logging

import pytz
from celery import shared_task

from .helpers import *
from ...models import *

log = logging.getLogger('ffdonations.tasks.tiltify.donations')


@shared_task(bind=True)
def update_donations(self, campaign_id):
    campaign = CampaignTiltifyModel.objects.get(id=campaign_id)

    tf = get_tiltify()

    updated = 0
    created = 0
    for c in tf.f_campaign_donations(campaign_id):
        log.warning("Working on campaign-donation %r", c.parsed.get('id', None), extra=dict(c=c.parsed))
        try:
            o = DonationTiltifyModel.objects.get(id=int(c.parsed.get('id')))

            n = {}
            for k in c.FIELDS_NORM:
                if c.parsed.get(k, None) is None:
                    continue
                if str(k) in ['completedAt', ]:
                    setattr(o, k, datetime.datetime.fromtimestamp(int(c.parsed.get(k, None)) / 1000, tz=pytz.UTC))
                else:
                    setattr(o, k, str(c.parsed.get(k, None)))

            # if c.parsed.get('rewardId',None):
            # TODO: Add rewards

            o.campaign_id = campaign.id
            o.raw = c.data
            o.subtype = c.__class__.__name__

            o.save()
            updated += 1
        except DonationTiltifyModel.DoesNotExist as e:
            n = {}
            for k in c.FIELDS_NORM:
                if c.parsed.get(k, None) is None:
                    continue
                if str(k) in ['completedAt', ]:
                    n[str(k)] = datetime.datetime.fromtimestamp(int(c.parsed.get(k)) / 1000, tz=pytz.UTC)
                else:
                    n[str(k)] = str(c.parsed.get(k))

            o = DonationTiltifyModel(
                raw=c.data,
                subtype=c.__class__.__name__,
                campaign=campaign,
                **n,
            )

            o.save()
            created += 1

    return created, updated
