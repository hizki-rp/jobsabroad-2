from rest_framework import serializers
from .models import CreatorApplication, OpportunityPost, CreatorRevenue, ApplicationSettings
from django.contrib.auth.models import User

class CreatorApplicationSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = CreatorApplication
        fields = ['id', 'user', 'user_username', 'application_text', 'experience', 'status', 'applied_at']
        read_only_fields = ['user', 'status', 'applied_at']

class OpportunityPostSerializer(serializers.ModelSerializer):
    creator_username = serializers.SerializerMethodField()
    is_premium_content = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    
    class Meta:
        model = OpportunityPost
        fields = ['id', 'creator', 'creator_username', 'title', 'description', 'content_type', 
                 'content', 'premium_content', 'opportunity_link', 'has_premium_section', 'is_active', 'is_draft', 'created_at', 'is_premium_content', 'is_verified']
        read_only_fields = ['creator', 'created_at']
    
    def get_creator_username(self, obj):
        if obj.creator.is_staff:
            return "MAT"  # Malta Addis Temari for admin posts
        return obj.creator.username
    
    def get_is_premium_content(self, obj):
        return obj.has_premium_section
    
    def get_is_verified(self, obj):
        return obj.creator.is_staff
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        # Use same logic as universities permission system
        if request and request.user.is_authenticated:
            # Staff always have access
            if request.user.is_staff:
                return data
            
            # Check subscription using same method as universities
            try:
                dashboard = request.user.dashboard
                has_active_subscription = dashboard.subscription_status == 'active'
                
                if not has_active_subscription:
                    data['premium_content'] = None
                    data['opportunity_link'] = None
            except AttributeError:
                # No dashboard - hide premium content
                data['premium_content'] = None
                data['opportunity_link'] = None
        else:
            # Not authenticated - hide premium content
            data['premium_content'] = None
            data['opportunity_link'] = None
        
        return data

class ApplicationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationSettings
        fields = ['is_open', 'creator_revenue_percentage', 'creators_needed', 'show_creator_tab']