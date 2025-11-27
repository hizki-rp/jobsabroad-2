from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class CreatorApplicationSettings(models.Model):
    """Global settings for creator applications"""
    applications_open = models.BooleanField(default=False)
    application_deadline = models.DateTimeField(null=True, blank=True)
    max_applications = models.IntegerField(default=100)
    current_applications = models.IntegerField(default=0)
    requirements = models.TextField(default="", help_text="Requirements for becoming a creator")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Creator Application Settings"
        verbose_name_plural = "Creator Application Settings"
    
    def __str__(self):
        return f"Creator Applications {'Open' if self.applications_open else 'Closed'}"

class CreatorApplication(models.Model):
    """User applications to become content creators"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='creator_application')
    motivation = models.TextField(help_text="Why do you want to become a creator?")
    expertise_areas = models.JSONField(default=list, help_text="Areas of expertise")
    experience = models.TextField(help_text="Relevant experience")
    sample_content = models.TextField(help_text="Sample content or portfolio")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Admin review notes")
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    
    class Meta:
        ordering = ['-applied_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.status}"

class CreatorProfile(models.Model):
    """Extended profile for content creators"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='creator_profile')
    bio = models.TextField(max_length=500, blank=True)
    expertise_areas = models.JSONField(default=list, help_text="Areas of expertise like 'scholarships', 'visa', 'applications'")
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    active_subscribers = models.IntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    is_approved_creator = models.BooleanField(default=False, help_text="Approved to create content")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - Creator"

class Opportunity(models.Model):
    """Main content model for opportunities, tutorials, etc."""
    CONTENT_TYPES = [
        ('scholarship', 'Scholarship'),
        ('internship', 'Internship'),
        ('job', 'Job Opportunity'),
        ('exchange', 'Exchange Program'),
        ('tutorial', 'Tutorial/Guide'),
        ('result', 'Success Story/Result'),
        ('insight', 'Country/University Insight'),
        ('other', 'Other')
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('published', 'Published'),
        ('rejected', 'Rejected')
    ]
    
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='opportunities')
    title = models.CharField(max_length=200)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    description = models.TextField(max_length=1000, help_text="Public preview description")
    content = models.TextField(help_text="Full content visible to premium users")
    opportunity_links = models.JSONField(default=list, help_text="Hidden links for premium users")
    tags = models.JSONField(default=list, help_text="Tags for categorization")
    country = models.CharField(max_length=100, blank=True)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    views_count = models.IntegerField(default=0)
    subscribers_gained = models.IntegerField(default=0, help_text="Subscriptions attributed to this post")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} by {self.creator.username}"

class SubscriptionAttribution(models.Model):
    """Track which creator gets revenue share from subscriptions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscription_attributions')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attributed_subscriptions')
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='subscription_attributions')
    subscription_start = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    monthly_share_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('35.00'))
    
    class Meta:
        unique_together = ['user', 'creator']
    
    def __str__(self):
        return f"{self.user.username} -> {self.creator.username} ({self.monthly_share_percentage}%)"

class CreatorEarning(models.Model):
    """Monthly earnings record for creators"""
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='earnings')
    month = models.DateField()
    total_subscribers = models.IntegerField(default=0)
    gross_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    creator_share = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['creator', 'month']
        ordering = ['-month']
    
    def __str__(self):
        return f"{self.creator.username} - {self.month.strftime('%Y-%m')} - {self.creator_share} ETB"

class OpportunityView(models.Model):
    """Track opportunity views for analytics"""
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['opportunity', 'user', 'ip_address']