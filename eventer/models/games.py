from django.contrib.postgres.fields import HStoreField
from django.db import models


class Game(models.Model):
    """ An IGDB backed game """

    name = models.CharField(max_length=255, unique=True, db_index=True, null=False, blank=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)
    igdb_id = models.SlugField(max_length=255, blank=False, null=False, unique=True)
    status = models.ForeignKey('GameStatus', on_delete=models.CASCADE, blank=False, null=False)
    flags = HStoreField(default=dict, blank=False, null=False)


class GameStatus(models.Model):
    """ Game's approval status """
    name = models.CharField(max_length=255, unique=True, db_index=True, null=False, blank=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)
