import requests
from celery import shared_task
from django.conf import settings

from ..models import *

TRACKING_BOT = 'TRACKING_BOT'


# @receiver(post_save, sender=DonationModel)
# def cb_post_save(sender, instance, **kwargs):
#     if settings.FRAG_BOT_KEY != "":
#         note_new_donation.delay(instance.id)


@shared_task(bind=True)
def note_new_donations(self):
    """ Check for missed donations """
    for donation in DonationModel.objects.filter(~Q(tracking__contains={TRACKING_BOT: "1"})).all():
        note_new_donation.delay(donation.id)


@shared_task(bind=True)
def note_new_donation(self, donationID):
    """ Send out a new donation """

    donation = DonationModel.objects.get(pk=donationID)

    # Don't send anything, but do mark the donation as tracked if no key set
    if settings.FRAG_BOT_KEY == "":
        donation.tracking[TRACKING_BOT] = '1'
        donation.tracking = donation.tracking.copy()
        donation.save()
        return

    # Skip ones we've already sent
    if donation.tracking.get(TRACKING_BOT, '0') == '1':
        return
    # Call the bot to send the chat message before the alert overlay
    message = f"Fragforce received a new donation of ${donation.amount}"

    if donation.displayName:
        message += f" from {donation.displayName}"
    else:
        message += " from Anonymous Coward"

    if donation.message:
        message += f" with the message: {donation.message}"

    payload = {
        'webauth': settings.FRAG_BOT_KEY,
        'user': settings.FRAG_BOT_BOT,
        'message': message.encode('utf-8'),
    }
    r = requests.put(settings.FRAG_BOT_API, headers=payload)
    r.raise_for_status()

    payload = {
        'webauth': settings.FRAG_BOT_KEY,
        'user': settings.FRAG_BOT_BOT,
        'message': '!bot_donate'
    }
    r = requests.put(settings.FRAG_BOT_API, headers=payload)
    r.raise_for_status()

    donation.tracking[TRACKING_BOT] = '1'
    donation.tracking = donation.tracking.copy()
    donation.save()
