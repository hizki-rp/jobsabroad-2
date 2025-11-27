from django.contrib import admin
from .models import CreatorApplication, OpportunityPost, CreatorRevenue, ApplicationSettings

@admin.register(ApplicationSettings)
class ApplicationSettingsAdmin(admin.ModelAdmin):
    list_display = ['is_open', 'creator_revenue_percentage']
    
    def has_add_permission(self, request):
        return not ApplicationSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(CreatorApplication)
class CreatorApplicationAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'applied_at', 'reviewed_at']
    list_filter = ['status', 'applied_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['applied_at', 'reviewed_at']
    
    actions = ['approve_applications', 'reject_applications']
    
    def approve_applications(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='approved', reviewed_at=timezone.now(), reviewed_by=request.user)
        self.message_user(request, f'{updated} applications approved.')
    approve_applications.short_description = "Approve selected applications"
    
    def reject_applications(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='rejected', reviewed_at=timezone.now(), reviewed_by=request.user)
        self.message_user(request, f'{updated} applications rejected.')
    reject_applications.short_description = "Reject selected applications"

@admin.register(OpportunityPost)
class OpportunityPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'creator', 'content_type', 'is_active', 'created_at']
    list_filter = ['content_type', 'is_active', 'created_at']
    search_fields = ['title', 'creator__username']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(CreatorRevenue)
class CreatorRevenueAdmin(admin.ModelAdmin):
    list_display = ['creator', 'subscriber', 'amount', 'created_at']
    list_filter = ['created_at']
    search_fields = ['creator__username', 'subscriber__username']
    readonly_fields = ['created_at']