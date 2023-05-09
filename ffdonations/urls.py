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

from ffdonations.views import *

urlpatterns = [
    # Test stuff - Only enabled if DEBUG=True
    path('test', v_testView, name='testview'),
    path('update/force', v_forceUpdate, name='force-update'),
    # Teams
    path('teams', v_teams, name='teams'),
    path('teams/tracked', v_tracked_teams, name='teams-tracked'),
    # Participants
    path('participants', v_participants, name='participants'),
    path('participants/tracked', v_tracked_participants, name='participants-tracked'),
    # Donations
    path('donations', v_donations, name='donations'),
    path('donations/tracked', v_tracked_donations, name='donations-tracked'),
    path('donations/tracked/stats', v_tracked_donations_stats, name='donations-tracked-stats'),
    # Stats
    path('stats/donations/tracked', v_tracked_donations_stats, name='stats-donations-tracked'),
]
