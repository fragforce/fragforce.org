import datetime

from django.conf import settings

def common_org(request):
    """ Context processors for all ffsite pages """
    return dict(
        now=datetime.datetime.utcnow(),
        gaid=settings.GOOGLE_ANALYTICS_ID,
    )
