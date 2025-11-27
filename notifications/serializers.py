from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    # is_read is annotated in the queryset; expose it as a read-only field
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'message',
            'created_at',
            'expires_at',
            'is_read',
        ]
