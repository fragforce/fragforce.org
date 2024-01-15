from django.db import models


class EventRole(models.Model):
    """ A role a user can have on an event """
    name = models.CharField(max_length=255, unique=True, db_index=True, null=False, blank=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)
