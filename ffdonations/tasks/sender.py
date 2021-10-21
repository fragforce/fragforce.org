from celery import shared_task
from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import *
from django.conf import settings
import requests


@receiver(post_save, sender=DonationModel)
def cb_post_save(sender, instance, **kwargs):
    if settings.FRAG_BOT_KEY != "":
        note_new_donation.delay(instance.id)


@shared_task(bind=True)
def note_new_donation(self, donationID):
    """ Send out a new donation """
    # Do nothing if no key set
    if settings.FRAG_BOT_KEY == "":
        return

    donation = DonationModel.objects.get(pk=donationID)

    payload = {
        'webauth': settings.FRAG_BOT_KEY,
        'user': settings.FRAG_BOT_BOT,
        'message': '!bot_donate'
    }
    r = requests.put(settings.FRAG_BOT_API, headers=payload)
    r.raise_for_status()

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
        'message': message,
    }
    r = requests.put(settings.FRAG_BOT_API, headers=payload)
    r.raise_for_status()
