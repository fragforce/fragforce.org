from django.db import models
from django.utils import timezone


class Hcmeta(models.Model):
    hcver = models.IntegerField(blank=True, null=True)
    org_id = models.CharField(max_length=50, blank=True, null=True)
    details = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = '_hcmeta'


class SfEventLog(models.Model):
    table_name = models.CharField(max_length=128, blank=True, null=True)
    action = models.CharField(max_length=7, blank=True, null=True)
    synced_at = models.DateTimeField(blank=True, null=True)
    sf_timestamp = models.DateTimeField(blank=True, null=True)
    sfid = models.CharField(max_length=20, blank=True, null=True)
    record = models.TextField(blank=True, null=True)
    processed = models.BooleanField(null=True)

    class Meta:
        managed = False
        db_table = '_sf_event_log'


class TriggerLog(models.Model):
    txid = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    processed_tx = models.BigIntegerField(blank=True, null=True)
    state = models.CharField(max_length=8, blank=True, null=True)
    action = models.CharField(max_length=7, blank=True, null=True)
    table_name = models.CharField(max_length=128, blank=True, null=True)
    record_id = models.IntegerField(blank=True, null=True)
    sfid = models.CharField(max_length=18, blank=True, null=True)
    old = models.TextField(blank=True, null=True)
    values = models.TextField(blank=True, null=True)
    sf_result = models.IntegerField(blank=True, null=True)
    sf_message = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = '_trigger_log'


class TriggerLogArchive(models.Model):
    id = models.IntegerField(primary_key=True)
    txid = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    processed_tx = models.BigIntegerField(blank=True, null=True)
    state = models.CharField(max_length=8, blank=True, null=True)
    action = models.CharField(max_length=7, blank=True, null=True)
    table_name = models.CharField(max_length=128, blank=True, null=True)
    record_id = models.IntegerField(blank=True, null=True)
    sfid = models.CharField(max_length=18, blank=True, null=True)
    old = models.TextField(blank=True, null=True)
    values = models.TextField(blank=True, null=True)
    sf_result = models.IntegerField(blank=True, null=True)
    sf_message = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = '_trigger_log_archive'


class SiteAccount(models.Model):
    jigsaw = models.CharField(max_length=20, blank=True, null=True)
    shippinglongitude = models.FloatField(blank=True, null=True)
    shippingstate = models.CharField(max_length=80, blank=True, null=True)
    youtubeid = models.CharField(db_column='youtubeid__c', max_length=80, blank=True, null=True)
    numberofemployees = models.IntegerField(blank=True, null=True)
    parent = models.ForeignKey('SiteAccount', to_field='sfid', db_column='parentid',
                               on_delete=models.CASCADE,
                               max_length=18, blank=True, null=True)
    recordtypeid = models.CharField(max_length=18, blank=True, null=True)
    shippingpostalcode = models.CharField(max_length=20, blank=True, null=True)
    billingcity = models.CharField(max_length=40, blank=True, null=True)
    billinglatitude = models.FloatField(blank=True, null=True)
    accountsource = models.CharField(max_length=40, blank=True, null=True)
    shippingcountry = models.CharField(max_length=80, blank=True, null=True)
    lastvieweddate = models.DateTimeField(blank=True, null=True)
    shippinggeocodeaccuracy = models.CharField(max_length=40, blank=True, null=True)
    last_el_update = models.DateTimeField(db_column='last_el_update__c', blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    site_el_raised = models.FloatField(db_column='site_el_raised__c', blank=True, null=True)
    lastmodifieddate = models.DateTimeField(blank=True, null=True)
    phone = models.CharField(max_length=40, blank=True, null=True)
    masterrecordid = models.CharField(max_length=18, blank=True, null=True)
    ownerid = models.CharField(max_length=18, blank=True, null=True)
    isdeleted = models.BooleanField(null=True)
    site_el_goal = models.FloatField(db_column='site_el_goal__c', blank=True, null=True)
    systemmodstamp = models.DateTimeField(blank=True, null=True)
    el_id = models.CharField(db_column='el_id__c', max_length=80, blank=True, null=True)
    lastmodifiedbyid = models.CharField(max_length=18, blank=True, null=True)
    shippingstreet = models.CharField(max_length=255, blank=True, null=True)
    lastactivitydate = models.DateField(blank=True, null=True)
    billingpostalcode = models.CharField(max_length=20, blank=True, null=True)
    billinglongitude = models.FloatField(blank=True, null=True)
    twitchid = models.CharField(db_column='twitchid__c', max_length=80, blank=True, null=True)
    twitterid = models.CharField(db_column='twitterid__c', max_length=80, blank=True, null=True)
    createddate = models.DateTimeField(blank=True, null=True)
    billingstate = models.CharField(max_length=80, blank=True, null=True)
    supplies = models.TextField(db_column='supplies__c', blank=True, null=True)
    jigsawcompanyid = models.CharField(max_length=20, blank=True, null=True)
    shippingcity = models.CharField(max_length=40, blank=True, null=True)
    shippinglatitude = models.FloatField(blank=True, null=True)
    createdbyid = models.CharField(max_length=18, blank=True, null=True)
    type = models.CharField(max_length=40, blank=True, null=True)
    website = models.CharField(max_length=255, blank=True, null=True)
    billingcountry = models.CharField(max_length=80, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    billinggeocodeaccuracy = models.CharField(max_length=40, blank=True, null=True)
    photourl = models.CharField(max_length=255, blank=True, null=True)
    lastreferenceddate = models.DateTimeField(blank=True, null=True)
    sicdesc = models.CharField(max_length=80, blank=True, null=True)
    industry = models.CharField(max_length=40, blank=True, null=True)
    billingstreet = models.CharField(max_length=255, blank=True, null=True)
    site_email = models.CharField(db_column='site_email__c', max_length=80, blank=True, null=True)
    sfid = models.CharField(unique=True, max_length=18, blank=True, null=True)
    field_hc_lastop = models.CharField(db_column='_hc_lastop', max_length=32, blank=True, null=True)
    field_hc_err = models.TextField(db_column='_hc_err', blank=True, null=True)
    site_info = models.TextField(db_column='site_info__c', blank=True, null=True)
    nerd_in_chief = models.CharField(db_column='nerd_in_chief__c', max_length=18, blank=True, null=True)
    mayedit = models.BooleanField(null=True)
    # contacturl = models.CharField(db_column='contacturl__c', max_length=1300, blank=True, null=True)
    islocked = models.BooleanField(null=True)
    loot_guard = models.CharField(db_column='loot_guard__c', max_length=18, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'account'

    def has_events(self):
        """ Return True if this account has upcoming events """
        return Event.objects.filter(event_start_date__gte=timezone.now(), site=self).count() > 0

    def upcoming(self):
        return self.events.filter(event_start_date__gte=timezone.now()).order_by('event_start_date').all()

    def past(self):
        return self.events.filter(event_start_date__lt=timezone.now()).order_by('-event_start_date').all()


class Contact(models.Model):
    lastname = models.CharField(max_length=80, blank=True, null=True)
    account = models.ForeignKey(SiteAccount, to_field='sfid', db_column='accountid', on_delete=models.CASCADE,
                                max_length=18, blank=True, null=True)
    name = models.CharField(max_length=121, blank=True, null=True)
    ownerid = models.CharField(max_length=18, blank=True, null=True)
    department = models.CharField(max_length=80, blank=True, null=True)
    extra_life_id = models.CharField(db_column='extra_life_id__c', unique=True, max_length=20, blank=True, null=True)
    fragforce_org_user = models.CharField(db_column='fragforce_org_user__c', max_length=18, blank=True, null=True)
    title = models.CharField(max_length=128, blank=True, null=True)
    firstname = models.CharField(max_length=40, blank=True, null=True)
    sfid = models.CharField(unique=True, max_length=18, blank=True, null=True)
    field_hc_lastop = models.CharField(db_column='_hc_lastop', max_length=32, blank=True, null=True)
    field_hc_err = models.TextField(db_column='_hc_err', blank=True, null=True)

    def donate_link(self):
        if self.extra_life_id:
            return "https://www.extra-life.org/index.cfm?fuseaction=donate.participant&participantID=%d" % (
                int(self.extra_life_id),
            )
        raise ValueError("No extra life id set for %r" % self)

    class Meta:
        managed = False
        db_table = 'contact'


class ELHistory(models.Model):
    currencyisocode = models.CharField(max_length=3, blank=True, null=True)
    contact = models.ForeignKey(Contact, to_field='sfid', db_column='contact__c', on_delete=models.CASCADE,
                                max_length=18, blank=True, null=True)
    year = models.CharField(db_column='year__c', max_length=255, blank=True, null=True)
    name = models.CharField(max_length=80, blank=True, null=True)
    raised = models.FloatField(db_column='raised__c', blank=True, null=True)
    lastmodifieddate = models.DateTimeField(blank=True, null=True)
    ownerid = models.CharField(max_length=18, blank=True, null=True)
    mayedit = models.BooleanField(null=True)
    isdeleted = models.BooleanField(null=True)
    goal = models.FloatField(db_column='goal__c', blank=True, null=True)
    systemmodstamp = models.DateTimeField(blank=True, null=True)
    el_id = models.CharField(db_column='el_id__c', max_length=7, blank=True, null=True)
    lastmodifiedbyid = models.CharField(max_length=18, blank=True, null=True)
    islocked = models.BooleanField(null=True)
    createddate = models.DateTimeField(blank=True, null=True)
    createdbyid = models.CharField(max_length=18, blank=True, null=True)
    site = models.ForeignKey(SiteAccount, to_field='sfid', db_column='site__c', on_delete=models.CASCADE, max_length=18,
                             blank=True, null=True)
    sfid = models.CharField(unique=True, max_length=18, blank=True, null=True)
    field_hc_lastop = models.CharField(db_column='_hc_lastop', max_length=32, blank=True, null=True)
    field_hc_err = models.TextField(db_column='_hc_err', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'el_history__c'


class Event(models.Model):
    lastvieweddate = models.DateTimeField(blank=True, null=True)
    volunteerforce_link = models.CharField(db_column='volunteerforce_link__c', max_length=255, blank=True, null=True)
    name = models.CharField(max_length=80, blank=True, null=True)
    event_end_date = models.DateTimeField(db_column='event_end_date__c', blank=True, null=True)
    lastmodifieddate = models.DateTimeField(blank=True, null=True)
    isdeleted = models.BooleanField(null=True)
    systemmodstamp = models.DateTimeField(blank=True, null=True)
    lastmodifiedbyid = models.CharField(max_length=18, blank=True, null=True)
    lastactivitydate = models.DateField(blank=True, null=True)
    event_start_date = models.DateTimeField(db_column='event_start_date__c', blank=True, null=True)
    createddate = models.DateTimeField(blank=True, null=True)
    createdbyid = models.CharField(max_length=18, blank=True, null=True)
    site = models.ForeignKey(SiteAccount, to_field='sfid', db_column='site__c', on_delete=models.CASCADE, max_length=18,
                             blank=True, null=True, related_name='events')
    lastreferenceddate = models.DateTimeField(blank=True, null=True)
    sfid = models.CharField(unique=True, max_length=18, blank=True, null=True)
    field_hc_lastop = models.CharField(db_column='_hc_lastop', max_length=32, blank=True, null=True)
    field_hc_err = models.TextField(db_column='_hc_err', blank=True, null=True)
    use_secondary_address = models.BooleanField(db_column='use_secondary_address__c', null=True)
    stream_recording_link = models.CharField(db_column='stream_recording_link__c', max_length=255, blank=True,
                                             null=True)
    # participant_count = models.FloatField(db_column='participant_count__c', blank=True, null=True)
    # prereg_url = models.CharField(db_column='prereg_url__c', max_length=1300, blank=True, null=True)
    mayedit = models.BooleanField(null=True)
    # open_for_preregistration = models.BooleanField(db_column='open_for_preregistration__c', null=True)
    islocked = models.BooleanField(null=True)
    # signinurl = models.CharField(db_column='signinurl__c', max_length=1300, blank=True, null=True)
    # event_address_lookup = models.CharField(db_column='event_address_lookup__c', max_length=1300, blank=True, null=True)
    event_information = models.TextField(db_column='event_information__c', blank=True, null=True)
    # open_for_registration = models.BooleanField(db_column='open_for_registration__c', null=True)
    # Short description of the event
    description = models.TextField(db_column='description__c', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fragforce_event__c'


class EventParticipant(models.Model):
    contact = models.ForeignKey(Contact, to_field='sfid', db_column='contact__c', on_delete=models.CASCADE,
                                max_length=18, blank=True, null=True)
    lastvieweddate = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=80, blank=True, null=True)
    lastmodifieddate = models.DateTimeField(blank=True, null=True)
    ownerid = models.CharField(max_length=18, blank=True, null=True)
    mayedit = models.BooleanField(null=True)
    event = models.ForeignKey(Event, to_field='sfid', db_column='fragforce_event__c', on_delete=models.CASCADE,
                              max_length=18, blank=True,
                              null=True)
    isdeleted = models.BooleanField(null=True)
    participant = models.BooleanField(db_column='participant__c', null=True)
    systemmodstamp = models.DateTimeField(blank=True, null=True)
    lastmodifiedbyid = models.CharField(max_length=18, blank=True, null=True)
    lastactivitydate = models.DateField(blank=True, null=True)
    islocked = models.BooleanField(null=True)
    createddate = models.DateTimeField(blank=True, null=True)
    name = models.CharField(db_column='name__c', max_length=120, blank=True, null=True)
    createdbyid = models.CharField(max_length=18, blank=True, null=True)
    lastreferenceddate = models.DateTimeField(blank=True, null=True)
    sfid = models.CharField(unique=True, max_length=18, blank=True, null=True)
    field_hc_lastop = models.CharField(db_column='_hc_lastop', max_length=32, blank=True, null=True)
    field_hc_err = models.TextField(db_column='_hc_err', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'event_participant__c'
