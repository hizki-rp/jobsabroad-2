from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    CreatorProfile, Opportunity, SubscriptionAttribution, CreatorEarning,
    CreatorApplicationSettings, CreatorApplication
)

class CreatorProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = CreatorProfile
        fields = ['username', 'bio', 'expertise_areas', 'total_earnings', 'active_subscribers', 'is_verified', 'created_at']
        read_only_fields = ['total_earnings', 'active_subscribers', 'is_verified']

class OpportunityListSerializer(serializers.ModelSerializer):
    """Serializer for opportunity list view (preview mode)"""
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    creator_verified = serializers.BooleanField(source='creator.creator_profile.is_verified', read_only=True)
    
    class Meta:
        model = Opportunity
        fields = [
            'id', 'title', 'content_type', 'description', 'tags', 'country', 
            'deadline', 'views_count', 'subscribers_gained', 'created_at',
            'creator_name', 'creator_verified'
        ]

class OpportunityDetailSerializer(serializers.ModelSerializer):
    """Serializer for opportunity detail view (premium content)"""
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    creator_verified = serializers.BooleanField(source='creator.creator_profile.is_verified', read_only=True)
    
    class Meta:
        model = Opportunity
        fields = [
            'id', 'title', 'content_type', 'description', 'content', 
            'opportunity_links', 'tags', 'country', 'deadline', 
            'views_count', 'subscribers_gained', 'created_at', 'updated_at',
            'creator_name', 'creator_verified'
        ]

class OpportunityCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating opportunities"""
    
    class Meta:
        model = Opportunity
        fields = [
            'title', 'content_type', 'description', 'content', 
            'opportunity_links', 'tags', 'country', 'deadline'
        ]
    
    def create(self, validated_data):
        validated_data['creator'] = self.context['request'].user
        validated_data['status'] = 'pending'
        return super().create(validated_data)

class SubscriptionAttributionSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    opportunity_title = serializers.CharField(source='opportunity.title', read_only=True)
    
    class Meta:
        model = SubscriptionAttribution
        fields = [
            'creator_name', 'opportunity_title', 'subscription_start', 
            'is_active', 'monthly_share_percentage'
        ]

class CreatorEarningSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorEarning
        fields = [
            'month', 'total_subscribers', 'gross_revenue', 
            'creator_share', 'is_paid', 'created_at'
        ]

class CreatorApplicationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorApplicationSettings
        fields = '__all__'

class CreatorApplicationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = CreatorApplication
        fields = [
            'id', 'username', 'user_email', 'motivation', 'expertise_areas',
            'experience', 'sample_content', 'status', 'admin_notes',
            'applied_at', 'reviewed_at', 'reviewed_by'
        ]
        read_only_fields = ['status', 'admin_notes', 'reviewed_at', 'reviewed_by']

class CreatorApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorApplication
        fields = ['motivation', 'expertise_areas', 'experience', 'sample_content']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)