from django.urls import path
from .views import NotificationListView, mark_all_read

urlpatterns = [
    path('notifications/', NotificationListView.as_view(), name='notifications-list'),
    path('notifications/mark-all-read/', mark_all_read, name='notifications-mark-all-read'),
]
