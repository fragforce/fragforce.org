from django.urls import path

from eventer import views

urlpatterns = [
    path('', views.event_list, name='eventer-event-list'),
    path('<slug:event_slug>/', views.event_detail, name='eventer-event-detail'),
    path('<slug:event_slug>/schedule/', views.public_schedule_view, name='eventer-public-schedule'),
    path(
        '<slug:event_slug>/schedule/coordinator/',
        views.coordinator_schedule_view,
        name='eventer-coordinator-schedule'
        ),
]
