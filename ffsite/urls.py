"""fforg URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path

from ffsite.views import *

urlpatterns = [
    path('', home, name='home'),
    path('donate', donate, name='donate'),
    path('join', join, name='join'),
    path('contact', contact, name='contact'),
    path('stream', stream, name='stream'),
    path('site', sites, name='org_sites'),
    path('site/<slug:sfid>', site, name='org_site'),
    path('event', events, name='org_events'),
    path('event-upcoming', events_upcoming, name='org_events_upcoming'),
    path('event/<slug:sfid>', event, name='org_event'),
]
