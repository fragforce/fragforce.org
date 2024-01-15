from django.contrib.postgres.fields import HStoreField
from django.db import models
from django_workflow_engine.executor import User


class Team(models.Model):
    """ A team or group of people who do events """
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    team_info = HStoreField(default=dict, null=False)
    role = models.ForeignKey('TeamRole', on_delete=models.CASCADE, blank=False, null=False)
    description = models.TextField(default='', blank=False, null=False)


class TeamRole(models.Model):
    """ A role a user can have in a team """
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)


class TeamMember(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, blank=False, null=False)
    role = models.ForeignKey(TeamRole, on_delete=models.CASCADE, blank=False, null=False)

    class Meta:
        unique_together = [
            ["user", "team"],  # Basic overlap check
        ]
