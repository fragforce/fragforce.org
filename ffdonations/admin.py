from django.contrib import admin

from .models import *
from .tasks.donations import update_donations_if_needed_team, update_donations_if_needed_participant


@admin.register(TeamModel)
class TeamModelAdmin(admin.ModelAdmin):
    actions = ['sync_donations']

    @admin.action(description='Sync donations for selected teams')
    def sync_donations(self, request, queryset):
        count = 0
        for team in queryset:
            update_donations_if_needed_team.delay(teamID=team.id)
            count += 1
        self.message_user(request, f"Queued donation sync for {count} team(s).")


# Register your models here.
admin.site.register(EventModel)
@admin.register(ParticipantModel)
class ParticipantModelAdmin(admin.ModelAdmin):
    actions = ['sync_donations']

    @admin.action(description='Sync donations for selected participants')
    def sync_donations(self, request, queryset):
        count = 0
        for participant in queryset:
            update_donations_if_needed_participant.delay(participantID=participant.id)
            count += 1
        self.message_user(request, f"Queued donation sync for {count} participant(s).")
admin.site.register(DonationModel)
admin.site.register(MediaTiltifyModel)
admin.site.register(RewardTiltifyModel)
admin.site.register(SocailTiltifyModel)
admin.site.register(AddressTiltifyModel)
admin.site.register(ColorTiltifyModel)
admin.site.register(SettingsTiltifyModel)
admin.site.register(CauseTiltifyModel)
admin.site.register(EventTiltifyModel)
admin.site.register(LiveStreamTiltifyModel)
admin.site.register(TeamTiltifyModel)
admin.site.register(UserTiltifyModel)
admin.site.register(CampaignTiltifyModel)
admin.site.register(DonationTiltifyModel)
