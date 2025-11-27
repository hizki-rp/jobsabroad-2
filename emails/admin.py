from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import EmailTemplate, EmailLog, BulkEmail


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'subject']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'subject', 'body', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'subject', 'status', 'sent_at', 'created_at']
    list_filter = ['status', 'sent_at', 'created_at', 'template']
    search_fields = ['recipient__username', 'recipient__email', 'subject']
    readonly_fields = ['created_at', 'sent_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('recipient', 'subject', 'body', 'template', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'sent_at'),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipient', 'template', 'sent_by')


@admin.register(BulkEmail)
class BulkEmailAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'status', 'total_recipients', 'sent_count', 'success_rate', 'created_at']
    list_filter = ['status', 'created_at', 'template']
    search_fields = ['name', 'subject']
    readonly_fields = ['created_at', 'sent_at', 'total_recipients', 'sent_count', 'failed_count']
    filter_horizontal = ['recipients']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'subject', 'body', 'template', 'status')
        }),
        ('Recipients', {
            'fields': ('recipients',),
        }),
        ('Statistics', {
            'fields': ('total_recipients', 'sent_count', 'failed_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'sent_at'),
            'classes': ('collapse',)
        }),
    )
    
    def success_rate(self, obj):
        rate = obj.get_success_rate()
        color = 'green' if rate >= 80 else 'orange' if rate >= 50 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate.short_description = 'Success Rate'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('template', 'created_by')




