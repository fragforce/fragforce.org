import uuid

from django.conf import settings
from django.db import models

from ffstream.wordlist import generate_stream_key


class Key(models.Model):
    stream_key = models.CharField(max_length=255, unique=True, blank=True, verbose_name="Stream Key")
    name = models.SlugField(max_length=256, unique=True, verbose_name="Display Name")
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Owner"
        )
    created = models.DateTimeField(verbose_name="Created At", null=True, blank=True, auto_now_add=True)
    modified = models.DateTimeField(null=False, auto_now=True, blank=True, verbose_name="Modified At")
    is_live = models.BooleanField(null=False, default=False, blank=True, verbose_name="Is Live")
    livestream = models.BooleanField(null=False, default=False, blank=True,
                                     verbose_name="Can be used to live stream via reflector directly")
    superstream = models.BooleanField(
        null=False,
        default=False,
        blank=True,
        verbose_name="Can be used for Super Stream events"
        )
    pull = models.BooleanField(default=False, blank=True, verbose_name="Can be used as a viewer key to watch streams")

    def save(self, *args, **kwargs):
        if not self.stream_key:
            candidate = generate_stream_key()
            while Key.objects.filter(stream_key=candidate).exists():
                candidate = generate_stream_key()
            self.stream_key = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        permissions = [
            ('set_key_livestream', 'Can set the livestream flag on stream keys'),
            ('set_key_superstream', 'Can set the superstream flag on stream keys'),
        ]


class Stream(models.Model):
    guid = models.UUIDField(default=uuid.uuid4, primary_key=True)
    key = models.ForeignKey(Key, on_delete=models.CASCADE, null=False, blank=False)
    # owner = models.ForeignKey('ffsfdc.Contact', on_delete=models.CASCADE, null=False, blank=False)
    created = models.DateTimeField(verbose_name="Created At", auto_now_add=True)
    modified = models.DateTimeField(null=False, auto_now=True, verbose_name="Modified At")
    is_live = models.BooleanField(null=False, default=False, verbose_name="Is Live")
    started = models.DateTimeField(verbose_name="Started Streaming At", null=True)
    ended = models.DateTimeField(verbose_name="Ended Streaming At", null=True)
    saved_as = models.CharField(max_length=254, null=True, blank=False)

    def set_stream_key(self):
        self.saved_as = self.stream_key()
        self.save()

    @staticmethod
    def make_stream_key(key_name, guid):
        # Changes here may need to be mirrored to migration 0003_stream_saved_as.py
        return "%s__%s" % (key_name, guid)

    def url(self):
        return "%s/dash/%s/index.mpd" % (
            settings.STREAM_DASH_BASE,
            self.stream_key(),
        )

    def stream_key(self):
        if self.saved_as:
            return self.saved_as
        return self.make_stream_key(self.key.name, self.guid)

    def __str__(self):
        return self.stream_key()
