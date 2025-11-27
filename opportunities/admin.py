from django.contrib import admin
from .models import CreatorProfile, Opportunity, SubscriptionAttribution, CreatorEarning

@admin.register(CreatorProfile)
class CreatorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_earnings', 'active_subscribers', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['total_earnings', 'active_subscribers', 'created_at']

@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ['title', 'creator', 'content_type', 'status', 'views_count', 'subscribers_gained', 'created_at']
    list_filter = ['content_type', 'status', 'country', 'created_at']
    search_fields = ['title', 'creator__username', 'description']
    readonly_fields = ['views_count', 'subscribers_gained', 'created_at', 'updated_at']
    actions = ['approve_opportunities', 'reject_opportunities']
    
    def approve_opportunities(self, request, queryset):
        queryset.update(status='published')
        self.message_user(request, f"{queryset.count()} opportunities approved.")
    approve_opportunities.short_description = "Approve selected opportunities"
    
    def reject_opportunities(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f"{queryset.count()} opportunities rejected.")
    reject_opportunities.short_description = "Reject selected opportunities"

@admin.register(SubscriptionAttribution)
class SubscriptionAttributionAdmin(admin.ModelAdmin):
    list_display = ['user', 'creator', 'opportunity', 'subscription_start', 'is_active', 'monthly_share_percentage']
    list_filter = ['is_active', 'subscription_start']
    search_fields = ['user__username', 'creator__username', 'opportunity__title']

@admin.register(CreatorEarning)
class CreatorEarningAdmin(admin.ModelAdmin):
    list_display = ['creator', 'month', 'total_subscribers', 'creator_share', 'is_paid']
    list_filter = ['month', 'is_paid']
    search_fields = ['creator__username']
    readonly_fields = ['created_at']