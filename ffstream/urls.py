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

from .views import *

urlpatterns = [
    path('pub/start', start, name='pub-start'),
    path('pub/start-srt', start_srt, name='pub-start-srt'),
    path('pub/start-livestream', start_livestream, name='pub-start-livestream'),
    path('pub/play', play, name='pub-play'),
    path('play/<str:key>/<str:name>', goto, name='goto'),
    path('view/<str:key>', view, name='view'),
    path('pub/stop', stop, name='pub-stop'),
]
