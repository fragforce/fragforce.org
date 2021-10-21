import datetime
import uuid

from django.db import models
from django.db.models import Q
from django.contrib.postgres.fields import HStoreField

## Extra-Life
class EventModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    tracked = models.BooleanField(default=False, verbose_name="Is Tracked")
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")

    # Extra-Life
    id = models.BigIntegerField(primary_key=True, editable=False, verbose_name="Event ID", null=False)
    name = models.CharField(max_length=8192, null=True, verbose_name="Event Name")


class TeamModel(models.Model):
    """ All teams """
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    tracked = models.BooleanField(default=False, verbose_name="Is Tracked")
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")

    # Extra-Life
    id = models.BigIntegerField(primary_key=True, editable=False, verbose_name="Team ID", null=False)
    name = models.CharField(max_length=8192, null=True, verbose_name="Team Name")
    # Info
    created = models.DateTimeField(verbose_name="Created At", null=True)
    fundraisingGoal = models.DecimalField(decimal_places=2, max_digits=50, verbose_name="Fundraising Goal", null=True)
    numDonations = models.BigIntegerField(verbose_name="Donation Count", null=True)
    sumDonations = models.DecimalField(decimal_places=2, max_digits=50, verbose_name="Donations Total", null=True)
    # Related
    event = models.ForeignKey(EventModel, null=True, default=None, verbose_name="Event", on_delete=models.DO_NOTHING)

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)


class ParticipantModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    tracked = models.BooleanField(default=False, verbose_name="Is Tracked")
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")

    # Extra-Life
    id = models.BigIntegerField(primary_key=True, editable=False, verbose_name="Participant ID", null=False)
    displayName = models.CharField(max_length=8192, verbose_name="Participant Name", null=True)
    # Info
    created = models.DateTimeField(verbose_name="Created At", null=True)
    avatarImage = models.URLField(verbose_name="Avatar Image", null=True, max_length=8192)
    campaignDate = models.DateTimeField(null=True, verbose_name="Campaign Date")
    campaignName = models.CharField(max_length=8192, null=True, verbose_name="Campaign Name")
    fundraisingGoal = models.DecimalField(decimal_places=2, max_digits=50, verbose_name="Fundraising Goal", null=True)
    numDonations = models.BigIntegerField(verbose_name="Donation Count", null=True)
    sumDonations = models.DecimalField(decimal_places=2, max_digits=50, verbose_name="Donations Total", null=True)
    sumPledges = models.DecimalField(decimal_places=2, max_digits=50, verbose_name="Pledges Total", null=True)
    isTeamCaptain = models.BooleanField(verbose_name="Is Team Captain", default=False, null=True)
    # Related
    event = models.ForeignKey(EventModel, null=True, default=None, verbose_name="Event", on_delete=models.DO_NOTHING)
    team = models.ForeignKey(TeamModel, null=True, default=None, verbose_name="Team", on_delete=models.DO_NOTHING)

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)


class DonationModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")

    # Extra-Life
    id = models.CharField(primary_key=True, max_length=1024, editable=False, verbose_name="Donation ID", null=False)
    message = models.CharField(max_length=1024 * 1024, verbose_name="Message", default='', null=True)
    amount = models.DecimalField(decimal_places=2, max_digits=50, null=True, default=0, verbose_name="Donation Amount")
    created = models.DateTimeField(verbose_name="Created At", null=True, default=datetime.datetime.utcnow)
    displayName = models.CharField(max_length=8192, verbose_name="Donor Name", null=True, default='')
    avatarImage = models.URLField(verbose_name="Avatar Image", null=True, max_length=8192)

    # Related
    participant = models.ForeignKey(ParticipantModel, null=True, default=None, verbose_name="Participant",
                                    on_delete=models.DO_NOTHING)
    team = models.ForeignKey(TeamModel, null=True, default=None, verbose_name="Team", on_delete=models.DO_NOTHING)

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)
    tracking = HStoreField(verbose_name="Tracking Data", null=True, default=dict)

    @classmethod
    def tracked_q(cls):
        """ Get a Q that filters Donations down to only tracked ones """
        return Q(team__tracked=True) | Q(participant__tracked=True)


## Tiltify
class MediaTiltifyModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")
    id = models.BigAutoField(primary_key=True, verbose_name="ID")

    # Tiltify
    src = models.URLField(max_length=8192, null=True, verbose_name="Source URL")
    alt = models.CharField(max_length=8192, null=True, default='', verbose_name="Alternate Text")
    width = models.IntegerField(null=True, verbose_name="Width (px)")
    height = models.IntegerField(null=True, verbose_name="Height (px)")

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)

    # Type of result from lib
    subtype = models.CharField(max_length=255, null=False, default='MediaResult')


class RewardTiltifyModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")

    # Tiltify
    id = models.BigIntegerField(verbose_name="ID", primary_key=True)
    name = models.CharField(max_length=8192, null=True, default='Name')
    description = models.CharField(max_length=1024 * 1024, null=True, default='Description')
    amount = models.IntegerField(null=True, verbose_name="Amount")
    kind = models.CharField(max_length=8192, null=True, default='Kind')
    quantity = models.IntegerField(null=True, verbose_name="Quantity")
    remaining = models.IntegerField(null=True, verbose_name="Remaining")
    fairMarketValue = models.DecimalField(decimal_places=2, max_digits=50, null=True, verbose_name="Fair Market Value")
    currency = models.CharField(max_length=8192, null=True, default='Currency')
    shippingAddressRequired = models.BooleanField(null=True, verbose_name="Is Active")
    shippingNote = models.CharField(max_length=1024 * 1024, null=True, default='Description')
    active = models.BooleanField(null=True, verbose_name="Is Active")
    startsAt = models.DateTimeField(null=True, verbose_name="Starts At")
    createdAt = models.DateTimeField(null=True, verbose_name="Created At")
    updatedAt = models.DateTimeField(null=True, verbose_name="Updated At")

    image = models.ForeignKey(MediaTiltifyModel, on_delete=models.DO_NOTHING, null=True, verbose_name="Image")

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)


class SocailTiltifyModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")
    id = models.BigAutoField(primary_key=True, verbose_name="ID")

    # Tiltify
    twitter = models.CharField(max_length=8192, null=True, default='Twitter')
    twitch = models.CharField(max_length=8192, null=True, default='Twitch')
    youtube = models.CharField(max_length=8192, null=True, default='Youtube')
    facebook = models.CharField(max_length=8192, null=True, default='Facebook')
    instagram = models.CharField(max_length=8192, null=True, default='Instagram')
    website = models.CharField(max_length=8192, null=True, default='Website')

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)


class AddressTiltifyModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")
    id = models.BigAutoField(primary_key=True, verbose_name="ID")

    # Tiltify
    addressLine1 = models.CharField(max_length=8192, null=True, default='Address Line 1')
    addressLine2 = models.CharField(max_length=8192, null=True, default='Address Line 2')
    city = models.CharField(max_length=8192, null=True, default='City')
    region = models.CharField(max_length=8192, null=True, default='Region')
    postalCode = models.BigIntegerField(null=True, default='Postal Code')
    country = models.CharField(max_length=8192, null=True, default='Country')

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)


class ColorTiltifyModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")
    id = models.BigAutoField(primary_key=True, verbose_name="ID")

    # Tiltify
    highlight = models.CharField(max_length=8192, null=True, default='Hightlight Color')
    background = models.CharField(max_length=8192, null=True, default='Background Color')

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)


class SettingsTiltifyModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")
    id = models.BigAutoField(primary_key=True, verbose_name="ID")

    # Tiltify
    headerIntro = models.CharField(max_length=8192, null=True, default='Intro')
    headerTitle = models.CharField(max_length=8192, null=True, default='Title')
    footerCopyright = models.CharField(max_length=8192, null=True, default='Copyright')
    findOutMoreLink = models.URLField(max_length=8192, null=True, verbose_name="Find Out More")

    colors = models.ForeignKey(ColorTiltifyModel, on_delete=models.DO_NOTHING, null=True, verbose_name="Colors")

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)


class CauseTiltifyModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")

    # Tilify
    id = models.BigIntegerField(verbose_name="ID", primary_key=True)
    name = models.CharField(max_length=8192, null=True, verbose_name="Name")
    legalName = models.CharField(max_length=8192, null=True, verbose_name="Legal Name")
    slug = models.CharField(max_length=8192, null=True, verbose_name="Slug")
    currency = models.CharField(max_length=8192, null=True, verbose_name="Currency")
    about = models.CharField(max_length=8192, null=True, verbose_name="About")
    video = models.URLField(max_length=8192, null=True, verbose_name="Name")
    contactEmail = models.EmailField(max_length=8192, null=True, verbose_name="Contact Email")
    paypalEmail = models.EmailField(max_length=8192, null=True, verbose_name="Paypal Email")
    paypalCurrencyCode = models.CharField(max_length=8192, null=True, verbose_name="Paypal Currency Code")
    status = models.CharField(max_length=8192, null=True, verbose_name="Status")
    stripeConnected = models.BooleanField(null=True, verbose_name="Stripe Connected")
    mailchimpConnected = models.BooleanField(null=True, verbose_name="Mail Chimp Connected")

    image = models.ForeignKey(MediaTiltifyModel, on_delete=models.DO_NOTHING, null=True, verbose_name="Image",
                              related_name='image')
    logo = models.ForeignKey(MediaTiltifyModel, on_delete=models.DO_NOTHING, null=True, verbose_name="Logo",
                             related_name='logo')
    banner = models.ForeignKey(MediaTiltifyModel, on_delete=models.DO_NOTHING, null=True, verbose_name="Banner",
                               related_name='banner')
    social = models.ForeignKey(SocailTiltifyModel, on_delete=models.DO_NOTHING, null=True, verbose_name="Social")
    settings = models.ForeignKey(SettingsTiltifyModel, on_delete=models.DO_NOTHING, null=True, verbose_name="Settings")
    address = models.ForeignKey(AddressTiltifyModel, on_delete=models.DO_NOTHING, null=True, verbose_name="Address")

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)


class EventTiltifyModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")

    # Tilify
    id = models.BigIntegerField(verbose_name="ID", primary_key=True)

    # FIXME: Find out what this should link to


class LiveStreamTiltifyModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")
    id = models.BigIntegerField(verbose_name="ID", primary_key=True)

    # Tilify
    channel = models.CharField(max_length=8192, verbose_name="Channel", null=True)
    stream_type = models.CharField(max_length=8192, verbose_name="Type", null=True)

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)


class TeamTiltifyModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")

    # Tilify
    id = models.BigIntegerField(verbose_name="ID", primary_key=True)
    name = models.CharField(verbose_name="Name", unique=True, null=True, max_length=8192)
    slug = models.CharField(verbose_name="Slug", unique=True, null=True, max_length=8192)
    url = models.CharField(verbose_name="URL", unique=True, null=True, max_length=8192)

    # Cascade
    avatar = models.ForeignKey(MediaTiltifyModel, verbose_name="Avatar", null=True, on_delete=models.DO_NOTHING)
    social = models.ForeignKey(SocailTiltifyModel, verbose_name="Social", null=True, on_delete=models.DO_NOTHING)

    # On some
    bio = models.CharField(max_length=1024 * 1024, verbose_name="Bio")
    inviteOnly = models.BooleanField(verbose_name="Is Invite Only Team", null=True)
    disbanded = models.BooleanField(verbose_name="Is Disbanded", null=True)
    totalAmountRaised = models.DecimalField(decimal_places=2, max_digits=50, verbose_name="Total Amount Raised",
                                            null=True)
    about = models.CharField(verbose_name="About", null=True, max_length=8192)

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)

    # Type of result from lib
    subtype = models.CharField(max_length=255, null=False, default='TeamResult')


class UserTiltifyModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")

    # Tilify
    id = models.BigIntegerField(verbose_name="ID", primary_key=True)
    username = models.CharField(max_length=8192, verbose_name="Username", unique=True, null=True)
    slug = models.CharField(max_length=8192, verbose_name="Slug", unique=True, null=True)
    url = models.URLField(max_length=8192, verbose_name="URL", unique=True, null=True)

    avatar = models.ForeignKey(MediaTiltifyModel, verbose_name="Avatar", null=True, on_delete=models.DO_NOTHING)

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)


class CampaignTiltifyModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")

    # Tilify
    id = models.BigIntegerField(verbose_name="ID", primary_key=True)
    name = models.CharField(max_length=8192, verbose_name="Name", unique=True, null=True)
    slug = models.CharField(max_length=8192, verbose_name="Slug", unique=True, null=True)
    url = models.URLField(max_length=8192, verbose_name="URL", unique=True, null=True)
    startsAt = models.DateTimeField(null=True, verbose_name='Starts At')
    endsAt = models.DateTimeField(null=True, verbose_name='Ends At')
    description = models.CharField(max_length=8192, verbose_name="Description", unique=True, null=True)
    goal = models.DecimalField(decimal_places=2, max_digits=50, verbose_name="Goal Amount", null=True)
    fundraiserGoalAmount = models.DecimalField(decimal_places=2, max_digits=50, verbose_name="Fundraiser Goal Amount",
                                               null=True)
    originalGoalAmount = models.DecimalField(decimal_places=2, max_digits=50, verbose_name="Origional Goal Amount",
                                             null=True)
    amountRaised = models.DecimalField(decimal_places=2, max_digits=50, verbose_name="Amount Raised", null=True)
    supportingAmountRaised = models.DecimalField(decimal_places=2, max_digits=50,
                                                 verbose_name="Supporting Amount Raised", null=True)
    totalAmountRaised = models.DecimalField(decimal_places=2, max_digits=50, verbose_name="Total Amount Raised",
                                            null=True)
    supportable = models.BooleanField(verbose_name="Is Supportable", null=True)
    status = models.CharField(max_length=8192, null=True, verbose_name="Status")
    startsOn = models.DateTimeField(null=True, verbose_name='Starts On')
    endsOn = models.DateTimeField(null=True, verbose_name='Ends On')

    thumbnail = models.ForeignKey(MediaTiltifyModel, verbose_name="Thumbnail", null=True, on_delete=models.DO_NOTHING,
                                  related_name='thumbnail')
    user = models.ForeignKey(UserTiltifyModel, verbose_name="user", null=True, on_delete=models.DO_NOTHING)
    team = models.ForeignKey(TeamTiltifyModel, verbose_name="Team", null=True, on_delete=models.DO_NOTHING)
    livestream = models.ForeignKey(LiveStreamTiltifyModel, verbose_name="Live Stream", null=True,
                                   on_delete=models.DO_NOTHING)
    cause = models.ForeignKey(CauseTiltifyModel, verbose_name="Cause", null=True, on_delete=models.DO_NOTHING)
    avatar = models.ForeignKey(MediaTiltifyModel, verbose_name="Avatar", null=True, on_delete=models.DO_NOTHING,
                               related_name='avatar')
    fundraisingEvent = models.ForeignKey(EventTiltifyModel, verbose_name="Fundraising Event", null=True,
                                         on_delete=models.DO_NOTHING)

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)

    # Type of result from lib
    subtype = models.CharField(max_length=255, null=False, default='CampaignResult')


class DonationTiltifyModel(models.Model):
    # Ours
    guid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, verbose_name="GUID", null=False)
    last_updated = models.DateTimeField(null=False, auto_now=True, verbose_name="Date Record Last Fetched")

    # Tilify
    id = models.BigIntegerField(verbose_name="ID", primary_key=True)
    amount = models.DecimalField(verbose_name="Amount", max_digits=50, decimal_places=2, null=True)
    name = models.CharField(max_length=8192, null=True, verbose_name="Name")
    comment = models.CharField(max_length=1024 * 1024, null=True, verbose_name="Comment")
    completedAt = models.DateTimeField(null=True, verbose_name="Completed At")
    reward = models.ForeignKey(RewardTiltifyModel, verbose_name="Reward", null=True, on_delete=models.DO_NOTHING)
    campaign = models.ForeignKey(CampaignTiltifyModel, verbose_name="Campaign", null=True, on_delete=models.CASCADE)

    # Extra
    raw = models.JSONField(verbose_name="Raw Data", null=True, default=dict)
