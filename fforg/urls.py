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

from django.contrib import admin
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.urls import path, include
from django.views.decorators.http import require_POST

@require_POST
def logout(request):
    auth_logout(request)
    return redirect('/')


urlpatterns = [
    path('auth/', include('social_django.urls', namespace='social')),
    path('auth/logout/', logout, name='logout'),
    path('admin/', admin.site.urls),
    path('d/', include('ffdonations.urls')),
    path('', include('ffsite.urls')),
    path('stream/', include('ffstream.urls')),
    path('overlays/', include('ffoverlay.urls')),
    path('signup/', include('evtsignup.urls')),
    path('events/', include('eventer.urls')),
]
