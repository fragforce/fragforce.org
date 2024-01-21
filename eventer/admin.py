from django.contrib import admin

from eventer.models import Event, EventPeriod, EventRole, Game, GameStatus, Team, TeamMember, TeamRole


@admin.register(EventPeriod)
class EventPeriodAdmin(admin.ModelAdmin):
    pass


@admin.register(EventRole)
class EventRoleAdmin(admin.ModelAdmin):
    pass


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    pass


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    pass


@admin.register(GameStatus)
class GameStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    pass


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    pass


@admin.register(TeamRole)
class TeamRoleAdmin(admin.ModelAdmin):
    pass
