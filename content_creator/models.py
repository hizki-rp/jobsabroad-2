from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class CreatorApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    application_text = models.TextField(help_text="Why do you want to become a creator?")
    experience = models.TextField(help_text="Your relevant experience")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    
    def __str__(self):
        return f"{self.user.username} - {self.status}"

class OpportunityPost(models.Model):
    CONTENT_TYPES = [
        ('scholarship', 'Scholarship'),
        ('internship', 'Internship'),
        ('job', 'Job'),
        ('exchange', 'Exchange Program'),
        ('tutorial', 'Tutorial'),
        ('guide', 'Application Guide'),
        ('success_story', 'Success Story'),
        ('insight', 'Country/University Insight'),
    ]
    
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200)
    description = models.TextField()
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    content = models.TextField(help_text="Public content visible to all users")
    premium_content = models.TextField(blank=True, help_text="Premium content only visible to subscribers")
    opportunity_link = models.URLField(blank=True, help_text="Premium link to opportunity")
    has_premium_section = models.BooleanField(default=False, help_text="Has premium content section")
    is_active = models.BooleanField(default=True)
    is_draft = models.BooleanField(default=False, help_text="Save as draft (not published)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} by {self.creator.username}"

class CreatorRevenue(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='revenues')
    subscriber = models.ForeignKey(User, on_delete=models.CASCADE, related_name='creator_subscriptions')
    post = models.ForeignKey(OpportunityPost, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['creator', 'subscriber', 'post']
    
    def __str__(self):
        return f"{self.creator.username} earned {self.amount} from {self.subscriber.username}"

class ApplicationSettings(models.Model):
    is_open = models.BooleanField(default=False, help_text="Allow new creator applications - only open when spots are available")
    creator_revenue_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=35.00, help_text="Percentage of subscription revenue for creators")
    creators_needed = models.PositiveIntegerField(default=5, help_text="Number of creators needed")
    show_creator_tab = models.BooleanField(default=False, help_text="Show creator application tab to users")
    
    class Meta:
        verbose_name = "Application Settings"
        verbose_name_plural = "Application Settings"
    
    def save(self, *args, **kwargs):
        if not self.pk and ApplicationSettings.objects.exists():
            raise ValueError('Only one ApplicationSettings instance allowed')
        return super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        settings, created = cls.objects.get_or_create(defaults={'is_open': False})
        return settings