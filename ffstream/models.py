import uuid

from django.conf import settings
from django.db import models


class Key(models.Model):
    id = models.CharField(max_length=255, primary_key=True, blank=True)
    name = models.SlugField(max_length=256, unique=True)
    # owner = models.ForeignKey('ffsfdc.Contact', on_delete=models.CASCADE, null=False, blank=False)
    created = models.DateTimeField(verbose_name="Created At", null=True, blank=True, auto_now_add=True)
    modified = models.DateTimeField(null=False, auto_now=True, blank=True, verbose_name="Modified At")
    is_live = models.BooleanField(null=False, default=False, blank=True, verbose_name="Is Live")
    livestream = models.BooleanField(null=False, default=False, blank=True, verbose_name="Can be used to live stream via reflector directly")
    active = models.BooleanField(default=True, blank=True, verbose_name="Can be used for streaming")
    pull = models.BooleanField(default=False, blank=True, verbose_name="Can be used for pulling streaming")

    def __str__(self):
        return self.name


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
