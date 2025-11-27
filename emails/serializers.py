from rest_framework import serializers
from django.contrib.auth.models import User
from .models import EmailTemplate, EmailLog, BulkEmail


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = ['id', 'name', 'subject', 'body', 'is_active', 'created_at', 'updated_at']


class EmailLogSerializer(serializers.ModelSerializer):
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    recipient_email = serializers.CharField(source='recipient.email', read_only=True)
    sent_by_username = serializers.CharField(source='sent_by.username', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    
    class Meta:
        model = EmailLog
        fields = [
            'id', 'recipient', 'recipient_username', 'recipient_email',
            'subject', 'body', 'template', 'template_name', 'status',
            'sent_at', 'error_message', 'created_at', 'sent_by', 'sent_by_username'
        ]


class BulkEmailSerializer(serializers.ModelSerializer):
    recipients_count = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    
    class Meta:
        model = BulkEmail
        fields = [
            'id', 'name', 'subject', 'body', 'template', 'template_name',
            'recipients', 'status', 'total_recipients', 'sent_count',
            'failed_count', 'recipients_count', 'success_rate',
            'created_at', 'sent_at', 'created_by', 'created_by_username'
        ]
    
    def get_recipients_count(self, obj):
        return obj.recipients.count()
    
    def get_success_rate(self, obj):
        return obj.get_success_rate()


class UserEmailSerializer(serializers.ModelSerializer):
    """Serializer for user selection in email forms"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'is_active']
    
    def get_full_name(self, obj):
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        return obj.username




