from django.db import models
from django_workflow_engine.executor import User


class DiscordEventUser(models.Model):
    """ Created if a User maps to a discord ID """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    discord_id = models.CharField(max_length=255, blank=False, db_index=True, null=False, unique=True)


class SalesforceEventUser(models.Model):
    """ Created if a user maps to a SFID """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    salesforce_id = models.CharField(max_length=64, blank=False, db_index=True, null=False, unique=True)


class ExtraLifeEventUser(models.Model):
    """ Created if a user maps to an extra life user """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    el_participant_id = models.PositiveBigIntegerField(blank=False, db_index=True, null=False, unique=True)
    # el_participant_url = models.URLField(max_length=8192, blank=False, null=False) # calc'ed
