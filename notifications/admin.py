from django.contrib import admin
from django.contrib.auth.models import User
from .models import Notification, NotificationRead

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "audience", "is_active", "created_at", "expires_at")
    list_filter = ("audience", "is_active", "created_at")
    search_fields = ("title", "message")
    filter_horizontal = ("recipients",)
    fieldsets = (
        (None, {"fields": ("title", "message")}),
        ("Audience", {"fields": ("audience", "recipients")}),
        ("Lifecycle", {"fields": ("is_active", "expires_at")}),
    )

@admin.register(NotificationRead)
class NotificationReadAdmin(admin.ModelAdmin):
    list_display = ("user", "notification", "read_at")
    list_filter = ("read_at",)
    autocomplete_fields = ("user", "notification")
