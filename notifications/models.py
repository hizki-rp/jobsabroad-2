from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Notification(models.Model):
    AUDIENCE_ALL = 'all'
    AUDIENCE_CUSTOM = 'custom'
    AUDIENCE_CHOICES = [
        (AUDIENCE_ALL, 'All Users'),
        (AUDIENCE_CUSTOM, 'Selected Users'),
    ]

    title = models.CharField(max_length=200)
    message = models.TextField()
    audience = models.CharField(max_length=10, choices=AUDIENCE_CHOICES, default=AUDIENCE_ALL)
    recipients = models.ManyToManyField(User, blank=True, related_name='notifications')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def is_expired(self):
        return self.expires_at and timezone.now() > self.expires_at


class NotificationRead(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='reads')
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'notification')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['notification']),
        ]

    def __str__(self):
        return f"{self.user.username} read {self.notification_id}"
